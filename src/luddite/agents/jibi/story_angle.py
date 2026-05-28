"""Rule-based Story Angle / Angle Lab helpers for Jibi.

The analyzer intentionally reads source-facing candidate metadata first.  It
does not use generated copy such as ``why_interesting`` or
``possible_expansions`` as primary trigger input, because those fields can
carry the wrong frame forward from an earlier generation step.
"""

from __future__ import annotations

import re
from typing import Any

STORY_ANGLE_SCENE_TERMS = {
    "막내",
    "신입",
    "첫 직장",
    "허드렛일",
    "실수",
    "현장",
    "공무원",
    "보고서",
    "드론",
    "치안",
    "병원",
    "학교",
    "출근",
    "복장",
    "반바지",
    "에어컨",
    "냉방",
    "물놀이",
    "잔디깎이",
    "소음",
    "배달",
    "점주",
    "구독",
    "환불",
    "선불충전금",
    "쉬었음",
    "비경제활동",
    "경제활동참가율",
}

STORY_ANGLE_MECHANISM_TERMS = {
    "비용",
    "부담",
    "전가",
    "책임",
    "사각지대",
    "규제",
    "수수료",
    "보조금",
    "전력망",
    "보험",
    "소유권",
    "인허가",
    "공급망",
    "희석",
    "정산",
    "가격표",
    "노동시장 밖",
    "구직 포기",
    "참가율",
    "비경제활동",
}

STORY_ANGLE_BROAD_TOPIC_GROUPS = {
    "broad_ai_topic": {"ai", "인공지능", "자동화", "챗봇"},
    "abstract_youth_labor_question": {"청년", "고용", "일자리", "노동시장"},
    "generic_energy_price_question": {"전기요금", "에너지", "전력", "energy"},
    "abstract_policy_support_question": {"정부", "정책", "지원", "보조", "공공"},
    "generic_export_or_growth_question": {"수출", "성장", "경제활력", "투자"},
}


def _term_in_text(term: str, text: str) -> bool:
    normalized_term = term.lower().strip()
    if not normalized_term:
        return False
    if re.fullmatch(r"[a-z0-9_+-]+", normalized_term):
        return bool(
            re.search(
                rf"(?<![a-z0-9]){re.escape(normalized_term)}(?![a-z0-9])",
                text,
            )
        )
    return normalized_term in text


def _angle_text(record: dict[str, Any], representative: dict[str, Any]) -> str:
    return " ".join(
        [
            str(representative.get("title") or ""),
            str(representative.get("summary") or ""),
            str(representative.get("seed_type") or ""),
            str(representative.get("source_role_class") or ""),
            str(record.get("bundle_title") or ""),
            str(record.get("story_fingerprint") or ""),
            str(record.get("storyline_fit") or ""),
        ]
    ).lower()


def _has_any(text: str, terms: set[str]) -> bool:
    return any(_term_in_text(term, text) for term in terms)


def _add_frame(
    frames: list[dict[str, Any]],
    *,
    frame: str,
    role_hint: str,
    reasons: list[str],
    needs: list[str],
) -> None:
    if any(item.get("frame") == frame for item in frames):
        return
    frames.append(
        {
            "frame": frame,
            "role_hint": role_hint,
            "reasons": reasons,
            "needs": needs,
        }
    )


def _frame_options(text: str) -> list[dict[str, Any]]:
    frames: list[dict[str, Any]] = []
    if _has_any(text, {"ai", "인공지능", "자동화"}) and _has_any(
        text,
        {"신입", "막내", "첫 직장", "자료조사", "사무직", "교육", "경력"},
    ):
        _add_frame(
            frames,
            frame="회사 막내가 사라질 때 조직은 누구를 어떻게 키우나",
            role_hint="conditional_seed",
            reasons=["role_disappears", "training_pipeline_break"],
            needs=["신입 교육 비용", "직무별 AI 대체 사례", "기업 규모별 채용 변화"],
        )
    if _has_any(text, {"청년", "고용", "노동시장"}) and _has_any(
        text,
        {"쉬었음", "경제활동참가율", "비경제활동", "노동시장 밖", "구직 포기"},
    ):
        _add_frame(
            frames,
            frame="실업률 밖으로 빠진 청년은 통계와 정책의 사각지대가 된다",
            role_hint="conditional_seed",
            reasons=["measurement_blind_spot", "labor_market_exit_scene"],
            needs=["비경제활동인구", "경제활동참가율", "첫 직장 이탈 이후 임금 경로"],
        )
    if _has_any(text, {"ai", "인공지능"}) and _has_any(
        text,
        {"공무원", "보고서", "행정", "드론", "치안", "현장", "책임"},
    ):
        _add_frame(
            frames,
            frame="AI가 행정 판단에 들어오면 책임은 사람과 시스템 중 어디에 남나",
            role_hint="conditional_seed",
            reasons=["institutional_responsibility_shift", "public_decision_scene"],
            needs=["공공 AI 가이드라인", "오판·감사 사례", "기관별 책임 규정"],
        )
    if _has_any(
        text,
        {"ai", "인공지능", "데이터센터", "datacentre", "datacenter"},
    ) and _has_any(
        text,
        {"전력", "전기", "전기요금", "배출", "탄소", "emissions", "electricity"},
    ):
        _add_frame(
            frames,
            frame="AI 화면 뒤에는 전력망과 탄소계산서가 붙어 있다",
            role_hint="conditional_seed",
            reasons=["physical_infrastructure_shift", "hidden_energy_bill"],
            needs=["데이터센터 전력 사용량", "지역 인허가", "전기요금·배출 산정 방식"],
        )
    if _has_any(text, {"무료배달", "배달앱", "배달비"}) and _has_any(
        text,
        {"수수료", "점주", "업주", "부담", "전가", "플랫폼"},
    ):
        _add_frame(
            frames,
            frame="공짜처럼 보이는 배달비는 누구의 손익계산서로 이동하나",
            role_hint="conditional_seed",
            reasons=["hidden_cost_transfer", "platform_margin_scene"],
            needs=["수수료율", "점주 마진", "소비자 가격 전가 사례"],
        )
    if _has_any(
        text,
        {
            "전기요금",
            "에너지 가격",
            "가스값",
            "연료비",
            "전력요금",
            "energy bills",
            "electricity prices",
            "energy price",
            "ofgem",
        },
    ):
        _add_frame(
            frames,
            frame="전쟁과 연료비는 어떤 경로로 집 전기요금이 되나",
            role_hint="conditional_seed",
            reasons=["cost_translation_chain", "household_bill_scene"],
            needs=["연료비 연동 구조", "가계 전기요금", "산업용 전력 가격"],
        )
    if _has_any(text, {"구독", "월 7.99달러", "유료", "subscription"}):
        _add_frame(
            frames,
            frame="무료 기능이 월 구독으로 바뀌면 플랫폼의 돈 버는 방식도 바뀐다",
            role_hint="sub_block",
            reasons=["pricing_model_shift", "user_tier_split"],
            needs=["무료·유료 기능 차이", "경쟁 서비스 가격", "이용자 반응"],
        )
    if _has_any(text, {"개발제한구역", "그린벨트", "greenbelt"}):
        _add_frame(
            frames,
            frame="도시 전체를 위한 규제 비용을 특정 주민이 얼마나 부담하나",
            role_hint="conditional_seed",
            reasons=["policy_cost_bearer", "property_rights_scene"],
            needs=["지원 가구 수", "규제 면적", "재산권 분쟁 사례"],
        )
    if _has_any(text, {"잔디깎이", "소음", "noise"}):
        _add_frame(
            frames,
            frame="생활 불편에 가격표가 붙으면 이웃 갈등은 시장 문제가 된다",
            role_hint="hook_only",
            reasons=["externality_pricing", "neighborhood_scene"],
            needs=["소음 규제", "분쟁 사례", "비용 산정 방식"],
        )
    if _has_any(text, {"특허", "기술정보", "patent"}):
        _add_frame(
            frames,
            frame="특허를 읽는 비용이 낮아지면 중소기업도 기술 지형을 볼 수 있나",
            role_hint="sub_block",
            reasons=["expert_tool_access_shift", "search_cost_drop"],
            needs=["이용 대상", "검색 데이터 범위", "민간 특허분석 서비스 비교"],
        )
    return frames


def analyze_story_angle(
    record: dict[str, Any],
    representative: dict[str, Any],
) -> dict[str, Any]:
    """Return the report-stable Angle Lab profile for one board record."""

    text = _angle_text(record, representative)
    broad_reasons = [
        reason
        for reason, terms in STORY_ANGLE_BROAD_TOPIC_GROUPS.items()
        if _has_any(text, terms)
    ]
    has_scene = _has_any(text, STORY_ANGLE_SCENE_TERMS)
    has_mechanism = _has_any(text, STORY_ANGLE_MECHANISM_TERMS)
    has_specific_number = bool(re.search(r"\d", text)) or any(
        unit in text for unit in ("억원", "조원", "만명", "%", "달러")
    )
    frames = _frame_options(text)
    frame_reasons = sorted(
        {
            str(reason)
            for frame in frames
            for reason in frame.get("reasons", [])
            if str(reason)
        }
    )
    angle_score = min(
        5,
        len(frames) * 2
        + (1 if has_scene else 0)
        + (1 if has_mechanism else 0)
        + (1 if has_specific_number else 0),
    )

    generic_reasons = list(broad_reasons)
    if broad_reasons and not has_scene:
        generic_reasons.append("no_specific_scene")
    if broad_reasons and not has_mechanism:
        generic_reasons.append("no_mechanism_shift")
    if broad_reasons and not frames:
        generic_reasons.append("no_frame_shift")

    if broad_reasons and not frames and (not has_scene or not has_mechanism):
        generic_risk = "high"
    elif broad_reasons and angle_score <= 2:
        generic_risk = "medium"
    elif broad_reasons:
        generic_risk = "low"
    else:
        generic_risk = "low"

    penalty = 0
    penalty_reason = ""
    if generic_risk == "high":
        penalty = -30
        penalty_reason = "-30 generic_frame_high_risk"
    elif generic_risk == "medium":
        penalty = -12
        penalty_reason = "-12 generic_frame_medium_risk"
    if penalty and angle_score >= 4:
        penalty = int(round(penalty / 2))
        penalty_reason += "_softened_by_angle_shift"

    bonus = 0
    bonus_reason = ""
    if angle_score >= 4:
        bonus = 6
        bonus_reason = "+6 strong_angle_shift"
    elif angle_score >= 2:
        bonus = 2
        bonus_reason = "+2 possible_angle_shift"

    return {
        "generic_frame_risk": generic_risk,
        "generic_frame_reasons": list(dict.fromkeys(generic_reasons)),
        "angle_shift_score": angle_score,
        "angle_shift_reasons": frame_reasons,
        "frame_options": frames[:3],
        "story_angle_score_delta": penalty + bonus,
        "story_angle_score_reasons": [
            reason for reason in [penalty_reason, bonus_reason] if reason
        ],
    }
