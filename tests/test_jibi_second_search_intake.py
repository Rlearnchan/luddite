import json

from luddite.agents.jibi.second_search_intake import (
    build_second_search_intake,
    render_markdown,
    write_second_search_intake,
)


def _feedback_payload():
    return {
        "run_date": "2026-05-26",
        "rows": [
            {
                "id": "rwa",
                "title": "자산 토큰화",
                "operator_lesson": "최신 뉴스 hook과 보강 링크가 필요합니다.",
            },
            {
                "id": "market",
                "title": "시장성 후보",
                "operator_lesson": "현재 형태로는 낮추는 편이 안전합니다.",
            },
            {
                "id": "empty",
                "title": "보강 필요 후보",
                "operator_lesson": "아직 자료가 부족합니다.",
            },
        ],
    }


def _plan_payload():
    return {
        "run_date": "2026-05-26",
        "plans": [
            {
                "id": "rwa",
                "title": "자산 토큰화",
                "priority": "high",
                "actions": ["find_supporting_links"],
                "why_search": "자산 토큰화는 최신 hook이 필요합니다.",
            },
            {
                "id": "market",
                "title": "시장성 후보",
                "priority": "low",
                "actions": ["avoid_market_advice_frame"],
                "why_search": "시장성 후보는 낮추는 편이 안전합니다.",
            },
            {
                "id": "empty",
                "title": "보강 필요 후보",
                "priority": "high",
                "actions": ["find_current_news_hook"],
                "why_search": "자료가 부족합니다.",
            },
            {
                "id": "evidence",
                "title": "근거 자료 후보",
                "priority": "low",
                "actions": ["demote_to_evidence_or_background"],
                "why_search": "근거로 낮춥니다.",
            },
        ],
    }


def _local_payload():
    return {
        "rows": [
            {
                "id": "rwa",
                "title": "자산 토큰화",
                "top_matches": [
                    {
                        "collector": "second_search_local",
                        "title": "금융위 자산 토큰화 논의",
                        "source": "연합뉴스",
                        "url": "https://example.com/local-rwa",
                        "matched_terms": ["자산 토큰화"],
                        "relevance_status": "accepted_local_match",
                    }
                ],
            }
        ]
    }


def _web_payload():
    return {
        "records": [
            {
                "collector": "second_search_web",
                "evidence_role": "supporting_link_candidate",
                "review_item_id": "rwa",
                "review_title": "자산 토큰화",
                "title": "토큰화 증권 제도 보강 기사",
                "source": "example-news",
                "url": "https://example.com/web-rwa",
                "search_query": "자산 토큰화 제도",
                "query_type": "broader_system",
                "matched_terms": ["자산", "토큰화"],
                "relevance_status": "accepted",
            }
        ],
        "query_runs": [
            {
                "review_item_id": "rwa",
                "returned": 3,
                "accepted": 1,
                "rejected_low_relevance": 1,
            },
            {
                "review_item_id": "empty",
                "returned": 0,
                "accepted": 0,
                "rejected_low_relevance": 0,
            },
        ],
    }


def test_build_second_search_intake_merges_local_and_web_results() -> None:
    payload = build_second_search_intake(
        run_date="2026-05-26",
        feedback_payload=_feedback_payload(),
        plan_payload=_plan_payload(),
        local_payload=_local_payload(),
        web_payload=_web_payload(),
        web_inbox_records=[],
        input_status={
            "feedback": "loaded",
            "plan": "loaded",
            "local": "loaded",
            "web": "loaded",
            "web_inbox": "not_run",
        },
    )

    rows = {row["review_item_id"]: row for row in payload["rows"]}
    assert rows["rwa"]["follow_up_status"] == "enough_supporting_links"
    assert rows["rwa"]["local_supporting_matches_count"] == 1
    assert rows["rwa"]["web_supporting_matches_count"] == 1
    assert rows["rwa"]["rejected_low_relevance_count"] == 1
    assert rows["empty"]["follow_up_status"] == "still_needs_sources"
    assert rows["market"]["follow_up_status"] == "reject_or_defer"
    assert rows["evidence"]["follow_up_status"] == "evidence_only"


def test_write_second_search_intake_treats_missing_inputs_as_not_run(tmp_path) -> None:
    feedback_path = tmp_path / "feedback.json"
    plan_path = tmp_path / "plan.json"
    local_path = tmp_path / "missing-local.json"
    web_path = tmp_path / "missing-web.json"
    inbox_path = tmp_path / "missing-web.jsonl"
    md_path = tmp_path / "intake.md"
    json_path = tmp_path / "intake.json"
    feedback_path.write_text(
        json.dumps(_feedback_payload(), ensure_ascii=False),
        encoding="utf-8",
    )
    plan_path.write_text(
        json.dumps(_plan_payload(), ensure_ascii=False),
        encoding="utf-8",
    )

    outputs = write_second_search_intake(
        run_date="2026-05-26",
        feedback_path=feedback_path,
        plan_path=plan_path,
        local_path=local_path,
        web_path=web_path,
        web_inbox_path=inbox_path,
        markdown_path=md_path,
        json_path=json_path,
    )

    assert outputs[0] == md_path
    assert outputs[1] == json_path
    payload = json.loads(json_path.read_text(encoding="utf-8"))
    assert payload["input_status"]["local"] == "not_run"
    assert payload["input_status"]["web"] == "not_run"
    assert payload["input_status"]["web_inbox"] == "not_run"
    markdown = render_markdown(payload)
    assert "Jibi Second-Search Evidence Intake" in markdown
