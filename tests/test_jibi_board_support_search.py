import csv
import json

from luddite.agents.jibi.append_to_sheet import BUNDLE_REVIEW_SHEET_COLUMNS
from luddite.agents.jibi.board_support_search import enrich_review_board_support_links
from luddite.agents.jibi.second_search_web import SearchResult


class FakeProvider:
    name = "fake"

    def __init__(self) -> None:
        self.calls = []

    def search(self, query, *, category, max_results):
        self.calls.append((query, category, max_results))
        if "임금" in query or "통계" in query:
            return [
                SearchResult(
                    title="AI 인재 부족과 임금 프리미엄 분석",
                    url="https://news.kbs.co.kr/news/pc/view/view.do?ncd=8357774",
                    snippet="AI 인재 부족, 임금 프리미엄, 기업 이동성 격차를 분석했다.",
                    source="kbs.co.kr",
                    provider=self.name,
                    category=category,
                    rank=1,
                ),
                SearchResult(
                    title="AI 인재 행사 경품 이벤트",
                    url="https://promo.example.com/event",
                    snippet="AI 인재 관련 이벤트와 경품 안내",
                    source="promo.example.com",
                    provider=self.name,
                    category=category,
                    rank=2,
                )
            ]
        if "AI 인재" in query:
            return [
                SearchResult(
                    title="AI 인재 부족과 임금 프리미엄 분석",
                    url="https://news.example.com/ai-talent",
                    snippet="AI 인재 부족 임금 이동성 격차를 분석했다.",
                    source="news.example.com",
                    provider=self.name,
                    category=category,
                    rank=1,
                ),
                SearchResult(
                    title="야구 경기 결과",
                    url="https://sports.example.com/baseball",
                    snippet="무관한 스포츠 기사",
                    source="sports.example.com",
                    provider=self.name,
                    category=category,
                    rank=2,
                ),
            ]
        return []


def test_enrich_review_board_support_links_updates_csv_and_metadata(tmp_path) -> None:
    csv_path = tmp_path / "2026-05-27_bundle_review_sheet.csv"
    with csv_path.open("w", encoding="utf-8-sig", newline="") as output:
        writer = csv.DictWriter(output, fieldnames=BUNDLE_REVIEW_SHEET_COLUMNS)
        writer.writeheader()
        writer.writerow(
            {
                "일시": "2026-05-26 23:00",
                "제목": "AI 인재 부족은 왜 매번 반복될까",
                "점수": "B · 75점",
                "메인 링크": "https://www.bok.or.kr/ai-talent",
                "서브 링크": "",
                "설명": (
                    "AI 인재의 규모, 임금, 기업 간 이동성, 지역 격차를 숫자로 볼 수 있습니다."
                ),
                "리뷰-성원": "",
                "리뷰-동찬": "",
                "리뷰-형찬": "",
                "ID": "2026-05-27:story_bundle_ai",
            }
        )
    metadata_path = tmp_path / "2026-05-27_bundle_review_sheet_metadata.json"
    metadata_path.write_text(
        json.dumps(
            {
                "run_date": "2026-05-27",
                "rows": [
                    {
                        "ID": "2026-05-27:story_bundle_ai",
                        "review_item_id": "2026-05-27:story_bundle_ai",
                        "source": "한국은행",
                        "main_link": "https://www.bok.or.kr/ai-talent",
                        "sub_links": [],
                    }
                ],
            },
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )

    payload = enrich_review_board_support_links(
        run_date="2026-05-27",
        board_csv_path=csv_path,
        metadata_path=metadata_path,
        provider=FakeProvider(),
        markdown_path=tmp_path / "support.md",
        json_path=tmp_path / "support.json",
        categories=["news"],
        max_links_per_row=1,
        max_provider_calls=2,
    )

    with csv_path.open(encoding="utf-8-sig", newline="") as source:
        rows = list(csv.DictReader(source))
    metadata = json.loads(metadata_path.read_text(encoding="utf-8"))

    assert rows[0]["서브 링크"].startswith(
        "1. https://news.kbs.co.kr/news/pc/view/view.do?ncd=8357774"
    )
    assert rows[0]["서브 링크"].count("\n") == 0
    assert "서브 링크는 kbs.co.kr의 보강 자료 1개만 남겼습니다." in rows[0]["설명"]
    assert "선택 이유:" in rows[0]["설명"]
    assert "대중 매체 보강 자료" in rows[0]["설명"]
    assert "news.example.com/ai-talent" not in rows[0]["서브 링크"]
    assert "sports.example.com" not in rows[0]["서브 링크"]
    assert metadata["rows"][0]["sub_links"] == [
        "https://news.kbs.co.kr/news/pc/view/view.do?ncd=8357774"
    ]
    support = metadata["rows"][0]["board_support_search"]
    assert support["accepted_count"] >= 1
    assert support["selected_link_details"][0]["score"] >= 8
    assert payload["selected_links_total"] == 1
