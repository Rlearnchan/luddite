"""Jibi -> Anny seed handoff contract v0."""

from __future__ import annotations

import json
from collections.abc import Callable
from pathlib import Path
from typing import Any

HANDOFF_VERSION = "jibi_anny_seed_v0"

EDITORIAL_ROLES = {"main_seed", "sub_block", "hook_only", "evidence"}
NEGATIVE_REVIEW_ADJUSTMENTS = {
    "sports_primary_downrank",
    "ai_grand_discourse_downrank",
    "past_topic_overlap_downrank",
    "needs_new_angle",
}
ROLE_CONSTRAINTS = {"hook_only", "sub_block"}


def _dedupe(values: list[Any]) -> list[str]:
    return list(dict.fromkeys(str(value) for value in values if str(value).strip()))


def _frame_role_hints(board_score: dict[str, Any]) -> set[str]:
    hints: set[str] = set()
    for frame in board_score.get("frame_options") or []:
        if isinstance(frame, dict) and str(frame.get("role_hint") or "").strip():
            hints.add(str(frame.get("role_hint")))
    return hints


def _is_syuka_duplicate(syuka_similarity: dict[str, Any] | None) -> bool:
    return str((syuka_similarity or {}).get("recommendation") or "") == "duplicate"


def normalize_editorial_role(
    *,
    record: dict[str, Any],
    representative: dict[str, Any],
    board_score: dict[str, Any] | None = None,
    selection_metadata: dict[str, Any] | None = None,
    syuka_similarity: dict[str, Any] | None = None,
) -> dict[str, str]:
    """Normalize Jibi's mixed role hints into the Anny-facing editorial role."""

    board_score = board_score or {}
    selection_metadata = selection_metadata or {}
    story_role = str(representative.get("story_role") or "")
    seed_quality = str(representative.get("seed_quality_classification") or "")
    quality_flags = set(str(flag) for flag in representative.get("quality_flags") or [])
    review_roles = set(str(item) for item in board_score.get("review_editorial_roles") or [])
    review_adjustments = set(str(item) for item in board_score.get("review_adjustments") or [])
    frame_role_hints = _frame_role_hints(board_score)
    selection_bucket = str(selection_metadata.get("selection_bucket") or "")
    bundle_type = str(record.get("bundle_type") or "")
    source_role = str(representative.get("source_role_class") or "")
    syuka_duplicate = _is_syuka_duplicate(syuka_similarity)
    angle_score = float(board_score.get("angle_shift_score") or 0)
    score = float(board_score.get("board_score") or board_score.get("total_score") or 0)
    history_statuses = set(str(item) for item in board_score.get("history_statuses") or [])
    history_risk = history_statuses.intersection(
        {"rejected_before", "promoted_before", "reviewed_before"}
    )

    if (
        story_role == "evidence_for_larger_story"
        or seed_quality == "evidence_only"
        or "policy_release_evidence_default" in quality_flags
        or bundle_type == "evidence_cluster"
        or selection_bucket == "evidence_backfill"
    ):
        return {
            "editorial_role": "evidence",
            "editorial_role_confidence": "high",
            "why_not_main_seed": "evidence_or_background_record",
        }

    if (
        "hook_only" in review_roles
        or "hook_only" in review_adjustments
        or "hook_only" in frame_role_hints
        or "sports_primary_downrank" in review_adjustments
    ):
        return {
            "editorial_role": "hook_only",
            "editorial_role_confidence": "medium",
            "why_not_main_seed": "fresh hook but weak standalone expansion",
        }

    if (
        story_role == "seed_with_supporting_links"
        or seed_quality in {"conditional_seed", "bundle_needed"}
        or "sub_block" in review_roles
        or "sub_block" in review_adjustments
        or "sub_block" in frame_role_hints
        or selection_bucket == "role_cap_backfill"
    ):
        return {
            "editorial_role": "sub_block",
            "editorial_role_confidence": "medium",
            "why_not_main_seed": "needs supporting links, tighter frame, or main-story host",
        }

    main_seed_signal = (
        (
            story_role == "standalone_seed"
            or seed_quality == "standalone_seed"
        )
        and score >= 65
        and selection_bucket == "primary_fit"
        and not history_risk
    ) or (
        angle_score >= 4
        and score >= 70
        and source_role in {"research_note", "academic_explainer"}
        and not history_risk
    )
    if main_seed_signal and not syuka_duplicate:
        return {
            "editorial_role": "main_seed",
            "editorial_role_confidence": "high" if score >= 75 else "medium",
            "why_not_main_seed": "",
        }

    if syuka_duplicate:
        return {
            "editorial_role": "sub_block",
            "editorial_role_confidence": "medium",
            "why_not_main_seed": "past Syuka similarity suggests duplicate or follow-up risk",
        }

    if history_risk:
        return {
            "editorial_role": "sub_block",
            "editorial_role_confidence": "medium",
            "why_not_main_seed": "review history suggests rejection, prior use, or overlap risk",
        }

    return {
        "editorial_role": "sub_block",
        "editorial_role_confidence": "low",
        "why_not_main_seed": "standalone evidence or angle strength is not yet clear",
    }


def required_evidence(
    *,
    representative: dict[str, Any],
    board_score: dict[str, Any],
) -> list[str]:
    frame_needs = [
        need
        for frame in board_score.get("frame_options") or []
        if isinstance(frame, dict)
        for need in frame.get("needs", [])
    ]
    candidate_needs = representative.get("evidence_needed") or []
    return _dedupe([*frame_needs, *candidate_needs])


def past_video_context(syuka_similarity: dict[str, Any] | None) -> dict[str, str]:
    if not syuka_similarity:
        return {"match_type": "none", "title": "", "reason": ""}
    recommendation = str(syuka_similarity.get("recommendation") or "")
    match_type = {
        "duplicate": "same_story",
        "adjacent": "adjacent_theme",
        "safe_new_angle": "none",
        "needs_human_check": "false_positive",
    }.get(recommendation, "none")
    title = str(syuka_similarity.get("top_match_title") or "")
    reason = str(syuka_similarity.get("reason") or syuka_similarity.get("recommendation") or "")
    return {"match_type": match_type, "title": title, "reason": reason}


def reviewer_objections(board_score: dict[str, Any]) -> list[str]:
    review_adjustments = [
        str(item) for item in board_score.get("review_adjustments") or []
    ]
    review_failure_modes = [
        str(item) for item in board_score.get("review_failure_modes") or []
    ]
    return _dedupe(
        [
            *[
                f"adjustment:{item}"
                for item in review_adjustments
                if item in NEGATIVE_REVIEW_ADJUSTMENTS
            ],
            *[f"failure:{item}" for item in review_failure_modes],
        ]
    )


def review_role_constraints(board_score: dict[str, Any]) -> list[str]:
    review_adjustments = [
        str(item) for item in board_score.get("review_adjustments") or []
    ]
    review_editorial_roles = [
        str(item) for item in board_score.get("review_editorial_roles") or []
    ]
    return _dedupe(
        [
            item
            for item in [*review_adjustments, *review_editorial_roles]
            if item in ROLE_CONSTRAINTS
        ]
    )


def handoff_item(
    *,
    run_date: str,
    record: dict[str, Any],
    representative: dict[str, Any],
    board_score: dict[str, Any],
    selection_metadata: dict[str, Any] | None,
    syuka_similarity: dict[str, Any] | None,
) -> dict[str, Any]:
    jibi_id = str(
        record.get("story_bundle_id") or representative.get("candidate_id") or ""
    )
    role_payload = normalize_editorial_role(
        record=record,
        representative=representative,
        board_score=board_score,
        selection_metadata=selection_metadata,
        syuka_similarity=syuka_similarity,
    )
    return {
        "jibi_id": f"{run_date}:{jibi_id}",
        "story_bundle_id": str(record.get("story_bundle_id") or ""),
        "story_fingerprint": str(record.get("story_fingerprint") or ""),
        "title": str(record.get("bundle_title") or representative.get("title") or ""),
        "source": str(representative.get("source") or ""),
        "url": str(representative.get("seed_url") or ""),
        "source_role": str(representative.get("source_role_class") or "unknown"),
        "total_score": board_score.get("total_score", 0),
        "board_score": board_score.get("board_score", 0),
        "board_score_reasons": board_score.get("reasons", []),
        "topic_families": board_score.get("topic_families", []),
        "primary_topic_family": str(board_score.get("primary_topic_family") or "other"),
        "editorial_role": role_payload["editorial_role"],
        "editorial_role_confidence": role_payload["editorial_role_confidence"],
        "why_not_main_seed": role_payload["why_not_main_seed"],
        "angle_options": board_score.get("frame_options", []),
        "required_evidence": required_evidence(
            representative=representative,
            board_score=board_score,
        ),
        "past_video_context": past_video_context(syuka_similarity),
        "reviewer_objections": reviewer_objections(board_score),
        "review_role_constraints": review_role_constraints(board_score),
        "review_positive_signals": board_score.get("review_positive_signals", []),
    }


def build_anny_handoff_payload(
    *,
    run_date: str,
    records: list[dict[str, Any]],
    candidate_by_id: dict[str, dict[str, Any]],
    board_score_by_id: dict[str, dict[str, Any]],
    selection_metadata_by_id: dict[str, dict[str, Any]] | None = None,
    syuka_similarity_index: dict[str, dict[str, Any]] | None = None,
    representative_for_record: Callable[
        [dict[str, Any], dict[str, dict[str, Any]]],
        dict[str, Any] | None,
    ],
    syuka_similarity_for_record: Callable[
        [dict[str, Any], dict[str, Any], dict[str, dict[str, Any]]],
        dict[str, Any] | None,
    ],
) -> dict[str, Any]:
    selection_metadata_by_id = selection_metadata_by_id or {}
    syuka_similarity_index = syuka_similarity_index or {}
    items = []
    for record in records:
        representative = representative_for_record(record, candidate_by_id) or {}
        record_id = str(record.get("story_bundle_id") or "")
        board_score = board_score_by_id.get(record_id, {})
        syuka_similarity = syuka_similarity_for_record(
            record,
            representative,
            syuka_similarity_index,
        )
        items.append(
            handoff_item(
                run_date=run_date,
                record=record,
                representative=representative,
                board_score=board_score,
                selection_metadata=selection_metadata_by_id.get(record_id, {}),
                syuka_similarity=syuka_similarity,
            )
        )
    return {
        "handoff_version": HANDOFF_VERSION,
        "run_date": run_date,
        "items": items,
    }


def write_anny_handoff_reports(
    *,
    payload: dict[str, Any],
    json_path: Path,
    md_path: Path | None = None,
) -> tuple[Path, Path | None]:
    json_path.parent.mkdir(parents=True, exist_ok=True)
    json_path.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    if md_path is None:
        return json_path, None
    md_path.parent.mkdir(parents=True, exist_ok=True)
    lines = [
        f"# Jibi -> Anny Handoff - {payload.get('run_date', '')}",
        "",
        f"- handoff_version: {payload.get('handoff_version', HANDOFF_VERSION)}",
        f"- item_count: {len(payload.get('items') or [])}",
        "",
        "| title | editorial_role | confidence | primary topic | board_score |",
        "| --- | --- | --- | --- | ---: |",
    ]
    for item in payload.get("items") or []:
        lines.append(
            "| "
            + " | ".join(
                [
                    str(item.get("title") or "").replace("|", "\\|"),
                    str(item.get("editorial_role") or ""),
                    str(item.get("editorial_role_confidence") or ""),
                    str(item.get("primary_topic_family") or ""),
                    f"{float(item.get('board_score') or 0):g}",
                ]
            )
            + " |"
        )
    if not payload.get("items"):
        lines.append("| none | none | none | none | 0 |")
    md_path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return json_path, md_path
