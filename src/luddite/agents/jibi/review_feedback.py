"""Read-only summaries for the Jibi bundle review board."""

from __future__ import annotations

import csv
import json
import re
from collections import Counter, defaultdict
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Annotated, Any
from urllib.parse import urlparse

import typer
from rich.console import Console

from luddite import paths
from luddite.agents.jibi.append_to_sheet import (
    BUNDLE_REVIEW_SHEET_COLUMNS,
    REVIEWER_COLUMNS,
    GoogleSheetAppendConfig,
    load_append_config,
)
from luddite.integrations.google_sheets import GoogleSheetsApiClient
from luddite.utils.jsonl import read_jsonl
from luddite.utils.urls import canonicalize_url

app = typer.Typer(no_args_is_help=False)
history_app = typer.Typer(no_args_is_help=False)
console = Console()

REVIEW_TAGS = ["seed", "evidence", "merge", "needs", "reject", "unclear", "unlabeled"]
TAG_ALIASES = {
    "seed": "seed",
    "방송": "seed",
    "소재": "seed",
    "evidence": "evidence",
    "근거": "evidence",
    "merge": "merge",
    "묶기": "merge",
    "중복": "merge",
    "needs": "needs",
    "보강": "needs",
    "자료필요": "needs",
    "reject": "reject",
    "기각": "reject",
    "별로": "reject",
    "아님": "reject",
    "unclear": "unclear",
    "애매": "unclear",
    "모름": "unclear",
}


@dataclass(frozen=True)
class ReviewFeedbackPaths:
    markdown_path: Path
    json_path: Path


@dataclass(frozen=True)
class ReviewHistoryCalibrationPaths:
    markdown_path: Path
    json_path: Path


def parse_review_tag(note: str) -> str:
    text = note.strip().lower()
    if not text:
        return "unlabeled"
    token = re.split(r"\s*(?:—|–|-|:)\s*|\s+", text, maxsplit=1)[0].strip()
    return TAG_ALIASES.get(token, "unlabeled")


def _rows_from_values(values: list[list[str]]) -> list[dict[str, str]]:
    if not values:
        return []
    header = values[0]
    rows: list[dict[str, str]] = []
    for raw_row in values[1:]:
        row = {
            column: raw_row[index] if index < len(raw_row) else ""
            for index, column in enumerate(header)
        }
        if any(str(value).strip() for value in row.values()):
            rows.append(row)
    return rows


def _rows_from_csv(path: Path) -> list[dict[str, str]]:
    with path.open(encoding="utf-8-sig", newline="") as source:
        return list(csv.DictReader(source))


def _reviewer_completion(rows: list[dict[str, str]]) -> dict[str, int]:
    return {
        column: sum(1 for row in rows if str(row.get(column, "")).strip())
        for column in REVIEWER_COLUMNS
    }


def _note_payload(note: str) -> dict[str, str]:
    return {"tag": parse_review_tag(note), "note": note.strip()}


def _row_registered_at(row: dict[str, Any]) -> str:
    return str(row.get("일시") or row.get("날짜") or "").strip()


def _row_date(row: dict[str, Any], fallback: str = "") -> str:
    value = _row_registered_at(row)
    if len(value) >= 10:
        return value[:10]
    return fallback


def summarize_review_feedback(
    rows: list[dict[str, str]],
    *,
    run_date: str,
) -> dict[str, Any]:
    tag_counts = Counter({tag: 0 for tag in REVIEW_TAGS})
    row_payloads: list[dict[str, Any]] = []
    disagreement_rows: list[dict[str, Any]] = []
    for index, row in enumerate(rows, start=2):
        reviewer_notes = {
            column: _note_payload(str(row.get(column, "")))
            for column in REVIEWER_COLUMNS
        }
        for note in reviewer_notes.values():
            if note["note"]:
                tag_counts[note["tag"]] += 1
        tags = {note["tag"] for note in reviewer_notes.values() if note["note"]}
        row_payload = {
            "row": index,
            "date": _row_date(row, run_date),
            "registered_at": _row_registered_at(row),
            "title": row.get("제목", ""),
            "score": row.get("점수", ""),
            "id": row.get("ID", ""),
            "reviewers": reviewer_notes,
        }
        row_payloads.append(row_payload)
        if "seed" in tags and "reject" in tags:
            disagreement_rows.append(
                {
                    "row": index,
                    "title": row.get("제목", ""),
                    "id": row.get("ID", ""),
                    "tags": sorted(tags),
                    "reason": "seed_vs_reject",
                }
            )
    return {
        "run_date": run_date,
        "generated_at": datetime.now(UTC).isoformat(),
        "total_rows": len(rows),
        "reviewer_completion": _reviewer_completion(rows),
        "tag_counts": dict(tag_counts),
        "rows": row_payloads,
        "disagreement_rows": disagreement_rows,
    }


def _markdown(summary: dict[str, Any]) -> str:
    lines = [
        f"# Jibi Review Feedback — {summary['run_date']}",
        "",
        f"- Total rows: {summary['total_rows']}",
        f"- Generated at: `{summary['generated_at']}`",
        "",
        "## Reviewer Completion",
        "",
    ]
    for reviewer, count in summary["reviewer_completion"].items():
        lines.append(f"- {reviewer}: {count}/{summary['total_rows']}")
    lines.extend(["", "## Tag Counts", ""])
    for tag in REVIEW_TAGS:
        lines.append(f"- {tag}: {summary['tag_counts'].get(tag, 0)}")
    lines.extend(["", "## Notes By Row", ""])
    for row in summary["rows"]:
        lines.append(f"### {row['title'] or 'untitled'}")
        lines.append("")
        lines.append(f"- ID: `{row['id']}`")
        if row.get("score"):
            lines.append(f"- 점수: {row['score']}")
        for reviewer in REVIEWER_COLUMNS:
            note = row["reviewers"][reviewer]
            note_text = note["note"] or "(blank)"
            lines.append(f"- {reviewer}: `{note['tag']}` — {note_text}")
        lines.append("")
    lines.extend(["## Disagreement Rows", ""])
    if summary["disagreement_rows"]:
        for row in summary["disagreement_rows"]:
            lines.append(
                f"- row {row['row']}: {row['title']} "
                f"({row['id']}) — {', '.join(row['tags'])}"
            )
    else:
        lines.append("- none")
    return "\n".join(lines) + "\n"


def _default_run_date(rows: list[dict[str, str]]) -> str:
    for row in rows:
        value = _row_registered_at(row)
        if value:
            return value[:10]
    return datetime.now(UTC).date().isoformat()


def _write_summary(
    summary: dict[str, Any],
    *,
    markdown_path: Path,
    json_path: Path,
) -> ReviewFeedbackPaths:
    markdown_path.parent.mkdir(parents=True, exist_ok=True)
    json_path.parent.mkdir(parents=True, exist_ok=True)
    markdown_path.write_text(_markdown(summary), encoding="utf-8")
    json_path.write_text(
        json.dumps(summary, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    return ReviewFeedbackPaths(markdown_path=markdown_path, json_path=json_path)


def _read_sheet_rows(config: GoogleSheetAppendConfig) -> list[dict[str, str]]:
    if not config.spreadsheet_id:
        raise ValueError("spreadsheet_id is required when --input-csv is not provided.")
    client = GoogleSheetsApiClient(
        credentials_path=config.service_account_json_path,
        auth_mode=config.auth_mode,
    )
    return _rows_from_values(
        client.get_values(config.spreadsheet_id, config.target_sheet_name)
    )


def render_review_feedback_summary(
    *,
    input_csv: Path | None = None,
    run_date: str | None = None,
    markdown_path: Path | None = None,
    json_path: Path | None = None,
    config: GoogleSheetAppendConfig | None = None,
) -> tuple[ReviewFeedbackPaths, dict[str, Any]]:
    loaded = config or load_append_config()
    rows = _rows_from_csv(input_csv) if input_csv else _read_sheet_rows(loaded)
    required_columns = [
        column
        for column in BUNDLE_REVIEW_SHEET_COLUMNS
        if column not in {"점수", "일시"}
    ]
    missing = [column for column in required_columns if rows and column not in rows[0]]
    if rows and "일시" not in rows[0] and "날짜" not in rows[0]:
        missing.append("일시")
    if missing:
        raise ValueError("Review board is missing columns: " + ", ".join(missing))
    date_value = run_date or _default_run_date(rows)
    summary = summarize_review_feedback(rows, run_date=date_value)
    paths_out = _write_summary(
        summary,
        markdown_path=markdown_path
        or paths.REPORTS_DIR / f"jibi_review_feedback_{date_value}.md",
        json_path=json_path
        or paths.REPORTS_DIR / f"jibi_review_feedback_{date_value}.json",
    )
    return paths_out, summary


def _history_key_from_row(row: dict[str, Any]) -> str:
    fingerprint = str(row.get("story_fingerprint") or "").strip()
    if fingerprint:
        return fingerprint
    review_id = str(row.get("ID") or row.get("id") or "").strip()
    if ":" in review_id:
        return review_id.rsplit(":", 1)[1]
    return review_id


def _domain(value: str) -> str:
    url = str(value or "").strip()
    if not url:
        return "unknown"
    parsed = urlparse(url)
    return parsed.netloc.lower().removeprefix("www.") or "unknown"


def _candidate_metadata_index(path: Path) -> dict[str, dict[str, str]]:
    if not path.exists():
        return {}
    index: dict[str, dict[str, str]] = {}
    for candidate in read_jsonl(path):
        urls = {
            str(candidate.get("seed_url") or ""),
            str(candidate.get("source_url_canonical") or ""),
        }
        metadata = {
            "source": str(candidate.get("source") or "").strip(),
            "source_role": str(candidate.get("source_role_class") or "unknown"),
            "seed_type": str(candidate.get("seed_type") or "unknown"),
            "candidate_id": str(candidate.get("candidate_id") or ""),
        }
        for url in urls:
            key = canonicalize_url(url)
            if key:
                index.setdefault(key, metadata)
    return index


def _metadata_for_row(
    row: dict[str, str],
    candidate_index: dict[str, dict[str, str]],
) -> dict[str, str]:
    link = str(row.get("메인 링크") or "").strip()
    metadata = candidate_index.get(canonicalize_url(link), {})
    return {
        "source": metadata.get("source") or _domain(link),
        "source_role": metadata.get("source_role") or "unknown",
        "seed_type": metadata.get("seed_type") or "unknown",
        "candidate_id": metadata.get("candidate_id") or "",
    }


def _history_payload_rows(history_path: Path) -> list[dict[str, Any]]:
    if not history_path.exists():
        return []
    rows: list[dict[str, Any]] = []
    for line in history_path.read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        try:
            payload = json.loads(line)
        except json.JSONDecodeError:
            continue
        run_date = str(payload.get("run_date") or "").strip()
        snapshot_created_at = str(payload.get("created_at") or "").strip()
        for row in payload.get("rows", []):
            if not isinstance(row, dict):
                continue
            item = {str(key): str(value) for key, value in row.items()}
            item["일시"] = item.get("일시") or item.get("날짜") or run_date
            item["story_fingerprint"] = _history_key_from_row(item)
            item["_snapshot_created_at"] = snapshot_created_at
            item["_source_kind"] = "history"
            rows.append(item)
    return rows


def _csv_payload_rows(path: Path, *, source_kind: str = "current_csv") -> list[dict[str, Any]]:
    rows = [dict(row) for row in _rows_from_csv(path)]
    for row in rows:
        row["story_fingerprint"] = _history_key_from_row(row)
        row["_source_kind"] = source_kind
    return rows


def _review_tags_for_row(row: dict[str, Any]) -> dict[str, dict[str, str]]:
    return {
        reviewer: _note_payload(str(row.get(reviewer, "")))
        for reviewer in REVIEWER_COLUMNS
    }


def _has_reviewer_note(row: dict[str, Any]) -> bool:
    return any(str(row.get(reviewer) or "").strip() for reviewer in REVIEWER_COLUMNS)


def _empty_tag_counter() -> Counter[str]:
    return Counter({tag: 0 for tag in REVIEW_TAGS})


def _dimension_feedback_summary(
    rows: list[dict[str, Any]],
    key_name: str,
) -> list[dict[str, Any]]:
    summary: dict[str, dict[str, Any]] = {}
    for row in rows:
        key = str(row.get(key_name) or "unknown")
        item = summary.setdefault(
            key,
            {
                "key": key,
                "rows": 0,
                "reviewed_rows": 0,
                "tag_counts": _empty_tag_counter(),
            },
        )
        item["rows"] += 1
        if _has_reviewer_note(row):
            item["reviewed_rows"] += 1
        for note in _review_tags_for_row(row).values():
            if note["note"]:
                item["tag_counts"][note["tag"]] += 1
    payload = []
    for item in summary.values():
        tag_counts = dict(item["tag_counts"])
        payload.append(
            {
                "key": item["key"],
                "rows": item["rows"],
                "reviewed_rows": item["reviewed_rows"],
                "tag_counts": tag_counts,
            }
        )
    payload.sort(
        key=lambda item: (
            -int(item["reviewed_rows"]),
            -int(item["rows"]),
            str(item["key"]),
        )
    )
    return payload


def _story_reappearance_summary(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    grouped: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for row in rows:
        key = str(row.get("story_fingerprint") or "").strip()
        if key:
            grouped[key].append(row)
    payload: list[dict[str, Any]] = []
    for key, items in grouped.items():
        tag_counts = _empty_tag_counter()
        for row in items:
            for note in _review_tags_for_row(row).values():
                if note["note"]:
                    tag_counts[note["tag"]] += 1
        dates = sorted(
            {
                _row_date(item)
                for item in items
                if _row_date(item)
            }
        )
        payload.append(
            {
                "story_fingerprint": key,
                "appearances": len(items),
                "dates": dates,
                "titles": sorted(
                    {str(item.get("제목") or "") for item in items if item.get("제목")}
                )[:3],
                "tag_counts": dict(tag_counts),
            }
        )
    payload.sort(key=lambda item: (-int(item["appearances"]), item["story_fingerprint"]))
    return payload


def _strong_disagreements(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    disagreements: list[dict[str, Any]] = []
    for row in rows:
        tags = {
            note["tag"]
            for note in _review_tags_for_row(row).values()
            if note["note"]
        }
        if "seed" in tags and "reject" in tags:
            reason = "seed_vs_reject"
        elif "evidence" in tags and "reject" in tags:
            reason = "evidence_vs_reject"
        else:
            continue
        disagreements.append(
            {
                "date": _row_date(row),
                "registered_at": _row_registered_at(row),
                "title": row.get("제목", ""),
                "id": row.get("ID", ""),
                "story_fingerprint": row.get("story_fingerprint", ""),
                "tags": sorted(tags),
                "reason": reason,
            }
        )
    return disagreements


def _recommendations_from_dimension(
    dimension: str,
    rows: list[dict[str, Any]],
) -> list[dict[str, str]]:
    recommendations: list[dict[str, str]] = []
    for item in rows:
        tags = item["tag_counts"]
        negative = tags.get("reject", 0) + tags.get("needs", 0) + tags.get("unclear", 0)
        positive = tags.get("seed", 0) + tags.get("evidence", 0)
        if item["reviewed_rows"] == 0:
            continue
        if positive >= 2 and positive > negative:
            recommendations.append(
                {
                    "type": f"{dimension}_to_promote",
                    "target": str(item["key"]),
                    "reason": "seed/evidence feedback is stronger than reject/needs",
                }
            )
        elif negative >= 2 and negative >= positive:
            recommendations.append(
                {
                    "type": f"{dimension}_to_watch",
                    "target": str(item["key"]),
                    "reason": "reject/needs/unclear feedback dominates",
                }
            )
    return recommendations


def _feedback_recommendations(summary: dict[str, Any]) -> list[dict[str, str]]:
    recommendations: list[dict[str, str]] = []
    recommendations.extend(
        _recommendations_from_dimension("source", summary["source_feedback"])
    )
    recommendations.extend(
        _recommendations_from_dimension("source_role", summary["source_role_feedback"])
    )
    recommendations.extend(
        _recommendations_from_dimension("seed_type", summary["seed_type_feedback"])
    )
    for story in summary["story_reappearance"]:
        tags = story["tag_counts"]
        if story["appearances"] < 2:
            continue
        if tags.get("reject", 0):
            recommendations.append(
                {
                    "type": "story_bundle_rule_to_adjust",
                    "target": story["story_fingerprint"],
                    "reason": "reappearing story has reject feedback",
                }
            )
        elif tags.get("seed", 0) or tags.get("merge", 0):
            recommendations.append(
                {
                    "type": "story_bundle_to_track",
                    "target": story["story_fingerprint"],
                    "reason": "reappearing story has seed/merge feedback",
                }
            )
    return recommendations or [
        {
            "type": "insufficient_feedback",
            "target": "review_board",
            "reason": "collect more one-line reviewer notes before tuning",
        }
    ]


def summarize_review_history_calibration(
    rows: list[dict[str, Any]],
    *,
    run_date: str,
) -> dict[str, Any]:
    tag_counts = _empty_tag_counter()
    reviewer_completion: dict[str, dict[str, int]] = defaultdict(
        lambda: {reviewer: 0 for reviewer in REVIEWER_COLUMNS}
    )
    rows_by_date: Counter[str] = Counter()
    normalized_rows: list[dict[str, Any]] = []
    for row in rows:
        date_value = _row_date(row, run_date)
        rows_by_date[date_value] += 1
        _ = reviewer_completion[date_value]
        reviewer_notes = _review_tags_for_row(row)
        for reviewer, note in reviewer_notes.items():
            if note["note"]:
                reviewer_completion[date_value][reviewer] += 1
                tag_counts[note["tag"]] += 1
        normalized_rows.append(
            {
                "date": date_value,
                "title": row.get("제목", ""),
                "score": row.get("점수", ""),
                "id": row.get("ID", ""),
                "story_fingerprint": row.get("story_fingerprint", ""),
                "source": row.get("source", "unknown"),
                "source_role": row.get("source_role", "unknown"),
                "seed_type": row.get("seed_type", "unknown"),
                "reviewers": reviewer_notes,
            }
        )
    summary = {
        "run_date": run_date,
        "generated_at": datetime.now(UTC).isoformat(),
        "total_rows": len(rows),
        "rows_by_date": dict(sorted(rows_by_date.items())),
        "reviewer_completion_by_date": dict(sorted(reviewer_completion.items())),
        "tag_counts": dict(tag_counts),
        "source_feedback": _dimension_feedback_summary(rows, "source"),
        "source_role_feedback": _dimension_feedback_summary(rows, "source_role"),
        "seed_type_feedback": _dimension_feedback_summary(rows, "seed_type"),
        "story_reappearance": _story_reappearance_summary(rows),
        "strong_disagreement_rows": _strong_disagreements(rows),
        "rows": normalized_rows,
    }
    summary["recommendations"] = _feedback_recommendations(summary)
    return summary


def _metadata_enriched_rows(
    rows: list[dict[str, Any]],
    *,
    candidates_path: Path,
) -> list[dict[str, Any]]:
    candidate_index = _candidate_metadata_index(candidates_path)
    enriched: list[dict[str, Any]] = []
    for row in rows:
        item = dict(row)
        metadata = _metadata_for_row(
            {str(key): str(value) for key, value in item.items()},
            candidate_index,
        )
        item.update(metadata)
        enriched.append(item)
    return enriched


def _feedback_table(rows: list[dict[str, Any]], label: str) -> list[str]:
    if not rows:
        return ["| none | 0 | 0 | 0 | 0 | 0 | 0 | 0 |"]
    lines = []
    for item in rows:
        tags = item["tag_counts"]
        lines.append(
            "| "
            + " | ".join(
                [
                    str(item["key"]),
                    str(item["rows"]),
                    str(item["reviewed_rows"]),
                    str(tags.get("seed", 0)),
                    str(tags.get("evidence", 0)),
                    str(tags.get("needs", 0)),
                    str(tags.get("reject", 0)),
                    str(tags.get("unlabeled", 0)),
                ]
            )
            + " |"
        )
    return lines or [f"| {label} | 0 | 0 | 0 | 0 | 0 | 0 | 0 |"]


def _history_markdown(summary: dict[str, Any]) -> str:
    lines = [
        f"# Jibi Feedback Calibration — {summary['run_date']}",
        "",
        f"- Total rows: {summary['total_rows']}",
        f"- Generated at: `{summary['generated_at']}`",
        "",
        "## Reviewer Completion By Date",
        "",
    ]
    for date_value, completion in summary["reviewer_completion_by_date"].items():
        total = summary["rows_by_date"].get(date_value, 0)
        counts = ", ".join(
            f"{reviewer}: {completion.get(reviewer, 0)}/{total}"
            for reviewer in REVIEWER_COLUMNS
        )
        lines.append(f"- {date_value}: {counts}")
    lines.extend(["", "## Tag Counts", ""])
    for tag in REVIEW_TAGS:
        lines.append(f"- {tag}: {summary['tag_counts'].get(tag, 0)}")
    for heading, key in [
        ("Source-Level Feedback Summary", "source_feedback"),
        ("Source-Role Feedback Summary", "source_role_feedback"),
        ("Seed-Type / Template Feedback Summary", "seed_type_feedback"),
    ]:
        lines.extend(
            [
                "",
                f"## {heading}",
                "",
                "| key | rows | reviewed_rows | seed | evidence | needs | reject | unlabeled |",
                "| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |",
                *_feedback_table(summary[key], key),
            ]
        )
    lines.extend(
        [
            "",
            "## Story-Fingerprint Reappearance Summary",
            "",
            "| story_fingerprint | appearances | dates | seed | merge | reject | titles |",
            "| --- | ---: | --- | ---: | ---: | ---: | --- |",
        ]
    )
    for story in summary["story_reappearance"]:
        tags = story["tag_counts"]
        lines.append(
            "| "
            + " | ".join(
                [
                    str(story["story_fingerprint"]),
                    str(story["appearances"]),
                    ", ".join(story["dates"]),
                    str(tags.get("seed", 0)),
                    str(tags.get("merge", 0)),
                    str(tags.get("reject", 0)),
                    "; ".join(story["titles"]),
                ]
            )
            + " |"
        )
    lines.extend(["", "## Rows With Strong Disagreement", ""])
    if summary["strong_disagreement_rows"]:
        for row in summary["strong_disagreement_rows"]:
            lines.append(
                f"- {row['date']} `{row['story_fingerprint']}` "
                f"{row['title']} — {row['reason']} ({', '.join(row['tags'])})"
            )
    else:
        lines.append("- none")
    lines.extend(["", "## Report-Only Recommendations", ""])
    for item in summary["recommendations"]:
        lines.append(f"- {item['type']}: `{item['target']}` — {item['reason']}")
    return "\n".join(lines) + "\n"


def _write_history_calibration(
    summary: dict[str, Any],
    *,
    markdown_path: Path,
    json_path: Path,
) -> ReviewHistoryCalibrationPaths:
    markdown_path.parent.mkdir(parents=True, exist_ok=True)
    json_path.parent.mkdir(parents=True, exist_ok=True)
    markdown_path.write_text(_history_markdown(summary), encoding="utf-8")
    json_path.write_text(
        json.dumps(summary, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    return ReviewHistoryCalibrationPaths(markdown_path=markdown_path, json_path=json_path)


def render_review_history_calibration(
    *,
    history_path: Path = paths.JIBI_REVIEW_BOARD_HISTORY_JSONL,
    current_csv: Path | None = None,
    include_current_sheet: bool = False,
    run_date: str | None = None,
    candidates_path: Path = paths.JIBI_SCORED_CANDIDATES_JSONL,
    markdown_path: Path | None = None,
    json_path: Path | None = None,
    config: GoogleSheetAppendConfig | None = None,
) -> tuple[ReviewHistoryCalibrationPaths, dict[str, Any]]:
    loaded = config or load_append_config()
    rows: list[dict[str, Any]] = _history_payload_rows(history_path)
    if current_csv:
        rows.extend(_csv_payload_rows(current_csv))
    if include_current_sheet:
        rows.extend(_rows_from_values(_read_sheet_values(loaded)))
        for row in rows:
            row.setdefault("story_fingerprint", _history_key_from_row(row))
            row.setdefault("_source_kind", "current_sheet")
    date_value = run_date or datetime.now(UTC).date().isoformat()
    enriched_rows = _metadata_enriched_rows(rows, candidates_path=candidates_path)
    summary = summarize_review_history_calibration(enriched_rows, run_date=date_value)
    paths_out = _write_history_calibration(
        summary,
        markdown_path=markdown_path
        or paths.REPORTS_DIR / f"jibi_feedback_calibration_{date_value}.md",
        json_path=json_path
        or paths.REPORTS_DIR / f"jibi_feedback_calibration_{date_value}.json",
    )
    return paths_out, summary


def _read_sheet_values(config: GoogleSheetAppendConfig) -> list[list[str]]:
    if not config.spreadsheet_id:
        raise ValueError("spreadsheet_id is required for current sheet readback.")
    client = GoogleSheetsApiClient(
        credentials_path=config.service_account_json_path,
        auth_mode=config.auth_mode,
    )
    return client.get_values(config.spreadsheet_id, config.target_sheet_name)


@app.callback(invoke_without_command=True)
def main(
    input_csv: Annotated[
        Path | None,
        typer.Option("--input-csv", help="Local Jibi bundle review CSV to summarize."),
    ] = None,
    run_date: Annotated[
        str | None,
        typer.Option("--date", help="Feedback report date in YYYY-MM-DD."),
    ] = None,
    spreadsheet_id: Annotated[
        str | None,
        typer.Option("--spreadsheet-id", help="Target Google spreadsheet id."),
    ] = None,
    sheet_name: Annotated[
        str | None,
        typer.Option("--sheet-name", help="Review board sheet name."),
    ] = None,
    markdown_path: Annotated[
        Path | None,
        typer.Option("--output-md", help="Markdown report path."),
    ] = None,
    json_path: Annotated[
        Path | None,
        typer.Option("--output-json", help="JSON report path."),
    ] = None,
) -> None:
    loaded = load_append_config()
    config = GoogleSheetAppendConfig(
        spreadsheet_id=spreadsheet_id or loaded.spreadsheet_id,
        target_sheet_name=sheet_name or loaded.target_sheet_name,
        sheet_schema=loaded.sheet_schema,
        dry_run=True,
        auth_mode=loaded.auth_mode,
        service_account_json_path=loaded.service_account_json_path,
    )
    try:
        outputs, summary = render_review_feedback_summary(
            input_csv=input_csv,
            run_date=run_date,
            markdown_path=markdown_path,
            json_path=json_path,
            config=config,
        )
    except ValueError as exc:
        console.print(f"[red]Jibi review feedback summary failed: {exc}[/red]")
        raise typer.Exit(1) from exc
    console.print(
        "[green]Wrote Jibi review feedback summary "
        f"for {summary['total_rows']} rows to {outputs.markdown_path} and "
        f"{outputs.json_path}.[/green]"
    )


@history_app.callback(invoke_without_command=True)
def history_main(
    history_path: Annotated[
        Path,
        typer.Option("--history", help="Local review board history JSONL."),
    ] = paths.JIBI_REVIEW_BOARD_HISTORY_JSONL,
    current_csv: Annotated[
        Path | None,
        typer.Option("--current-csv", help="Optional current review board CSV."),
    ] = None,
    include_current_sheet: Annotated[
        bool,
        typer.Option(
            "--include-current-sheet/--no-include-current-sheet",
            help="Read the live Jibi sheet and include it in the calibration report.",
        ),
    ] = False,
    run_date: Annotated[
        str | None,
        typer.Option("--date", help="Calibration report date in YYYY-MM-DD."),
    ] = None,
    candidates_path: Annotated[
        Path,
        typer.Option("--candidates", help="Scored candidates JSONL for source metadata."),
    ] = paths.JIBI_SCORED_CANDIDATES_JSONL,
    spreadsheet_id: Annotated[
        str | None,
        typer.Option("--spreadsheet-id", help="Target Google spreadsheet id."),
    ] = None,
    sheet_name: Annotated[
        str | None,
        typer.Option("--sheet-name", help="Review board sheet name."),
    ] = None,
    markdown_path: Annotated[
        Path | None,
        typer.Option("--output-md", help="Markdown report path."),
    ] = None,
    json_path: Annotated[
        Path | None,
        typer.Option("--output-json", help="JSON report path."),
    ] = None,
) -> None:
    loaded = load_append_config()
    config = GoogleSheetAppendConfig(
        spreadsheet_id=spreadsheet_id or loaded.spreadsheet_id,
        target_sheet_name=sheet_name or loaded.target_sheet_name,
        sheet_schema=loaded.sheet_schema,
        dry_run=True,
        auth_mode=loaded.auth_mode,
        service_account_json_path=loaded.service_account_json_path,
    )
    try:
        outputs, summary = render_review_history_calibration(
            history_path=history_path,
            current_csv=current_csv,
            include_current_sheet=include_current_sheet,
            run_date=run_date,
            candidates_path=candidates_path,
            markdown_path=markdown_path,
            json_path=json_path,
            config=config,
        )
    except ValueError as exc:
        console.print(f"[red]Jibi feedback calibration failed: {exc}[/red]")
        raise typer.Exit(1) from exc
    console.print(
        "[green]Wrote Jibi feedback calibration report "
        f"for {summary['total_rows']} rows to {outputs.markdown_path} and "
        f"{outputs.json_path}.[/green]"
    )


if __name__ == "__main__":
    app()
