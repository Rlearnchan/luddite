"""Report-only intake summary for Jibi second-search evidence."""

from __future__ import annotations

import json
from collections import Counter, defaultdict
from datetime import UTC, datetime
from pathlib import Path
from typing import Annotated, Any

import typer
from rich.console import Console

from luddite import paths
from luddite.utils.jsonl import read_jsonl
from luddite.utils.urls import canonicalize_url

app = typer.Typer(no_args_is_help=False)
console = Console()


def compact_text(value: object) -> str:
    return " ".join(str(value or "").split())


def _default_feedback_path(run_date: str) -> Path:
    return paths.REPORTS_DIR / f"jibi_review_feedback_{run_date}.json"


def _default_plan_path(run_date: str) -> Path:
    return paths.REPORTS_DIR / f"jibi_second_search_plan_{run_date}.json"


def _default_local_path(run_date: str) -> Path:
    return paths.REPORTS_DIR / f"jibi_second_search_results_{run_date}.json"


def _default_web_path(run_date: str) -> Path:
    return paths.REPORTS_DIR / f"jibi_second_search_web_{run_date}.json"


def _default_web_inbox_path(run_date: str) -> Path:
    return paths.ARTICLE_INBOX_DIR / f"second_search_{run_date}.jsonl"


def _default_markdown_path(run_date: str) -> Path:
    return paths.REPORTS_DIR / f"jibi_second_search_intake_{run_date}.md"


def _default_json_path(run_date: str) -> Path:
    return paths.REPORTS_DIR / f"jibi_second_search_intake_{run_date}.json"


def _load_json(path: Path) -> tuple[dict[str, Any], str]:
    if not path.exists():
        return {}, "not_run"
    return json.loads(path.read_text(encoding="utf-8")), "loaded"


def _load_jsonl(path: Path) -> tuple[list[dict[str, Any]], str]:
    if not path.exists():
        return [], "not_run"
    return read_jsonl(path), "loaded"


def _index_feedback_rows(payload: dict[str, Any]) -> dict[str, dict[str, Any]]:
    rows = payload.get("rows", [])
    return {
        compact_text(row.get("id") or row.get("ID") or row.get("review_item_id")): row
        for row in rows
        if compact_text(row.get("id") or row.get("ID") or row.get("review_item_id"))
    }


def _index_plan_rows(payload: dict[str, Any]) -> dict[str, dict[str, Any]]:
    return {
        compact_text(row.get("id") or row.get("review_item_id")): row
        for row in payload.get("plans", [])
        if compact_text(row.get("id") or row.get("review_item_id"))
    }


def _index_local_rows(payload: dict[str, Any]) -> dict[str, dict[str, Any]]:
    return {
        compact_text(row.get("id") or row.get("review_item_id")): row
        for row in payload.get("rows", [])
        if compact_text(row.get("id") or row.get("review_item_id"))
    }


def _url(record: dict[str, Any]) -> str:
    return compact_text(
        record.get("url")
        or record.get("source_url_canonical")
        or record.get("link")
        or record.get("seed_url")
    )


def _link_from_local(match: dict[str, Any], row: dict[str, Any]) -> dict[str, Any]:
    return {
        "collector": "second_search_local",
        "evidence_role": "supporting_link_candidate",
        "review_item_id": compact_text(match.get("review_item_id") or row.get("id")),
        "review_title": compact_text(match.get("review_title") or row.get("title")),
        "title": compact_text(match.get("title")),
        "source": compact_text(match.get("source")),
        "url": _url(match),
        "matched_terms": match.get("matched_terms", []),
        "relevance_status": compact_text(match.get("relevance_status"))
        or "accepted_local_match",
        "match_score": match.get("match_score"),
    }


def _link_from_web(record: dict[str, Any]) -> dict[str, Any]:
    return {
        "collector": compact_text(record.get("collector")) or "second_search_web",
        "evidence_role": compact_text(record.get("evidence_role"))
        or "supporting_link_candidate",
        "review_item_id": compact_text(record.get("review_item_id")),
        "review_title": compact_text(record.get("review_title")),
        "title": compact_text(record.get("title")),
        "source": compact_text(record.get("source")),
        "url": _url(record),
        "search_query": compact_text(record.get("search_query")),
        "query_type": compact_text(record.get("query_type")) or "fallback",
        "matched_terms": record.get("matched_terms")
        or record.get("search_relevance_terms", []),
        "relevance_status": compact_text(record.get("relevance_status")) or "accepted",
        "search_rank": record.get("search_rank"),
    }


def _dedupe_links(links: list[dict[str, Any]]) -> list[dict[str, Any]]:
    seen: set[str] = set()
    output = []
    for link in links:
        key = canonicalize_url(_url(link)) or compact_text(link.get("title"))
        if not key or key in seen:
            continue
        seen.add(key)
        output.append(link)
    return output


def _web_records(
    web_payload: dict[str, Any],
    inbox_records: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    records = list(web_payload.get("records", [])) + inbox_records
    return _dedupe_links(records)


def _web_rejected_by_id(web_payload: dict[str, Any]) -> dict[str, int]:
    counts: dict[str, int] = defaultdict(int)
    for run in web_payload.get("query_runs", []):
        row_id = compact_text(run.get("review_item_id"))
        if not row_id:
            continue
        counts[row_id] += int(run.get("rejected_low_relevance") or 0)
    return dict(counts)


def _web_returned_by_id(web_payload: dict[str, Any]) -> dict[str, int]:
    counts: dict[str, int] = defaultdict(int)
    for run in web_payload.get("query_runs", []):
        row_id = compact_text(run.get("review_item_id"))
        if not row_id:
            continue
        counts[row_id] += int(run.get("returned") or 0)
    return dict(counts)


def _feedback_lesson(row_id: str, feedback_rows: dict[str, dict[str, Any]]) -> str:
    row = feedback_rows.get(row_id, {})
    return compact_text(row.get("operator_lesson"))


def _follow_up_status(
    *,
    priority: str,
    actions: list[str],
    accepted_count: int,
    rejected_low_relevance_count: int,
    web_returned_count: int,
) -> str:
    action_set = set(actions)
    if "demote_to_evidence_or_background" in action_set:
        return "evidence_only"
    if priority == "low" and action_set.intersection(
        {
            "avoid_market_advice_frame",
            "demote_or_reject",
            "reject_or_defer",
        }
    ):
        return "reject_or_defer"
    if accepted_count >= 2:
        return "enough_supporting_links"
    if accepted_count == 0:
        return "still_needs_sources"
    if rejected_low_relevance_count or web_returned_count <= accepted_count:
        return "needs_broader_query"
    return "still_needs_sources"


def build_second_search_intake(
    *,
    run_date: str,
    feedback_payload: dict[str, Any],
    plan_payload: dict[str, Any],
    local_payload: dict[str, Any],
    web_payload: dict[str, Any],
    web_inbox_records: list[dict[str, Any]],
    input_status: dict[str, str],
) -> dict[str, Any]:
    feedback_rows = _index_feedback_rows(feedback_payload)
    plan_rows = _index_plan_rows(plan_payload)
    local_rows = _index_local_rows(local_payload)
    web_records_by_id: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for record in _web_records(web_payload, web_inbox_records):
        row_id = compact_text(record.get("review_item_id"))
        if row_id:
            web_records_by_id[row_id].append(record)
    rejected_by_id = _web_rejected_by_id(web_payload)
    returned_by_id = _web_returned_by_id(web_payload)
    row_ids = list(
        dict.fromkeys(
            [
                *plan_rows.keys(),
                *feedback_rows.keys(),
                *local_rows.keys(),
                *web_records_by_id.keys(),
            ]
        )
    )
    rows: list[dict[str, Any]] = []
    for row_id in row_ids:
        plan = plan_rows.get(row_id, {})
        local = local_rows.get(row_id, {})
        web_links = [_link_from_web(record) for record in web_records_by_id.get(row_id, [])]
        local_links = [
            _link_from_local(match, local)
            for match in local.get("top_matches", [])
        ]
        accepted_links = _dedupe_links([*local_links, *web_links])
        priority = compact_text(plan.get("priority") or local.get("priority"))
        actions = [
            compact_text(action)
            for action in (plan.get("actions") or local.get("actions") or [])
            if compact_text(action)
        ]
        review_title = compact_text(
            plan.get("title")
            or local.get("title")
            or feedback_rows.get(row_id, {}).get("title")
        )
        rejected_count = int(rejected_by_id.get(row_id, 0))
        returned_count = int(returned_by_id.get(row_id, 0))
        follow_up_status = _follow_up_status(
            priority=priority,
            actions=actions,
            accepted_count=len(accepted_links),
            rejected_low_relevance_count=rejected_count,
            web_returned_count=returned_count,
        )
        rows.append(
            {
                "review_item_id": row_id,
                "review_title": review_title,
                "priority": priority,
                "original_review_lesson": compact_text(plan.get("why_search"))
                or _feedback_lesson(row_id, feedback_rows),
                "actions": actions,
                "local_supporting_matches_count": len(local_links),
                "web_supporting_matches_count": len(web_links),
                "accepted_links": accepted_links,
                "rejected_low_relevance_count": rejected_count,
                "web_returned_count": returned_count,
                "follow_up_status": follow_up_status,
            }
        )
    status_counts = Counter(row["follow_up_status"] for row in rows)
    return {
        "run_date": run_date,
        "generated_at": datetime.now(UTC).isoformat(),
        "input_status": input_status,
        "row_count": len(rows),
        "follow_up_status_counts": dict(status_counts),
        "rows": rows,
    }


def _table_cell(value: object) -> str:
    return compact_text(value).replace("|", "\\|") or "-"


def render_markdown(payload: dict[str, Any]) -> str:
    lines = [
        f"# Jibi Second-Search Evidence Intake — {payload['run_date']}",
        "",
        f"- Generated at: `{payload['generated_at']}`",
        f"- Rows: {payload['row_count']}",
        "",
        "## Input Status",
        "",
    ]
    for key, status in payload["input_status"].items():
        lines.append(f"- {key}: `{status}`")
    lines.extend(["", "## Follow-Up Status Counts", ""])
    for status, count in sorted(payload.get("follow_up_status_counts", {}).items()):
        lines.append(f"- {status}: {count}")
    lines.extend(
        [
            "",
            "## Intake Summary",
            "",
            "| status | title | actions | local | web | rejected | first link |",
            "| --- | --- | --- | ---: | ---: | ---: | --- |",
        ]
    )
    for row in payload["rows"]:
        first_link = row["accepted_links"][0] if row["accepted_links"] else {}
        first_label = (
            f"{first_link.get('source', '')}: {first_link.get('title', '')}"
            if first_link
            else "none"
        )
        lines.append(
            "| "
            + " | ".join(
                [
                    _table_cell(row["follow_up_status"]),
                    _table_cell(row["review_title"]),
                    _table_cell(", ".join(row["actions"])),
                    str(row["local_supporting_matches_count"]),
                    str(row["web_supporting_matches_count"]),
                    str(row["rejected_low_relevance_count"]),
                    _table_cell(first_label),
                ]
            )
            + " |"
        )
    lines.extend(["", "## Detail", ""])
    for row in payload["rows"]:
        lines.append(f"### {row['review_title'] or row['review_item_id']}")
        lines.append("")
        lines.append(f"- ID: `{row['review_item_id']}`")
        lines.append(f"- follow_up_status: `{row['follow_up_status']}`")
        lines.append(f"- original_review_lesson: {row['original_review_lesson'] or 'none'}")
        lines.append(
            "- counts: "
            f"local={row['local_supporting_matches_count']}, "
            f"web={row['web_supporting_matches_count']}, "
            f"rejected_low_relevance={row['rejected_low_relevance_count']}"
        )
        if not row["accepted_links"]:
            lines.append("- accepted_links: none")
            lines.append("")
            continue
        lines.append("- accepted_links:")
        for link in row["accepted_links"]:
            title = _table_cell(link.get("title"))
            url = compact_text(link.get("url"))
            source = _table_cell(link.get("source"))
            collector = _table_cell(link.get("collector"))
            lines.append(f"  - {collector} / {source}: [{title}]({url})")
            if link.get("query_type") or link.get("search_query"):
                lines.append(
                    "    - query: "
                    f"`{link.get('query_type', 'fallback')}` "
                    f"{_table_cell(link.get('search_query'))}"
                )
            if link.get("matched_terms"):
                lines.append(
                    f"    - matched_terms: `{', '.join(link['matched_terms'])}`"
                )
        lines.append("")
    return "\n".join(lines).rstrip() + "\n"


def write_second_search_intake(
    *,
    run_date: str,
    feedback_path: Path,
    plan_path: Path,
    local_path: Path,
    web_path: Path,
    web_inbox_path: Path,
    markdown_path: Path,
    json_path: Path,
) -> tuple[Path, Path, dict[str, Any]]:
    feedback_payload, feedback_status = _load_json(feedback_path)
    plan_payload, plan_status = _load_json(plan_path)
    local_payload, local_status = _load_json(local_path)
    web_payload, web_status = _load_json(web_path)
    web_inbox_records, web_inbox_status = _load_jsonl(web_inbox_path)
    payload = build_second_search_intake(
        run_date=run_date,
        feedback_payload=feedback_payload,
        plan_payload=plan_payload,
        local_payload=local_payload,
        web_payload=web_payload,
        web_inbox_records=web_inbox_records,
        input_status={
            "feedback": feedback_status,
            "plan": plan_status,
            "local": local_status,
            "web": web_status,
            "web_inbox": web_inbox_status,
        },
    )
    payload["paths"] = {
        "feedback": str(feedback_path),
        "plan": str(plan_path),
        "local": str(local_path),
        "web": str(web_path),
        "web_inbox": str(web_inbox_path),
    }
    markdown_path.parent.mkdir(parents=True, exist_ok=True)
    json_path.parent.mkdir(parents=True, exist_ok=True)
    markdown_path.write_text(render_markdown(payload), encoding="utf-8")
    json_path.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    return markdown_path, json_path, payload


@app.command("main")
def main(
    date: Annotated[str, typer.Option("--date", help="Jibi run date YYYY-MM-DD.")] = "",
    feedback: Annotated[
        Path | None,
        typer.Option("--feedback", help="Review feedback JSON report."),
    ] = None,
    plan: Annotated[
        Path | None,
        typer.Option("--plan", help="Second-search plan JSON."),
    ] = None,
    local: Annotated[
        Path | None,
        typer.Option("--local", help="Local second-search JSON."),
    ] = None,
    web: Annotated[
        Path | None,
        typer.Option("--web", help="Web second-search JSON."),
    ] = None,
    web_inbox: Annotated[
        Path | None,
        typer.Option("--web-inbox", help="Web second-search article JSONL."),
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
    md_path, json_path, payload = write_second_search_intake(
        run_date=run_date,
        feedback_path=feedback or _default_feedback_path(run_date),
        plan_path=plan or _default_plan_path(run_date),
        local_path=local or _default_local_path(run_date),
        web_path=web or _default_web_path(run_date),
        web_inbox_path=web_inbox or _default_web_inbox_path(run_date),
        markdown_path=markdown or _default_markdown_path(run_date),
        json_path=output_json or _default_json_path(run_date),
    )
    console.print(
        "[green]Wrote Jibi second-search intake "
        f"({payload['row_count']} rows): {md_path} / {json_path}[/green]"
    )


if __name__ == "__main__":
    typer.run(main)
