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
    assert sources["bok"].role == "numbers_evidence"
