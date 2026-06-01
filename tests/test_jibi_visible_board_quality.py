from luddite.agents.jibi.visible_board_quality import (
    classify_seed_readiness,
    evaluate_visible_board_row,
    recommend_quality_floor_visible_rows,
)


def test_final_visible_generic_title_is_detected_after_copy_render() -> None:
    result = evaluate_visible_board_row(
        row={
            "제목": "해외 후보, 한 가지 질문으로 더 좁혀볼 소재",
            "설명": "원문 하나만으로는 아직 결론을 내리기 이릅니다.",
        },
        metadata={},
        board_score={"board_score": 60},
    )

    assert result["generic_visible_copy_warning"] is True
    assert result["visible_quality_status"] == "generic_backfill"
    assert result["would_hide_if_quality_floor_active"] is True
    assert result["quality_floor_exclusion_reason"] == "generic_visible_copy_warning"


def test_sejong_ai_work_innovation_is_not_ready_seed_candidate() -> None:
    result = classify_seed_readiness(
        {
            "title": "[세종은 지금] 구윤철이 꽂힌 'AI 업무혁신'",
            "board_score": 85.4,
            "source_role": "market_wire",
            "story_role": "seed_with_supporting_links",
            "seed_quality_classification": "conditional_seed",
            "second_search_accepted_links_count": 0,
            "support_status": "not_required",
            "frame_options": [
                {
                    "needs": [
                        "공공 AI 가이드라인",
                        "오판·감사 사례",
                        "기관별 책임 규정",
                    ]
                }
            ],
            "support_requirements": [],
            "visible_description": "generic_why_without_specific_template",
            "syuka_lesson_match_type": "weak_adjacent",
            "syuka_lesson_shared_terms": ["세종은", "지금"],
        }
    )

    assert result["main_seed_candidate"] in {True, False}
    assert result["ready_seed_candidate"] is False
    assert result["seed_readiness_level"] == "needs_support"
    assert "second_search_required" in result["required_before_ready"]


def test_quality_floor_uses_final_visible_copy_not_pre_copy_title() -> None:
    visible = evaluate_visible_board_row(
        row={
            "제목": "해외 후보, 한 가지 질문으로 더 좁혀볼 소재",
            "설명": "원문 하나만으로는 아직 결론을 내리기 이릅니다.",
        },
        metadata={"story_bundle_id": "generic_visible"},
        board_score={"board_score": 60},
    )
    result = recommend_quality_floor_visible_rows(
        [{"story_bundle_id": "generic_visible", "title": "원래 제목", **visible}]
    )

    assert result["quality_floor_excluded_count"] == 1
    assert result["would_hide_if_quality_floor_active_count"] == 1
    assert result["quality_floor_excluded_rows"][0]["reason"] == (
        "generic_visible_copy_warning"
    )
