import json

from luddite.agents.jibi.content_enrichment import (
    enrich_candidate,
    enriched_what_if,
    render_content_enrichment_review,
)
from luddite.collectors.rss_probe import HttpResponse
from luddite.utils.jsonl import write_jsonl


class FakeArticleHttpClient:
    def __init__(self, html_by_url):
        self.html_by_url = html_by_url
        self.calls = []

    def fetch(self, url: str, *, timeout: float) -> HttpResponse:
        self.calls.append((url, timeout))
        html = self.html_by_url[url]
        return HttpResponse(
            url=url,
            status=200,
            content_type="text/html; charset=utf-8",
            body=html.encode("utf-8"),
        )


class RaisingHttpClient:
    def fetch(self, url: str, *, timeout: float) -> HttpResponse:
        raise AssertionError("Atlas should be marked blocked without fetching")


def _long_text(label: str) -> str:
    return (
        f"{label} shows named actors, a funding mechanism, a concrete number, "
        "and a policy tension for viewers. "
        "The story connects market structure, regulation, infrastructure, and Korea. "
    ) * 4


def _candidate(**overrides):
    candidate = {
        "candidate_id": "candidate",
        "article_id": "article_candidate",
        "title": "AI search changes the homepage",
        "seed_url": "https://example.com/story",
        "source_url_canonical": "https://example.com/story",
        "duplicate_key": "https://example.com/story",
        "source": "NPR",
        "source_id": "npr_rss_candidate",
        "source_type": "rss_candidate",
        "published_at": "2026-05-23T00:00:00+00:00",
        "collected_at": "2026-05-23T01:00:00+00:00",
        "summary": "",
        "recommended_action": "gather_more_evidence",
        "final_grade": "B",
        "quality_flags": [],
        "failure_modes": ["thin_evidence"],
        "scores": {"total_score": 60, "broadcast_potential_proxy": 4},
        "story_specificity": {
            "score": 0.8,
            "level": "high",
            "signals": ["has_number"],
            "generic_why_detected": False,
        },
        "seed_type": "ai_knowledge_institution",
    }
    candidate.update(overrides)
    return candidate


def test_bbc_extractor_reads_next_data_text() -> None:
    body = _long_text("BBC body")
    html = json.dumps(
        {
            "props": {
                "pageProps": {
                    "blocks": [
                        {"model": {"text": body}},
                        {"model": {"text": _long_text("BBC second paragraph")}},
                    ]
                }
            }
        }
    )
    client = FakeArticleHttpClient(
        {
            "https://www.bbc.com/news/story": (
                "<html><head><meta name='description' content='BBC metadata'></head>"
                f"<script id='__NEXT_DATA__'>{html}</script></html>"
            )
        }
    )

    result = enrich_candidate(
        _candidate(
            source="BBC News",
            source_id="bbc_rss_candidate",
            seed_url="https://www.bbc.com/news/story",
            source_url_canonical="https://www.bbc.com/news/story",
        ),
        selection_role="top",
        http_client=client,
    )

    assert result.content_enrichment_status == "ok"
    assert result.content_enrichment_method == "bbc_next_data_text"
    assert result.body_chars > 450
    assert result.paragraph_count == 2


def test_npr_extractor_reads_storytext_paragraphs() -> None:
    body = _long_text("NPR body")
    client = FakeArticleHttpClient(
        {
            "https://www.npr.org/story": (
                "<html><body><div id='storytext'>"
                f"<p>{body}</p><p>{_long_text('NPR second')}</p>"
                "</div></body></html>"
            )
        }
    )

    result = enrich_candidate(
        _candidate(seed_url="https://www.npr.org/story", source_url_canonical=""),
        selection_role="near_miss",
        http_client=client,
    )

    assert result.content_enrichment_status == "ok"
    assert result.content_enrichment_method == "npr_storytext_p"
    assert result.paragraph_count == 2


def test_infomax_extractor_reads_article_view_content() -> None:
    client = FakeArticleHttpClient(
        {
            "https://news.einfomax.co.kr/news/articleView.html?idxno=1": (
                "<html><body><article id='article-view-content-div'>"
                f"<p>{_long_text('Infomax body')}</p>"
                f"<p>{_long_text('Infomax second')}</p>"
                "</article></body></html>"
            )
        }
    )

    result = enrich_candidate(
        _candidate(
            source="연합인포맥스",
            source_id="infomax_manual",
            seed_url="https://news.einfomax.co.kr/news/articleView.html?idxno=1",
            source_url_canonical="",
        ),
        selection_role="near_miss",
        http_client=client,
    )

    assert result.content_enrichment_status == "ok"
    assert result.content_enrichment_method == "infomax_article_view_content"


def test_hankyung_extractor_detects_paywall_teaser() -> None:
    client = FakeArticleHttpClient(
        {
            "https://www.hankyung.com/article/1": (
                "<html><body><div id='articletxt'>"
                "<p>한경 프리미엄9을 구독하고 무제한으로 만나보세요.</p>"
                "<p>짧은 티저 문장입니다.</p>"
                "</div></body></html>"
            )
        }
    )

    result = enrich_candidate(
        _candidate(
            source="한국경제",
            source_id="hankyung_manual",
            seed_url="https://www.hankyung.com/article/1",
            source_url_canonical="",
        ),
        selection_role="near_miss",
        http_client=client,
    )

    assert result.content_enrichment_status == "paywalled_or_teaser"
    assert result.content_enrichment_method == "hankyung_articletxt"


def test_atlas_is_blocked_without_fetch_attempt() -> None:
    result = enrich_candidate(
        _candidate(
            source="Atlas Obscura",
            source_id="atlas_obscura",
            seed_url="https://www.atlasobscura.com/places/example",
            source_url_canonical="",
        ),
        selection_role="near_miss",
        http_client=RaisingHttpClient(),
    )

    assert result.content_enrichment_status == "blocked"
    assert result.content_enrichment_method == "atlas_blocked_manual_only"
    assert result.http_status is None


def test_unknown_source_is_not_attempted_by_default() -> None:
    result = enrich_candidate(
        _candidate(
            source="Unknown Source",
            source_id="unknown_feed",
            seed_url="https://unknown.example/story",
            source_url_canonical="",
        ),
        selection_role="near_miss",
        http_client=RaisingHttpClient(),
    )

    assert result.content_enrichment_status == "not_attempted"
    assert result.content_enrichment_method == "unsupported_source"
    assert result.paywall_or_blocked_reason == "unsupported_source"
    assert result.http_status is None


def test_unknown_source_can_use_generic_extraction_when_explicitly_allowed() -> None:
    client = FakeArticleHttpClient(
        {
            "https://unknown.example/story": (
                "<html><head><meta name='description' content='Fallback metadata'></head>"
                f"<body><p>{_long_text('Generic source body')}</p>"
                f"<p>{_long_text('Generic source second')}</p></body></html>"
            )
        }
    )

    result = enrich_candidate(
        _candidate(
            source="Unknown Source",
            source_id="unknown_feed",
            seed_url="https://unknown.example/story",
            source_url_canonical="",
        ),
        selection_role="near_miss",
        http_client=client,
        allow_generic_extraction=True,
    )

    assert result.content_enrichment_status == "ok"
    assert result.content_enrichment_method == "generic_article_p"
    assert client.calls == [("https://unknown.example/story", 12)]


def test_enriched_what_if_resolves_empty_summary() -> None:
    candidate = _candidate(
        source="BBC News",
        source_id="bbc_rss_candidate",
        quality_flags=["empty_summary"],
        summary="",
    )
    client = FakeArticleHttpClient(
        {
            "https://example.com/story": (
                "<html><body><p>"
                + _long_text("Enriched BBC evidence with 2030 and policy mechanism")
                + "</p><p>"
                + _long_text("Second paragraph")
                + "</p></body></html>"
            )
        }
    )
    result = enrich_candidate(candidate, selection_role="near_miss", http_client=client)

    what_if = enriched_what_if(candidate, result)

    assert what_if is not None
    assert what_if["empty_summary_resolved"] is True


def test_enriched_what_if_reveals_disqualifying_market_frame() -> None:
    candidate = _candidate(
        source="연합인포맥스",
        source_id="infomax_manual",
        seed_url="https://news.einfomax.co.kr/news/articleView.html?idxno=2",
        source_url_canonical="",
        title="Company financing plan",
        quality_flags=[],
    )
    client = FakeArticleHttpClient(
        {
            "https://news.einfomax.co.kr/news/articleView.html?idxno=2": (
                "<html><body><article id='article-view-content-div'>"
                "<p>상장 회사의 유상증자와 주식 청약, 금리 부담, 투자 자금 조달을 다룬다.</p>"
                f"<p>{_long_text('single company financing')}</p>"
                "</article></body></html>"
            )
        }
    )
    result = enrich_candidate(candidate, selection_role="near_miss", http_client=client)

    what_if = enriched_what_if(candidate, result)

    assert what_if is not None
    assert what_if["disqualifying_details_found"] is True
    assert "single_stock_or_asset_frame" in what_if["enriched_quality_flags"]


def test_report_does_not_include_full_body_text(tmp_path) -> None:
    secret_body = "THIS_UNIQUE_SYNTHETIC_ARTICLE_BODY_MUST_NOT_APPEAR"
    input_path = tmp_path / "scored.jsonl"
    md_path = tmp_path / "content_enrichment.md"
    json_path = tmp_path / "content_enrichment.json"
    candidate = _candidate(
        title="Report storage safety story",
        seed_url="https://www.npr.org/story",
        source_url_canonical="https://www.npr.org/story",
        scores={"total_score": 70, "broadcast_potential_proxy": 4},
    )
    write_jsonl(input_path, [candidate])
    client = FakeArticleHttpClient(
        {
            "https://www.npr.org/story": (
                "<html><body><div id='storytext'>"
                f"<p>{secret_body} {_long_text('storage safety')}</p>"
                f"<p>{_long_text('second')}</p>"
                "</div></body></html>"
            )
        }
    )

    render_content_enrichment_review(
        input_path=input_path,
        output_md=md_path,
        output_json=json_path,
        review_date="2026-05-23",
        http_client=client,
    )

    assert secret_body not in md_path.read_text(encoding="utf-8")
    assert secret_body not in json_path.read_text(encoding="utf-8")
    assert "No full article bodies are printed or committed" in md_path.read_text(
        encoding="utf-8"
    )
