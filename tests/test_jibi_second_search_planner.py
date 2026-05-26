import json

from luddite.agents.jibi.second_search_planner import (
    build_second_search_plan,
    render_markdown,
    write_second_search_plan,
)


def _feedback_summary():
    return {
        "run_date": "2026-05-26",
        "rows": [
            {
                "id": "2026-05-26:tokenization",
                "title": "집도, 채권도 쪼개 사고파는 시대: 자산 토큰화",
                "row_review_signal": "conditional",
                "row_failure_modes": ["needs_news_hook", "needs_supporting_links"],
                "row_positive_signals": [],
                "row_next_research_actions": [
                    "find_current_news_hook",
                    "find_supporting_links",
                ],
                "operator_lesson": "자산 토큰화: 자료 자체보다 최신 뉴스나 현상 hook을 먼저 찾아야 합니다.",
            },
            {
                "id": "2026-05-26:market",
                "title": "단일기업 유상증자 후보",
                "row_review_signal": "reject",
                "row_failure_modes": ["market_risk"],
                "row_positive_signals": [],
                "row_next_research_actions": ["avoid_market_advice_frame"],
                "operator_lesson": "현재 형태로는 낮추거나 제외하는 편이 안전합니다.",
            },
        ],
    }


def _metadata_payload():
    return {
        "rows": [
            {
                "ID": "2026-05-26:tokenization",
                "title": "집도, 채권도 쪼개 사고파는 시대: 자산 토큰화",
                "description": "핵심 질문은 '코인 가격이 아니라, 집과 채권의 권리를 토큰으로 쪼개면 누가 책임질까?'입니다.",
                "source": "한국은행",
                "source_role": "research_note",
                "seed_type": "policy_research_note",
                "story_role": "seed_with_supporting_links",
                "story_role_reasons": ["research_note_needs_current_news_hook"],
            },
            {
                "ID": "2026-05-26:market",
                "title": "단일기업 유상증자 후보",
                "source": "연합뉴스 경제",
                "source_role": "market_wire",
                "seed_type": "market_wire",
                "story_role": "demote_or_reject",
            },
        ]
    }


def test_build_second_search_plan_prioritizes_news_hook_and_supporting_links() -> None:
    plan = build_second_search_plan(
        run_date="2026-05-26",
        feedback_summary=_feedback_summary(),
        metadata_payload=_metadata_payload(),
    )

    first = plan["plans"][0]
    assert first["id"] == "2026-05-26:tokenization"
    assert first["priority"] == "high"
    assert "자산 토큰화" in first["topic_terms"]
    assert "연합뉴스" in first["source_suggestions"]
    queries = [
        query
        for task in first["query_plan"]
        for query in task.get("queries", [])
    ]
    assert "자산 토큰화 최신 뉴스" in queries
    assert "자산 토큰화 통계 사례" in queries


def test_render_markdown_includes_search_queue() -> None:
    plan = build_second_search_plan(
        run_date="2026-05-26",
        feedback_summary=_feedback_summary(),
        metadata_payload=_metadata_payload(),
    )

    markdown = render_markdown(plan)

    assert "# Jibi Second-Search Plan" in markdown
    assert "## Search Queue" in markdown
    assert "자산 토큰화 최신 뉴스" in markdown
    assert "avoid_market_advice_frame" in markdown


def test_write_second_search_plan_outputs_markdown_and_json(tmp_path) -> None:
    feedback_path = tmp_path / "feedback.json"
    metadata_path = tmp_path / "metadata.json"
    markdown_path = tmp_path / "plan.md"
    json_path = tmp_path / "plan.json"
    feedback_path.write_text(
        json.dumps(_feedback_summary(), ensure_ascii=False),
        encoding="utf-8",
    )
    metadata_path.write_text(
        json.dumps(_metadata_payload(), ensure_ascii=False),
        encoding="utf-8",
    )

    outputs = write_second_search_plan(
        run_date="2026-05-26",
        feedback_path=feedback_path,
        metadata_path=metadata_path,
        markdown_path=markdown_path,
        json_path=json_path,
    )

    assert outputs[0] == markdown_path
    assert outputs[1] == json_path
    assert markdown_path.exists()
    payload = json.loads(json_path.read_text(encoding="utf-8"))
    assert payload["planned_rows"] == 2
    assert payload["priority_counts"]["high"] == 1


def test_second_search_plan_backfills_old_feedback_json_shape() -> None:
    feedback = {
        "run_date": "2026-05-26",
        "rows": [
            {
                "id": "2026-05-26:old",
                "title": "낡은 피드백 형식 후보",
                "reviewers": {
                    "리뷰-형찬": {
                        "note": "이거 하나만 가져오면 자료로 만들 수 없다. 최신 뉴스 hook이 필요함.",
                        "tag": "unlabeled",
                    }
                },
            }
        ],
    }
    metadata = {
        "rows": [
            {
                "ID": "2026-05-26:old",
                "title": "낡은 피드백 형식 후보",
                "source": "한국은행",
                "source_role": "research_note",
                "seed_type": "policy_research_note",
            }
        ]
    }

    plan = build_second_search_plan(
        run_date="2026-05-26",
        feedback_summary=feedback,
        metadata_payload=metadata,
    )

    assert plan["planned_rows"] == 1
    assert plan["plans"][0]["priority"] == "high"
    assert "find_supporting_links" in plan["plans"][0]["actions"]
    assert "find_current_news_hook" in plan["plans"][0]["actions"]
