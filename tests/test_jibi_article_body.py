import json

from luddite.agents.jibi.article_body import (
    ArticleTarget,
    collect_article_targets,
    fetch_article_bodies,
    run_article_body_fetch,
)
from luddite.collectors.rss_probe import HttpResponse


class FakeHttpClient:
    def __init__(self, response_by_url):
        self.response_by_url = response_by_url
        self.calls = []

    def fetch(self, url: str, *, timeout: float) -> HttpResponse:
        self.calls.append((url, timeout))
        response = self.response_by_url[url]
        if isinstance(response, Exception):
            raise response
        return response


class FakeLlmClient:
    model = "gpt-5-mini"

    def json_response(
        self,
        prompt: str,
        *,
        timeout_seconds: int = 120,
        max_output_tokens: int = 1200,
    ):
        assert "article body could not be fetched" in prompt
        return (
            json.dumps(
                {
                    "translated_title_ko": "테스트 기사",
                    "summary_ko": (
                        "본문 수집 실패 시 RSS 메타데이터만 바탕으로 만든 "
                        "한국어 요약입니다."
                    ),
                    "likely_editorial_value": "fallback",
                    "known_limitations": ["body_not_fetched"],
                },
                ensure_ascii=False,
            ),
            {"id": "resp_test"},
        )


def _response(url: str, html: str, *, status: int = 200) -> HttpResponse:
    return HttpResponse(
        url=url,
        status=status,
        content_type="text/html; charset=utf-8",
        body=html.encode("utf-8"),
    )


def _long_body(label: str) -> str:
    return (
        f"{label}에는 한국전력, 전기요금, 2026년 6월, 12.5% 같은 숫자와 제도 설명이 있다. "
        "전쟁과 가스값, 전력망 투자 비용이 가계 청구서로 이동하는 구조를 설명한다. "
    ) * 5


def test_fetch_article_body_extracts_and_caches_full_text(tmp_path) -> None:
    url = "https://www.yna.co.kr/view/AKR202606010001"
    client = FakeHttpClient(
        {
            url: _response(
                url,
                (
                    "<html><head><title>전기요금 기사</title></head><body><p>"
                    f"{_long_body('본문')}</p></body></html>"
                ),
            )
        }
    )
    cache_path = tmp_path / "article_bodies.jsonl"

    records = fetch_article_bodies(
        targets=[ArticleTarget(url=url, title="RSS title", source="연합뉴스 경제")],
        output_jsonl=cache_path,
        http_client=client,
    )

    assert records[0].fetch_status == "ok"
    assert records[0].extractor == "yna_generic_article_p"
    assert records[0].body_char_count > 280
    assert records[0].body_text_hash
    assert _long_body("본문")[:40] in cache_path.read_text(encoding="utf-8")


def test_body_cache_hit_does_not_refetch(tmp_path) -> None:
    url = "https://www.bbc.com/news/articles/example"
    cache_path = tmp_path / "article_bodies.jsonl"
    client = FakeHttpClient(
        {
            url: _response(
                url,
                f"<html><body><p>{_long_body('BBC')}</p><p>{_long_body('second')}</p></body></html>",
            )
        }
    )
    fetch_article_bodies(
        targets=[ArticleTarget(url=url, title="BBC story", source="BBC News")],
        output_jsonl=cache_path,
        http_client=client,
    )
    raising_client = FakeHttpClient({url: AssertionError("should not refetch")})

    records = fetch_article_bodies(
        targets=[ArticleTarget(url=url, title="BBC story", source="BBC News")],
        output_jsonl=cache_path,
        http_client=raising_client,
    )

    assert records[0].cache_status == "hit"
    assert raising_client.calls == []


def test_llm_summary_fallback_records_gpt5_mini_summary(tmp_path) -> None:
    url = "https://blocked.example/story"
    cache_path = tmp_path / "article_bodies.jsonl"
    client = FakeHttpClient({url: _response(url, "<html>blocked</html>", status=403)})

    records = fetch_article_bodies(
        targets=[
            ArticleTarget(
                url=url,
                title="Blocked article",
                source="Blocked Source",
                summary="Short RSS summary",
            )
        ],
        output_jsonl=cache_path,
        http_client=client,
        llm_summary_fallback=True,
        llm_client=FakeLlmClient(),
    )

    assert records[0].fetch_status == "blocked"
    assert records[0].llm_summary_status == "ok"
    assert records[0].llm_summary_model == "gpt-5-mini"
    assert "한국어 요약" in records[0].llm_summary_ko


def test_collect_targets_dedupes_metadata_and_scored_candidates(tmp_path) -> None:
    metadata_path = tmp_path / "metadata.json"
    scored_path = tmp_path / "scored.jsonl"
    metadata_path.write_text(
        json.dumps(
            {
                "rows": [
                    {
                        "story_bundle_id": "bundle",
                        "primary_candidate_id": "candidate_1",
                        "main_link": "https://example.com/story?utm_source=rss",
                        "title": "Visible title",
                    }
                ]
            }
        ),
        encoding="utf-8",
    )
    scored_path.write_text(
        json.dumps(
            {
                "candidate_id": "candidate_1",
                "seed_url": "https://example.com/story",
                "title": "Scored title",
                "source": "Example",
                "scores": {"total_score": 80},
            }
        )
        + "\n",
        encoding="utf-8",
    )

    targets = collect_article_targets(
        metadata_path=metadata_path,
        scored_candidates_path=scored_path,
        include_scored_candidates=True,
    )

    assert len(targets) == 1
    assert targets[0].story_bundle_id == "bundle"


def test_fetch_report_does_not_print_full_body(tmp_path) -> None:
    url = "https://example.com/story"
    secret = "UNIQUE_FULL_BODY_SHOULD_STAY_ONLY_IN_CACHE"
    metadata_path = tmp_path / "metadata.json"
    scored_path = tmp_path / "scored.jsonl"
    metadata_path.write_text(
        json.dumps({"rows": [{"main_link": url, "title": "Story"}]}),
        encoding="utf-8",
    )
    scored_path.write_text("", encoding="utf-8")
    client = FakeHttpClient(
        {
            url: _response(
                url,
                f"<html><body><p>{secret} {_long_body('report')}</p></body></html>",
            )
        }
    )

    md_path, json_path, _records = run_article_body_fetch(
        run_date="2026-06-01",
        input_metadata=metadata_path,
        input_scored=scored_path,
        output_jsonl=tmp_path / "cache.jsonl",
        report_md=tmp_path / "report.md",
        report_json=tmp_path / "report.json",
        http_client=client,
    )

    assert secret not in md_path.read_text(encoding="utf-8")
    assert secret not in json_path.read_text(encoding="utf-8")
