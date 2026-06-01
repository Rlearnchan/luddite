import json

from luddite import paths
from luddite.agents.jibi.quality_replay import (
    build_quality_replay_report,
    topic_concentration_diagnostics,
    write_quality_replay_report,
)


def test_replay_jibi_quality_skips_missing_dates_and_reports_available_dates(
    tmp_path,
    monkeypatch,
) -> None:
    daily_dir = tmp_path / "daily_digest"
    reports_dir = tmp_path / "reports"
    daily_dir.mkdir()
    reports_dir.mkdir()
    monkeypatch.setattr(paths, "DAILY_DIGEST_DIR", daily_dir)
    monkeypatch.setattr(paths, "REPORTS_DIR", reports_dir)
    (daily_dir / "2026-06-01_bundle_review_sheet_metadata.json").write_text(
        json.dumps(
            {
                "rows": [
                    {
                        "title": "AI 행정 책임",
                        "board_score": 83,
                        "primary_topic_family": "ai_tech",
                        "source_role": "market_wire",
                        "generic_visible_copy_warning": True,
                        "quality_floor_exclusion_reason": (
                            "generic_visible_copy_warning"
                        ),
                    }
                ]
            },
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )
    (reports_dir / "jibi_selection_calibration_2026-06-01.json").write_text(
        json.dumps(
            {
                "selected_count": 1,
                "main_seed_count": 0,
                "main_seed_candidate_count": 1,
                "ready_seed_candidate_count": 0,
                "syuka_weak_adjacent_count": 1,
            },
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )

    payload = build_quality_replay_report(["2026-05-31", "2026-06-01"])

    assert payload["available_count"] == 1
    assert payload["missing_count"] == 1
    assert payload["rows"][0]["available"] is False
    assert payload["rows"][1]["selected_count"] == 1
    assert payload["rows"][1]["generic_visible_copy_warning_count"] == 1
    assert payload["rows"][1]["syuka_weak_adjacent_count"] == 1

    md_path, json_path = write_quality_replay_report(
        run_dates=["2026-05-31", "2026-06-01"],
        markdown_path=reports_dir / "jibi_quality_replay_2026-06-01.md",
    )
    assert "2026-06-01" in md_path.read_text(encoding="utf-8")
    assert json.loads(json_path.read_text(encoding="utf-8"))["available_count"] == 1


def test_topic_concentration_warns_for_ai_heavy_visible_rows() -> None:
    rows = [
        {
            "title": "AI 1",
            "board_score": 80,
            "primary_topic_family": "ai_tech",
            "source_role": "section_news",
            "seed_readiness_level": "needs_support",
        },
        {
            "title": "AI 2",
            "board_score": 76,
            "primary_topic_family": "ai_tech",
            "source_role": "section_news",
        },
        {
            "title": "AI 3",
            "board_score": 42,
            "primary_topic_family": "ai_tech",
            "source_role": "section_news",
            "generic_visible_copy_warning": True,
        },
        {
            "title": "Energy",
            "board_score": 88,
            "primary_topic_family": "energy_climate",
            "source_role": "section_news",
        },
    ]

    result = topic_concentration_diagnostics(rows)

    assert result["topic_concentration_warning"] is True
    assert "ai_tech selected 3/4" in result["topic_concentration_reasons"]
    assert result["topic_concentration_rows"][0]["weakest_row"] == "AI 3"
