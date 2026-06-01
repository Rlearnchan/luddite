"""Replay Jibi visible-board quality metrics from local report artifacts."""

from __future__ import annotations

import csv
import json
from collections import Counter
from pathlib import Path
from typing import Annotated, Any

import typer

from luddite import paths
from luddite.agents.jibi.visible_board_quality import recommend_quality_floor_visible_rows

app = typer.Typer(no_args_is_help=False)


def _load_json(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {}
    payload = json.loads(path.read_text(encoding="utf-8"))
    return payload if isinstance(payload, dict) else {}


def _load_csv_rows(path: Path) -> list[dict[str, Any]]:
    if not path.exists():
        return []
    with path.open("r", encoding="utf-8-sig", newline="") as input_file:
        return [dict(row) for row in csv.DictReader(input_file)]


def _date_paths(run_date: str) -> dict[str, Path]:
    return {
        "csv": paths.DAILY_DIGEST_DIR / f"{run_date}_bundle_review_sheet.csv",
        "metadata": paths.DAILY_DIGEST_DIR
        / f"{run_date}_bundle_review_sheet_metadata.json",
        "board_score": paths.REPORTS_DIR / f"jibi_board_score_{run_date}.json",
        "calibration": paths.REPORTS_DIR
        / f"jibi_selection_calibration_{run_date}.json",
    }


def _metadata_rows(payload: dict[str, Any]) -> list[dict[str, Any]]:
    rows = payload.get("rows")
    return rows if isinstance(rows, list) else []


def _board_rows(board_payload: dict[str, Any]) -> list[dict[str, Any]]:
    selected = board_payload.get("selected")
    if isinstance(selected, list):
        return selected
    distribution = board_payload.get("board_score_distribution")
    if isinstance(distribution, dict):
        rows = distribution.get("board_score_top_candidates")
        if isinstance(rows, list):
            return rows
    return []


def _float_value(value: Any) -> float:
    try:
        return float(value or 0)
    except (TypeError, ValueError):
        return 0.0


def _counter_from_rows(rows: list[dict[str, Any]], key: str) -> dict[str, int]:
    counts = Counter(str(row.get(key) or "other") for row in rows)
    counts.pop("", None)
    return dict(sorted(counts.items(), key=lambda item: (-item[1], item[0])))


def _topic_family_counts(rows: list[dict[str, Any]]) -> dict[str, int]:
    counts: Counter[str] = Counter()
    for row in rows:
        families = row.get("topic_families")
        if not isinstance(families, list):
            families = []
        for family in families or [row.get("primary_topic_family") or "other"]:
            counts[str(family)] += 1
    return dict(sorted(counts.items(), key=lambda item: (-item[1], item[0])))


def topic_concentration_diagnostics(rows: list[dict[str, Any]]) -> dict[str, Any]:
    if not rows:
        return {
            "topic_concentration_warning": False,
            "topic_concentration_reasons": [],
            "topic_floor_suggestion": [],
            "topic_concentration_rows": [],
        }
    total = len(rows)
    primary_counts = _counter_from_rows(rows, "primary_topic_family")
    source_counts = _counter_from_rows(rows, "source_role")
    reasons: list[str] = []
    diagnostic_rows: list[dict[str, Any]] = []

    for topic, count in primary_counts.items():
        topic_rows = [
            row for row in rows if str(row.get("primary_topic_family") or "other") == topic
        ]
        weakest = min(topic_rows, key=lambda row: _float_value(row.get("board_score")))
        has_weak_ai_row = topic == "ai_tech" and any(
            row.get("generic_visible_copy_warning")
            or str(row.get("seed_readiness_level") or "") == "needs_support"
            for row in topic_rows
        )
        if count >= 4 or (topic == "ai_tech" and count >= 3 and has_weak_ai_row):
            reasons.append(f"{topic} selected {count}/{total}")
            diagnostic_rows.append(
                {
                    "dimension": "primary_topic_family",
                    "topic": topic,
                    "count": count,
                    "weakest_row": str(weakest.get("title") or weakest.get("제목") or ""),
                    "suggested_action": f"consider replacing weakest {topic} row",
                }
            )

    for source_role, count in source_counts.items():
        if count < 5:
            continue
        source_rows = [
            row for row in rows if str(row.get("source_role") or "other") == source_role
        ]
        weakest = min(source_rows, key=lambda row: _float_value(row.get("board_score")))
        reasons.append(f"{source_role} source_role selected {count}/{total}")
        diagnostic_rows.append(
            {
                "dimension": "source_role",
                "topic": source_role,
                "count": count,
                "weakest_row": str(weakest.get("title") or weakest.get("제목") or ""),
                "suggested_action": f"consider replacing weakest {source_role} row",
            }
        )

    return {
        "topic_concentration_warning": bool(reasons),
        "topic_concentration_reasons": reasons,
        "topic_floor_suggestion": [
            row["suggested_action"] for row in diagnostic_rows
        ],
        "topic_concentration_rows": diagnostic_rows,
    }


def _metric_from_payloads(
    key: str,
    *,
    calibration: dict[str, Any],
    board: dict[str, Any],
    rows: list[dict[str, Any]],
) -> int:
    if key in calibration:
        return int(calibration.get(key) or 0)
    if key in board:
        return int(board.get(key) or 0)
    return int(sum(1 for row in rows if row.get(key.replace("_count", ""))))


def replay_quality_for_date(run_date: str) -> dict[str, Any]:
    path_map = _date_paths(run_date)
    metadata = _load_json(path_map["metadata"])
    board = _load_json(path_map["board_score"])
    calibration = _load_json(path_map["calibration"])
    csv_rows = _load_csv_rows(path_map["csv"])
    rows = _metadata_rows(metadata) or _board_rows(board)
    quality_floor_payload = (
        metadata.get("quality_floor")
        if isinstance(metadata.get("quality_floor"), dict)
        else {}
    )
    warnings = [
        f"missing:{name}"
        for name, path in path_map.items()
        if not path.exists()
    ]
    if not rows and csv_rows:
        rows = csv_rows
        warnings.append("metadata_missing_using_csv_only")
    if not rows and not board and not calibration:
        return {
            "date": run_date,
            "available": False,
            "warnings": warnings or ["no_artifacts_found"],
        }

    quality_floor = recommend_quality_floor_visible_rows(rows)
    topic_concentration = topic_concentration_diagnostics(rows)
    selected_count = len(rows) or int(
        calibration.get("selected_count") or board.get("selected_count") or 0
    )
    return {
        "date": run_date,
        "available": True,
        "selected_count": selected_count,
        "main_seed_count": int(
            calibration.get("main_seed_count")
            or sum(1 for row in rows if row.get("editorial_role") == "main_seed")
        ),
        "main_seed_candidate_count": _metric_from_payloads(
            "main_seed_candidate_count",
            calibration=calibration,
            board=board,
            rows=rows,
        ),
        "ready_seed_candidate_count": _metric_from_payloads(
            "ready_seed_candidate_count",
            calibration=calibration,
            board=board,
            rows=rows,
        ),
        "generic_visible_copy_warning_count": int(
            calibration.get("generic_visible_copy_warning_count")
            or board.get("generic_visible_copy_warning_count")
            or sum(1 for row in rows if row.get("generic_visible_copy_warning"))
        ),
        "quality_floor_recommended_visible_count": int(
            quality_floor_payload.get("quality_floor_recommended_visible_count")
            or board.get("quality_floor_recommended_visible_count")
            or calibration.get("quality_floor_recommended_visible_count")
            or quality_floor.get("quality_floor_recommended_visible_count")
            or 0
        ),
        "quality_floor_active": bool(
            quality_floor_payload.get("quality_floor_active")
            or board.get("quality_floor_active")
            or calibration.get("quality_floor_active")
        ),
        "quality_floor_applied": bool(
            quality_floor_payload.get("quality_floor_applied")
            or board.get("quality_floor_applied")
            or calibration.get("quality_floor_applied")
        ),
        "quality_floor_actual_hidden_count": int(
            quality_floor_payload.get("quality_floor_actual_hidden_count")
            or board.get("quality_floor_actual_hidden_count")
            or calibration.get("quality_floor_actual_hidden_count")
            or 0
        ),
        "selected_count_before_quality_floor": int(
            quality_floor_payload.get("selected_count_before_quality_floor")
            or board.get("selected_count_before_quality_floor")
            or calibration.get("selected_count_before_quality_floor")
            or selected_count
        ),
        "quality_floor_preview_recommended_visible_count": int(
            quality_floor.get("quality_floor_recommended_visible_count") or 0
        ),
        "quality_floor_excluded_count": int(
            quality_floor.get("quality_floor_excluded_count") or 0
        ),
        "syuka_concrete_overlap_count": int(
            calibration.get("syuka_concrete_overlap_count")
            or board.get("syuka_concrete_overlap_count")
            or 0
        ),
        "syuka_broad_adjacent_count": int(
            calibration.get("syuka_broad_adjacent_count")
            or board.get("syuka_broad_adjacent_count")
            or 0
        ),
        "syuka_weak_adjacent_count": int(
            calibration.get("syuka_weak_adjacent_count")
            or board.get("syuka_weak_adjacent_count")
            or 0
        ),
        "syuka_false_positive_count": int(
            calibration.get("syuka_false_positive_count")
            or board.get("syuka_false_positive_count")
            or 0
        ),
        "support_missing_count": int(
            calibration.get("support_missing_count")
            or board.get("support_missing_count")
            or sum(1 for row in rows if row.get("support_missing_requirements"))
        ),
        "topic_family_counts": _topic_family_counts(rows),
        "primary_topic_counts": _counter_from_rows(rows, "primary_topic_family"),
        "source_role_counts": _counter_from_rows(rows, "source_role"),
        "warnings": [*warnings, *topic_concentration["topic_concentration_reasons"]],
        **topic_concentration,
    }


def build_quality_replay_report(run_dates: list[str]) -> dict[str, Any]:
    rows = [replay_quality_for_date(run_date) for run_date in run_dates]
    available_rows = [row for row in rows if row.get("available")]
    return {
        "dates": run_dates,
        "available_count": len(available_rows),
        "missing_count": len(rows) - len(available_rows),
        "rows": rows,
    }


def quality_replay_markdown(payload: dict[str, Any]) -> str:
    lines = [
        "# Jibi Quality Replay",
        "",
        f"- available_count: {payload['available_count']}",
        f"- missing_count: {payload['missing_count']}",
        "",
        "## Date Metrics",
        "",
        (
            "| date | selected | main | main candidates | ready candidates | "
            "generic warnings | quality floor | syuka concrete/broad/weak/false | "
            "support missing | warnings |"
        ),
        "| --- | ---: | ---: | ---: | ---: | ---: | ---: | --- | ---: | --- |",
    ]
    for row in payload["rows"]:
        lines.append(
            "| "
            + " | ".join(
                [
                    str(row.get("date", "")),
                    str(row.get("selected_count", 0)),
                    str(row.get("main_seed_count", 0)),
                    str(row.get("main_seed_candidate_count", 0)),
                    str(row.get("ready_seed_candidate_count", 0)),
                    str(row.get("generic_visible_copy_warning_count", 0)),
                    (
                        f"{row.get('quality_floor_recommended_visible_count', 0)}"
                        f" active={str(row.get('quality_floor_active', False)).lower()}"
                        f" hidden={row.get('quality_floor_actual_hidden_count', 0)}"
                    ),
                    "/".join(
                        str(row.get(key, 0))
                        for key in [
                            "syuka_concrete_overlap_count",
                            "syuka_broad_adjacent_count",
                            "syuka_weak_adjacent_count",
                            "syuka_false_positive_count",
                        ]
                    ),
                    str(row.get("support_missing_count", 0)),
                    ", ".join(row.get("warnings", [])) or "-",
                ]
            )
            + " |"
        )
    lines.extend(["", "## Topic Concentration Warnings", ""])
    lines.extend(
        [
            "| date | topic | count | weakest row | suggested action |",
            "| --- | --- | ---: | --- | --- |",
        ]
    )
    emitted = False
    for row in payload["rows"]:
        for item in row.get("topic_concentration_rows", []):
            emitted = True
            lines.append(
                "| "
                + " | ".join(
                    [
                        str(row.get("date", "")),
                        str(item.get("topic", "")),
                        str(item.get("count", 0)),
                        str(item.get("weakest_row", "")).replace("|", "\\|"),
                        str(item.get("suggested_action", "")),
                    ]
                )
                + " |"
            )
    if not emitted:
        lines.append("| none | none | 0 | none | none |")
    return "\n".join(lines) + "\n"


def write_quality_replay_report(
    *,
    run_dates: list[str],
    markdown_path: Path,
    json_path: Path | None = None,
) -> tuple[Path, Path]:
    payload = build_quality_replay_report(run_dates)
    json_out = json_path or markdown_path.with_suffix(".json")
    markdown_path.parent.mkdir(parents=True, exist_ok=True)
    json_out.parent.mkdir(parents=True, exist_ok=True)
    markdown_path.write_text(quality_replay_markdown(payload), encoding="utf-8")
    json_out.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    return markdown_path, json_out


def _parse_dates(value: str) -> list[str]:
    return [item.strip() for item in value.split(",") if item.strip()]


@app.callback(invoke_without_command=True)
def main(
    dates: Annotated[
        str,
        typer.Option(
            "--dates",
            help="Comma-separated Jibi dates to replay, e.g. 2026-05-27,2026-06-01.",
        ),
    ] = "2026-05-27,2026-05-31,2026-06-01",
    output: Annotated[
        Path | None,
        typer.Option("--output", help="Markdown report path."),
    ] = None,
) -> None:
    """Replay local Jibi quality artifacts across multiple dates."""

    run_dates = _parse_dates(dates)
    last_date = run_dates[-1] if run_dates else "unknown"
    markdown_path = output or paths.REPORTS_DIR / f"jibi_quality_replay_{last_date}.md"
    md_path, json_path = write_quality_replay_report(
        run_dates=run_dates,
        markdown_path=markdown_path,
    )
    typer.echo(f"Wrote Jibi quality replay to {md_path} and {json_path}.")
