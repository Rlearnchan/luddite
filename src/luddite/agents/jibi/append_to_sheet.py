"""Append jibi Daily Digest preview rows to the `jibi 후보` Google Sheet."""

from __future__ import annotations

import csv
import os
import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Annotated

import typer
from rich.console import Console

from luddite import paths
from luddite.integrations.google_sheets import (
    AppendResult,
    GoogleSheetsApiClient,
    GoogleSheetsClient,
)

app = typer.Typer(no_args_is_help=False)
console = Console()

LEGACY_25_SHEET_COLUMNS = [
    "digest_date",
    "collected_at",
    "last_seen_at",
    "jibi_id",
    "duplicate_key",
    "source_url_canonical",
    "rank",
    "status",
    "주제명",
    "링크",
    "출처",
    "source_type",
    "jibi_grade",
    "total_score",
    "recommended_action",
    "risk_level",
    "risk_flags",
    "why_interesting",
    "possible_expansions",
    "evidence_needed",
    "중복후보",
    "reviewer",
    "review_result",
    "promoted_to_topic_finding",
    "notes",
]
SLIDEABILITY_SHEET_COLUMNS = [
    "slideability_score",
    "slideability",
    "first_slide_idea",
    "likely_proof_object_types",
    "visual_risks",
]
SHEET_COLUMNS = [*LEGACY_25_SHEET_COLUMNS, *SLIDEABILITY_SHEET_COLUMNS]
REVIEW_RESULT_VALUES = {
    "",
    "keep",
    "promote",
    "needs_more_evidence",
    "editorial_review",
    "reject",
}
DAILY_PREVIEW_RE = re.compile(r"^\d{4}-\d{2}-\d{2}_sheet_append_preview\.csv$")


@dataclass(frozen=True)
class GoogleSheetAppendConfig:
    spreadsheet_id: str | None = None
    target_sheet_name: str = "jibi 후보"
    source_preview_csv: Path | None = None
    dry_run: bool = True
    create_sheet_if_missing: bool = True
    create_header_if_missing: bool = True
    skip_duplicates: bool = True
    duplicate_keys: tuple[str, ...] = ("duplicate_key", "source_url_canonical")
    styling_enabled: bool = False
    auth_mode: str = "service_account"
    service_account_json_path: str | None = None


@dataclass
class SheetAppendReport:
    spreadsheet_id: str | None
    sheet_name: str
    preview_csv: Path
    rows_read: int = 0
    rows_appended: int = 0
    duplicates_skipped: int = 0
    errors: list[str] = field(default_factory=list)
    dry_run: bool = True
    styling_applied: bool = False
    sheet_created: bool = False
    header_created: bool = False
    header_status: str = "not_checked"
    header_safe_to_update: bool = False
    header_reason: str = "not_checked"
    header_update_planned: bool = False
    header_updated: bool = False
    duplicate_keys: list[str] = field(default_factory=list)
    appended_range: AppendResult | None = None


def _parse_scalar(value: str) -> str | bool | None:
    value = value.strip()
    if value in {"", "null", "None"}:
        return None
    if value.lower() == "true":
        return True
    if value.lower() == "false":
        return False
    return value.strip('"').strip("'")


def _read_flat_yaml(path: Path) -> dict[str, str | bool | None]:
    if not path.exists():
        return {}
    parsed: dict[str, str | bool | None] = {}
    section: str | None = None
    for raw_line in path.read_text(encoding="utf-8").splitlines():
        line = raw_line.split("#", 1)[0].strip()
        if not line:
            continue
        if line.endswith(":") and not line.startswith("-"):
            section = line[:-1].strip()
            continue
        if ":" not in line:
            continue
        key, value = line.split(":", 1)
        key = key.strip()
        if section and raw_line.startswith("  "):
            key = f"{section}.{key}"
        parsed[key] = _parse_scalar(value)
    return parsed


def _env_bool(name: str) -> bool | None:
    value = os.environ.get(name)
    if value is None:
        return None
    return value.strip().lower() in {"1", "true", "yes", "y", "on"}


def _latest_preview_csv() -> Path | None:
    paths.DAILY_DIGEST_DIR.mkdir(parents=True, exist_ok=True)
    previews = sorted(
        [
            path
            for path in paths.DAILY_DIGEST_DIR.glob("*_sheet_append_preview.csv")
            if DAILY_PREVIEW_RE.match(path.name)
        ],
        reverse=True,
    )
    return previews[0] if previews else None


def _merge_config_values(*configs: dict[str, str | bool | None]) -> dict[str, str | bool | None]:
    merged: dict[str, str | bool | None] = {}
    for config in configs:
        for key, value in config.items():
            if value is not None:
                merged[key] = value
    return merged


def load_append_config(
    config_path: Path | None = None,
    local_config_path: Path = paths.GOOGLE_SHEETS_LOCAL_CONFIG_YAML,
) -> GoogleSheetAppendConfig:
    example_path = config_path or paths.GOOGLE_SHEETS_EXAMPLE_CONFIG_YAML
    raw = _merge_config_values(
        _read_flat_yaml(example_path),
        _read_flat_yaml(local_config_path),
    )
    preview_value = os.environ.get("LUDDITE_JIBI_PREVIEW_CSV") or raw.get("source_preview_csv")
    dry_run = _env_bool("LUDDITE_GOOGLE_SHEETS_DRY_RUN")
    styling_enabled = _env_bool("LUDDITE_GOOGLE_SHEETS_STYLING")
    return GoogleSheetAppendConfig(
        spreadsheet_id=os.environ.get("LUDDITE_GOOGLE_SPREADSHEET_ID")
        or _as_optional_str(raw.get("spreadsheet_id")),
        target_sheet_name=os.environ.get("LUDDITE_GOOGLE_TARGET_SHEET")
        or _as_optional_str(raw.get("target_sheet_name"))
        or "jibi 후보",
        source_preview_csv=Path(str(preview_value)) if preview_value else None,
        dry_run=bool(raw.get("dry_run_default", True)) if dry_run is None else dry_run,
        create_sheet_if_missing=bool(raw.get("create_sheet_if_missing", True)),
        create_header_if_missing=bool(raw.get("create_header_if_missing", True)),
        skip_duplicates=bool(raw.get("skip_duplicates", True)),
        styling_enabled=(
            bool(raw.get("styling.enabled", False)) if styling_enabled is None else styling_enabled
        ),
        auth_mode=os.environ.get("LUDDITE_GOOGLE_AUTH_MODE")
        or _as_optional_str(raw.get("auth_mode"))
        or "service_account",
        service_account_json_path=os.environ.get("LUDDITE_GOOGLE_SERVICE_ACCOUNT_JSON")
        or os.environ.get("GOOGLE_APPLICATION_CREDENTIALS")
        or _as_optional_str(raw.get("service_account_json_path")),
    )


def _as_optional_str(value: object) -> str | None:
    if value is None:
        return None
    text = str(value).strip()
    return text or None


def read_preview_rows(preview_csv: Path) -> list[dict[str, str]]:
    with preview_csv.open(encoding="utf-8-sig", newline="") as source:
        rows = list(csv.DictReader(source))
    missing = [column for column in SHEET_COLUMNS if column not in (rows[0].keys() if rows else [])]
    if rows and missing:
        raise ValueError(f"Preview CSV missing required columns: {', '.join(missing)}")
    return rows


def _header_status(existing_values: list[list[str]]) -> str:
    if not existing_values:
        return "missing"
    header = existing_values[0]
    if header == SHEET_COLUMNS:
        return "ok"
    if header == LEGACY_25_SHEET_COLUMNS:
        return "legacy_25"
    return "unsafe_mismatch"


def _header_reason(status: str) -> str:
    return {
        "ok": "ok",
        "missing": "missing_empty_sheet",
        "legacy_25": "legacy_25_known_schema",
        "unsafe_mismatch": "unknown_header_shape",
    }.get(status, "unknown")


def _header_safe_to_update(status: str) -> bool:
    return status in {"missing", "legacy_25", "ok"}


def _unsafe_header_error() -> str:
    return (
        "Target sheet header does not match the canonical schema or the known "
        "legacy 25-column schema; refusing to update header or append rows."
    )


def _existing_duplicate_values(existing_values: list[list[str]]) -> tuple[set[str], set[str]]:
    if not existing_values:
        return set(), set()
    header = existing_values[0]
    duplicate_key_index = _column_index(header, "duplicate_key")
    source_url_index = _column_index(header, "source_url_canonical")
    duplicate_keys: set[str] = set()
    source_urls: set[str] = set()
    for row in existing_values[1:]:
        if (
            duplicate_key_index is not None
            and duplicate_key_index < len(row)
            and row[duplicate_key_index]
        ):
            duplicate_keys.add(row[duplicate_key_index])
        if source_url_index is not None and source_url_index < len(row) and row[source_url_index]:
            source_urls.add(row[source_url_index])
    return duplicate_keys, source_urls


def _column_index(header: list[str], column: str) -> int | None:
    try:
        return header.index(column)
    except ValueError:
        return None


def _sheet_row(row: dict[str, str]) -> list[str]:
    prepared = dict(row)
    prepared["status"] = prepared.get("status") or "new"
    prepared["출처"] = prepared.get("출처") or "jibi"
    review_result = prepared.get("review_result", "")
    if review_result not in REVIEW_RESULT_VALUES:
        prepared["review_result"] = ""
    return [prepared.get(column, "") for column in SHEET_COLUMNS]


def append_jibi_sheet(
    *,
    config: GoogleSheetAppendConfig,
    client: GoogleSheetsClient | None = None,
    report_path: Path | None = None,
) -> SheetAppendReport:
    preview_csv = config.source_preview_csv or _latest_preview_csv()
    if preview_csv is None:
        raise FileNotFoundError("No jibi sheet preview CSV found.")
    preview_csv = preview_csv.resolve()
    rows = read_preview_rows(preview_csv)
    report = SheetAppendReport(
        spreadsheet_id=config.spreadsheet_id,
        sheet_name=config.target_sheet_name,
        preview_csv=preview_csv,
        rows_read=len(rows),
        dry_run=config.dry_run,
    )

    if not config.spreadsheet_id and not config.dry_run:
        report.errors.append("spreadsheet_id is required when dry_run is false.")
        write_append_report(report_path or default_report_path(preview_csv), report)
        return report

    existing_values: list[list[str]] = []
    sheet_id: int | None = None
    if client and config.spreadsheet_id:
        sheet_id = client.get_sheet_id(config.spreadsheet_id, config.target_sheet_name)
        if sheet_id is None:
            report.sheet_created = True
            if not config.create_sheet_if_missing:
                report.errors.append(f"Target sheet does not exist: {config.target_sheet_name}")
            elif not config.dry_run:
                sheet_id = client.create_sheet(config.spreadsheet_id, config.target_sheet_name)
        if sheet_id is not None:
            existing_values = client.get_values(config.spreadsheet_id, config.target_sheet_name)

    header_status = _header_status(existing_values)
    report.header_status = header_status
    report.header_reason = _header_reason(header_status)
    report.header_safe_to_update = _header_safe_to_update(header_status)
    if header_status == "unsafe_mismatch":
        report.errors.append(_unsafe_header_error())
        write_append_report(report_path or default_report_path(preview_csv), report)
        return report
    if header_status != "ok":
        report.header_created = True
        if not config.create_header_if_missing:
            report.errors.append(
                "Target sheet header is missing or does not match expected columns."
            )
            write_append_report(report_path or default_report_path(preview_csv), report)
            return report
        elif config.dry_run:
            report.header_update_planned = True
            if header_status == "legacy_25":
                report.header_status = "legacy_25_upgrade_planned"
        elif client and config.spreadsheet_id and not config.dry_run:
            client.update_values(
                config.spreadsheet_id,
                config.target_sheet_name,
                "A1",
                [SHEET_COLUMNS],
            )
            existing_values = [SHEET_COLUMNS, *existing_values[1:]]
            report.header_updated = True
            if header_status == "legacy_25":
                report.header_status = "legacy_25_upgraded"

    duplicate_keys, source_urls = _existing_duplicate_values(existing_values)
    rows_to_append: list[list[str]] = []
    seen_in_input: set[str] = set()
    seen_urls_in_input: set[str] = set()
    for row in rows:
        duplicate_key = row.get("duplicate_key", "")
        source_url = row.get("source_url_canonical", "")
        duplicate_key_enabled = "duplicate_key" in config.duplicate_keys
        source_url_enabled = "source_url_canonical" in config.duplicate_keys
        is_duplicate = config.skip_duplicates and (
            (duplicate_key_enabled and duplicate_key and duplicate_key in duplicate_keys)
            or (source_url_enabled and source_url and source_url in source_urls)
            or (duplicate_key_enabled and duplicate_key and duplicate_key in seen_in_input)
            or (source_url_enabled and source_url and source_url in seen_urls_in_input)
        )
        if is_duplicate:
            report.duplicates_skipped += 1
            report.duplicate_keys.append(duplicate_key or source_url)
            continue
        rows_to_append.append(_sheet_row(row))
        if duplicate_key:
            seen_in_input.add(duplicate_key)
        if source_url:
            seen_urls_in_input.add(source_url)

    report.rows_appended = len(rows_to_append)
    if client and config.spreadsheet_id and rows_to_append and not config.dry_run:
        result = client.append_rows(config.spreadsheet_id, config.target_sheet_name, rows_to_append)
        report.appended_range = result
        if (
            config.styling_enabled
            and sheet_id is not None
            and result.start_row is not None
            and result.end_row is not None
        ):
            client.format_rows(
                config.spreadsheet_id,
                sheet_id,
                result.start_row,
                result.end_row,
            )
            report.styling_applied = True

    write_append_report(report_path or default_report_path(preview_csv), report)
    return report


def default_report_path(preview_csv: Path) -> Path:
    stem = preview_csv.stem.replace("_sheet_append_preview", "")
    return paths.REPORTS_DIR / f"jibi_sheet_append_{stem}.md"


def write_append_report(path: Path, report: SheetAppendReport) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    lines = [
        "# jibi Google Sheet Append Report",
        "",
        f"- Target spreadsheet id: `{report.spreadsheet_id or ''}`",
        f"- Target sheet name: `{report.sheet_name}`",
        f"- Input preview csv: `{report.preview_csv}`",
        f"- Rows read: {report.rows_read}",
        f"- Rows appended: {report.rows_appended}",
        f"- Duplicates skipped: {report.duplicates_skipped}",
        f"- Dry run: {report.dry_run}",
        f"- Styling applied: {report.styling_applied}",
        f"- Sheet created: {report.sheet_created}",
        f"- Header status: `{report.header_status}`",
        f"- Header safe to update: {report.header_safe_to_update}",
        f"- Header reason: `{report.header_reason}`",
        f"- Header update planned: {report.header_update_planned}",
        f"- Header updated: {report.header_updated}",
        f"- Header created: {report.header_created}",
        f"- Errors: {len(report.errors)}",
        "",
        "## Duplicate keys skipped",
        "",
    ]
    if report.duplicate_keys:
        lines.extend(f"- `{key}`" for key in report.duplicate_keys)
    else:
        lines.append("- none")
    lines.extend(["", "## Errors", ""])
    if report.errors:
        lines.extend(f"- {error}" for error in report.errors)
    else:
        lines.append("- none")
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def _build_default_client(config: GoogleSheetAppendConfig) -> GoogleSheetsClient | None:
    if not config.spreadsheet_id:
        return None
    return GoogleSheetsApiClient(
        credentials_path=config.service_account_json_path,
        auth_mode=config.auth_mode,
    )


@app.callback(invoke_without_command=True)
def main(
    preview_csv: Annotated[
        Path | None,
        typer.Option("--preview-csv", help="Sheet preview CSV to append."),
    ] = None,
    spreadsheet_id: Annotated[
        str | None,
        typer.Option("--spreadsheet-id", help="Target Google spreadsheet id."),
    ] = None,
    sheet_name: Annotated[
        str | None,
        typer.Option("--sheet-name", help="Target staging sheet name."),
    ] = None,
    dry_run: Annotated[
        bool | None,
        typer.Option("--dry-run/--no-dry-run", help="Report planned changes without append."),
    ] = None,
    styling: Annotated[
        bool | None,
        typer.Option("--styling/--no-styling", help="Apply background styling to appended rows."),
    ] = None,
) -> None:
    loaded = load_append_config()
    config = GoogleSheetAppendConfig(
        spreadsheet_id=spreadsheet_id or loaded.spreadsheet_id,
        target_sheet_name=sheet_name or loaded.target_sheet_name,
        source_preview_csv=preview_csv or loaded.source_preview_csv,
        dry_run=loaded.dry_run if dry_run is None else dry_run,
        create_sheet_if_missing=loaded.create_sheet_if_missing,
        create_header_if_missing=loaded.create_header_if_missing,
        skip_duplicates=loaded.skip_duplicates,
        duplicate_keys=loaded.duplicate_keys,
        styling_enabled=loaded.styling_enabled if styling is None else styling,
        auth_mode=loaded.auth_mode,
        service_account_json_path=loaded.service_account_json_path,
    )
    client = _build_default_client(config)
    report = append_jibi_sheet(config=config, client=client)
    console.print(
        "[green]jibi sheet append report ready "
        f"(read={report.rows_read}, append={report.rows_appended}, "
        f"duplicates={report.duplicates_skipped}, dry_run={report.dry_run}).[/green]"
    )
    if report.errors:
        raise typer.Exit(1)


if __name__ == "__main__":
    app()
