"""Article body fetch/cache layer for Jibi report-only evidence building."""

from __future__ import annotations

import hashlib
import json
import re
from collections import Counter
from dataclasses import asdict, dataclass, field
from datetime import UTC, datetime
from pathlib import Path
from typing import Annotated, Any, Protocol

import typer
from rich.console import Console

from luddite import paths
from luddite.agents.jibi.content_enrichment import (
    ArticleHttpClient,
    UrlLibArticleHttpClient,
    _ArticleTextParser,
    _clean_text,
    _decode_html,
    _dedupe_paragraphs,
    _next_data_texts,
    _parse_target_paragraphs,
)
from luddite.agents.jibi.llm_client import (
    OpenAIResponsesClient,
    jibi_llm_model,
    parse_json_object,
)
from luddite.collectors.rss_probe import HttpResponse
from luddite.utils.jsonl import read_jsonl, write_jsonl
from luddite.utils.urls import canonicalize_url

app = typer.Typer(no_args_is_help=False)
console = Console()

ARTICLE_CACHE_JSONL = paths.DATA_DIR / "jibi" / "article_cache" / "article_bodies.jsonl"
FETCH_STATUSES = {
    "ok",
    "blocked",
    "paywall",
    "no_body",
    "unsupported",
    "error",
}
PAYWALL_MARKERS = {
    "subscribe",
    "paywall",
    "구독",
    "프리미엄",
    "로그인 후",
    "회원 전용",
}
SOURCE_TARGET_IDS = {
    "npr": "storytext",
    "infomax": "article-view-content-div",
    "hankyung": "articletxt",
}


class LlmJsonClient(Protocol):
    model: str

    def json_response(
        self,
        prompt: str,
        *,
        timeout_seconds: int = 120,
        max_output_tokens: int = 1200,
    ) -> tuple[str, dict[str, Any]]:
        """Return JSON text plus the raw API payload."""


@dataclass
class ArticleTarget:
    url: str
    title: str = ""
    source: str = "unknown"
    published_at: str = ""
    summary: str = ""
    candidate_id: str = ""
    story_bundle_id: str = ""
    source_role: str = ""

    @property
    def canonical_url(self) -> str:
        return canonicalize_url(self.url)


@dataclass
class ArticleBodyRecord:
    url: str
    canonical_url: str
    source: str
    fetch_status: str
    http_status: int | None = None
    title: str = ""
    published_at: str = ""
    body_text: str = ""
    body_text_hash: str = ""
    body_char_count: int = 0
    body_word_count: int = 0
    extracted_at: str = ""
    extractor: str = ""
    warnings: list[str] = field(default_factory=list)
    candidate_ids: list[str] = field(default_factory=list)
    story_bundle_ids: list[str] = field(default_factory=list)
    cache_status: str = "miss"
    llm_summary_status: str = "not_requested"
    llm_summary_model: str = ""
    llm_translated_title_ko: str = ""
    llm_summary_ko: str = ""
    llm_known_limitations: list[str] = field(default_factory=list)

    def to_json_dict(self) -> dict[str, Any]:
        return asdict(self)

    def to_report_dict(self) -> dict[str, Any]:
        payload = asdict(self)
        payload.pop("body_text", "")
        payload["body_preview_available"] = bool(self.body_text)
        return payload


def _source_key(source: str, url: str) -> str:
    return f"{source} {url}".lower()


def _extractor_for(source: str, url: str) -> tuple[str, str | None]:
    key = _source_key(source, url)
    if url.lower().endswith(".pdf") or "application/pdf" in key:
        return "pdf_unsupported", None
    if "yna.co.kr" in key or "연합뉴스" in key or "yonhap" in key:
        return "yna_generic_article_p", None
    if "theguardian.com" in key or "guardian" in key:
        return "guardian_generic_article_p", None
    if "theconversation.com" in key or "conversation" in key:
        return "conversation_article_p", None
    if "bbc" in key:
        return "bbc_next_data_text", None
    if "bok.or.kr" in key or "한국은행" in key:
        return "bok_generic_article_p", None
    if "korea.kr" in key or "정책브리핑" in key:
        return "policy_briefing_article_p", None
    if "npr" in key:
        return "npr_storytext_p", SOURCE_TARGET_IDS["npr"]
    if "infomax" in key or "연합인포맥스" in key:
        return "infomax_article_view_content", SOURCE_TARGET_IDS["infomax"]
    if "hankyung" in key or "한국경제" in key:
        return "hankyung_articletxt", SOURCE_TARGET_IDS["hankyung"]
    return "generic_article_p", None


def _body_hash(body_text: str) -> str:
    if not body_text:
        return ""
    return hashlib.sha256(body_text.encode("utf-8")).hexdigest()


def _word_count(body_text: str) -> int:
    return len(re.findall(r"[\w가-힣]+", body_text))


def _paragraph_body(paragraphs: list[str]) -> str:
    return _clean_text("\n".join(_dedupe_paragraphs(paragraphs)))


def _json_ld_article_bodies(html_text: str) -> list[str]:
    texts: list[str] = []
    script_pattern = re.compile(
        r"<script[^>]+type=[\"']application/ld\+json[\"'][^>]*>(.*?)</script>",
        flags=re.I | re.S,
    )
    for match in script_pattern.finditer(html_text):
        raw = match.group(1).strip()
        try:
            payload = json.loads(raw)
        except json.JSONDecodeError:
            continue

        def walk(value: Any) -> None:
            if isinstance(value, dict):
                article_body = value.get("articleBody")
                if isinstance(article_body, str) and len(article_body) >= 120:
                    texts.append(article_body)
                for child in value.values():
                    walk(child)
            elif isinstance(value, list):
                for child in value:
                    walk(child)

        walk(payload)
    return [_clean_text(item) for item in texts if _clean_text(item)]


def extract_article_body(
    *,
    response: HttpResponse,
    source: str,
    url: str,
) -> tuple[str, str, str, str, list[str]]:
    """Return extractor, title, meta description, body text, warnings."""
    extractor, target_id = _extractor_for(source, url)
    warnings: list[str] = []
    content_type = response.content_type or ""
    if extractor == "pdf_unsupported" or "application/pdf" in content_type.lower():
        return "pdf_unsupported", "", "", "", ["pdf_body_extraction_not_implemented"]

    html_text = _decode_html(response)
    title, meta_description, paragraphs = _parse_target_paragraphs(
        html_text,
        target_id=target_id,
    )
    if extractor == "bbc_next_data_text":
        parser = _ArticleTextParser()
        parser.feed(html_text)
        paragraphs = _next_data_texts(parser.next_data) or paragraphs
        title = parser.title or title
        meta_description = parser.meta_description or meta_description
    else:
        json_ld_bodies = _json_ld_article_bodies(html_text)
        if json_ld_bodies and len(" ".join(json_ld_bodies)) > len(" ".join(paragraphs)):
            paragraphs = json_ld_bodies
            warnings.append("used_json_ld_articleBody")
    body_text = _paragraph_body(paragraphs)
    return extractor, title, meta_description, body_text, warnings


def _status_for_body(
    *,
    response: HttpResponse,
    body_text: str,
    warnings: list[str],
) -> tuple[str, list[str]]:
    if response.status in {401, 403, 451}:
        return "blocked", [*warnings, f"http_{response.status}"]
    if response.status == 402:
        return "paywall", [*warnings, "http_402"]
    if response.status is not None and response.status >= 400:
        return "error", [*warnings, f"http_{response.status}"]
    lowered = body_text.lower()
    if any(marker.lower() in lowered for marker in PAYWALL_MARKERS) and len(body_text) < 800:
        return "paywall", [*warnings, "paywall_or_teaser_detected"]
    if "pdf_body_extraction_not_implemented" in warnings:
        return "unsupported", warnings
    if len(body_text) < 280:
        return "no_body", [*warnings, "body_below_minimum_length"]
    return "ok", warnings


def fetch_article_body(
    target: ArticleTarget,
    *,
    http_client: ArticleHttpClient | None = None,
    timeout: float = 12,
    extracted_at: str | None = None,
) -> ArticleBodyRecord:
    url = target.url
    canonical_url = target.canonical_url
    record = ArticleBodyRecord(
        url=url,
        canonical_url=canonical_url,
        source=target.source or "unknown",
        fetch_status="error",
        title=target.title,
        published_at=target.published_at,
        extracted_at=extracted_at or datetime.now(UTC).isoformat(),
        candidate_ids=_dedupe_strings([target.candidate_id]),
        story_bundle_ids=_dedupe_strings([target.story_bundle_id]),
    )
    if not canonical_url:
        record.fetch_status = "error"
        record.warnings = ["missing_url"]
        return record

    client = http_client or UrlLibArticleHttpClient()
    try:
        response = client.fetch(url, timeout=timeout)
    except Exception as exc:
        record.fetch_status = "error"
        record.warnings = [type(exc).__name__]
        record.extractor = _extractor_for(target.source, url)[0]
        return record

    record.url = response.url or url
    record.canonical_url = canonicalize_url(response.url or canonical_url)
    record.http_status = response.status
    extractor, title, _meta_description, body_text, warnings = extract_article_body(
        response=response,
        source=target.source,
        url=record.url,
    )
    status, warnings = _status_for_body(
        response=response,
        body_text=body_text,
        warnings=warnings,
    )
    record.fetch_status = status
    record.extractor = extractor
    record.title = title or target.title
    record.body_text = body_text
    record.body_text_hash = _body_hash(body_text)
    record.body_char_count = len(body_text)
    record.body_word_count = _word_count(body_text)
    record.warnings = warnings
    return record


def _dedupe_strings(values: list[str]) -> list[str]:
    seen: set[str] = set()
    deduped: list[str] = []
    for value in values:
        text = str(value or "").strip()
        if not text or text in seen:
            continue
        seen.add(text)
        deduped.append(text)
    return deduped


def _split_links(value: Any) -> list[str]:
    if isinstance(value, list):
        return [str(item) for item in value if str(item).strip()]
    if not value:
        return []
    text = str(value)
    return [
        part.strip()
        for part in re.split(r"[\n,]", text)
        if part.strip().startswith(("http://", "https://"))
    ]


def _load_metadata_rows(path: Path) -> list[dict[str, Any]]:
    if not path.exists():
        return []
    payload = json.loads(path.read_text(encoding="utf-8"))
    if isinstance(payload, dict) and isinstance(payload.get("rows"), list):
        return [row for row in payload["rows"] if isinstance(row, dict)]
    if isinstance(payload, list):
        return [row for row in payload if isinstance(row, dict)]
    return []


def _score_value(candidate: dict[str, Any]) -> float:
    scores = candidate.get("scores") if isinstance(candidate.get("scores"), dict) else {}
    return float(candidate.get("board_score") or scores.get("total_score") or 0)


def collect_article_targets(
    *,
    metadata_path: Path | None = None,
    scored_candidates_path: Path | None = None,
    include_scored_candidates: bool = False,
    max_items: int = 40,
) -> list[ArticleTarget]:
    scored_candidates = (
        read_jsonl(scored_candidates_path)
        if scored_candidates_path and scored_candidates_path.exists()
        else []
    )
    candidates_by_id = {
        str(item.get("candidate_id") or ""): item
        for item in scored_candidates
        if item.get("candidate_id")
    }
    targets: list[ArticleTarget] = []
    for row in _load_metadata_rows(metadata_path) if metadata_path else []:
        candidate_id = str(row.get("primary_candidate_id") or "")
        candidate = candidates_by_id.get(candidate_id, {})
        urls = [
            str(row.get("main_link") or candidate.get("seed_url") or ""),
            *_split_links(row.get("sub_links")),
        ]
        for index, url in enumerate(urls):
            if not url:
                continue
            source_role = "main" if index == 0 else "sub"
            targets.append(
                ArticleTarget(
                    url=url,
                    title=str(row.get("title") or candidate.get("title") or ""),
                    source=str(row.get("source") or candidate.get("source") or "unknown"),
                    published_at=str(candidate.get("published_at") or row.get("run_date") or ""),
                    summary=str(
                        candidate.get("summary")
                        or candidate.get("raw_summary")
                        or row.get("description")
                        or row.get("so_what")
                        or ""
                    ),
                    candidate_id=candidate_id,
                    story_bundle_id=str(row.get("story_bundle_id") or row.get("ID") or ""),
                    source_role=source_role,
                )
            )
    if include_scored_candidates:
        for candidate in sorted(scored_candidates, key=_score_value, reverse=True):
            url = str(candidate.get("seed_url") or candidate.get("source_url_canonical") or "")
            if not url:
                continue
            targets.append(
                ArticleTarget(
                    url=url,
                    title=str(candidate.get("title") or ""),
                    source=str(candidate.get("source") or candidate.get("source_id") or "unknown"),
                    published_at=str(candidate.get("published_at") or ""),
                    summary=str(candidate.get("summary") or candidate.get("raw_summary") or ""),
                    candidate_id=str(candidate.get("candidate_id") or ""),
                    story_bundle_id=str(candidate.get("near_duplicate_group_id") or ""),
                    source_role="candidate_pool",
                )
            )
    deduped: list[ArticleTarget] = []
    seen_urls: set[str] = set()
    for target in targets:
        key = target.canonical_url
        if not key or key in seen_urls:
            continue
        seen_urls.add(key)
        deduped.append(target)
        if max_items > 0 and len(deduped) >= max_items:
            break
    return deduped


def load_article_cache(path: Path = ARTICLE_CACHE_JSONL) -> dict[str, ArticleBodyRecord]:
    if not path.exists():
        return {}
    cache: dict[str, ArticleBodyRecord] = {}
    for row in read_jsonl(path):
        canonical_url = str(row.get("canonical_url") or "")
        if not canonical_url:
            continue
        known = {field.name for field in ArticleBodyRecord.__dataclass_fields__.values()}
        payload = {key: value for key, value in row.items() if key in known}
        cache[canonical_url] = ArticleBodyRecord(**payload)
    return cache


def _merge_target_context(record: ArticleBodyRecord, target: ArticleTarget) -> ArticleBodyRecord:
    record.candidate_ids = _dedupe_strings([*record.candidate_ids, target.candidate_id])
    record.story_bundle_ids = _dedupe_strings([*record.story_bundle_ids, target.story_bundle_id])
    if not record.title and target.title:
        record.title = target.title
    if not record.published_at and target.published_at:
        record.published_at = target.published_at
    if not record.source or record.source == "unknown":
        record.source = target.source
    return record


def summarize_metadata_with_llm(
    target: ArticleTarget,
    *,
    llm_client: LlmJsonClient,
    timeout_seconds: int = 120,
) -> dict[str, Any]:
    prompt = f"""
You are helping Jibi understand a news candidate for downstream editorial triage.
The article body could not be fetched. Use only the title, source, and RSS summary below.
Return a compact Korean JSON object with:
translated_title_ko, summary_ko, likely_editorial_value, known_limitations.
Do not invent facts, URLs, quotes, or numbers not present in the metadata.

Source: {target.source}
Title: {target.title}
RSS summary: {target.summary}
URL: {target.url}
""".strip()
    text, _payload = llm_client.json_response(
        prompt,
        timeout_seconds=timeout_seconds,
        max_output_tokens=900,
    )
    return parse_json_object(text)


def _attach_llm_summary(
    record: ArticleBodyRecord,
    target: ArticleTarget,
    *,
    llm_client: LlmJsonClient,
    timeout_seconds: int,
) -> ArticleBodyRecord:
    try:
        payload = summarize_metadata_with_llm(
            target,
            llm_client=llm_client,
            timeout_seconds=timeout_seconds,
        )
    except Exception as exc:
        record.llm_summary_status = "error"
        record.llm_known_limitations = [type(exc).__name__]
        record.llm_summary_model = getattr(llm_client, "model", "")
        return record
    record.llm_summary_status = "ok"
    record.llm_summary_model = getattr(llm_client, "model", "")
    record.llm_translated_title_ko = str(payload.get("translated_title_ko") or "")
    record.llm_summary_ko = str(payload.get("summary_ko") or "")
    limitations = payload.get("known_limitations") or []
    if isinstance(limitations, str):
        limitations = [limitations]
    record.llm_known_limitations = [str(item) for item in limitations]
    return record


def fetch_article_bodies(
    *,
    targets: list[ArticleTarget],
    output_jsonl: Path = ARTICLE_CACHE_JSONL,
    http_client: ArticleHttpClient | None = None,
    timeout: float = 12,
    refresh: bool = False,
    llm_summary_fallback: bool = False,
    llm_max_items: int = 10,
    llm_model: str | None = None,
    llm_client: LlmJsonClient | None = None,
    llm_timeout_seconds: int = 120,
) -> list[ArticleBodyRecord]:
    cache = load_article_cache(output_jsonl)
    fetched_at = datetime.now(UTC).isoformat()
    records_by_url: dict[str, ArticleBodyRecord] = dict(cache)
    output_records: list[ArticleBodyRecord] = []
    llm_used = 0
    active_llm_client = llm_client
    for target in targets:
        cached = cache.get(target.canonical_url)
        if cached and not refresh:
            record = _merge_target_context(cached, target)
            record.cache_status = "hit"
        else:
            record = fetch_article_body(
                target,
                http_client=http_client,
                timeout=timeout,
                extracted_at=fetched_at,
            )
        if (
            llm_summary_fallback
            and record.fetch_status != "ok"
            and record.llm_summary_status != "ok"
            and (llm_max_items <= 0 or llm_used < llm_max_items)
        ):
            if active_llm_client is None:
                active_llm_client = OpenAIResponsesClient(model=jibi_llm_model(llm_model))
            record = _attach_llm_summary(
                record,
                target,
                llm_client=active_llm_client,
                timeout_seconds=llm_timeout_seconds,
            )
            llm_used += 1
        records_by_url[record.canonical_url] = record
        output_records.append(record)
    write_jsonl(
        output_jsonl,
        [records_by_url[key].to_json_dict() for key in sorted(records_by_url)],
    )
    return output_records


def _table_cell(value: object, *, limit: int = 140) -> str:
    text = _clean_text(str(value or ""))
    if len(text) > limit:
        text = text[: limit - 3].rstrip() + "..."
    return text.replace("|", "\\|")


def write_article_body_fetch_report(
    *,
    records: list[ArticleBodyRecord],
    report_md: Path,
    report_json: Path,
    run_date: str,
    output_jsonl: Path,
) -> None:
    status_counts = Counter(record.fetch_status for record in records)
    cache_counts = Counter(record.cache_status for record in records)
    llm_counts = Counter(record.llm_summary_status for record in records)
    source_counts: dict[str, Counter[str]] = {}
    for record in records:
        source_counts.setdefault(record.source, Counter())[record.fetch_status] += 1
    lines = [
        f"# Jibi Article Body Fetch — {run_date}",
        "",
        "## Summary",
        "",
        f"- target_count: {len(records)}",
        f"- cache_path: `{output_jsonl}`",
    ]
    for status in ["ok", "blocked", "paywall", "no_body", "unsupported", "error"]:
        lines.append(f"- fetch_{status}: {status_counts.get(status, 0)}")
    lines.extend(
        [
            f"- cache_hits: {cache_counts.get('hit', 0)}",
            f"- cache_misses: {cache_counts.get('miss', 0)}",
            f"- llm_summary_ok: {llm_counts.get('ok', 0)}",
            f"- llm_summary_error: {llm_counts.get('error', 0)}",
            "",
            "## Source Status",
            "",
            "| source | total | ok | blocked | paywall | no_body | unsupported | error |",
            "| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |",
        ]
    )
    for source, counts in sorted(source_counts.items()):
        lines.append(
            "| "
            + " | ".join(
                [
                    _table_cell(source),
                    str(sum(counts.values())),
                    str(counts.get("ok", 0)),
                    str(counts.get("blocked", 0)),
                    str(counts.get("paywall", 0)),
                    str(counts.get("no_body", 0)),
                    str(counts.get("unsupported", 0)),
                    str(counts.get("error", 0)),
                ]
            )
            + " |"
        )
    lines.extend(
        [
            "",
            "## Fetched Targets",
            "",
            "| title | source | status | extractor | chars | cache | llm fallback | warnings |",
            "| --- | --- | --- | --- | ---: | --- | --- | --- |",
        ]
    )
    for record in records:
        lines.append(
            "| "
            + " | ".join(
                [
                    _table_cell(record.title),
                    _table_cell(record.source),
                    _table_cell(record.fetch_status),
                    _table_cell(record.extractor),
                    str(record.body_char_count),
                    _table_cell(record.cache_status),
                    _table_cell(record.llm_summary_status),
                    _table_cell(", ".join(record.warnings)),
                ]
            )
            + " |"
        )
    lines.extend(
        [
            "",
            "## Storage Note",
            "",
            (
                "Full body_text is stored only in the local gitignored cache JSONL. "
                "Reports include hashes, lengths, status diagnostics, and LLM fallback "
                "summaries."
            ),
            "",
        ]
    )
    report_payload = {
        "run_date": run_date,
        "target_count": len(records),
        "cache_path": str(output_jsonl),
        "status_counts": dict(status_counts),
        "cache_counts": dict(cache_counts),
        "llm_summary_counts": dict(llm_counts),
        "rows": [record.to_report_dict() for record in records],
    }
    report_md.parent.mkdir(parents=True, exist_ok=True)
    report_json.parent.mkdir(parents=True, exist_ok=True)
    report_md.write_text("\n".join(lines), encoding="utf-8")
    report_json.write_text(
        json.dumps(report_payload, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )


def run_article_body_fetch(
    *,
    run_date: str,
    input_metadata: Path,
    input_scored: Path,
    output_jsonl: Path = ARTICLE_CACHE_JSONL,
    report_md: Path | None = None,
    report_json: Path | None = None,
    include_scored_candidates: bool = False,
    max_items: int = 40,
    timeout: float = 12,
    refresh: bool = False,
    llm_summary_fallback: bool = False,
    llm_max_items: int = 10,
    llm_model: str | None = None,
    http_client: ArticleHttpClient | None = None,
    llm_client: LlmJsonClient | None = None,
) -> tuple[Path, Path, list[ArticleBodyRecord]]:
    targets = collect_article_targets(
        metadata_path=input_metadata,
        scored_candidates_path=input_scored,
        include_scored_candidates=include_scored_candidates,
        max_items=max_items,
    )
    records = fetch_article_bodies(
        targets=targets,
        output_jsonl=output_jsonl,
        http_client=http_client,
        timeout=timeout,
        refresh=refresh,
        llm_summary_fallback=llm_summary_fallback,
        llm_max_items=llm_max_items,
        llm_model=llm_model,
        llm_client=llm_client,
    )
    md_path = report_md or paths.REPORTS_DIR / f"jibi_article_body_fetch_{run_date}.md"
    json_path = report_json or paths.REPORTS_DIR / f"jibi_article_body_fetch_{run_date}.json"
    write_article_body_fetch_report(
        records=records,
        report_md=md_path,
        report_json=json_path,
        run_date=run_date,
        output_jsonl=output_jsonl,
    )
    return md_path, json_path, records


@app.callback(invoke_without_command=True)
def main(
    date_text: Annotated[
        str | None,
        typer.Option("--date", help="Run date for default input/output filenames."),
    ] = None,
    input_metadata: Annotated[
        Path | None,
        typer.Option("--input-metadata", help="Bundle review metadata JSON."),
    ] = None,
    input_scored: Annotated[
        Path,
        typer.Option("--input-scored", help="Scored candidate JSONL."),
    ] = paths.JIBI_SCORED_CANDIDATES_JSONL,
    output_jsonl: Annotated[
        Path,
        typer.Option("--output-jsonl", help="Local article body cache JSONL."),
    ] = ARTICLE_CACHE_JSONL,
    report_md: Annotated[
        Path | None,
        typer.Option("--report-md", help="Markdown report path."),
    ] = None,
    report_json: Annotated[
        Path | None,
        typer.Option("--report-json", help="JSON report path."),
    ] = None,
    include_scored_candidates: Annotated[
        bool,
        typer.Option(
            "--include-scored-candidates/--metadata-only",
            help="Also fetch the scored candidate pool after selected metadata rows.",
        ),
    ] = False,
    max_items: Annotated[
        int,
        typer.Option("--max-items", help="Maximum unique URLs to fetch; 0 means all."),
    ] = 40,
    timeout: Annotated[
        float,
        typer.Option("--timeout", help="Per-article network timeout in seconds."),
    ] = 12,
    refresh: Annotated[
        bool,
        typer.Option("--refresh/--use-cache", help="Refetch URLs already in cache."),
    ] = False,
    llm_summary_fallback: Annotated[
        bool,
        typer.Option(
            "--llm-summary-fallback/--no-llm-summary-fallback",
            help="Use GPT-5 mini lane to create Korean metadata summaries for failed bodies.",
        ),
    ] = False,
    llm_max_items: Annotated[
        int,
        typer.Option("--llm-max-items", help="Maximum failed URLs to summarize with LLM."),
    ] = 10,
    llm_model: Annotated[
        str | None,
        typer.Option("--llm-model", help="OpenAI model override; defaults to gpt-5-mini lane."),
    ] = None,
) -> None:
    run_date = date_text or datetime.now(UTC).date().isoformat()
    metadata_path = input_metadata or (
        paths.DAILY_DIGEST_DIR / f"{run_date}_bundle_review_sheet_metadata.json"
    )
    md_path, json_path, records = run_article_body_fetch(
        run_date=run_date,
        input_metadata=metadata_path,
        input_scored=input_scored,
        output_jsonl=output_jsonl,
        report_md=report_md,
        report_json=report_json,
        include_scored_candidates=include_scored_candidates,
        max_items=max_items,
        timeout=timeout,
        refresh=refresh,
        llm_summary_fallback=llm_summary_fallback,
        llm_max_items=llm_max_items,
        llm_model=llm_model,
    )
    status_counts = Counter(record.fetch_status for record in records)
    console.print(
        "[green]Wrote Jibi article body fetch report "
        f"({len(records)} targets; {dict(status_counts)}) to {md_path} and {json_path}."
        "[/green]"
    )


if __name__ == "__main__":
    app()
