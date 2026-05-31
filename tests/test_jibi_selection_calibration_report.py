import json

from luddite.agents.jibi.board_scoring import compute_board_score
from luddite.agents.jibi.selection_lessons import (
    build_selection_calibration_report,
    write_selection_calibration_report,
)


def _record(story_id: str, title: str) -> dict:
    return {
        "story_bundle_id": story_id,
        "story_fingerprint": story_id,
        "bundle_title": title,
    }


def _candidate(story_id: str, title: str, summary: str) -> dict:
    return {
        "candidate_id": story_id + "_candidate",
        "title": title,
        "summary": summary,
        "source": "fixture",
        "source_role_class": "public_wire",
        "seed_type": "other",
        "story_role": "standalone_seed",
        "seed_quality_classification": "standalone_seed",
        "quality_flags": [],
        "risk_flags": [],
        "scores": {"total_score": 72, "broadcast_potential_proxy": 4},
    }


def _computed_score_row(story_id: str, title: str, summary: str) -> dict:
    record = _record(story_id, title)
    representative = _candidate(story_id, title, summary)
    board_score = compute_board_score(
        record=record,
        representative=representative,
        history_rows=[],
        mismatch_reasons=[],
        syuka_similarity=None,
        second_search=None,
    )
    return {
        **record,
        **board_score,
        "title": title,
        "story_role": representative["story_role"],
        "seed_quality_classification": representative[
            "seed_quality_classification"
        ],
    }


def test_selection_calibration_report_counts_lessons_and_support_missing(tmp_path) -> None:
    score_rows = [
        {
            "story_bundle_id": "story_ai",
            "title": "AI 역사 브이로그",
            "total_score": 72,
            "board_score_before_calibration": 80,
            "board_score": 82,
            "editorial_role": "sub_block",
            "selection_lesson_role": "sub_block",
            "selection_lessons": [
                "casual_ai_use_case_bonus",
                "needs_parallel_examples",
                "needs_second_source",
            ],
            "support_requirements": ["parallel_case"],
            "support_requirement_details": [
                {"key": "parallel_case", "severity": "critical"}
            ],
            "support_missing_requirements": ["parallel_case"],
            "why_not_main_seed": "support missing: 두 번째 사례",
            "why_not_main_seed_reasons": ["support_missing:parallel_case"],
        },
        {
            "story_bundle_id": "story_sports",
            "title": "월드컵 티켓값",
            "total_score": 70,
            "board_score_before_calibration": 78,
            "board_score": 33,
            "selection_lesson_role": "hook_only",
            "selection_lessons": [
                "sports_primary_downrank",
                "sports_business_hook_only",
            ],
            "support_requirements": [],
            "support_missing_requirements": [],
        },
        {
            "story_bundle_id": "story_battery",
            "title": "배터리 소",
            "total_score": 68,
            "board_score_before_calibration": 76,
            "board_score": 16,
            "selection_lesson_role": "suppress",
            "selection_lesson_role_hints": ["suppress"],
            "selection_lessons": ["advocacy_or_moral_journalism_downrank"],
        },
    ]

    payload = build_selection_calibration_report(
        run_date="2026-05-27",
        score_rows=score_rows,
        selected_ids={"story_ai", "story_sports"},
    )

    assert payload["selected_count"] == 2
    assert payload["sub_block_count"] == 1
    assert payload["hook_only_count"] == 1
    assert payload["suppress_candidate_count"] == 1
    assert payload["needs_second_source_count"] == 1
    assert payload["support_missing_count"] == 1
    assert payload["reviewer_lesson_counts"]["sports_primary_downrank"] == 1
    assert payload["selected"][0]["board_score_before"] == 80
    assert payload["top_10_before_calibration"][0]["title"] == "AI 역사 브이로그"
    assert payload["top_10_after_calibration"][0]["title"] == "AI 역사 브이로그"
    assert any(row["title"] == "월드컵 티켓값" for row in payload["dropped_by_calibration"])
    assert any(
        row["title"] == "AI 역사 브이로그"
        for row in payload["promoted_by_calibration"]
    )
    assert "role_changed_by_calibration" in payload

    md_path = tmp_path / "jibi_selection_calibration_2026-05-27.md"
    json_path = tmp_path / "jibi_selection_calibration_2026-05-27.json"
    write_selection_calibration_report(
        run_date="2026-05-27",
        score_rows=score_rows,
        selected_ids={"story_ai", "story_sports"},
        markdown_path=md_path,
        json_path=json_path,
    )

    assert "support_missing_count: 1" in md_path.read_text(encoding="utf-8")
    assert "Top 10 Before Calibration" in md_path.read_text(encoding="utf-8")
    written = json.loads(json_path.read_text(encoding="utf-8"))
    assert written["selected"][0]["support_requirements"] == ["parallel_case"]


def test_selection_calibration_report_accepts_computed_board_score_rows() -> None:
    score_rows = [
        _computed_score_row(
            "story_ai_history_vlog",
            "AI 역사 브이로그",
            "AI 역사 인물이 여행 브이로그처럼 편하게 즐기는 사용 사례",
        ),
        _computed_score_row(
            "story_worldcup_ticket",
            "월드컵 티켓값이 왜 이렇게 비싸졌나",
            "FIFA 월드컵 티켓 가격과 이벤트 비즈니스 이야기",
        ),
        _computed_score_row(
            "story_battery_cow",
            "배터리 소",
            "동물권 폭로성 기사라 제목 훅은 강하지만 내용은 도덕 고발 중심",
        ),
        _computed_score_row(
            "story_delivery_robot",
            "배달로봇은 왜 길에서 멈추나",
            "배달로봇과 전동 킥보드가 한국 보행자 정책과 충돌",
        ),
    ]

    payload = build_selection_calibration_report(
        run_date="2026-05-27",
        score_rows=score_rows,
        selected_ids={"story_ai_history_vlog", "story_delivery_robot"},
    )

    by_id = {row["story_bundle_id"]: row for row in score_rows}
    assert by_id["story_worldcup_ticket"]["selection_lesson_score_delta"] == -45
    assert by_id["story_worldcup_ticket"]["selection_lesson_score_delta"] > -105
    assert {
        "sports_primary_downrank",
        "sports_business_hook_only",
    }.issubset(by_id["story_worldcup_ticket"]["selection_lessons"])
    assert "casual_ai_use_case_bonus" in by_id["story_ai_history_vlog"][
        "selection_lessons"
    ]
    assert by_id["story_battery_cow"]["selection_lesson_role"] == "suppress"
    assert "daily_life_problem_bonus" in by_id["story_delivery_robot"][
        "selection_lessons"
    ]

    assert payload["selected_count"] == 2
    assert len(payload["top_10_before_calibration"]) == 4
    assert len(payload["top_10_after_calibration"]) == 4
    assert any(
        row["story_bundle_id"] == "story_worldcup_ticket"
        for row in payload["dropped_by_calibration"]
    )
    assert any(
        row["story_bundle_id"] == "story_battery_cow"
        for row in payload["dropped_by_calibration"]
    )
    assert any(
        row["story_bundle_id"] == "story_ai_history_vlog"
        for row in payload["promoted_by_calibration"]
    )
    assert any(
        row["story_bundle_id"] == "story_delivery_robot"
        for row in payload["promoted_by_calibration"]
    )
    assert any(
        row["story_bundle_id"] == "story_battery_cow"
        and row["editorial_role_after"] == "suppress"
        for row in payload["role_changed_by_calibration"]
    )
