import json
from datetime import UTC, datetime

from luddite.agents.anny.plan_evidence_enrichment import (
    build_evidence_enrichment_plan,
    collect_slide_needs,
)
from luddite.utils.schemas import validate_with_schema


def _bundle() -> dict:
    return {
        "bundle_id": "anny_bundle_09277535430e",
        "story_seed_title": "AI 즉답 시대의 지식기관 역할",
        "candidate_articles": [
            {
                "title": "Instant AI answers can trivialise human intelligence",
                "url": "https://www.bbc.com/news/articles/c2023l60370o",
                "source": "BBC News",
                "summary": "Royal Observatory warning context.",
            }
        ],
    }


def _storyline() -> dict:
    return {
        "title": "AI 즉답 시대의 지식기관 역할",
        "sections": [
            {
                "section_title": "AI가 답을 바로 주는 시대",
                "slides": [
                    {
                        "headline": "AI가 답을 바로 주는 건 정말 편리하다",
                        "needs_source": True,
                        "needs_fact_check": True,
                        "notes": "AI 검색/즉답 서비스 사용 행태 관련 보조 자료 필요.",
                    }
                ],
            },
            {
                "section_title": "학교와 지식기관은 무엇을 해야 하나",
                "slides": [
                    {
                        "headline": "박물관은 전시품 옆 설명문 이상의 것이 필요해진다",
                        "needs_source": True,
                        "needs_fact_check": True,
                        "notes": "박물관/천문관 공식 사례 확인 필요.",
                    },
                    {
                        "headline": "그러면 이제 공부는 무엇이 되는가",
                        "needs_source": True,
                        "needs_fact_check": False,
                        "notes": "전개용 질문.",
                    }
                ],
            },
        ],
    }


def test_collect_slide_needs_adds_order_and_classification() -> None:
    needs = collect_slide_needs(_storyline())

    assert len(needs) == 3
    assert needs[0]["slide_no"] == 1
    assert needs[0]["local_order"] == 1
    assert needs[0]["priority"] == "high"
    assert needs[1]["evidence_type"] == "institution_example"
    assert needs[2]["evidence_type"] == "rhetorical_bridge"
    assert needs[2]["source_priority"] == "low"


def test_build_evidence_enrichment_plan_outputs_pack_and_reports(tmp_path) -> None:
    bundle_path = tmp_path / "bundle.json"
    storyline_path = tmp_path / "storyline.json"
    pack_path = tmp_path / "pack.json"
    needs_report = tmp_path / "needs.md"
    plan_report = tmp_path / "plan.md"
    bundle_path.write_text(json.dumps(_bundle(), ensure_ascii=False), encoding="utf-8")
    storyline_path.write_text(json.dumps(_storyline(), ensure_ascii=False), encoding="utf-8")

    result = build_evidence_enrichment_plan(
        bundle_path=bundle_path,
        storyline_path=storyline_path,
        evidence_pack_path=pack_path,
        needs_report_path=needs_report,
        plan_report_path=plan_report,
        now=datetime(2026, 5, 18, tzinfo=UTC),
    )

    pack = json.loads(pack_path.read_text(encoding="utf-8"))
    assert validate_with_schema(pack, "evidence_pack_schema.json") == []
    assert result["slide_needs_count"] == 3
    assert "BBC / Royal Observatory 원문 전문 확인" in pack["manual_research_checklist"]
    assert pack["supporting_articles"][0]["url"]
    assert pack["institution_examples"][0]["needs_manual_check"] is False
    plan_text = plan_report.read_text(encoding="utf-8")
    needs_text = needs_report.read_text(encoding="utf-8")
    assert "Milestone 1.5.2" in plan_text
    assert "ready_for_enriched_dry_run: True" in plan_text
    assert "Evidence Status" in needs_text
    assert "rhetorical_bridge" in needs_text
