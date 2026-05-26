"""Rule-based seed quality diagnostics for Jibi candidates.

These helpers are deliberately deterministic and report-first.  They do not use
LLMs, source allowlist edits, or past-video database access.
"""

from __future__ import annotations

import re
from typing import Any

from luddite.agents.jibi.heuristics import contains_any, text_blob

MONEY_HOUSEHOLD_TERMS = {
    "가격",
    "물가",
    "환불",
    "충전금",
    "선불",
    "잔액",
    "소비자",
    "가계",
    "생활비",
    "비용",
    "cost",
    "price",
    "refund",
    "prepaid",
}
JOB_WORK_TERMS = {
    "청년",
    "노동",
    "일자리",
    "취업",
    "구직",
    "쉬었음",
    "경제활동참가율",
    "직장",
    "회사",
    "노사",
    "workplace",
    "job",
    "labor",
}
PUBLIC_AI_TERMS = {
    "공공",
    "공무원",
    "행정",
    "보고서",
    "치안",
    "드론",
    "병원",
    "ai",
    "인공지능",
}
STRUCTURAL_TERMS = {
    "규제",
    "사각지대",
    "제도",
    "구조",
    "메커니즘",
    "권리",
    "토큰화",
    "시장",
    "산업",
    "공급망",
    "regulation",
    "mechanism",
    "market",
    "industry",
}
OWNERSHIP_REGULATION_TERMS = {
    "권리",
    "조각투자",
    "sto",
    "cbdc",
    "투자자 보호",
    "소유권",
    "regulatory",
}
CONSEQUENCE_TERMS = {
    "영향",
    "부담",
    "비용",
    "피해",
    "환불",
    "소득",
    "임금",
    "물가",
    "위험",
    "리스크",
    "gap",
}
EVERYDAY_ANALOGY_TERMS = {
    "반바지",
    "폭염",
    "양파",
    "계란",
    "스타벅스",
    "배달",
    "마트",
    "농산물",
}
WEIRD_BUT_EXPANDABLE_TERMS = {
    "마른논",
    "써레질",
    "감귤",
    "화장품",
    "우주",
    "스타십",
    "spacex",
}

CONTEST_CAMPAIGN_TERMS = {
    "공모전",
    "캠페인",
    "릴레이",
    "챌린지",
    "contest",
    "campaign",
}
EVENT_DEMO_TERMS = {
    "연시회",
    "시연회",
    "시연",
    "행사",
    "개최",
    "발대식",
    "demonstration",
    "event",
}
MEETING_COORDINATION_TERMS = {
    "회의",
    "간담회",
    "협의",
    "협력방안",
    "업무협약",
    "mou",
    "meeting",
    "coordination",
}
PRODUCT_PROMO_TERMS = {
    "신제품",
    "출시",
    "어패럴",
    "인증",
    "기능성 화장품",
    "특판",
    "프로모션",
    "product",
    "launch",
    "certification",
}
NARROW_MARKET_TERMS = {
    "트랙레코드",
    "loc",
    "수요예측",
    "청약",
    "ipo챗",
    "코스닥리그",
    "막판 격돌",
    "주주배정",
}
ONE_OFF_TERMS = {"단발", "일회성", "one-off", "single article"}
TEXTBOOK_TERMS = {"교과서", "textbook", "설명서", "원론"}
CONCRETE_AUDIENCE_BRIDGE_SIGNALS = {
    "direct_money_or_household_impact",
    "job_workplace_labor_change",
    "consumer_funds_or_regulation_gap",
    "ai_entering_real_operations",
    "everyday_analogy_or_life_hook",
    "ownership_or_regulatory_conflict",
}
MECHANISM_SIGNALS = {
    "distinctive_mechanism",
    "research_note_structural_depth",
    "ownership_or_regulatory_conflict",
    "consequence_or_second_order_effect",
}
PROMO_BULLETIN_FLAGS = {
    "contest_or_campaign_bulletin",
    "event_or_demonstration_only",
    "meeting_or_coordination_only",
    "product_or_certification_promo",
    "narrow_market_track_record",
}
STANDALONE_RESEARCH_NOTE_SIGNALS = {
    "direct_money_or_household_impact",
    "job_workplace_labor_change",
    "consumer_funds_or_regulation_gap",
    "ai_entering_real_operations",
    "everyday_analogy_or_life_hook",
}


def _add_unique(values: list[str], value: str) -> None:
    if value and value not in values:
        values.append(value)


def _company_like_text(text: str) -> bool:
    return bool(
        re.search(r"[A-Z][A-Za-z0-9&. -]{1,24}", text)
        or contains_any(text, {"스타벅스", "아모텍", "삼성전자", "skc", "starbucks"})
    )


def analyze_so_what(candidate: dict[str, Any]) -> dict[str, Any]:
    """Return report-only audience-interest diagnostics for a candidate."""

    text = text_blob(
        candidate.get("title"),
        candidate.get("summary"),
        candidate.get("why_interesting"),
        candidate.get("seed_type"),
        candidate.get("source"),
        " ".join(candidate.get("quality_flags") or []),
    )
    source_role = str(candidate.get("source_role_class") or "")
    seed_type = str(candidate.get("seed_type") or "")
    existing_flags = set(str(flag) for flag in candidate.get("quality_flags") or [])
    risk_flags = set(str(flag) for flag in candidate.get("risk_flags") or [])

    score = 0
    audience_bridge_signals: list[str] = []
    weakness_signals: list[str] = []
    quality_flags: list[str] = []

    if contains_any(text, MONEY_HOUSEHOLD_TERMS):
        score += 2
        _add_unique(audience_bridge_signals, "direct_money_or_household_impact")
    if contains_any(text, JOB_WORK_TERMS):
        score += 2
        _add_unique(audience_bridge_signals, "job_workplace_labor_change")
    if contains_any(text, {"선불", "충전금", "잔액", "환불", "consumer funds", "prepaid"}):
        score += 2
        _add_unique(audience_bridge_signals, "consumer_funds_or_regulation_gap")
    if contains_any(text, PUBLIC_AI_TERMS) and contains_any(
        text, {"공공", "공무원", "행정", "치안", "현장", "병원", "노사", "workplace"}
    ):
        score += 2
        _add_unique(audience_bridge_signals, "ai_entering_real_operations")
    if contains_any(text, STRUCTURAL_TERMS):
        score += 1
        _add_unique(audience_bridge_signals, "distinctive_mechanism")
    if contains_any(text, {"토큰화", "tokenization", "rwa"}) and contains_any(
        text,
        OWNERSHIP_REGULATION_TERMS | {"제도", "규제", "소비자", "투자자", "권리"},
    ):
        score += 1
        _add_unique(audience_bridge_signals, "ownership_or_regulatory_conflict")
    if contains_any(text, CONSEQUENCE_TERMS):
        _add_unique(audience_bridge_signals, "consequence_or_second_order_effect")
    if contains_any(text, EVERYDAY_ANALOGY_TERMS):
        score += 1
        _add_unique(audience_bridge_signals, "everyday_analogy_or_life_hook")
    if "한국" in text or source_role in {"research_note", "policy_release", "public_wire"}:
        score += 1
        _add_unique(audience_bridge_signals, "korea_bridge")
    if source_role == "research_note" and audience_bridge_signals:
        score += 1
        _add_unique(audience_bridge_signals, "research_note_structural_depth")
    if contains_any(text, WEIRD_BUT_EXPANDABLE_TERMS):
        score += 1
        _add_unique(audience_bridge_signals, "weird_hook_needs_structural_expansion")

    if contains_any(text, CONTEST_CAMPAIGN_TERMS):
        _add_unique(quality_flags, "contest_or_campaign_bulletin")
        _add_unique(weakness_signals, "official_contest_or_campaign_bulletin")
    if contains_any(text, EVENT_DEMO_TERMS) and not contains_any(
        text, {"가격", "비용", "물가", "피해", "규제", "노동", "ai", "인공지능"}
    ):
        _add_unique(quality_flags, "event_or_demonstration_only")
        _add_unique(weakness_signals, "event_or_demonstration_only")
    if contains_any(text, MEETING_COORDINATION_TERMS) and source_role == "policy_release":
        _add_unique(quality_flags, "meeting_or_coordination_only")
        _add_unique(weakness_signals, "official_meeting_or_coordination_only")
    if contains_any(text, PRODUCT_PROMO_TERMS):
        _add_unique(quality_flags, "product_or_certification_promo")
        _add_unique(weakness_signals, "product_or_certification_promo")
    if contains_any(text, NARROW_MARKET_TERMS):
        _add_unique(quality_flags, "narrow_market_track_record")
        _add_unique(weakness_signals, "narrow_market_track_record")
    if "single_company_frame" in existing_flags or "corporate_promo_risk" in risk_flags:
        _add_unique(quality_flags, "single_company_case_needs_bundle")
        _add_unique(weakness_signals, "single_company_case_needs_bundle")
    elif _company_like_text(text) and contains_any(
        text, {"환불", "충전금", "유상증자", "shares", "founder", "brand"}
    ):
        _add_unique(quality_flags, "single_company_case_needs_bundle")
        _add_unique(weakness_signals, "single_company_case_needs_bundle")
    if contains_any(text, ONE_OFF_TERMS):
        _add_unique(weakness_signals, "one_off_article")
    if contains_any(text, TEXTBOOK_TERMS):
        _add_unique(weakness_signals, "textbook_explainer_only")

    concrete_bridge = bool(
        CONCRETE_AUDIENCE_BRIDGE_SIGNALS.intersection(audience_bridge_signals)
    )
    mechanism_or_consequence = bool(MECHANISM_SIGNALS.intersection(audience_bridge_signals))
    strong_system_issue = (
        "consumer_funds_or_regulation_gap" in audience_bridge_signals
        or (
            contains_any(text, {"제도", "규제", "사각지대", "구조"})
            and contains_any(text, {"소비자", "청년", "노동", "환불", "충전금", "비용", "가격"})
        )
    )
    if not concrete_bridge or (
        not mechanism_or_consequence
        and not strong_system_issue
        and source_role != "research_note"
    ):
        _add_unique(quality_flags, "weak_audience_bridge")
        _add_unique(weakness_signals, "weak_audience_bridge")

    if PROMO_BULLETIN_FLAGS.intersection(quality_flags) and not strong_system_issue:
        score = min(score, 1)
        _add_unique(weakness_signals, "promo_or_bulletin_cap")

    score = max(0, min(5, score - min(2, len(weakness_signals) // 2)))
    if score >= 4 and concrete_bridge and (mechanism_or_consequence or strong_system_issue):
        label = "strong"
    elif score >= 2 and concrete_bridge and (mechanism_or_consequence or strong_system_issue):
        label = "conditional"
    else:
        label = "weak"

    classification = _seed_quality_classification(
        label=label,
        seed_type=seed_type,
        source_role=source_role,
        quality_flags=set(quality_flags) | existing_flags,
        audience_bridge_signals=audience_bridge_signals,
        weakness_signals=weakness_signals,
        text=text,
    )
    story_role = _story_role_from_seed_quality(
        classification["label"],
        source_role=source_role,
        seed_type=seed_type,
        quality_flags=set(quality_flags) | existing_flags,
        weakness_signals=weakness_signals,
    )
    gap = _so_what_gap(
        label=label,
        quality_flags=set(quality_flags) | existing_flags,
        audience_bridge_signals=audience_bridge_signals,
        weakness_signals=weakness_signals,
    )

    return {
        "so_what_score": score,
        "so_what_label": label,
        "so_what_gap": gap,
        "so_what_reasons": [
            *audience_bridge_signals[:4],
            *[f"weakness:{signal}" for signal in weakness_signals[:4]],
        ],
        "audience_bridge_signals": audience_bridge_signals,
        "weakness_signals": weakness_signals,
        "quality_flags": quality_flags,
        "seed_quality_classification": classification["label"],
        "seed_quality_reasons": classification["reasons"],
        "story_role": story_role["label"],
        "story_role_reasons": story_role["reasons"],
    }


def _so_what_gap(
    *,
    label: str,
    quality_flags: set[str],
    audience_bridge_signals: list[str],
    weakness_signals: list[str],
) -> str:
    if PROMO_BULLETIN_FLAGS.intersection(quality_flags):
        return "promo_or_bulletin_needs_stronger_system_issue"
    if "weak_audience_bridge" in weakness_signals:
        return "needs_concrete_audience_bridge_plus_mechanism"
    if "single_company_case_needs_bundle" in quality_flags:
        return "single_company_case_needs_bundle_or_system_evidence"
    if label == "conditional":
        return "conditional_seed_needs_second_source_or_story_bundle"
    if label == "strong":
        return "clear_audience_bridge_and_mechanism"
    if not audience_bridge_signals:
        return "no_clear_audience_bridge"
    return "manual_editorial_review_needed"


def _seed_quality_classification(
    *,
    label: str,
    seed_type: str,
    source_role: str,
    quality_flags: set[str],
    audience_bridge_signals: list[str],
    weakness_signals: list[str],
    text: str,
) -> dict[str, Any]:
    if source_role == "research_note" and label in {"strong", "conditional"}:
        if not STANDALONE_RESEARCH_NOTE_SIGNALS.intersection(audience_bridge_signals):
            return {
                "label": "conditional_seed",
                "reasons": [
                    "research_note_needs_current_news_hook",
                    "mechanism_or_policy_note_without_direct_audience_bridge",
                ],
            }
        return {
            "label": "standalone_seed",
            "reasons": ["research_note_with_structural_or_audience_signal"],
        }
    if (
        "contest_or_campaign_bulletin" in quality_flags
        or "event_or_demonstration_only" in quality_flags
    ):
        return {"label": "reject_or_downrank", "reasons": ["bulletin_or_event_only"]}
    if "narrow_market_track_record" in quality_flags:
        return {"label": "evidence_only", "reasons": ["market_story_context_only"]}
    if "product_or_certification_promo" in quality_flags:
        return {
            "label": "evidence_only",
            "reasons": ["product_or_certification_needs_larger_industry_story"],
        }
    if "meeting_or_coordination_only" in quality_flags:
        return {
            "label": "evidence_only",
            "reasons": ["meeting_or_coordination_evidence_default"],
        }
    if "consumer_funds_or_regulation_gap" in audience_bridge_signals:
        return {
            "label": "conditional_seed",
            "reasons": ["system_issue_bundle_needed", "single_company_case_needs_context"],
        }
    if "single_company_case_needs_bundle" in quality_flags and not contains_any(
        text,
        {"규제", "사각지대", "환불", "소비자", "제도", "노동", "가격", "비용"},
    ):
        return {
            "label": "evidence_only",
            "reasons": ["single_company_case_without_clear_system_issue"],
        }
    if seed_type in {"platform_labor_market", "public_ai_governance", "public_ai_enforcement"}:
        return {"label": "bundle_needed", "reasons": ["public_wire_needs_second_source"]}
    if "life_change" == seed_type or contains_any(text, {"반바지", "폭염", "쿨비즈"}):
        return {
            "label": "bundle_needed",
            "reasons": ["life_hook_needs_climate_workplace_or_power_bundle"],
        }
    if source_role == "policy_release":
        return {"label": "evidence_only", "reasons": ["policy_release_evidence_default"]}
    if label == "strong":
        return {"label": "standalone_seed", "reasons": ["strong_audience_bridge"]}
    if label == "conditional":
        return {"label": "conditional_seed", "reasons": ["conditional_audience_bridge"]}
    return {"label": "reject_or_downrank", "reasons": weakness_signals or ["weak_audience_bridge"]}


def _story_role_from_seed_quality(
    classification: str,
    *,
    source_role: str,
    seed_type: str,
    quality_flags: set[str],
    weakness_signals: list[str],
) -> dict[str, Any]:
    if classification == "standalone_seed":
        return {"label": "standalone_seed", "reasons": ["seed_quality_standalone"]}
    if classification in {"conditional_seed", "bundle_needed"}:
        reasons = ["seed_needs_supporting_links_or_frame"]
        if source_role == "research_note":
            reasons.append("research_note_needs_news_hook_before_board")
        if source_role == "public_wire":
            reasons.append("public_wire_needs_second_source")
        return {"label": "seed_with_supporting_links", "reasons": reasons}
    if classification == "evidence_only":
        if "narrow_market_track_record" in quality_flags or seed_type in {
            "single_company_financing",
            "market_rate_stress",
        }:
            return {
                "label": "background_reference",
                "reasons": ["market_or_single_company_context_only"],
            }
        return {
            "label": "evidence_for_larger_story",
            "reasons": ["seed_quality_evidence_only"],
        }
    return {
        "label": "demote_or_reject",
        "reasons": weakness_signals or ["seed_quality_reject_or_downrank"],
    }
