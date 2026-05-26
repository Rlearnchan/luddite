"""Two-pass Jibi review-board refresh with local syuka snapshot annotations."""

from __future__ import annotations

import csv
import json
import subprocess
from collections import Counter
from datetime import UTC, datetime
from pathlib import Path
from typing import Annotated, Any

import typer
from rich.console import Console

from luddite import paths
from luddite.agents.jibi.append_to_sheet import (
    BUNDLE_REVIEW_SHEET_SCHEMA,
    GoogleSheetAppendConfig,
    _build_default_client,
    append_jibi_sheet,
    load_append_config,
)
from luddite.agents.jibi.board_support_search import (
    enrich_review_board_support_links,
)
from luddite.agents.jibi.board_support_search import (
    provider_from_env as board_support_provider_from_env,
)
from luddite.agents.jibi.render_daily_digest import render_daily_digest
from luddite.agents.jibi.syuka_snapshot_probe import (
    DEFAULT_SYUKA_DATA_DIR,
    probe_syuka_snapshot,
)

app = typer.Typer(no_args_is_help=False)
console = Console()


def _bridge_queries_path(run_date: str) -> Path:
    return paths.REPORTS_DIR / f"jibi_syuka_bridge_queries_{run_date}.json"


def _syuka_md_path(run_date: str) -> Path:
    return paths.REPORTS_DIR / f"jibi_syuka_snapshot_matches_{run_date}.md"


def _syuka_json_path(run_date: str) -> Path:
    return paths.REPORTS_DIR / f"jibi_syuka_snapshot_matches_{run_date}.json"


def _refresh_md_path(run_date: str) -> Path:
    return paths.REPORTS_DIR / f"jibi_syuka_refresh_{run_date}.md"


def _refresh_json_path(run_date: str) -> Path:
    return paths.REPORTS_DIR / f"jibi_syuka_refresh_{run_date}.json"


def _board_csv_path(run_date: str, output_dir: Path) -> Path:
    return output_dir / f"{run_date}_bundle_review_sheet.csv"


def _board_metadata_path(run_date: str, output_dir: Path) -> Path:
    return output_dir / f"{run_date}_bundle_review_sheet_metadata.json"


def _git_commit() -> str:
    try:
        result = subprocess.run(
            ["git", "rev-parse", "--short", "HEAD"],
            cwd=paths.REPO_ROOT,
            text=True,
            capture_output=True,
            check=False,
        )
    except OSError:
        return ""
    return result.stdout.strip() if result.returncode == 0 else ""


def _count_jsonl(path: Path) -> int:
    if not path.exists():
        return 0
    with path.open(encoding="utf-8") as source:
        return sum(1 for line in source if line.strip())


def _rss_unique_count(path: Path) -> int:
    if not path.exists():
        return 0
    urls: set[str] = set()
    with path.open(encoding="utf-8") as source:
        for line in source:
            if not line.strip():
                continue
            try:
                payload = json.loads(line)
            except json.JSONDecodeError:
                continue
            url = str(payload.get("url") or payload.get("seed_url") or "").strip()
            if url:
                urls.add(url)
    return len(urls)


def _csv_row_count(path: Path) -> int:
    if not path.exists():
        return 0
    with path.open(encoding="utf-8-sig", newline="") as source:
        return sum(1 for _row in csv.DictReader(source))


def _split_csv(value: str, default: list[str]) -> list[str]:
    items = [item.strip() for item in value.split(",") if item.strip()]
    return items or default


def _metadata_override_count(path: Path) -> int:
    if not path.exists():
        return 0
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return 0
    return sum(1 for row in payload.get("rows", []) if row.get("editorial_override_applied"))


def _syuka_counts(payload: dict[str, Any]) -> Counter[str]:
    return Counter(
        str(item.get("recommendation") or "unknown")
        for item in payload.get("results", [])
    )


def _append_operating_log(record: dict[str, Any]) -> Path:
    path = paths.REPORTS_DIR / "jibi_operating_experiment_log.jsonl"
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as output:
        output.write(json.dumps(record, ensure_ascii=False, sort_keys=True) + "\n")
    return path


def _write_refresh_report(payload: dict[str, Any]) -> tuple[Path, Path]:
    md_path = _refresh_md_path(str(payload["run_date"]))
    json_path = _refresh_json_path(str(payload["run_date"]))
    md_path.parent.mkdir(parents=True, exist_ok=True)
    json_path.parent.mkdir(parents=True, exist_ok=True)
    lines = [
        f"# Jibi Syuka Refresh — {payload['run_date']}",
        "",
        f"- mode: `{payload['mode']}`",
        f"- render_pass_1_status: `{payload['render_pass_1_status']}`",
        f"- bridge_query_path: `{payload['bridge_query_path']}`",
        f"- syuka_probe_status: `{payload['syuka_probe_status']}`",
        f"- render_pass_2_status: `{payload['render_pass_2_status']}`",
        f"- editorial_override_path: `{payload.get('editorial_override_path', '')}`",
        f"- editorial_override_count: {payload.get('editorial_override_count', 0)}",
        f"- board_csv_path: `{payload['board_csv_path']}`",
        f"- board_metadata_path: `{payload['board_metadata_path']}`",
        f"- sheet_mode: `{payload['sheet_mode']}`",
        f"- sheet_replace_status: `{payload['sheet_replace_status']}`",
        f"- overwrite_guard_status: `{payload['overwrite_guard_status']}`",
        "- board_support_search_status: "
        f"`{payload.get('board_support_search_status', 'not_requested')}`",
        f"- board_support_links_total: {payload.get('board_support_links_total', 0)}",
        "",
        "## Warnings",
        "",
    ]
    warnings = payload.get("warnings") or []
    lines.extend(f"- {warning}" for warning in warnings)
    if not warnings:
        lines.append("- none")
    md_path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    json_path.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    return md_path, json_path


def refresh_review_board_with_syuka(
    *,
    run_date: str,
    input_path: Path = paths.JIBI_SCORED_CANDIDATES_JSONL,
    output_dir: Path = paths.DAILY_DIGEST_DIR,
    syuka_data_dir: Path = DEFAULT_SYUKA_DATA_DIR,
    editorial_overrides_path: Path | None = None,
    review_history_path: Path = paths.JIBI_REVIEW_BOARD_HISTORY_JSONL,
    review_board_limit: int | None = None,
    replace_sheet: bool = False,
    sheet_name: str = "Jibi",
    support_search: bool = False,
    support_search_categories: list[str] | None = None,
    support_search_results_per_query: int = 5,
    support_search_max_calls: int = 60,
    support_links_per_row: int = 1,
) -> dict[str, Any]:
    warnings: list[str] = []
    render_daily_digest(
        input_path=input_path,
        output_dir=output_dir,
        digest_date=run_date,
        review_board_limit=review_board_limit,
        review_history_path=review_history_path,
        editorial_overrides_path=editorial_overrides_path,
    )
    bridge_path = _bridge_queries_path(run_date)
    syuka_md, syuka_json, syuka_payload = probe_syuka_snapshot(
        run_date=run_date,
        queries_json=bridge_path,
        syuka_data_dir=syuka_data_dir,
        output_md=_syuka_md_path(run_date),
        output_json=_syuka_json_path(run_date),
    )
    snapshot_status = syuka_payload.get("snapshot_status", {})
    if snapshot_status.get("status") != "usable":
        warnings.append(
            "syuka snapshot unavailable; board was rendered without reliable past-video matches"
        )
    render_daily_digest(
        input_path=input_path,
        output_dir=output_dir,
        digest_date=run_date,
        review_board_limit=review_board_limit,
        review_history_path=review_history_path,
        editorial_overrides_path=editorial_overrides_path,
    )

    board_csv = _board_csv_path(run_date, output_dir)
    metadata_path = _board_metadata_path(run_date, output_dir)
    support_search_status = "not_requested"
    support_search_links_total = 0
    support_search_report_md = ""
    support_search_report_json = ""
    if support_search:
        try:
            support_provider = board_support_provider_from_env()
            support_payload = enrich_review_board_support_links(
                run_date=run_date,
                board_csv_path=board_csv,
                metadata_path=metadata_path,
                provider=support_provider,
                categories=support_search_categories or ["news"],
                max_links_per_row=support_links_per_row,
                results_per_query=support_search_results_per_query,
                max_provider_calls=support_search_max_calls,
            )
        except ValueError as error:
            support_search_status = "skipped_missing_credentials"
            warnings.append(str(error))
        else:
            support_search_status = "succeeded"
            support_search_links_total = int(support_payload.get("selected_links_total") or 0)
            support_search_report_md = str(support_payload.get("markdown_path") or "")
            support_search_report_json = str(support_payload.get("json_path") or "")

    sheet_replace_status = "not_requested"
    overwrite_guard_status = "not_triggered"
    append_errors: list[str] = []
    if replace_sheet:
        loaded = load_append_config()
        config = GoogleSheetAppendConfig(
            spreadsheet_id=loaded.spreadsheet_id,
            target_sheet_name=sheet_name or loaded.target_sheet_name,
            source_preview_csv=board_csv,
            sheet_schema=BUNDLE_REVIEW_SHEET_SCHEMA,
            dry_run=False,
            replace_existing=True,
            create_sheet_if_missing=loaded.create_sheet_if_missing,
            create_header_if_missing=loaded.create_header_if_missing,
            skip_duplicates=loaded.skip_duplicates,
            duplicate_keys=loaded.duplicate_keys,
            styling_enabled=loaded.styling_enabled,
            allow_review_overwrite=loaded.allow_review_overwrite,
            review_snapshot_dir=loaded.review_snapshot_dir,
            auth_mode=loaded.auth_mode,
            service_account_json_path=loaded.service_account_json_path,
        )
        report = append_jibi_sheet(config=config, client=_build_default_client(config))
        append_errors = list(report.errors)
        if report.review_comments_found and report.errors:
            overwrite_guard_status = "blocked_existing_reviews"
        elif report.review_comments_found and config.allow_review_overwrite:
            overwrite_guard_status = "overwritten_after_explicit_allow"
        sheet_replace_status = "succeeded" if report.sheet_replaced else "blocked"
        if append_errors:
            warnings.extend(append_errors)

    counts = _syuka_counts(syuka_payload)
    editorial_path = editorial_overrides_path or (
        paths.JIBI_EDITORIAL_OVERRIDES_DIR / f"jibi_review_board_{run_date}.json"
    )
    log_record = {
        "run_date": run_date,
        "registered_at": datetime.now(UTC).isoformat(),
        "git_commit": _git_commit(),
        "command": "jibi-review-board-replace-with-syuka"
        if replace_sheet
        else "jibi-review-board-refresh-with-syuka",
        "mode": "replace" if replace_sheet else "dry_run",
        "rss_raw_count": _count_jsonl(paths.ARTICLE_INBOX_DIR / f"rss_{run_date}.jsonl"),
        "rss_unique_count": _rss_unique_count(paths.ARTICLE_INBOX_DIR / f"rss_{run_date}.jsonl"),
        "board_row_count": _csv_row_count(board_csv),
        "syuka_probe_status": str(snapshot_status.get("status") or "unknown"),
        "syuka_duplicate_count": counts.get("duplicate", 0),
        "syuka_adjacent_count": counts.get("adjacent", 0),
        "editorial_override_path": str(editorial_path),
        "editorial_override_count": _metadata_override_count(metadata_path),
        "sheet_mode": "staging_replace" if replace_sheet else "none",
        "sheet_replace_status": sheet_replace_status,
        "overwrite_guard_status": overwrite_guard_status,
        "board_support_search_status": support_search_status,
        "board_support_links_total": support_search_links_total,
        "board_support_search_report_md": support_search_report_md,
        "board_support_search_report_json": support_search_report_json,
        "feedback_completion_counts": {},
        "triage_label_counts": {},
    }
    log_path = _append_operating_log(log_record)
    payload = {
        **log_record,
        "render_pass_1_status": "succeeded",
        "bridge_query_path": str(bridge_path),
        "syuka_probe_status": str(snapshot_status.get("status") or "unknown"),
        "syuka_report_md_path": str(syuka_md),
        "syuka_report_json_path": str(syuka_json),
        "render_pass_2_status": "succeeded",
        "board_csv_path": str(board_csv),
        "board_metadata_path": str(metadata_path),
        "operating_log_path": str(log_path),
        "warnings": warnings,
    }
    report_md, report_json = _write_refresh_report(payload)
    payload["refresh_report_md_path"] = str(report_md)
    payload["refresh_report_json_path"] = str(report_json)
    return payload


@app.callback(invoke_without_command=True)
def main(
    run_date: Annotated[str, typer.Option("--date", help="Run date in YYYY-MM-DD.")],
    input_path: Annotated[
        Path,
        typer.Option("--input", help="Scored candidate JSONL input path."),
    ] = paths.JIBI_SCORED_CANDIDATES_JSONL,
    output_dir: Annotated[
        Path,
        typer.Option("--output-dir", help="Daily digest output directory."),
    ] = paths.DAILY_DIGEST_DIR,
    syuka_data_dir: Annotated[
        Path,
        typer.Option("--syuka-data-dir", help="Read-only syuka snapshot data directory."),
    ] = DEFAULT_SYUKA_DATA_DIR,
    editorial_overrides_path: Annotated[
        Path | None,
        typer.Option("--editorial-overrides", help="Optional editorial override JSON."),
    ] = None,
    review_history_path: Annotated[
        Path,
        typer.Option("--review-history", help="Local review-board history JSONL."),
    ] = paths.JIBI_REVIEW_BOARD_HISTORY_JSONL,
    review_board_limit: Annotated[
        int | None,
        typer.Option("--review-board-limit", help="Max rows in review board."),
    ] = None,
    replace_sheet: Annotated[
        bool,
        typer.Option("--replace-sheet/--no-replace-sheet", help="Replace the Jibi sheet."),
    ] = False,
    sheet_name: Annotated[
        str,
        typer.Option("--sheet-name", help="Google Sheet tab name."),
    ] = "Jibi",
    support_search: Annotated[
        bool,
        typer.Option(
            "--support-search/--no-support-search",
            help="Use Naver Search to fill review-board sub links.",
        ),
    ] = False,
    support_search_categories_csv: Annotated[
        str,
        typer.Option("--support-search-categories", help="Comma-separated search categories."),
    ] = "news,webkr",
    support_search_results_per_query: Annotated[
        int,
        typer.Option("--support-search-results-per-query", help="Search results per query."),
    ] = 5,
    support_search_max_calls: Annotated[
        int,
        typer.Option("--support-search-max-calls", help="Maximum provider calls."),
    ] = 60,
    support_links_per_row: Annotated[
        int,
        typer.Option("--support-links-per-row", help="Maximum sub links per board row."),
    ] = 1,
) -> None:
    payload = refresh_review_board_with_syuka(
        run_date=run_date,
        input_path=input_path,
        output_dir=output_dir,
        syuka_data_dir=syuka_data_dir,
        editorial_overrides_path=editorial_overrides_path,
        review_history_path=review_history_path,
        review_board_limit=review_board_limit,
        replace_sheet=replace_sheet,
        sheet_name=sheet_name,
        support_search=support_search,
        support_search_categories=_split_csv(support_search_categories_csv, ["news"]),
        support_search_results_per_query=support_search_results_per_query,
        support_search_max_calls=support_search_max_calls,
        support_links_per_row=support_links_per_row,
    )
    console.print(
        "[green]Jibi syuka refresh complete "
        f"(rows={payload['board_row_count']}, syuka={payload['syuka_probe_status']}, "
        f"sheet={payload['sheet_replace_status']}).[/green]"
    )
    if payload.get("warnings"):
        console.print(f"[yellow]Warnings: {len(payload['warnings'])}[/yellow]")
    if replace_sheet and payload["sheet_replace_status"] != "succeeded":
        raise typer.Exit(1)


if __name__ == "__main__":
    app()
