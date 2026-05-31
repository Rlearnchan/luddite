"""Deterministic selection lessons for Jibi review-board calibration."""

from __future__ import annotations

import json
import re
from collections import Counter
from dataclasses import dataclass
from pathlib import Path
from typing import Any

CALIBRATION_EDITORIAL_ROLES = {
    "main_seed",
    "sub_block",
    "hook_only",
    "evidence",
    "suppress",
}

SUPPORT_REQUIREMENTS = {
    "parallel_case",
    "korea_bridge",
    "policy_or_stat",
    "past_video_new_angle",
}

SPORTS_PRIMARY_TERMS = {
    "스포츠",
    "축구",
    "야구",
    "농구",
    "fifa",
    "월드컵",
    "올림픽",
    "챔피언스리그",
    "epl",
    "football",
    "formula 1",
    "formula one",
    "f1",
    "포뮬러",
    "모터스포츠",
}
SPORTS_BUSINESS_TERMS = {
    "가격",
    "가격차별",
    "티켓",
    "티켓값",
    "중계권",
    "광고",
    "스폰서",
    "이벤트 비즈니스",
    "관광",
    "도시 경제",
}
AI_GRAND_DISCOURSE_TERMS = {
    "ai 저작권",
    "저작권 논쟁",
    "허위 정보",
    "허위정보",
    "거대 담론",
    "거대담론",
}
CASUAL_AI_USE_CASE_TERMS = {
    "ai 역사",
    "역사 브이로그",
    "여행 브이로그",
    "방구석 여행",
    "time-travellers",
    "vlogging from history",
    "편하게 즐",
    "ai 영상",
}
VOICE_STALENESS_TERMS = {
    "내 목소리도 재산",
    "목소리도 재산",
    "taylor swift",
    "테일러 스위프트",
    "음성권",
    "voice clone",
    "voice cloning",
    "목소리 복제",
}
FOREIGN_COMPANY_IR_TERMS = {
    "b&q",
    "kingfisher",
    "해외 기업 실적",
    "foreign company",
    "weather-sales",
    "날씨-매출",
    "날씨 매출",
}
STALE_ESG_TERMS = {"esg", "기후 프레임", "친환경 매출", "날씨 효과"}
DAILY_PRICE_LOW_NOVELTY_TERMS = {
    "계란값",
    "계란 값",
    "egg price",
    "egg prices",
    "달걀값",
    "달걀 값",
}
DELIVERY_ROBOT_TERMS = {"배달로봇", "배달 로봇", "delivery robot"}
REAL_ESTATE_ASYMMETRY_TERMS = {
    "미끼매물",
    "부동산 허위매물",
    "허위 매물",
    "false listing",
}
SPACE_INSURANCE_TERMS = {
    "우주보험",
    "우주 보험",
    "space insurance",
    "위성 보험",
}
ADVOCACY_MORAL_TERMS = {
    "동물권",
    "동물 복지 폭로",
    "폭로성",
    "도덕 고발",
    "moral journalism",
    "advocacy",
}
BATTERY_COW_TERMS = {"배터리 소", "battery cow", "battery cows"}
FERRARI_EV_TERMS = {"페라리 ev", "ferrari ev", "페라리 전기차"}
PLATFORM_HIDDEN_COST_TERMS = {
    "무료배달",
    "무료 배달",
    "배달비",
    "수수료",
    "숨은 비용",
    "hidden cost",
    "플랫폼 비용",
}
PAST_SYUKA_OVERLAP_TERMS = {
    "과거 슈카",
    "과거 영상",
    "이미 다룬",
    "이미 했던",
    "겹침",
}
LOW_PERFORMANCE_TERMS = {"조회수 폭망", "조회수 낮", "성과 낮", "low performance"}
KOREA_BRIDGE_TERMS = {"한국", "국내", "우리나라", "korea", "korean"}

QUERY_TYPE_REQUIREMENT_MAP = {
    "parallel_case": "parallel_case",
    "similar_case": "parallel_case",
    "case": "parallel_case",
    "korea_bridge": "korea_bridge",
    "korean_context": "korea_bridge",
    "local_context": "korea_bridge",
    "policy_or_stat": "policy_or_stat",
    "policy": "policy_or_stat",
    "stat": "policy_or_stat",
    "statistics": "policy_or_stat",
    "survey": "policy_or_stat",
    "broader_system": "policy_or_stat",
    "past_video_new_angle": "past_video_new_angle",
    "new_angle": "past_video_new_angle",
    "past_overlap": "past_video_new_angle",
}

SUPPORT_REQUIREMENT_LABELS = {
    "parallel_case": "두 번째 사례",
    "korea_bridge": "한국 연결",
    "policy_or_stat": "정책/통계/여론조사",
    "past_video_new_angle": "과거 영상과 다른 새 각도",
}


@dataclass(frozen=True)
class SelectionLesson:
    key: str
    score_delta: float = 0.0
    role_hint: str = ""
    support_requirements: tuple[str, ...] = ()
    critical_support_requirements: tuple[str, ...] = ()
    why_not_main_seed: str = ""
    trigger_reasons: tuple[str, ...] = ()


SELECTION_LESSON_DEFINITIONS = {
    lesson.key: lesson
    for lesson in [
        SelectionLesson(
            key="sports_primary_downrank",
            score_delta=-60,
            role_hint="suppress",
            why_not_main_seed="sports-only topics are weak SyukaWorld primary seeds",
            trigger_reasons=("sports topic is the main substance",),
        ),
        SelectionLesson(
            key="sports_business_hook_only",
            score_delta=-45,
            role_hint="hook_only",
            why_not_main_seed="sports business angle can open a broader non-sports story",
            trigger_reasons=("tickets, pricing, media rights, or sponsorship hook",),
        ),
        SelectionLesson(
            key="ai_grand_discourse_downrank",
            score_delta=-18,
            why_not_main_seed="avoid broad AI copyright or misinformation discourse",
            trigger_reasons=("AI copyright, misinformation, or grand-discourse frame",),
        ),
        SelectionLesson(
            key="casual_ai_use_case_bonus",
            score_delta=8,
            role_hint="sub_block",
            why_not_main_seed="needs more parallel casual-use examples before standing alone",
            trigger_reasons=("casual AI use case instead of grand discourse",),
        ),
        SelectionLesson(
            key="needs_parallel_examples",
            role_hint="sub_block",
            support_requirements=("parallel_case",),
            why_not_main_seed="needs one or more parallel examples before standing alone",
            trigger_reasons=("single example needs a comparison set",),
        ),
        SelectionLesson(
            key="needs_second_source",
            role_hint="sub_block",
            support_requirements=("policy_or_stat",),
            critical_support_requirements=("policy_or_stat",),
            why_not_main_seed="needs a second source before main_seed promotion",
            trigger_reasons=("single source lacks enough structure for main seed",),
        ),
        SelectionLesson(
            key="stale_single_case_risk",
            score_delta=-15,
            role_hint="sub_block",
            support_requirements=("parallel_case",),
            critical_support_requirements=("parallel_case",),
            why_not_main_seed="single famous-person hook needs a fresher parallel case",
            trigger_reasons=("older celebrity or single-case hook",),
        ),
        SelectionLesson(
            key="needs_fresher_parallel_case",
            role_hint="sub_block",
            support_requirements=("parallel_case",),
            critical_support_requirements=("parallel_case",),
            why_not_main_seed="needs a fresher parallel case",
            trigger_reasons=("staleness risk without current parallel case",),
        ),
        SelectionLesson(
            key="foreign_company_ir_without_korea_bridge",
            score_delta=-35,
            role_hint="suppress",
            support_requirements=("korea_bridge",),
            critical_support_requirements=("korea_bridge",),
            why_not_main_seed="foreign company performance item needs Korea or audience bridge",
            trigger_reasons=("foreign company IR or performance-only frame",),
        ),
        SelectionLesson(
            key="stale_ESG_style_frame",
            score_delta=-10,
            role_hint="suppress",
            trigger_reasons=("stale ESG/weather-sales style frame",),
        ),
        SelectionLesson(
            key="past_syuka_overlap_needs_new_angle",
            score_delta=-30,
            role_hint="sub_block",
            support_requirements=("past_video_new_angle",),
            critical_support_requirements=("past_video_new_angle",),
            why_not_main_seed="past Syuka overlap means main seed needs a new angle",
            trigger_reasons=("past Syuka duplicate or overlap signal",),
        ),
        SelectionLesson(
            key="past_syuka_low_performance_risk",
            score_delta=-10,
            role_hint="sub_block",
            support_requirements=("past_video_new_angle",),
            critical_support_requirements=("past_video_new_angle",),
            why_not_main_seed="past low-performance coverage is a risk, not a positive prior",
            trigger_reasons=("past video performance risk",),
        ),
        SelectionLesson(
            key="syuka_similarity_false_positive_risk",
            score_delta=-4,
            role_hint="sub_block",
            why_not_main_seed="past-video match appears broad and needs human duplicate check",
            trigger_reasons=("shared broad keyword without concrete entity or mechanism",),
        ),
        SelectionLesson(
            key="low_novelty_daily_price",
            score_delta=-25,
            role_hint="suppress",
            why_not_main_seed="daily price topic has low novelty without a new angle",
            trigger_reasons=("familiar daily price move",),
        ),
        SelectionLesson(
            key="advocacy_or_moral_journalism_downrank",
            score_delta=-45,
            role_hint="suppress",
            why_not_main_seed=(
                "moral/advocacy frame lacks mechanism, money, institution, or daily scene"
            ),
            trigger_reasons=("advocacy or moral journalism frame",),
        ),
        SelectionLesson(
            key="title_hook_content_thin_downrank",
            score_delta=-15,
            role_hint="suppress",
            why_not_main_seed="title hook is stronger than the underlying mechanism",
            trigger_reasons=("thin content under a strong title hook",),
        ),
        SelectionLesson(
            key="daily_life_problem_bonus",
            score_delta=7,
            role_hint="sub_block",
            trigger_reasons=("daily-life problem with audience bridge",),
        ),
        SelectionLesson(
            key="platform_hidden_cost_bonus",
            score_delta=5,
            role_hint="sub_block",
            support_requirements=("policy_or_stat",),
            trigger_reasons=("platform hidden-cost mechanism",),
        ),
        SelectionLesson(
            key="fresh_industry_mechanism",
            score_delta=6,
            role_hint="sub_block",
            support_requirements=("parallel_case", "policy_or_stat"),
            critical_support_requirements=("parallel_case",),
            trigger_reasons=("fresh industry mechanism",),
        ),
        SelectionLesson(
            key="platform_information_asymmetry",
            score_delta=5,
            role_hint="sub_block",
            support_requirements=("policy_or_stat", "parallel_case"),
            critical_support_requirements=("policy_or_stat",),
            trigger_reasons=("platform information asymmetry",),
        ),
        SelectionLesson(
            key="known_brand_hook",
            score_delta=4,
            role_hint="sub_block",
            support_requirements=("parallel_case",),
            trigger_reasons=("known brand hook",),
        ),
        SelectionLesson(
            key="needs_story_expansion",
            role_hint="sub_block",
            support_requirements=("parallel_case",),
            why_not_main_seed="brand hook needs expansion beyond one model or announcement",
            trigger_reasons=("brand hook is not yet a story mechanism",),
        ),
    ]
}

SELECTION_LESSONS = set(SELECTION_LESSON_DEFINITIONS)

LESSON_SCORE_FAMILIES = {
    "sports_primary_downrank": "sports",
    "sports_business_hook_only": "sports",
}


def _dedupe(values: list[Any] | set[Any]) -> list[str]:
    return list(dict.fromkeys(str(value) for value in values if str(value).strip()))


def _text(record: dict[str, Any], representative: dict[str, Any]) -> str:
    pieces = [
        record.get("bundle_title"),
        record.get("primary_title"),
        record.get("why_bundle"),
        representative.get("title"),
        representative.get("summary"),
        representative.get("why_interesting"),
        representative.get("source"),
        representative.get("source_id"),
        representative.get("seed_type"),
        " ".join(str(item) for item in representative.get("possible_expansions", [])),
        " ".join(str(item) for item in representative.get("evidence_needed", [])),
    ]
    return " ".join(str(piece or "") for piece in pieces).lower()


def _has_any(text: str, terms: set[str]) -> bool:
    return any(term.lower() in text for term in terms)


def _accepted_query_types(second_search: dict[str, Any] | None) -> set[str]:
    query_types: set[str] = set()
    for link in (second_search or {}).get("accepted_links") or []:
        if isinstance(link, dict):
            query_type = str(link.get("query_type") or "").strip()
            if query_type:
                query_types.add(query_type)
    return query_types


def _fulfilled_support_requirements(
    requirements: list[str],
    *,
    second_search: dict[str, Any] | None,
    text: str,
) -> list[str]:
    query_types = _accepted_query_types(second_search)
    fulfilled = {
        requirement
        for query_type in query_types
        for requirement in [QUERY_TYPE_REQUIREMENT_MAP.get(query_type)]
        if requirement
    }
    accepted_count = len((second_search or {}).get("accepted_links") or [])
    if accepted_count >= 2:
        fulfilled.update({"parallel_case", "policy_or_stat"}.intersection(requirements))
    if "korea_bridge" in requirements and _has_any(text, KOREA_BRIDGE_TERMS):
        fulfilled.add("korea_bridge")
    return [requirement for requirement in requirements if requirement in fulfilled]


def _support_was_checked(second_search: dict[str, Any] | None) -> bool:
    if second_search is None:
        return False
    return True


def _token_set(value: str) -> set[str]:
    return {
        token
        for token in re.split(r"[^0-9a-zA-Z가-힣]+", value.lower())
        if len(token) >= 2
    }


def _syuka_false_positive_risk(
    record: dict[str, Any],
    representative: dict[str, Any],
    syuka_similarity: dict[str, Any] | None,
) -> bool:
    if not syuka_similarity:
        return False
    recommendation = str(syuka_similarity.get("recommendation") or "")
    if recommendation == "needs_human_check":
        return True
    if recommendation not in {"duplicate", "adjacent"}:
        return False
    candidate_tokens = _token_set(
        " ".join(
            str(value or "")
            for value in [
                record.get("bundle_title"),
                representative.get("title"),
                representative.get("summary"),
            ]
        )
    )
    past_tokens = _token_set(
        " ".join(
            str(syuka_similarity.get(key) or "")
            for key in ["top_match_title", "matched_title", "reason"]
        )
    )
    shared = candidate_tokens.intersection(past_tokens)
    return len(shared) <= 1


def _add(
    *,
    lessons: list[str],
    roles: list[str],
    requirements: list[str],
    why_not_main_seed: list[str],
    score_reasons: list[str],
    lesson: str,
    role: str | None = None,
    support: list[str] | None = None,
    critical_support: list[str] | None = None,
    why_not: str | None = None,
    score_delta_override: float | None = None,
    critical_requirements: list[str] | None = None,
    why_not_main_seed_reasons: list[str] | None = None,
) -> float:
    definition = SELECTION_LESSON_DEFINITIONS.get(lesson, SelectionLesson(key=lesson))
    lessons.append(lesson)
    role_hint = role if role is not None else definition.role_hint
    if role_hint:
        roles.append(role_hint)
    support_items = support if support is not None else list(definition.support_requirements)
    if support_items:
        requirements.extend(support_items)
    critical_items = (
        critical_support
        if critical_support is not None
        else list(definition.critical_support_requirements)
    )
    if critical_items and critical_requirements is not None:
        critical_requirements.extend(critical_items)
    why_not_text = why_not if why_not is not None else definition.why_not_main_seed
    if why_not_text:
        why_not_main_seed.append(why_not_text)
    if why_not_main_seed_reasons is not None:
        why_not_main_seed_reasons.append(lesson)
    score_delta = (
        score_delta_override
        if score_delta_override is not None
        else definition.score_delta
    )
    if score_delta:
        score_reasons.append(f"{score_delta:+g} lesson_{lesson}")
    return float(score_delta)


def _family_score_delta(lessons: set[str], family: str) -> tuple[float, str]:
    candidates = [
        (lesson, SELECTION_LESSON_DEFINITIONS[lesson].score_delta)
        for lesson in lessons
        if LESSON_SCORE_FAMILIES.get(lesson) == family
        and SELECTION_LESSON_DEFINITIONS[lesson].score_delta
    ]
    if not candidates:
        return 0.0, ""
    lesson, score_delta = max(candidates, key=lambda item: item[1])
    return float(score_delta), f"{score_delta:+g} lesson_{lesson}"


def infer_selection_lessons(
    *,
    record: dict[str, Any],
    representative: dict[str, Any],
    review_context: dict[str, list[str]] | None = None,
    syuka_similarity: dict[str, Any] | None = None,
    second_search: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Infer deterministic review lessons and support needs for a candidate."""

    text = _text(record, representative)
    review_context = review_context or {}
    review_adjustments = set(review_context.get("review_adjustments") or [])
    review_roles = set(review_context.get("review_editorial_roles") or [])
    lessons: list[str] = [lesson for lesson in review_adjustments if lesson in SELECTION_LESSONS]
    roles: list[str] = [role for role in review_roles if role in CALIBRATION_EDITORIAL_ROLES]
    requirements: list[str] = []
    critical_requirements: list[str] = []
    why_not_main_seed: list[str] = []
    why_not_main_seed_reasons: list[str] = []
    score_reasons: list[str] = []
    score_delta = 0.0

    seed_type = str(representative.get("seed_type") or "").lower()
    quality_flags = set(str(flag) for flag in representative.get("quality_flags") or [])
    sports_primary = (
        seed_type == "sports"
        or "sports_only" in quality_flags
        or _has_any(text, SPORTS_PRIMARY_TERMS)
    )
    sports_business = sports_primary and _has_any(text, SPORTS_BUSINESS_TERMS)
    if sports_primary:
        _add(
            lessons=lessons,
            roles=roles,
            requirements=requirements,
            why_not_main_seed=why_not_main_seed,
            score_reasons=score_reasons,
            lesson="sports_primary_downrank",
            role="hook_only" if sports_business else "suppress",
            why_not="sports topic is weak as the primary story",
            score_delta_override=0.0,
        )
        if sports_business:
            _add(
                lessons=lessons,
                roles=roles,
                requirements=requirements,
                why_not_main_seed=why_not_main_seed,
                score_reasons=score_reasons,
                lesson="sports_business_hook_only",
                role="hook_only",
                why_not="sports business angle can open a broader non-sports story",
                score_delta_override=0.0,
            )
        family_delta, family_reason = _family_score_delta(set(lessons), "sports")
        if family_delta:
            score_delta += family_delta
            score_reasons.append(family_reason)

    ai_grand = _has_any(text, AI_GRAND_DISCOURSE_TERMS)
    casual_ai = _has_any(text, CASUAL_AI_USE_CASE_TERMS)
    if ai_grand:
        score_delta += _add(
            lessons=lessons,
            roles=roles,
            requirements=requirements,
            why_not_main_seed=why_not_main_seed,
            score_reasons=score_reasons,
            lesson="ai_grand_discourse_downrank",
            why_not="avoid broad AI copyright or misinformation discourse",
        )
    if casual_ai:
        score_delta += _add(
            lessons=lessons,
            roles=roles,
            requirements=requirements,
            why_not_main_seed=why_not_main_seed,
            score_reasons=score_reasons,
            lesson="casual_ai_use_case_bonus",
            role="sub_block",
            why_not="needs more parallel casual-use examples before standing alone",
        )
        _add(
            lessons=lessons,
            roles=roles,
            requirements=requirements,
            why_not_main_seed=why_not_main_seed,
            score_reasons=score_reasons,
            lesson="needs_parallel_examples",
            role="sub_block",
            support=["parallel_case"],
        )

    if _has_any(text, VOICE_STALENESS_TERMS):
        score_delta += _add(
            lessons=lessons,
            roles=roles,
            requirements=requirements,
            why_not_main_seed=why_not_main_seed,
            score_reasons=score_reasons,
            lesson="stale_single_case_risk",
            role="sub_block",
            support=["parallel_case"],
            why_not="single famous-person hook needs a fresher parallel case",
        )
        _add(
            lessons=lessons,
            roles=roles,
            requirements=requirements,
            why_not_main_seed=why_not_main_seed,
            score_reasons=score_reasons,
            lesson="needs_fresher_parallel_case",
            role="sub_block",
            support=["parallel_case"],
        )

    if _has_any(text, DELIVERY_ROBOT_TERMS):
        score_delta += _add(
            lessons=lessons,
            roles=roles,
            requirements=requirements,
            why_not_main_seed=why_not_main_seed,
            score_reasons=score_reasons,
            lesson="daily_life_problem_bonus",
            role="sub_block",
            support=["policy_or_stat", "korea_bridge"],
        )
        _add(
            lessons=lessons,
            roles=roles,
            requirements=requirements,
            why_not_main_seed=why_not_main_seed,
            score_reasons=score_reasons,
            lesson="needs_second_source",
            role="sub_block",
            support=["policy_or_stat", "korea_bridge"],
            why_not="delivery robot story needs policy, statistic, survey, or Korea bridge",
        )

    if _has_any(text, REAL_ESTATE_ASYMMETRY_TERMS):
        score_delta += _add(
            lessons=lessons,
            roles=roles,
            requirements=requirements,
            why_not_main_seed=why_not_main_seed,
            score_reasons=score_reasons,
            lesson="daily_life_problem_bonus",
            role="sub_block",
            support=["policy_or_stat", "parallel_case"],
        )
        score_delta += _add(
            lessons=lessons,
            roles=roles,
            requirements=requirements,
            why_not_main_seed=why_not_main_seed,
            score_reasons=score_reasons,
            lesson="platform_information_asymmetry",
            role="sub_block",
            support=["policy_or_stat", "parallel_case"],
        )
        _add(
            lessons=lessons,
            roles=roles,
            requirements=requirements,
            why_not_main_seed=why_not_main_seed,
            score_reasons=score_reasons,
            lesson="needs_second_source",
            role="sub_block",
            support=["policy_or_stat", "parallel_case"],
            why_not="single enforcement item needs one more case or statistic",
        )

    if _has_any(text, SPACE_INSURANCE_TERMS):
        score_delta += _add(
            lessons=lessons,
            roles=roles,
            requirements=requirements,
            why_not_main_seed=why_not_main_seed,
            score_reasons=score_reasons,
            lesson="fresh_industry_mechanism",
            role="sub_block",
            support=["parallel_case", "policy_or_stat"],
        )
        _add(
            lessons=lessons,
            roles=roles,
            requirements=requirements,
            why_not_main_seed=why_not_main_seed,
            score_reasons=score_reasons,
            lesson="needs_second_source",
            role="sub_block",
            support=["parallel_case", "policy_or_stat"],
            why_not="space insurance needs another case, premium data, or failure-risk source",
        )

    if _has_any(text, FOREIGN_COMPANY_IR_TERMS):
        score_delta += _add(
            lessons=lessons,
            roles=roles,
            requirements=requirements,
            why_not_main_seed=why_not_main_seed,
            score_reasons=score_reasons,
            lesson="foreign_company_ir_without_korea_bridge",
            role="suppress",
            support=["korea_bridge"],
            why_not="foreign company performance item needs Korea or audience bridge",
        )
        if _has_any(text, STALE_ESG_TERMS):
            score_delta += _add(
                lessons=lessons,
                roles=roles,
                requirements=requirements,
                why_not_main_seed=why_not_main_seed,
                score_reasons=score_reasons,
                lesson="stale_ESG_style_frame",
                role="suppress",
            )

    if _has_any(text, DAILY_PRICE_LOW_NOVELTY_TERMS):
        score_delta += _add(
            lessons=lessons,
            roles=roles,
            requirements=requirements,
            why_not_main_seed=why_not_main_seed,
            score_reasons=score_reasons,
            lesson="past_syuka_overlap_needs_new_angle",
            role="suppress",
            support=["past_video_new_angle"],
            why_not="daily price topic needs a clearly new angle versus past Syuka coverage",
        )
        score_delta += _add(
            lessons=lessons,
            roles=roles,
            requirements=requirements,
            why_not_main_seed=why_not_main_seed,
            score_reasons=score_reasons,
            lesson="low_novelty_daily_price",
            role="suppress",
        )

    syuka_recommendation = str((syuka_similarity or {}).get("recommendation") or "")
    if syuka_recommendation in {"duplicate", "adjacent"} or _has_any(
        text,
        PAST_SYUKA_OVERLAP_TERMS,
    ):
        _add(
            lessons=lessons,
            roles=roles,
            requirements=requirements,
            why_not_main_seed=why_not_main_seed,
            score_reasons=score_reasons,
            lesson="past_syuka_overlap_needs_new_angle",
            role="sub_block",
            support=["past_video_new_angle"],
            why_not="past Syuka overlap means main seed needs a new angle",
        )
    if _has_any(text, LOW_PERFORMANCE_TERMS) or str(
        (syuka_similarity or {}).get("performance_risk") or ""
    ).lower() in {"low", "high"}:
        score_delta += _add(
            lessons=lessons,
            roles=roles,
            requirements=requirements,
            why_not_main_seed=why_not_main_seed,
            score_reasons=score_reasons,
            lesson="past_syuka_low_performance_risk",
            role="sub_block",
            support=["past_video_new_angle"],
        )
    if _syuka_false_positive_risk(record, representative, syuka_similarity):
        score_delta += _add(
            lessons=lessons,
            roles=roles,
            requirements=requirements,
            why_not_main_seed=why_not_main_seed,
            score_reasons=score_reasons,
            lesson="syuka_similarity_false_positive_risk",
            role="sub_block",
            why_not="past-video match appears broad and needs human duplicate check",
        )

    if _has_any(text, ADVOCACY_MORAL_TERMS):
        score_delta += _add(
            lessons=lessons,
            roles=roles,
            requirements=requirements,
            why_not_main_seed=why_not_main_seed,
            score_reasons=score_reasons,
            lesson="advocacy_or_moral_journalism_downrank",
            role="suppress",
            why_not="moral/advocacy frame lacks mechanism, money, institution, or daily scene",
        )
    if _has_any(text, BATTERY_COW_TERMS):
        score_delta += _add(
            lessons=lessons,
            roles=roles,
            requirements=requirements,
            why_not_main_seed=why_not_main_seed,
            score_reasons=score_reasons,
            lesson="title_hook_content_thin_downrank",
            role="suppress",
            why_not="title hook is stronger than the underlying mechanism",
        )

    if _has_any(text, FERRARI_EV_TERMS):
        score_delta += _add(
            lessons=lessons,
            roles=roles,
            requirements=requirements,
            why_not_main_seed=why_not_main_seed,
            score_reasons=score_reasons,
            lesson="known_brand_hook",
            role="sub_block",
            support=["parallel_case"],
        )
        _add(
            lessons=lessons,
            roles=roles,
            requirements=requirements,
            why_not_main_seed=why_not_main_seed,
            score_reasons=score_reasons,
            lesson="needs_story_expansion",
            role="sub_block",
            support=["parallel_case"],
            why_not="brand hook needs expansion beyond one model or announcement",
        )

    if _has_any(text, PLATFORM_HIDDEN_COST_TERMS):
        score_delta += _add(
            lessons=lessons,
            roles=roles,
            requirements=requirements,
            why_not_main_seed=why_not_main_seed,
            score_reasons=score_reasons,
            lesson="platform_hidden_cost_bonus",
            role="sub_block",
            support=["policy_or_stat"],
        )

    requirements = [
        requirement for requirement in _dedupe(requirements) if requirement in SUPPORT_REQUIREMENTS
    ]
    for lesson in lessons:
        definition = SELECTION_LESSON_DEFINITIONS.get(lesson)
        if definition:
            critical_requirements.extend(definition.critical_support_requirements)
    critical_requirements = [
        requirement
        for requirement in _dedupe(critical_requirements)
        if requirement in set(requirements)
    ]
    support_requirement_details = [
        {
            "key": requirement,
            "severity": "critical"
            if requirement in set(critical_requirements)
            else "optional",
        }
        for requirement in requirements
    ]
    fulfilled = _fulfilled_support_requirements(
        requirements,
        second_search=second_search,
        text=text,
    )
    support_checked = _support_was_checked(second_search)
    missing = [
        requirement
        for requirement in critical_requirements
        if support_checked and requirement not in set(fulfilled)
    ]
    if missing:
        if "needs_second_source" not in lessons and set(missing).intersection(
            {"parallel_case", "policy_or_stat"}
        ):
            lessons.append("needs_second_source")
        roles.append("sub_block")
        score_delta -= 6
        score_reasons.append("-6 lesson_support_missing")
        why_not_main_seed.append(
            "support missing: "
            + ", ".join(SUPPORT_REQUIREMENT_LABELS.get(item, item) for item in missing)
        )
        why_not_main_seed_reasons.extend(f"support_missing:{item}" for item in missing)
    elif requirements and support_checked and (critical_requirements or fulfilled):
        score_delta += 3
        score_reasons.append("+3 lesson_support_satisfied")

    roles = _dedupe(roles)
    if "suppress" in roles:
        recommended_role = "suppress"
    elif "hook_only" in roles:
        recommended_role = "hook_only"
    elif "sub_block" in roles:
        recommended_role = "sub_block"
    elif "evidence" in roles:
        recommended_role = "evidence"
    else:
        recommended_role = ""

    return {
        "selection_lessons": sorted(set(lessons)),
        "selection_lesson_score_delta": round(score_delta, 1),
        "selection_lesson_score_reasons": _dedupe(score_reasons),
        "selection_lesson_role": recommended_role,
        "selection_lesson_role_hints": roles,
        "support_requirements": requirements,
        "critical_support_requirements": critical_requirements,
        "support_requirement_details": support_requirement_details,
        "support_fulfilled_requirements": fulfilled,
        "support_missing_requirements": missing,
        "support_status": "missing"
        if missing
        else "satisfied"
        if requirements and support_checked
        else "not_checked"
        if requirements
        else "not_required",
        "why_not_main_seed": "; ".join(_dedupe(why_not_main_seed)),
        "why_not_main_seed_reasons": _dedupe(
            [*why_not_main_seed_reasons, *[str(lesson) for lesson in lessons]]
        ),
    }


def _role_for_report(row: dict[str, Any]) -> str:
    return str(
        row.get("editorial_role")
        or row.get("selection_lesson_role")
        or row.get("calibration_role")
        or "sub_block"
    )


def _score_before(row: dict[str, Any]) -> float:
    return float(
        row.get("board_score_before_calibration")
        if row.get("board_score_before_calibration") is not None
        else row.get("total_score", 0)
    )


def _score_after(row: dict[str, Any]) -> float:
    return float(row.get("board_score") or 0)


def _pre_calibration_role(row: dict[str, Any]) -> str:
    story_role = str(row.get("story_role") or "")
    seed_quality = str(row.get("seed_quality_classification") or "")
    before_score = _score_before(row)
    if story_role == "evidence_for_larger_story" or seed_quality == "evidence_only":
        return "evidence"
    if (
        story_role == "standalone_seed"
        or seed_quality == "standalone_seed"
    ) and before_score >= 65:
        return "main_seed"
    if story_role == "seed_with_supporting_links" or seed_quality in {
        "conditional_seed",
        "bundle_needed",
    }:
        return "sub_block"
    return "sub_block"


def _report_row(row: dict[str, Any]) -> dict[str, Any]:
    before = _score_before(row)
    after = _score_after(row)
    return {
        "story_bundle_id": str(row.get("story_bundle_id") or ""),
        "title": str(row.get("title") or ""),
        "board_score_before": before,
        "board_score_after": after,
        "score_delta": round(after - before, 1),
        "editorial_role_before": _pre_calibration_role(row),
        "editorial_role_after": _role_for_report(row),
        "selection_lessons": row.get("selection_lessons", []),
        "support_requirements": row.get("support_requirements", []),
        "critical_support_requirements": row.get("critical_support_requirements", []),
        "support_requirement_details": row.get("support_requirement_details", []),
        "support_missing_requirements": row.get("support_missing_requirements", []),
        "why_not_main_seed": str(row.get("why_not_main_seed") or ""),
        "why_not_main_seed_reasons": row.get("why_not_main_seed_reasons", []),
    }


def build_selection_calibration_report(
    *,
    run_date: str,
    score_rows: list[dict[str, Any]],
    selected_ids: list[str] | set[str],
) -> dict[str, Any]:
    selected_id_set = {str(item) for item in selected_ids}
    selected_rows = [
        row for row in score_rows if str(row.get("story_bundle_id") or "") in selected_id_set
    ]
    selected_role_counts = Counter(_role_for_report(row) for row in selected_rows)
    lesson_counts = Counter(
        lesson for row in score_rows for lesson in row.get("selection_lessons", [])
    )
    selected_payload_rows = []
    for row in selected_rows:
        selected_payload_rows.append(_report_row(row))
    non_evidence_count = (
        selected_role_counts.get("main_seed", 0)
        + selected_role_counts.get("sub_block", 0)
        + selected_role_counts.get("hook_only", 0)
    )
    recommended_visible_board_size = min(
        len(selected_rows),
        max(min(6, len(selected_rows)), non_evidence_count),
    )
    before_ranked = sorted(score_rows, key=_score_before, reverse=True)
    after_ranked = sorted(score_rows, key=_score_after, reverse=True)
    before_rank_by_id = {
        str(row.get("story_bundle_id") or ""): index
        for index, row in enumerate(before_ranked, start=1)
    }
    after_rank_by_id = {
        str(row.get("story_bundle_id") or ""): index
        for index, row in enumerate(after_ranked, start=1)
    }
    dropped_by_calibration = [
        {
            **_report_row(row),
            "rank_before": before_rank_by_id.get(str(row.get("story_bundle_id") or "")),
            "rank_after": after_rank_by_id.get(str(row.get("story_bundle_id") or "")),
        }
        for row in before_ranked
        if _score_after(row) < _score_before(row)
    ][:25]
    promoted_by_calibration = [
        {
            **_report_row(row),
            "rank_before": before_rank_by_id.get(str(row.get("story_bundle_id") or "")),
            "rank_after": after_rank_by_id.get(str(row.get("story_bundle_id") or "")),
        }
        for row in after_ranked
        if _score_after(row) > _score_before(row)
    ][:25]
    role_changed_by_calibration = [
        _report_row(row)
        for row in score_rows
        if _pre_calibration_role(row) != _role_for_report(row)
    ][:25]
    return {
        "run_date": run_date,
        "selected_count": len(selected_rows),
        "recommended_visible_board_size": recommended_visible_board_size,
        "main_seed_count": selected_role_counts.get("main_seed", 0),
        "sub_block_count": selected_role_counts.get("sub_block", 0),
        "hook_only_count": selected_role_counts.get("hook_only", 0),
        "evidence_count": selected_role_counts.get("evidence", 0),
        "suppress_candidate_count": sum(
            1
            for row in score_rows
            if str(row.get("selection_lesson_role") or "") == "suppress"
            or "suppress" in set(row.get("selection_lesson_role_hints") or [])
        ),
        "needs_second_source_count": lesson_counts.get("needs_second_source", 0),
        "support_missing_count": sum(
            1 for row in score_rows if row.get("support_missing_requirements")
        ),
        "syuka_false_positive_risk_count": lesson_counts.get(
            "syuka_similarity_false_positive_risk",
            0,
        ),
        "past_overlap_needs_new_angle_count": lesson_counts.get(
            "past_syuka_overlap_needs_new_angle",
            0,
        ),
        "reviewer_lesson_counts": dict(sorted(lesson_counts.items())),
        "top_10_before_calibration": [_report_row(row) for row in before_ranked[:10]],
        "top_10_after_calibration": [_report_row(row) for row in after_ranked[:10]],
        "dropped_by_calibration": dropped_by_calibration,
        "promoted_by_calibration": promoted_by_calibration,
        "role_changed_by_calibration": role_changed_by_calibration,
        "selected": selected_payload_rows,
    }


def _table_cell(value: Any) -> str:
    return str(value or "").replace("|", "\\|").replace("\n", " ")


def selection_calibration_markdown(payload: dict[str, Any]) -> str:
    lines = [
        f"# Jibi Selection Calibration — {payload['run_date']}",
        "",
        "Report-only calibration summary. Visible Google Sheet columns are unchanged.",
        "",
        f"- selected_count: {payload['selected_count']}",
        f"- recommended_visible_board_size: {payload['recommended_visible_board_size']}",
        f"- main_seed_count: {payload['main_seed_count']}",
        f"- sub_block_count: {payload['sub_block_count']}",
        f"- hook_only_count: {payload['hook_only_count']}",
        f"- evidence_count: {payload['evidence_count']}",
        f"- suppress_candidate_count: {payload['suppress_candidate_count']}",
        f"- needs_second_source_count: {payload['needs_second_source_count']}",
        f"- support_missing_count: {payload['support_missing_count']}",
        "- syuka_false_positive_risk_count: "
        f"{payload['syuka_false_positive_risk_count']}",
        "- past_overlap_needs_new_angle_count: "
        f"{payload['past_overlap_needs_new_angle_count']}",
        "",
        "## Reviewer Lesson Counts",
        "",
    ]
    for lesson, count in payload["reviewer_lesson_counts"].items():
        lines.append(f"- {lesson}: {count}")
    if not payload["reviewer_lesson_counts"]:
        lines.append("- none: 0")
    for heading, key in [
        ("Top 10 Before Calibration", "top_10_before_calibration"),
        ("Top 10 After Calibration", "top_10_after_calibration"),
        ("Dropped By Calibration", "dropped_by_calibration"),
        ("Promoted By Calibration", "promoted_by_calibration"),
        ("Role Changed By Calibration", "role_changed_by_calibration"),
    ]:
        lines.extend(
            [
                "",
                f"## {heading}",
                "",
                (
                    "| title | before | after | delta | role before | role after | "
                    "lessons | missing support |"
                ),
                "| --- | ---: | ---: | ---: | --- | --- | --- | --- |",
            ]
        )
        for row in payload.get(key, []):
            lines.append(
                "| "
                + " | ".join(
                    [
                        _table_cell(row.get("title", "")),
                        f"{float(row.get('board_score_before') or 0):g}",
                        f"{float(row.get('board_score_after') or 0):g}",
                        f"{float(row.get('score_delta') or 0):g}",
                        _table_cell(row.get("editorial_role_before", "")),
                        _table_cell(row.get("editorial_role_after", "")),
                        _table_cell(", ".join(row.get("selection_lessons", [])) or "-"),
                        _table_cell(
                            ", ".join(row.get("support_missing_requirements", [])) or "-"
                        ),
                    ]
                )
                + " |"
            )
        if not payload.get(key):
            lines.append("| none | 0 | 0 | 0 | none | none | none | none |")
    lines.extend(
        [
            "",
            "## Selected Rows",
            "",
            (
                "| title | before | after | editorial_role | lessons | "
                "support_requirements | why_not_main_seed |"
            ),
            "| --- | ---: | ---: | --- | --- | --- | --- |",
        ]
    )
    for row in payload["selected"]:
        lines.append(
            "| "
            + " | ".join(
                [
                    _table_cell(row.get("title", "")),
                    f"{float(row.get('board_score_before') or 0):g}",
                    f"{float(row.get('board_score_after') or 0):g}",
                    _table_cell(row.get("editorial_role_after", "")),
                    _table_cell(", ".join(row.get("selection_lessons", [])) or "-"),
                    _table_cell(", ".join(row.get("support_requirements", [])) or "-"),
                    _table_cell(row.get("why_not_main_seed", "")),
                ]
            )
            + " |"
        )
    if not payload["selected"]:
        lines.append("| none | 0 | 0 | none | none | none | none |")
    return "\n".join(lines) + "\n"


def write_selection_calibration_report(
    *,
    run_date: str,
    score_rows: list[dict[str, Any]],
    selected_ids: list[str] | set[str],
    markdown_path: Path,
    json_path: Path | None = None,
) -> tuple[Path, Path]:
    payload = build_selection_calibration_report(
        run_date=run_date,
        score_rows=score_rows,
        selected_ids=selected_ids,
    )
    json_out = json_path or markdown_path.with_suffix(".json")
    markdown_path.parent.mkdir(parents=True, exist_ok=True)
    json_out.parent.mkdir(parents=True, exist_ok=True)
    markdown_path.write_text(selection_calibration_markdown(payload), encoding="utf-8")
    json_out.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    return markdown_path, json_out
