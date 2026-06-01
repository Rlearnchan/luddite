"""Build Jibi evidence packs from board metadata and cached article bodies."""

from __future__ import annotations

import json
import re
from collections import Counter
from datetime import UTC, datetime
from pathlib import Path
from typing import Annotated, Any

import typer
from rich.console import Console

from luddite import paths
from luddite.agents.jibi.article_body import (
    ARTICLE_CACHE_JSONL,
    ArticleBodyRecord,
    _clean_text,
    _split_links,
    load_article_cache,
)
from luddite.utils.urls import canonicalize_url

app = typer.Typer(no_args_is_help=False)
console = Console()

NUMBER_RE = re.compile(
    r"(?<![A-Za-z0-9])\d+(?:[.,]\d+)?\s*(?:%|％|원|억원|조원|달러|억달러|조달러|명|건|개|배|년|개월|일|bn|m|million|billion|trillion)?",
    flags=re.I,
)
DATE_RE = re.compile(
    r"\b\d{4}[.-]\d{1,2}(?:[.-]\d{1,2})?\b|"
    r"\b\d{4}년(?:\s*\d{1,2}월)?(?:\s*\d{1,2}일)?\b|"
    r"\b\d{1,2}\s?(?:월|일)\b|"
    r"\b(?:Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)[a-z]*\.?\s+\d{1,2},?\s+\d{4}\b",
    flags=re.I,
)
QUOTE_RE = re.compile(r"[\"“‘']([^\"”’']{12,180})[\"”’']")
KOREAN_ORG_RE = re.compile(
    r"[가-힣A-Za-z0-9·]{2,30}(?:정부|부|청|위원회|공사|공단|은행|연구원|거래소|"
    r"증권|카드|보험|그룹|대학|재단|협회|조합|플랫폼|앱|회사)"
)
ENGLISH_ENTITY_RE = re.compile(
    r"\b(?:[A-Z][A-Za-z0-9&.-]+(?:\s+[A-Z][A-Za-z0-9&.-]+){0,4})\b"
)
POLICY_RE = re.compile(r"[가-힣A-Za-z0-9·]{2,30}(?:법|제도|정책|규제|계약|요금|수수료)")


def _dedupe(values: list[str], *, limit: int = 12) -> list[str]:
    seen: set[str] = set()
    deduped: list[str] = []
    for value in values:
        text = _clean_text(value)
        if not text or text in seen:
            continue
        seen.add(text)
        deduped.append(text)
        if len(deduped) >= limit:
            break
    return deduped


def _sentences(text: str) -> list[str]:
    parts = re.split(r"(?<=[.!?。！？])\s+|(?<=[다요음함됨])\.\s+|\n+", text)
    return [_clean_text(part) for part in parts if len(_clean_text(part)) >= 30]


def extract_evidence_features(text: str) -> dict[str, list[str]]:
    sentences = _sentences(text)
    numbers = _dedupe(NUMBER_RE.findall(text), limit=18)
    dates = _dedupe(DATE_RE.findall(text), limit=12)
    quotes = _dedupe([match.group(1) for match in QUOTE_RE.finditer(text)], limit=8)
    korean_orgs = KOREAN_ORG_RE.findall(text)
    english_entities = [
        value
        for value in ENGLISH_ENTITY_RE.findall(text)
        if value.lower() not in {"The", "This", "That", "Reuters", "BBC"}
    ]
    entities = _dedupe([*korean_orgs, *english_entities], limit=20)
    policies = _dedupe(POLICY_RE.findall(text), limit=12)
    key_sentences = sorted(
        sentences,
        key=lambda sentence: (
            bool(NUMBER_RE.search(sentence)) + bool(KOREAN_ORG_RE.search(sentence)),
            len(sentence),
        ),
        reverse=True,
    )
    return {
        "key_sentences": _dedupe(key_sentences, limit=6),
        "numbers": numbers,
        "dates": dates,
        "entities": entities,
        "quotes": quotes,
        "policy_terms": policies,
        "claims": _dedupe(key_sentences, limit=5),
    }


def _load_metadata_rows(path: Path) -> list[dict[str, Any]]:
    if not path.exists():
        return []
    payload = json.loads(path.read_text(encoding="utf-8"))
    if isinstance(payload, dict) and isinstance(payload.get("rows"), list):
        return [row for row in payload["rows"] if isinstance(row, dict)]
    if isinstance(payload, list):
        return [row for row in payload if isinstance(row, dict)]
    return []


def _article_for_url(
    url: str,
    *,
    cache: dict[str, ArticleBodyRecord],
) -> ArticleBodyRecord | None:
    canonical = canonicalize_url(url)
    return cache.get(canonical)


def _body_excerpt(record: ArticleBodyRecord, *, limit: int = 900) -> str:
    if record.body_text:
        return _clean_text(record.body_text[:limit])
    if record.llm_summary_ko:
        return _clean_text(record.llm_summary_ko[:limit])
    return ""


def _article_payload(record: ArticleBodyRecord) -> dict[str, Any]:
    text = record.body_text or record.llm_summary_ko
    features = extract_evidence_features(text)
    return {
        "url": record.url,
        "canonical_url": record.canonical_url,
        "fetch_status": record.fetch_status,
        "source": record.source,
        "title": record.title,
        "published_at": record.published_at,
        "body_excerpt": _body_excerpt(record),
        "body_char_count": record.body_char_count,
        "body_text_hash": record.body_text_hash,
        "extractor": record.extractor,
        "llm_summary_status": record.llm_summary_status,
        "llm_translated_title_ko": record.llm_translated_title_ko,
        "llm_summary_ko": record.llm_summary_ko,
        **features,
    }


def _rule_diagnostics(row: dict[str, Any]) -> dict[str, Any]:
    return {
        "board_score": row.get("board_score"),
        "selection_lessons": row.get("selection_lessons", []),
        "selection_lesson_role": row.get("selection_lesson_role", ""),
        "syuka_lesson_match_type": row.get("syuka_lesson_match_type", ""),
        "generic_visible_copy_warning": bool(row.get("generic_visible_copy_warning")),
        "main_seed_candidate": bool(row.get("main_seed_candidate")),
        "ready_seed_candidate": bool(row.get("ready_seed_candidate")),
        "support_status": row.get("support_status", ""),
        "support_missing_requirements": row.get("support_missing_requirements", []),
        "critical_support_requirements": row.get("critical_support_requirements", []),
        "seed_readiness_level": row.get("seed_readiness_level", ""),
        "seed_readiness_blockers": row.get("seed_readiness_blockers", []),
    }


def build_evidence_pack(
    *,
    run_date: str,
    metadata_path: Path,
    article_cache_path: Path = ARTICLE_CACHE_JSONL,
) -> dict[str, Any]:
    rows = _load_metadata_rows(metadata_path)
    cache = load_article_cache(article_cache_path)
    items: list[dict[str, Any]] = []
    for row in rows:
        urls = [
            str(row.get("main_link") or ""),
            *_split_links(row.get("sub_links")),
        ]
        article_bodies = []
        for url in urls:
            if not url:
                continue
            record = _article_for_url(url, cache=cache)
            if record:
                article_bodies.append(_article_payload(record))
            else:
                article_bodies.append(
                    {
                        "url": url,
                        "canonical_url": canonicalize_url(url),
                        "fetch_status": "missing_from_cache",
                        "body_excerpt": "",
                        "key_sentences": [],
                        "numbers": [],
                        "dates": [],
                        "entities": [],
                        "quotes": [],
                        "policy_terms": [],
                        "claims": [],
                    }
                )
        item = {
            "run_date": run_date,
            "review_item_id": row.get("ID") or row.get("review_item_id") or "",
            "story_bundle_id": row.get("story_bundle_id") or row.get("ID") or "",
            "story_fingerprint": row.get("story_fingerprint") or "",
            "visible_title": row.get("title") or "",
            "visible_description": row.get("description") or "",
            "main_url": row.get("main_link") or "",
            "source": row.get("source") or "",
            "source_role": row.get("source_role") or "",
            "editorial_role": row.get("editorial_role") or "",
            "editorial_role_confidence": row.get("editorial_role_confidence") or "",
            "board_score": row.get("board_score"),
            "rule_diagnostics": _rule_diagnostics(row),
            "article_bodies": article_bodies,
            "missing_evidence_from_rules": row.get("support_missing_requirements", []),
            "support_search_links": _split_links(row.get("support_links")),
        }
        items.append(item)
    status_counts = Counter(
        str(article.get("fetch_status"))
        for item in items
        for article in item.get("article_bodies", [])
    )
    return {
        "run_date": run_date,
        "metadata_path": str(metadata_path),
        "article_cache_path": str(article_cache_path),
        "item_count": len(items),
        "article_status_counts": dict(status_counts),
        "items": items,
    }


def _table_cell(value: object, *, limit: int = 140) -> str:
    text = _clean_text(str(value or ""))
    if len(text) > limit:
        text = text[: limit - 3].rstrip() + "..."
    return text.replace("|", "\\|")


def write_evidence_pack_report(
    *,
    payload: dict[str, Any],
    output_json: Path,
    output_md: Path,
) -> None:
    output_json.parent.mkdir(parents=True, exist_ok=True)
    output_md.parent.mkdir(parents=True, exist_ok=True)
    output_json.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    lines = [
        f"# Jibi Evidence Pack — {payload['run_date']}",
        "",
        "## Summary",
        "",
        f"- item_count: {payload['item_count']}",
    ]
    for status, count in sorted(payload.get("article_status_counts", {}).items()):
        lines.append(f"- article_{status}: {count}")
    lines.extend(
        [
            "",
            "## Evidence Items",
            "",
            "| title | role | board_score | article statuses | numbers | entities | key sentence |",
            "| --- | --- | ---: | --- | --- | --- | --- |",
        ]
    )
    for item in payload.get("items", []):
        articles = item.get("article_bodies", [])
        statuses = [str(article.get("fetch_status")) for article in articles]
        numbers = []
        entities = []
        key_sentence = ""
        for article in articles:
            numbers.extend(article.get("numbers") or [])
            entities.extend(article.get("entities") or [])
            if not key_sentence and article.get("key_sentences"):
                key_sentence = str(article["key_sentences"][0])
        lines.append(
            "| "
            + " | ".join(
                [
                    _table_cell(item.get("visible_title")),
                    _table_cell(item.get("editorial_role")),
                    str(item.get("board_score") or 0),
                    _table_cell(", ".join(statuses)),
                    _table_cell(", ".join(_dedupe(numbers, limit=5))),
                    _table_cell(", ".join(_dedupe(entities, limit=5))),
                    _table_cell(key_sentence, limit=180),
                ]
            )
            + " |"
        )
    lines.append("")
    output_md.write_text("\n".join(lines), encoding="utf-8")


def run_evidence_pack(
    *,
    run_date: str,
    metadata_path: Path,
    article_cache_path: Path = ARTICLE_CACHE_JSONL,
    output_json: Path | None = None,
    output_md: Path | None = None,
) -> tuple[Path, Path, dict[str, Any]]:
    payload = build_evidence_pack(
        run_date=run_date,
        metadata_path=metadata_path,
        article_cache_path=article_cache_path,
    )
    json_path = output_json or paths.REPORTS_DIR / f"jibi_evidence_pack_{run_date}.json"
    md_path = output_md or paths.REPORTS_DIR / f"jibi_evidence_pack_{run_date}.md"
    write_evidence_pack_report(payload=payload, output_json=json_path, output_md=md_path)
    return json_path, md_path, payload


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
    article_cache: Annotated[
        Path,
        typer.Option("--article-cache", help="Article body cache JSONL."),
    ] = ARTICLE_CACHE_JSONL,
    output_json: Annotated[
        Path | None,
        typer.Option("--output-json", help="Evidence pack JSON output."),
    ] = None,
    output_md: Annotated[
        Path | None,
        typer.Option("--output-md", help="Evidence pack Markdown output."),
    ] = None,
) -> None:
    run_date = date_text or datetime.now(UTC).date().isoformat()
    metadata_path = input_metadata or (
        paths.DAILY_DIGEST_DIR / f"{run_date}_bundle_review_sheet_metadata.json"
    )
    json_path, md_path, payload = run_evidence_pack(
        run_date=run_date,
        metadata_path=metadata_path,
        article_cache_path=article_cache,
        output_json=output_json,
        output_md=output_md,
    )
    console.print(
        "[green]Wrote Jibi evidence pack "
        f"({payload['item_count']} items) to {json_path} and {md_path}.[/green]"
    )


if __name__ == "__main__":
    app()
