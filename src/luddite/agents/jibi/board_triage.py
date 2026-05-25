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


def _review_primary_label(feedback_row: dict[str, Any]) -> str:
    labels = [
        str(payload.get("primary_inferred_label") or payload.get("inferred_label") or "")
        for payload in _reviewer_payloads(feedback_row)
    ]
    labels = [label for label in labels if label and label not in {"unlabeled", "unclear"}]
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


def triage_board_row(
    row: dict[str, Any],
    feedback_row: dict[str, Any] | None = None,
) -> dict[str, Any]:
    feedback_row = feedback_row or {}
    review_label = _review_primary_label(feedback_row)
    modifiers = set(_review_modifiers(feedback_row))
    syuka = row.get("syuka_similarity") if isinstance(row.get("syuka_similarity"), dict) else {}
    syuka_recommendation = str(syuka.get("recommendation") or "missing")
    so_what_label = _so_what_label(row)
    seed_quality = str(row.get("seed_quality_classification") or "")
    source_role = str(row.get("source_role_class") or row.get("source_role") or "unknown")
    reasons: list[str] = []

    def result(label: str, *new_reasons: str) -> dict[str, Any]:
        reasons.extend(reason for reason in new_reasons if reason)
        return {
            "id": str(row.get("ID") or row.get("review_item_id") or ""),
            "title": str(row.get("title") or ""),
            "triage_label": label,
            "review_primary_label": review_label,
            "review_modifiers": sorted(modifiers),
            "syuka_recommendation": syuka_recommendation,
            "past_video_response_signal": str(syuka.get("past_video_response_signal") or ""),
            "so_what_label": so_what_label,
            "seed_quality_classification": seed_quality,
            "source": str(row.get("source") or ""),
            "source_role_class": source_role,
            "reasons": list(dict.fromkeys(reasons)),
        }

    if review_label == "reject":
        return result("reject_or_downrank", "reviewer_reject")
    if "promo_or_bulletin" in modifiers and so_what_label in {"weak", "conditional"}:
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
        *[
            f"- {label}: {count}"
            for label, count in sorted(payload["triage_label_counts"].items())
        ],
        "",
        "## Triage Rows",
        "",
        (
            "| title | triage_label | reviewer | syuka | so_what | "
            "source_role | reasons |"
        ),
        "| --- | --- | --- | --- | --- | --- | --- |",
    ]
    for row in payload["rows"]:
        lines.append(
            "| "
            + " | ".join(
                [
                    _table_cell(row["title"]),
                    row["triage_label"],
                    row["review_primary_label"],
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
            "| none | needs_more_sources | unlabeled | missing | unknown | unknown | none |"
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


def _source_recommendation(source: str, rows: list[dict[str, Any]]) -> str:
    source_lower = source.lower()
    roles = Counter(
        str(row.get("source_role_class") or row.get("source_role") or "")
        for row in rows
    )
    so_whats = Counter(_so_what_label(row) for row in rows)
    count = len(rows)
    if any(term in source_lower for term in ("nikkei", "yougov", "pew", "gallup", "statista")):
        return "manual_only"
    if roles.get("policy_release", 0) >= max(1, count // 2):
        return "evidence_only"
    if "guardian" in source_lower and count >= 3:
        return "keep_but_cap"
    if count >= 4:
        return "keep_but_cap"
    if so_whats.get("strong", 0) >= 1:
        return "keep_candidate_source"
    if so_whats.get("weak", 0) >= max(1, count):
        return "hold"
    return "keep_but_cap"


def build_source_experiment_payload(
    *,
    run_date: str,
    baseline_metadata_path: Path,
    experiment_metadata_path: Path,
    baseline_label: str = "baseline",
    experiment_label: str = "experiment",
) -> dict[str, Any]:
    baseline_rows = _metadata_rows(baseline_metadata_path)
    experiment_rows = _metadata_rows(experiment_metadata_path)
    rows_by_source: dict[str, list[dict[str, Any]]] = {}
    for row in experiment_rows:
        rows_by_source.setdefault(str(row.get("source") or "unknown"), []).append(row)
    source_recommendations = {
        source: _source_recommendation(source, rows)
        for source, rows in sorted(rows_by_source.items())
    }
    return {
        "run_date": run_date,
        "inputs": {
            "baseline_metadata_path": str(baseline_metadata_path),
            "experiment_metadata_path": str(experiment_metadata_path),
        },
        "labels": {
            "baseline": baseline_label,
            "experiment": experiment_label,
        },
        "baseline": _metadata_metrics(baseline_rows),
        "experiment": _metadata_metrics(experiment_rows),
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
        "## Promo / Bulletin Flags",
        "",
        f"- baseline: {baseline['promo_bulletin_flagged']}",
        f"- experiment: {experiment['promo_bulletin_flagged']}",
        "",
        "## Report-only Source Recommendations",
        "",
        "| source | recommendation |",
        "| --- | --- |",
    ]
    for source, recommendation in payload["source_recommendations"].items():
        lines.append(f"| {_table_cell(source)} | {recommendation} |")
    if not payload["source_recommendations"]:
        lines.append("| none | hold |")
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
) -> tuple[Path, Path, dict[str, Any]]:
    output_md.parent.mkdir(parents=True, exist_ok=True)
    output_json.parent.mkdir(parents=True, exist_ok=True)
    payload = build_source_experiment_payload(
        run_date=run_date,
        baseline_metadata_path=baseline_metadata_path,
        experiment_metadata_path=experiment_metadata_path,
        baseline_label=baseline_label,
        experiment_label=experiment_label,
    )
    output_md.write_text(_source_experiment_markdown(payload), encoding="utf-8")
    output_json.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    return output_md, output_json, payload


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
    )
    console.print(
        "[green]Wrote Jibi source experiment comparison "
        f"(delta={payload['delta']['board_row_count']}) to {md_path} and {json_path}.[/green]"
    )
