"""Report-only Jibi board triage and source experiment comparison."""

from __future__ import annotations

import json
import re
from collections import Counter
from pathlib import Path
from typing import Annotated, Any

import typer
from rich.console import Console

from luddite import paths

triage_app = typer.Typer(no_args_is_help=False)
source_experiment_app = typer.Typer(no_args_is_help=False)
source_runner_app = typer.Typer(no_args_is_help=False)
console = Console()

TRIAGE_LABELS = {
    "promote_candidate",
    "conditional_update_angle",
    "adjacent_context",
    "needs_more_sources",
    "evidence_only",
    "past_overlap_check",
    "reject_or_downrank",
}
REVIEW_LABEL_PRIORITY = {
    "reject": 100,
    "seed": 90,
    "conditional_seed": 80,
    "past_topic_overlap": 70,
    "merge_or_duplicate": 70,
    "needs_more_sources": 60,
    "evidence_only": 50,
    "unclear": 10,
    "unlabeled": 0,
}
TRIAGE_DISPLAY_LABELS = {
    "promote_candidate": "promote_candidate",
    "conditional_update_angle": "conditional_update_angle",
    "adjacent_context": "adjacent_context",
    "needs_more_sources": "needs_more_sources",
    "evidence_only": "evidence_only",
    "past_overlap_check": "check_past_overlap",
    "reject_or_downrank": "weak_or_downrank_candidate",
}
NEXT_ACTION_BY_TRIAGE_LABEL = {
    "promote_candidate": "promote",
    "conditional_update_angle": "collect_sources",
    "adjacent_context": "check_past_overlap",
    "needs_more_sources": "collect_sources",
    "evidence_only": "keep_as_evidence",
    "past_overlap_check": "check_past_overlap",
    "reject_or_downrank": "reject",
}
POSITIVE_REVIEW_LABELS = {"seed", "conditional_seed", "needs_more_sources"}
SYSTEM_ISSUE_TERMS = {
    "선불충전금",
    "예치금",
    "충전금",
    "환불",
    "머지포인트",
    "규제 사각지대",
}


def _default_metadata_path(run_date: str) -> Path:
    return paths.DAILY_DIGEST_DIR / f"{run_date}_bundle_review_sheet_metadata.json"


def _default_feedback_path(run_date: str) -> Path:
    return paths.REPORTS_DIR / f"jibi_review_feedback_{run_date}.json"


def _default_triage_md_path(run_date: str) -> Path:
    return paths.REPORTS_DIR / f"jibi_board_triage_{run_date}.md"


def _default_triage_json_path(run_date: str) -> Path:
    return paths.REPORTS_DIR / f"jibi_board_triage_{run_date}.json"


def _default_source_experiment_md_path(run_date: str) -> Path:
    return paths.REPORTS_DIR / f"jibi_source_experiment_{run_date}.md"


def _default_source_experiment_json_path(run_date: str) -> Path:
    return paths.REPORTS_DIR / f"jibi_source_experiment_{run_date}.json"


def _default_source_experiment_plan_md_path(run_date: str, experiment: str) -> Path:
    return paths.REPORTS_DIR / f"jibi_source_experiment_plan_{experiment}_{run_date}.md"


def _default_source_experiment_plan_json_path(run_date: str, experiment: str) -> Path:
    return paths.REPORTS_DIR / f"jibi_source_experiment_plan_{experiment}_{run_date}.json"


def _load_json(path: Path | None) -> dict[str, Any]:
    if path is None or not path.exists():
        return {}
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return {}


def _metadata_rows(path: Path) -> list[dict[str, Any]]:
    payload = _load_json(path)
    return [row for row in payload.get("rows", []) if isinstance(row, dict)]


def _feedback_index(path: Path | None) -> dict[str, dict[str, Any]]:
    payload = _load_json(path)
    output: dict[str, dict[str, Any]] = {}
    for row in payload.get("rows", []):
        if not isinstance(row, dict):
            continue
        for key in [str(row.get("id") or ""), str(row.get("title") or "")]:
            if key.strip():
                output.setdefault(key.strip(), row)
    return output


def _feedback_for_row(
    row: dict[str, Any],
    feedback_rows: dict[str, dict[str, Any]],
) -> dict[str, Any]:
    for key in [
        str(row.get("ID") or ""),
        str(row.get("review_item_id") or ""),
        str(row.get("title") or ""),
    ]:
        if key.strip() in feedback_rows:
            return feedback_rows[key.strip()]
    return {}


def _reviewer_payloads(feedback_row: dict[str, Any]) -> list[dict[str, Any]]:
    reviewers = feedback_row.get("reviewers")
    if not isinstance(reviewers, dict):
        return []
    return [payload for payload in reviewers.values() if isinstance(payload, dict)]


def _meaningful_review_label(payload: dict[str, Any]) -> str:
    label = str(payload.get("primary_inferred_label") or payload.get("inferred_label") or "")
    if label and label not in {"unlabeled", "unclear"}:
        return label
    return ""


def _review_label_distribution(feedback_row: dict[str, Any]) -> dict[str, int]:
    return dict(
        Counter(
            label
            for payload in _reviewer_payloads(feedback_row)
            for label in [_meaningful_review_label(payload)]
            if label
        )
    )


def _review_sample_size(feedback_row: dict[str, Any]) -> int:
    count = 0
    for payload in _reviewer_payloads(feedback_row):
        label = _meaningful_review_label(payload)
        note = str(payload.get("raw_note") or payload.get("note") or "").strip()
        modifiers = payload.get("modifiers")
        if label or note or (isinstance(modifiers, list) and modifiers):
            count += 1
    return count


def _reviewer_disagreement(distribution: dict[str, int]) -> bool:
    return len([label for label, count in distribution.items() if count > 0]) >= 2


def _review_primary_label(feedback_row: dict[str, Any]) -> str:
    labels = [
        label
        for payload in _reviewer_payloads(feedback_row)
        for label in [_meaningful_review_label(payload)]
        if label
    ]
    if not labels:
        return "unlabeled"
    counts = Counter(labels)
    return sorted(
        counts,
        key=lambda label: (counts[label], REVIEW_LABEL_PRIORITY.get(label, 0)),
        reverse=True,
    )[0]


def _review_modifiers(feedback_row: dict[str, Any]) -> list[str]:
    modifiers: list[str] = []
    for payload in _reviewer_payloads(feedback_row):
        modifiers.extend(str(item) for item in payload.get("modifiers", []) if str(item))
    return list(dict.fromkeys(modifiers))


def _so_what_label(row: dict[str, Any]) -> str:
    so_what = row.get("so_what")
    if isinstance(so_what, dict):
        return str(so_what.get("so_what_label") or "unknown")
    return "unknown"


def _row_text(row: dict[str, Any]) -> str:
    so_what = row.get("so_what") if isinstance(row.get("so_what"), dict) else {}
    pieces = [
        row.get("title"),
        row.get("seed_type"),
        row.get("source"),
        row.get("source_role_class"),
        row.get("seed_quality_classification"),
        " ".join(str(item) for item in row.get("seed_quality_reasons", [])),
        " ".join(str(item) for item in so_what.get("audience_bridge_signals", [])),
        " ".join(str(item) for item in so_what.get("weakness_signals", [])),
    ]
    return " ".join(str(item or "") for item in pieces).lower()


def _has_system_issue_terms(row: dict[str, Any]) -> bool:
    text = _row_text(row)
    return any(term.lower() in text for term in SYSTEM_ISSUE_TERMS)


def _reviewer_positive_signal(review_label: str) -> bool:
    return review_label in POSITIVE_REVIEW_LABELS


def _triage_display_label(label: str) -> str:
    return TRIAGE_DISPLAY_LABELS.get(label, label)


def _next_action_for_label(label: str, reasons: list[str]) -> str:
    if label == "conditional_update_angle" and any(
        "syuka_duplicate" in reason for reason in reasons
    ):
        return "check_past_overlap"
    if label == "reject_or_downrank" and any("weak_metadata" in reason for reason in reasons):
        return "ask_reviewer"
    return NEXT_ACTION_BY_TRIAGE_LABEL.get(label, "ask_reviewer")


def _lower_confidence(confidence: str) -> str:
    if confidence == "high":
        return "medium"
    if confidence == "medium":
        return "low"
    return "low"


def _triage_confidence(
    *,
    label: str,
    review_label: str,
    feedback_row: dict[str, Any],
    review_sample_size: int,
    reviewer_label_distribution: dict[str, int],
    syuka_recommendation: str,
    so_what_label: str,
    seed_quality: str,
    source_role: str,
    reasons: list[str],
) -> str:
    reviewer_payloads = _reviewer_payloads(feedback_row)
    has_explicit_tag = any(
        str(payload.get("explicit_tag") or payload.get("tag") or "")
        not in {"", "unlabeled", "unclear"}
        for payload in reviewer_payloads
    )
    reviewer_confidence = any(
        str(payload.get("inferred_confidence") or "") == "high"
        for payload in reviewer_payloads
    )
    supporting_signals = sum(
        [
            syuka_recommendation in {"duplicate", "adjacent", "needs_human_check"},
            so_what_label in {"strong", "weak"},
            seed_quality in {"reject_or_downrank", "evidence_only", "standalone_seed"},
            source_role in {"policy_release", "research_note", "public_wire"},
        ]
    )
    confidence = "low"
    if review_sample_size > 0:
        if has_explicit_tag or (
            reviewer_confidence and supporting_signals >= 1
        ) or "reviewer_overlap_and_syuka_duplicate" in reasons:
            confidence = "high"
        else:
            confidence = "medium"
    elif supporting_signals >= 2 and label in {
        "conditional_update_angle",
        "past_overlap_check",
        "evidence_only",
        "reject_or_downrank",
    }:
        confidence = "medium"

    if label == "reject_or_downrank" and "promo_or_bulletin_with_weak_so_what" in reasons:
        confidence = "high" if review_sample_size == 0 else confidence
    if _reviewer_disagreement(reviewer_label_distribution):
        confidence = _lower_confidence(confidence)
    if review_label == "unclear":
        confidence = _lower_confidence(confidence)
    return confidence


def triage_board_row(
    row: dict[str, Any],
    feedback_row: dict[str, Any] | None = None,
) -> dict[str, Any]:
    feedback_row = feedback_row or {}
    review_label = _review_primary_label(feedback_row)
    review_sample_size = _review_sample_size(feedback_row)
    reviewer_label_distribution = _review_label_distribution(feedback_row)
    modifiers = set(_review_modifiers(feedback_row))
    syuka = row.get("syuka_similarity") if isinstance(row.get("syuka_similarity"), dict) else {}
    syuka_recommendation = str(syuka.get("recommendation") or "missing")
    so_what_label = _so_what_label(row)
    seed_quality = str(row.get("seed_quality_classification") or "")
    source_role = str(row.get("source_role_class") or row.get("source_role") or "unknown")
    reasons: list[str] = []

    def result(label: str, *new_reasons: str) -> dict[str, Any]:
        reasons.extend(reason for reason in new_reasons if reason)
        unique_reasons = list(dict.fromkeys(reasons))
        display_label = _triage_display_label(label)
        confidence = _triage_confidence(
            label=label,
            review_label=review_label,
            feedback_row=feedback_row,
            review_sample_size=review_sample_size,
            reviewer_label_distribution=reviewer_label_distribution,
            syuka_recommendation=syuka_recommendation,
            so_what_label=so_what_label,
            seed_quality=seed_quality,
            source_role=source_role,
            reasons=unique_reasons,
        )
        return {
            "id": str(row.get("ID") or row.get("review_item_id") or ""),
            "title": str(row.get("title") or ""),
            "triage_label": label,
            "triage_display_label": display_label,
            "triage_confidence": confidence,
            "next_action": _next_action_for_label(label, unique_reasons),
            "review_primary_label": review_label,
            "review_modifiers": sorted(modifiers),
            "review_sample_size": review_sample_size,
            "reviewer_label_distribution": reviewer_label_distribution,
            "syuka_recommendation": syuka_recommendation,
            "past_video_response_signal": str(syuka.get("past_video_response_signal") or ""),
            "so_what_label": so_what_label,
            "seed_quality_classification": seed_quality,
            "source": str(row.get("source") or ""),
            "source_role_class": source_role,
            "reasons": unique_reasons,
        }

    if review_label == "reject":
        return result("reject_or_downrank", "reviewer_reject")
    if (
        "promo_or_bulletin" in modifiers
        and so_what_label in {"weak", "conditional"}
        and not _reviewer_positive_signal(review_label)
    ):
        return result("reject_or_downrank", "promo_or_bulletin_with_weak_so_what")
    if "past_topic_overlap" in modifiers and syuka_recommendation == "duplicate":
        return result("past_overlap_check", "reviewer_overlap_and_syuka_duplicate")
    if review_label in {"past_topic_overlap", "merge_or_duplicate"}:
        return result("past_overlap_check", f"reviewer_{review_label}")
    if review_label == "seed":
        if syuka_recommendation == "duplicate":
            return result("conditional_update_angle", "reviewer_seed_but_syuka_duplicate")
        if syuka_recommendation == "adjacent":
            return result("conditional_update_angle", "reviewer_seed_with_adjacent_context")
        return result("promote_candidate", "reviewer_seed")
    if review_label == "conditional_seed":
        return result("conditional_update_angle", "reviewer_conditional_seed")
    if review_label == "needs_more_sources":
        return result("needs_more_sources", "reviewer_needs_more_sources")
    if review_label == "evidence_only":
        return result("evidence_only", "reviewer_evidence_only")
    if "system_issue" in modifiers and _has_system_issue_terms(row):
        return result("conditional_update_angle", "system_issue_with_known_policy_hook")
    if seed_quality in {"reject_or_downrank"}:
        return result("reject_or_downrank", "seed_quality_reject_or_downrank")
    if seed_quality == "evidence_only" or source_role == "policy_release":
        return result("evidence_only", "evidence_or_policy_release_default")
    if syuka_recommendation == "duplicate":
        return result("past_overlap_check", "syuka_duplicate")
    if syuka_recommendation == "adjacent":
        if so_what_label == "strong":
            return result("conditional_update_angle", "syuka_adjacent_with_strong_so_what")
        return result("adjacent_context", "syuka_adjacent")
    if syuka_recommendation == "needs_human_check":
        return result("past_overlap_check", "syuka_needs_human_check")
    if so_what_label == "strong":
        return result("needs_more_sources", "strong_so_what_without_reviewer_promotion")
    if so_what_label == "weak":
        return result("reject_or_downrank", "weak_so_what")
    return result("needs_more_sources", "default_report_only_review")


def build_board_triage_payload(
    *,
    run_date: str,
    metadata_path: Path,
    feedback_path: Path | None = None,
) -> dict[str, Any]:
    rows = _metadata_rows(metadata_path)
    feedback_rows = _feedback_index(feedback_path)
    triage_rows = [
        triage_board_row(row, _feedback_for_row(row, feedback_rows))
        for row in rows
    ]
    return {
        "run_date": run_date,
        "inputs": {
            "metadata_path": str(metadata_path),
            "feedback_path": str(feedback_path or ""),
        },
        "row_count": len(rows),
        "triage_label_counts": dict(Counter(row["triage_label"] for row in triage_rows)),
        "triage_display_label_counts": dict(
            Counter(row["triage_display_label"] for row in triage_rows)
        ),
        "triage_confidence_counts": dict(
            Counter(row["triage_confidence"] for row in triage_rows)
        ),
        "next_action_counts": dict(Counter(row["next_action"] for row in triage_rows)),
        "review_sample_size_total": sum(
            int(row.get("review_sample_size") or 0) for row in triage_rows
        ),
        "source_counts": dict(Counter(row["source"] for row in triage_rows)),
        "source_role_counts": dict(Counter(row["source_role_class"] for row in triage_rows)),
        "rows": triage_rows,
    }


def _table_cell(value: Any) -> str:
    return re.sub(r"\s+", " ", str(value or "")).replace("|", "\\|").strip()


def _triage_markdown(payload: dict[str, Any]) -> str:
    lines = [
        f"# Jibi Board Triage — {payload['run_date']}",
        "",
        "Report-only triage. This does not change scoring, board rows, source "
        "allowlists, or the visible Google Sheet schema.",
        "",
        "## Summary",
        "",
        f"- row_count: {payload['row_count']}",
        f"- review_sample_size_total: {payload['review_sample_size_total']}",
        *[
            f"- {label}: {count}"
            for label, count in sorted(payload["triage_label_counts"].items())
        ],
        "",
        "## Next Action Counts",
        "",
        *[
            f"- {action}: {count}"
            for action, count in sorted(payload["next_action_counts"].items())
        ],
        "",
        "## Triage Rows",
        "",
        (
            "| title | display_label | confidence | next_action | reviewer | "
            "sample | syuka | so_what | source_role | reasons |"
        ),
        "| --- | --- | --- | --- | ---: | --- | --- | --- | --- | --- |",
    ]
    for row in payload["rows"]:
        lines.append(
            "| "
            + " | ".join(
                [
                    _table_cell(row["title"]),
                    row["triage_display_label"],
                    row["triage_confidence"],
                    row["next_action"],
                    row["review_primary_label"],
                    str(row["review_sample_size"]),
                    row["syuka_recommendation"],
                    row["so_what_label"],
                    row["source_role_class"],
                    _table_cell(", ".join(row["reasons"])),
                ]
            )
            + " |"
        )
    if not payload["rows"]:
        lines.append(
            "| none | needs_more_sources | low | ask_reviewer | unlabeled | "
            "0 | missing | unknown | unknown | none |"
        )
    return "\n".join(lines) + "\n"


def write_board_triage_outputs(
    *,
    run_date: str,
    metadata_path: Path,
    feedback_path: Path | None,
    output_md: Path,
    output_json: Path,
) -> tuple[Path, Path, dict[str, Any]]:
    output_md.parent.mkdir(parents=True, exist_ok=True)
    output_json.parent.mkdir(parents=True, exist_ok=True)
    payload = build_board_triage_payload(
        run_date=run_date,
        metadata_path=metadata_path,
        feedback_path=feedback_path,
    )
    output_md.write_text(_triage_markdown(payload), encoding="utf-8")
    output_json.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    return output_md, output_json, payload


def _metadata_metrics(rows: list[dict[str, Any]]) -> dict[str, Any]:
    syuka_counts = Counter(
        str((row.get("syuka_similarity") or {}).get("recommendation") or "missing")
        for row in rows
    )
    so_what_counts = Counter(_so_what_label(row) for row in rows)
    source_counts = Counter(str(row.get("source") or "unknown") for row in rows)
    source_role_counts = Counter(
        str(row.get("source_role_class") or row.get("source_role") or "unknown")
        for row in rows
    )
    seed_quality_counts = Counter(
        str(row.get("seed_quality_classification") or "unknown") for row in rows
    )
    promo_bulletin_count = sum(
        1
        for row in rows
        if any(
            term in _row_text(row)
            for term in ("promo", "bulletin", "홍보", "공모전", "이벤트")
        )
    )
    return {
        "board_row_count": len(rows),
        "source_mix": dict(source_counts),
        "source_role_mix": dict(source_role_counts),
        "so_what_distribution": dict(so_what_counts),
        "seed_quality_distribution": dict(seed_quality_counts),
        "syuka_similarity_distribution": dict(syuka_counts),
        "promo_bulletin_flagged": promo_bulletin_count,
    }


def _triage_metrics(triage_path: Path | None) -> dict[str, Any]:
    payload = _load_json(triage_path)
    rows = [row for row in payload.get("rows", []) if isinstance(row, dict)]
    if not rows:
        return {
            "triage_label_distribution": {},
            "triage_display_label_distribution": {},
            "triage_confidence_distribution": {},
            "next_action_distribution": {},
            "reviewed_rows": 0,
            "review_sample_size_total": 0,
        }
    sample_sizes = [int(row.get("review_sample_size") or 0) for row in rows]
    return {
        "triage_label_distribution": dict(
            Counter(str(row.get("triage_label") or "unknown") for row in rows)
        ),
        "triage_display_label_distribution": dict(
            Counter(str(row.get("triage_display_label") or "unknown") for row in rows)
        ),
        "triage_confidence_distribution": dict(
            Counter(str(row.get("triage_confidence") or "unknown") for row in rows)
        ),
        "next_action_distribution": dict(
            Counter(str(row.get("next_action") or "unknown") for row in rows)
        ),
        "reviewed_rows": sum(1 for size in sample_sizes if size > 0),
        "review_sample_size_total": sum(sample_sizes),
    }


def _rows_by_source_from_triage(triage_path: Path | None) -> dict[str, list[dict[str, Any]]]:
    payload = _load_json(triage_path)
    rows_by_source: dict[str, list[dict[str, Any]]] = {}
    for row in payload.get("rows", []):
        if isinstance(row, dict):
            rows_by_source.setdefault(str(row.get("source") or "unknown"), []).append(row)
    return rows_by_source


def _source_recommendation(
    source: str,
    rows: list[dict[str, Any]],
    triage_rows: list[dict[str, Any]] | None = None,
) -> dict[str, Any]:
    source_lower = source.lower()
    roles = Counter(
        str(row.get("source_role_class") or row.get("source_role") or "")
        for row in rows
    )
    so_whats = Counter(_so_what_label(row) for row in rows)
    syuka_counts = Counter(
        str((row.get("syuka_similarity") or {}).get("recommendation") or "missing")
        for row in rows
    )
    count = len(rows)
    triage_rows = triage_rows or []
    reviewed_rows = sum(int(row.get("review_sample_size") or 0) > 0 for row in triage_rows)
    triage_labels = Counter(str(row.get("triage_label") or "unknown") for row in triage_rows)
    reasons: list[str] = []
    confidence = "low"

    if so_whats.get("strong", 0) or so_whats.get("conditional", 0):
        reasons.append("useful_strong_or_conditional_rows")
    promo_bulletin_count = sum(
        1
        for row in rows
        if any(
            term in _row_text(row)
            for term in ("promo", "bulletin", "홍보", "공모전", "이벤트")
        )
    )
    if promo_bulletin_count >= max(1, count // 2):
        reasons.append("too_many_promo_bulletin_rows")
    if syuka_counts.get("duplicate", 0) >= max(1, count // 2) or triage_labels.get(
        "past_overlap_check",
        0,
    ) >= max(1, len(triage_rows) // 2):
        reasons.append("syuka_duplicate_heavy")
    if so_whats.get("weak", 0) >= max(1, count // 2):
        reasons.append("weak_audience_bridge")
    if not triage_rows:
        reasons.append("no_triage_metadata")
    elif reviewed_rows == 0:
        reasons.append("no_reviewed_rows_yet")
    else:
        confidence = "medium"

    if any(term in source_lower for term in ("nikkei", "yougov", "pew", "gallup", "statista")):
        recommendation = "manual_only"
        reasons.append("manual_or_subscription_probe_source")
    elif roles.get("policy_release", 0) >= max(1, count // 2):
        recommendation = "evidence_only"
        reasons.append("policy_release_evidence_default")
    elif "guardian" in source_lower and count >= 3:
        recommendation = "keep_but_cap"
        reasons.append("guardian_section_experiment_requires_cap")
    elif count >= 4:
        recommendation = "keep_but_cap"
        reasons.append("source_volume_needs_cap")
    elif so_whats.get("strong", 0) >= 1:
        recommendation = "keep_candidate_source"
        reasons.append("has_strong_so_what_candidate")
    elif so_whats.get("weak", 0) >= max(1, count):
        recommendation = "hold"
        reasons.append("all_rows_weak_so_what")
    else:
        recommendation = "keep_but_cap"
        reasons.append("default_controlled_keep_with_cap")

    if reviewed_rows >= 3 and "weak_audience_bridge" not in reasons:
        confidence = "high"
    if "no_triage_metadata" in reasons or "no_reviewed_rows_yet" in reasons:
        confidence = "low"
    return {
        "recommendation": recommendation,
        "confidence": confidence,
        "reasons": list(dict.fromkeys(reasons)),
    }


def build_source_experiment_payload(
    *,
    run_date: str,
    baseline_metadata_path: Path,
    experiment_metadata_path: Path,
    baseline_label: str = "baseline",
    experiment_label: str = "experiment",
    baseline_triage_path: Path | None = None,
    experiment_triage_path: Path | None = None,
) -> dict[str, Any]:
    baseline_rows = _metadata_rows(baseline_metadata_path)
    experiment_rows = _metadata_rows(experiment_metadata_path)
    experiment_triage_by_source = _rows_by_source_from_triage(experiment_triage_path)
    rows_by_source: dict[str, list[dict[str, Any]]] = {}
    for row in experiment_rows:
        rows_by_source.setdefault(str(row.get("source") or "unknown"), []).append(row)
    source_recommendations = {
        source: _source_recommendation(
            source,
            rows,
            experiment_triage_by_source.get(source, []),
        )
        for source, rows in sorted(rows_by_source.items())
    }
    baseline_metrics = _metadata_metrics(baseline_rows)
    baseline_metrics.update(_triage_metrics(baseline_triage_path))
    experiment_metrics = _metadata_metrics(experiment_rows)
    experiment_metrics.update(_triage_metrics(experiment_triage_path))
    return {
        "run_date": run_date,
        "inputs": {
            "baseline_metadata_path": str(baseline_metadata_path),
            "experiment_metadata_path": str(experiment_metadata_path),
            "baseline_triage_path": str(baseline_triage_path or ""),
            "experiment_triage_path": str(experiment_triage_path or ""),
        },
        "labels": {
            "baseline": baseline_label,
            "experiment": experiment_label,
        },
        "baseline": baseline_metrics,
        "experiment": experiment_metrics,
        "delta": {
            "board_row_count": len(experiment_rows) - len(baseline_rows),
        },
        "source_recommendations": source_recommendations,
    }


def _counter_delta_lines(
    baseline: dict[str, int],
    experiment: dict[str, int],
) -> list[str]:
    keys = sorted(set(baseline) | set(experiment))
    return [
        f"- {key}: baseline={baseline.get(key, 0)}, "
        f"experiment={experiment.get(key, 0)}, "
        f"delta={experiment.get(key, 0) - baseline.get(key, 0)}"
        for key in keys
    ] or ["- none"]


def _source_experiment_markdown(payload: dict[str, Any]) -> str:
    baseline = payload["baseline"]
    experiment = payload["experiment"]
    lines = [
        f"# Jibi Source Experiment Comparison — {payload['run_date']}",
        "",
        "Report-only comparison. This does not edit source allowlists or Jibi scoring.",
        "",
        "## Row Counts",
        "",
        f"- baseline: {baseline['board_row_count']}",
        f"- experiment: {experiment['board_row_count']}",
        f"- delta: {payload['delta']['board_row_count']}",
        "",
        "## Source Mix",
        "",
        *_counter_delta_lines(baseline["source_mix"], experiment["source_mix"]),
        "",
        "## Source Role Mix",
        "",
        *_counter_delta_lines(baseline["source_role_mix"], experiment["source_role_mix"]),
        "",
        "## So-What Distribution",
        "",
        *_counter_delta_lines(
            baseline["so_what_distribution"],
            experiment["so_what_distribution"],
        ),
        "",
        "## Syuka Similarity Distribution",
        "",
        *_counter_delta_lines(
            baseline["syuka_similarity_distribution"],
            experiment["syuka_similarity_distribution"],
        ),
        "",
        "## Triage Label Distribution",
        "",
        *_counter_delta_lines(
            baseline["triage_label_distribution"],
            experiment["triage_label_distribution"],
        ),
        "",
        "## Triage Confidence Distribution",
        "",
        *_counter_delta_lines(
            baseline["triage_confidence_distribution"],
            experiment["triage_confidence_distribution"],
        ),
        "",
        "## Next Action Distribution",
        "",
        *_counter_delta_lines(
            baseline["next_action_distribution"],
            experiment["next_action_distribution"],
        ),
        "",
        "## Promo / Bulletin Flags",
        "",
        f"- baseline: {baseline['promo_bulletin_flagged']}",
        f"- experiment: {experiment['promo_bulletin_flagged']}",
        "",
        "## Report-only Source Recommendations",
        "",
        "| source | recommendation | confidence | reasons |",
        "| --- | --- | --- | --- |",
    ]
    for source, recommendation in payload["source_recommendations"].items():
        lines.append(
            "| "
            + " | ".join(
                [
                    _table_cell(source),
                    recommendation["recommendation"],
                    recommendation["confidence"],
                    _table_cell(", ".join(recommendation["reasons"])),
                ]
            )
            + " |"
        )
    if not payload["source_recommendations"]:
        lines.append("| none | hold | low | no_rows |")
    return "\n".join(lines) + "\n"


def write_source_experiment_outputs(
    *,
    run_date: str,
    baseline_metadata_path: Path,
    experiment_metadata_path: Path,
    output_md: Path,
    output_json: Path,
    baseline_label: str = "baseline",
    experiment_label: str = "experiment",
    baseline_triage_path: Path | None = None,
    experiment_triage_path: Path | None = None,
) -> tuple[Path, Path, dict[str, Any]]:
    output_md.parent.mkdir(parents=True, exist_ok=True)
    output_json.parent.mkdir(parents=True, exist_ok=True)
    payload = build_source_experiment_payload(
        run_date=run_date,
        baseline_metadata_path=baseline_metadata_path,
        experiment_metadata_path=experiment_metadata_path,
        baseline_label=baseline_label,
        experiment_label=experiment_label,
        baseline_triage_path=baseline_triage_path,
        experiment_triage_path=experiment_triage_path,
    )
    output_md.write_text(_source_experiment_markdown(payload), encoding="utf-8")
    output_json.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    return output_md, output_json, payload


def _parse_config_scalar(value: str) -> str | int | bool | None:
    value = value.strip()
    if value in {"", "null", "None"}:
        return None
    if value.lower() == "true":
        return True
    if value.lower() == "false":
        return False
    if value.isdigit():
        return int(value)
    return value.strip('"').strip("'")


def _parse_yaml_list_section(text: str, section_name: str) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    current: dict[str, Any] | None = None
    in_section = False
    for raw_line in text.splitlines():
        stripped = raw_line.split("#", 1)[0].rstrip()
        if not stripped:
            continue
        if not raw_line.startswith(" ") and stripped.endswith(":"):
            if in_section and current:
                rows.append(current)
            in_section = stripped[:-1] == section_name
            current = None
            continue
        if not in_section:
            continue
        line = stripped.strip()
        if line.startswith("- "):
            if current:
                rows.append(current)
            current = {}
            item = line[2:].strip()
            if ":" in item:
                key, value = item.split(":", 1)
                current[key.strip()] = _parse_config_scalar(value)
            continue
        if current is not None and ":" in line:
            key, value = line.split(":", 1)
            current[key.strip()] = _parse_config_scalar(value)
    if in_section and current:
        rows.append(current)
    return rows


def _parse_yaml_mapping_section(text: str, section_name: str) -> dict[str, Any]:
    values: dict[str, Any] = {}
    in_section = False
    for raw_line in text.splitlines():
        stripped = raw_line.split("#", 1)[0].rstrip()
        if not stripped:
            continue
        if not raw_line.startswith(" ") and stripped.endswith(":"):
            in_section = stripped[:-1] == section_name
            continue
        if not in_section:
            continue
        line = stripped.strip()
        if line.startswith("- ") or ":" not in line:
            continue
        key, value = line.split(":", 1)
        values[key.strip()] = _parse_config_scalar(value)
    return values


def _parse_experiment_id(text: str) -> str:
    for raw_line in text.splitlines():
        line = raw_line.split("#", 1)[0].strip()
        if line.startswith("experiment_id:"):
            return str(_parse_config_scalar(line.split(":", 1)[1]) or "")
    return ""


def _source_experiment_dir(run_date: str, experiment: str) -> Path:
    return paths.OUTPUTS_DIR / "experiments" / experiment / run_date


def _allowlist_yaml(entries: list[dict[str, Any]]) -> str:
    lines = [
        "# Temporary Jibi source experiment allowlist.",
        "# Generated by run-jibi-source-experiment; do not copy over the default allowlist.",
        "sources:",
    ]
    for entry in entries:
        lines.extend(
            [
                f"  - source_id: {entry['source_id']}",
                f"    collection_enabled: {str(entry.get('collection_enabled', True)).lower()}",
                f"    fetch_limit: {int(entry.get('fetch_limit') or 20)}",
                f"    reason: {entry.get('reason') or 'controlled_source_experiment'}",
            ]
        )
    return "\n".join(lines) + "\n"


def build_source_experiment_plan(
    *,
    run_date: str,
    experiment: str,
    config_path: Path,
    experiment_dir: Path | None = None,
) -> dict[str, Any]:
    config_text = config_path.read_text(encoding="utf-8")
    configured_experiment = _parse_experiment_id(config_text)
    if configured_experiment and configured_experiment != experiment:
        raise ValueError(
            f"experiment mismatch: requested {experiment}, config has {configured_experiment}"
        )
    guardrails = _parse_yaml_mapping_section(config_text, "guardrails")
    entries = _parse_yaml_list_section(config_text, "temporary_allowlist_sources")
    excluded = _parse_yaml_list_section(config_text, "explicitly_excluded")
    if not entries:
        raise ValueError(f"no temporary allowlist sources found in {config_path}")
    broad_excluded = any(
        str(item.get("source_id") or "") == "guardian_rss_candidate" for item in excluded
    )
    if experiment == "guardian_sections_v1" and not broad_excluded:
        raise ValueError("guardian_sections_v1 must explicitly exclude guardian_rss_candidate")

    resolved_experiment_dir = experiment_dir or _source_experiment_dir(run_date, experiment)
    allowlist_path = resolved_experiment_dir / "rss_collection_allowlist.yaml"
    inbox_path = resolved_experiment_dir / f"rss_{run_date}.jsonl"
    ingest_report_path = resolved_experiment_dir / f"rss_ingest_{run_date}.md"
    commands = [
        (
            "PYTHONPATH=src .venv/bin/python -m luddite fetch-rss-articles "
            f"--date {run_date} --allowlist-path {allowlist_path} "
            f"--output {inbox_path} --report {ingest_report_path} --skip-history"
        ),
        (
            "PYTHONPATH=src .venv/bin/python -m luddite import-articles "
            f"--input-file {inbox_path}"
        ),
        "make normalize-candidates",
        "make score-candidates",
        "make cluster-jibi-candidates",
        "make render-daily-digest",
        (
            "PYTHONPATH=src .venv/bin/python -m luddite summarize-jibi-board-triage "
            f"--date {run_date}"
        ),
    ]
    return {
        "run_date": run_date,
        "experiment": experiment,
        "config_path": str(config_path),
        "experiment_dir": str(resolved_experiment_dir),
        "temporary_allowlist_path": str(allowlist_path),
        "rss_inbox_path": str(inbox_path),
        "rss_ingest_report_path": str(ingest_report_path),
        "temporary_allowlist_sources": entries,
        "explicitly_excluded": excluded,
        "guardrails": guardrails,
        "commands": commands,
        "notes": [
            "default_allowlist_unchanged",
            "no_google_sheet_write",
            "compare_experiment_board_to_baseline_before_source_default_changes",
        ],
    }


def _source_experiment_plan_markdown(payload: dict[str, Any]) -> str:
    lines = [
        f"# Jibi Source Experiment Plan — {payload['experiment']} — {payload['run_date']}",
        "",
        "This creates a temporary allowlist and command plan only. It does not edit "
        "`config/rss_collection_allowlist.yaml`, change scoring, or write Google Sheets.",
        "",
        "## Temporary Allowlist",
        "",
        f"- path: `{payload['temporary_allowlist_path']}`",
        f"- source_count: {len(payload['temporary_allowlist_sources'])}",
        "",
        "## Enabled Sources",
        "",
    ]
    for source in payload["temporary_allowlist_sources"]:
        lines.append(
            f"- {source['source_id']}: fetch_limit={source.get('fetch_limit')}, "
            f"reason={source.get('reason')}"
        )
    lines.extend(["", "## Explicitly Excluded", ""])
    for source in payload["explicitly_excluded"]:
        lines.append(f"- {source.get('source_id')}: {source.get('reason')}")
    lines.extend(["", "## Command Plan", ""])
    lines.extend(f"{index}. `{command}`" for index, command in enumerate(payload["commands"], 1))
    lines.extend(["", "## Guardrails", ""])
    lines.extend(f"- {key}: {value}" for key, value in sorted(payload["guardrails"].items()))
    lines.extend(["", "## Notes", ""])
    lines.extend(f"- {note}" for note in payload["notes"])
    return "\n".join(lines) + "\n"


def write_source_experiment_plan_outputs(
    *,
    run_date: str,
    experiment: str,
    config_path: Path,
    output_md: Path,
    output_json: Path,
    experiment_dir: Path | None = None,
) -> tuple[Path, Path, Path, dict[str, Any]]:
    payload = build_source_experiment_plan(
        run_date=run_date,
        experiment=experiment,
        config_path=config_path,
        experiment_dir=experiment_dir,
    )
    allowlist_path = Path(payload["temporary_allowlist_path"])
    allowlist_path.parent.mkdir(parents=True, exist_ok=True)
    output_md.parent.mkdir(parents=True, exist_ok=True)
    output_json.parent.mkdir(parents=True, exist_ok=True)
    allowlist_path.write_text(
        _allowlist_yaml(payload["temporary_allowlist_sources"]),
        encoding="utf-8",
    )
    output_md.write_text(_source_experiment_plan_markdown(payload), encoding="utf-8")
    output_json.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    return output_md, output_json, allowlist_path, payload


@triage_app.callback(invoke_without_command=True)
def summarize_board_triage(
    date: Annotated[str, typer.Option("--date", help="Jibi run date YYYY-MM-DD.")],
    metadata: Annotated[
        Path | None,
        typer.Option("--metadata", help="Bundle review metadata sidecar."),
    ] = None,
    feedback: Annotated[
        Path | None,
        typer.Option("--feedback", help="Jibi review feedback JSON report."),
    ] = None,
    output_md: Annotated[
        Path | None,
        typer.Option("--output-md", help="Markdown triage report path."),
    ] = None,
    output_json: Annotated[
        Path | None,
        typer.Option("--output-json", help="JSON triage report path."),
    ] = None,
) -> None:
    md_path, json_path, payload = write_board_triage_outputs(
        run_date=date,
        metadata_path=metadata or _default_metadata_path(date),
        feedback_path=feedback or _default_feedback_path(date),
        output_md=output_md or _default_triage_md_path(date),
        output_json=output_json or _default_triage_json_path(date),
    )
    console.print(
        "[green]Wrote Jibi board triage "
        f"({payload['row_count']} rows) to {md_path} and {json_path}.[/green]"
    )


@source_runner_app.callback(invoke_without_command=True)
def run_source_experiment(
    date: Annotated[str, typer.Option("--date", help="Jibi run date YYYY-MM-DD.")],
    experiment: Annotated[
        str,
        typer.Option("--experiment", help="Controlled experiment id."),
    ] = "guardian_sections_v1",
    config: Annotated[
        Path,
        typer.Option("--config", help="Controlled source experiment config YAML."),
    ] = paths.CONFIG_DIR / "experiments" / "rss_guardian_sections.yaml",
    experiment_dir: Annotated[
        Path | None,
        typer.Option("--experiment-dir", help="Temporary experiment output directory."),
    ] = None,
    output_md: Annotated[
        Path | None,
        typer.Option("--output-md", help="Markdown source experiment plan path."),
    ] = None,
    output_json: Annotated[
        Path | None,
        typer.Option("--output-json", help="JSON source experiment plan path."),
    ] = None,
) -> None:
    md_path, json_path, allowlist_path, payload = write_source_experiment_plan_outputs(
        run_date=date,
        experiment=experiment,
        config_path=config,
        output_md=output_md or _default_source_experiment_plan_md_path(date, experiment),
        output_json=output_json or _default_source_experiment_plan_json_path(date, experiment),
        experiment_dir=experiment_dir,
    )
    console.print(
        "[green]Wrote Jibi source experiment plan "
        f"({len(payload['temporary_allowlist_sources'])} sources) to {md_path}, "
        f"{json_path}, and {allowlist_path}.[/green]"
    )


@source_experiment_app.callback(invoke_without_command=True)
def compare_source_experiment(
    date: Annotated[str, typer.Option("--date", help="Jibi run date YYYY-MM-DD.")],
    baseline_metadata: Annotated[
        Path,
        typer.Option("--baseline-metadata", help="Baseline bundle review metadata JSON."),
    ],
    experiment_metadata: Annotated[
        Path,
        typer.Option("--experiment-metadata", help="Experiment bundle review metadata JSON."),
    ],
    baseline_triage: Annotated[
        Path | None,
        typer.Option("--baseline-triage", help="Baseline board triage JSON."),
    ] = None,
    experiment_triage: Annotated[
        Path | None,
        typer.Option("--experiment-triage", help="Experiment board triage JSON."),
    ] = None,
    output_md: Annotated[
        Path | None,
        typer.Option("--output-md", help="Markdown source experiment report path."),
    ] = None,
    output_json: Annotated[
        Path | None,
        typer.Option("--output-json", help="JSON source experiment report path."),
    ] = None,
    baseline_label: Annotated[str, typer.Option("--baseline-label")] = "baseline",
    experiment_label: Annotated[str, typer.Option("--experiment-label")] = "experiment",
) -> None:
    md_path, json_path, payload = write_source_experiment_outputs(
        run_date=date,
        baseline_metadata_path=baseline_metadata,
        experiment_metadata_path=experiment_metadata,
        output_md=output_md or _default_source_experiment_md_path(date),
        output_json=output_json or _default_source_experiment_json_path(date),
        baseline_label=baseline_label,
        experiment_label=experiment_label,
        baseline_triage_path=baseline_triage,
        experiment_triage_path=experiment_triage,
    )
    console.print(
        "[green]Wrote Jibi source experiment comparison "
        f"(delta={payload['delta']['board_row_count']}) to {md_path} and {json_path}.[/green]"
    )
