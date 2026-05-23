from luddite.collectors.source_registry import source_by_id


def test_source_registry_v0_9_3_groups_and_fetch_policy() -> None:
    sources = source_by_id()

    assert sources["google_sheet_jibi_candidates"].type == "sheet"
    assert sources["google_sheet_jibi_candidates"].role == "staging_append"
    assert sources["ft_manual"].type == "subscription_manual"
    assert sources["ft_manual"].subscription is True
    assert sources["ft_manual"].auto_fetch is False
    assert sources["ap_rss_candidate"].type == "rss_candidate"
    assert sources["ap_rss_candidate"].group == "primary_wire"
    assert sources["bok"].type == "official_release"
    assert sources["bok"].role == "seed_and_numbers_evidence"
    assert sources["bok"].verified_feed_url == (
        "https://www.bok.or.kr/portal/bbs/P0002353/news.rss?menuNo=200433"
    )
    assert sources["bok"].freshness_policy == "low_frequency_research"
    assert sources["bok"].freshness_window_days == 90
    assert sources["bok"].role_class == "research_note"
    assert sources["korea_policy_briefing"].role_class == "policy_release"
    assert sources["the_conversation"].role_class == "academic_explainer"
    assert sources["guardian_business"].role_class == "section_news"
    assert sources["guardian_business"].verified_feed_url == (
        "https://www.theguardian.com/business/rss"
    )
    assert sources["yonhap_rss_candidate"].verified_feed_url == (
        "https://www.yna.co.kr/rss/news.xml"
    )
    assert sources["yonhap_international_rss_candidate"].verified_feed_url == (
        "https://www.yna.co.kr/rss/international.xml"
    )
    assert sources["yonhap_rss_candidate"].section_name == "latest"
    assert sources["yonhap_economy"].role_class == "public_wire"
    assert sources["yonhap_economy"].section_name == "economy"
    assert sources["yonhap_economy"].verified_feed_url == (
        "https://www.yna.co.kr/rss/economy.xml"
    )
    assert sources["yonhap_industry"].section_name == "industry"
    assert sources["yonhap_international"].section_name == "international"
    assert sources["yonhap_market"].role_class == "market_wire"
    assert sources["yonhap_health"].section_name == "health"
    assert sources["korea_policy_briefing"].role == "policy_seed_and_evidence"
