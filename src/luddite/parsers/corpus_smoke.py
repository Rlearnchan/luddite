"""Run parser smoke checks over the local raw corpus and write a Markdown report."""

from __future__ import annotations

from pathlib import Path
from statistics import mean
from typing import Annotated, Any

import typer

from luddite import paths
from luddite.parsers.build_corpus_manifest import build_and_write_manifest
from luddite.parsers.fetch_sheets import fetch_sheets
from luddite.parsers.parse_pptx import parse_directory as parse_pptx_directory
from luddite.parsers.parse_storylines import parse_directory as parse_storyline_directory

app = typer.Typer(no_args_is_help=False)


def _failed(records: list[dict[str, Any]]) -> list[str]:
    failed_files: list[str] = []
    for record in records:
        if record.get("parse_status") == "failed":
            failed_files.append(record.get("local_path") or record.get("file_name") or "unknown")
    return failed_files


def _format_failure_list(failures: list[str]) -> str:
    if not failures:
        return "- None\n"
    return "".join(f"- {failure}\n" for failure in failures)


def _write_report(
    output: Path,
    storyline_records: list[dict[str, Any]],
    ppt_records: list[dict[str, Any]],
    sheet_records: list[dict[str, Any]],
    manifest_items: list[dict[str, Any]],
) -> None:
    output.parent.mkdir(parents=True, exist_ok=True)

    storyline_url_counts = [record.get("url_count", 0) for record in storyline_records]
    total_storyline_urls = sum(storyline_url_counts)
    avg_storyline_urls = mean(storyline_url_counts) if storyline_url_counts else 0

    parsed_ppt_records = [
        record for record in ppt_records if record.get("parse_status") == "parsed"
    ]
    notes_success: str
    if not parsed_ppt_records:
        notes_success = "n/a"
    elif all(
        any(slide.get("notes") for slide in record.get("slides", []))
        for record in parsed_ppt_records
    ):
        notes_success = "yes"
    else:
        notes_success = "no"
    sheet_redactions = sum(1 for record in sheet_records if record.get("credential_risk"))
    validation_failures = [
        item for item in manifest_items if item.get("validation_status") != "passed"
    ]
    parse_failures = [
        *_failed(storyline_records),
        *_failed(ppt_records),
    ]

    lines: list[str] = [
        "# Parser Smoke Report",
        "",
        "## Storylines",
        "",
        f"- File count: {len(storyline_records)}",
        f"- URL total: {total_storyline_urls}",
        f"- URL average: {avg_storyline_urls:.2f}",
        "",
        "## PPT",
        "",
        f"- File count: {len(ppt_records)}",
        f"- Notes extraction success: {notes_success}",
        "",
        "| File | Slides | URL Count | Slides With URLs | Notes Extracted |",
        "|---|---:|---:|---:|---|",
    ]

    for record in ppt_records:
        notes_extracted = any(slide.get("notes") for slide in record.get("slides", []))
        lines.append(
            "| {file} | {slides} | {urls} | {slides_with_urls} | {notes} |".format(
                file=record.get("file_name", record.get("title", "unknown")),
                slides=record.get("slide_count", 0),
                urls=record.get("url_count", 0),
                slides_with_urls=record.get("slides_with_urls", 0),
                notes="yes" if notes_extracted else "no",
            )
        )

    lines.extend(
        [
            "",
            "## Sheets",
            "",
            f"- Row count: {len(sheet_records)}",
            f"- Redaction hits: {sheet_redactions}",
            "",
            "## Manifest",
            "",
            f"- Item count: {len(manifest_items)}",
            f"- Validation failures: {len(validation_failures)}",
            "",
            "## Parse Failures",
            "",
            _format_failure_list(parse_failures).rstrip(),
        ]
    )

    if validation_failures:
        lines.extend(["", "## Manifest Validation Failures", ""])
        for item in validation_failures:
            errors = "; ".join(item.get("validation_errors", []))
            lines.append(f"- {item.get('local_path', item.get('corpus_id'))}: {errors}")

    output.write_text("\n".join(lines) + "\n", encoding="utf-8")


def _write_notes(
    output: Path,
    storyline_records: list[dict[str, Any]],
    ppt_records: list[dict[str, Any]],
    sheet_records: list[dict[str, Any]],
    manifest_items: list[dict[str, Any]],
) -> None:
    output.parent.mkdir(parents=True, exist_ok=True)

    ppt_failures = _failed(ppt_records)
    storyline_failures = _failed(storyline_records)
    validation_failures = [
        item for item in manifest_items if item.get("validation_status") != "passed"
    ]
    sheet_redactions = [record for record in sheet_records if record.get("credential_risk")]

    lines = [
        "# Parser Smoke Notes",
        "",
        "## Current Run",
        "",
        f"- Storyline records: {len(storyline_records)}",
        f"- PPT records: {len(ppt_records)}",
        f"- Sheet rows: {len(sheet_records)}",
        f"- Manifest items: {len(manifest_items)}",
        f"- Sheet redaction hits: {len(sheet_redactions)}",
        f"- Parse failures: {len(storyline_failures) + len(ppt_failures)}",
        f"- Manifest validation failures: {len(validation_failures)}",
        "",
        "## Notes",
        "",
        "- This file is generated by `make corpus-smoke` from the same parser run as "
        "`parser_smoke_report.md`.",
        "- Raw corpus files remain local and ignored by git.",
        "- Sheet parsing is local export-first; Google Sheets API integration is still "
        "deferred.",
    ]

    if sheet_redactions:
        lines.extend(["", "## Redaction Rows", ""])
        for record in sheet_redactions[:20]:
            lines.append(
                "- {source} / {sheet} row {row_no}: {flags}".format(
                    source=record.get("source_file", "unknown"),
                    sheet=record.get("sheet_name", "unknown"),
                    row_no=record.get("row_no", "unknown"),
                    flags=", ".join(record.get("risk_flags", [])),
                )
            )

    if storyline_failures or ppt_failures:
        lines.extend(["", "## Parse Failures", ""])
        for failure in [*storyline_failures, *ppt_failures]:
            lines.append(f"- {failure}")

    if validation_failures:
        lines.extend(["", "## Manifest Validation Failures", ""])
        for item in validation_failures:
            errors = "; ".join(item.get("validation_errors", []))
            lines.append(f"- {item.get('local_path', item.get('corpus_id'))}: {errors}")

    output.write_text("\n".join(lines) + "\n", encoding="utf-8")


def run_corpus_smoke(report_path: Path = paths.PARSER_SMOKE_REPORT) -> Path:
    storyline_records = parse_storyline_directory(
        paths.STORYLINE_RAW_DIR,
        paths.STORYLINE_PARSED_JSONL,
    )
    ppt_records = parse_pptx_directory(paths.LATEST_PPT_RAW_DIR, paths.PPT_PARSED_JSONL)
    sheet_records = fetch_sheets(
        paths.SHEETS_RAW_DIR,
        paths.SHEETS_PARSED_JSONL,
        paths.SHEETS_PARSED_DIR,
    )
    manifest_items = build_and_write_manifest(paths.CORPUS_MANIFEST_JSONL)
    _write_report(report_path, storyline_records, ppt_records, sheet_records, manifest_items)
    _write_notes(
        paths.PARSER_SMOKE_NOTES,
        storyline_records,
        ppt_records,
        sheet_records,
        manifest_items,
    )
    return report_path


@app.callback(invoke_without_command=True)
def main(
    report: Annotated[
        Path,
        typer.Option("--report", help="Markdown parser smoke report path."),
    ] = paths.PARSER_SMOKE_REPORT,
) -> None:
    output = run_corpus_smoke(report)
    typer.echo(f"Wrote parser smoke report to {output}")


if __name__ == "__main__":
    app()
