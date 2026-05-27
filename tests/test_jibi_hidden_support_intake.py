import json

from luddite.agents.jibi.hidden_support_intake import (
    build_hidden_support_intake,
    render_markdown,
    write_hidden_support_intake,
)


def _feedback_payload():
    return {
        "run_date": "2026-05-27",
        "rows": [
            {
                "id": "ai-vlog",
                "title": "AI가 역사를 브이로그로 만들기 시작했다",
                "row_review_signal": "weak",
                "row_failure_modes": ["needs_supporting_links"],
                "row_positive_signals": ["fresh_angle", "specific_case_needed"],
                "row_next_research_actions": ["find_supporting_links"],
                "operator_lesson": "병렬 사례를 더 찾아야 합니다.",
                "reviewers": {
                    "리뷰-형찬": {
                        "raw_note": (
                            "비슷한 사례가 병렬적으로 더 있을 것 같은데 "
                            "더 서치했으면 좋겠다."
                        )
                    }
                },
            },
            {
                "id": "worldcup",
                "title": "월드컵 티켓값은 어디로 가나",
                "row_review_signal": "weak",
                "row_failure_modes": ["weak_audience_bridge"],
                "row_positive_signals": [],
                "row_next_research_actions": [],
                "operator_lesson": "스포츠 자체로 깊이 파면 약합니다.",
                "reviewers": {
                    "리뷰-동찬": {
                        "raw_note": (
                            "스포츠를 소재로 다른 내용으로 흘러가면 상관없지만 "
                            "주구장창 스포츠면 안된다."
                        )
                    }
                },
            },
            {
                "id": "egg",
                "title": "계란값은 왜 매번 식탁 물가 뉴스가 되나",
                "row_review_signal": "weak",
                "row_failure_modes": ["too_familiar"],
                "row_positive_signals": [],
                "row_next_research_actions": ["check_past_topic_differentiation"],
                "operator_lesson": "이미 익숙한 주제입니다.",
                "reviewers": {
                    "리뷰-형찬": {"raw_note": "사람들도 다 아는 내용이라 novelty가 없다."}
                },
            },
            {
                "id": "robot",
                "title": "배달로봇은 왜 불쌍하고 짜증날까",
                "row_review_signal": "unlabeled",
                "row_failure_modes": [],
                "row_positive_signals": [],
                "row_next_research_actions": [],
                "operator_lesson": "정책이나 통계가 필요합니다.",
                "reviewers": {
                    "리뷰-동찬": {
                        "raw_note": (
                            "관련된 정책이 새로 나왔다던지, "
                            "관련된 통계나 여론조사가 있어야 한다."
                        )
                    }
                },
            },
        ],
    }


def _hidden_support_payload():
    return {
        "run_date": "2026-05-27",
        "rows": [
            {
                "review_item_id": "ai-vlog",
                "review_title": "AI가 역사를 브이로그로 만들기 시작했다",
                "hidden_support_status": "hidden_support_ready",
                "accepted_count": 2,
                "rejected_low_relevance_count": 1,
                "selected_link_details": [
                    {
                        "title": "AI 역사 영상 사례",
                        "url": "https://example.com/ai-history",
                        "source": "example",
                        "query_type": "system_context",
                        "usefulness_score": 12,
                    },
                    {
                        "title": "AI 교육 영상 활용",
                        "url": "https://example.com/ai-education",
                        "source": "example",
                        "query_type": "origin_precision",
                        "usefulness_score": 10,
                    },
                ],
            },
            {
                "review_item_id": "worldcup",
                "review_title": "월드컵 티켓값은 어디로 가나",
                "hidden_support_status": "one_hidden_support_link",
                "accepted_count": 1,
                "selected_link_details": [
                    {
                        "title": "FIFA 티켓 가격",
                        "url": "https://example.com/worldcup",
                        "source": "example",
                        "query_type": "origin_title",
                        "usefulness_score": 9,
                    }
                ],
            },
            {
                "review_item_id": "egg",
                "review_title": "계란값은 왜 매번 식탁 물가 뉴스가 되나",
                "hidden_support_status": "no_hidden_support_found",
                "accepted_count": 0,
                "selected_link_details": [],
            },
            {
                "review_item_id": "robot",
                "review_title": "배달로봇은 왜 불쌍하고 짜증날까",
                "hidden_support_status": "one_hidden_support_link",
                "accepted_count": 1,
                "selected_link_details": [
                    {
                        "title": "배달로봇 정책",
                        "url": "https://example.com/robot-policy",
                        "source": "example",
                        "query_type": "system_context",
                        "usefulness_score": 9,
                    }
                ],
            },
        ],
    }


def test_build_hidden_support_intake_joins_review_needs_with_presearched_links():
    payload = build_hidden_support_intake(
        run_date="2026-05-27",
        feedback_payload=_feedback_payload(),
        hidden_support_payload=_hidden_support_payload(),
        input_status={"feedback": "loaded", "hidden_support": "loaded"},
    )

    rows = {row["review_item_id"]: row for row in payload["rows"]}
    assert rows["ai-vlog"]["review_support_status"] == "hidden_support_can_test_review_need"
    assert rows["ai-vlog"]["hidden_selected_count"] == 2
    assert rows["ai-vlog"]["recommended_next_step"] == "use_hidden_links_for_followup_pack"
    assert rows["worldcup"]["review_support_status"] == "do_not_rescue_with_links_only"
    assert rows["egg"]["review_support_status"] == "needs_new_angle_not_more_links"
    assert (
        rows["robot"]["review_support_status"]
        == "support_available_needs_relevance_review"
    )
    assert payload["review_need_counts"]["supporting_links"] == 1


def test_write_hidden_support_intake_treats_missing_hidden_run_as_not_run(tmp_path):
    feedback_path = tmp_path / "feedback.json"
    hidden_path = tmp_path / "missing.json"
    md_path = tmp_path / "intake.md"
    json_path = tmp_path / "intake.json"
    feedback_path.write_text(
        json.dumps(_feedback_payload(), ensure_ascii=False),
        encoding="utf-8",
    )

    outputs = write_hidden_support_intake(
        run_date="2026-05-27",
        feedback_path=feedback_path,
        hidden_support_path=hidden_path,
        markdown_path=md_path,
        json_path=json_path,
    )

    assert outputs[0] == md_path
    payload = json.loads(json_path.read_text(encoding="utf-8"))
    assert payload["input_status"]["hidden_support"] == "not_run"
    assert {
        row["review_support_status"] for row in payload["rows"]
    } == {"hidden_support_not_run"}
    assert "Jibi Hidden Support Intake" in render_markdown(payload)
