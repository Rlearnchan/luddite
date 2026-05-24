"""Local article seen-history ledger for RSS collection runs."""

from __future__ import annotations

import json
import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from luddite import paths
from luddite.utils.jsonl import read_jsonl, write_jsonl

RUN_ID_SAFE_RE = re.compile(r"[^0-9A-Za-z]+")


@dataclass
class SourceHistoryDelta:
    source: str
    current_urls: int = 0
    new_to_history: int = 0
    new_since_previous_run: int = 0
    dropped_since_previous_run: int = 0


@dataclass
class ArticleHistorySummary:
    run_id: str
    run_date: str
    collected_at: str
    history_path: Path
    run_ledger_path: Path
    current_urls: int
    known_before: int
    known_after: int
    new_to_history: int
    returning_known: int
    previous_run_id: str | None = None
    previous_run_urls: int = 0
    new_since_previous_run: int = 0
    dropped_since_previous_run: int = 0
    percent_new_since_previous_run: float = 0.0
    percent_dropped_since_previous_run: float = 0.0
    churn_label: str = "low_churn"
    per_source: list[SourceHistoryDelta] = field(default_factory=list)
    new_examples: list[dict[str, str]] = field(default_factory=list)
    dropped_examples: list[dict[str, str]] = field(default_factory=list)


def update_article_history(
    articles: list[dict[str, object]],
    *,
    run_date: str,
    collected_at: str,
    history_path: Path = paths.JIBI_ARTICLE_HISTORY_JSONL,
    run_ledger_path: Path = paths.JIBI_ARTICLE_RUNS_JSONL,
) -> ArticleHistorySummary:
    """Update durable URL-level history and append one run snapshot."""
    run_id = make_run_id(run_date, collected_at)
    current_by_url = _articles_by_url(articles)
    current_urls = set(current_by_url)
    history_before = _load_history(history_path)
    known_before_urls = set(history_before)
    previous_run = _latest_run_snapshot(run_ledger_path)
    previous_urls = set(previous_run.get("canonical_urls", [])) if previous_run else set()
    previous_by_url = {
        str(item.get("canonical_url") or ""): item
        for item in previous_run.get("items", [])
        if isinstance(item, dict) and item.get("canonical_url")
    } if previous_run else {}

    new_to_history_urls = current_urls - known_before_urls
    returning_known_urls = current_urls & known_before_urls
    if previous_run:
        new_since_previous_urls = current_urls - previous_urls
        dropped_since_previous_urls = previous_urls - current_urls
    else:
        new_since_previous_urls = set(current_urls)
        dropped_since_previous_urls = set()
    percent_new = _percentage(len(new_since_previous_urls), len(current_urls))
    percent_dropped = _percentage(len(dropped_since_previous_urls), len(previous_urls))
    churn_label = _churn_label(percent_new, percent_dropped)

    updated_history = dict(history_before)
    for canonical_url, article in current_by_url.items():
        existing = updated_history.get(canonical_url)
        if existing:
            existing["last_seen_at"] = collected_at
            existing["last_seen_run_date"] = run_date
            existing["last_seen_run_id"] = run_id
            existing["seen_count"] = int(existing.get("seen_count") or 0) + 1
            existing["title"] = str(article.get("title") or existing.get("title") or "")
            existing["source"] = str(article.get("source") or existing.get("source") or "")
            existing["source_id"] = str(
                article.get("source_id") or existing.get("source_id") or ""
            )
            existing["published_at"] = (
                str(article.get("published_at") or existing.get("published_at") or "")
                or None
            )
            existing["last_collected_at"] = str(article.get("collected_at") or collected_at)
        else:
            updated_history[canonical_url] = _new_history_record(
                article,
                canonical_url=canonical_url,
                run_date=run_date,
                run_id=run_id,
                collected_at=collected_at,
            )

    history_records = sorted(updated_history.values(), key=lambda item: str(item["canonical_url"]))
    write_jsonl(history_path, history_records)

    run_items = [
        _run_item(article, canonical_url)
        for canonical_url, article in current_by_url.items()
    ]
    run_snapshot = {
        "run_id": run_id,
        "run_date": run_date,
        "collected_at": collected_at,
        "current_urls": len(current_urls),
        "new_to_history": len(new_to_history_urls),
        "returning_known": len(returning_known_urls),
        "previous_run_id": previous_run.get("run_id") if previous_run else None,
        "previous_run_urls": len(previous_urls),
        "new_since_previous_run": len(new_since_previous_urls),
        "dropped_since_previous_run": len(dropped_since_previous_urls),
        "percent_new_since_previous_run": percent_new,
        "percent_dropped_since_previous_run": percent_dropped,
        "churn_label": churn_label,
        "canonical_urls": sorted(current_urls),
        "items": sorted(run_items, key=lambda item: item["canonical_url"]),
    }
    _append_jsonl(run_ledger_path, run_snapshot)

    return ArticleHistorySummary(
        run_id=run_id,
        run_date=run_date,
        collected_at=collected_at,
        history_path=history_path,
        run_ledger_path=run_ledger_path,
        current_urls=len(current_urls),
        known_before=len(known_before_urls),
        known_after=len(updated_history),
        new_to_history=len(new_to_history_urls),
        returning_known=len(returning_known_urls),
        previous_run_id=str(previous_run.get("run_id")) if previous_run else None,
        previous_run_urls=len(previous_urls),
        new_since_previous_run=len(new_since_previous_urls),
        dropped_since_previous_run=len(dropped_since_previous_urls),
        percent_new_since_previous_run=percent_new,
        percent_dropped_since_previous_run=percent_dropped,
        churn_label=churn_label,
        per_source=_source_deltas(
            current_by_url=current_by_url,
            previous_by_url=previous_by_url,
            new_to_history_urls=new_to_history_urls,
            new_since_previous_urls=new_since_previous_urls,
            dropped_since_previous_urls=dropped_since_previous_urls,
        ),
        new_examples=_examples(current_by_url, new_since_previous_urls),
        dropped_examples=_examples(previous_by_url, dropped_since_previous_urls),
    )


def make_run_id(run_date: str, collected_at: str) -> str:
    safe_timestamp = RUN_ID_SAFE_RE.sub("", collected_at)[:16]
    return f"rss_{run_date}_{safe_timestamp}"


def _percentage(numerator: int, denominator: int) -> float:
    if denominator <= 0:
        return 0.0
    return round(numerator / denominator * 100, 2)


def _churn_label(percent_new: float, percent_dropped: float) -> str:
    churn = max(percent_new, percent_dropped)
    if churn <= 5:
        return "low_churn"
    if churn <= 25:
        return "normal_churn"
    return "high_churn"


def _load_history(path: Path) -> dict[str, dict[str, Any]]:
    if not path.exists():
        return {}
    records = read_jsonl(path)
    return {
        str(record["canonical_url"]): record
        for record in records
        if isinstance(record, dict) and record.get("canonical_url")
    }


def _latest_run_snapshot(path: Path) -> dict[str, Any] | None:
    if not path.exists():
        return None
    latest: dict[str, Any] | None = None
    for record in read_jsonl(path):
        if isinstance(record, dict) and int(record.get("current_urls") or 0) > 0:
            latest = record
    return latest


def _articles_by_url(articles: list[dict[str, object]]) -> dict[str, dict[str, object]]:
    by_url: dict[str, dict[str, object]] = {}
    for article in articles:
        canonical_url = str(
            article.get("source_url_canonical") or article.get("url") or ""
        ).strip()
        if canonical_url and canonical_url not in by_url:
            by_url[canonical_url] = article
    return by_url


def _new_history_record(
    article: dict[str, object],
    *,
    canonical_url: str,
    run_date: str,
    run_id: str,
    collected_at: str,
) -> dict[str, object]:
    return {
        "article_id": str(article.get("article_id") or ""),
        "canonical_url": canonical_url,
        "duplicate_key": str(article.get("duplicate_key") or ""),
        "title": str(article.get("title") or ""),
        "source": str(article.get("source") or ""),
        "source_id": str(article.get("source_id") or ""),
        "published_at": article.get("published_at") or None,
        "first_seen_at": collected_at,
        "first_seen_run_date": run_date,
        "first_seen_run_id": run_id,
        "last_seen_at": collected_at,
        "last_seen_run_date": run_date,
        "last_seen_run_id": run_id,
        "last_collected_at": str(article.get("collected_at") or collected_at),
        "seen_count": 1,
    }


def _run_item(article: dict[str, object], canonical_url: str) -> dict[str, str]:
    return {
        "canonical_url": canonical_url,
        "title": str(article.get("title") or ""),
        "source": str(article.get("source") or ""),
        "source_id": str(article.get("source_id") or ""),
        "published_at": str(article.get("published_at") or ""),
    }


def _append_jsonl(path: Path, record: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as output:
        output.write(json.dumps(record, ensure_ascii=False, sort_keys=True))
        output.write("\n")


def _source_deltas(
    *,
    current_by_url: dict[str, dict[str, object]],
    previous_by_url: dict[str, dict[str, object]],
    new_to_history_urls: set[str],
    new_since_previous_urls: set[str],
    dropped_since_previous_urls: set[str],
) -> list[SourceHistoryDelta]:
    source_names = {
        str(article.get("source") or "")
        for article in [*current_by_url.values(), *previous_by_url.values()]
        if str(article.get("source") or "").strip()
    }
    deltas: list[SourceHistoryDelta] = []
    for source_name in sorted(source_names):
        current_source_urls = {
            url
            for url, article in current_by_url.items()
            if str(article.get("source") or "") == source_name
        }
        previous_source_urls = {
            url
            for url, article in previous_by_url.items()
            if str(article.get("source") or "") == source_name
        }
        deltas.append(
            SourceHistoryDelta(
                source=source_name,
                current_urls=len(current_source_urls),
                new_to_history=len(current_source_urls & new_to_history_urls),
                new_since_previous_run=len(current_source_urls & new_since_previous_urls),
                dropped_since_previous_run=len(
                    previous_source_urls & dropped_since_previous_urls
                ),
            )
        )
    return deltas


def _examples(
    by_url: dict[str, dict[str, object]],
    urls: set[str],
    *,
    limit: int = 10,
) -> list[dict[str, str]]:
    examples: list[dict[str, str]] = []
    for url in sorted(urls):
        article = by_url.get(url)
        if not article:
            continue
        examples.append(
            {
                "source": str(article.get("source") or ""),
                "title": str(article.get("title") or ""),
                "url": url,
                "published_at": str(article.get("published_at") or ""),
            }
        )
        if len(examples) >= limit:
            break
    return examples
