from datetime import UTC, datetime

from luddite.collectors.rss_probe import (
    HttpResponse,
    parse_feed,
    probe_sources,
    write_jsonl,
    write_markdown_report,
    write_suggested_patch,
)


class FakeHttpClient:
    def __init__(self, responses):
        self.responses = responses
        self.calls = []

    def fetch(self, url: str, *, timeout: float) -> HttpResponse:
        self.calls.append((url, timeout))
        response = self.responses.get(url)
        if isinstance(response, Exception):
            raise response
        if response is None:
            return HttpResponse(url=url, status=404, content_type="text/html", body=b"not found")
        return response


VALID_RSS = b"""<?xml version="1.0"?>
<rss version="2.0">
  <channel>
    <title>Example RSS</title>
    <item>
      <title>Drone defense cost asymmetry</title>
      <link>https://example.com/drone</link>
      <pubDate>Mon, 18 May 2026 00:00:00 GMT</pubDate>
    </item>
    <item>
      <title>Office shorts heatwave</title>
      <link>https://example.com/shorts</link>
    </item>
  </channel>
</rss>
"""

VALID_ATOM = b"""<?xml version="1.0"?>
<feed xmlns="http://www.w3.org/2005/Atom">
  <title>Example Atom</title>
  <entry>
    <title>Vietnam pawnshop listing</title>
    <link href="https://example.com/f88" />
    <updated>2026-05-18T00:00:00Z</updated>
  </entry>
</feed>
"""


def _write_registry(path):
    path.write_text(
        """
sources:
  - id: rss_source
    name: RSS Source
    type: rss_candidate
    status: rss_candidate
    group: primary_wire
    homepage_url: https://example.com
  - id: configured_source
    name: Configured Source
    type: rss_candidate
    status: rss_candidate
    collection_enabled: false
    terms_check_required: false
    feed_url_candidates:
      - https://configured.example.com/rss.xml
  - id: autodiscovery_source
    name: Autodiscovery Source
    type: rss_candidate
    status: rss_candidate
    homepage_url: https://auto.example.com
  - id: rss_index_source
    name: RSS Index Source
    type: rss_candidate
    status: rss_candidate
    rss_index_url: https://index.example.com/rss
    desired_feed: 보도자료
  - id: atom_source
    name: Atom Source
    type: rss_candidate
    status: rss_candidate
    group: primary_wire
    feed_url: https://atom.example.com/feed.xml
  - id: subscription_source
    name: Subscription Source
    type: subscription_manual
    group: premium_manual
  - id: manual_source
    name: Manual Source
    type: manual
    group: workflow
  - id: broken_source
    name: Broken Source
    type: rss_candidate
    status: rss_candidate
    homepage_url: https://broken.example.com
  - id: no_url_source
    name: No URL Source
    type: rss_candidate
    status: rss_candidate
""",
        encoding="utf-8",
    )


def test_parse_valid_rss_and_atom() -> None:
    rss = parse_feed(VALID_RSS)
    atom = parse_feed(VALID_ATOM)

    assert rss.item_count == 2
    assert rss.sample_items[0].title == "Drone defense cost asymmetry"
    assert atom.item_count == 1
    assert atom.sample_items[0].url == "https://example.com/f88"


def test_parse_invalid_xml_reports_failure() -> None:
    parsed = parse_feed(b"<rss><channel>")

    assert parsed.item_count == 0
    assert parsed.failure_reason is not None
    assert parsed.failure_reason.startswith("invalid_xml:")


def test_probe_defaults_to_rss_candidates_and_skips_manual_sources(tmp_path) -> None:
    registry = tmp_path / "sources.yaml"
    _write_registry(registry)
    client = FakeHttpClient(
        {
            "https://example.com/rss": HttpResponse(
                url="https://example.com/rss",
                status=200,
                content_type="application/rss+xml",
                body=VALID_RSS,
            ),
            "https://atom.example.com/feed.xml": HttpResponse(
                url="https://atom.example.com/feed.xml",
                status=200,
                content_type="application/atom+xml",
                body=VALID_ATOM,
            ),
        }
    )

    results = probe_sources(
        registry_path=registry,
        http_client=client,
        checked_at=datetime(2026, 5, 18, tzinfo=UTC),
    )

    by_id = {result.source_id: result for result in results}
    assert by_id["rss_source"].recommendation == "rss_verified_terms_pending"
    assert by_id["atom_source"].parse_status == "parsed"
    assert by_id["subscription_source"].skipped is True
    assert by_id["subscription_source"].recommendation == "keep_subscription_manual"
    assert by_id["manual_source"].skipped is True
    assert by_id["manual_source"].recommendation == "manual_only"


def test_configured_feed_url_candidate_success(tmp_path) -> None:
    registry = tmp_path / "sources.yaml"
    _write_registry(registry)
    client = FakeHttpClient(
        {
            "https://configured.example.com/rss.xml": HttpResponse(
                url="https://configured.example.com/rss.xml",
                status=200,
                content_type="application/rss+xml",
                body=VALID_RSS,
            )
        }
    )

    results = probe_sources(
        registry_path=registry,
        http_client=client,
        source_id="configured_source",
        checked_at=datetime(2026, 5, 18, tzinfo=UTC),
    )

    assert results[0].discovery_method == "configured_feed_url"
    assert results[0].verified_feed_url == "https://configured.example.com/rss.xml"
    assert results[0].recommendation == "promote_to_rss_verified"
    assert results[0].collection_enabled is False


def test_html_autodiscovery_success(tmp_path) -> None:
    registry = tmp_path / "sources.yaml"
    _write_registry(registry)
    client = FakeHttpClient(
        {
            "https://auto.example.com": HttpResponse(
                url="https://auto.example.com",
                status=200,
                content_type="text/html",
                body=(
                    b'<html><head><link rel="alternate" '
                    b'type="application/rss+xml" href="/feed.xml"></head></html>'
                ),
            ),
            "https://auto.example.com/feed.xml": HttpResponse(
                url="https://auto.example.com/feed.xml",
                status=200,
                content_type="application/rss+xml",
                body=VALID_RSS,
            ),
        }
    )

    results = probe_sources(
        registry_path=registry,
        http_client=client,
        source_id="autodiscovery_source",
        checked_at=datetime(2026, 5, 18, tzinfo=UTC),
    )

    assert results[0].discovery_method == "html_autodiscovery"
    assert results[0].verified_feed_url == "https://auto.example.com/feed.xml"
    assert results[0].recommendation == "rss_verified_terms_pending"
    assert results[0].terms_check_required is True


def test_rss_index_discovery_prefers_desired_feed(tmp_path) -> None:
    registry = tmp_path / "sources.yaml"
    _write_registry(registry)
    client = FakeHttpClient(
        {
            "https://index.example.com/rss": HttpResponse(
                url="https://index.example.com/rss",
                status=200,
                content_type="text/html",
                body=(
                    '<html><body><a href="/rss/all.xml">전체</a>'
                    '<a href="/rss/press.xml">보도자료</a></body></html>'
                ).encode(),
            ),
            "https://index.example.com/rss/press.xml": HttpResponse(
                url="https://index.example.com/rss/press.xml",
                status=200,
                content_type="application/rss+xml",
                body=VALID_RSS,
            ),
        }
    )

    results = probe_sources(
        registry_path=registry,
        http_client=client,
        source_id="rss_index_source",
        checked_at=datetime(2026, 5, 18, tzinfo=UTC),
    )

    assert results[0].discovery_method == "rss_index_url"
    assert results[0].verified_feed_url == "https://index.example.com/rss/press.xml"
    assert results[0].extracted_feed_candidates == [
        "https://index.example.com/rss/press.xml",
        "https://index.example.com/rss/all.xml",
    ]


def test_failed_source_records_reason(tmp_path) -> None:
    registry = tmp_path / "sources.yaml"
    _write_registry(registry)
    client = FakeHttpClient({})

    results = probe_sources(
        registry_path=registry,
        http_client=client,
        source_id="broken_source",
        checked_at=datetime(2026, 5, 18, tzinfo=UTC),
    )

    assert len(results) == 1
    assert results[0].parse_status == "failed"
    assert results[0].failure_reason is not None
    assert results[0].recommendation == "mark_rss_failed"


def test_timeout_records_reason(tmp_path) -> None:
    registry = tmp_path / "sources.yaml"
    _write_registry(registry)
    client = FakeHttpClient({"https://broken.example.com/rss": TimeoutError()})

    results = probe_sources(
        registry_path=registry,
        http_client=client,
        source_id="broken_source",
        checked_at=datetime(2026, 5, 18, tzinfo=UTC),
    )

    assert results[0].parse_status == "failed"
    assert results[0].failure_reason is not None


def test_source_without_feed_or_homepage_url_keeps_candidate(tmp_path) -> None:
    registry = tmp_path / "sources.yaml"
    _write_registry(registry)
    client = FakeHttpClient({})

    results = probe_sources(
        registry_path=registry,
        http_client=client,
        source_id="no_url_source",
        checked_at=datetime(2026, 5, 18, tzinfo=UTC),
    )

    assert results[0].tested_url is None
    assert results[0].recommendation == "keep_rss_candidate"
    assert results[0].failure_reason == "No feed_url or homepage_url available for discovery."


def test_report_and_jsonl_are_written(tmp_path) -> None:
    registry = tmp_path / "sources.yaml"
    report = tmp_path / "rss_probe.md"
    jsonl = tmp_path / "rss_probe_results.jsonl"
    _write_registry(registry)
    client = FakeHttpClient(
        {
            "https://example.com/rss": HttpResponse(
                url="https://example.com/rss",
                status=200,
                content_type="application/rss+xml",
                body=VALID_RSS,
            )
        }
    )
    results = probe_sources(
        registry_path=registry,
        http_client=client,
        source_id="rss_source",
        checked_at=datetime(2026, 5, 18, tzinfo=UTC),
    )

    write_markdown_report(report, results, title_date="2026-05-18")
    write_jsonl(jsonl, results)

    assert "# RSS Probe Report" in report.read_text(encoding="utf-8")
    assert "rss_verified_terms_pending" in report.read_text(encoding="utf-8")
    assert "discovery method" in report.read_text(encoding="utf-8")
    assert "rss_index_url" in report.read_text(encoding="utf-8")
    assert '"source_id": "rss_source"' in jsonl.read_text(encoding="utf-8")
    assert '"discovery_method": "known_path_candidate"' in jsonl.read_text(encoding="utf-8")


def test_suggested_patch_is_written(tmp_path) -> None:
    registry = tmp_path / "sources.yaml"
    patch = tmp_path / "rss_probe_suggested_sources_patch.yaml"
    _write_registry(registry)
    client = FakeHttpClient(
        {
            "https://configured.example.com/rss.xml": HttpResponse(
                url="https://configured.example.com/rss.xml",
                status=200,
                content_type="application/rss+xml",
                body=VALID_RSS,
            )
        }
    )
    results = probe_sources(
        registry_path=registry,
        http_client=client,
        source_id="configured_source",
        checked_at=datetime(2026, 5, 18, tzinfo=UTC),
    )

    write_suggested_patch(patch, results)

    text = patch.read_text(encoding="utf-8")
    assert "status: rss_verified" in text
    assert "verified_feed_url: https://configured.example.com/rss.xml" in text
    assert "collection_enabled: false" in text
