from luddite.agents.jibi.board_scoring import compute_board_score
from luddite.agents.jibi.selection_lessons import (
    SELECTION_LESSONS,
    detect_generic_visible_copy,
    infer_selection_lessons,
    recommend_quality_floor_visible_rows,
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


def test_sports_business_hook_uses_family_override_not_double_penalty() -> None:
    result = infer_selection_lessons(
        record=_record("월드컵 티켓값이 왜 이렇게 비싸졌나"),
        representative=_candidate(
            "월드컵 티켓값이 왜 이렇게 비싸졌나",
            "FIFA 월드컵 티켓 가격과 이벤트 비즈니스 이야기",
        ),
    )

    assert {"sports_primary_downrank", "sports_business_hook_only"}.issubset(
        result["selection_lessons"]
    )
    assert result["selection_lesson_role"] == "hook_only"
    assert -60 <= result["selection_lesson_score_delta"] <= -40
    assert result["selection_lesson_score_delta"] == -45
    assert result["selection_lesson_score_delta"] > -105


def test_sports_short_tokens_do_not_match_inside_english_words() -> None:
    for title, summary in [
        (
            "The best fans to keep you cool in 2026",
            "Sweaty, sleepless nights are now common in summer heatwaves.",
        ),
        (
            "Anthropic alliance with pope on AI harms",
            "The technology may be replacing workers and exploiting the environment.",
        ),
    ]:
        result = infer_selection_lessons(
            record=_record(title),
            representative=_candidate(title, summary),
        )

        assert "sports_primary_downrank" not in result["selection_lessons"]
        assert "sports_business_hook_only" not in result["selection_lessons"]


def test_anthropic_pope_ai_harms_does_not_trigger_sports_downrank() -> None:
    result = infer_selection_lessons(
        record=_record("Anthropic’s alliance with pope on AI harms"),
        representative=_candidate(
            "Anthropic’s alliance with pope on AI harms",
            "all in good faith or Vatican-washing?",
        ),
    )

    assert "sports_primary_downrank" not in result["selection_lessons"]
    assert "sports_business_hook_only" not in result["selection_lessons"]


def test_ibk_ai_misselling_vs_ssg_automation_is_false_positive_not_overlap() -> None:
    result = infer_selection_lessons(
        record=_record("IBK기업은행 AI 불완전판매 탐지 시스템"),
        representative=_candidate(
            "IBK기업은행 AI 불완전판매 탐지 시스템",
            "AI로 금융상품 불완전판매를 탐지하는 시스템",
        ),
        syuka_similarity={
            "recommendation": "duplicate",
            "top_match_title": "SSG닷컴 자동물류시스템 NE.O 센터",
            "matched_terms": ["도입", "시스템"],
            "reason": "broad keyword match",
        },
    )

    assert result["syuka_lesson_match_type"] == "false_positive"
    assert "syuka_similarity_false_positive_risk" in result["selection_lessons"]
    assert "past_syuka_overlap_needs_new_angle" not in result["selection_lessons"]
    assert "past_video_new_angle" not in result["critical_support_requirements"]


def test_energy_price_and_heatwave_is_broad_adjacent_not_critical_overlap() -> None:
    result = infer_selection_lessons(
        record=_record("전기요금은 왜 전쟁과 가스값을 따라 움직이나"),
        representative=_candidate(
            "전기요금은 왜 전쟁과 가스값을 따라 움직이나",
            "가스값과 전쟁, 전력망 투자가 가계 전기요금으로 이어진다",
        ),
        syuka_similarity={
            "recommendation": "adjacent",
            "top_match_title": "유럽이 40°C 폭염을 에어컨 없이 버텨야하는 이유",
            "matched_terms": ["전기요금", "폭염", "냉방"],
        },
        second_search={"accepted_links": []},
    )

    assert result["syuka_lesson_match_type"] == "broad_adjacent"
    assert "past_syuka_overlap_needs_new_angle" not in result["selection_lessons"]
    assert "past_video_new_angle" not in result["critical_support_requirements"]
    assert result["support_missing_requirements"] == []


def test_syuka_low_value_terms_are_hidden_from_display_terms() -> None:
    result = infer_selection_lessons(
        record=_record("[세종은 지금] 구윤철이 꽂힌 'AI 업무혁신'"),
        representative=_candidate(
            "[세종은 지금] 구윤철이 꽂힌 'AI 업무혁신'",
            "정부 AI 업무혁신 도입 기사",
        ),
        syuka_similarity={
            "recommendation": "adjacent",
            "matched_terms": ["세종은", "지금"],
        },
    )

    assert result["syuka_lesson_match_type"] == "weak_adjacent"
    assert result["syuka_lesson_display_terms"] == []
    assert result["syuka_lesson_low_value_terms"] == ["세종은", "지금"]
    assert result["syuka_lesson_low_value_warning"] is True


def test_energy_bill_candidate_is_main_seed_candidate() -> None:
    score = compute_board_score(
        record=_record("전기요금은 왜 전쟁과 가스값을 따라 움직이나"),
        representative=_candidate(
            "전기요금은 왜 전쟁과 가스값을 따라 움직이나",
            "가스값과 전쟁, 전력망 투자가 가계 전기요금으로 이어진다",
        ),
        history_rows=[],
        mismatch_reasons=[],
        syuka_similarity={
            "recommendation": "adjacent",
            "top_match_title": "유럽이 40°C 폭염을 에어컨 없이 버텨야하는 이유",
            "matched_terms": ["전기요금", "폭염", "냉방"],
        },
        second_search=None,
    )

    assert score["syuka_lesson_match_type"] == "broad_adjacent"
    assert score["main_seed_candidate"] is True


def test_free_delivery_hidden_cost_is_main_seed_candidate() -> None:
    score = compute_board_score(
        record=_record("무료배달은 누가 내나"),
        representative=_candidate(
            "무료배달은 누가 내나",
            "플랫폼 무료배달 경쟁의 비용이 점주와 소비자 가격으로 이동한다",
        ),
        history_rows=[],
        mismatch_reasons=[],
        syuka_similarity=None,
        second_search=None,
    )

    assert "platform_hidden_cost_bonus" in score["selection_lessons"]
    assert score["main_seed_candidate"] is True


def test_generic_visible_title_gets_warning() -> None:
    result = detect_generic_visible_copy(
        {
            "제목": "해외 후보, 한 가지 질문으로 더 좁혀볼 소재",
            "설명": "원문 하나만으로는 아직 결론을 내리기 이릅니다.",
        }
    )

    assert result["generic_visible_copy_warning"] is True
    assert "generic_title:해외 후보" in result["generic_visible_copy_reasons"]


def test_quality_floor_excludes_evidence_low_and_generic_rows() -> None:
    rows = [
        {"story_bundle_id": "strong", "title": "좋은 메인 후보", "board_score": 86},
        {"story_bundle_id": "sub", "title": "좋은 서브 후보", "board_score": 74},
        {
            "story_bundle_id": "generic",
            "title": "해외 후보",
            "board_score": 82,
            "generic_visible_copy_warning": True,
        },
        {
            "story_bundle_id": "evidence_low",
            "title": "근거 보강 후보",
            "board_score": 58,
            "editorial_role": "evidence",
            "editorial_role_confidence": "low",
        },
        {
            "story_bundle_id": "suppress",
            "title": "억제 후보",
            "board_score": 72,
            "selection_lesson_role": "suppress",
        },
    ]

    result = recommend_quality_floor_visible_rows(rows)

    assert {"generic", "evidence_low", "suppress"}.issubset(result["excluded_ids"])
    assert result["quality_floor_recommended_visible_count"] == 5


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
