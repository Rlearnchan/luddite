from luddite.agents.jibi.score_candidates import score_candidate, score_candidates
from luddite.utils.jsonl import write_jsonl


def test_score_candidate_rejects_direct_president_party_evaluation() -> None:
    candidate = {
        "candidate_id": "jibi_1",
        "title": "대통령 발언 직후 증시 급등락",
        "summary": "속보성 정치/시장 뉴스",
        "why_interesting": "숫자는 있지만 정치 민감도 높음",
        "risk_flags": ["political_sensitivity", "investment_advice_risk"],
        "published_at": "2026-05-17",
        "evidence_depth_hint": "medium",
    }

    scored = score_candidate(candidate)

    assert scored["recommended_action"] == "reject"
    assert scored["blocked_reason"] == "direct_president_party_evaluation"
    assert scored["risk_level"] == "high"
    assert "total_score" in scored["scores"]
    assert scored["scores"]["weights"]["broadcast_potential_proxy"] == 25


def test_score_candidate_sends_strong_sensitive_nonpolitical_to_editorial_review() -> None:
    candidate = {
        "candidate_id": "jibi_hippo",
        "title": "콜롬비아 마약왕의 하마, 살처분 대신 인도행?",
        "summary": "이상한 동물 뉴스 hook과 인도 소비재 시장 확장",
        "why_interesting": "엥? hook과 구조 확장",
        "risk_flags": ["crime_or_drug_sensitivity"],
        "published_at": "2026-05-17",
        "evidence_depth_hint": "medium",
    }

    scored = score_candidate(candidate)

    assert scored["final_grade"] in {"A", "B", "C"}
    assert scored["risk_level"] == "high"
    assert scored["recommended_action"] == "editorial_review"


def test_score_candidate_gathers_more_evidence_for_strong_hook_with_weak_evidence() -> None:
    candidate = {
        "candidate_id": "jibi_need_sources",
        "title": "이상한 전당포 밈이 갑자기 유행",
        "summary": "엥? hook은 강하지만 근거가 부족",
        "why_interesting": "엥? hook",
        "risk_flags": [],
        "published_at": "2026-05-17",
        "evidence_depth_hint": "low",
    }

    scored = score_candidate(candidate)

    assert scored["recommended_action"] == "gather_more_evidence"


def test_score_candidate_gathers_more_evidence_for_investment_risk() -> None:
    candidate = {
        "candidate_id": "jibi_f88",
        "title": "베트남 전당포 F88, 메인 증시 이전 상장 추진",
        "summary": "전당포 상장과 신흥국 금융시장 구조",
        "why_interesting": "엥? hook과 구조 확장",
        "risk_flags": ["investment_advice_risk"],
        "published_at": "2026-05-17",
        "evidence_depth_hint": "medium",
    }

    scored = score_candidate(candidate)

    assert scored["recommended_action"] == "gather_more_evidence"


def test_score_candidates_sorts_by_total_score(tmp_path) -> None:
    input_path = tmp_path / "candidates.jsonl"
    output_path = tmp_path / "scored.jsonl"
    write_jsonl(
        input_path,
        [
            {
                "candidate_id": "low",
                "title": "단순 신제품 출시",
                "summary": "",
                "why_interesting": "",
                "risk_flags": ["corporate_promo_risk"],
            },
            {
                "candidate_id": "high",
                "title": "300달러 드론을 수백만 달러 미사일로 막는 비용 역전",
                "summary": "시장 구조와 숫자",
                "why_interesting": "엥? hook과 구조 확장",
                "risk_flags": [],
            },
        ],
    )

    scored = score_candidates(input_path=input_path, output_path=output_path)

    assert scored[0]["candidate_id"] == "high"
    assert output_path.exists()
