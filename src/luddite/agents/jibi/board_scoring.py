"""Review-board scoring helpers for Jibi selection."""

from __future__ import annotations

import re
from typing import Any

from luddite.agents.jibi.append_to_sheet import REVIEWER_COLUMNS
from luddite.agents.jibi.review_feedback import infer_review_feedback
from luddite.agents.jibi.seed_quality import analyze_so_what
from luddite.agents.jibi.story_angle import analyze_story_angle
from luddite.agents.jibi.topic_diversity import infer_topic_profile, topic_term_in_text

BoardScoreResult = dict[str, Any]

BOARD_SCORE_PROMO_FLAGS = {
    "contest_or_campaign_bulletin",
    "event_or_demonstration_only",
    "meeting_or_coordination_only",
    "product_or_certification_promo",
    "narrow_market_track_record",
    "policy_release_announcement_only",
}

BOARD_SCORE_MISMATCH_WARNING_TERMS = {
    "mismatch",
    "source mismatch",
    "cluster mismatch",
    "매칭이 흔들",
    "원문 매칭",
    "source/cluster",
}

BOARD_SCORE_TOPIC_GROUPS = {
    "delivery_fee": {"무료배달", "배달앱", "배달비", "수수료", "업주", "점주"},
    "notion_ai": {"노션", "notion", "업무자동화", "개발자 플랫폼"},
    "asset_tokenization": {"자산 토큰화", "토큰화", "rwa", "sto", "조각투자"},
}

BOARD_SCORE_MARKET_RISK_TERMS = {
    "단일종목",
    "레버리지",
    "etf",
    "ipo",
    "주주배정",
    "유상증자",
    "공모주",
    "수요예측",
    "상장",
    "주가",
}

BOARD_SCORE_PROMO_TEXT_TERMS = {
    "모집",
    "운영계획",
    "소개",
    "출시",
    "공개",
    "협력",
    "협약",
    "상생협약",
    "협약 체결",
    "업무협약",
    "mou",
    "양성",
    "인증",
    "수상",
    "신제품",
    "자문위원회",
    "포럼",
    "워크숍",
}

BOARD_SCORE_SYSTEM_TOPIC_TERMS = {
    "고용",
    "임금",
    "노동",
    "보험",
    "주거",
    "부동산",
    "공급",
    "우주산업",
    "규제",
    "사각지대",
    "물가",
    "전력",
    "교육",
    "의료",
}

BOARD_SCORE_SPORTS_PRIMARY_TERMS = {
    "스포츠",
    "축구",
    "야구",
    "농구",
    "football",
    "premier league",
    "manchester united",
    "fifa",
    "f1",
    "formula 1",
    "formula one",
    "포뮬러",
    "모터스포츠",
    "월드컵",
    "올림픽",
    "챔피언스리그",
    "epl",
}

BOARD_SCORE_SPORTS_HOOK_TERMS = {
    "가격",
    "티켓",
    "중계권",
    "광고",
    "스폰서",
    "타이틀 스폰서",
    "sponsor",
    "sponsorship",
    "title sponsor",
    "수수료",
    "이벤트",
    "관광",
    "도시",
    "경제",
}

BOARD_SCORE_AI_GRAND_DISCOURSE_TERMS = {
    "ai 저작권",
    "저작권 논쟁",
    "허위 정보",
    "허위정보",
    "거대 담론",
    "거대담론",
}

BOARD_SCORE_CASUAL_AI_TERMS = {
    "방구석 여행",
    "여행 브이로그",
    "편하게 즐",
    "ai 영상",
}

BOARD_SCORE_PRODUCT_REVIEW_TERMS = {
    "best fans",
    "tried and tested",
    "best air conditioners",
    "best air conditioning",
    "product review",
    "shopping guide",
    "buying guide",
}

BOARD_SCORE_GRADE_CUTS = {
    "A": 90,
    "B": 60,
    "C": 40,
}


def total_score(candidate: dict[str, Any]) -> float:
    return float(candidate.get("scores", {}).get("total_score", 0) or 0)


def candidate_role(candidate: dict[str, Any]) -> str:
    return str(candidate.get("source_role_class") or "unknown")


def source_text(candidate: dict[str, Any]) -> str:
    return " ".join(
        str(candidate.get(key) or "")
        for key in ("title", "summary", "source", "source_id")
    ).lower()


def candidate_so_what(candidate: dict[str, Any]) -> dict[str, Any]:
    so_what = candidate.get("so_what")
    if isinstance(so_what, dict) and so_what.get("so_what_label"):
        return so_what
    return {
        key: value
        for key, value in analyze_so_what(candidate).items()
        if key != "quality_flags"
    }


def board_score_grade(score: float) -> str:
    if score >= BOARD_SCORE_GRADE_CUTS["A"]:
        return "A"
    if score >= BOARD_SCORE_GRADE_CUTS["B"]:
        return "B"
    if score >= BOARD_SCORE_GRADE_CUTS["C"]:
        return "C"
    return "D"


def board_score_agreement_or_event_bulletin_signal(text: str) -> bool:
    lowered = text.lower()
    if bool(re.search(r"\bmou\b", lowered)):
        return True
    return any(
        term in lowered
        for term in (
            "업무협약",
            "상생협약",
            "협약 체결",
            "협약을 체결",
            "협약",
            "자문위원회",
            "포럼",
            "워크숍",
            "세미나",
        )
    )


def record_board_quality_status(
    record: dict[str, Any],
    representative: dict[str, Any],
    *,
    mismatch_reasons: list[str] | None = None,
) -> str:
    if mismatch_reasons:
        return "hard_blocked"
    title_text = source_text(representative) + " " + str(record.get("bundle_title") or "")
    if any(term in title_text for term in ("[부고]", "부친상", "모친상", "별세", "씨 별세")):
        return "hard_blocked"
    lowered_title_text = title_text.lower()
    if any(term in lowered_title_text for term in BOARD_SCORE_PRODUCT_REVIEW_TERMS):
        return "hard_blocked"
    story_role = str(representative.get("story_role") or "")
    seed_quality = str(representative.get("seed_quality_classification") or "")
    if story_role == "demote_or_reject" or seed_quality == "reject_or_downrank":
        return "hard_blocked"
    if story_role == "evidence_for_larger_story" or seed_quality == "evidence_only":
        return "evidence_backfill"
    if board_score_agreement_or_event_bulletin_signal(title_text):
        return "evidence_backfill"
    return "ok"


def hard_block_reasons(
    record: dict[str, Any],
    representative: dict[str, Any],
    mismatch_reasons: list[str],
) -> list[str]:
    reasons = list(mismatch_reasons)
    title_text = source_text(representative) + " " + str(record.get("bundle_title") or "")
    if any(term in title_text for term in ("[부고]", "부친상", "모친상", "별세", "씨 별세")):
        reasons.append("obituary_or_personnel_notice")
    lowered_title_text = title_text.lower()
    if any(term in lowered_title_text for term in BOARD_SCORE_PRODUCT_REVIEW_TERMS):
        reasons.append("product_review_or_shopping_guide")
    story_role = str(representative.get("story_role") or "")
    seed_quality = str(representative.get("seed_quality_classification") or "")
    if story_role == "demote_or_reject":
        reasons.append("story_role=demote_or_reject")
    if seed_quality == "reject_or_downrank":
        reasons.append("seed_quality=reject_or_downrank")
    return list(dict.fromkeys(reasons or ["hard_blocked"]))


def board_mismatch_reasons(
    record: dict[str, Any],
    representative: dict[str, Any],
    override: dict[str, Any] | None,
) -> list[str]:
    reasons: list[str] = []
    if not representative:
        return reasons
    override_text = " ".join(
        str((override or {}).get(key) or "")
        for key in ["title", "description", "reason"]
    ).lower()
    if any(term in override_text for term in BOARD_SCORE_MISMATCH_WARNING_TERMS):
        reasons.append("editorial_override_source_mismatch_warning")

    visible_text = " ".join(
        [
            str((override or {}).get("title") or record.get("bundle_title") or ""),
            str((override or {}).get("description") or record.get("why_bundle") or ""),
        ]
    ).lower()
    source = source_text(representative)
    for group_name, terms in BOARD_SCORE_TOPIC_GROUPS.items():
        visible_has_group = any(topic_term_in_text(term, visible_text) for term in terms)
        source_has_group = any(topic_term_in_text(term, source) for term in terms)
        if visible_has_group and not source_has_group:
            reasons.append(f"visible_primary_topic_mismatch={group_name}")
    return list(dict.fromkeys(reasons))


def _history_review_context(history_rows: list[dict[str, Any]]) -> dict[str, list[str]]:
    adjustments: list[str] = []
    roles: list[str] = []
    failure_modes: list[str] = []
    positive_signals: list[str] = []
    for row in history_rows:
        for column in REVIEWER_COLUMNS:
            note = str(row.get(column) or "").strip()
            if not note:
                continue
            payload = infer_review_feedback(note)
            adjustments.extend(str(item) for item in payload.get("review_adjustments", []))
            roles.append(str(payload.get("editorial_role") or ""))
            failure_modes.extend(str(item) for item in payload.get("failure_modes", []))
            positive_signals.extend(str(item) for item in payload.get("positive_signals", []))
    return {
        "review_adjustments": sorted({item for item in adjustments if item}),
        "review_editorial_roles": sorted({item for item in roles if item}),
        "review_failure_modes": sorted({item for item in failure_modes if item}),
        "review_positive_signals": sorted({item for item in positive_signals if item}),
    }


def _board_score_review_lesson_adjustments(
    *,
    source: str,
    seed_type: str,
    quality_flags: set[str],
    review_context: dict[str, list[str]],
) -> tuple[float, list[str], list[str], list[str]]:
    score_delta = 0.0
    reasons: list[str] = []
    adjustments = set(review_context.get("review_adjustments") or [])
    roles = set(review_context.get("review_editorial_roles") or [])
    failure_modes = set(review_context.get("review_failure_modes") or [])
    positive_signals = set(review_context.get("review_positive_signals") or [])

    sports_signal = any(
        topic_term_in_text(term, source) for term in BOARD_SCORE_SPORTS_PRIMARY_TERMS
    )
    sports_hook_signal = any(
        topic_term_in_text(term, source) for term in BOARD_SCORE_SPORTS_HOOK_TERMS
    )
    sports_primary = (
        "sports_primary_downrank" in adjustments
        or "sports_only" in quality_flags
        or seed_type == "sports"
        or sports_signal
    )
    sports_hook = sports_primary and sports_hook_signal
    if sports_primary:
        adjustments.add("sports_primary_downrank")
        if sports_hook or roles.intersection({"hook_only", "sub_block"}):
            roles.add("hook_only")
            score_delta -= 45
            reasons.append("-45 review_sports_hook_only_not_primary")
        else:
            roles.add("suppress")
            score_delta -= 60
            reasons.append("-60 review_sports_primary_downrank")

    ai_grand = "ai_grand_discourse_downrank" in adjustments or any(
        topic_term_in_text(term, source)
        for term in BOARD_SCORE_AI_GRAND_DISCOURSE_TERMS
    )
    casual_ai = "casual_ai_use_case_bonus" in adjustments or any(
        topic_term_in_text(term, source)
        for term in BOARD_SCORE_CASUAL_AI_TERMS
    )
    if ai_grand:
        adjustments.add("ai_grand_discourse_downrank")
        score_delta -= 18
        reasons.append("-18 review_ai_grand_discourse_downrank")
    if casual_ai:
        adjustments.add("casual_ai_use_case_bonus")
        roles.add("sub_block")
        score_delta += 8
        reasons.append("+8 review_casual_ai_use_case_sub_block")

    if "past_topic_overlap_downrank" in adjustments or "too_familiar" in failure_modes:
        adjustments.add("past_topic_overlap_downrank")
        score_delta -= 25
        reasons.append("-25 review_past_topic_overlap")
    if "needs_new_angle" in adjustments:
        score_delta -= 12
        reasons.append("-12 review_needs_new_angle")

    if "hook_only" in adjustments or "hook_only" in roles:
        roles.add("hook_only")
        score_delta -= 10
        reasons.append("-10 review_hook_only_not_primary")
    elif "sub_block" in adjustments or "sub_block" in roles:
        roles.add("sub_block")
        score_delta -= 6
        reasons.append("-6 review_sub_block_not_primary")

    if "specific_case_needed" in positive_signals and "sub_block" in roles:
        score_delta += 2
        reasons.append("+2 review_specific_case_sub_block")

    return (
        score_delta,
        reasons,
        sorted(adjustments),
        sorted(item for item in roles if item),
    )


def compute_board_score(
    *,
    record: dict[str, Any],
    representative: dict[str, Any],
    history_rows: list[dict[str, Any]],
    mismatch_reasons: list[str],
    syuka_similarity: dict[str, Any] | None,
    second_search: dict[str, Any] | None,
) -> BoardScoreResult:
    base_total_score = total_score(representative)
    score = base_total_score
    reasons: list[str] = [f"base_total_score={base_total_score:g}"]

    story_role = str(representative.get("story_role") or "")
    seed_quality = str(representative.get("seed_quality_classification") or "")
    seed_type = str(representative.get("seed_type") or "")
    source_role = candidate_role(representative)
    source = source_text(representative)
    so_what = candidate_so_what(representative)
    so_what_label = str(so_what.get("so_what_label") or "")
    quality_flags = set(str(flag) for flag in representative.get("quality_flags") or [])
    weakness = set(str(flag) for flag in so_what.get("weakness_signals") or [])
    review_context = _history_review_context(history_rows)
    topic_profile = infer_topic_profile(record, representative)
    story_angle = analyze_story_angle(record, representative)
    if (
        source_role == "research_note"
        and "measurement_blind_spot" in set(story_angle.get("angle_shift_reasons") or [])
        and float(story_angle.get("story_angle_score_delta") or 0) > 0
    ):
        story_angle = {
            **story_angle,
            "story_angle_score_delta": 0,
            "story_angle_score_reasons": [
                "+0 story_angle_report_only_research_note_already_scored"
            ],
        }

    if story_role == "standalone_seed" or seed_quality == "standalone_seed":
        score += 8
        reasons.append("+8 standalone_seed")
    if story_role == "seed_with_supporting_links":
        score += 5
        reasons.append("+5 seed_with_supporting_links")
    if seed_quality in {"conditional_seed", "bundle_needed"}:
        score += 3
        reasons.append("+3 conditional_or_bundle_seed")
    if so_what_label == "strong":
        score += 6
        reasons.append("+6 strong_so_what")
    elif so_what_label == "conditional":
        score += 2
        reasons.append("+2 conditional_so_what")

    if second_search:
        accepted_count = len(second_search.get("accepted_links") or [])
        query_types = {
            str(link.get("query_type") or "")
            for link in second_search.get("accepted_links") or []
            if isinstance(link, dict)
        }
        if accepted_count >= 2:
            score += 5
            reasons.append("+5 second_search_links>=2")
        if "broader_system" in query_types:
            score += 3
            reasons.append("+3 broader_system_second_search")

    syuka_recommendation = str((syuka_similarity or {}).get("recommendation") or "")
    if syuka_recommendation == "duplicate":
        score -= 25
        reasons.append("-25 syuka_duplicate")
    elif syuka_recommendation == "adjacent":
        score += 2
        reasons.append("+2 syuka_adjacent_context")

    if story_role == "evidence_for_larger_story" or seed_quality == "evidence_only":
        score -= 18
        reasons.append("-18 evidence_only")
    if story_role == "demote_or_reject" or seed_quality == "reject_or_downrank":
        score -= 60
        reasons.append("-60 demote_or_reject")
    if "weak_audience_bridge" in quality_flags or "weak_audience_bridge" in weakness:
        score -= 18
        reasons.append("-18 weak_audience_bridge")
    if quality_flags.intersection(BOARD_SCORE_PROMO_FLAGS):
        score -= 15
        reasons.append("-15 promo_or_program_bulletin")
    if any(topic_term_in_text(term, source) for term in BOARD_SCORE_MARKET_RISK_TERMS):
        score -= 22
        reasons.append("-22 market_or_security_specific_frame")
    if (
        source_role in {"public_wire", "policy_release"}
        and any(topic_term_in_text(term, source) for term in BOARD_SCORE_PROMO_TEXT_TERMS)
    ):
        score -= 15
        reasons.append("-15 promo_or_announcement_text")
    if board_score_agreement_or_event_bulletin_signal(source):
        score -= 30
        reasons.append("-30 agreement_or_event_bulletin")
    if (
        source_role == "public_wire"
        and seed_type == "other"
        and not any(
            topic_term_in_text(term, source)
            for term in BOARD_SCORE_SYSTEM_TOPIC_TERMS
        )
    ):
        score -= 8
        reasons.append("-8 public_wire_other_needs_clear_system_frame")
    if "single_company_frame" in quality_flags:
        score -= 10
        reasons.append("-10 single_company_frame")
    if mismatch_reasons:
        score -= 100
        reasons.append("-100 source_cluster_title_mismatch")

    angle_delta = float(story_angle.get("story_angle_score_delta") or 0)
    if angle_delta:
        score += angle_delta
    reasons.extend(str(reason) for reason in story_angle.get("story_angle_score_reasons", []))

    review_delta, review_reasons, review_adjustments, review_editorial_roles = (
        _board_score_review_lesson_adjustments(
            source=source,
            seed_type=seed_type,
            quality_flags=quality_flags,
            review_context=review_context,
        )
    )
    if review_delta:
        score += review_delta
    reasons.extend(review_reasons)

    history_statuses = {
        str(row.get("history_status") or "reviewed_before") for row in history_rows
    }
    if "rejected_before" in history_statuses:
        score -= 80
        reasons.append("-80 rejected_before")
    elif "promoted_before" in history_statuses:
        score -= 35
        reasons.append("-35 promoted_before")
    elif history_statuses:
        score -= 25
        reasons.append("-25 reviewed_before")

    return {
        "total_score": base_total_score,
        "board_score": round(max(0.0, score), 1),
        "reasons": reasons,
        "mismatch_reasons": mismatch_reasons,
        "history_statuses": sorted(history_statuses),
        "review_adjustments": review_adjustments,
        "review_editorial_roles": review_editorial_roles,
        "review_failure_modes": review_context.get("review_failure_modes", []),
        "review_positive_signals": review_context.get("review_positive_signals", []),
        **story_angle,
        **topic_profile,
    }


def _history_reviewers(row: dict[str, Any]) -> list[str]:
    reviewers: list[str] = []
    reviewer_payloads = row.get("reviewers")
    if isinstance(reviewer_payloads, dict):
        for reviewer, payload in reviewer_payloads.items():
            if isinstance(payload, dict) and str(payload.get("raw_note") or "").strip():
                reviewers.append(str(reviewer))
    for column in REVIEWER_COLUMNS:
        if str(row.get(column) or "").strip():
            reviewers.append(column.replace("리뷰-", ""))
    return list(dict.fromkeys(reviewers))


def board_score_report_row(
    *,
    record: dict[str, Any],
    representative: dict[str, Any],
    board_score: dict[str, Any],
    history_rows: list[dict[str, Any]],
    mismatch_reasons: list[str],
    second_search: dict[str, Any] | None,
    override: dict[str, Any] | None = None,
) -> dict[str, Any]:
    title = str(record.get("bundle_title") or record.get("primary_title") or "")
    return {
        "story_bundle_id": str(record.get("story_bundle_id") or ""),
        "story_fingerprint": str(record.get("story_fingerprint") or ""),
        "title": title,
        "visible_title": str((override or {}).get("title") or title),
        "primary_title": str(representative.get("title") or ""),
        "source": str(representative.get("source") or ""),
        "source_role": candidate_role(representative),
        "story_role": str(representative.get("story_role") or ""),
        "seed_quality_classification": str(
            representative.get("seed_quality_classification") or ""
        ),
        "total_score": board_score.get("total_score", 0),
        "board_score": board_score.get("board_score", 0),
        "board_score_before_topic_diversity": board_score.get(
            "board_score_before_topic_diversity",
            board_score.get("board_score", 0),
        ),
        "board_score_reasons": board_score.get("reasons", []),
        "generic_frame_risk": board_score.get("generic_frame_risk", "low"),
        "generic_frame_reasons": board_score.get("generic_frame_reasons", []),
        "angle_shift_score": board_score.get("angle_shift_score", 0),
        "angle_shift_reasons": board_score.get("angle_shift_reasons", []),
        "frame_options": board_score.get("frame_options", []),
        "story_angle_score_delta": board_score.get("story_angle_score_delta", 0),
        "story_angle_score_reasons": board_score.get("story_angle_score_reasons", []),
        "topic_families": board_score.get("topic_families", []),
        "primary_topic_family": board_score.get("primary_topic_family", "other"),
        "topic_confidence": board_score.get("topic_confidence", ""),
        "topic_signals": board_score.get("topic_signals", {}),
        "topic_diversity_rank_by_family": board_score.get(
            "topic_diversity_rank_by_family",
            {},
        ),
        "topic_diversity_potential_penalty": board_score.get(
            "topic_diversity_potential_penalty",
            0,
        ),
        "topic_diversity_penalty": board_score.get("topic_diversity_penalty", 0),
        "topic_diversity_reason": board_score.get("topic_diversity_reason", ""),
        "review_adjustments": board_score.get("review_adjustments", []),
        "review_editorial_roles": board_score.get("review_editorial_roles", []),
        "review_failure_modes": board_score.get("review_failure_modes", []),
        "review_positive_signals": board_score.get("review_positive_signals", []),
        "history_statuses": board_score.get("history_statuses", []),
        "reviewers": list(
            dict.fromkeys(
                reviewer for row in history_rows for reviewer in _history_reviewers(row)
            )
        ),
        "mismatch_reasons": mismatch_reasons,
        "second_search_follow_up_status": str(
            (second_search or {}).get("follow_up_status") or ""
        ),
        "second_search_accepted_links_count": len(
            (second_search or {}).get("accepted_links") or []
        ),
        "second_search_query_types": sorted(
            {
                str(link.get("query_type") or "")
                for link in (second_search or {}).get("accepted_links") or []
                if isinstance(link, dict) and str(link.get("query_type") or "").strip()
            }
        ),
    }
