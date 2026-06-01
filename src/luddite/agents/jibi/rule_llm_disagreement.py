"""Report rule-vs-LLM disagreements for Jibi evidence-first runs."""

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

MAIN_ROLES = {"main_seed", "main_seed_candidate"}
WEAK_ROLES = {"sub_block", "hook_only", "evidence", "reject"}


def _load_json(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {}
    payload = json.loads(path.read_text(encoding="utf-8"))
    return payload if isinstance(payload, dict) else {}


def _by_bundle_id(items: list[dict[str, Any]]) -> dict[str, dict[str, Any]]:
    return {str(item.get("story_bundle_id") or ""): item for item in items}


def _rule_role(item: dict[str, Any]) -> str:
    raw_diagnostics = item.get("rule_diagnostics")
    diagnostics = raw_diagnostics if isinstance(raw_diagnostics, dict) else {}
    if diagnostics.get("ready_seed_candidate"):
        return "ready_seed_candidate"
    if diagnostics.get("main_seed_candidate"):
        return "main_seed_candidate"
    role = str(item.get("editorial_role") or diagnostics.get("selection_lesson_role") or "")
    return role or "unknown"


def _rule_is_main_candidate(item: dict[str, Any]) -> bool:
    raw_diagnostics = item.get("rule_diagnostics")
    diagnostics = raw_diagnostics if isinstance(raw_diagnostics, dict) else {}
    if diagnostics.get("ready_seed_candidate") or diagnostics.get("main_seed_candidate"):
        return True
    return _rule_role(item) in {"main_seed", "ready_seed_candidate", "main_seed_candidate"}


def _rule_is_weak_or_blocking(item: dict[str, Any]) -> bool:
    raw_diagnostics = item.get("rule_diagnostics")
    diagnostics = raw_diagnostics if isinstance(raw_diagnostics, dict) else {}
    if diagnostics.get("generic_visible_copy_warning"):
        return True
    if diagnostics.get("selection_lesson_role") == "suppress":
        return True
    if diagnostics.get("support_status") == "missing" and diagnostics.get(
        "critical_support_requirements"
    ):
        return True
    return _rule_role(item) in {"sub_block", "hook_only", "evidence", "reject", "suppress"}


def _judge_role(row: dict[str, Any]) -> str:
    return str(row.get("llm_editorial_role") or "unknown")


def _judge_is_main_candidate(row: dict[str, Any]) -> bool:
    return _judge_role(row) in MAIN_ROLES


def _judge_is_weak(row: dict[str, Any]) -> bool:
    return _judge_role(row) in WEAK_ROLES


def _disagreement_reasons(row: dict[str, Any]) -> list[str]:
    disagreement = row.get("rule_disagreement")
    if not isinstance(disagreement, dict):
        return []
    return [str(item) for item in disagreement.get("reasons") or []]


def _summary_row(
    *,
    evidence_item: dict[str, Any],
    judge_row: dict[str, Any],
    category: str,
) -> dict[str, Any]:
    return {
        "category": category,
        "story_bundle_id": evidence_item.get("story_bundle_id") or judge_row.get("story_bundle_id"),
        "review_item_id": evidence_item.get("review_item_id") or "",
        "title": evidence_item.get("visible_title") or judge_row.get("visible_title") or "",
        "rule_role": _rule_role(evidence_item),
        "llm_role": _judge_role(judge_row),
        "llm_confidence": judge_row.get("llm_confidence") or "",
        "board_score": evidence_item.get("board_score") or judge_row.get("board_score"),
        "rule_main_seed_candidate": _rule_is_main_candidate(evidence_item),
        "llm_opening_question": judge_row.get("opening_question") or "",
        "missing_evidence": judge_row.get("missing_evidence") or [],
        "disagreement_reasons": _disagreement_reasons(judge_row),
    }


def build_rule_llm_disagreement_report(
    *,
    evidence_pack_path: Path,
    llm_judge_path: Path,
) -> dict[str, Any]:
    evidence_pack = _load_json(evidence_pack_path)
    llm_judge = _load_json(llm_judge_path)
    evidence_by_id = _by_bundle_id(
        [item for item in evidence_pack.get("items", []) if isinstance(item, dict)]
    )
    rows: list[dict[str, Any]] = []
    for judge_row in llm_judge.get("items", []):
        if not isinstance(judge_row, dict):
            continue
        evidence_item = evidence_by_id.get(str(judge_row.get("story_bundle_id") or ""), {})
        if not evidence_item:
            continue
        rule_main = _rule_is_main_candidate(evidence_item)
        llm_main = _judge_is_main_candidate(judge_row)
        if not rule_main and llm_main:
            category = "rule_rejected_llm_rescued"
        elif rule_main and _judge_is_weak(judge_row):
            category = "rule_promoted_llm_lowered"
        elif rule_main and llm_main:
            category = "both_agree_main_candidate"
        elif _rule_is_weak_or_blocking(evidence_item) and _judge_is_weak(judge_row):
            category = "both_agree_weak"
        else:
            category = "other"
        row = _summary_row(
            evidence_item=evidence_item,
            judge_row=judge_row,
            category=category,
        )
        if row["missing_evidence"] and row["llm_role"] in {
            "main_seed_candidate",
            "sub_block",
            "hook_only",
        }:
            row["evidence_missing_but_salvageable"] = True
        rows.append(row)
    counts = Counter(row["category"] for row in rows)
    return {
        "run_date": evidence_pack.get("run_date") or llm_judge.get("run_date") or "",
        "evidence_pack_path": str(evidence_pack_path),
        "llm_judge_path": str(llm_judge_path),
        "row_count": len(rows),
        "category_counts": dict(counts),
        "evidence_missing_but_salvageable_count": sum(
            1 for row in rows if row.get("evidence_missing_but_salvageable")
        ),
        "rows": rows,
    }


def _table_cell(value: object, *, limit: int = 140) -> str:
    if isinstance(value, list):
        text = "; ".join(str(item) for item in value)
    else:
        text = str(value or "")
    text = " ".join(text.split())
    if len(text) > limit:
        text = text[: limit - 3].rstrip() + "..."
    return text.replace("|", "\\|")


def _section_rows(rows: list[dict[str, Any]], category: str) -> list[str]:
    lines = [
        "| title | rule role | llm role | board_score | why | missing evidence |",
        "| --- | --- | --- | ---: | --- | --- |",
    ]
    filtered = [row for row in rows if row.get("category") == category]
    for row in filtered:
        lines.append(
            "| "
            + " | ".join(
                [
                    _table_cell(row.get("title")),
                    _table_cell(row.get("rule_role")),
                    _table_cell(row.get("llm_role")),
                    str(row.get("board_score") or 0),
                    _table_cell(row.get("disagreement_reasons")),
                    _table_cell(row.get("missing_evidence")),
                ]
            )
            + " |"
        )
    if not filtered:
        lines.append("| none | none | none | 0 | none | none |")
    return lines


def write_rule_llm_disagreement_report(
    *,
    payload: dict[str, Any],
    output_json: Path,
    output_md: Path,
) -> None:
    output_json.parent.mkdir(parents=True, exist_ok=True)
    output_md.parent.mkdir(parents=True, exist_ok=True)
    output_json.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    lines = [
        f"# Jibi Rule vs LLM Disagreement — {payload.get('run_date')}",
        "",
        "## Summary",
        "",
        f"- row_count: {payload.get('row_count', 0)}",
        "- evidence_missing_but_salvageable_count: "
        f"{payload.get('evidence_missing_but_salvageable_count', 0)}",
    ]
    for category, count in sorted(payload.get("category_counts", {}).items()):
        lines.append(f"- {category}: {count}")
    sections = [
        ("Rule Rejected, LLM Rescued", "rule_rejected_llm_rescued"),
        ("Rule Promoted, LLM Lowered", "rule_promoted_llm_lowered"),
        ("Both Agree Main Candidate", "both_agree_main_candidate"),
        ("Both Agree Weak", "both_agree_weak"),
    ]
    for title, category in sections:
        lines.extend(["", f"## {title}", "", *_section_rows(payload.get("rows", []), category)])
    salvageable = [
        row for row in payload.get("rows", []) if row.get("evidence_missing_but_salvageable")
    ]
    lines.extend(
        [
            "",
            "## Evidence Missing But Salvageable",
            "",
            "| title | llm role | missing evidence | opening question |",
            "| --- | --- | --- | --- |",
        ]
    )
    for row in salvageable:
        lines.append(
            "| "
            + " | ".join(
                [
                    _table_cell(row.get("title")),
                    _table_cell(row.get("llm_role")),
                    _table_cell(row.get("missing_evidence")),
                    _table_cell(row.get("llm_opening_question")),
                ]
            )
            + " |"
        )
    if not salvageable:
        lines.append("| none | none | none | none |")
    lines.append("")
    output_md.write_text("\n".join(lines), encoding="utf-8")


def run_rule_llm_disagreement_report(
    *,
    run_date: str,
    evidence_pack_path: Path | None = None,
    llm_judge_path: Path | None = None,
    output_json: Path | None = None,
    output_md: Path | None = None,
) -> tuple[Path, Path, dict[str, Any]]:
    evidence_path = evidence_pack_path or paths.REPORTS_DIR / f"jibi_evidence_pack_{run_date}.json"
    judge_path = llm_judge_path or paths.REPORTS_DIR / f"jibi_llm_editorial_judge_{run_date}.json"
    payload = build_rule_llm_disagreement_report(
        evidence_pack_path=evidence_path,
        llm_judge_path=judge_path,
    )
    json_path = output_json or paths.REPORTS_DIR / f"jibi_rule_llm_disagreement_{run_date}.json"
    md_path = output_md or paths.REPORTS_DIR / f"jibi_rule_llm_disagreement_{run_date}.md"
    write_rule_llm_disagreement_report(payload=payload, output_json=json_path, output_md=md_path)
    return json_path, md_path, payload


@app.callback(invoke_without_command=True)
def main(
    date_text: Annotated[
        str | None,
        typer.Option("--date", help="Run date for default input/output filenames."),
    ] = None,
    evidence_pack_path: Annotated[
        Path | None,
        typer.Option("--evidence-pack", help="Jibi evidence pack JSON."),
    ] = None,
    llm_judge_path: Annotated[
        Path | None,
        typer.Option("--llm-judge", help="Jibi LLM editorial judge JSON."),
    ] = None,
    output_json: Annotated[
        Path | None,
        typer.Option("--output-json", help="Disagreement JSON output."),
    ] = None,
    output_md: Annotated[
        Path | None,
        typer.Option("--output-md", help="Disagreement Markdown output."),
    ] = None,
) -> None:
    run_date = date_text or datetime.now(UTC).date().isoformat()
    json_path, md_path, payload = run_rule_llm_disagreement_report(
        run_date=run_date,
        evidence_pack_path=evidence_pack_path,
        llm_judge_path=llm_judge_path,
        output_json=output_json,
        output_md=output_md,
    )
    console.print(
        "[green]Wrote Jibi rule-vs-LLM disagreement report "
        f"({payload['row_count']} rows) to {json_path} and {md_path}.[/green]"
    )


if __name__ == "__main__":
    app()
