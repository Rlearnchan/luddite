"""Rule-based slideability signals for Jibi candidates.

These signals are review hints only. They do not change Jibi ranking,
recommended_action, or handoff readiness.
"""

from __future__ import annotations

from typing import Any

from luddite.agents.jibi.heuristics import contains_any, count_any, text_blob

VISUAL_LEVELS = ("low", "medium", "high")
PROOF_LEVELS = ("none", "weak", "strong")

CHART_TERMS = {
    "%",
    "억",
    "조",
    "가격",
    "비율",
    "비중",
    "순위",
    "통계",
    "추세",
    "예산",
    "금리",
    "고용",
    "gdp",
    "투자액",
    "증가",
    "감소",
    "역대",
    "상위",
    "하위",
    "추이",
    "전년 대비",
    "year-on-year",
    "ranking",
    "rank",
    "ratio",
    "trend",
    "budget",
    "interest rate",
    "yield",
    "employment",
    "investment",
    "million",
    "billion",
    "trillion",
    "percent",
}
DIAGRAM_TERMS = {
    "구조",
    "이해관계자",
    "흐름",
    "과정",
    "메커니즘",
    "원인",
    "결과",
    "왜",
    "이어",
    "전환",
    "충돌",
    "갈등",
    "역할",
    "위험분담",
    "공급망",
    "정책",
    "산업",
    "금융",
    "규제",
    "actor",
    "mechanism",
    "result",
    "tradeoff",
    "process",
    "conflict",
    "tension",
    "transition",
    "supply chain",
}
SCREENSHOT_TERMS = {
    "기사",
    "보고서",
    "기관",
    "발표",
    "논문",
    "웹페이지",
    "표",
    "그림",
    "자료",
    "statement",
    "report",
    "paper",
    "webpage",
    "table",
    "figure",
}
SOURCE_CARD_TERMS = {
    "연합인포맥스",
    "bbc",
    "npr",
    "reuters",
    "ap",
    "guardian",
    "금융위원회",
    "한국은행",
    "기획재정부",
    "과학기술정보통신부",
    "산업통상자원부",
    "정부",
    "un",
    "oecd",
    "imf",
    "world bank",
    "official",
    "ministry",
}
OFFICIAL_DATA_TERMS = {
    "정책",
    "금융",
    "시장",
    "투자",
    "금리",
    "예산",
    "통계",
    "gdp",
    "고용",
    "policy",
    "finance",
    "market",
    "investment",
    "rate",
    "budget",
}
MARKET_RISK_TERMS = {
    "주식",
    "증시",
    "코스피",
    "채권",
    "금리",
    "비트코인",
    "코인",
    "stock",
    "market",
    "bond",
    "crypto",
    "yield",
}
ABSTRACT_TERMS = {
    "철학",
    "가치",
    "의미",
    "담론",
    "개념",
    "정체성",
    "생각",
    "문화",
    "관점",
    "philosophy",
    "identity",
    "meaning",
    "concept",
}
GENERIC_STORY_REASON_TERMS = {
    "배경",
    "이해관계자",
    "구조적 연결고리",
    "한국 시청자",
    "structural connection",
}
CATEGORY_PROOF_HINTS = {
    "productive_finance_policy": ("diagram", "chart", "source_card"),
    "industrial_policy_rnd": ("diagram", "chart", "source_card"),
    "infrastructure_project_failure": ("diagram", "chart", "source_card"),
    "ai_knowledge_institution": ("diagram", "source_card"),
    "climate_policy_conflict": ("diagram", "source_card"),
    "market_rate_stress": ("chart", "diagram", "source_card"),
    "single_company_financing": ("chart", "source_card"),
    "cost_asymmetry": ("chart", "diagram"),
    "macro_research_note": ("chart", "diagram", "source_card"),
    "policy_research_note": ("chart", "diagram", "source_card"),
    "academic_explainer": ("diagram", "source_card"),
    "policy_release_seed": ("chart", "diagram", "source_card"),
}


def _candidate_text(candidate: dict[str, Any]) -> str:
    return text_blob(
        candidate.get("title"),
        candidate.get("summary"),
        candidate.get("why_interesting"),
        " ".join(str(item) for item in candidate.get("possible_expansions", [])),
        candidate.get("source"),
        candidate.get("source_id"),
        candidate.get("source_type"),
        candidate.get("editorial_category"),
        candidate.get("seed_type"),
    )


def _level(score: int, *, strong: int, weak: int) -> str:
    if score >= strong:
        return "strong"
    if score >= weak:
        return "weak"
    return "none"


def _visualizability(score: float) -> str:
    if score >= 0.68:
        return "high"
    if score >= 0.36:
        return "medium"
    return "low"


def _source_count(candidate: dict[str, Any]) -> int:
    value = candidate.get("source_count")
    if isinstance(value, int):
        return value
    supporting_articles = candidate.get("supporting_articles")
    if isinstance(supporting_articles, list):
        return max(1, len(supporting_articles) + 1)
    return 1


def _source_title(candidate: dict[str, Any]) -> str:
    return str(candidate.get("source") or candidate.get("source_id") or "").strip()


def _generic_story_reason(candidate: dict[str, Any], text: str) -> bool:
    quality_flags = set(str(item) for item in candidate.get("quality_flags", []))
    return (
        "generic_story_reason" in quality_flags
        or count_any(text, GENERIC_STORY_REASON_TERMS) >= 3
    )


def _first_slide_idea(
    *,
    candidate: dict[str, Any],
    chartability: str,
    diagramability: str,
    source_card_fit: str,
) -> str:
    title = str(candidate.get("title") or "후보 소재").strip()
    category = str(candidate.get("editorial_category") or candidate.get("seed_type") or "")
    if diagramability == "strong" and chartability in {"strong", "weak"}:
        return f"{title}: 구조 diagram으로 시작하고 핵심 숫자는 보조 chart로 확인"
    if chartability == "strong":
        return f"{title}: 핵심 수치/추세를 한 장 chart로 먼저 보여주기"
    if diagramability == "strong":
        return f"{title}: actor -> mechanism -> result 구조 diagram"
    if source_card_fit == "strong":
        return f"{title}: 원문 source card로 시작해 쟁점 질문 제시"
    if category:
        return f"{title}: {category} 관점의 질문형 title slide"
    return f"{title}: 질문형 title slide"


def _likely_proof_types(
    *,
    candidate: dict[str, Any],
    chartability: str,
    diagramability: str,
    source_card_fit: str,
) -> list[str]:
    proof_types: list[str] = []
    if diagramability in {"strong", "weak"}:
        proof_types.append("diagram")
    if chartability in {"strong", "weak"}:
        proof_types.append("chart")
    if source_card_fit in {"strong", "weak"}:
        proof_types.append("source_card")
    category = str(candidate.get("editorial_category") or candidate.get("seed_type") or "")
    proof_types.extend(CATEGORY_PROOF_HINTS.get(category, ()))
    return list(dict.fromkeys(proof_types))[:4]


def _risks(
    *,
    candidate: dict[str, Any],
    text: str,
    score: float,
    chartability: str,
    diagramability: str,
    source_card_fit: str,
) -> list[str]:
    risks: list[str] = []
    if contains_any(text, ABSTRACT_TERMS) and chartability == "none" and diagramability == "none":
        risks.append("too_abstract")
    if _source_count(candidate) <= 1:
        risks.append("single_source")
    if contains_any(text, OFFICIAL_DATA_TERMS) and chartability in {"weak", "strong"}:
        risks.append("needs_official_data")
    risk_flags = set(candidate.get("risk_flags", []))
    if "investment_advice_risk" in risk_flags or contains_any(text, MARKET_RISK_TERMS):
        risks.append("market_claim_risk")
    if "political_sensitivity" in risk_flags or contains_any(text, {"정책", "정부", "policy"}):
        risks.append("policy_claim_risk")
    no_visual_channel = (
        chartability == "none" and diagramability == "none" and source_card_fit == "none"
    )
    if score < 0.36 or no_visual_channel:
        risks.append("no_clear_visual")
    return list(dict.fromkeys(risks))


def analyze_slideability(candidate: dict[str, Any]) -> dict[str, Any]:
    """Return deterministic slideability review hints for one candidate."""
    text = _candidate_text(candidate)
    category = str(candidate.get("editorial_category") or candidate.get("seed_type") or "")
    chart_signal = count_any(text, CHART_TERMS) + int(any(char.isdigit() for char in text))
    diagram_signal = count_any(text, DIAGRAM_TERMS)
    screenshot_signal = count_any(text, SCREENSHOT_TERMS)
    source_signal = count_any(text, SOURCE_CARD_TERMS)
    if candidate.get("seed_url"):
        source_signal += 1
        screenshot_signal += 1
    if _source_title(candidate):
        source_signal += 1
    if _source_count(candidate) >= 2:
        source_signal += 1
    if category in CATEGORY_PROOF_HINTS:
        diagram_signal += int("diagram" in CATEGORY_PROOF_HINTS[category])
        chart_signal += int("chart" in CATEGORY_PROOF_HINTS[category])
        source_signal += int("source_card" in CATEGORY_PROOF_HINTS[category])
    if _generic_story_reason(candidate, text) and category not in CATEGORY_PROOF_HINTS:
        diagram_signal = max(0, diagram_signal - 2)

    chartability = _level(chart_signal, strong=3, weak=1)
    diagramability = _level(diagram_signal, strong=3, weak=1)
    screenshotability = _level(screenshot_signal, strong=3, weak=1)
    source_card_fit = _level(source_signal, strong=3, weak=1)

    raw_score = (
        min(chart_signal, 4) * 0.18
        + min(diagram_signal, 4) * 0.22
        + min(screenshot_signal, 3) * 0.08
        + min(source_signal, 4) * 0.10
    )
    score = round(min(1.0, raw_score), 2)
    visualizability = _visualizability(score)
    risks = _risks(
        candidate=candidate,
        text=text,
        score=score,
        chartability=chartability,
        diagramability=diagramability,
        source_card_fit=source_card_fit,
    )
    likely_proof_types = _likely_proof_types(
        candidate=candidate,
        chartability=chartability,
        diagramability=diagramability,
        source_card_fit=source_card_fit,
    )
    reason_parts = [
        f"chart={chartability}",
        f"diagram={diagramability}",
        f"source_card={source_card_fit}",
    ]
    if risks:
        reason_parts.append(f"risks={', '.join(risks)}")
    return {
        "score": score,
        "visualizability": visualizability,
        "chartability": chartability,
        "diagramability": diagramability,
        "screenshotability": screenshotability,
        "source_card_fit": source_card_fit,
        "first_slide_idea": _first_slide_idea(
            candidate=candidate,
            chartability=chartability,
            diagramability=diagramability,
            source_card_fit=source_card_fit,
        ),
        "likely_proof_object_types": likely_proof_types,
        "risks": risks,
        "reason": "; ".join(reason_parts),
    }


def merge_cluster_slideability(candidates: list[dict[str, Any]]) -> dict[str, Any]:
    """Aggregate candidate slideability for a story seed cluster."""
    slideabilities = [
        item.get("slideability")
        for item in candidates
        if isinstance(item.get("slideability"), dict)
    ]
    if not slideabilities:
        return analyze_slideability(candidates[0]) if candidates else analyze_slideability({})
    best = max(slideabilities, key=lambda item: float(item.get("score", 0) or 0))
    proof_types: list[str] = []
    risks: list[str] = []
    for item in slideabilities:
        proof_types.extend(str(value) for value in item.get("likely_proof_object_types", []))
        risks.extend(str(value) for value in item.get("risks", []))
    avg_score = round(
        sum(float(item.get("score", 0) or 0) for item in slideabilities) / len(slideabilities),
        2,
    )
    return {
        **best,
        "score": max(float(best.get("score", 0) or 0), avg_score),
        "likely_proof_object_types": list(dict.fromkeys(proof_types))[:5],
        "risks": list(dict.fromkeys(risks)),
        "reason": f"cluster best: {best.get('reason', '')}",
    }
