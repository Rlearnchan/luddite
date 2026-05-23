"""Manual one-shot Jibi operating-run helpers."""

from __future__ import annotations

import json
from dataclasses import asdict, dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Annotated

import typer
from rich.console import Console

from luddite import paths
from luddite.agents.jibi.ops_safety import validate_ops_safety

app = typer.Typer(no_args_is_help=False)
console = Console()


@dataclass(frozen=True)
class JibiManualRunPaths:
    run_date: str
    rss_inbox_path: Path
    preview_csv_path: Path
    daily_digest_path: Path
    quality_report_path: Path
    content_enrichment_report_path: Path
    content_enrichment_json_path: Path
    sheet_append_report_path: Path
    manual_summary_md_path: Path
    manual_summary_json_path: Path


@dataclass(frozen=True)
class JibiManualRunManifest:
    run_date: str
    append_mode: str
    target_sheet_name: str
    append_dry_run: bool
    rss_inbox_path: str
    preview_csv_path: str
    daily_digest_path: str
    quality_report_path: str
    content_enrichment_report_path: str
    content_enrichment_json_path: str
    sheet_append_report_path: str
    manual_summary_md_path: str
    manual_summary_json_path: str
    content_enrichment_status: str
    append_status: str
    command_status: str
    log_file_path: str
    err_log_file_path: str
    created_at: str


def manual_run_paths(
    run_date: str,
    *,
    rss_inbox_path: Path | None = None,
) -> JibiManualRunPaths:
    return JibiManualRunPaths(
        run_date=run_date,
        rss_inbox_path=rss_inbox_path
        or paths.ARTICLE_INBOX_DIR / f"rss_{run_date}.jsonl",
        preview_csv_path=paths.DAILY_DIGEST_DIR
        / f"{run_date}_sheet_append_preview.csv",
        daily_digest_path=paths.DAILY_DIGEST_DIR / f"{run_date}.md",
        quality_report_path=paths.REPORTS_DIR / f"jibi_quality_{run_date}.md",
        content_enrichment_report_path=paths.REPORTS_DIR
        / f"jibi_content_enrichment_{run_date}.md",
        content_enrichment_json_path=paths.REPORTS_DIR
        / f"jibi_content_enrichment_{run_date}.json",
        sheet_append_report_path=paths.REPORTS_DIR
        / f"jibi_sheet_append_{run_date}.md",
        manual_summary_md_path=paths.REPORTS_DIR
        / f"jibi_manual_update_{run_date}.md",
        manual_summary_json_path=paths.REPORTS_DIR
        / f"jibi_manual_update_{run_date}.json",
    )


def append_jibi_sheet_args(
    *,
    run_date: str,
    append_mode: str | None = None,
    target_sheet_name: str | None = None,
    preview_csv_path: Path | None = None,
) -> list[str]:
    config = validate_ops_safety(
        append_mode=append_mode,
        target_sheet_name=target_sheet_name,
    )
    preview_csv = preview_csv_path or manual_run_paths(run_date).preview_csv_path
    return [
        "append-jibi-sheet",
        "--preview-csv",
        str(preview_csv),
        "--dry-run" if config.dry_run else "--no-dry-run",
        "--sheet-name",
        config.target_sheet_name,
    ]


def write_manual_run_manifest(
    *,
    run_date: str,
    append_mode: str,
    target_sheet_name: str,
    rss_inbox_path: Path,
    preview_csv_path: Path,
    daily_digest_path: Path,
    quality_report_path: Path,
    content_enrichment_report_path: Path,
    content_enrichment_json_path: Path,
    sheet_append_report_path: Path,
    manual_summary_md_path: Path,
    manual_summary_json_path: Path,
    content_enrichment_status: str,
    append_status: str,
    command_status: str,
    log_file_path: Path,
    err_log_file_path: Path,
    created_at: str | None = None,
) -> JibiManualRunManifest:
    config = validate_ops_safety(
        append_mode=append_mode,
        target_sheet_name=target_sheet_name,
    )
    manifest = JibiManualRunManifest(
        run_date=run_date,
        append_mode=config.append_mode,
        target_sheet_name=config.target_sheet_name,
        append_dry_run=config.dry_run,
        rss_inbox_path=str(rss_inbox_path),
        preview_csv_path=str(preview_csv_path),
        daily_digest_path=str(daily_digest_path),
        quality_report_path=str(quality_report_path),
        content_enrichment_report_path=str(content_enrichment_report_path),
        content_enrichment_json_path=str(content_enrichment_json_path),
        sheet_append_report_path=str(sheet_append_report_path),
        manual_summary_md_path=str(manual_summary_md_path),
        manual_summary_json_path=str(manual_summary_json_path),
        content_enrichment_status=content_enrichment_status,
        append_status=append_status,
        command_status=command_status,
        log_file_path=str(log_file_path),
        err_log_file_path=str(err_log_file_path),
        created_at=created_at or datetime.now(UTC).isoformat(),
    )
    manual_summary_md_path.parent.mkdir(parents=True, exist_ok=True)
    manual_summary_json_path.parent.mkdir(parents=True, exist_ok=True)
    manual_summary_md_path.write_text(_manifest_markdown(manifest), encoding="utf-8")
    manual_summary_json_path.write_text(
        json.dumps(asdict(manifest), ensure_ascii=False, indent=2, sort_keys=True)
        + "\n",
        encoding="utf-8",
    )
    return manifest


def _manifest_markdown(manifest: JibiManualRunManifest) -> str:
    lines = [
        f"# Jibi Manual Update Summary — {manifest.run_date}",
        "",
        f"- Run date: {manifest.run_date}",
        f"- Append mode: `{manifest.append_mode}`",
        f"- Target sheet: `{manifest.target_sheet_name}`",
        f"- Append dry-run: {manifest.append_dry_run}",
        f"- Content enrichment status: `{manifest.content_enrichment_status}`",
        f"- Append status: `{manifest.append_status}`",
        f"- Command status: `{manifest.command_status}`",
        f"- Created at: `{manifest.created_at}`",
        "",
        "## Artifacts",
        "",
        f"- RSS inbox: `{manifest.rss_inbox_path}`",
        f"- Preview CSV: `{manifest.preview_csv_path}`",
        f"- Daily digest: `{manifest.daily_digest_path}`",
        f"- Quality report: `{manifest.quality_report_path}`",
        f"- Content enrichment report: `{manifest.content_enrichment_report_path}`",
        f"- Content enrichment JSON: `{manifest.content_enrichment_json_path}`",
        f"- Sheet append report: `{manifest.sheet_append_report_path}`",
        f"- Manual summary JSON: `{manifest.manual_summary_json_path}`",
        "",
        "## Logs",
        "",
        f"- stdout log: `{manifest.log_file_path}`",
        f"- stderr log: `{manifest.err_log_file_path}`",
        "",
    ]
    return "\n".join(lines)


@app.callback(invoke_without_command=True)
def main(
    run_date: Annotated[str, typer.Option("--date", help="Manual run date.")],
    append_mode: Annotated[
        str,
        typer.Option("--append-mode", help="dry_run or staging_append."),
    ],
    target_sheet_name: Annotated[
        str,
        typer.Option("--target-sheet", help="Target Google Sheet tab."),
    ],
    rss_inbox_path: Annotated[Path, typer.Option("--rss-inbox")],
    preview_csv_path: Annotated[Path, typer.Option("--preview-csv")],
    daily_digest_path: Annotated[Path, typer.Option("--daily-digest")],
    quality_report_path: Annotated[Path, typer.Option("--quality-report")],
    content_enrichment_report_path: Annotated[
        Path,
        typer.Option("--content-enrichment-report"),
    ],
    content_enrichment_json_path: Annotated[
        Path,
        typer.Option("--content-enrichment-json"),
    ],
    sheet_append_report_path: Annotated[Path, typer.Option("--sheet-append-report")],
    manual_summary_md_path: Annotated[Path, typer.Option("--summary-md")],
    manual_summary_json_path: Annotated[Path, typer.Option("--summary-json")],
    content_enrichment_status: Annotated[
        str,
        typer.Option("--content-enrichment-status"),
    ],
    append_status: Annotated[str, typer.Option("--append-status")],
    command_status: Annotated[str, typer.Option("--command-status")],
    log_file_path: Annotated[Path, typer.Option("--log-file")],
    err_log_file_path: Annotated[Path, typer.Option("--err-log-file")],
) -> None:
    manifest = write_manual_run_manifest(
        run_date=run_date,
        append_mode=append_mode,
        target_sheet_name=target_sheet_name,
        rss_inbox_path=rss_inbox_path,
        preview_csv_path=preview_csv_path,
        daily_digest_path=daily_digest_path,
        quality_report_path=quality_report_path,
        content_enrichment_report_path=content_enrichment_report_path,
        content_enrichment_json_path=content_enrichment_json_path,
        sheet_append_report_path=sheet_append_report_path,
        manual_summary_md_path=manual_summary_md_path,
        manual_summary_json_path=manual_summary_json_path,
        content_enrichment_status=content_enrichment_status,
        append_status=append_status,
        command_status=command_status,
        log_file_path=log_file_path,
        err_log_file_path=err_log_file_path,
    )
    console.print(
        "[green]Wrote Jibi manual update summary "
        f"to {manifest.manual_summary_md_path} and "
        f"{manifest.manual_summary_json_path}.[/green]"
    )


if __name__ == "__main__":
    app()
