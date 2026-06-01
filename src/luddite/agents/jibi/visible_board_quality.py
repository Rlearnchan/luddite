"""Final visible-row quality checks for Jibi review boards."""

from __future__ import annotations

import os
from typing import Any

GENERIC_VISIBLE_COPY_PATTERNS = {
    "해외 후보",
    "한 가지 질문으로 더 좁혀볼 소재",
    "해외 ai 이슈",
    "신뢰와 책임의 변화",
    "원문 하나만으로는 아직 결론",
    "이 후보를 단독 주제로 만들려면",
    "추가 독립 출처 1개 이상",
    "생활 영향, 구조적 배경, 반대 근거가 붙어야",
    "generic_why_without_specific_template",
}


def _dedupe(values: list[Any] | set[Any]) -> list[str]:
    return list(dict.fromkeys(str(value) for value in values if str(value).strip()))


def _as_list(value: Any) -> list[Any]:
    return value if isinstance(value, list) else []


def _score(row: dict[str, Any]) -> float:
    return float(row.get("board_score") or row.get("board_score_after") or 0)


def _critical_missing(row: dict[str, Any]) -> set[str]:
    support_missing = set(row.get("support_missing_requirements") or [])
    critical = set(row.get("critical_support_requirements") or [])
    return support_missing.intersection(critical) if critical else support_missing


def _accepted_link_count(row: dict[str, Any]) -> int:
    try:
        return int(row.get("second_search_accepted_links_count") or 0)
    except (TypeError, ValueError):
        return 0


def detect_generic_visible_copy(row: dict[str, Any]) -> dict[str, Any]:
    title = " ".join(
        str(row.get(key) or "")
        for key in ["제목", "title", "visible_title", "bundle_title"]
    ).lower()
    description = " ".join(
        str(row.get(key) or "")
        for key in ["설명", "description", "visible_description", "why_bundle", "summary"]
    ).lower()
    reasons: list[str] = []
    for pattern in GENERIC_VISIBLE_COPY_PATTERNS:
        pattern_lower = pattern.lower()
        if pattern_lower in title:
            reasons.append(f"generic_title:{pattern}")
        if pattern_lower in description:
            reasons.append(f"generic_description:{pattern}")
    return {
        "generic_visible_copy_warning": bool(reasons),
        "generic_visible_copy_reasons": _dedupe(reasons),
    }


def visible_copy_specificity(row: dict[str, Any]) -> dict[str, Any]:
    title = str(row.get("제목") or row.get("visible_title") or row.get("title") or "")
    description = str(
        row.get("설명")
        or row.get("visible_description")
        or row.get("description")
        or ""
    )
    score = 100
    reasons: list[str] = []
    if len(title.strip()) < 10:
        score -= 30
        reasons.append("short_visible_title")
    if any(pattern.lower() in title.lower() for pattern in GENERIC_VISIBLE_COPY_PATTERNS):
        score -= 50
        reasons.append("generic_visible_title")
    if not description.strip():
        score -= 20
        reasons.append("missing_visible_description")
    elif any(
        pattern.lower() in description.lower()
        for pattern in GENERIC_VISIBLE_COPY_PATTERNS
    ):
        score -= 35
        reasons.append("generic_visible_description")
    return {
        "visible_copy_specificity_score": max(0, score),
        "visible_copy_specificity_reasons": _dedupe(reasons),
    }


def classify_seed_readiness(row: dict[str, Any]) -> dict[str, Any]:
    score = _score(row)
    selection_role = str(row.get("selection_lesson_role") or "")
    support_status = str(row.get("support_status") or "")
    generic_frame_risk = str(row.get("generic_frame_risk") or "low")
    syuka_match_type = str(row.get("syuka_lesson_match_type") or "none")
    visible_title = str(row.get("visible_title") or row.get("title") or row.get("제목") or "")
    critical_missing = _critical_missing(row)
    accepted_links = _accepted_link_count(row)
    frame_options = _as_list(row.get("frame_options"))
    support_requirements = set(row.get("support_requirements") or [])
    selection_lessons = set(row.get("selection_lessons") or [])
    source_role = str(row.get("source_role") or row.get("source_role_class") or "")
    story_role = str(row.get("story_role") or "")
    seed_quality = str(row.get("seed_quality_classification") or "")
    visible_description = str(
        row.get("visible_description") or row.get("description") or row.get("설명") or ""
    )

    generic_warning = bool(row.get("generic_visible_copy_warning"))
    concrete_overlap_blocked = (
        syuka_match_type == "concrete_overlap"
        and "past_video_new_angle" not in set(row.get("support_fulfilled_requirements") or [])
    )

    main_reasons: list[str] = []
    main_blockers: list[str] = []
    if score >= 78:
        main_reasons.append("board_score>=78")
    else:
        main_blockers.append("board_score<78")
    if selection_role == "suppress":
        main_blockers.append("selection_lesson_role=suppress")
    if critical_missing:
        main_blockers.append("critical_support_missing:" + ",".join(sorted(critical_missing)))
    if generic_warning:
        main_blockers.append("generic_visible_copy_warning")
    if concrete_overlap_blocked:
        main_blockers.append("syuka_concrete_overlap_needs_new_angle")
    if syuka_match_type == "none":
        main_reasons.append("syuka_match_type=none")
    elif syuka_match_type == "false_positive":
        main_reasons.append("not_blocked_by_syuka_false_positive")
    if selection_role and selection_role != "suppress":
        main_reasons.append(f"selection_lesson_role={selection_role}")
    if not critical_missing:
        main_reasons.append("no_critical_support_missing")

    main_seed_candidate = not main_blockers
    ready_reasons: list[str] = []
    ready_blockers: list[str] = []
    required_before_ready: list[str] = []
    if score >= 82:
        ready_reasons.append("board_score>=82")
    else:
        ready_blockers.append("board_score<82")
    if critical_missing:
        ready_blockers.append("critical_support_missing:" + ",".join(sorted(critical_missing)))
    if support_status == "missing":
        ready_blockers.append("support_status=missing")
    if generic_frame_risk == "high":
        ready_blockers.append("generic_frame_risk=high")
    if generic_warning:
        ready_blockers.append("generic_visible_copy_warning")
    if syuka_match_type == "concrete_overlap":
        ready_blockers.append("syuka_match_type=concrete_overlap")
        required_before_ready.append("past_video_new_angle")
    if syuka_match_type == "weak_adjacent":
        ready_blockers.append("syuka_match_type=weak_adjacent")
        required_before_ready.append("syuka_match_human_check")
    if len(visible_title.strip()) < 6:
        ready_blockers.append("visible_title_too_thin")
    if story_role == "seed_with_supporting_links" and accepted_links == 0:
        ready_blockers.append("story_needs_supporting_links")
        required_before_ready.append("second_search_required")
    if seed_quality == "conditional_seed" and support_status in {
        "not_required",
        "not_checked",
        "",
    }:
        ready_blockers.append("conditional_seed_support_not_verified")
        required_before_ready.append("support_verification_required")
    if any(isinstance(frame, dict) and frame.get("needs") for frame in frame_options):
        if not support_requirements:
            ready_blockers.append("frame_needs_missing_support_requirements")
            required_before_ready.append("frame_needs_support_requirements")
    if visible_description == "generic_why_without_specific_template":
        ready_blockers.append("generic_visible_description_template")
        required_before_ready.append("rewrite_visible_copy")
    if source_role == "market_wire" and not selection_lessons and accepted_links == 0:
        ready_blockers.append("market_wire_without_lesson_or_second_source")
        required_before_ready.append("second_search_required")
    if visible_title.strip():
        ready_reasons.append("visible_title_present")

    ready_seed_candidate = main_seed_candidate and not ready_blockers
    if not main_seed_candidate:
        readiness_level = "not_seed"
    elif ready_seed_candidate:
        readiness_level = "ready"
    elif required_before_ready:
        readiness_level = "needs_support"
    else:
        readiness_level = "candidate"

    return {
        "main_seed_candidate": main_seed_candidate,
        "ready_seed_candidate": ready_seed_candidate,
        "seed_readiness_level": readiness_level,
        "seed_readiness_reasons": _dedupe([*main_reasons, *ready_reasons]),
        "seed_readiness_blockers": _dedupe([*main_blockers, *ready_blockers]),
        "required_before_ready": _dedupe(required_before_ready),
        "main_seed_candidate_reasons": _dedupe(main_reasons),
        "ready_seed_candidate_reasons": _dedupe(ready_reasons),
        "main_seed_candidate_blockers": _dedupe(main_blockers),
        "ready_seed_candidate_blockers": _dedupe(ready_blockers),
    }


def _quality_floor_exclusion_reason(row: dict[str, Any]) -> str:
    if row.get("quality_floor_exclusion_reason"):
        return str(row.get("quality_floor_exclusion_reason") or "")
    score = _score(row)
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
    critical_missing = _critical_missing(row)
    if str(row.get("support_status") or "") == "missing" and critical_missing:
        return "critical_support_missing"
    if critical_missing:
        return "critical_support_missing"
    if str(row.get("seed_readiness_level") or "") == "not_seed":
        return "ready_status=not_seed"
    if (
        str(row.get("syuka_lesson_match_type") or "") == "weak_adjacent"
        and row.get("generic_visible_copy_warning")
    ):
        return "weak_adjacent_only_with_generic_copy"
    return ""


def evaluate_visible_board_row(
    *,
    row: dict[str, Any],
    metadata: dict[str, Any] | None = None,
    board_score: dict[str, Any] | None = None,
) -> dict[str, Any]:
    combined = {
        **(metadata or {}),
        **(board_score or {}),
        "제목": row.get("제목", ""),
        "설명": row.get("설명", ""),
        "과거 영상": row.get("과거 영상", ""),
        "visible_title": row.get("제목") or (metadata or {}).get("title", ""),
        "visible_description": row.get("설명") or (metadata or {}).get("description", ""),
    }
    generic = detect_generic_visible_copy(combined)
    specificity = visible_copy_specificity(combined)
    readiness = classify_seed_readiness({**combined, **generic, **specificity})
    evaluation = {**generic, **specificity, **readiness}

    if str(combined.get("selection_lesson_role") or "") == "suppress":
        status = "suppress"
    elif generic["generic_visible_copy_warning"]:
        status = "generic_backfill"
    elif _score(combined) < 35:
        status = "low_quality"
    elif str(combined.get("editorial_role") or "") == "evidence":
        status = "evidence_only"
    elif readiness["ready_seed_candidate"]:
        status = "ready"
    elif readiness["main_seed_candidate"]:
        status = "needs_support" if readiness["required_before_ready"] else "candidate"
    else:
        status = "low_quality"

    evaluation["visible_quality_status"] = status
    evaluation["visible_quality_score"] = max(
        0,
        min(
            100,
            int(specificity["visible_copy_specificity_score"])
            + (20 if readiness["ready_seed_candidate"] else 0)
            - (30 if status in {"generic_backfill", "suppress", "low_quality"} else 0),
        ),
    )
    reason = _quality_floor_exclusion_reason({**combined, **evaluation})
    evaluation["would_hide_if_quality_floor_active"] = bool(reason)
    evaluation["quality_floor_exclusion_reason"] = reason
    return evaluation


def recommend_quality_floor_visible_rows(
    rows: list[dict[str, Any]],
    *,
    hard_min_visible_rows: int = 6,
    target_visible_rows: int = 8,
    max_visible_rows: int = 10,
    fixed_10: bool | None = None,
) -> dict[str, Any]:
    if fixed_10 is None:
        fixed_10 = os.environ.get("JIBI_FIXED_10_BOARD") == "1"
    excluded_rows = []
    kept_rows = []
    for row in rows:
        reason = _quality_floor_exclusion_reason(row)
        payload = {
            "story_bundle_id": str(row.get("story_bundle_id") or ""),
            "title": str(row.get("title") or row.get("visible_title") or row.get("제목") or ""),
            "reason": reason,
            "board_score": row.get("board_score", row.get("board_score_after", 0)),
            "visible_quality_status": str(row.get("visible_quality_status") or ""),
        }
        if reason:
            excluded_rows.append(payload)
        else:
            kept_rows.append(payload)
    eligible_count = max(0, len(rows) - len(excluded_rows))
    if fixed_10:
        recommended_count = min(max_visible_rows, len(rows))
    elif not rows:
        recommended_count = 0
    else:
        floor = min(hard_min_visible_rows, len(rows))
        recommended_count = min(
            max_visible_rows,
            max(floor, min(target_visible_rows, eligible_count)),
        )
    return {
        "quality_floor_fixed_10": bool(fixed_10),
        "quality_floor_recommended_visible_count": recommended_count,
        "quality_floor_excluded_count": len(excluded_rows),
        "quality_floor_excluded_rows": excluded_rows,
        "quality_floor_kept_rows": kept_rows,
        "would_hide_if_quality_floor_active_count": len(excluded_rows),
        "excluded_ids": [
            row["story_bundle_id"] for row in excluded_rows if row.get("story_bundle_id")
        ],
    }


def _quality_floor_fallback_rank(row: dict[str, Any]) -> tuple[int, float, float]:
    reason = _quality_floor_exclusion_reason(row)
    severity = {
        "selection_lesson_role=suppress": 100,
        "board_score<35": 95,
        "generic_visible_copy_warning": 90,
        "critical_support_missing": 80,
        "editorial_role=evidence_low": 70,
        "weak_adjacent_only_with_generic_copy": 65,
        "ready_status=not_seed": 60,
    }.get(reason, 50)
    return (
        severity,
        -_score(row),
        -float(row.get("visible_quality_score") or 0),
    )


def select_quality_floor_visible_rows(
    rows: list[dict[str, Any]],
    *,
    hard_min_visible_rows: int = 6,
    target_visible_rows: int = 8,
    max_visible_rows: int = 10,
    fixed_10: bool | None = None,
) -> dict[str, Any]:
    """Return the opt-in variable visible-board selection for final visible rows."""

    recommendation = recommend_quality_floor_visible_rows(
        rows,
        hard_min_visible_rows=hard_min_visible_rows,
        target_visible_rows=target_visible_rows,
        max_visible_rows=max_visible_rows,
        fixed_10=fixed_10,
    )
    if recommendation["quality_floor_fixed_10"]:
        selected_indices = list(range(min(max_visible_rows, len(rows))))
    else:
        recommended_count = int(
            recommendation["quality_floor_recommended_visible_count"] or 0
        )
        annotated = [
            {
                "index": index,
                "row": row,
                "reason": _quality_floor_exclusion_reason(row),
            }
            for index, row in enumerate(rows)
        ]
        eligible = [item for item in annotated if not item["reason"]]
        fallback = sorted(
            [item for item in annotated if item["reason"]],
            key=lambda item: _quality_floor_fallback_rank(item["row"]),
        )
        selected_items = [*eligible[:recommended_count]]
        if len(selected_items) < recommended_count:
            selected_items.extend(fallback[: recommended_count - len(selected_items)])
        selected_indices = sorted(int(item["index"]) for item in selected_items)

    selected_index_set = set(selected_indices)
    hidden_indices = [
        index for index in range(len(rows)) if index not in selected_index_set
    ]
    included_with_warnings = [
        {
            "story_bundle_id": str(row.get("story_bundle_id") or ""),
            "title": str(row.get("title") or row.get("visible_title") or row.get("제목") or ""),
            "reason": _quality_floor_exclusion_reason(row),
            "board_score": row.get("board_score", row.get("board_score_after", 0)),
        }
        for index, row in enumerate(rows)
        if index in selected_index_set and _quality_floor_exclusion_reason(row)
    ]
    hidden_rows = [
        {
            "story_bundle_id": str(row.get("story_bundle_id") or ""),
            "title": str(row.get("title") or row.get("visible_title") or row.get("제목") or ""),
            "reason": _quality_floor_exclusion_reason(row) or "above_target_visible_count",
            "board_score": row.get("board_score", row.get("board_score_after", 0)),
            "visible_quality_status": str(row.get("visible_quality_status") or ""),
        }
        for index, row in enumerate(rows)
        if index in hidden_indices
    ]
    return {
        **recommendation,
        "quality_floor_selected_indices": selected_indices,
        "quality_floor_hidden_indices": hidden_indices,
        "quality_floor_selected_count": len(selected_indices),
        "quality_floor_hidden_count": len(hidden_indices),
        "quality_floor_hidden_rows": hidden_rows,
        "quality_floor_included_with_warnings": included_with_warnings,
        "quality_floor_included_with_warnings_count": len(included_with_warnings),
    }
