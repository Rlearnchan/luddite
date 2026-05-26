import json

from luddite.agents.jibi.second_search_runner import (
    load_article_pool,
    render_markdown,
    run_local_second_search,
    write_local_second_search_results,
)
from luddite.utils.jsonl import write_jsonl


def _plan_payload():
    return {
        "run_date": "2026-05-26",
        "plans": [
            {
                "id": "tokenization",
                "title": "집도, 채권도 쪼개 사고파는 시대: 자산 토큰화",
                "priority": "high",
                "actions": ["find_current_news_hook", "find_supporting_links"],
                "topic_terms": ["자산 토큰화", "RWA", "STO", "조각투자"],
                "main_link": "https://example.com/original-rwa",
                "sub_links": [],
                "source_suggestions": ["연합뉴스", "한국은행"],
                "query_plan": [
                    {
                        "action": "find_current_news_hook",
                        "queries": ["자산 토큰화 최신 뉴스", "자산 토큰화 2026"],
                    }
                ],
            },
            {
                "id": "weak",
                "title": "매칭 없는 후보",
                "priority": "low",
                "actions": ["find_supporting_links"],
                "topic_terms": ["희귀한없는단어"],
                "query_plan": [
                    {
                        "action": "find_supporting_links",
                        "queries": ["희귀한없는단어 사례"],
                    }
                ],
            },
        ],
    }


def _articles():
    return [
        {
            "article_id": "supporting",
            "title": "금융위, 자산 토큰화 제도 개선 논의",
            "raw_summary": "RWA와 STO 조각투자 관련 규제 쟁점이 다시 부상했다.",
            "source": "연합뉴스 경제",
            "published_at": "2026-05-26T00:00:00+09:00",
            "url": "https://example.com/supporting-rwa",
        },
        {
            "article_id": "original",
            "title": "한국은행 자산 토큰화 이슈노트",
            "raw_summary": "원래 보드에 올라간 링크",
            "source": "한국은행",
            "url": "https://example.com/original-rwa",
        },
        {
            "article_id": "unrelated",
            "title": "스포츠 경기 결과",
            "raw_summary": "축구 결과",
            "source": "BBC",
            "url": "https://example.com/sports",
        },
    ]


def test_run_local_second_search_matches_supporting_articles_and_excludes_self() -> None:
    result = run_local_second_search(
        run_date="2026-05-26",
        plan_payload=_plan_payload(),
        article_pool=_articles(),
    )

    assert result["plan_rows"] == 2
    assert result["matched_rows"] == 1
    first = result["rows"][0]
    assert first["id"] == "tokenization"
    assert first["match_count"] == 1
    assert first["top_matches"][0]["title"] == "금융위, 자산 토큰화 제도 개선 논의"
    assert first["top_matches"][0]["collector"] == "second_search_local"
    assert first["top_matches"][0]["evidence_role"] == "supporting_link_candidate"
    assert first["top_matches"][0]["review_item_id"] == "tokenization"
    assert first["top_matches"][0]["relevance_status"] == "accepted_local_match"
    assert "자산 토큰화" in first["top_matches"][0]["matched_terms"]


def test_render_local_second_search_markdown() -> None:
    result = run_local_second_search(
        run_date="2026-05-26",
        plan_payload=_plan_payload(),
        article_pool=_articles(),
    )

    markdown = render_markdown(result)

    assert "# Jibi Local Second-Search Results" in markdown
    assert "자산 토큰화" in markdown
    assert "local_matches: none" in markdown


def test_write_local_second_search_results_uses_jsonl_pools(tmp_path) -> None:
    plan_path = tmp_path / "plan.json"
    pool_path = tmp_path / "pool.jsonl"
    md_path = tmp_path / "results.md"
    json_path = tmp_path / "results.json"
    plan_path.write_text(
        json.dumps(_plan_payload(), ensure_ascii=False),
        encoding="utf-8",
    )
    write_jsonl(pool_path, _articles())

    outputs = write_local_second_search_results(
        run_date="2026-05-26",
        plan_path=plan_path,
        article_paths=[pool_path],
        markdown_path=md_path,
        json_path=json_path,
    )

    assert outputs[0] == md_path
    assert outputs[1] == json_path
    payload = json.loads(json_path.read_text(encoding="utf-8"))
    assert payload["matched_rows"] == 1
    assert load_article_pool([pool_path])[0]["article_id"] == "supporting"


def test_local_second_search_short_terms_do_not_match_inside_other_words() -> None:
    plan = {
        "run_date": "2026-05-26",
        "plans": [
            {
                "id": "ai",
                "title": "공공 AI 후보",
                "priority": "high",
                "actions": ["find_supporting_links"],
                "topic_terms": ["공공 AI", "AI", "유가"],
                "query_plan": [],
            }
        ],
    }
    articles = [
        {
            "article_id": "false_ai",
            "title": "Starmer says case remains under review",
            "raw_summary": "The prime minister said it was right.",
            "source": "BBC",
            "url": "https://example.com/false-ai",
        },
        {
            "article_id": "false_oil",
            "title": "다시 올릴 이유가 분명한 후보",
            "raw_summary": "이유가 충분하다는 평가",
            "source": "example",
            "url": "https://example.com/false-oil",
        },
        {
            "article_id": "true_ai",
            "title": "공공 AI 도입 확대",
            "raw_summary": "AI 활용 가이드라인 논의",
            "source": "연합뉴스",
            "url": "https://example.com/true-ai",
        },
    ]

    result = run_local_second_search(
        run_date="2026-05-26",
        plan_payload=plan,
        article_pool=articles,
    )

    matches = result["rows"][0]["top_matches"]
    assert [item["article_id"] for item in matches] == ["true_ai"]
