import json
from datetime import UTC, datetime

from luddite.agents.anny.review_fact_check import (
    build_fact_check_review,
    build_hygiene_records,
    build_source_role_map,
)


def _storyline() -> dict:
    return {
        "title": "AI 즉답 시대의 지식기관 역할",
        "sections": [
            {
                "section_title": "AI가 답을 바로 주는 시대",
                "slides": [
                    {
                        "slide_no": 1,
                        "local_order": 1,
                        "slide_type": "quote",
                        "headline": "영국 왕립천문대 쪽에서 나온 경고",
                        "body": ["Royal Observatory 발언 맥락 확인 필요"],
                        "source_urls": ["https://www.bbc.com/news/articles/c2023l60370o"],
                        "image_urls": [],
                        "notes": "[내용] BBC / Royal Observatory article.",
                        "needs_fact_check": True,
                        "needs_source": False,
                    },
                    {
                        "slide_no": 2,
                        "local_order": 2,
                        "slide_type": "closing_question",
                        "headline": "AI가 답을 해주면, 사람은 질문을 해야 한다",
                        "body": ["방송용 질문"],
                        "source_urls": [],
                        "image_urls": [],
                        "notes": "[rhetorical_bridge]",
                        "needs_fact_check": False,
                        "needs_source": False,
                    },
                ],
            }
        ],
    }


def _pack() -> dict:
    return {
        "primary_article": {
            "title": "BBC article",
            "url": "https://www.bbc.com/news/articles/c2023l60370o",
            "source": "BBC News",
            "source_type": "primary_article",
            "summary": "Royal Observatory context.",
            "role": "primary_seed",
            "reliability": "medium",
            "needs_manual_check": False,
        },
        "supporting_articles": [],
        "research_or_survey": [],
        "counterpoints": [],
        "institution_examples": [],
        "korea_bridge": [],
        "visual_candidates": [],
    }


def test_build_source_role_map_labels_primary_article() -> None:
    role_map = build_source_role_map(_pack())

    assert role_map["https://www.bbc.com/news/articles/c2023l60370o"] == [
        "primary_article"
    ]


def test_build_hygiene_records_adds_priority_and_required_flag() -> None:
    records = build_hygiene_records(_storyline(), _pack())

    assert len(records) == 2
    assert records[0]["fact_check_priority"] == "high"
    assert records[0]["fact_check_kind"] == "institution_quote_context"
    assert records[0]["required_before_storyline"] is False
    assert records[0]["required_before_broadcast"] is True
    assert records[0]["source_roles"][0]["roles"] == ["primary_article"]
    assert records[0]["source_refs"][0]["role"] == "primary_article"
    assert records[0]["source_refs"][0]["manual_check_required"] is True
    assert records[1]["fact_check_priority"] == "low"
    assert records[1]["fact_check_kind"] == "rhetorical_caution"
    assert records[1]["required_before_broadcast"] is False


def test_build_fact_check_review_writes_sidecar_and_report(tmp_path) -> None:
    storyline_path = tmp_path / "storyline.json"
    pack_path = tmp_path / "pack.json"
    hygiene_path = tmp_path / "hygiene.jsonl"
    report_path = tmp_path / "report.md"
    storyline_path.write_text(json.dumps(_storyline(), ensure_ascii=False), encoding="utf-8")
    pack_path.write_text(json.dumps(_pack(), ensure_ascii=False), encoding="utf-8")

    result = build_fact_check_review(
        storyline_path=storyline_path,
        evidence_pack_path=pack_path,
        hygiene_jsonl_path=hygiene_path,
        report_path=report_path,
        now=datetime(2026, 5, 18, tzinfo=UTC),
    )

    assert result["needs_fact_check_count"] == 1
    assert result["required_before_storyline_count"] == 0
    assert result["ready_for_prompt_design"] is True
    assert result["ready_for_production_agent"] is False
    assert "ready_for_prompt_design: True" in report_path.read_text(encoding="utf-8")
    assert "Fact-Check Kind Distribution" in report_path.read_text(encoding="utf-8")
    assert len(hygiene_path.read_text(encoding="utf-8").splitlines()) == 2
