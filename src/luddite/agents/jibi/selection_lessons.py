"""Deterministic selection lessons for Jibi review-board calibration."""

from __future__ import annotations

import json
import re
from collections import Counter
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from luddite.agents.jibi.visible_board_quality import (
    classify_seed_readiness,
)
from luddite.agents.jibi.visible_board_quality import (
    detect_generic_visible_copy as _detect_generic_visible_copy_v2,
)
from luddite.agents.jibi.visible_board_quality import (
    recommend_quality_floor_visible_rows as _recommend_quality_floor_visible_rows_v2,
)

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
SPORTS_CONTEXT_GUARD_TERMS = {
    "anthropic",
    "pope",
    "vatican",
    "ai harms",
    "copyright",
    "workers",
    "environment",
    "저작권",
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
SYUKA_BROAD_MATCH_TERMS = {
    "ai",
    "가격",
    "price",
    "prices",
    "system",
    "도입",
    "냉방",
    "비용",
    "산업",
    "시스템",
    "시장",
    "에어컨",
    "요금",
    "전기",
    "전기요금",
    "전력",
    "정책",
    "폭염",
    "heatwave",
    "cooling",
}
SYUKA_LOW_VALUE_MATCH_TERMS = {
    "china",
    "line",
    "oil",
    "plan",
    "stop",
    "도입",
    "세종은",
    "시스템",
    "오일",
    "지금",
}
SYUKA_CONCRETE_MATCH_TERMS = {
    "cbdc",
    "rwa",
    "sto",
    "계란값",
    "달걀값",
    "근로소득",
    "디지털 화폐",
    "무료배달",
    "무료 배달",
    "배달 수수료",
    "비경제활동",
    "불완전판매",
    "쉬었음",
    "수수료",
    "자산 토큰화",
    "토큰화",
}
GENERIC_VISIBLE_COPY_PATTERNS = {
    "해외 후보",
    "한 가지 질문으로 더 좁혀볼 소재",
    "해외 ai 이슈",
    "신뢰와 책임의 변화",
    "원문 하나만으로는 아직 결론",
    "이 후보를 단독 주제로 만들려면",
    "추가 독립 출처 1개 이상",
    "생활 영향, 구조적 배경, 반대 근거가 붙어야",
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
ASCII_WORD_TERM_RE = re.compile(r"^[a-z0-9]+(?: [a-z0-9]+)*$")


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


def _primary_story_text(record: dict[str, Any], representative: dict[str, Any]) -> str:
    pieces = [
        record.get("bundle_title"),
        record.get("primary_title"),
        record.get("why_bundle"),
        representative.get("title"),
        representative.get("summary"),
    ]
    return " ".join(str(piece or "") for piece in pieces).lower()


def _has_term(text: str, term: str) -> bool:
    normalized = term.lower()
    if ASCII_WORD_TERM_RE.fullmatch(normalized):
        phrase_pattern = re.escape(normalized).replace(r"\ ", r"\s+")
        return bool(re.search(rf"(?<![0-9a-z]){phrase_pattern}(?![0-9a-z])", text))
    return normalized in text


def _has_any(text: str, terms: set[str]) -> bool:
    return any(_has_term(text, term) for term in terms)


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


def _normalise_term(value: Any) -> str:
    return re.sub(r"\s+", " ", str(value or "").strip().lower())


def _syuka_match_terms(syuka_similarity: dict[str, Any] | None) -> list[str]:
    if not syuka_similarity:
        return []
    terms = syuka_similarity.get("matched_terms")
    if not isinstance(terms, list):
        terms = syuka_similarity.get("shared_terms")
    if isinstance(terms, list):
        return _dedupe([_normalise_term(term) for term in terms])
    return []


def _candidate_syuka_text(record: dict[str, Any], representative: dict[str, Any]) -> str:
    return " ".join(
        str(value or "")
        for value in [
            record.get("bundle_title"),
            record.get("primary_title"),
            record.get("why_bundle"),
            representative.get("title"),
            representative.get("summary"),
        ]
    )


def _past_syuka_text(syuka_similarity: dict[str, Any] | None) -> str:
    return " ".join(
        str((syuka_similarity or {}).get(key) or "")
        for key in [
            "top_match_title",
            "matched_title",
            "title",
            "reason",
            "match_reason",
        ]
    )


def _is_broad_syuka_term(term: str) -> bool:
    normalised = _normalise_term(term)
    if normalised in SYUKA_LOW_VALUE_MATCH_TERMS:
        return False
    if normalised in SYUKA_BROAD_MATCH_TERMS:
        return True
    tokens = _token_set(normalised)
    return bool(tokens) and tokens.issubset(SYUKA_BROAD_MATCH_TERMS)


def _is_concrete_syuka_term(term: str) -> bool:
    normalised = _normalise_term(term)
    if not normalised or _is_broad_syuka_term(normalised):
        return False
    for concrete in SYUKA_CONCRETE_MATCH_TERMS:
        if concrete == normalised:
            return True
        if not ASCII_WORD_TERM_RE.fullmatch(concrete) and concrete in normalised:
            return True
    return False


def _is_low_value_syuka_term(term: str) -> bool:
    normalised = _normalise_term(term)
    if not normalised:
        return False
    if normalised in SYUKA_LOW_VALUE_MATCH_TERMS:
        return True
    return not _is_broad_syuka_term(normalised) and not _is_concrete_syuka_term(normalised)


def infer_syuka_lesson_match(
    record: dict[str, Any],
    representative: dict[str, Any],
    syuka_similarity: dict[str, Any] | None,
) -> dict[str, Any]:
    """Classify past-Syuka similarity before turning it into support requirements."""

    payload: dict[str, Any] = {
        "syuka_lesson_match_type": "none",
        "syuka_lesson_match_reasons": [],
        "syuka_lesson_shared_terms": [],
        "syuka_lesson_shared_terms_raw": [],
        "syuka_lesson_display_terms": [],
        "syuka_lesson_low_value_terms": [],
        "syuka_lesson_low_value_warning": False,
        "syuka_lesson_concrete_terms": [],
        "syuka_lesson_broad_terms": [],
    }
    if not syuka_similarity:
        return payload
    recommendation = str(syuka_similarity.get("recommendation") or "")
    if recommendation not in {"duplicate", "adjacent", "needs_human_check"}:
        return payload

    shared_terms = _syuka_match_terms(syuka_similarity)
    if not shared_terms:
        candidate_tokens = _token_set(_candidate_syuka_text(record, representative))
        past_tokens = _token_set(_past_syuka_text(syuka_similarity))
        shared_terms = sorted(candidate_tokens.intersection(past_tokens))
    raw_shared_terms = _dedupe(shared_terms)
    broad_terms = [term for term in raw_shared_terms if _is_broad_syuka_term(term)]
    concrete_terms = [term for term in shared_terms if _is_concrete_syuka_term(term)]
    display_terms = _dedupe([*concrete_terms, *broad_terms])
    display_set = set(display_terms)
    low_value_terms = [
        term
        for term in raw_shared_terms
        if term not in display_set and _is_low_value_syuka_term(term)
    ]
    reasons: list[str] = [f"recommendation:{recommendation}"]
    if broad_terms:
        reasons.append("shared_broad_terms:" + ",".join(broad_terms[:5]))
    if concrete_terms:
        reasons.append("shared_concrete_terms:" + ",".join(concrete_terms[:5]))
    if low_value_terms:
        reasons.append("low_value_shared_terms_hidden")

    if recommendation == "needs_human_check":
        match_type = "false_positive"
        reasons.append("needs_human_check")
    elif concrete_terms:
        match_type = "concrete_overlap"
    elif broad_terms:
        match_type = "broad_adjacent" if recommendation == "adjacent" else "false_positive"
    elif recommendation == "adjacent":
        match_type = "weak_adjacent"
        if not shared_terms:
            reasons.append("adjacent_without_shared_concrete_terms")
    else:
        match_type = "false_positive"
        if not shared_terms:
            reasons.append("duplicate_without_shared_terms")
        elif broad_terms:
            reasons.append("duplicate_only_broad_terms")

    return {
        **payload,
        "syuka_lesson_match_type": match_type,
        "syuka_lesson_match_reasons": _dedupe(reasons),
        "syuka_lesson_shared_terms": display_terms if display_terms else raw_shared_terms,
        "syuka_lesson_shared_terms_raw": raw_shared_terms,
        "syuka_lesson_display_terms": display_terms,
        "syuka_lesson_low_value_terms": _dedupe(low_value_terms),
        "syuka_lesson_low_value_warning": bool(low_value_terms and not display_terms),
        "syuka_lesson_concrete_terms": _dedupe(concrete_terms),
        "syuka_lesson_broad_terms": _dedupe(broad_terms),
    }


def _syuka_false_positive_risk(match_payload: dict[str, Any]) -> bool:
    return str(match_payload.get("syuka_lesson_match_type") or "") == "false_positive"


def detect_generic_visible_copy(row: dict[str, Any]) -> dict[str, Any]:
    return _detect_generic_visible_copy_v2(row)


def seed_candidate_flags(row: dict[str, Any]) -> dict[str, Any]:
    return classify_seed_readiness(row)


def _quality_floor_exclusion_reason(row: dict[str, Any]) -> str:
    score = float(row.get("board_score") or row.get("board_score_after") or 0)
    if score < 35:
        return "board_score<35"
    if str(row.get("selection_lesson_role") or "") == "suppress" or "suppress" in set(
        row.get("selection_lesson_role_hints") or []
    ):
        return "selection_lesson_role=suppress"
    if (
        str(row.get("editorial_role") or "") == "evidence"
        and str(row.get("editorial_role_confidence") or "") == "low"
    ):
        return "editorial_role=evidence_low"
    if row.get("generic_visible_copy_warning"):
        return "generic_visible_copy_warning"
    critical_missing = set(row.get("support_missing_requirements") or []).intersection(
        set(row.get("critical_support_requirements") or [])
    )
    if not row.get("critical_support_requirements"):
        critical_missing = set(row.get("support_missing_requirements") or [])
    if str(row.get("support_status") or "") == "missing" and critical_missing:
        return "critical_support_missing"
    return ""


def recommend_quality_floor_visible_rows(
    rows: list[dict[str, Any]],
    *,
    hard_min_visible_rows: int = 6,
    target_visible_rows: int = 8,
    max_visible_rows: int = 10,
    fixed_10: bool | None = None,
) -> dict[str, Any]:
    return _recommend_quality_floor_visible_rows_v2(
        rows,
        hard_min_visible_rows=hard_min_visible_rows,
        target_visible_rows=target_visible_rows,
        max_visible_rows=max_visible_rows,
        fixed_10=fixed_10,
    )


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
    primary_text = _primary_story_text(record, representative)
    sports_primary = (
        seed_type == "sports"
        or "sports_only" in quality_flags
        or _has_any(primary_text, SPORTS_PRIMARY_TERMS)
    )
    if sports_primary and _has_any(primary_text, SPORTS_CONTEXT_GUARD_TERMS) and not _has_any(
        primary_text,
        SPORTS_PRIMARY_TERMS - {"sports", "football"},
    ):
        sports_primary = False
    sports_business = sports_primary and _has_any(primary_text, SPORTS_BUSINESS_TERMS)
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

    syuka_match_payload = infer_syuka_lesson_match(
        record,
        representative,
        syuka_similarity,
    )
    syuka_match_type = str(syuka_match_payload.get("syuka_lesson_match_type") or "none")
    if syuka_match_type == "concrete_overlap" or _has_any(
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
    if _syuka_false_positive_risk(syuka_match_payload):
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
        **syuka_match_payload,
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
        "support_status": str(row.get("support_status") or ""),
        "syuka_lesson_match_type": str(row.get("syuka_lesson_match_type") or "none"),
        "syuka_lesson_match_reasons": row.get("syuka_lesson_match_reasons", []),
        "syuka_lesson_shared_terms": row.get("syuka_lesson_shared_terms", []),
        "syuka_lesson_shared_terms_raw": row.get("syuka_lesson_shared_terms_raw", []),
        "syuka_lesson_display_terms": row.get("syuka_lesson_display_terms", []),
        "syuka_lesson_low_value_terms": row.get("syuka_lesson_low_value_terms", []),
        "syuka_lesson_low_value_warning": bool(
            row.get("syuka_lesson_low_value_warning")
        ),
        "syuka_lesson_concrete_terms": row.get("syuka_lesson_concrete_terms", []),
        "syuka_lesson_broad_terms": row.get("syuka_lesson_broad_terms", []),
        "generic_visible_copy_warning": bool(
            row.get("generic_visible_copy_warning")
        ),
        "generic_visible_copy_reasons": row.get("generic_visible_copy_reasons", []),
        "visible_quality_status": str(row.get("visible_quality_status") or ""),
        "visible_quality_score": row.get("visible_quality_score", 0),
        "visible_copy_specificity_score": row.get(
            "visible_copy_specificity_score",
            0,
        ),
        "visible_copy_specificity_reasons": row.get(
            "visible_copy_specificity_reasons",
            [],
        ),
        "would_hide_if_quality_floor_active": bool(
            row.get("would_hide_if_quality_floor_active")
        ),
        "quality_floor_exclusion_reason": str(
            row.get("quality_floor_exclusion_reason") or ""
        ),
        "main_seed_candidate": bool(row.get("main_seed_candidate")),
        "ready_seed_candidate": bool(row.get("ready_seed_candidate")),
        "seed_readiness_level": str(row.get("seed_readiness_level") or ""),
        "seed_readiness_reasons": row.get("seed_readiness_reasons", []),
        "seed_readiness_blockers": row.get("seed_readiness_blockers", []),
        "required_before_ready": row.get("required_before_ready", []),
        "main_seed_candidate_reasons": row.get("main_seed_candidate_reasons", []),
        "ready_seed_candidate_reasons": row.get("ready_seed_candidate_reasons", []),
        "main_seed_candidate_blockers": row.get("main_seed_candidate_blockers", []),
        "ready_seed_candidate_blockers": row.get("ready_seed_candidate_blockers", []),
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
    main_seed_candidates = [
        _report_row(row)
        for row in after_ranked
        if row.get("main_seed_candidate")
    ][:25]
    ready_seed_candidates = [
        _report_row(row)
        for row in after_ranked
        if row.get("ready_seed_candidate")
    ][:25]
    syuka_similarity_diagnostics = [
        _report_row(row)
        for row in after_ranked
        if str(row.get("syuka_lesson_match_type") or "none") != "none"
    ][:25]
    generic_visible_copy_warnings = [
        _report_row(row)
        for row in selected_rows
        if row.get("generic_visible_copy_warning")
    ][:25]
    quality_floor = recommend_quality_floor_visible_rows(selected_rows)
    return {
        "run_date": run_date,
        "selected_count": len(selected_rows),
        "recommended_visible_board_size": recommended_visible_board_size,
        "main_seed_candidate_count": sum(
            1 for row in score_rows if row.get("main_seed_candidate")
        ),
        "ready_seed_candidate_count": sum(
            1 for row in score_rows if row.get("ready_seed_candidate")
        ),
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
        "syuka_concrete_overlap_count": sum(
            1
            for row in score_rows
            if str(row.get("syuka_lesson_match_type") or "") == "concrete_overlap"
        ),
        "syuka_broad_adjacent_count": sum(
            1
            for row in score_rows
            if str(row.get("syuka_lesson_match_type") or "") == "broad_adjacent"
        ),
        "syuka_weak_adjacent_count": sum(
            1
            for row in score_rows
            if str(row.get("syuka_lesson_match_type") or "") == "weak_adjacent"
        ),
        "syuka_false_positive_count": sum(
            1
            for row in score_rows
            if str(row.get("syuka_lesson_match_type") or "") == "false_positive"
        ),
        "generic_visible_copy_warning_count": sum(
            1 for row in selected_rows if row.get("generic_visible_copy_warning")
        ),
        "past_overlap_needs_new_angle_count": lesson_counts.get(
            "past_syuka_overlap_needs_new_angle",
            0,
        ),
        **quality_floor,
        "reviewer_lesson_counts": dict(sorted(lesson_counts.items())),
        "top_10_before_calibration": [_report_row(row) for row in before_ranked[:10]],
        "top_10_after_calibration": [_report_row(row) for row in after_ranked[:10]],
        "dropped_by_calibration": dropped_by_calibration,
        "promoted_by_calibration": promoted_by_calibration,
        "role_changed_by_calibration": role_changed_by_calibration,
        "main_seed_candidates": main_seed_candidates,
        "ready_seed_candidates": ready_seed_candidates,
        "syuka_similarity_diagnostics": syuka_similarity_diagnostics,
        "generic_visible_copy_warnings": generic_visible_copy_warnings,
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
        f"- main_seed_candidate_count: {payload['main_seed_candidate_count']}",
        f"- ready_seed_candidate_count: {payload['ready_seed_candidate_count']}",
        f"- sub_block_count: {payload['sub_block_count']}",
        f"- hook_only_count: {payload['hook_only_count']}",
        f"- evidence_count: {payload['evidence_count']}",
        f"- suppress_candidate_count: {payload['suppress_candidate_count']}",
        f"- needs_second_source_count: {payload['needs_second_source_count']}",
        f"- support_missing_count: {payload['support_missing_count']}",
        "- syuka_false_positive_risk_count: "
        f"{payload['syuka_false_positive_risk_count']}",
        f"- syuka_concrete_overlap_count: {payload['syuka_concrete_overlap_count']}",
        f"- syuka_broad_adjacent_count: {payload['syuka_broad_adjacent_count']}",
        f"- syuka_weak_adjacent_count: {payload['syuka_weak_adjacent_count']}",
        f"- syuka_false_positive_count: {payload['syuka_false_positive_count']}",
        "- past_overlap_needs_new_angle_count: "
        f"{payload['past_overlap_needs_new_angle_count']}",
        "- generic_visible_copy_warning_count: "
        f"{payload['generic_visible_copy_warning_count']}",
        "- quality_floor_recommended_visible_count: "
        f"{payload['quality_floor_recommended_visible_count']}",
        "",
        "## Reviewer Lesson Counts",
        "",
    ]
    for lesson, count in payload["reviewer_lesson_counts"].items():
        lines.append(f"- {lesson}: {count}")
    if not payload["reviewer_lesson_counts"]:
        lines.append("- none: 0")
    lines.extend(
        [
            "",
            "## Main Seed Candidates",
            "",
            "| title | board_score | why candidate | remaining risk |",
            "| --- | ---: | --- | --- |",
        ]
    )
    for row in payload.get("main_seed_candidates", []):
        lines.append(
            "| "
            + " | ".join(
                [
                    _table_cell(row.get("title", "")),
                    f"{float(row.get('board_score_after') or 0):g}",
                    _table_cell(", ".join(row.get("main_seed_candidate_reasons", [])) or "-"),
                    _table_cell(", ".join(row.get("main_seed_candidate_blockers", [])) or "-"),
                ]
            )
            + " |"
        )
    if not payload.get("main_seed_candidates"):
        lines.append("| none | 0 | none | none |")
    lines.extend(
        [
            "",
            "## Syuka Similarity Diagnostics",
            "",
            "| title | match_type | shared terms | reason |",
            "| --- | --- | --- | --- |",
        ]
    )
    for row in payload.get("syuka_similarity_diagnostics", []):
        lines.append(
            "| "
            + " | ".join(
                [
                    _table_cell(row.get("title", "")),
                    _table_cell(row.get("syuka_lesson_match_type", "")),
                    _table_cell(
                        ", ".join(row.get("syuka_lesson_display_terms", []))
                        or (
                            "low-value shared terms hidden; needs human check"
                            if row.get("syuka_lesson_low_value_warning")
                            else "-"
                        )
                    ),
                    _table_cell(", ".join(row.get("syuka_lesson_match_reasons", [])) or "-"),
                ]
            )
            + " |"
        )
    if not payload.get("syuka_similarity_diagnostics"):
        lines.append("| none | none | none | none |")
    lines.extend(
        [
            "",
            "## Generic Visible Copy Warnings",
            "",
            "| title | warning reason | suggested action |",
            "| --- | --- | --- |",
        ]
    )
    for row in payload.get("generic_visible_copy_warnings", []):
        lines.append(
            "| "
            + " | ".join(
                [
                    _table_cell(row.get("title", "")),
                    _table_cell(", ".join(row.get("generic_visible_copy_reasons", []))),
                    "rewrite_visible_title_or_keep_as_evidence_backfill",
                ]
            )
            + " |"
        )
    if not payload.get("generic_visible_copy_warnings"):
        lines.append("| none | none | none |")
    lines.extend(
        [
            "",
            "## Quality Floor Exclusions",
            "",
            "| title | reason |",
            "| --- | --- |",
        ]
    )
    for row in payload.get("quality_floor_excluded_rows", []):
        lines.append(
            f"| {_table_cell(row.get('title', ''))} | {_table_cell(row.get('reason', ''))} |"
        )
    if not payload.get("quality_floor_excluded_rows"):
        lines.append("| none | none |")
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
