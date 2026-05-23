import json
from pathlib import Path

from luddite import paths as repo_paths
from luddite.agents.jibi.manual_ops import (
    append_jibi_sheet_args,
    manual_run_paths,
    write_manual_run_manifest,
)


def test_manual_run_paths_pin_preview_csv_to_run_date() -> None:
    paths = manual_run_paths(
        "2026-05-23",
        rss_inbox_path=Path("data/inbox/articles/rss_2026-05-23.jsonl"),
    )

    assert paths.preview_csv_path.relative_to(repo_paths.REPO_ROOT) == Path(
        "outputs/daily_digest/2026-05-23_sheet_append_preview.csv"
    )
    assert paths.daily_digest_path.relative_to(repo_paths.REPO_ROOT) == Path(
        "outputs/daily_digest/2026-05-23.md"
    )
    assert paths.sheet_append_report_path.relative_to(repo_paths.REPO_ROOT) == Path(
        "outputs/reports/jibi_sheet_append_2026-05-23.md"
    )


def test_append_args_include_date_specific_preview_csv() -> None:
    args = append_jibi_sheet_args(
        run_date="2026-05-23",
        append_mode="dry_run",
        target_sheet_name="jibi 후보",
        preview_csv_path=Path(
            "outputs/daily_digest/2026-05-23_sheet_append_preview.csv"
        ),
    )

    assert args == [
        "append-jibi-sheet",
        "--preview-csv",
        "outputs/daily_digest/2026-05-23_sheet_append_preview.csv",
        "--dry-run",
        "--sheet-name",
        "jibi 후보",
    ]


def test_append_args_for_staging_append_are_pinned() -> None:
    args = append_jibi_sheet_args(
        run_date="2026-05-23",
        append_mode="staging_append",
        target_sheet_name="jibi 후보",
    )

    assert "--preview-csv" in args
    assert any(
        item.endswith("outputs/daily_digest/2026-05-23_sheet_append_preview.csv")
        for item in args
    )
    assert "--no-dry-run" in args


def test_write_manual_run_manifest_has_no_credentials(tmp_path) -> None:
    md_path = tmp_path / "jibi_manual_update_2026-05-23.md"
    json_path = tmp_path / "jibi_manual_update_2026-05-23.json"

    manifest = write_manual_run_manifest(
        run_date="2026-05-23",
        append_mode="dry_run",
        target_sheet_name="jibi 후보",
        rss_inbox_path=Path("data/inbox/articles/rss_2026-05-23.jsonl"),
        preview_csv_path=Path(
            "outputs/daily_digest/2026-05-23_sheet_append_preview.csv"
        ),
        daily_digest_path=Path("outputs/daily_digest/2026-05-23.md"),
        quality_report_path=Path("outputs/reports/jibi_quality_2026-05-23.md"),
        content_enrichment_report_path=Path(
            "outputs/reports/jibi_content_enrichment_2026-05-23.md"
        ),
        content_enrichment_json_path=Path(
            "outputs/reports/jibi_content_enrichment_2026-05-23.json"
        ),
        sheet_append_report_path=Path(
            "outputs/reports/jibi_sheet_append_2026-05-23.md"
        ),
        manual_summary_md_path=md_path,
        manual_summary_json_path=json_path,
        content_enrichment_status="succeeded",
        append_status="dry_run_completed",
        command_status="success",
        log_file_path=Path("~/Library/Logs/luddite/jibi_manual_2026-05-23.log"),
        err_log_file_path=Path(
            "~/Library/Logs/luddite/jibi_manual_2026-05-23.err.log"
        ),
        created_at="2026-05-23T00:00:00+00:00",
    )

    assert manifest.append_dry_run is True
    md_text = md_path.read_text(encoding="utf-8")
    json_payload = json.loads(json_path.read_text(encoding="utf-8"))
    assert "Preview CSV" in md_text
    assert "service-account" not in md_text
    assert "GOOGLE_APPLICATION_CREDENTIALS" not in json.dumps(json_payload)
