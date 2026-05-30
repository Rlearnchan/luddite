"""Review-board record selection and backfill metadata for Jibi."""

from __future__ import annotations

from collections import Counter
from collections.abc import Callable
from typing import Any

from luddite.agents.jibi.board_scoring import (
    board_mismatch_reasons,
    board_score_report_row,
    compute_board_score,
    hard_block_reasons,
    record_board_quality_status,
    total_score,
)
from luddite.agents.jibi.topic_diversity import apply_topic_diversity_adjustments

DEFAULT_SOURCE_ROLE_TOP_CAPS = {
    "research_note": 3,
    "policy_release": 2,
    "public_wire": 3,
    "academic_explainer": 2,
    "market_wire": 1,
    "section_news": 3,
}

SelectionMetadata = dict[str, Any]


def _record_review_item_id(digest_date: str, record: dict[str, Any]) -> str:
    return f"{digest_date}:{record['story_bundle_id']}"


def _record_source_role(
    record: dict[str, Any],
    candidate_by_id: dict[str, dict[str, Any]],
    representative_for_record: Callable[
        [dict[str, Any], dict[str, dict[str, Any]]],
        dict[str, Any] | None,
    ],
) -> str:
    representative = representative_for_record(record, candidate_by_id)
    if representative:
        return str(representative.get("source_role_class") or "unknown")
    return "unknown"


def _selection_metadata(
    *,
    record: dict[str, Any],
    bucket: str,
    board_score: dict[str, Any],
    why_selected: str,
    why_not_stronger: str = "",
) -> SelectionMetadata:
    return {
        "story_bundle_id": str(record.get("story_bundle_id") or ""),
        "selection_bucket": bucket,
        "why_selected": why_selected,
        "why_not_stronger": why_not_stronger,
        "board_score": board_score.get("board_score", 0),
        "total_score": board_score.get("total_score", 0),
    }


def _apply_selection_metadata(
    score_rows: list[dict[str, Any]],
    selection_metadata_by_id: dict[str, SelectionMetadata],
) -> None:
    for row in score_rows:
        metadata = selection_metadata_by_id.get(str(row.get("story_bundle_id") or ""))
        if metadata:
            row.update(
                {
                    "selection_bucket": metadata.get("selection_bucket", ""),
                    "why_selected": metadata.get("why_selected", ""),
                    "why_not_stronger": metadata.get("why_not_stronger", ""),
                }
            )


def select_review_board_records(
    records: list[dict[str, Any]],
    history_index: dict[str, list[dict[str, Any]]],
    *,
    candidate_by_id: dict[str, dict[str, Any]],
    editorial_overrides: dict[str, dict[str, Any]],
    syuka_similarity_index: dict[str, dict[str, Any]],
    second_search_index: dict[str, dict[str, Any]],
    digest_date: str,
    review_board_limit: int,
    allow_reviewed_candidates: bool,
    use_board_score: bool,
    use_topic_diversity: bool,
    representative_for_record: Callable[
        [dict[str, Any], dict[str, dict[str, Any]]],
        dict[str, Any] | None,
    ],
    reviewed_history_rows_for_record: Callable[
        [dict[str, Any], dict[str, list[dict[str, Any]]]],
        list[dict[str, Any]],
    ],
    editorial_override_for_row: Callable[
        [dict[str, dict[str, Any]], str, str],
        dict[str, Any],
    ],
    syuka_similarity_for_record: Callable[
        [dict[str, Any], dict[str, Any], dict[str, dict[str, Any]]],
        dict[str, Any] | None,
    ],
    second_search_for_record: Callable[
        [dict[str, Any], dict[str, dict[str, Any]]],
        dict[str, Any] | None,
    ],
) -> tuple[list[dict[str, Any]], list[dict[str, Any]], dict[str, Any]]:
    selected: list[dict[str, Any]] = []
    selected_ids: set[str] = set()
    suppressed: list[dict[str, Any]] = []
    role_counts: Counter[str] = Counter()
    role_cap_blocked: list[dict[str, Any]] = []
    evidence_backfill: list[dict[str, Any]] = []
    hard_blocked: list[dict[str, Any]] = []
    mismatch_blocked: list[dict[str, Any]] = []
    score_rows: list[dict[str, Any]] = []
    override_by_record_id: dict[str, dict[str, Any]] = {}
    selection_metadata_by_id: dict[str, SelectionMetadata] = {}

    scored_records: list[tuple[dict[str, Any], dict[str, Any]]] = []
    for record in records:
        representative = representative_for_record(record, candidate_by_id) or {}
        reviewed_rows = reviewed_history_rows_for_record(record, history_index)
        override = editorial_override_for_row(
            editorial_overrides,
            _record_review_item_id(digest_date, record),
            str(record.get("story_fingerprint") or ""),
        )
        record_id = str(record.get("story_bundle_id") or "")
        if override and record_id:
            override_by_record_id[record_id] = override
        mismatch_reasons = board_mismatch_reasons(record, representative, override)
        syuka_similarity = syuka_similarity_for_record(
            record,
            representative,
            syuka_similarity_index,
        )
        second_search = second_search_for_record(record, second_search_index)
        board_score = compute_board_score(
            record=record,
            representative=representative,
            history_rows=reviewed_rows,
            mismatch_reasons=mismatch_reasons,
            syuka_similarity=syuka_similarity,
            second_search=second_search,
        )
        scored_records.append((record, board_score))
        score_rows.append(
            board_score_report_row(
                record=record,
                representative=representative,
                board_score=board_score,
                history_rows=reviewed_rows,
                mismatch_reasons=mismatch_reasons,
                second_search=second_search,
                override=override,
            )
        )

    apply_topic_diversity_adjustments(
        scored_records,
        score_rows,
        use_topic_diversity=use_topic_diversity,
    )

    if use_board_score:
        scored_records.sort(
            key=lambda item: (
                float(item[1].get("board_score") or 0),
                total_score(representative_for_record(item[0], candidate_by_id) or {}),
            ),
            reverse=True,
        )

    for record, board_score in scored_records:
        representative = representative_for_record(record, candidate_by_id) or {}
        reviewed_rows = reviewed_history_rows_for_record(record, history_index)
        mismatch_reasons = list(board_score.get("mismatch_reasons") or [])
        record_id = str(record.get("story_bundle_id") or "")
        if reviewed_rows and not allow_reviewed_candidates:
            suppressed.append(
                {
                    "record": record,
                    "history_rows": reviewed_rows,
                    "suppressed_reason": "reviewed_history",
                    "board_score": board_score,
                }
            )
            continue
        board_status = record_board_quality_status(
            record,
            representative,
            mismatch_reasons=mismatch_reasons,
        )
        if board_status == "hard_blocked":
            item = {
                "record": record,
                "board_score": board_score,
                "override": override_by_record_id.get(record_id, {}),
                "reasons": hard_block_reasons(record, representative, mismatch_reasons),
            }
            hard_blocked.append(item)
            if mismatch_reasons:
                mismatch_blocked.append(item)
            continue
        if (
            use_board_score
            and str(board_score.get("selection_lesson_role") or "") == "suppress"
        ):
            hard_blocked.append(
                {
                    "record": record,
                    "board_score": board_score,
                    "override": override_by_record_id.get(record_id, {}),
                    "reasons": list(
                        dict.fromkeys(
                            [
                                "selection_lesson_role=suppress",
                                *[
                                    str(lesson)
                                    for lesson in board_score.get("selection_lessons", [])
                                ],
                            ]
                        )
                    ),
                }
            )
            continue
        if board_status == "evidence_backfill":
            evidence_backfill.append(record)
            continue
        role = _record_source_role(record, candidate_by_id, representative_for_record)
        cap = DEFAULT_SOURCE_ROLE_TOP_CAPS.get(role)
        if cap is not None and role_counts[role] >= cap:
            role_cap_blocked.append(record)
            continue
        selected.append(record)
        selected_ids.add(record_id)
        role_counts[role] += 1
        selection_metadata_by_id[record_id] = _selection_metadata(
            record=record,
            bucket="primary_fit",
            board_score=board_score,
            why_selected="passed board quality, reviewed-history, and source-role checks",
            why_not_stronger=(
                "reviewed history allowed by operator flag" if reviewed_rows else ""
            ),
        )
        if len(selected) >= review_board_limit:
            break

    if len(selected) < review_board_limit:
        for record in role_cap_blocked:
            record_id = str(record.get("story_bundle_id") or "")
            if record_id in selected_ids:
                continue
            selected.append(record)
            selected_ids.add(record_id)
            board_score = dict(
                next(
                    score
                    for candidate_record, score in scored_records
                    if str(candidate_record.get("story_bundle_id") or "") == record_id
                )
            )
            selection_metadata_by_id[record_id] = _selection_metadata(
                record=record,
                bucket="role_cap_backfill",
                board_score=board_score,
                why_selected="filled fixed-size board after primary source-role cap pass",
                why_not_stronger="source_role cap overflow in primary pass",
            )
            if len(selected) >= review_board_limit:
                break

    if len(selected) < review_board_limit:
        for record in evidence_backfill:
            record_id = str(record.get("story_bundle_id") or "")
            if record_id in selected_ids:
                continue
            selected.append(record)
            selected_ids.add(record_id)
            board_score = dict(
                next(
                    score
                    for candidate_record, score in scored_records
                    if str(candidate_record.get("story_bundle_id") or "") == record_id
                )
            )
            selection_metadata_by_id[record_id] = _selection_metadata(
                record=record,
                bucket="evidence_backfill",
                board_score=board_score,
                why_selected="filled fixed-size board with evidence/background record",
                why_not_stronger="better suited as evidence, support, or background than main seed",
            )
            if len(selected) >= review_board_limit:
                break

    _apply_selection_metadata(score_rows, selection_metadata_by_id)
    selected_metadata = [
        selection_metadata_by_id.get(str(record.get("story_bundle_id") or ""), {})
        for record in selected
    ]
    bucket_counts = Counter(
        str(item.get("selection_bucket") or "unknown")
        for item in selected_metadata
        if item
    )
    fixed_backfill_used = any(
        bucket in bucket_counts for bucket in ("role_cap_backfill", "evidence_backfill")
    )

    return selected, suppressed, {
        "use_board_score": use_board_score,
        "use_topic_diversity": use_topic_diversity,
        "score_rows": score_rows,
        "board_score_by_id": {
            str(record.get("story_bundle_id") or ""): board_score
            for record, board_score in scored_records
        },
        "hard_blocked": hard_blocked,
        "mismatch_blocked": mismatch_blocked,
        "reviewed_suppressed": suppressed,
        "role_cap_blocked": role_cap_blocked,
        "evidence_backfill": evidence_backfill,
        "selected_ids": [str(record.get("story_bundle_id") or "") for record in selected],
        "selection_metadata_by_id": selection_metadata_by_id,
        "selected_metadata": selected_metadata,
        "selection_bucket_counts": dict(sorted(bucket_counts.items())),
        "fixed_10_backfill_used": fixed_backfill_used,
    }
