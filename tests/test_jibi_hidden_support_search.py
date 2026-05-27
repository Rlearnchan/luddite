import json

from luddite.agents.jibi.hidden_support_search import (
    render_markdown,
    run_hidden_support_search,
    write_hidden_support_search,
)
from luddite.agents.jibi.second_search_web import SearchResult


class FakeHiddenSupportProvider:
    name = "fake"

    def __init__(self) -> None:
        self.calls = []

    def search(self, query, *, category, max_results):
        self.calls.append((query, category, max_results))
        if "열사병" in query or "산업현장" in query:
            return [
                SearchResult(
                    title="산업현장 열사병 산재 예방 대책 강화",
                    url="https://www.moel.go.kr/heat-safety",
                    snippet="폭염, 열사병, 작업중지권, 산업현장 안전 대책을 설명했다.",
                    source="moel.go.kr",
                    provider=self.name,
                    category=category,
                    rank=1,
                ),
                SearchResult(
                    title="반바지 입어도 되나요",
                    url="https://example.com/shorts",
                    snippet="쿨비즈 복장문화 이야기",
                    source="example.com",
                    provider=self.name,
                    category=category,
                    rank=2,
                ),
            ]
        if "AI" in query or "인공지능" in query:
            return [
                SearchResult(
                    title="AI 업무자동화 행사 안내",
                    url="https://event.example.com/ai",
                    snippet="AI 행사와 경품 안내",
                    source="event.example.com",
                    provider=self.name,
                    category=category,
                    rank=1,
                ),
                SearchResult(
                    title="AI 업무자동화 책임과 노동시장 변화",
                    url="https://news.kbs.co.kr/news/pc/view/view.do?ncd=8450000",
                    snippet="AI 업무자동화, 책임, 노동시장, 규제 사례를 분석했다.",
                    source="kbs.co.kr",
                    provider=self.name,
                    category=category,
                    rank=2,
                ),
            ]
        return []


def _metadata_payload() -> dict:
    return {
        "run_date": "2026-05-27",
        "rows": [
            {
                "ID": "2026-05-27:story_bundle_heat",
                "review_item_id": "2026-05-27:story_bundle_heat",
                "title": "반바지가 복지가 되는 시대",
                "auto_title": "산업현장 열사병 예방 대책",
                "description": "폭염 때문에 반바지와 쿨비즈를 이야기할 수 있습니다.",
                "source": "연합뉴스",
                "source_role": "public_wire",
                "seed_type": "workplace_safety",
                "main_link": "https://www.yna.co.kr/view/AKR202605270001",
                "sub_links": [],
            }
        ],
    }


def test_hidden_support_uses_origin_metadata_not_visible_copy(tmp_path) -> None:
    metadata_path = tmp_path / "metadata.json"
    metadata_path.write_text(
        json.dumps(_metadata_payload(), ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    original = metadata_path.read_text(encoding="utf-8")
    provider = FakeHiddenSupportProvider()

    md_path, json_path, payload = write_hidden_support_search(
        run_date="2026-05-27",
        metadata_path=metadata_path,
        provider=provider,
        markdown_path=tmp_path / "hidden.md",
        json_path=tmp_path / "hidden.json",
        categories=["news"],
        max_links_per_row=1,
        results_per_query=2,
        max_provider_calls=5,
    )

    queries = [call[0] for call in provider.calls]
    assert queries
    assert all("반바지" not in query for query in queries)
    assert all("쿨비즈" not in query for query in queries)
    assert any("열사병" in query or "산업현장" in query for query in queries)
    assert metadata_path.read_text(encoding="utf-8") == original
    assert payload["rows"][0]["query_basis"] == "origin_metadata_only"
    assert payload["rows"][0]["selected_links"] == ["https://www.moel.go.kr/heat-safety"]
    assert "서브 링크" not in json_path.read_text(encoding="utf-8")
    markdown = md_path.read_text(encoding="utf-8")
    assert "Google Sheet의 `서브 링크`나 `설명`은 수정하지 않습니다." in markdown


def test_hidden_support_filters_low_relevance_and_reports_status() -> None:
    payload = {
        "run_date": "2026-05-27",
        "rows": [
            {
                "ID": "2026-05-27:story_bundle_ai",
                "title": "AI가 사무실 일을 바꾸는 속도",
                "auto_title": "AI 업무자동화와 노동시장 변화",
                "source": "연합뉴스",
                "source_role": "public_wire",
                "seed_type": "workplace_ai_transition",
                "main_link": "https://www.yna.co.kr/view/AKR202605270002",
            }
        ],
    }

    result = run_hidden_support_search(
        run_date="2026-05-27",
        metadata_payload=payload,
        provider=FakeHiddenSupportProvider(),
        categories=["news"],
        max_links_per_row=1,
        results_per_query=2,
        max_provider_calls=5,
    )

    row = result["rows"][0]
    assert row["hidden_support_status"] == "one_hidden_support_link"
    assert row["selected_links"] == [
        "https://news.kbs.co.kr/news/pc/view/view.do?ncd=8450000"
    ]
    assert row["rejected_low_relevance_count"] >= 1
    assert row["selected_link_details"][0]["usefulness_score"] >= 8
    assert "Jibi Hidden Support Search" in render_markdown(result)


def test_hidden_support_does_not_treat_dairy_as_ai_signal() -> None:
    payload = {
        "run_date": "2026-05-27",
        "rows": [
            {
                "ID": "2026-05-27:story_bundle_dairy",
                "title": "배터리 소는 왜 생겼나",
                "auto_title": "Battery cows and dairy farming pressure",
                "source": "The Guardian Environment",
                "source_role": "section_news",
                "seed_type": "life_change",
                "main_link": "https://www.theguardian.com/environment/battery-cows",
            }
        ],
    }
    provider = FakeHiddenSupportProvider()

    run_hidden_support_search(
        run_date="2026-05-27",
        metadata_payload=payload,
        provider=provider,
        categories=["news"],
        max_links_per_row=1,
        results_per_query=2,
        max_provider_calls=5,
    )

    queries = [call[0] for call in provider.calls]
    assert queries
    assert all("AI 도입 책임" not in query for query in queries)
