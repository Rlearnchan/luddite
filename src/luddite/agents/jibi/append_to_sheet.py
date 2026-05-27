"""Append jibi Daily Digest preview rows to the `Jibi` Google Sheet."""

from __future__ import annotations

import csv
import json
import os
import re
from dataclasses import dataclass, field
from datetime import UTC, datetime
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
BUNDLE_REVIEW_SHEET_COLUMNS = [
    "일시",
    "제목",
    "점수",
    "메인 링크",
    "서브 링크",
    "설명",
    "참고",
    "리뷰-성원",
    "리뷰-동찬",
    "리뷰-형찬",
    "ID",
]
LEGACY_BUNDLE_REVIEW_SHEET_COLUMNS = [
    column for column in BUNDLE_REVIEW_SHEET_COLUMNS if column != "참고"
]
REVIEWER_COLUMNS = ["리뷰-성원", "리뷰-동찬", "리뷰-형찬"]
REVIEW_BOARD_INTRO_TITLE = "안녕하세요. Jibi입니다."
CANDIDATE_SHEET_SCHEMA = "candidate"
BUNDLE_REVIEW_SHEET_SCHEMA = "bundle_review"
VALID_SHEET_SCHEMAS = {CANDIDATE_SHEET_SCHEMA, BUNDLE_REVIEW_SHEET_SCHEMA}
REVIEW_RESULT_VALUES = {
    "",
    "keep",
    "promote",
    "needs_more_evidence",
    "editorial_review",
    "merge",
    "evidence_only",
    "needs_external_sources",
    "reject",
}
DAILY_PREVIEW_RE = re.compile(r"^\d{4}-\d{2}-\d{2}_sheet_append_preview\.csv$")
BUNDLE_REVIEW_PREVIEW_RE = re.compile(r"^\d{4}-\d{2}-\d{2}_bundle_review_sheet\.csv$")


@dataclass(frozen=True)
class GoogleSheetAppendConfig:
    spreadsheet_id: str | None = None
    target_sheet_name: str = "Jibi"
    source_preview_csv: Path | None = None
    sheet_schema: str = CANDIDATE_SHEET_SCHEMA
    dry_run: bool = True
    replace_existing: bool = False
    create_sheet_if_missing: bool = True
    create_header_if_missing: bool = True
    skip_duplicates: bool = True
    duplicate_keys: tuple[str, ...] = ("duplicate_key", "source_url_canonical")
    styling_enabled: bool = False
    allow_review_overwrite: bool = False
    review_snapshot_dir: Path = paths.REPORTS_DIR
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
    sheet_schema: str = CANDIDATE_SHEET_SCHEMA
    replace_existing: bool = False
    styling_applied: bool = False
    sheet_created: bool = False
    header_created: bool = False
    header_status: str = "not_checked"
    header_safe_to_update: bool = False
    header_reason: str = "not_checked"
    header_update_planned: bool = False
    header_updated: bool = False
    sheet_replace_planned: bool = False
    sheet_replaced: bool = False
    duplicate_keys: list[str] = field(default_factory=list)
    appended_range: AppendResult | None = None
    review_comments_found: bool = False
    review_comment_cells: int = 0
    review_overwrite_allowed: bool = False
    review_snapshot_path: Path | None = None
    review_history_archive_path: Path | None = None


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


def _normalize_sheet_schema(value: str | None) -> str:
    schema = (value or CANDIDATE_SHEET_SCHEMA).strip().replace("-", "_")
    if schema not in VALID_SHEET_SCHEMAS:
        raise ValueError(
            "sheet schema must be one of: " + ", ".join(sorted(VALID_SHEET_SCHEMAS))
        )
    return schema


def _schema_columns(sheet_schema: str) -> list[str]:
    schema = _normalize_sheet_schema(sheet_schema)
    if schema == BUNDLE_REVIEW_SHEET_SCHEMA:
        return BUNDLE_REVIEW_SHEET_COLUMNS
    return SHEET_COLUMNS


def _schema_legacy_columns(sheet_schema: str) -> list[str] | None:
    schema = _normalize_sheet_schema(sheet_schema)
    if schema == CANDIDATE_SHEET_SCHEMA:
        return LEGACY_25_SHEET_COLUMNS
    if schema == BUNDLE_REVIEW_SHEET_SCHEMA:
        return LEGACY_BUNDLE_REVIEW_SHEET_COLUMNS
    return None


def _schema_default_duplicate_keys(sheet_schema: str) -> tuple[str, ...]:
    schema = _normalize_sheet_schema(sheet_schema)
    if schema == BUNDLE_REVIEW_SHEET_SCHEMA:
        return ("ID",)
    return ("duplicate_key", "source_url_canonical")


def _latest_preview_csv(sheet_schema: str = CANDIDATE_SHEET_SCHEMA) -> Path | None:
    paths.DAILY_DIGEST_DIR.mkdir(parents=True, exist_ok=True)
    pattern = (
        BUNDLE_REVIEW_PREVIEW_RE
        if _normalize_sheet_schema(sheet_schema) == BUNDLE_REVIEW_SHEET_SCHEMA
        else DAILY_PREVIEW_RE
    )
    glob_pattern = (
        "*_bundle_review_sheet.csv"
        if _normalize_sheet_schema(sheet_schema) == BUNDLE_REVIEW_SHEET_SCHEMA
        else "*_sheet_append_preview.csv"
    )
    previews = sorted(
        [
            path
            for path in paths.DAILY_DIGEST_DIR.glob(glob_pattern)
            if pattern.match(path.name)
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
    allow_review_overwrite = _env_bool("JIBI_ALLOW_REVIEW_OVERWRITE")
    sheet_schema = _normalize_sheet_schema(
        os.environ.get("LUDDITE_JIBI_SHEET_SCHEMA")
        or _as_optional_str(raw.get("sheet_schema"))
    )
    replace_existing = _env_bool("LUDDITE_JIBI_REPLACE_EXISTING")
    return GoogleSheetAppendConfig(
        spreadsheet_id=os.environ.get("LUDDITE_GOOGLE_SPREADSHEET_ID")
        or _as_optional_str(raw.get("spreadsheet_id")),
        target_sheet_name=os.environ.get("LUDDITE_GOOGLE_TARGET_SHEET")
        or _as_optional_str(raw.get("target_sheet_name"))
        or "Jibi",
        source_preview_csv=Path(str(preview_value)) if preview_value else None,
        sheet_schema=sheet_schema,
        dry_run=bool(raw.get("dry_run_default", True)) if dry_run is None else dry_run,
        replace_existing=(
            bool(raw.get("replace_existing", False))
            if replace_existing is None
            else replace_existing
        ),
        create_sheet_if_missing=bool(raw.get("create_sheet_if_missing", True)),
        create_header_if_missing=bool(raw.get("create_header_if_missing", True)),
        skip_duplicates=bool(raw.get("skip_duplicates", True)),
        duplicate_keys=_schema_default_duplicate_keys(sheet_schema),
        styling_enabled=(
            bool(raw.get("styling.enabled", False)) if styling_enabled is None else styling_enabled
        ),
        allow_review_overwrite=(
            bool(raw.get("allow_review_overwrite", False))
            if allow_review_overwrite is None
            else allow_review_overwrite
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


def read_preview_rows(
    preview_csv: Path,
    *,
    sheet_schema: str = CANDIDATE_SHEET_SCHEMA,
) -> list[dict[str, str]]:
    with preview_csv.open(encoding="utf-8-sig", newline="") as source:
        rows = list(csv.DictReader(source))
    columns = _schema_columns(sheet_schema)
    missing = [column for column in columns if column not in (rows[0].keys() if rows else [])]
    if rows and missing:
        raise ValueError(f"Preview CSV missing required columns: {', '.join(missing)}")
    return rows


def _header_status(
    existing_values: list[list[str]],
    *,
    expected_columns: list[str],
    legacy_columns: list[str] | None,
) -> str:
    if not existing_values:
        return "missing"
    header_index = _find_exact_header_row(existing_values, expected_columns)
    if header_index is not None:
        return "ok"
    if legacy_columns and _find_exact_header_row(existing_values, legacy_columns) is not None:
        return "legacy_25"
    header = existing_values[0]
    if header == expected_columns:
        return "ok"
    if legacy_columns and header == legacy_columns:
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


def _existing_duplicate_values(
    existing_values: list[list[str]],
    duplicate_columns: tuple[str, ...],
) -> dict[str, set[str]]:
    values = {column: set() for column in duplicate_columns}
    if not existing_values:
        return values
    header_index = _find_header_row_containing(existing_values, list(duplicate_columns))
    header_index = 0 if header_index is None else header_index
    header = existing_values[header_index]
    column_indexes = {
        column: _column_index(header, column)
        for column in duplicate_columns
    }
    for row in existing_values[header_index + 1 :]:
        for column, column_index in column_indexes.items():
            if column_index is not None and column_index < len(row) and row[column_index]:
                values[column].add(row[column_index])
    return values


def _normalize_header_cells(row: list[str]) -> list[str]:
    return [str(value).strip() for value in row]


def _find_exact_header_row(
    values: list[list[str]],
    expected_columns: list[str],
) -> int | None:
    expected = [str(value).strip() for value in expected_columns]
    for index, row in enumerate(values):
        cells = _normalize_header_cells(row)
        if cells[: len(expected)] == expected:
            return index
    return None


def _find_header_row_containing(
    values: list[list[str]],
    columns: list[str],
) -> int | None:
    required = {str(value).strip() for value in columns}
    for index, row in enumerate(values):
        cells = set(_normalize_header_cells(row))
        if required.issubset(cells):
            return index
    return None


def _find_bundle_review_header_row(values: list[list[str]]) -> int | None:
    current = _find_exact_header_row(values, BUNDLE_REVIEW_SHEET_COLUMNS)
    if current is not None:
        return current
    return _find_exact_header_row(values, LEGACY_BUNDLE_REVIEW_SHEET_COLUMNS)


def _column_index(header: list[str], column: str) -> int | None:
    try:
        return header.index(column)
    except ValueError:
        return None


def _sheet_row(row: dict[str, str], *, columns: list[str]) -> list[str]:
    prepared = dict(row)
    prepared["status"] = prepared.get("status") or "new"
    prepared["review_status"] = prepared.get("review_status") or "new"
    prepared["출처"] = prepared.get("출처") or "jibi"
    review_result = prepared.get("review_result", "")
    if review_result not in REVIEW_RESULT_VALUES:
        prepared["review_result"] = ""
    return [prepared.get(column, "") for column in columns]


def _preview_date(preview_csv: Path) -> str:
    match = re.match(r"^(\d{4}-\d{2}-\d{2})", preview_csv.name)
    if match:
        return match.group(1)
    return datetime.now(UTC).date().isoformat()


def _review_board_theme_sentence(rows: list[dict[str, str]]) -> str:
    text = " ".join(
        str(row.get("제목") or row.get("설명") or "")
        for row in rows
    )
    themes: list[str] = []
    if "AI" in text or "인공지능" in text:
        themes.append("AI가 신뢰·노동·공공 현장으로 들어오는 장면")
    if any(keyword in text for keyword in ["월급", "돈", "자금", "은행", "금융"]):
        themes.append("돈의 흐름과 생활경제")
    if any(keyword in text for keyword in ["날씨", "전기요금", "중동", "해외"]):
        themes.append("해외 이슈가 일상 가격으로 번지는 경로")
    if any(keyword in text for keyword in ["배달", "로봇", "경력", "일자리"]):
        themes.append("일하는 방식과 현장 자동화")
    if not themes:
        themes.append("오늘 수집된 후보 중 방송 소재 가능성이 있는 항목")
    return "오늘은 " + ", ".join(themes[:3]) + " 관련 후보를 함께 올렸습니다."


def _bundle_review_intro_rows(rows: list[dict[str, str]]) -> list[list[str]]:
    count = len(rows)
    return [
        [REVIEW_BOARD_INTRO_TITLE],
        [_review_board_theme_sentence(rows)],
        [
            (
                f"아래 {count}개 후보는 완성안이 아니라, 단독 seed인지 근거자료인지 "
                "또는 다른 후보와 묶어야 하는지 확인하기 위한 리뷰 보드입니다."
            )
        ],
        [
            (
                "좋으면 왜 좋은지, 약하면 왜 약한지, 살리려면 무엇을 더 찾아야 "
                "하는지 리뷰 칸에 한 줄씩 남겨주세요."
            )
        ],
    ]


def _bundle_review_header_row_number(rows: list[dict[str, str]]) -> int:
    return len(_bundle_review_intro_rows(rows)) + 2


def _bundle_review_sheet_values(
    rows: list[dict[str, str]],
    rows_to_write: list[list[str]],
    columns: list[str],
) -> tuple[list[list[str]], int, int]:
    intro_rows = _bundle_review_intro_rows(rows)
    header_row_number = len(intro_rows) + 2
    values = [*intro_rows, [""], columns, *rows_to_write]
    return values, header_row_number, len(intro_rows)


def _review_comment_cells(existing_values: list[list[str]]) -> list[dict[str, str | int]]:
    if not existing_values:
        return []
    header_index = _find_bundle_review_header_row(existing_values)
    if header_index is None:
        return []
    header = existing_values[header_index]
    column_indexes = {
        column: _column_index(header, column)
        for column in REVIEWER_COLUMNS
    }
    title_index = _column_index(header, "제목")
    id_index = _column_index(header, "ID")
    cells: list[dict[str, str | int]] = []
    for row_number, row in enumerate(existing_values[header_index + 1 :], start=header_index + 2):
        title = row[title_index] if title_index is not None and title_index < len(row) else ""
        review_id = row[id_index] if id_index is not None and id_index < len(row) else ""
        for column, column_index in column_indexes.items():
            if column_index is None or column_index >= len(row):
                continue
            value = row[column_index].strip()
            if value:
                cells.append(
                    {
                        "row": row_number,
                        "column": column,
                        "title": title,
                        "id": review_id,
                        "value": value,
                    }
                )
    return cells


def _snapshot_rows(existing_values: list[list[str]]) -> list[dict[str, object]]:
    if not existing_values:
        return []
    header_index = _find_bundle_review_header_row(existing_values)
    if header_index is None:
        return []
    header = existing_values[header_index]
    indexes = {column: _column_index(header, column) for column in BUNDLE_REVIEW_SHEET_COLUMNS}
    rows: list[dict[str, object]] = []
    for row_number, row in enumerate(existing_values[header_index + 1 :], start=header_index + 2):
        if not any(str(value).strip() for value in row):
            continue
        item: dict[str, object] = {"row": row_number}
        for column in BUNDLE_REVIEW_SHEET_COLUMNS:
            column_index = indexes.get(column)
            item[column] = (
                row[column_index]
                if column_index is not None and column_index < len(row)
                else ""
            )
        rows.append(item)
    return rows


def _fingerprint_from_review_id(value: str) -> str:
    text = value.strip()
    if ":" in text:
        return text.rsplit(":", 1)[1]
    return text


def _review_board_metadata_paths(preview_csv: Path) -> list[Path]:
    return sorted(preview_csv.parent.glob("*_bundle_review_sheet_metadata.json"))


def _load_review_board_metadata_index(preview_csv: Path) -> dict[str, dict[str, object]]:
    index: dict[str, dict[str, object]] = {}
    for path in _review_board_metadata_paths(preview_csv):
        try:
            payload = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            continue
        for row in payload.get("rows", []):
            if not isinstance(row, dict):
                continue
            keys = {
                str(row.get("ID") or "").strip(),
                str(row.get("review_item_id") or "").strip(),
                str(row.get("story_bundle_id") or "").strip(),
                str(row.get("story_fingerprint") or "").strip(),
            }
            for key in keys:
                if key:
                    index.setdefault(key, row)
    return index


def _enrich_snapshot_row(
    row: dict[str, object],
    metadata_index: dict[str, dict[str, object]],
) -> None:
    review_id = str(row.get("ID") or "").strip()
    fingerprint = str(row.get("story_fingerprint") or "").strip()
    metadata = metadata_index.get(review_id) or metadata_index.get(fingerprint) or {}
    for key in [
        "review_item_id",
        "registered_at",
        "run_date",
        "story_bundle_id",
        "title",
        "score",
        "total_score",
        "main_link",
        "sub_links",
        "source",
        "source_id",
        "source_role",
        "source_role_class",
        "seed_type",
        "bundle_type",
        "suggested_operator_action",
        "primary_candidate_id",
        "supporting_candidate_ids",
        "evidence_candidate_ids",
        "candidate_count",
    ]:
        value = metadata.get(key)
        if value not in (None, "", []):
            row[key] = value


def _append_review_board_history(payload: dict[str, object], output_dir: Path) -> Path:
    archive_path = output_dir / "jibi_review_board_history.jsonl"
    output_dir.mkdir(parents=True, exist_ok=True)
    with archive_path.open("a", encoding="utf-8") as output:
        output.write(json.dumps(payload, ensure_ascii=False, sort_keys=True) + "\n")
    return archive_path


def _write_review_board_snapshot(
    *,
    preview_csv: Path,
    sheet_name: str,
    existing_values: list[list[str]],
    output_dir: Path,
) -> tuple[Path, Path]:
    output_dir.mkdir(parents=True, exist_ok=True)
    timestamp = datetime.now(UTC).strftime("%Y-%m-%d_%H%M%S_%f")
    snapshot_path = output_dir / f"jibi_review_board_snapshot_{timestamp}.json"
    metadata_index = _load_review_board_metadata_index(preview_csv)
    rows = _snapshot_rows(existing_values)
    for row in rows:
        review_id = str(row.get("ID") or "")
        row["story_fingerprint"] = _fingerprint_from_review_id(review_id)
        _enrich_snapshot_row(row, metadata_index)
    payload = {
        "created_at": datetime.now(UTC).isoformat(),
        "run_date": _preview_date(preview_csv),
        "sheet_name": sheet_name,
        "preview_csv": str(preview_csv),
        "metadata_sidecars": [str(path) for path in _review_board_metadata_paths(preview_csv)],
        "reviewer_columns": REVIEWER_COLUMNS,
        "rows": rows,
    }
    snapshot_path.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    return snapshot_path, _append_review_board_history(payload, output_dir)


def append_jibi_sheet(
    *,
    config: GoogleSheetAppendConfig,
    client: GoogleSheetsClient | None = None,
    report_path: Path | None = None,
) -> SheetAppendReport:
    sheet_schema = _normalize_sheet_schema(config.sheet_schema)
    columns = _schema_columns(sheet_schema)
    preview_csv = config.source_preview_csv or _latest_preview_csv(sheet_schema)
    if preview_csv is None:
        raise FileNotFoundError("No jibi sheet preview CSV found.")
    preview_csv = preview_csv.resolve()
    rows = read_preview_rows(preview_csv, sheet_schema=sheet_schema)
    report = SheetAppendReport(
        spreadsheet_id=config.spreadsheet_id,
        sheet_name=config.target_sheet_name,
        preview_csv=preview_csv,
        rows_read=len(rows),
        dry_run=config.dry_run,
        sheet_schema=sheet_schema,
        replace_existing=config.replace_existing,
        review_overwrite_allowed=config.allow_review_overwrite,
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

    header_status = _header_status(
        existing_values,
        expected_columns=columns,
        legacy_columns=_schema_legacy_columns(sheet_schema),
    )
    report.header_status = header_status
    report.header_reason = _header_reason(header_status)
    report.header_safe_to_update = _header_safe_to_update(header_status) or config.replace_existing
    if header_status == "unsafe_mismatch" and not config.replace_existing:
        report.errors.append(_unsafe_header_error())
        write_append_report(report_path or default_report_path(preview_csv), report)
        return report
    if config.replace_existing:
        rows_to_write = [_sheet_row(row, columns=columns) for row in rows]
        report.rows_appended = len(rows_to_write)
        report.sheet_replace_planned = True
        report.header_update_planned = config.dry_run
        report.header_created = header_status != "ok"
        if sheet_schema == BUNDLE_REVIEW_SHEET_SCHEMA:
            comment_cells = _review_comment_cells(existing_values)
            report.review_comment_cells = len(comment_cells)
            report.review_comments_found = bool(comment_cells)
            if existing_values and len(existing_values) > 1 and not config.dry_run:
                snapshot_path, archive_path = _write_review_board_snapshot(
                    preview_csv=preview_csv,
                    sheet_name=config.target_sheet_name,
                    existing_values=existing_values,
                    output_dir=config.review_snapshot_dir,
                )
                report.review_snapshot_path = snapshot_path
                report.review_history_archive_path = archive_path
            if comment_cells and not config.dry_run and not config.allow_review_overwrite:
                report.errors.append(
                    "Existing Jibi review comments found; refusing to replace the "
                    "bundle review board. Set JIBI_ALLOW_REVIEW_OVERWRITE=1 or pass "
                    "--allow-review-overwrite after snapshotting/reviewing the board."
                )
                write_append_report(report_path or default_report_path(preview_csv), report)
                return report
        if header_status == "unsafe_mismatch":
            report.header_status = "unsafe_mismatch_replace_planned"
            report.header_reason = "replace_existing_explicit"
        if client and config.spreadsheet_id and not config.dry_run:
            client.clear_values(config.spreadsheet_id, config.target_sheet_name)
            values_to_write = [columns, *rows_to_write]
            header_row_number = 1
            intro_row_count = 0
            if sheet_schema == BUNDLE_REVIEW_SHEET_SCHEMA:
                values_to_write, header_row_number, intro_row_count = (
                    _bundle_review_sheet_values(rows, rows_to_write, columns)
                )
            client.update_values(
                config.spreadsheet_id,
                config.target_sheet_name,
                "A1",
                values_to_write,
            )
            report.sheet_replaced = True
            report.header_updated = True
            report.header_update_planned = False
            report.appended_range = AppendResult(
                start_row=header_row_number + 1 if rows_to_write else None,
                end_row=(header_row_number + len(rows_to_write)) if rows_to_write else None,
            )
            if sheet_schema == BUNDLE_REVIEW_SHEET_SCHEMA and sheet_id is not None:
                client.format_review_board(
                    config.spreadsheet_id,
                    sheet_id,
                    row_count=len(values_to_write),
                    column_count=len(columns),
                    header_row=header_row_number,
                    intro_row_count=intro_row_count,
                )
                report.styling_applied = True
            if (
                sheet_schema != BUNDLE_REVIEW_SHEET_SCHEMA
                and config.styling_enabled
                and sheet_id is not None
                and rows_to_write
            ):
                client.format_rows(
                    config.spreadsheet_id,
                    sheet_id,
                    2,
                    len(rows_to_write) + 1,
                )
                report.styling_applied = True
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
                [columns],
            )
            existing_values = [columns, *existing_values[1:]]
            report.header_updated = True
            if header_status == "legacy_25":
                report.header_status = "legacy_25_upgraded"

    existing_duplicate_values = _existing_duplicate_values(
        existing_values,
        config.duplicate_keys,
    )
    rows_to_append: list[list[str]] = []
    seen_in_input = {column: set() for column in config.duplicate_keys}
    for row in rows:
        duplicate_values = [
            (column, row.get(column, ""))
            for column in config.duplicate_keys
            if row.get(column, "")
        ]
        is_duplicate = config.skip_duplicates and any(
            value in existing_duplicate_values.get(column, set())
            or value in seen_in_input.get(column, set())
            for column, value in duplicate_values
        )
        if is_duplicate:
            report.duplicates_skipped += 1
            report.duplicate_keys.append(
                next((value for _column, value in duplicate_values if value), "")
            )
            continue
        rows_to_append.append(_sheet_row(row, columns=columns))
        for column, value in duplicate_values:
            seen_in_input.setdefault(column, set()).add(value)

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
        f"- Sheet schema: `{report.sheet_schema}`",
        f"- Rows read: {report.rows_read}",
        f"- Rows appended: {report.rows_appended}",
        f"- Duplicates skipped: {report.duplicates_skipped}",
        f"- Dry run: {report.dry_run}",
        f"- Replace existing sheet values: {report.replace_existing}",
        f"- Sheet replace planned: {report.sheet_replace_planned}",
        f"- Sheet replaced: {report.sheet_replaced}",
        f"- Styling applied: {report.styling_applied}",
        f"- Sheet created: {report.sheet_created}",
        f"- Review comments found: {report.review_comments_found}",
        f"- Review comment cells: {report.review_comment_cells}",
        f"- Review overwrite allowed: {report.review_overwrite_allowed}",
        f"- Review snapshot path: `{report.review_snapshot_path or ''}`",
        f"- Review history archive path: `{report.review_history_archive_path or ''}`",
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
    sheet_schema: Annotated[
        str | None,
        typer.Option("--schema", help="Sheet schema: candidate or bundle-review."),
    ] = None,
    dry_run: Annotated[
        bool | None,
        typer.Option("--dry-run/--no-dry-run", help="Report planned changes without append."),
    ] = None,
    replace_existing: Annotated[
        bool | None,
        typer.Option(
            "--replace-existing/--append-existing",
            help="Clear the target tab and write the preview as the current review board.",
        ),
    ] = None,
    styling: Annotated[
        bool | None,
        typer.Option("--styling/--no-styling", help="Apply background styling to appended rows."),
    ] = None,
    allow_review_overwrite: Annotated[
        bool | None,
        typer.Option(
            "--allow-review-overwrite/--protect-review-overwrite",
            help="Allow bundle review replace when reviewer comment cells already exist.",
        ),
    ] = None,
) -> None:
    loaded = load_append_config()
    config = GoogleSheetAppendConfig(
        spreadsheet_id=spreadsheet_id or loaded.spreadsheet_id,
        target_sheet_name=sheet_name or loaded.target_sheet_name,
        source_preview_csv=preview_csv or loaded.source_preview_csv,
        sheet_schema=_normalize_sheet_schema(sheet_schema or loaded.sheet_schema),
        dry_run=loaded.dry_run if dry_run is None else dry_run,
        replace_existing=loaded.replace_existing if replace_existing is None else replace_existing,
        create_sheet_if_missing=loaded.create_sheet_if_missing,
        create_header_if_missing=loaded.create_header_if_missing,
        skip_duplicates=loaded.skip_duplicates,
        duplicate_keys=_schema_default_duplicate_keys(sheet_schema or loaded.sheet_schema),
        styling_enabled=loaded.styling_enabled if styling is None else styling,
        allow_review_overwrite=(
            loaded.allow_review_overwrite
            if allow_review_overwrite is None
            else allow_review_overwrite
        ),
        review_snapshot_dir=loaded.review_snapshot_dir,
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
