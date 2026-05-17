"""Rule-based pre-score for jibi candidate drafts."""

from __future__ import annotations

from pathlib import Path
from typing import Annotated, Any

import typer
from rich.console import Console

from luddite import paths
from luddite.agents.jibi.heuristics import (
    NUMBER_TERMS,
    POLITICAL_TERMS,
    PUNCHLINE_TERMS,
    STRUCTURAL_TERMS,
    WEIRD_TERMS,
    contains_any,
    count_any,
    infer_seed_type,
    text_blob,
)
from luddite.utils.jsonl import read_jsonl, write_jsonl
from luddite.utils.urls import canonicalize_url

app = typer.Typer(no_args_is_help=False)
console = Console()

HIGH_RISK_FLAGS = {
    "political_sensitivity",
    "medical_claim_risk",
    "crime_or_drug_sensitivity",
    "live_news_volatility",
}
DOMESTIC_POLITICAL_TARGET_TERMS = {
    "대통령",
    "국회",
    "여당",
    "야당",
    "정당",
    "민주당",
    "국민의힘",
    "정치인",
}
DIRECT_POLITICAL_FRAME_TERMS = {
    "지지율",
    "지지",
    "비판",
    "호불호",
    "인성",
    "가십",
    "발언 직후",
    "정쟁",
    "급등락",
    "폭등",
    "폭락",
    "approval",
    "support",
    "critic",
    "personality",
}
OVERSEAS_POLITICAL_CONTEXT_TERMS = {
    "영국",
    "미국",
    "프랑스",
    "독일",
    "일본",
    "캐나다",
    "유럽",
    "개혁당",
    "해외",
    "uk",
    "britain",
    "british",
    "reform party",
    "u.s.",
    "europe",
    "canada",
}
STRUCTURAL_POLITICAL_CONTEXT_TERMS = {
    "포퓰리즘",
    "지역 격차",
    "채권시장",
    "이민",
    "노동자",
    "계층",
    "경제",
    "사회 구조",
    "populism",
    "immigration",
    "bond market",
    "working class",
    "regional",
}
GENERIC_EVIDENCE_REQUESTS = {
    "원문 기사 링크",
    "추가 독립 출처 1개 이상",
    "추가 독립 출처 확인",
    "숫자/통계 또는 공식 자료",
}
GENERIC_EXPANSIONS = {
    "배경 설명",
    "구조적 확장",
    "한국 시청자 연결 지점",
}
FALLBACK_EXPANSIONS = {
    "cost_asymmetry": [
        "우크라이나/중동 전장에서 드론이 비용 구조를 바꾼 사례",
        "싼 공격 수단을 비싼 미사일로 막는 방어자 딜레마",
        "레이저/전자전/그물총 같은 저비용 대응책 경쟁",
    ],
    "life_change": [
        "5월 폭염과 일본 40도 용어",
        "에너지 가격과 오피스 복장 변화",
        "한국 기업 쿨비즈/반바지 문화",
    ],
    "political_fracture": [
        "정당 지지율보다 제도/지역 균열 중심으로 재구성",
        "경제 불만과 시장/정책 영향",
        "직접 정치 평가를 피하는 안전한 설명 프레임",
    ],
    "industry_disruption": [
        "공급망/전력/인프라 병목",
        "기업 단일 이슈가 아니라 산업 구조 변화로 확장",
        "숫자/그래프/공식자료로 확인할 포인트",
    ],
    "absurd_foreign": [
        "이상한 해외 뉴스가 나온 배경",
        "현지 시장/사회 구조로 확장되는 지점",
        "한국 시청자가 이해할 수 있는 비유와 회수",
    ],
}

SCORING_WEIGHTS = {
    "broadcast_potential_proxy": 25,
    "evidence_depth": 20,
    "numbers_strength": 15,
    "weird_hook": 12,
    "structural_expansion": 12,
    "punchline_potential": 8,
    "timeliness": 5,
    "risk_penalty": -30,
}


def _bounded(value: int, low: int = 0, high: int = 5) -> int:
    return max(low, min(high, value))


def _score_band(total_score: int, risk_penalty: int) -> str:
    if risk_penalty >= 4 and total_score < 70:
        return "D"
    if total_score >= 75:
        return "A"
    if total_score >= 55:
        return "B"
    if total_score >= 35:
        return "C"
    return "D"


def _risk_level(risk_flags: list[str], risk_penalty: int) -> str:
    if risk_penalty >= 4 or any(flag in HIGH_RISK_FLAGS for flag in risk_flags):
        return "high"
    if risk_penalty >= 2 or risk_flags:
        return "medium"
    return "low"


def _is_direct_domestic_political_evaluation(text: str) -> bool:
    """Hard reject only direct domestic president/party evaluation frames."""
    if contains_any(text, OVERSEAS_POLITICAL_CONTEXT_TERMS) and (
        contains_any(text, STRUCTURAL_POLITICAL_CONTEXT_TERMS)
        or not contains_any(text, {"대통령", "국회", "민주당", "국민의힘"})
    ):
        return False

    has_domestic_target = contains_any(text, DOMESTIC_POLITICAL_TARGET_TERMS)
    has_direct_frame = contains_any(text, DIRECT_POLITICAL_FRAME_TERMS)
    return has_domestic_target and has_direct_frame


def _is_overseas_political_fracture(candidate: dict[str, Any], text: str) -> bool:
    seed_type = str(candidate.get("seed_type") or "")
    return (
        seed_type == "political_fracture"
        or contains_any(text, OVERSEAS_POLITICAL_CONTEXT_TERMS)
    ) and contains_any(text, STRUCTURAL_POLITICAL_CONTEXT_TERMS)


def _source_count(candidate: dict[str, Any]) -> int:
    explicit = candidate.get("source_count")
    if isinstance(explicit, int):
        return explicit
    supporting_articles = candidate.get("supporting_articles")
    if isinstance(supporting_articles, list) and supporting_articles:
        return len(supporting_articles) + 1
    return 1


def _has_source_link(candidate: dict[str, Any]) -> bool:
    source_url = canonicalize_url(str(candidate.get("seed_url") or ""))
    return source_url.startswith(("http://", "https://"))


def _has_official_source(candidate: dict[str, Any]) -> bool:
    official_sources = candidate.get("official_sources")
    if isinstance(official_sources, list) and official_sources:
        return True
    if candidate.get("official_source_count"):
        return True
    return candidate.get("source_type") == "official_release"


def _evidence_needed_is_generic(candidate: dict[str, Any]) -> bool:
    evidence_needed = [
        str(value).strip()
        for value in candidate.get("evidence_needed", [])
        if str(value).strip()
    ]
    if not evidence_needed:
        return True
    return any(
        item in GENERIC_EVIDENCE_REQUESTS
        or "원문 기사 링크" in item
        or "추가 독립 출처" in item
        or "숫자/통계" in item
        or "공식 자료" in item
        for item in evidence_needed
    )


def _concrete_expansions(candidate: dict[str, Any], text: str) -> list[str]:
    expansions = [
        str(value).strip()
        for value in candidate.get("possible_expansions", [])
        if str(value).strip()
    ]
    if len(expansions) >= 3 and not set(expansions).issubset(GENERIC_EXPANSIONS):
        return expansions
    seed_type = str(
        candidate.get("seed_type") or infer_seed_type(str(candidate.get("title", "")), text)
    )
    return FALLBACK_EXPANSIONS.get(
        seed_type,
        [
            "핵심 사건의 배경과 이해관계자",
            "시장/사회/제도 구조로 확장되는 지점",
            "한국 시청자가 체감할 수 있는 비교 사례",
        ],
    )


def _has_storyline_ready_evidence(
    *,
    candidate: dict[str, Any],
    evidence_depth: int,
    possible_expansions: list[str],
) -> bool:
    return (
        _has_source_link(candidate)
        and (_source_count(candidate) >= 2 or _has_official_source(candidate))
        and evidence_depth >= 3
        and len(possible_expansions) >= 3
        and not _evidence_needed_is_generic(candidate)
    )


def _failure_modes(
    *,
    candidate: dict[str, Any],
    risk_flags: list[str],
    blocked_reason: str | None,
    evidence_depth: int,
    final_grade: str,
    broadcast_potential_proxy: int,
) -> list[str]:
    modes = [
        str(value).strip()
        for value in candidate.get("failure_modes", [])
        if str(value).strip()
    ]
    if blocked_reason == "direct_president_party_evaluation":
        modes.append("political_direct_eval")
    if evidence_depth < 3 or _evidence_needed_is_generic(candidate):
        modes.append("thin_evidence")
    if "corporate_promo_risk" in risk_flags and broadcast_potential_proxy <= 2:
        modes.append("single_company_frame")
    if "investment_advice_risk" in risk_flags and contains_any(
        text_blob(candidate.get("title"), candidate.get("summary")),
        {"손절", "목표가", "매수", "매도", "추천", "종목", "stock pick"},
    ):
        modes.append("single_stock_investment_frame")
    if "live_news_volatility" in risk_flags:
        modes.append("live_news_volatility")
    if final_grade == "D" and any(flag in HIGH_RISK_FLAGS for flag in risk_flags):
        modes.append("sensitive_high_low_gain")
    return list(dict.fromkeys(modes))


def _recommended_action(
    *,
    final_grade: str,
    risk_level: str,
    risk_flags: list[str],
    evidence_depth: int,
    numbers_strength: int,
    broadcast_potential_proxy: int,
    storyline_ready_evidence: bool,
    evidence_gap: bool,
    blocked_reason: str | None = None,
) -> str:
    if blocked_reason:
        return "reject"
    if "political_sensitivity" in risk_flags:
        return "editorial_review"
    if risk_level == "high" and final_grade in {"A", "B", "C"}:
        return "editorial_review"
    if broadcast_potential_proxy >= 3 and (evidence_depth < 3 or numbers_strength < 3):
        return "gather_more_evidence"
    if final_grade in {"A", "B"} and risk_level in {"low", "medium"}:
        if storyline_ready_evidence:
            return "send_to_anny"
        return "gather_more_evidence"
    if (
        "investment_advice_risk" in risk_flags
        and evidence_depth >= 3
        and final_grade in {"A", "B", "C"}
    ):
        return "gather_more_evidence"
    if broadcast_potential_proxy >= 3 and evidence_gap:
        return "gather_more_evidence"
    if final_grade == "C":
        return "keep_for_later"
    return "reject"


def _weighted_score(value: int, weight: int) -> float:
    return (value / 5) * weight


def score_candidate(candidate: dict[str, Any]) -> dict[str, Any]:
    text = text_blob(
        candidate.get("title"),
        candidate.get("summary"),
        candidate.get("why_interesting"),
        " ".join(candidate.get("score_reason", [])),
        " ".join(candidate.get("risk_flags", [])),
    )
    risk_flags = list(candidate.get("risk_flags", []))
    blocked_reason = None
    if "political_sensitivity" in risk_flags and _is_direct_domestic_political_evaluation(text):
        blocked_reason = "direct_president_party_evaluation"
    possible_expansions = _concrete_expansions(candidate, text)
    weird_hook = _bounded(1 + count_any(text, WEIRD_TERMS), high=5)
    structural_expansion = _bounded(1 + count_any(text, STRUCTURAL_TERMS), high=5)
    numbers_strength = _bounded(
        1 + count_any(text, NUMBER_TERMS) + int(any(c.isdigit() for c in text))
    )
    punchline_potential = _bounded(1 + count_any(text, PUNCHLINE_TERMS), high=5)
    evidence_depth = {"low": 1, "medium": 3, "high": 5}.get(
        candidate.get("evidence_depth_hint"),
        2,
    )
    timeliness = 3 if candidate.get("published_at") else 2
    broadcast_potential_proxy = _bounded(
        weird_hook + structural_expansion + punchline_potential - 3,
        high=5,
    )
    political_risk_extra = (
        0
        if _is_overseas_political_fracture(candidate, text)
        else 2 if contains_any(text, POLITICAL_TERMS) else 0
    )
    risk_penalty = min(5, len(risk_flags) + political_risk_extra)
    score_components = {
        "broadcast_potential_proxy": round(
            _weighted_score(
                broadcast_potential_proxy,
                SCORING_WEIGHTS["broadcast_potential_proxy"],
            ),
            1,
        ),
        "evidence_depth": round(
            _weighted_score(evidence_depth, SCORING_WEIGHTS["evidence_depth"]),
            1,
        ),
        "numbers_strength": round(
            _weighted_score(numbers_strength, SCORING_WEIGHTS["numbers_strength"]),
            1,
        ),
        "weird_hook": round(_weighted_score(weird_hook, SCORING_WEIGHTS["weird_hook"]), 1),
        "structural_expansion": round(
            _weighted_score(structural_expansion, SCORING_WEIGHTS["structural_expansion"]),
            1,
        ),
        "punchline_potential": round(
            _weighted_score(punchline_potential, SCORING_WEIGHTS["punchline_potential"]),
            1,
        ),
        "timeliness": round(_weighted_score(timeliness, SCORING_WEIGHTS["timeliness"]), 1),
        "risk_penalty": -round(
            _weighted_score(risk_penalty, abs(SCORING_WEIGHTS["risk_penalty"])),
            1,
        ),
    }
    total_score = round(sum(score_components.values()), 1)
    if contains_any(text, {"단발성", "single source"}) or "single_source_dependency" in risk_flags:
        total_score -= 8
    if "corporate_promo_risk" in risk_flags and broadcast_potential_proxy <= 2:
        total_score -= 10
    if blocked_reason:
        total_score = min(total_score, 20)
    if not blocked_reason and _is_overseas_political_fracture(candidate, text):
        total_score = max(total_score, 35)
    total_score = round(max(0, total_score), 1)
    final_grade = _score_band(int(total_score), risk_penalty)
    risk_level = _risk_level(risk_flags, risk_penalty)
    storyline_ready_evidence = _has_storyline_ready_evidence(
        candidate=candidate,
        evidence_depth=evidence_depth,
        possible_expansions=possible_expansions,
    )
    evidence_gap = not storyline_ready_evidence
    recommended_action = _recommended_action(
        final_grade=final_grade,
        risk_level=risk_level,
        risk_flags=risk_flags,
        evidence_depth=evidence_depth,
        numbers_strength=numbers_strength,
        broadcast_potential_proxy=broadcast_potential_proxy,
        storyline_ready_evidence=storyline_ready_evidence,
        evidence_gap=evidence_gap,
        blocked_reason=blocked_reason,
    )
    failure_modes = _failure_modes(
        candidate=candidate,
        risk_flags=risk_flags,
        blocked_reason=blocked_reason,
        evidence_depth=evidence_depth,
        final_grade=final_grade,
        broadcast_potential_proxy=broadcast_potential_proxy,
    )
    scored = {
        **candidate,
        "possible_expansions": possible_expansions,
        "scores": {
            "weights": SCORING_WEIGHTS,
            "components": score_components,
            "broadcast_potential_proxy": broadcast_potential_proxy,
            "evidence_depth": evidence_depth,
            "numbers_strength": numbers_strength,
            "weird_hook": weird_hook,
            "structural_expansion": structural_expansion,
            "punchline_potential": punchline_potential,
            "timeliness": timeliness,
            "risk_penalty": risk_penalty,
            "total_score": total_score,
        },
        "final_grade": final_grade,
        "risk_level": risk_level,
        "recommended_action": recommended_action,
        "blocked_reason": blocked_reason,
        "failure_modes": failure_modes,
        "status": "scored",
    }
    return scored


def score_candidates(
    input_path: Path = paths.JIBI_CANDIDATES_JSONL,
    output_path: Path = paths.JIBI_SCORED_CANDIDATES_JSONL,
) -> list[dict[str, Any]]:
    candidates = read_jsonl(input_path) if input_path.exists() else []
    scored = [score_candidate(candidate) for candidate in candidates]
    scored.sort(
        key=lambda item: (
            item.get("scores", {}).get("total_score", 0),
            item.get("scores", {}).get("broadcast_potential_proxy", 0),
        ),
        reverse=True,
    )
    write_jsonl(output_path, scored)
    return scored


@app.callback(invoke_without_command=True)
def main(
    input_path: Annotated[
        Path,
        typer.Option("--input", help="Jibi candidate JSONL input path."),
    ] = paths.JIBI_CANDIDATES_JSONL,
    output: Annotated[
        Path,
        typer.Option("--output", help="Scored candidate JSONL output path."),
    ] = paths.JIBI_SCORED_CANDIDATES_JSONL,
) -> None:
    scored = score_candidates(input_path=input_path, output_path=output)
    console.print(f"[green]Wrote {len(scored)} scored candidates to {output}.[/green]")


if __name__ == "__main__":
    app()
