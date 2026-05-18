import json
from datetime import UTC, datetime

from luddite import paths
from luddite.agents.anny.build_input_bundle import build_anny_input_bundles
from luddite.utils.jsonl import read_jsonl, write_jsonl
from luddite.utils.schemas import load_schema, validate_with_schema


def _handoff_seed() -> dict:
    return {
        "cluster_id": "cluster_productive_finance",
        "story_seed_title": "생산적 금융과 정책자금 전환",
        "readiness": "needs_more_evidence",
        "handoff_priority": "high",
        "primary_seed_candidate_id": "candidate_one",
        "candidate_ids": ["candidate_one"],
        "source_ids": ["infomax_manual"],
        "editorial_category": "productive_finance_policy",
        "seed_type": "productive_finance_policy",
        "why_story": "정책금융이 생산적 투자로 이동해야 한다는 문제",
        "known_facts": ["이억원 발언 (연합인포맥스)"],
        "missing_evidence": ["공식 자료 또는 숫자/통계 확인"],
        "possible_story_angles": ["정책금융 역할", "위험분담"],
        "risk_flags": [],
        "risk_level": "low",
        "quality_flags": ["official_evidence_missing"],
        "official_evidence_needed": True,
        "suggested_official_sources": ["금융위원회", "한국은행"],
        "syuka_ops_query_terms": ["생산적 금융", "국민성장펀드"],
        "llm_enrichment_needed": True,
        "next_action": "공식자료 보강",
    }


def _candidate() -> dict:
    return {
        "candidate_id": "candidate_one",
        "title": "이억원 \"담보 및 단기수익 중심 금융 경쟁 앞서가기 어려워\"",
        "seed_url": "https://example.com/finance",
        "source": "연합인포맥스",
        "source_id": "infomax_manual",
        "source_url_canonical": "https://example.com/finance",
        "duplicate_key": "rss_finance",
        "published_at": "2026-05-18 14:03:00",
        "summary": "정책금융이 생산적 투자 중심으로 이동해야 한다는 발언.",
        "why_interesting": "정책금융이 생산적 투자로 이동하는 구조",
        "possible_expansions": ["정책금융 역할"],
        "evidence_needed": ["원문 기사 링크", "숫자/통계 또는 공식 자료"],
        "final_grade": "B",
        "recommended_action": "gather_more_evidence",
        "editorial_category": "productive_finance_policy",
        "risk_flags": [],
        "quality_flags": [],
    }


def test_anny_input_bundle_schema_loads() -> None:
    assert load_schema("anny_input_bundle_schema.json")["title"] == "AnnyInputBundle"


def test_handoff_seed_becomes_input_bundle_with_candidate_article(tmp_path) -> None:
    handoff_path = tmp_path / "handoff.jsonl"
    candidates_path = tmp_path / "scored.jsonl"
    output_path = tmp_path / "bundles.jsonl"
    report_path = tmp_path / "bundles.md"
    write_jsonl(handoff_path, [_handoff_seed()])
    write_jsonl(candidates_path, [_candidate()])

    bundles = build_anny_input_bundles(
        handoff_path=handoff_path,
        candidates_path=candidates_path,
        output_path=output_path,
        report_path=report_path,
        now=datetime(2026, 5, 18, tzinfo=UTC),
    )

    assert len(bundles) == 1
    bundle = bundles[0]
    assert bundle["story_seed_id"] == "cluster_productive_finance"
    assert bundle["candidate_articles"][0]["candidate_id"] == "candidate_one"
    assert bundle["candidate_articles"][0]["source_url_canonical"] == "https://example.com/finance"
    assert bundle["candidate_articles"][0]["duplicate_key"] == "rss_finance"
    assert (
        bundle["candidate_articles"][0]["why_interesting"]
        == "정책금융이 생산적 투자로 이동하는 구조"
    )
    assert bundle["candidate_articles"][0]["final_grade"] == "B"
    assert bundle["candidate_articles"][0]["recommended_action"] == "gather_more_evidence"
    assert "원문 전문 확인" in bundle["candidate_articles"][0]["evidence_needed"]
    assert "원문 기사 링크" not in bundle["candidate_articles"][0]["evidence_needed"]
    assert "금융은 안전하게 돈을 빌려주는 산업인가" in bundle["core_question"]
    assert "담보·단기수익 중심 금융의 한계" in bundle["suggested_story_structure"]
    assert "원문 기사 링크" not in bundle["missing_evidence"]
    assert "원문 전문 확인" in bundle["fact_check_tasks"]
    assert "숫자/통계 원자료 확인" in bundle["required_evidence"]
    assert bundle["opening_hook"].startswith("이억원")
    assert bundle["slide_count_target"].startswith("standard")
    assert "정책 효과를 단정하지 말 것" in bundle["do_not_claim"]
    assert "투자 조언처럼 쓰지 말 것" in bundle["do_not_claim"]
    assert "가격/수익률/주가 전망을 단정하지 말 것" in bundle["do_not_claim"]
    assert "특정 금융회사/정책상품 홍보처럼 쓰지 말 것" in bundle["avoid"]
    assert "investment_advice_risk" in bundle["risk_flags"]
    assert "single_source_dependency" in bundle["risk_flags"]
    assert "official_evidence_missing" in bundle["risk_flags"]
    assert "현재 단일 기사 기반임을 잊지 말 것" in bundle["do_not_claim"]
    assert bundle["needs_fact_check"] is True
    assert validate_with_schema(bundle, "anny_input_bundle_schema.json") == []
    assert read_jsonl(output_path)[0]["bundle_id"] == bundle["bundle_id"]
    assert "생산적 금융과 정책자금 전환" in report_path.read_text(encoding="utf-8")


def test_do_not_claim_includes_risk_specific_rules(tmp_path) -> None:
    seed = _handoff_seed()
    seed["cluster_id"] = "cluster_market"
    seed["story_seed_title"] = "금리/자산가격 스트레스와 거시 리스크"
    seed["editorial_category"] = "market_rate_stress"
    seed["risk_flags"] = ["investment_advice_risk"]
    seed["risk_level"] = "medium"
    seed["readiness"] = "editorial_review"
    handoff_path = tmp_path / "handoff.jsonl"
    candidates_path = tmp_path / "scored.jsonl"
    write_jsonl(handoff_path, [seed])
    write_jsonl(candidates_path, [_candidate() | {"risk_flags": ["investment_advice_risk"]}])

    bundles = build_anny_input_bundles(
        handoff_path=handoff_path,
        candidates_path=candidates_path,
        output_path=tmp_path / "bundles.jsonl",
        report_path=tmp_path / "bundles.md",
        now=datetime(2026, 5, 18, tzinfo=UTC),
    )

    assert "특정 자산/주식 매수·매도 의견처럼 쓰지 말 것" in bundles[0]["do_not_claim"]
    assert bundles[0]["needs_fact_check"] is True


def test_single_company_financing_gets_loose_cluster_bridge_flag(tmp_path) -> None:
    seed = _handoff_seed()
    seed["cluster_id"] = "cluster_company"
    seed["story_seed_title"] = "AI 공급망 투자와 단일 기업 자금조달"
    seed["editorial_category"] = "single_company_financing"
    seed["risk_flags"] = ["corporate_promo_risk", "investment_advice_risk"]
    seed["risk_level"] = "medium"
    handoff_path = tmp_path / "handoff.jsonl"
    candidates_path = tmp_path / "scored.jsonl"
    write_jsonl(handoff_path, [seed])
    write_jsonl(candidates_path, [_candidate()])

    bundles = build_anny_input_bundles(
        handoff_path=handoff_path,
        candidates_path=candidates_path,
        output_path=tmp_path / "bundles.jsonl",
        report_path=tmp_path / "bundles.md",
        now=datetime(2026, 5, 18, tzinfo=UTC),
    )

    assert "loose_cluster_bridge" in bundles[0]["quality_flags"]
    assert (
        "서로 약하게 연결된 단일 기업 뉴스를 하나의 확정 서사로 묶지 말 것"
        in bundles[0]["avoid"]
    )


def test_anny_dry_run_cases_json_loads() -> None:
    with (paths.EVAL_DIR / "golden_cases" / "anny_dry_run_cases.json").open(
        encoding="utf-8"
    ) as source:
        payload = json.load(source)

    assert payload["version"] == "v1.6"
    assert payload["cases"][0]["case_id"] == "anny_dry_run_ai_knowledge_institution_v1"
    assert payload["cases"][1]["case_id"] == "anny_dry_run_productive_finance_policy_v1"
