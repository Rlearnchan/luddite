from luddite.agents.jibi.score_candidates import score_candidate
from luddite.agents.jibi.slideability import analyze_slideability


def test_numeric_trend_candidate_has_chartability() -> None:
    candidate = {
        "candidate_id": "chart",
        "title": "2030년까지 504억 투입, 예산 증가 추세",
        "summary": "정부 R&D 예산과 투자액, 전년 대비 증가율을 비교할 수 있다.",
        "source": "과학기술정보통신부",
        "seed_url": "https://example.com/report",
    }

    slideability = analyze_slideability(candidate)

    assert slideability["chartability"] in {"weak", "strong"}
    assert "chart" in slideability["likely_proof_object_types"]


def test_actor_mechanism_result_candidate_has_diagramability() -> None:
    candidate = {
        "candidate_id": "diagram",
        "title": "은행 담보대출 관행이 장기 위험자본 부족으로 이어지는 구조",
        "summary": "은행, 정책금융, AI 반도체 투자자가 왜 충돌하는지 설명한다.",
        "why_interesting": "actor -> mechanism -> result 구조가 뚜렷하다.",
        "editorial_category": "productive_finance_policy",
        "source": "연합인포맥스",
        "seed_url": "https://example.com/policy",
    }

    slideability = analyze_slideability(candidate)

    assert slideability["diagramability"] == "strong"
    assert "diagram" in slideability["likely_proof_object_types"]


def test_clear_report_source_has_source_card_fit() -> None:
    candidate = {
        "candidate_id": "source",
        "title": "OECD report warns of grid investment gap",
        "summary": "보고서 원문과 기관명이 명확해 source card로 보여주기 좋다.",
        "source": "OECD report",
        "source_type": "official_release",
        "seed_url": "https://example.com/oecd-report",
    }

    slideability = analyze_slideability(candidate)

    assert slideability["source_card_fit"] == "strong"
    assert "source_card" in slideability["likely_proof_object_types"]


def test_abstract_candidate_gets_visual_risk() -> None:
    candidate = {
        "candidate_id": "abstract",
        "title": "현대 사회에서 의미와 정체성의 변화",
        "summary": "철학적 개념과 가치 담론 중심이라 구체 화면이 떠오르지 않는다.",
        "source": "",
    }

    slideability = analyze_slideability(candidate)

    assert "too_abstract" in slideability["risks"]
    assert "no_clear_visual" in slideability["risks"]


def test_scoring_adds_slideability_without_changing_action_shape() -> None:
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
    assert scored["slideability"]["score"] > 0
    assert scored["slideability"]["likely_proof_object_types"]

