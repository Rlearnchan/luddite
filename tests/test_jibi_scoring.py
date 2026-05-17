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
    assert "political_direct_eval" in scored["failure_modes"]


def test_score_candidate_keeps_overseas_political_fracture_out_of_hard_reject() -> None:
    candidate = {
        "candidate_id": "jibi_uk_reform",
        "title": "영국 양당 지지율 동반 하락과 개혁당 부상",
        "summary": "포퓰리즘, 지역 격차, 이민, 노동자 계층 이동으로 확장 가능",
        "why_interesting": "해외 정치 균열을 경제/사회 구조로 볼 수 있음",
        "risk_flags": ["political_sensitivity"],
        "published_at": "2026-05-17",
        "evidence_depth_hint": "medium",
        "possible_expansions": [
            "포퓰리즘과 지역 격차",
            "이민 이슈와 노동자 계층 이동",
            "채권시장과 정책 불확실성",
        ],
    }

    scored = score_candidate(candidate)

    assert scored["blocked_reason"] is None
    assert scored["recommended_action"] in {"editorial_review", "gather_more_evidence"}
    assert "political_direct_eval" not in scored["failure_modes"]


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
    assert scored["recommended_action"] != "send_to_anny"
    assert "thin_evidence" in scored["failure_modes"]


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


def test_score_candidate_only_sends_to_anny_when_evidence_is_ready() -> None:
    candidate = {
        "candidate_id": "jibi_drone_ready",
        "title": "300달러 드론을 수백만 달러 미사일로 막는 비용 역전",
        "seed_url": "https://example.com/drone-cost",
        "summary": "우크라이나 전장과 방공 비용 구조를 숫자로 비교",
        "why_interesting": "값싼 드론과 비싼 방어 수단의 비용 교환비가 핵심",
        "risk_flags": [],
        "published_at": "2026-05-17",
        "evidence_depth_hint": "high",
        "source_count": 2,
        "possible_expansions": [
            "우크라이나/중동 전장에서 드론이 비용 구조를 바꾼 사례",
            "싼 공격 수단을 비싼 미사일로 막는 방어자 딜레마",
            "레이저/전자전/그물총 같은 저비용 대응책 경쟁",
        ],
        "evidence_needed": ["방산 지출 비교 수치의 최신 연도 확인"],
    }

    scored = score_candidate(candidate)

    assert scored["recommended_action"] == "send_to_anny"


def test_score_candidate_keeps_no_ai_label_out_of_hard_reject() -> None:
    candidate = {
        "candidate_id": "jibi_no_ai_label",
        "title": "AI 미사용 라벨을 붙이는 브랜드들",
        "seed_url": "https://example.com/no-ai",
        "summary": "AI slop 피로감과 진정성 마케팅",
        "why_interesting": "AI 표기 규제와 창작자 반발로 확장 가능",
        "risk_flags": ["corporate_promo_risk"],
        "published_at": "2026-05-17",
        "evidence_depth_hint": "medium",
        "possible_expansions": [
            "AI slop 범람과 소비자 피로감",
            "진정성 마케팅과 AI 미사용 라벨",
            "AI 표기 규제와 창작자 반발",
        ],
    }

    scored = score_candidate(candidate)

    assert scored["blocked_reason"] is None
    assert scored["recommended_action"] in {"gather_more_evidence", "keep_for_later"}


def test_score_candidate_fills_empty_possible_expansions() -> None:
    candidate = {
        "candidate_id": "jibi_heat",
        "title": "5월 폭염에 회사 반바지 논쟁",
        "summary": "오피스 복장과 전력 수요 변화",
        "why_interesting": "생활 체감형 소재",
        "risk_flags": [],
        "published_at": "2026-05-17",
        "evidence_depth_hint": "medium",
        "possible_expansions": [],
    }

    scored = score_candidate(candidate)

    assert len(scored["possible_expansions"]) >= 3


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
