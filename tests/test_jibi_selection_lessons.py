from luddite.agents.jibi.board_scoring import compute_board_score
from luddite.agents.jibi.selection_lessons import (
    SELECTION_LESSONS,
    infer_selection_lessons,
)


def _record(title: str) -> dict:
    return {
        "story_bundle_id": "story_" + title[:8],
        "bundle_title": title,
        "story_fingerprint": title,
    }


def _candidate(title: str, summary: str = "", *, seed_type: str = "other") -> dict:
    return {
        "candidate_id": "candidate_" + title[:8],
        "title": title,
        "summary": summary,
        "source": "fixture",
        "source_role_class": "public_wire",
        "seed_type": seed_type,
        "story_role": "standalone_seed",
        "seed_quality_classification": "standalone_seed",
        "quality_flags": [],
        "risk_flags": [],
        "scores": {"total_score": 72, "broadcast_potential_proxy": 4},
    }


def test_selection_lesson_taxonomy_contains_review_board_minimum() -> None:
    expected = {
        "sports_primary_downrank",
        "sports_business_hook_only",
        "ai_grand_discourse_downrank",
        "casual_ai_use_case_bonus",
        "needs_parallel_examples",
        "needs_second_source",
        "stale_single_case_risk",
        "foreign_company_ir_without_korea_bridge",
        "past_syuka_overlap_needs_new_angle",
        "past_syuka_low_performance_risk",
        "syuka_similarity_false_positive_risk",
        "advocacy_or_moral_journalism_downrank",
        "title_hook_content_thin_downrank",
        "daily_life_problem_bonus",
        "platform_hidden_cost_bonus",
    }

    assert expected.issubset(SELECTION_LESSONS)


def test_2026_05_27_review_board_fixtures_map_to_expected_lessons() -> None:
    cases = [
        {
            "title": "월드컵 티켓값이 왜 이렇게 비싸졌나",
            "summary": "FIFA 월드컵 티켓 가격과 이벤트 비즈니스 이야기",
            "role": "hook_only",
            "lessons": {"sports_primary_downrank", "sports_business_hook_only"},
        },
        {
            "title": "AI 역사 브이로그",
            "summary": "AI 역사 인물이 여행 브이로그처럼 편하게 즐기는 사용 사례",
            "role": "sub_block",
            "lessons": {"casual_ai_use_case_bonus", "needs_parallel_examples"},
            "forbidden": {"ai_grand_discourse_downrank"},
        },
        {
            "title": "내 목소리도 재산이 되는 시대",
            "summary": "Taylor Swift 목소리 복제 사례가 오래돼 새 병렬 사례가 필요",
            "role": "sub_block",
            "lessons": {"stale_single_case_risk", "needs_fresher_parallel_case"},
        },
        {
            "title": "배달로봇은 왜 길에서 멈추나",
            "summary": "배달로봇과 전동 킥보드가 한국 보행자 정책과 충돌",
            "role": "sub_block",
            "lessons": {"daily_life_problem_bonus", "needs_second_source"},
            "support": {"policy_or_stat", "korea_bridge"},
        },
        {
            "title": "B&Q 날씨-매출",
            "summary": "B&Q 해외 기업 실적과 ESG 스타일 날씨 효과 프레임",
            "role": "suppress",
            "lessons": {
                "foreign_company_ir_without_korea_bridge",
                "stale_ESG_style_frame",
            },
        },
        {
            "title": "계란값은 왜 또 올랐나",
            "summary": "계란값은 과거 영상과 겹치고 novelty가 낮은 일상 가격 소재",
            "role": "suppress",
            "lessons": {
                "past_syuka_overlap_needs_new_angle",
                "low_novelty_daily_price",
            },
        },
        {
            "title": "우주보험은 누가 얼마를 내나",
            "summary": "우주보험과 위성 보험료, 발사 실패 리스크라는 신선한 산업 메커니즘",
            "role": "sub_block",
            "lessons": {"fresh_industry_mechanism", "needs_second_source"},
            "support": {"parallel_case", "policy_or_stat"},
        },
        {
            "title": "부동산 미끼매물 단속",
            "summary": "부동산 허위매물과 플랫폼 정보 비대칭, 단속 기사 외 통계 필요",
            "role": "sub_block",
            "lessons": {
                "daily_life_problem_bonus",
                "platform_information_asymmetry",
                "needs_second_source",
            },
        },
        {
            "title": "배터리 소",
            "summary": "동물권 폭로성 기사라 제목 훅은 강하지만 내용은 도덕 고발 중심",
            "role": "suppress",
            "lessons": {
                "advocacy_or_moral_journalism_downrank",
                "title_hook_content_thin_downrank",
            },
        },
        {
            "title": "페라리 EV",
            "summary": "Ferrari EV라는 알려진 브랜드 훅이 있지만 스토리 확장이 필요",
            "role": "sub_block",
            "lessons": {
                "known_brand_hook",
                "needs_story_expansion",
                "syuka_similarity_false_positive_risk",
            },
            "syuka_similarity": {
                "recommendation": "duplicate",
                "top_match_title": "전설의 싸움소들",
                "reason": "broad keyword match",
            },
        },
    ]

    for case in cases:
        result = infer_selection_lessons(
            record=_record(case["title"]),
            representative=_candidate(case["title"], case["summary"]),
            syuka_similarity=case.get("syuka_similarity"),
            second_search=None,
        )

        assert result["selection_lesson_role"] == case["role"], case["title"]
        assert case["lessons"].issubset(result["selection_lessons"]), case["title"]
        assert not set(case.get("forbidden", set())).intersection(
            result["selection_lessons"]
        ), case["title"]
        assert set(case.get("support", set())).issubset(
            set(result["support_requirements"])
        ), case["title"]


def test_board_score_exposes_support_requirements_and_blocks_main_seed() -> None:
    result = compute_board_score(
        record=_record("배달로봇은 왜 길에서 멈추나"),
        representative=_candidate(
            "배달로봇은 왜 길에서 멈추나",
            "배달로봇과 전동 킥보드가 한국 보행자 정책과 충돌",
        ),
        history_rows=[],
        mismatch_reasons=[],
        syuka_similarity=None,
        second_search=None,
    )

    assert "needs_second_source" in result["selection_lessons"]
    assert {"policy_or_stat", "korea_bridge"}.issubset(result["support_requirements"])
    assert not result["support_missing_requirements"]
    assert result["selection_lesson_role"] == "sub_block"
    assert "delivery robot story needs" in result["why_not_main_seed"]
    assert result["support_status"] == "not_checked"
    assert result["board_score_before_calibration"] != result["board_score"]


def test_support_missing_is_set_only_after_support_search_checked() -> None:
    unchecked = infer_selection_lessons(
        record=_record("배달로봇은 왜 길에서 멈추나"),
        representative=_candidate(
            "배달로봇은 왜 길에서 멈추나",
            "배달로봇과 전동 킥보드가 한국 보행자 정책과 충돌",
        ),
        second_search=None,
    )
    checked_missing = infer_selection_lessons(
        record=_record("배달로봇은 왜 길에서 멈추나"),
        representative=_candidate(
            "배달로봇은 왜 길에서 멈추나",
            "배달로봇과 전동 킥보드가 한국 보행자 정책과 충돌",
        ),
        second_search={"accepted_links": []},
    )

    assert unchecked["support_missing_requirements"] == []
    assert unchecked["support_status"] == "not_checked"
    assert "policy_or_stat" in checked_missing["support_missing_requirements"]
    assert checked_missing["support_status"] == "missing"
    assert any(
        item == {"key": "policy_or_stat", "severity": "critical"}
        for item in checked_missing["support_requirement_details"]
    )
