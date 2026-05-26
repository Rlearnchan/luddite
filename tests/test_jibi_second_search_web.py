import json

from luddite.agents.jibi.second_search_web import (
    NaverSearchProvider,
    SearchResult,
    render_markdown,
    run_web_second_search,
    write_web_second_search_outputs,
)


class FakeSearchProvider:
    name = "fake"

    def __init__(self) -> None:
        self.calls = []

    def search(
        self,
        query: str,
        *,
        category: str,
        max_results: int,
    ) -> list[SearchResult]:
        self.calls.append((query, category, max_results))
        return [
            SearchResult(
                title=f"{query} 보강 기사",
                url="https://news.example.com/supporting",
                snippet="방송 seed로 쓰려면 추가 근거가 필요하다는 내용.",
                source="news.example.com",
                published_at="Tue, 26 May 2026 09:00:00 +0900",
                provider=self.name,
                category=category,
                rank=1,
            ),
            SearchResult(
                title="원본 링크는 제외",
                url="https://example.com/original-rwa",
                source="example.com",
                provider=self.name,
                category=category,
                rank=2,
            ),
            SearchResult(
                title="중복 링크는 한 번만",
                url="https://news.example.com/supporting",
                source="news.example.com",
                provider=self.name,
                category=category,
                rank=3,
            ),
        ]


def _plan_payload():
    return {
        "run_date": "2026-05-26",
        "plans": [
            {
                "id": "rwa",
                "title": "자산 토큰화",
                "priority": "high",
                "actions": ["find_current_news_hook"],
                "topic_terms": ["자산 토큰화", "RWA"],
                "main_link": "https://example.com/original-rwa",
                "sub_links": ["https://example.com/original-support"],
                "query_plan": [
                    {
                        "action": "find_current_news_hook",
                        "queries": ["자산 토큰화 최신 뉴스", "자산 토큰화 사례"],
                    }
                ],
            },
            {
                "id": "low",
                "title": "낮은 우선순위 후보",
                "priority": "low",
                "actions": ["find_supporting_links"],
                "topic_terms": ["저우선"],
                "query_plan": [{"action": "find_supporting_links", "queries": ["저우선 검색"]}],
            },
        ],
    }


def test_run_web_second_search_uses_high_priority_and_dedupes_results() -> None:
    provider = FakeSearchProvider()

    payload = run_web_second_search(
        run_date="2026-05-26",
        plan_payload=_plan_payload(),
        provider=provider,
        categories=["news"],
        queries_per_plan=1,
        results_per_query=3,
        max_queries=10,
    )

    assert provider.calls == [("자산 토큰화 최신 뉴스", "news", 3)]
    assert payload["calls_used"] == 1
    assert payload["records_written"] == 1
    assert payload["accepted_by_review_item"] == {"rwa": 1}
    record = payload["records"][0]
    assert record["collector"] == "second_search_web"
    assert record["review_item_id"] == "rwa"
    assert record["search_query"] == "자산 토큰화 최신 뉴스"
    assert record["source_url_canonical"] == "https://news.example.com/supporting"
    assert "provider:fake" in record["tags"]


def test_naver_provider_maps_request_and_items() -> None:
    captured = {}

    def fake_get_json(url: str, headers: dict[str, str], timeout: float) -> dict:
        captured["url"] = url
        captured["headers"] = headers
        captured["timeout"] = timeout
        return {
            "items": [
                {
                    "title": "<b>자산</b> 토큰화",
                    "originallink": "https://www.example.com/article",
                    "link": "https://search.naver.com/redirect",
                    "description": "RWA &amp; STO 보강 기사",
                    "pubDate": "Tue, 26 May 2026 09:00:00 +0900",
                }
            ]
        }

    provider = NaverSearchProvider(
        client_id="client-id",
        client_secret="client-secret",
        http_get_json=fake_get_json,
    )

    results = provider.search("자산 토큰화", category="news", max_results=7)

    assert "/v1/search/news.json?" in captured["url"]
    assert "query=%EC%9E%90%EC%82%B0+%ED%86%A0%ED%81%B0%ED%99%94" in captured["url"]
    assert "display=7" in captured["url"]
    assert "sort=date" in captured["url"]
    assert captured["headers"]["X-Naver-Client-Id"] == "client-id"
    assert captured["headers"]["X-Naver-Client-Secret"] == "client-secret"
    assert results[0].title == "자산 토큰화"
    assert results[0].snippet == "RWA & STO 보강 기사"
    assert results[0].url == "https://www.example.com/article"
    assert results[0].source == "example.com"
    assert results[0].rank == 1


def test_write_web_second_search_outputs(tmp_path) -> None:
    plan_path = tmp_path / "plan.json"
    inbox_path = tmp_path / "second_search.jsonl"
    md_path = tmp_path / "second_search.md"
    json_path = tmp_path / "second_search.json"
    plan_path.write_text(
        json.dumps(_plan_payload(), ensure_ascii=False),
        encoding="utf-8",
    )

    outputs = write_web_second_search_outputs(
        run_date="2026-05-26",
        plan_path=plan_path,
        provider=FakeSearchProvider(),
        inbox_path=inbox_path,
        markdown_path=md_path,
        json_path=json_path,
        categories=["news"],
        priority_filter=["high"],
        queries_per_plan=1,
        results_per_query=3,
        max_queries=10,
    )

    assert outputs[0] == inbox_path
    assert outputs[1] == md_path
    assert outputs[2] == json_path
    assert inbox_path.read_text(encoding="utf-8").count("\n") == 1
    payload = json.loads(json_path.read_text(encoding="utf-8"))
    markdown = render_markdown(payload)
    assert "Jibi Web Second-Search" in markdown
    assert "자산 토큰화 최신 뉴스" in markdown
