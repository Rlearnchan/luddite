from datetime import UTC, datetime
from urllib.error import URLError

from luddite.collectors.rss_item_fetcher import (
    fetch_rss_articles,
    load_allowlist,
    parse_feed_items,
    truncate_summary,
)
from luddite.collectors.rss_probe import HttpResponse
from luddite.utils.jsonl import read_jsonl
from luddite.utils.schemas import validate_with_schema


class FakeHttpClient:
    def __init__(self, responses):
        self.responses = responses
        self.calls = []

    def fetch(self, url: str, *, timeout: float) -> HttpResponse:
        self.calls.append((url, timeout))
        response = self.responses[url]
        if isinstance(response, Exception):
            raise response
        return response


VALID_RSS = b"""<?xml version="1.0"?>
<rss version="2.0">
  <channel>
    <item>
      <title>BBC RSS Item</title>
      <link>https://example.com/item?utm_source=rss</link>
      <pubDate>Mon, 18 May 2026 00:00:00 GMT</pubDate>
      <description>Short feed summary.</description>
    </item>
  </channel>
</rss>
"""

VALID_ATOM = b"""<?xml version="1.0"?>
<feed xmlns="http://www.w3.org/2005/Atom">
  <entry>
    <title>NPR Atom Item</title>
    <link href="https://example.com/atom?utm_campaign=x" />
    <updated>2026-05-18T00:00:00Z</updated>
    <summary>Atom summary.</summary>
  </entry>
</feed>
"""

DUPLICATE_RSS = b"""<?xml version="1.0"?>
<rss version="2.0">
  <channel>
    <item>
      <title>First duplicate</title>
      <link>https://example.com/dupe?utm_source=rss</link>
      <pubDate>Mon, 18 May 2026 00:00:00 GMT</pubDate>
      <description><![CDATA[<p>First summary.</p>]]></description>
    </item>
    <item>
      <title>Second duplicate</title>
      <link>https://example.com/dupe</link>
      <pubDate>Mon, 18 May 2026 01:00:00 GMT</pubDate>
      <description>Second summary.</description>
    </item>
  </channel>
</rss>
"""

TWO_ITEM_RSS = b"""<?xml version="1.0"?>
<rss version="2.0">
  <channel>
    <item>
      <title>BBC RSS Item</title>
      <link>https://example.com/item?utm_source=rss</link>
      <pubDate>Mon, 18 May 2026 00:00:00 GMT</pubDate>
      <description>Short feed summary.</description>
    </item>
    <item>
      <title>BBC New RSS Item</title>
      <link>https://example.com/new-item</link>
      <pubDate>Mon, 18 May 2026 01:00:00 GMT</pubDate>
      <description>Second feed summary.</description>
    </item>
  </channel>
</rss>
"""


def _write_registry(path):
    path.write_text(
        """
sources:
  - id: bbc_rss_candidate
    name: BBC News
    type: rss_candidate
    status: rss_verified
    group: primary_wire
    role: seed_discovery
    region: global
    verified_feed_url: https://feeds.example.com/bbc.xml
  - id: npr_rss_candidate
    name: NPR
    type: rss_candidate
    status: rss_verified
    group: primary_wire
    section_name: npr
    region: global
    verified_feed_url: https://feeds.example.com/npr.xml
  - id: guardian_rss_candidate
    name: The Guardian
    type: rss_candidate
    status: rss_verified
    verified_feed_url: https://feeds.example.com/guardian.xml
  - id: missing_feed
    name: Missing Feed
    type: rss_candidate
    status: rss_verified
  - id: premium
    name: Premium
    type: subscription_manual
    status: subscription_manual
""",
        encoding="utf-8",
    )


def _write_allowlist(path):
    path.write_text(
        """
sources:
  - source_id: bbc_rss_candidate
    collection_enabled: true
    reason: public_feed_test_ingestion
  - source_id: npr_rss_candidate
    collection_enabled: true
    fetch_limit: 5
    reason: public_feed_test_ingestion
  - source_id: guardian_rss_candidate
    collection_enabled: false
    reason: terms_pending
  - source_id: missing_feed
    collection_enabled: true
    reason: test_missing_feed
""",
        encoding="utf-8",
    )


def test_load_allowlist(tmp_path) -> None:
    allowlist = tmp_path / "allowlist.yaml"
    _write_allowlist(allowlist)

    loaded = load_allowlist(allowlist)

    assert loaded["bbc_rss_candidate"].collection_enabled is True
    assert loaded["guardian_rss_candidate"].collection_enabled is False


def test_real_allowlist_prefers_yonhap_sections_over_latest() -> None:
    loaded = load_allowlist()

    assert loaded["yonhap_rss_candidate"].collection_enabled is False
    assert loaded["yonhap_economy"].collection_enabled is True
    assert loaded["yonhap_industry"].collection_enabled is True
    assert loaded["yonhap_international"].collection_enabled is True
    assert loaded["yonhap_economy"].fetch_limit == 120


def test_parse_valid_rss_and_atom_items() -> None:
    rss_items, rss_failure = parse_feed_items(VALID_RSS)
    atom_items, atom_failure = parse_feed_items(VALID_ATOM)

    assert rss_failure is None
    assert rss_items[0].title == "BBC RSS Item"
    assert atom_failure is None
    assert atom_items[0].url == "https://example.com/atom?utm_campaign=x"


def test_fetch_enabled_sources_to_article_jsonl(tmp_path) -> None:
    registry = tmp_path / "sources.yaml"
    allowlist = tmp_path / "allowlist.yaml"
    output = tmp_path / "rss_2026-05-18.jsonl"
    report_path = tmp_path / "rss_ingest_2026-05-18.md"
    _write_registry(registry)
    _write_allowlist(allowlist)
    client = FakeHttpClient(
        {
            "https://feeds.example.com/bbc.xml": HttpResponse(
                url="https://feeds.example.com/bbc.xml",
                status=200,
                content_type="application/rss+xml",
                body=VALID_RSS,
            ),
            "https://feeds.example.com/npr.xml": HttpResponse(
                url="https://feeds.example.com/npr.xml",
                status=200,
                content_type="application/atom+xml",
                body=VALID_ATOM,
            ),
        }
    )

    articles, report = fetch_rss_articles(
        registry_path=registry,
        allowlist_path=allowlist,
        output_path=output,
        report_path=report_path,
        http_client=client,
        collected_at=datetime(2026, 5, 18, tzinfo=UTC),
    )

    assert len(articles) == 2
    assert report.sources_fetched == 2
    assert report.sources_skipped == 3
    assert report.output_status == "written"
    assert len(client.calls) == 2
    assert "guardian" not in [call[0] for call in client.calls]
    assert articles[0]["source_url_canonical"] == "https://example.com/item"
    assert str(articles[0]["duplicate_key"]).startswith("rss_")
    assert validate_with_schema(articles[0], "article_schema.json") == []
    assert output.read_text(encoding="utf-8").count("\n") == 2
    assert "collection_enabled_false" in report_path.read_text(encoding="utf-8")


def test_fetch_failure_preserves_existing_output_file(tmp_path) -> None:
    registry = tmp_path / "sources.yaml"
    allowlist = tmp_path / "allowlist.yaml"
    output = tmp_path / "rss_existing.jsonl"
    report_path = tmp_path / "rss_failure.md"
    _write_registry(registry)
    _write_allowlist(allowlist)
    output.write_text('{"title": "keep me"}\n', encoding="utf-8")
    client = FakeHttpClient(
        {
            "https://feeds.example.com/bbc.xml": URLError("network down"),
        }
    )

    articles, report = fetch_rss_articles(
        registry_path=registry,
        allowlist_path=allowlist,
        output_path=output,
        report_path=report_path,
        http_client=client,
        source_id="bbc_rss_candidate",
        collected_at=datetime(2026, 5, 18, tzinfo=UTC),
    )

    assert articles == []
    assert report.output_status == "preserved_existing"
    assert output.read_text(encoding="utf-8") == '{"title": "keep me"}\n'
    assert "zero_articles_with_fetch_failures" in report_path.read_text(encoding="utf-8")


def test_article_history_tracks_new_and_previous_run_delta(tmp_path) -> None:
    registry = tmp_path / "sources.yaml"
    allowlist = tmp_path / "allowlist.yaml"
    history_path = tmp_path / "jibi_article_history.jsonl"
    run_ledger_path = tmp_path / "jibi_article_runs.jsonl"
    _write_registry(registry)
    _write_allowlist(allowlist)
    first_client = FakeHttpClient(
        {
            "https://feeds.example.com/bbc.xml": HttpResponse(
                url="https://feeds.example.com/bbc.xml",
                status=200,
                content_type="application/rss+xml",
                body=VALID_RSS,
            )
        }
    )
    second_client = FakeHttpClient(
        {
            "https://feeds.example.com/bbc.xml": HttpResponse(
                url="https://feeds.example.com/bbc.xml",
                status=200,
                content_type="application/rss+xml",
                body=TWO_ITEM_RSS,
            )
        }
    )

    first_articles, first_report = fetch_rss_articles(
        registry_path=registry,
        allowlist_path=allowlist,
        output_path=tmp_path / "rss_first.jsonl",
        report_path=tmp_path / "rss_first.md",
        history_path=history_path,
        run_ledger_path=run_ledger_path,
        http_client=first_client,
        source_id="bbc_rss_candidate",
        collected_at=datetime(2026, 5, 18, 0, 0, tzinfo=UTC),
    )
    second_articles, second_report = fetch_rss_articles(
        registry_path=registry,
        allowlist_path=allowlist,
        output_path=tmp_path / "rss_second.jsonl",
        report_path=tmp_path / "rss_second.md",
        history_path=history_path,
        run_ledger_path=run_ledger_path,
        http_client=second_client,
        source_id="bbc_rss_candidate",
        collected_at=datetime(2026, 5, 18, 1, 0, tzinfo=UTC),
    )

    assert len(first_articles) == 1
    assert first_report.article_history
    assert first_report.article_history.new_since_previous_run == 1
    assert len(second_articles) == 2
    assert second_report.article_history
    assert second_report.article_history.previous_run_id == first_report.article_history.run_id
    assert second_report.article_history.new_to_history == 1
    assert second_report.article_history.returning_known == 1
    assert second_report.article_history.new_since_previous_run == 1
    assert second_report.article_history.dropped_since_previous_run == 0
    assert len(read_jsonl(history_path)) == 2
    assert len(read_jsonl(run_ledger_path)) == 2
    assert "## Article History" in (tmp_path / "rss_second.md").read_text(encoding="utf-8")


def test_source_id_and_limit_per_source(tmp_path) -> None:
    registry = tmp_path / "sources.yaml"
    allowlist = tmp_path / "allowlist.yaml"
    _write_registry(registry)
    _write_allowlist(allowlist)
    client = FakeHttpClient(
        {
            "https://feeds.example.com/bbc.xml": HttpResponse(
                url="https://feeds.example.com/bbc.xml",
                status=200,
                content_type="application/rss+xml",
                body=VALID_RSS,
            )
        }
    )

    articles, report = fetch_rss_articles(
        registry_path=registry,
        allowlist_path=allowlist,
        output_path=tmp_path / "rss_source_id.jsonl",
        report_path=tmp_path / "rss_source_id.md",
        http_client=client,
        source_id="bbc_rss_candidate",
        limit_per_source=1,
        collected_at=datetime(2026, 5, 18, tzinfo=UTC),
    )

    assert len(articles) == 1
    assert report.sources_considered == 1


def test_run_dedupe_and_total_limit(tmp_path) -> None:
    registry = tmp_path / "sources.yaml"
    allowlist = tmp_path / "allowlist.yaml"
    _write_registry(registry)
    _write_allowlist(allowlist)
    client = FakeHttpClient(
        {
            "https://feeds.example.com/bbc.xml": HttpResponse(
                url="https://feeds.example.com/bbc.xml",
                status=200,
                content_type="application/rss+xml",
                body=DUPLICATE_RSS,
            ),
            "https://feeds.example.com/npr.xml": HttpResponse(
                url="https://feeds.example.com/npr.xml",
                status=200,
                content_type="application/atom+xml",
                body=VALID_ATOM,
            ),
        }
    )

    articles, report = fetch_rss_articles(
        registry_path=registry,
        allowlist_path=allowlist,
        output_path=tmp_path / "rss_dedupe.jsonl",
        report_path=tmp_path / "rss_dedupe.md",
        http_client=client,
        total_limit=2,
        collected_at=datetime(2026, 5, 18, tzinfo=UTC),
    )

    assert len(articles) == 2
    assert report.duplicates_skipped == 1
    assert report.per_source[0].duplicates_skipped == 1
    assert "https://example.com/dupe" in report.per_source[0].duplicate_examples[0]


def test_cross_feed_url_dedupe_preserves_supporting_sections(tmp_path) -> None:
    registry = tmp_path / "sources.yaml"
    allowlist = tmp_path / "allowlist.yaml"
    registry.write_text(
        """
sources:
  - id: yonhap_economy
    name: 연합뉴스 경제
    type: rss_candidate
    status: rss_verified
    group: korea_business
    role: domestic_bridge
    role_class: public_wire
    region: kr
    section_name: economy
    verified_feed_url: https://feeds.example.com/yonhap-economy.xml
  - id: yonhap_industry
    name: 연합뉴스 산업
    type: rss_candidate
    status: rss_verified
    group: korea_business
    role: domestic_bridge
    role_class: public_wire
    region: kr
    section_name: industry
    verified_feed_url: https://feeds.example.com/yonhap-industry.xml
""",
        encoding="utf-8",
    )
    allowlist.write_text(
        """
sources:
  - source_id: yonhap_economy
    collection_enabled: true
    fetch_limit: 10
    reason: test
  - source_id: yonhap_industry
    collection_enabled: true
    fetch_limit: 10
    reason: test
""",
        encoding="utf-8",
    )
    duplicate_body = b"""<?xml version="1.0"?>
<rss version="2.0">
  <channel>
    <item>
      <title>Same Yonhap story</title>
      <link>https://www.yna.co.kr/view/AKR20260523000100001?utm_source=rss</link>
      <pubDate>Sat, 23 May 2026 10:00:00 +0900</pubDate>
      <description>Cross-section story.</description>
    </item>
  </channel>
</rss>
"""
    client = FakeHttpClient(
        {
            "https://feeds.example.com/yonhap-economy.xml": HttpResponse(
                url="https://feeds.example.com/yonhap-economy.xml",
                status=200,
                content_type="application/rss+xml",
                body=duplicate_body,
            ),
            "https://feeds.example.com/yonhap-industry.xml": HttpResponse(
                url="https://feeds.example.com/yonhap-industry.xml",
                status=200,
                content_type="application/rss+xml",
                body=duplicate_body,
            ),
        }
    )

    articles, report = fetch_rss_articles(
        registry_path=registry,
        allowlist_path=allowlist,
        output_path=tmp_path / "rss_yonhap_dedupe.jsonl",
        report_path=tmp_path / "rss_yonhap_dedupe.md",
        http_client=client,
        collected_at=datetime(2026, 5, 23, tzinfo=UTC),
    )

    assert len(articles) == 1
    assert report.duplicates_skipped == 1
    assert report.unique_urls_written == 1
    assert articles[0]["source_count"] == 2
    assert articles[0]["source_sections"] == ["economy", "industry"]
    assert articles[0]["supporting_source_ids"] == ["yonhap_industry"]


def test_summary_cleanup_and_truncate() -> None:
    assert truncate_summary("x" * 600, limit=10) == "xxxxxxxxx…"
    assert truncate_summary("<p>Hello&nbsp;world</p><a>관련기사</a>", limit=100) == "Hello world"
    assert truncate_summary("&lt;p&gt;Escaped&nbsp;HTML&lt;/p&gt;", limit=100) == "Escaped HTML"
