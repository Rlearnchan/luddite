"""Join pre-review hidden support search with post-review feedback."""

from __future__ import annotations

import json
from collections import Counter
from datetime import UTC, datetime
from pathlib import Path
from typing import Annotated, Any

import typer
from rich.console import Console

from luddite import paths

app = typer.Typer(no_args_is_help=False)
console = Console()


def compact_text(value: object) -> str:
    return " ".join(str(value or "").split())


def default_feedback_path(run_date: str) -> Path:
    return paths.REPORTS_DIR / f"jibi_review_feedback_{run_date}.json"


def default_hidden_support_path(run_date: str) -> Path:
    return paths.REPORTS_DIR / f"jibi_hidden_support_search_{run_date}.json"


def default_markdown_path(run_date: str) -> Path:
    return paths.REPORTS_DIR / f"jibi_hidden_support_intake_{run_date}.md"


def default_json_path(run_date: str) -> Path:
    return paths.REPORTS_DIR / f"jibi_hidden_support_intake_{run_date}.json"


def _load_json(path: Path) -> tuple[dict[str, Any], str]:
    if not path.exists():
        return {}, "not_run"
    return json.loads(path.read_text(encoding="utf-8")), "loaded"


def _row_id(row: dict[str, Any]) -> str:
    return compact_text(row.get("id") or row.get("ID") or row.get("review_item_id"))


def _index_rows(payload: dict[str, Any]) -> dict[str, dict[str, Any]]:
    rows = payload.get("rows") or []
    return {_row_id(row): row for row in rows if _row_id(row)}


def _as_list(value: object) -> list[str]:
    if isinstance(value, list):
        return [compact_text(item) for item in value if compact_text(item)]
    if isinstance(value, tuple):
        return [compact_text(item) for item in value if compact_text(item)]
    text = compact_text(value)
    if not text:
        return []
    return [item.strip() for item in text.split(",") if item.strip()]


def _review_notes(row: dict[str, Any]) -> list[str]:
    reviewers = row.get("reviewers") or {}
    notes = []
    if isinstance(reviewers, dict):
        for value in reviewers.values():
            if isinstance(value, dict):
                note = compact_text(value.get("raw_note") or value.get("note"))
                if note and note != "(blank)":
                    notes.append(note)
    return notes


def _review_need_flags(row: dict[str, Any]) -> list[str]:
    failures = set(_as_list(row.get("row_failure_modes")))
    positives = set(_as_list(row.get("row_positive_signals")))
    actions = set(_as_list(row.get("row_next_research_actions")))
    text = " ".join(_review_notes(row))
    needs: list[str] = []
    if failures.intersection({"needs_supporting_links"}) or actions.intersection(
        {"find_supporting_links"}
    ):
        needs.append("supporting_links")
    if positives.intersection({"specific_case_needed"}) or actions.intersection(
        {"find_specific_case_or_odd_hook"}
    ):
        needs.append("specific_case_or_odd_hook")
    if failures.intersection({"too_familiar"}) or actions.intersection(
        {"check_past_topic_differentiation"}
    ):
        needs.append("differentiate_from_past_topics")
    if failures.intersection({"weak_audience_bridge"}):
        needs.append("audience_bridge")
    if "통계" in text or "여론조사" in text or "정책" in text:
        needs.append("numbers_policy_or_poll")
    if "한국" in text or "전동 킥보드" in text:
        needs.append("korea_bridge")
    return list(dict.fromkeys(needs))


def _selected_links(hidden_row: dict[str, Any]) -> list[dict[str, Any]]:
    details = hidden_row.get("selected_link_details") or []
    if isinstance(details, list):
        return [item for item in details if isinstance(item, dict)]
    return []


def _support_status(
    *,
    feedback_row: dict[str, Any] | None,
    hidden_row: dict[str, Any] | None,
    input_status: dict[str, str],
) -> str:
    if input_status.get("hidden_support") != "loaded":
        return "hidden_support_not_run"
    if not feedback_row:
        return "no_review_feedback"
    if not _review_notes(feedback_row):
        return "no_review_feedback"
    selected_count = len(_selected_links(hidden_row or {}))
    needs = set(_review_need_flags(feedback_row))
    failures = set(_as_list(feedback_row.get("row_failure_modes")))
    positives = set(_as_list(feedback_row.get("row_positive_signals")))
    review_signal = compact_text(feedback_row.get("row_review_signal"))
    if "audience_bridge" in needs:
        return "do_not_rescue_with_links_only"
    if "differentiate_from_past_topics" in needs:
        if selected_count:
            return "support_exists_but_needs_new_angle_check"
        return "needs_new_angle_not_more_links"
    if needs.intersection({"supporting_links", "specific_case_or_odd_hook"}):
        if selected_count >= 2:
            return "hidden_support_can_test_review_need"
        if selected_count == 1:
            return "partial_support_can_test_review_need"
        return "still_needs_targeted_search"
    if needs.intersection({"numbers_policy_or_poll", "korea_bridge"}):
        if selected_count:
            return "support_available_needs_relevance_review"
        return "still_needs_targeted_search"
    if positives.intersection({"fresh_angle", "promising_hook", "good_question"}):
        if selected_count:
            return "hidden_support_available_for_promising_hook"
        return "promising_hook_needs_support_search"
    if review_signal in {"reject", "weak"} or failures:
        if selected_count:
            return "support_available_but_review_weak"
        return "review_weak_no_support"
    if selected_count:
        return "background_support_available"
    return "no_hidden_support_found"


def _next_step(status: str) -> str:
    return {
        "hidden_support_not_run": "run_hidden_support_search_before_next_board",
        "no_review_feedback": "wait_for_review_or_ignore",
        "do_not_rescue_with_links_only": "suppress_or_reframe_for_audience_bridge",
        "support_exists_but_needs_new_angle_check": "inspect_links_for_new_frame",
        "needs_new_angle_not_more_links": "search_for_differentiating_angle",
        "hidden_support_can_test_review_need": "use_hidden_links_for_followup_pack",
        "partial_support_can_test_review_need": "run_second_search_for_one_more_case",
        "still_needs_targeted_search": "run_second_search_for_specific_cases",
        "support_available_needs_relevance_review": "inspect_links_before_reusing",
        "hidden_support_available_for_promising_hook": "use_hidden_links_for_enrichment",
        "promising_hook_needs_support_search": "run_second_search_for_promising_hook",
        "support_available_but_review_weak": "do_not_repost_without_new_frame",
        "review_weak_no_support": "suppress_or_hold",
        "background_support_available": "keep_as_background_evidence",
        "no_hidden_support_found": "no_action",
    }.get(status, "review_manually")


def build_hidden_support_intake(
    *,
    run_date: str,
    feedback_payload: dict[str, Any],
    hidden_support_payload: dict[str, Any],
    input_status: dict[str, str],
) -> dict[str, Any]:
    feedback_rows = _index_rows(feedback_payload)
    hidden_rows = _index_rows(hidden_support_payload)
    row_ids = sorted(set(feedback_rows) | set(hidden_rows))
    rows: list[dict[str, Any]] = []
    for row_id in row_ids:
        feedback_row = feedback_rows.get(row_id)
        hidden_row = hidden_rows.get(row_id)
        status = _support_status(
            feedback_row=feedback_row,
            hidden_row=hidden_row,
            input_status=input_status,
        )
        links = _selected_links(hidden_row or {})
        rows.append(
            {
                "review_item_id": row_id,
                "review_title": compact_text(
                    (feedback_row or {}).get("title")
                    or (hidden_row or {}).get("review_title")
                ),
                "row_review_signal": compact_text(
                    (feedback_row or {}).get("row_review_signal")
                ),
                "review_needs": _review_need_flags(feedback_row or {}),
                "row_failure_modes": _as_list(
                    (feedback_row or {}).get("row_failure_modes")
                ),
                "row_positive_signals": _as_list(
                    (feedback_row or {}).get("row_positive_signals")
                ),
                "row_next_research_actions": _as_list(
                    (feedback_row or {}).get("row_next_research_actions")
                ),
                "operator_lesson": compact_text(
                    (feedback_row or {}).get("operator_lesson")
                ),
                "review_notes_count": len(_review_notes(feedback_row or {})),
                "hidden_support_status": compact_text(
                    (hidden_row or {}).get("hidden_support_status")
                )
                or "not_run",
                "hidden_selected_count": len(links),
                "hidden_accepted_count": int((hidden_row or {}).get("accepted_count") or 0),
                "hidden_rejected_low_relevance_count": int(
                    (hidden_row or {}).get("rejected_low_relevance_count") or 0
                ),
                "selected_links": links,
                "review_support_status": status,
                "recommended_next_step": _next_step(status),
            }
        )
    status_counts = Counter(row["review_support_status"] for row in rows)
    need_counts = Counter(need for row in rows for need in row["review_needs"])
    return {
        "run_date": run_date,
        "generated_at": datetime.now(UTC).isoformat(),
        "input_status": input_status,
        "rows": rows,
        "total_rows": len(rows),
        "rows_with_review_notes": sum(1 for row in rows if row["review_notes_count"]),
        "rows_with_hidden_support": sum(
            1 for row in rows if row["hidden_selected_count"]
        ),
        "review_support_status_counts": dict(sorted(status_counts.items())),
        "review_need_counts": dict(sorted(need_counts.items())),
    }


def render_markdown(payload: dict[str, Any]) -> str:
    lines = [
        f"# Jibi Hidden Support Intake — {payload['run_date']}",
        "",
        f"- Generated at: `{payload['generated_at']}`",
        f"- Total rows: {payload['total_rows']}",
        f"- Rows with review notes: {payload['rows_with_review_notes']}",
        f"- Rows with hidden support: {payload['rows_with_hidden_support']}",
        "",
        "## Status Counts",
        "",
    ]
    for key, value in payload.get("review_support_status_counts", {}).items():
        lines.append(f"- {key}: {value}")
    lines.extend(["", "## Review Need Counts", ""])
    for key, value in payload.get("review_need_counts", {}).items():
        lines.append(f"- {key}: {value}")
    lines.extend(
        [
            "",
            "## Operator Table",
            "",
            "| status | title | review needs | hidden links | next step |",
            "| --- | --- | --- | ---: | --- |",
        ]
    )
    for row in payload.get("rows", []):
        lines.append(
            "| "
            + " | ".join(
                [
                    _table_cell(row.get("review_support_status")),
                    _table_cell(row.get("review_title")),
                    _table_cell(", ".join(row.get("review_needs") or []) or "-"),
                    str(row.get("hidden_selected_count") or 0),
                    _table_cell(row.get("recommended_next_step")),
                ]
            )
            + " |"
        )
    lines.extend(["", "## Detail", ""])
    for row in payload.get("rows", []):
        lines.append(f"### {row.get('review_title') or row.get('review_item_id')}")
        lines.append("")
        lines.append(f"- ID: `{row.get('review_item_id')}`")
        lines.append(f"- review_support_status: `{row.get('review_support_status')}`")
        lines.append(f"- recommended_next_step: `{row.get('recommended_next_step')}`")
        lines.append(f"- operator_lesson: {row.get('operator_lesson') or '-'}")
        lines.append(
            "- review_needs: "
            + (", ".join(row.get("review_needs") or []) or "none")
        )
        lines.append(f"- hidden_support_status: `{row.get('hidden_support_status')}`")
        if row.get("selected_links"):
            lines.append("- hidden selected links:")
            for link in row["selected_links"]:
                title = compact_text(link.get("title")) or compact_text(link.get("url"))
                lines.append(f"  - [{title}]({link.get('url')})")
                lines.append(
                    "    - "
                    f"source: `{compact_text(link.get('source'))}`, "
                    f"query_type: `{compact_text(link.get('query_type'))}`, "
                    f"score: {link.get('usefulness_score')}"
                )
                if link.get("usefulness_reason"):
                    lines.append(f"    - reason: {link.get('usefulness_reason')}")
        else:
            lines.append("- hidden selected links: none")
        lines.append("")
    return "\n".join(lines).rstrip() + "\n"


def write_hidden_support_intake(
    *,
    run_date: str,
    feedback_path: Path,
    hidden_support_path: Path,
    markdown_path: Path,
    json_path: Path,
) -> tuple[Path, Path, dict[str, Any]]:
    feedback_payload, feedback_status = _load_json(feedback_path)
    hidden_payload, hidden_status = _load_json(hidden_support_path)
    payload = build_hidden_support_intake(
        run_date=run_date,
        feedback_payload=feedback_payload,
        hidden_support_payload=hidden_payload,
        input_status={
            "feedback": feedback_status,
            "hidden_support": hidden_status,
        },
    )
    payload["feedback_path"] = str(feedback_path)
    payload["hidden_support_path"] = str(hidden_support_path)
    markdown_path.parent.mkdir(parents=True, exist_ok=True)
    json_path.parent.mkdir(parents=True, exist_ok=True)
    markdown_path.write_text(render_markdown(payload), encoding="utf-8")
    json_path.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    return markdown_path, json_path, payload


def _table_cell(value: object) -> str:
    return compact_text(value).replace("|", "\\|") or "-"


@app.callback(invoke_without_command=True)
def main(
    date: Annotated[str, typer.Option("--date", help="Jibi run date YYYY-MM-DD.")] = "",
    feedback: Annotated[
        Path | None,
        typer.Option("--feedback", help="Jibi review feedback JSON."),
    ] = None,
    hidden_support: Annotated[
        Path | None,
        typer.Option("--hidden-support", help="Jibi hidden support search JSON."),
    ] = None,
    markdown: Annotated[
        Path | None,
        typer.Option("--markdown", help="Output markdown path."),
    ] = None,
    output_json: Annotated[
        Path | None,
        typer.Option("--json", help="Output JSON path."),
    ] = None,
) -> None:
    run_date = date or datetime.now().strftime("%Y-%m-%d")
    md_path, json_path, payload = write_hidden_support_intake(
        run_date=run_date,
        feedback_path=feedback or default_feedback_path(run_date),
        hidden_support_path=hidden_support or default_hidden_support_path(run_date),
        markdown_path=markdown or default_markdown_path(run_date),
        json_path=output_json or default_json_path(run_date),
    )
    console.print(
        "[green]Wrote Jibi hidden support intake "
        f"for {payload['total_rows']} rows: {md_path} / {json_path}[/green]"
    )


if __name__ == "__main__":
    app()
