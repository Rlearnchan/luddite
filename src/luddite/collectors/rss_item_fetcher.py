"""Fetch enabled RSS/Atom feed items into article inbox JSONL."""

from __future__ import annotations

import hashlib
import re
from dataclasses import dataclass, field
from datetime import UTC, datetime
from email.utils import parsedate_to_datetime
from html import unescape
from html.parser import HTMLParser
from pathlib import Path
from typing import Annotated
from urllib.error import HTTPError, URLError
from xml.etree import ElementTree

import typer
from rich.console import Console

from luddite import paths
from luddite.collectors.article_history import (
    ArticleHistorySummary,
    update_article_history,
)
from luddite.collectors.rss_probe import HttpClient, UrlLibHttpClient
from luddite.collectors.source_registry import Source, load_sources
from luddite.utils.jsonl import write_jsonl
from luddite.utils.schemas import validate_with_schema
from luddite.utils.urls import canonicalize_url

app = typer.Typer(no_args_is_help=False)
console = Console()

SUMMARY_LIMIT = 500
RELATED_LINK_RE = re.compile(
    r"\b(read more|related|관련기사|관련 기사|이미지|사진|광고)\b[:：]?\s*",
    re.IGNORECASE,
)


class SummaryTextExtractor(HTMLParser):
    def __init__(self) -> None:
        super().__init__()
        self.parts: list[str] = []

    def handle_data(self, data: str) -> None:
        text = data.strip()
        if text:
            self.parts.append(text)

    @classmethod
    def to_text(cls, value: str) -> str:
        parser = cls()
        parser.feed(value)
        parser.close()
        return " ".join(parser.parts) or value


@dataclass(frozen=True)
class AllowlistEntry:
    source_id: str
    collection_enabled: bool = False
    reason: str | None = None
    fetch_limit: int | None = None


@dataclass(frozen=True)
class FeedItem:
    title: str | None
    url: str | None
    published_at: str | None
    summary: str | None


@dataclass
class SourceIngestResult:
    source_id: str
    name: str
    feed_url: str | None
    collection_enabled: bool
    status: str
    section_name: str | None = None
    fetch_limit: int | None = None
    fetch_status: str = "not_fetched"
    parse_status: str = "not_parsed"
    item_count: int = 0
    items_written: int = 0
    duplicates_skipped: int = 0
    duplicate_examples: list[str] = field(default_factory=list)
    failure_count: int = 0
    oldest_published_at: str | None = None
    newest_published_at: str | None = None
    sample_titles: list[str] = field(default_factory=list)
    skipped_reason: str | None = None
    failure_reason: str | None = None


@dataclass
class RssIngestReport:
    date: str
    sources_considered: int = 0
    sources_fetched: int = 0
    sources_enabled: int = 0
    sources_skipped: int = 0
    items_fetched: int = 0
    items_written: int = 0
    unique_urls_written: int = 0
    duplicate_url_appearances: int = 0
    duplicates_skipped: int = 0
    output_status: str = "not_written"
    output_preserved_reason: str | None = None
    failures: list[str] = field(default_factory=list)
    per_source: list[SourceIngestResult] = field(default_factory=list)
    article_history: ArticleHistorySummary | None = None


def load_allowlist(
    path: Path = paths.CONFIG_DIR / "rss_collection_allowlist.yaml",
) -> dict[str, AllowlistEntry]:
    if not path.exists():
        return {}
    entries: dict[str, AllowlistEntry] = {}
    current: dict[str, object] | None = None
    for raw_line in path.read_text(encoding="utf-8").splitlines():
        line = raw_line.split("#", 1)[0].strip()
        if not line or line == "sources:":
            continue
        if line.startswith("- "):
            if current:
                _store_allowlist_entry(entries, current)
            current = {}
            line = line[2:].strip()
            if ":" in line:
                key, value = line.split(":", 1)
                current[key.strip()] = _parse_scalar(value)
            continue
        if current is not None and ":" in line:
            key, value = line.split(":", 1)
            current[key.strip()] = _parse_scalar(value)
    if current:
        _store_allowlist_entry(entries, current)
    return entries


def _store_allowlist_entry(entries: dict[str, AllowlistEntry], item: dict[str, object]) -> None:
    source_id = item.get("source_id")
    if not source_id:
        return
    entries[str(source_id)] = AllowlistEntry(
        source_id=str(source_id),
        collection_enabled=bool(item.get("collection_enabled", False)),
        reason=str(item["reason"]) if item.get("reason") else None,
        fetch_limit=(
            int(item["fetch_limit"])
            if isinstance(item.get("fetch_limit"), int)
            else None
        ),
    )


def _parse_scalar(value: str) -> str | int | bool | None:
    value = value.strip()
    if value in {"", "null", "None"}:
        return None
    if value.lower() == "true":
        return True
    if value.lower() == "false":
        return False
    if value.isdigit():
        return int(value)
    return value.strip('"').strip("'")


def fetch_rss_articles(
    *,
    registry_path: Path = paths.SOURCE_REGISTRY_YAML,
    allowlist_path: Path = paths.CONFIG_DIR / "rss_collection_allowlist.yaml",
    output_path: Path | None = None,
    report_path: Path | None = None,
    history_path: Path | None = None,
    run_ledger_path: Path | None = None,
    http_client: HttpClient | None = None,
    source_id: str | None = None,
    limit_per_source: int = 20,
    total_limit: int | None = None,
    run_date: str | None = None,
    timeout: float = 8.0,
    collected_at: datetime | None = None,
) -> tuple[list[dict[str, object]], RssIngestReport]:
    date_text = run_date or datetime.now(UTC).strftime("%Y-%m-%d")
    output_path = output_path or paths.ARTICLE_INBOX_DIR / f"rss_{date_text}.jsonl"
    report_path = report_path or paths.REPORTS_DIR / f"rss_ingest_{date_text}.md"
    client = http_client or UrlLibHttpClient()
    collected_at_text = (collected_at or datetime.now(UTC)).isoformat()
    sources = load_sources(registry_path)
    if source_id:
        sources = [source for source in sources if source.id == source_id]
    allowlist = load_allowlist(allowlist_path)
    report = RssIngestReport(date=date_text)
    articles: list[dict[str, object]] = []
    seen_duplicate_keys: set[str] = set()
    seen_urls: set[str] = set()
    article_by_url: dict[str, dict[str, object]] = {}

    for source in sources:
        remaining_total_limit = None if total_limit is None else total_limit - len(articles)
        if remaining_total_limit is not None and remaining_total_limit <= 0:
            break
        report.sources_considered += 1
        result, source_articles = _ingest_source(
            source=source,
            allowlist=allowlist,
            client=client,
            limit_per_source=limit_per_source,
            timeout=timeout,
            collected_at=collected_at_text,
            seen_duplicate_keys=seen_duplicate_keys,
            seen_urls=seen_urls,
            article_by_url=article_by_url,
            remaining_total_limit=remaining_total_limit,
        )
        report.per_source.append(result)
        if result.collection_enabled:
            report.sources_enabled += 1
        if result.skipped_reason:
            report.sources_skipped += 1
            continue
        if result.failure_reason:
            report.failures.append(f"{source.id}: {result.failure_reason}")
        if result.fetch_status == "fetched":
            report.sources_fetched += 1
        report.items_fetched += result.item_count
        report.items_written += result.items_written
        report.duplicates_skipped += result.duplicates_skipped
        report.duplicate_url_appearances += result.duplicates_skipped
        articles.extend(source_articles)
    report.unique_urls_written = len(
        {str(article.get("source_url_canonical")) for article in articles}
    )
    if not articles and report.failures and output_path.exists():
        report.output_status = "preserved_existing"
        report.output_preserved_reason = "zero_articles_with_fetch_failures"
    else:
        write_jsonl(output_path, articles)
        report.output_status = "written"
    report.items_written = len(articles)
    if history_path and articles:
        report.article_history = update_article_history(
            articles,
            run_date=date_text,
            collected_at=collected_at_text,
            history_path=history_path,
            run_ledger_path=run_ledger_path or paths.JIBI_ARTICLE_RUNS_JSONL,
        )
    write_ingest_report(report_path, report, output_path)
    return articles, report


def _ingest_source(
    *,
    source: Source,
    allowlist: dict[str, AllowlistEntry],
    client: HttpClient,
    limit_per_source: int,
    timeout: float,
    collected_at: str,
    seen_duplicate_keys: set[str],
    seen_urls: set[str],
    article_by_url: dict[str, dict[str, object]],
    remaining_total_limit: int | None,
) -> tuple[SourceIngestResult, list[dict[str, object]]]:
    status = _source_status(source)
    allowlist_entry = allowlist.get(source.id)
    collection_enabled = bool(allowlist_entry and allowlist_entry.collection_enabled)
    feed_url = source.verified_feed_url
    result = SourceIngestResult(
        source_id=source.id,
        name=source.name,
        feed_url=feed_url,
        collection_enabled=collection_enabled,
        status=status,
        section_name=source.section_name or source.desired_feed,
        fetch_limit=allowlist_entry.fetch_limit if allowlist_entry else None,
    )
    if status in {"manual", "subscription_manual", "disabled"} or source.type in {
        "manual",
        "subscription_manual",
    }:
        result.skipped_reason = f"skipped_status:{status}"
        return result, []
    if not collection_enabled:
        result.skipped_reason = "collection_enabled_false"
        return result, []
    if not feed_url:
        result.skipped_reason = "missing_verified_feed_url"
        return result, []

    try:
        response = client.fetch(feed_url, timeout=timeout)
    except HTTPError as error:
        result.fetch_status = f"http_{error.code}"
        result.failure_reason = f"HTTP {error.code}"
        result.failure_count = 1
        return result, []
    except TimeoutError:
        result.fetch_status = "timeout"
        result.failure_reason = "timeout"
        result.failure_count = 1
        return result, []
    except URLError as error:
        result.fetch_status = "url_error"
        result.failure_reason = f"url_error: {error.reason}"
        result.failure_count = 1
        return result, []
    except OSError as error:
        result.fetch_status = "network_error"
        result.failure_reason = f"network_error: {error}"
        result.failure_count = 1
        return result, []

    result.fetch_status = "fetched"
    items, failure = parse_feed_items(response.body)
    if failure:
        result.parse_status = "failed"
        result.failure_reason = failure
        result.failure_count = 1
        return result, []
    result.parse_status = "parsed"
    result.item_count = len(items)
    result.oldest_published_at, result.newest_published_at = _published_bounds(items)
    result.sample_titles = [unescape(str(item.title).strip()) for item in items if item.title][:3]
    articles: list[dict[str, object]] = []
    write_limit = (
        allowlist_entry.fetch_limit
        if allowlist_entry and allowlist_entry.fetch_limit
        else limit_per_source
    )
    if remaining_total_limit is not None:
        write_limit = min(write_limit, remaining_total_limit)
    for item in items:
        if len(articles) >= write_limit:
            break
        article = feed_item_to_article(source, item, collected_at=collected_at)
        if not article:
            continue
        duplicate_key = str(article["duplicate_key"])
        canonical_url = str(article["source_url_canonical"])
        if duplicate_key in seen_duplicate_keys or canonical_url in seen_urls:
            existing = article_by_url.get(canonical_url)
            if existing:
                _merge_duplicate_source_metadata(existing, source)
            result.duplicates_skipped += 1
            if len(result.duplicate_examples) < 3:
                result.duplicate_examples.append(f"{article['title']} — {canonical_url}")
            continue
        errors = validate_with_schema(article, "article_schema.json")
        if errors:
            result.failure_reason = f"schema errors: {'; '.join(errors)}"
            result.failure_count += 1
            continue
        seen_duplicate_keys.add(duplicate_key)
        seen_urls.add(canonical_url)
        article_by_url[canonical_url] = article
        articles.append(article)
    result.items_written = len(articles)
    return result, articles


def parse_feed_items(body: bytes) -> tuple[list[FeedItem], str | None]:
    try:
        root = ElementTree.fromstring(body)
    except ElementTree.ParseError as error:
        return [], f"invalid_xml: {error}"
    root_tag = _strip_ns(root.tag).lower()
    if root_tag == "rss":
        return [_rss_item_to_feed_item(item) for item in root.findall(".//item")], None
    if root_tag == "feed":
        entries = [child for child in root if _strip_ns(child.tag).lower() == "entry"]
        return [_atom_entry_to_feed_item(entry) for entry in entries], None
    return [], f"unsupported_feed_root: {_strip_ns(root.tag)}"


def feed_item_to_article(
    source: Source,
    item: FeedItem,
    *,
    collected_at: str,
) -> dict[str, object] | None:
    title = unescape(item.title or "").strip()
    url = canonicalize_url(item.url or "")
    if not title or not url:
        return None
    source_url_canonical = canonicalize_url(url)
    duplicate_key = stable_duplicate_key(source_url_canonical)
    return {
        "article_id": f"article_{duplicate_key}",
        "title": title,
        "url": source_url_canonical,
        "source": source.name,
        "source_id": source.id,
        "source_url_canonical": source_url_canonical,
        "duplicate_key": duplicate_key,
        "published_at": item.published_at,
        "collected_at": collected_at,
        "language": None,
        "region": source.region,
        "raw_summary": truncate_summary(item.summary),
        "collector": "rss",
        "tags": ["rss", source.group or "", source.role or ""],
        "source_count": 1,
        "source_sections": [
            source.section_name or source.desired_feed or source.category_hint or source.id
        ],
        "supporting_source_ids": [],
    }


def _merge_duplicate_source_metadata(article: dict[str, object], source: Source) -> None:
    primary_source_id = str(article.get("source_id") or "")
    source_ids = [primary_source_id]
    supporting_ids = [
        str(value)
        for value in article.get("supporting_source_ids", [])
        if str(value).strip()
    ]
    if source.id != primary_source_id and source.id not in supporting_ids:
        supporting_ids.append(source.id)
    source_ids.extend(supporting_ids)
    sections = [
        str(value)
        for value in article.get("source_sections", [])
        if str(value).strip()
    ]
    section = source.section_name or source.desired_feed or source.category_hint or source.id
    if section and section not in sections:
        sections.append(section)
    article["supporting_source_ids"] = supporting_ids
    article["source_sections"] = sections
    article["source_count"] = len(dict.fromkeys(source_ids))


def stable_duplicate_key(url: str) -> str:
    digest = hashlib.sha1(url.encode("utf-8")).hexdigest()[:12]
    return f"rss_{digest}"


def _source_status(source: Source) -> str:
    return source.status or source.type


def truncate_summary(summary: str | None, *, limit: int = SUMMARY_LIMIT) -> str | None:
    if not summary:
        return None
    text = SummaryTextExtractor.to_text(unescape(summary))
    text = unescape(text)
    text = RELATED_LINK_RE.sub("", text)
    text = " ".join(text.split()).strip()
    if not text:
        return None
    if len(text) <= limit:
        return text
    return text[: limit - 1].rstrip() + "…"


def _published_bounds(items: list[FeedItem]) -> tuple[str | None, str | None]:
    parsed_values = [
        (parsed, raw)
        for raw in (str(item.published_at).strip() for item in items if item.published_at)
        if (parsed := _parse_published_at(raw)) is not None
    ]
    if not parsed_values:
        return None, None
    parsed_values.sort(key=lambda item: item[0])
    return parsed_values[0][1], parsed_values[-1][1]


def _parse_published_at(value: str) -> datetime | None:
    try:
        parsed = parsedate_to_datetime(value)
        if parsed.tzinfo is None:
            return parsed.replace(tzinfo=UTC)
        return parsed
    except (TypeError, ValueError):
        pass
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
        if parsed.tzinfo is None:
            return parsed.replace(tzinfo=UTC)
        return parsed
    except ValueError:
        return None


def _strip_ns(tag: str) -> str:
    return tag.rsplit("}", 1)[-1] if "}" in tag else tag


def _first_child_text(element: ElementTree.Element, *names: str) -> str | None:
    wanted = set(names)
    for child in element:
        if _strip_ns(child.tag) in wanted and child.text:
            return child.text.strip()
    return None


def _rss_item_to_feed_item(item: ElementTree.Element) -> FeedItem:
    return FeedItem(
        title=_first_child_text(item, "title"),
        url=_first_child_text(item, "link", "guid"),
        published_at=_first_child_text(item, "pubDate", "date", "published", "updated"),
        summary=_first_child_text(item, "description", "summary"),
    )


def _atom_entry_to_feed_item(entry: ElementTree.Element) -> FeedItem:
    link_url = None
    for child in entry:
        if _strip_ns(child.tag) != "link":
            continue
        rel = child.attrib.get("rel", "alternate")
        if rel == "alternate" and child.attrib.get("href"):
            link_url = child.attrib["href"]
            break
    return FeedItem(
        title=_first_child_text(entry, "title"),
        url=link_url or _first_child_text(entry, "id"),
        published_at=_first_child_text(entry, "published", "updated"),
        summary=_first_child_text(entry, "summary", "content"),
    )


def write_ingest_report(path: Path, report: RssIngestReport, output_path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    lines = [
        f"# RSS Ingest Report — {report.date}",
        "",
        "## Summary",
        "",
        f"- sources considered: {report.sources_considered}",
        f"- sources enabled: {report.sources_enabled}",
        f"- sources fetched: {report.sources_fetched}",
        f"- sources skipped: {report.sources_skipped}",
        f"- raw feed items: {report.items_fetched}",
        f"- unique URLs written: {report.unique_urls_written or report.items_written}",
        f"- items written: {report.items_written}",
        f"- duplicate URL appearances: {report.duplicate_url_appearances}",
        f"- duplicates skipped: {report.duplicates_skipped}",
        f"- failures: {len(report.failures)}",
        f"- output status: `{report.output_status}`",
        f"- output preserved reason: `{report.output_preserved_reason or ''}`",
        f"- output: `{output_path}`",
        "",
    ]
    lines.extend(_article_history_report_lines(report.article_history))
    lines.extend(["## Per Source", ""])
    for result in report.per_source:
        lines.extend(
            [
                f"### {result.source_id} — {result.name}",
                "",
                f"- feed_url: `{result.feed_url or ''}`",
                f"- section_name: `{result.section_name or ''}`",
                f"- fetch_limit: {result.fetch_limit or ''}",
                f"- collection_enabled: {result.collection_enabled}",
                f"- status: `{result.status}`",
                f"- fetch_status: `{result.fetch_status}`",
                f"- parse_status: `{result.parse_status}`",
                f"- item_count: {result.item_count}",
                f"- items_written: {result.items_written}",
                f"- duplicate_skipped: {result.duplicates_skipped}",
                "- duplicate_examples:",
                *[f"  - {example}" for example in result.duplicate_examples],
                f"- failure_count: {result.failure_count}",
                f"- oldest_published_at: `{result.oldest_published_at or ''}`",
                f"- newest_published_at: `{result.newest_published_at or ''}`",
                "- sample_titles:",
                *[f"  - {title}" for title in result.sample_titles],
                f"- skipped_reason: `{result.skipped_reason or ''}`",
                f"- failure_reason: `{result.failure_reason or ''}`",
                "",
            ]
        )
    lines.extend(["## Failures", ""])
    if report.failures:
        lines.extend(f"- {failure}" for failure in report.failures)
    else:
        lines.append("- none")
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def _article_history_report_lines(history: ArticleHistorySummary | None) -> list[str]:
    if not history:
        return []
    lines = [
        "## Article History",
        "",
        f"- run_id: `{history.run_id}`",
        f"- previous_run_id: `{history.previous_run_id or ''}`",
        f"- current URLs: {history.current_urls}",
        f"- known before: {history.known_before}",
        f"- known after: {history.known_after}",
        f"- new to history: {history.new_to_history}",
        f"- returning known: {history.returning_known}",
        f"- previous run URLs: {history.previous_run_urls}",
        f"- new since previous run: {history.new_since_previous_run}",
        f"- dropped since previous run: {history.dropped_since_previous_run}",
        f"- percent new since previous run: {history.percent_new_since_previous_run:.2f}%",
        f"- percent dropped since previous run: {history.percent_dropped_since_previous_run:.2f}%",
        f"- churn label: `{history.churn_label}`",
        f"- history ledger: `{history.history_path}`",
        f"- run ledger: `{history.run_ledger_path}`",
        "",
        "### Cadence Recommendation",
        "",
        *_cadence_recommendation_lines(history),
        "",
        "### Source Delta",
        "",
        "| source | current | new_to_history | new_since_previous | dropped_since_previous |",
        "| --- | ---: | ---: | ---: | ---: |",
    ]
    lines.extend(
        (
            f"| {delta.source} | {delta.current_urls} | {delta.new_to_history} | "
            f"{delta.new_since_previous_run} | {delta.dropped_since_previous_run} |"
        )
        for delta in history.per_source
    )
    lines.extend(["", "### New Since Previous Run Examples", ""])
    if history.new_examples:
        lines.extend(
            (
                f"- {example['source']} | {example['published_at']} | "
                f"[{example['title']}]({example['url']})"
            )
            for example in history.new_examples
        )
    else:
        lines.append("- none")
    lines.extend(["", "### Dropped Since Previous Run Examples", ""])
    if history.dropped_examples:
        lines.extend(
            (
                f"- {example['source']} | {example['published_at']} | "
                f"[{example['title']}]({example['url']})"
            )
            for example in history.dropped_examples
        )
    else:
        lines.append("- none")
    lines.append("")
    return lines


def _cadence_recommendation_lines(history: ArticleHistorySummary) -> list[str]:
    if history.churn_label == "high_churn":
        return [
            "- recommendation: optional_evening_rss_observation_only",
            "- reason: RSS moving window churn is high; inspect new/dropped "
            "examples before changing cadence",
            "- guardrail: do not replace the visible board twice after reviewers start writing",
        ]
    if history.churn_label == "normal_churn":
        return [
            "- recommendation: one_visible_board_per_day_plus_optional_rss_check",
            "- reason: RSS churn is noticeable but not enough to justify a "
            "second visible board by itself",
            "- guardrail: keep newness report-only; do not use it as a scoring boost yet",
        ]
    return [
        "- recommendation: one_visible_board_per_day_is_enough",
        "- reason: RSS churn is low versus the previous run",
        "- guardrail: use evening runs for observation only, not board replacement",
    ]


@app.callback(invoke_without_command=True)
def main(
    source_id: Annotated[
        str | None,
        typer.Option("--source-id", help="Fetch one enabled RSS source id."),
    ] = None,
    limit_per_source: Annotated[
        int,
        typer.Option("--limit-per-source", min=1, help="Max items per source."),
    ] = 20,
    total_limit: Annotated[
        int | None,
        typer.Option("--total-limit", min=1, help="Max items across all sources."),
    ] = None,
    date: Annotated[
        str | None,
        typer.Option("--date", help="Output date stamp YYYY-MM-DD."),
    ] = None,
    output: Annotated[
        Path | None,
        typer.Option("--output", help="Output article inbox JSONL path."),
    ] = None,
    report: Annotated[
        Path | None,
        typer.Option("--report", help="Markdown ingest report path."),
    ] = None,
    history_output: Annotated[
        Path,
        typer.Option("--history-output", help="Durable URL-level article history JSONL."),
    ] = paths.JIBI_ARTICLE_HISTORY_JSONL,
    run_ledger_output: Annotated[
        Path,
        typer.Option("--run-ledger-output", help="Append-only RSS run snapshot JSONL."),
    ] = paths.JIBI_ARTICLE_RUNS_JSONL,
    skip_history: Annotated[
        bool,
        typer.Option("--skip-history", help="Do not update article history ledgers."),
    ] = False,
    timeout: Annotated[
        float,
        typer.Option("--timeout", min=0.5, help="Fetch timeout seconds."),
    ] = 8.0,
) -> None:
    articles, ingest_report = fetch_rss_articles(
        source_id=source_id,
        limit_per_source=limit_per_source,
        total_limit=total_limit,
        run_date=date,
        output_path=output,
        report_path=report,
        history_path=None if skip_history else history_output,
        run_ledger_path=None if skip_history else run_ledger_output,
        timeout=timeout,
    )
    history_text = ""
    if ingest_report.article_history:
        history = ingest_report.article_history
        history_text = (
            f", new_since_previous={history.new_since_previous_run}, "
            f"dropped_since_previous={history.dropped_since_previous_run}, "
            f"known={history.known_after}"
        )
    console.print(
        "[green]rss articles fetched "
        f"(sources={ingest_report.sources_fetched}, articles={len(articles)}, "
        f"skipped={ingest_report.sources_skipped}{history_text}).[/green]"
    )


if __name__ == "__main__":
    app()
