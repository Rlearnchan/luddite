"""Safe RSS endpoint discovery and fetch/parse probe tooling."""

from __future__ import annotations

import json
from dataclasses import asdict, dataclass, field
from datetime import UTC, datetime
from html.parser import HTMLParser
from pathlib import Path
from typing import Annotated, Protocol
from urllib.error import HTTPError, URLError
from urllib.parse import urljoin
from urllib.request import Request, urlopen
from xml.etree import ElementTree

import typer
from rich.console import Console

from luddite import paths
from luddite.collectors.source_registry import Source, load_sources

app = typer.Typer(no_args_is_help=False)
console = Console()

DISCOVERY_PATHS = (
    "/rss",
    "/rss.xml",
    "/feed",
    "/feed.xml",
    "/atom.xml",
    "/feeds",
    "/feeds/rss",
    "/news/rss",
    "/news/rss.xml",
    "/world/rss",
    "/world/rss.xml",
    "/business/rss",
    "/business/rss.xml",
    "/economy/rss",
    "/economy/rss.xml",
    "/international/rss",
    "/international/rss.xml",
)

SKIPPED_DEFAULT_STATUSES = {
    "manual",
    "subscription_manual",
    "official_evidence",
    "official_release",
    "disabled",
}


@dataclass(frozen=True)
class HttpResponse:
    url: str
    status: int | None
    content_type: str | None
    body: bytes


class HttpClient(Protocol):
    def fetch(self, url: str, *, timeout: float) -> HttpResponse:
        """Fetch a URL and return response metadata plus body."""


class UrlLibHttpClient:
    def fetch(self, url: str, *, timeout: float) -> HttpResponse:
        request = Request(
            url,
            headers={
                "User-Agent": "LudditeRSSProbe/1.0 (+https://github.com/Rlearnchan/luddite)"
            },
        )
        with urlopen(request, timeout=timeout) as response:  # noqa: S310
            return HttpResponse(
                url=response.geturl(),
                status=response.status,
                content_type=response.headers.get("content-type"),
                body=response.read(1_000_000),
            )


@dataclass(frozen=True)
class SampleItem:
    title: str | None
    url: str | None
    published_at: str | None


@dataclass(frozen=True)
class FeedCandidate:
    url: str
    method: str
    label: str | None = None


@dataclass
class RssProbeResult:
    source_id: str
    name: str
    group: str | None
    input_status: str
    collection_enabled: bool = False
    homepage_url: str | None = None
    rss_index_url: str | None = None
    desired_feed: str | None = None
    extracted_feed_candidates: list[str] = field(default_factory=list)
    tested_urls: list[str] = field(default_factory=list)
    verified_feed_url: str | None = None
    discovery_method: str = "failed"
    tested_url: str | None = None
    http_status: int | None = None
    content_type: str | None = None
    parse_status: str = "not_tested"
    item_count: int = 0
    sample_items: list[SampleItem] = field(default_factory=list)
    recommendation: str = "keep_rss_candidate"
    failure_reason: str | None = None
    checked_at: str = ""
    skipped: bool = False
    terms_check_required: bool = False

    def to_json_dict(self) -> dict[str, object]:
        payload = asdict(self)
        payload["sample_items"] = [asdict(item) for item in self.sample_items]
        return payload


@dataclass(frozen=True)
class ProbeSummary:
    total_sources_checked: int
    verified: int
    failed: int
    skipped: int


def source_status(source: Source) -> str:
    return source.status or source.type


def discovery_urls(source: Source) -> list[str]:
    return [candidate.url for candidate in feed_candidates(source)]


def feed_candidates(source: Source) -> list[FeedCandidate]:
    candidates: list[FeedCandidate] = []
    for url in source.feed_url_candidates:
        candidates.append(FeedCandidate(url=url, method="configured_feed_url"))
    if source.feed_url:
        candidates.insert(0, FeedCandidate(url=source.feed_url, method="configured_feed_url"))
    if source.verified_feed_url:
        candidates.insert(
            0, FeedCandidate(url=source.verified_feed_url, method="configured_feed_url")
        )
    if not source.homepage_url:
        return candidates
    base_url = source.homepage_url.rstrip("/") + "/"
    candidates.extend(
        FeedCandidate(url=urljoin(base_url, path.lstrip("/")), method="known_path_candidate")
        for path in DISCOVERY_PATHS
    )
    return _dedupe_candidates(candidates)


def _dedupe_candidates(candidates: list[FeedCandidate]) -> list[FeedCandidate]:
    seen: set[str] = set()
    deduped: list[FeedCandidate] = []
    for candidate in candidates:
        if candidate.url in seen:
            continue
        seen.add(candidate.url)
        deduped.append(candidate)
    return deduped


def should_probe_source(source: Source, *, include_official: bool = False) -> bool:
    status = source_status(source)
    if status in {"rss_candidate", "rss_verified", "rss_failed"}:
        return True
    if include_official and status in {"official_evidence", "official_release"}:
        return True
    return False


def skipped_result(source: Source, *, checked_at: str) -> RssProbeResult:
    status = source_status(source)
    return RssProbeResult(
        source_id=source.id,
        name=source.name,
        group=source.group,
        input_status=status,
        collection_enabled=source.collection_enabled,
        homepage_url=source.homepage_url,
        rss_index_url=source.rss_index_url,
        desired_feed=source.desired_feed,
        recommendation=(
            "keep_subscription_manual" if status == "subscription_manual" else "manual_only"
        ),
        failure_reason=f"Skipped status: {status}",
        checked_at=checked_at,
        skipped=True,
    )


def probe_sources(
    *,
    registry_path: Path = paths.SOURCE_REGISTRY_YAML,
    http_client: HttpClient | None = None,
    include_official: bool = False,
    include_disabled: bool = False,
    source_id: str | None = None,
    limit: int | None = None,
    timeout: float = 8.0,
    checked_at: datetime | None = None,
) -> list[RssProbeResult]:
    client = http_client or UrlLibHttpClient()
    checked_at_text = (checked_at or datetime.now(UTC)).isoformat()
    sources = load_sources(registry_path)
    if source_id:
        sources = [source for source in sources if source.id == source_id]

    results: list[RssProbeResult] = []
    probed_count = 0
    for source in sources:
        if source_status(source) == "disabled" and not include_disabled:
            results.append(skipped_result(source, checked_at=checked_at_text))
            continue
        if not should_probe_source(source, include_official=include_official):
            if source_status(source) in SKIPPED_DEFAULT_STATUSES:
                results.append(skipped_result(source, checked_at=checked_at_text))
            continue
        if limit is not None and probed_count >= limit:
            break
        probed_count += 1
        results.append(
            probe_source(
                source,
                http_client=client,
                timeout=timeout,
                checked_at=checked_at_text,
            )
        )
    return results


def probe_source(
    source: Source,
    *,
    http_client: HttpClient,
    timeout: float,
    checked_at: str,
) -> RssProbeResult:
    base = RssProbeResult(
        source_id=source.id,
        name=source.name,
        group=source.group,
        input_status=source_status(source),
        collection_enabled=source.collection_enabled,
        homepage_url=source.homepage_url,
        rss_index_url=source.rss_index_url,
        desired_feed=source.desired_feed,
        checked_at=checked_at,
        terms_check_required=source.terms_check_required or source.feed_url is None,
    )
    candidates = feed_candidates(source)
    if source.rss_index_url:
        index_candidates = rss_index_candidates(
            source,
            http_client=http_client,
            timeout=timeout,
            result=base,
        )
        base.extracted_feed_candidates = [candidate.url for candidate in index_candidates]
        candidates = [*index_candidates, *candidates]
    if source.homepage_url:
        candidates = [
            *html_autodiscovery_candidates(
                source,
                http_client=http_client,
                timeout=timeout,
                result=base,
            ),
            *candidates,
        ]
        candidates = _dedupe_candidates(candidates)
    if not candidates:
        base.failure_reason = "No feed_url or homepage_url available for discovery."
        base.recommendation = "keep_rss_candidate"
        return base

    last_failure: str | None = None
    last_status: int | None = None
    last_content_type: str | None = None
    for candidate in candidates:
        url = candidate.url
        base.tested_urls.append(url)
        try:
            response = http_client.fetch(url, timeout=timeout)
        except HTTPError as error:
            last_failure = f"HTTP {error.code}"
            last_status = error.code
            continue
        except TimeoutError:
            last_failure = "timeout"
            continue
        except URLError as error:
            last_failure = f"url_error: {error.reason}"
            continue
        except OSError as error:
            last_failure = f"network_error: {error}"
            continue

        last_status = response.status
        last_content_type = response.content_type
        parsed = parse_feed(response.body)
        if parsed.item_count > 0:
            recommendation = (
                "rss_verified_terms_pending"
                if source.terms_check_required or candidate.method != "configured_feed_url"
                else "promote_to_rss_verified"
            )
            return RssProbeResult(
                source_id=source.id,
                name=source.name,
                group=source.group,
                input_status=source_status(source),
                collection_enabled=source.collection_enabled,
                homepage_url=source.homepage_url,
                rss_index_url=source.rss_index_url,
                desired_feed=source.desired_feed,
                extracted_feed_candidates=base.extracted_feed_candidates,
                tested_urls=base.tested_urls,
                verified_feed_url=response.url,
                discovery_method=candidate.method,
                tested_url=response.url,
                http_status=response.status,
                content_type=response.content_type,
                parse_status="parsed",
                item_count=parsed.item_count,
                sample_items=parsed.sample_items,
                recommendation=recommendation,
                checked_at=checked_at,
                terms_check_required=(
                    source.terms_check_required or candidate.method != "configured_feed_url"
                ),
            )
        last_failure = parsed.failure_reason or "Feed parsed with zero items."

    return RssProbeResult(
        source_id=source.id,
        name=source.name,
        group=source.group,
        input_status=source_status(source),
        collection_enabled=source.collection_enabled,
        homepage_url=source.homepage_url,
        rss_index_url=source.rss_index_url,
        desired_feed=source.desired_feed,
        extracted_feed_candidates=base.extracted_feed_candidates,
        tested_urls=base.tested_urls,
        discovery_method="failed",
        tested_url=candidates[-1].url,
        http_status=last_status,
        content_type=last_content_type,
        parse_status="failed",
        recommendation="mark_rss_failed" if last_status in {404, 410} else "keep_rss_candidate",
        failure_reason=last_failure or "No candidate feed URL succeeded.",
        checked_at=checked_at,
        terms_check_required=source.terms_check_required or source.feed_url is None,
    )


class FeedLinkParser(HTMLParser):
    def __init__(self) -> None:
        super().__init__()
        self.feed_links: list[tuple[str, str | None]] = []
        self._last_link_index: int | None = None

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        lower_tag = tag.lower()
        if lower_tag == "a":
            values = {key.lower(): value or "" for key, value in attrs}
            href = values.get("href", "")
            if _looks_like_feed_href(href):
                self.feed_links.append((href, None))
                self._last_link_index = len(self.feed_links) - 1
            return
        if lower_tag != "link":
            return
        values = {key.lower(): value or "" for key, value in attrs}
        rel_values = {part.lower() for part in values.get("rel", "").split()}
        link_type = values.get("type", "").lower()
        href = values.get("href", "")
        if "alternate" in rel_values and link_type in {
            "application/rss+xml",
            "application/atom+xml",
        } and href:
            self.feed_links.append((href, values.get("title") or None))
            self._last_link_index = len(self.feed_links) - 1

    def handle_data(self, data: str) -> None:
        if self._last_link_index is None:
            return
        text = data.strip()
        if not text:
            return
        href, label = self.feed_links[self._last_link_index]
        if not label:
            self.feed_links[self._last_link_index] = (href, text)
        self._last_link_index = None


def html_autodiscovery_candidates(
    source: Source,
    *,
    http_client: HttpClient,
    timeout: float,
    result: RssProbeResult,
) -> list[FeedCandidate]:
    if not source.homepage_url:
        return []
    try:
        response = http_client.fetch(source.homepage_url, timeout=timeout)
    except HTTPError as error:
        result.failure_reason = f"homepage_autodiscovery_http_{error.code}"
        return []
    except TimeoutError:
        result.failure_reason = "homepage_autodiscovery_timeout"
        return []
    except URLError as error:
        result.failure_reason = f"homepage_autodiscovery_url_error: {error.reason}"
        return []
    except OSError as error:
        result.failure_reason = f"homepage_autodiscovery_network_error: {error}"
        return []

    parser = FeedLinkParser()
    try:
        parser.feed(response.body.decode("utf-8", errors="ignore"))
    except ValueError as error:
        result.failure_reason = f"homepage_autodiscovery_parse_error: {error}"
        return []
    return [
        FeedCandidate(
            url=urljoin(response.url or source.homepage_url, href),
            method="html_autodiscovery",
            label=label,
        )
        for href, label in parser.feed_links
    ]


def rss_index_candidates(
    source: Source,
    *,
    http_client: HttpClient,
    timeout: float,
    result: RssProbeResult,
) -> list[FeedCandidate]:
    if not source.rss_index_url:
        return []
    try:
        response = http_client.fetch(source.rss_index_url, timeout=timeout)
    except HTTPError as error:
        result.failure_reason = f"rss_index_http_{error.code}"
        return []
    except TimeoutError:
        result.failure_reason = "rss_index_timeout"
        return []
    except URLError as error:
        result.failure_reason = f"rss_index_url_error: {error.reason}"
        return []
    except OSError as error:
        result.failure_reason = f"rss_index_network_error: {error}"
        return []

    parser = FeedLinkParser()
    parser.feed(response.body.decode("utf-8", errors="ignore"))
    candidates = [
        FeedCandidate(
            url=urljoin(response.url or source.rss_index_url, href),
            method="rss_index_url",
            label=label,
        )
        for href, label in parser.feed_links
    ]
    return sorted(
        _dedupe_candidates(candidates),
        key=lambda candidate: _desired_feed_rank(candidate, source.desired_feed),
    )


def _looks_like_feed_href(href: str) -> bool:
    lowered = href.lower()
    return any(token in lowered for token in ["rss", "feed", "atom", ".xml"])


def _desired_feed_rank(candidate: FeedCandidate, desired_feed: str | None) -> int:
    if not desired_feed:
        return 1
    target = desired_feed.replace(" ", "").lower()
    haystack = f"{candidate.label or ''} {candidate.url}".replace(" ", "").lower()
    return 0 if target in haystack else 1


@dataclass(frozen=True)
class ParsedFeed:
    item_count: int
    sample_items: list[SampleItem]
    failure_reason: str | None = None


def parse_feed(body: bytes) -> ParsedFeed:
    try:
        root = ElementTree.fromstring(body)
    except ElementTree.ParseError as error:
        return ParsedFeed(item_count=0, sample_items=[], failure_reason=f"invalid_xml: {error}")

    root_tag = _strip_ns(root.tag).lower()
    if root_tag == "rss":
        items = list(root.findall(".//item"))
        return ParsedFeed(
            item_count=len(items),
            sample_items=[_sample_rss_item(item) for item in items[:3]],
        )
    if root_tag == "feed":
        entries = [child for child in root if _strip_ns(child.tag).lower() == "entry"]
        return ParsedFeed(
            item_count=len(entries),
            sample_items=[_sample_atom_entry(entry) for entry in entries[:3]],
        )
    return ParsedFeed(
        item_count=0,
        sample_items=[],
        failure_reason=f"unsupported_feed_root: {_strip_ns(root.tag)}",
    )


def _strip_ns(tag: str) -> str:
    return tag.rsplit("}", 1)[-1] if "}" in tag else tag


def _first_child_text(element: ElementTree.Element, *names: str) -> str | None:
    wanted = set(names)
    for child in element:
        if _strip_ns(child.tag) in wanted and child.text:
            return child.text.strip()
    return None


def _sample_rss_item(item: ElementTree.Element) -> SampleItem:
    return SampleItem(
        title=_first_child_text(item, "title"),
        url=_first_child_text(item, "link", "guid"),
        published_at=_first_child_text(item, "pubDate", "date", "published", "updated"),
    )


def _sample_atom_entry(entry: ElementTree.Element) -> SampleItem:
    link_url = None
    for child in entry:
        if _strip_ns(child.tag) != "link":
            continue
        rel = child.attrib.get("rel", "alternate")
        if rel == "alternate" and child.attrib.get("href"):
            link_url = child.attrib["href"]
            break
    return SampleItem(
        title=_first_child_text(entry, "title"),
        url=link_url or _first_child_text(entry, "id"),
        published_at=_first_child_text(entry, "published", "updated"),
    )


def write_jsonl(path: Path, results: list[RssProbeResult]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as output:
        for result in results:
            output.write(json.dumps(result.to_json_dict(), ensure_ascii=False) + "\n")


def write_markdown_report(path: Path, results: list[RssProbeResult], *, title_date: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    summary = summarize_results(results)
    lines = [
        f"# RSS Probe Report — {title_date}",
        "",
        "## Summary",
        "",
        f"- total sources checked: {summary.total_sources_checked}",
        f"- verified: {summary.verified}",
        f"- failed: {summary.failed}",
        f"- manual/subscription skipped: {summary.skipped}",
        "",
        "## Per Source",
        "",
    ]
    for result in results:
        lines.extend(
            [
                f"### {result.source_id} — {result.name}",
                "",
                f"- group: `{result.group or ''}`",
                f"- status: `{result.input_status}`",
                f"- collection_enabled: {result.collection_enabled}",
                f"- terms_check_required: {result.terms_check_required}",
                f"- homepage_url: `{result.homepage_url or ''}`",
                f"- rss_index_url: `{result.rss_index_url or ''}`",
                f"- desired_feed: `{result.desired_feed or ''}`",
                f"- extracted_feed_candidates: `{', '.join(result.extracted_feed_candidates)}`",
                f"- feed_url_candidates tried: `{', '.join(result.tested_urls)}`",
                f"- verified_feed_url: `{result.verified_feed_url or ''}`",
                f"- discovery method: `{result.discovery_method}`",
                f"- feed_url tested: `{result.tested_url or ''}`",
                f"- HTTP status: `{result.http_status or ''}`",
                f"- content-type: `{result.content_type or ''}`",
                f"- parse result: `{result.parse_status}`",
                f"- item count: {result.item_count}",
                f"- failure reason: `{result.failure_reason or ''}`",
                f"- recommendation: `{result.recommendation}`",
                "- sample titles:",
            ]
        )
        if result.sample_items:
            lines.extend(f"  - {item.title or '(untitled)'}" for item in result.sample_items)
        else:
            lines.append("  - none")
        lines.append("")
    path.write_text("\n".join(lines), encoding="utf-8")


def summarize_results(results: list[RssProbeResult]) -> ProbeSummary:
    return ProbeSummary(
        total_sources_checked=sum(1 for result in results if not result.skipped),
        verified=sum(
            1
            for result in results
            if result.recommendation
            in {"promote_to_rss_verified", "rss_verified_terms_pending"}
        ),
        failed=sum(1 for result in results if result.recommendation == "mark_rss_failed"),
        skipped=sum(1 for result in results if result.skipped),
    )


def default_report_path(today: datetime | None = None) -> Path:
    stamp = (today or datetime.now()).strftime("%Y-%m-%d")
    return paths.REPORTS_DIR / f"rss_probe_{stamp}.md"


def default_jsonl_path() -> Path:
    return paths.MANIFESTS_DIR / "rss_probe_results.jsonl"


def default_suggested_patch_path() -> Path:
    return paths.REPORTS_DIR / "rss_probe_suggested_sources_patch.yaml"


def write_suggested_patch(path: Path, results: list[RssProbeResult]) -> None:
    candidates = [
        result
        for result in results
        if result.recommendation
        in {"promote_to_rss_verified", "rss_verified_terms_pending"}
        and result.verified_feed_url
    ]
    path.parent.mkdir(parents=True, exist_ok=True)
    lines = [
        "# Suggested source registry patch from RSS probe.",
        "# Review terms and apply manually; this file is not applied automatically.",
        "",
        "sources:",
    ]
    if not candidates:
        lines.append("  []")
    for result in candidates:
        lines.extend(
            [
                f"  - id: {result.source_id}",
                "    status: rss_verified",
                f"    verified_feed_url: {result.verified_feed_url}",
                f"    terms_check_required: {str(result.terms_check_required).lower()}",
                "    collection_enabled: false",
                f"    last_probe_status: {result.parse_status}",
                f"    last_probe_at: {result.checked_at}",
                "    failure_reason: null",
            ]
        )
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


@app.callback(invoke_without_command=True)
def main(
    include_official: Annotated[
        bool,
        typer.Option("--include-official", help="Also probe official evidence sources."),
    ] = False,
    include_disabled: Annotated[
        bool,
        typer.Option("--include-disabled", help="Also probe disabled RSS sources."),
    ] = False,
    source_id: Annotated[
        str | None,
        typer.Option("--source-id", help="Probe one source id."),
    ] = None,
    limit: Annotated[
        int | None,
        typer.Option("--limit", min=1, help="Limit sources probed."),
    ] = None,
    timeout: Annotated[
        float,
        typer.Option("--timeout", min=0.5, help="Fetch timeout in seconds."),
    ] = 8.0,
    output_report: Annotated[
        Path | None,
        typer.Option("--output-report", help="Markdown report path."),
    ] = None,
    output_jsonl: Annotated[
        Path | None,
        typer.Option("--output-jsonl", help="JSONL results path."),
    ] = None,
    write_suggested_patch_file: Annotated[
        bool,
        typer.Option(
            "--write-suggested-patch",
            help="Write a manual sources.yaml patch suggestion for verified feeds.",
        ),
    ] = False,
) -> None:
    now = datetime.now(UTC)
    results = probe_sources(
        include_official=include_official,
        include_disabled=include_disabled,
        source_id=source_id,
        limit=limit,
        timeout=timeout,
        checked_at=now,
    )
    report_path = output_report or default_report_path(now)
    jsonl_path = output_jsonl or default_jsonl_path()
    write_jsonl(jsonl_path, results)
    write_markdown_report(report_path, results, title_date=now.strftime("%Y-%m-%d"))
    if write_suggested_patch_file:
        write_suggested_patch(default_suggested_patch_path(), results)
    summary = summarize_results(results)
    console.print(
        "[green]rss probe ready "
        f"(checked={summary.total_sources_checked}, verified={summary.verified}, "
        f"failed={summary.failed}, skipped={summary.skipped}).[/green]"
    )


if __name__ == "__main__":
    app()
