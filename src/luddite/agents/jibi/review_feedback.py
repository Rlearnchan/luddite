"""Read-only summaries for the Jibi bundle review board."""

from __future__ import annotations

import csv
import json
import re
from collections import Counter
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Annotated, Any

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

app = typer.Typer(no_args_is_help=False)
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
            "date": row.get("날짜", ""),
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
        value = str(row.get("날짜", "")).strip()
        if value:
            return value
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
    required_columns = [column for column in BUNDLE_REVIEW_SHEET_COLUMNS if column != "점수"]
    missing = [column for column in required_columns if rows and column not in rows[0]]
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


if __name__ == "__main__":
    app()
