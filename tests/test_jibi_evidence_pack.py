import json

from luddite.agents.jibi.article_body import ArticleBodyRecord
from luddite.agents.jibi.evidence_pack import build_evidence_pack, extract_evidence_features
from luddite.utils.jsonl import write_jsonl


def test_extract_evidence_features_finds_numbers_entities_dates_and_claims() -> None:
    text = (
        "한국전력은 2026년 6월 전기요금이 12.5% 오를 수 있다고 설명했다. "
        "산업통상자원부와 전력거래소는 가스값과 전력망 투자 비용이 요금제도에 반영된다고 밝혔다."
    )

    features = extract_evidence_features(text)

    assert "12.5%" in features["numbers"]
    assert any("2026" in item for item in features["dates"])
    assert "산업통상자원부" in features["entities"]
    assert any("요금제도" in item for item in features["policy_terms"])
    assert features["key_sentences"]


def test_build_evidence_pack_joins_metadata_to_article_cache(tmp_path) -> None:
    metadata_path = tmp_path / "metadata.json"
    article_cache = tmp_path / "article_bodies.jsonl"
    url = "https://example.com/electricity"
    metadata_path.write_text(
        json.dumps(
            {
                "rows": [
                    {
                        "story_bundle_id": "bundle_1",
                        "title": "전기요금은 왜 전쟁과 가스값을 따라 움직이나",
                        "description": "가계 전기요금 구조",
                        "main_link": url,
                        "source": "Example",
                        "editorial_role": "sub_block",
                        "board_score": 88,
                        "selection_lessons": ["daily_life_problem_bonus"],
                        "main_seed_candidate": True,
                    }
                ]
            },
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )
    write_jsonl(
        article_cache,
        [
            ArticleBodyRecord(
                url=url,
                canonical_url=url,
                source="Example",
                fetch_status="ok",
                title="전기요금 기사",
                body_text=(
                    "한국전력은 2026년 6월 전기요금 12.5% 인상 가능성과 "
                    "전력망 투자 비용을 설명했다."
                ),
                body_text_hash="hash",
                body_char_count=54,
                body_word_count=10,
                extractor="generic_article_p",
            ).to_json_dict()
        ],
    )

    payload = build_evidence_pack(
        run_date="2026-06-01",
        metadata_path=metadata_path,
        article_cache_path=article_cache,
    )

    assert payload["item_count"] == 1
    item = payload["items"][0]
    assert item["rule_diagnostics"]["main_seed_candidate"] is True
    assert item["article_bodies"][0]["fetch_status"] == "ok"
    assert "12.5%" in item["article_bodies"][0]["numbers"]
