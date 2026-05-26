import json

from luddite.agents.jibi.second_search_web import (
    NaverSearchProvider,
    SearchResult,
    load_env_file,
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
        supporting_url = (
            "https://news.example.com/supporting-broader"
            if "투자자 보호" in query
            else "https://news.example.com/supporting"
        )
        return [
            SearchResult(
                title="확률적 생성의 덫 AI 환각 문제 지속",
                url="https://news.example.com/off-topic-ai",
                snippet="통계와 사례가 필요하다는 일반론.",
                source="news.example.com",
                provider=self.name,
                category=category,
                rank=0,
            ),
            SearchResult(
                title=f"{query} 보강 기사",
                url=supporting_url,
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
                url=supporting_url,
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
                        "query_type": "precision",
                        "queries": ["자산 토큰화 최신 뉴스", "자산 토큰화 사례"],
                    },
                    {
                        "action": "find_current_news_hook",
                        "query_type": "broader_system",
                        "queries": ["토큰화 증권 제도 투자자 보호 금융 인프라"],
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
        queries_per_plan=2,
        results_per_query=3,
        max_queries=10,
    )

    assert provider.calls == [
        ("자산 토큰화 최신 뉴스", "news", 3),
        ("토큰화 증권 제도 투자자 보호 금융 인프라", "news", 3),
    ]
    assert payload["calls_used"] == 2
    assert payload["query_runs"][0]["rejected_low_relevance"] == 1
    assert payload["query_runs"][0]["query_type"] == "precision"
    assert payload["query_runs"][1]["query_type"] == "broader_system"
    assert payload["rejected_low_relevance"] == 2
    assert payload["records_written"] == 2
    assert payload["accepted_by_review_item"] == {"rwa": 2}
    record = payload["records"][0]
    assert record["collector"] == "second_search_web"
    assert record["evidence_role"] == "supporting_link_candidate"
    assert record["review_item_id"] == "rwa"
    assert record["search_query"] == "자산 토큰화 최신 뉴스"
    assert record["query_type"] == "precision"
    assert record["relevance_status"] == "accepted"
    assert record["source_url_canonical"] == "https://news.example.com/supporting"
    assert record["matched_terms"] == ["자산", "토큰화"]
    assert record["search_relevance_terms"] == ["자산", "토큰화"]
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


def test_load_env_file_sets_missing_values_without_overriding(tmp_path, monkeypatch) -> None:
    env_path = tmp_path / ".env.local"
    env_path.write_text(
        "NAVER_SEARCH_CLIENT_ID=file-client\n"
        "NAVER_SEARCH_CLIENT_SECRET='file-secret'\n"
        "EXISTING=from-file\n",
        encoding="utf-8",
    )
    monkeypatch.setenv("EXISTING", "already-set")
    monkeypatch.delenv("NAVER_SEARCH_CLIENT_ID", raising=False)
    monkeypatch.delenv("NAVER_SEARCH_CLIENT_SECRET", raising=False)

    loaded = load_env_file(env_path)

    assert loaded == ["NAVER_SEARCH_CLIENT_ID", "NAVER_SEARCH_CLIENT_SECRET"]
    assert NaverSearchProvider.from_env().client_id == "file-client"
    assert NaverSearchProvider.from_env().client_secret == "file-secret"
    assert loaded_env_value("EXISTING") == "already-set"


def loaded_env_value(key: str) -> str:
    import os

    return os.environ[key]


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
