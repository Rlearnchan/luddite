"""Report-only LLM editorial judge for Jibi evidence packs."""

from __future__ import annotations

import json
import os
from collections import Counter
from datetime import UTC, datetime
from pathlib import Path
from typing import Annotated, Any, Protocol

import typer
from rich.console import Console

from luddite import paths
from luddite.agents.jibi.llm_client import (
    OpenAIResponsesClient,
    is_jibi_llm_enabled,
    jibi_llm_model,
    parse_json_object,
)

app = typer.Typer(no_args_is_help=False)
console = Console()

EDITORIAL_ROLES = {
    "main_seed",
    "main_seed_candidate",
    "sub_block",
    "hook_only",
    "evidence",
    "reject",
}
CONFIDENCE_VALUES = {"high", "medium", "low"}


class LlmJsonClient(Protocol):
    model: str

    def json_response(
        self,
        prompt: str,
        *,
        timeout_seconds: int = 120,
        max_output_tokens: int = 1200,
    ) -> tuple[str, dict[str, Any]]:
        """Return JSON text plus raw response payload."""


def _compact_json(value: Any, *, limit: int = 9000) -> str:
    text = json.dumps(value, ensure_ascii=False, sort_keys=True)
    if len(text) <= limit:
        return text
    return text[: limit - 3] + "..."


def build_judge_prompt(item: dict[str, Any]) -> str:
    return f"""
You are a report-only editorial judge for Jibi, a Korean broadcast-topic triage tool
for a Syukaworld-style explainer show.

Your job is not to approve production and not to change selection. Classify how this
candidate should be used after reading the evidence pack. Be conservative with
main_seed. However, if rules marked a candidate generic but the body has concrete
numbers, institutions, mechanisms, daily-life costs, or ownership/conflict structure,
do not blindly reject it.

Role definitions:
- main_seed: strong enough to anchor an episode, with concrete body evidence.
- main_seed_candidate: promising main candidate, but still needs a small check.
- sub_block: useful supporting block under a larger theme.
- hook_only: useful only as a hook, not the body of the episode.
- evidence: source/evidence item only.
- reject: too thin, promotional, moral-only, celebrity-only, or not relevant enough.

Reject is a narrow label. If the article has enough concrete evidence to support any
usable broadcast block, choose sub_block, hook_only, or evidence instead of reject.
If why_it_could_work says the candidate can anchor or support an episode, the role
must not be reject.

Write all human-facing text in Korean, including opening_question, why fields,
evidence lists, search queries, and disagreement reasons.

Return exactly one JSON object with these keys:
llm_editorial_role, llm_confidence, opening_question, why_it_could_work,
why_it_might_fail, required_evidence, missing_evidence, suggested_second_search_queries,
syuka_style_fit, rule_disagreement.

syuka_style_fit must include booleans:
daily_life_bridge, hidden_cost_or_owner, institutional_absurdity,
known_brand_hook, too_moral_or_generic.

rule_disagreement must include:
disagrees_with_rule, reasons.

Evidence pack:
{_compact_json(item)}
""".strip()


def _string_list(value: Any) -> list[str]:
    if isinstance(value, list):
        return [str(item) for item in value]
    if isinstance(value, str) and value:
        return [value]
    return []


def normalize_judge_payload(payload: dict[str, Any]) -> dict[str, Any]:
    role = str(payload.get("llm_editorial_role") or "reject")
    if role not in EDITORIAL_ROLES:
        role = "reject"
    confidence = str(payload.get("llm_confidence") or "low")
    if confidence not in CONFIDENCE_VALUES:
        confidence = "low"
    fit = payload.get("syuka_style_fit")
    if not isinstance(fit, dict):
        fit = {}
    rule_disagreement = payload.get("rule_disagreement")
    if not isinstance(rule_disagreement, dict):
        rule_disagreement = {}
    return {
        "llm_editorial_role": role,
        "llm_confidence": confidence,
        "opening_question": str(payload.get("opening_question") or ""),
        "why_it_could_work": str(payload.get("why_it_could_work") or ""),
        "why_it_might_fail": str(payload.get("why_it_might_fail") or ""),
        "required_evidence": _string_list(payload.get("required_evidence")),
        "missing_evidence": _string_list(payload.get("missing_evidence")),
        "suggested_second_search_queries": _string_list(
            payload.get("suggested_second_search_queries")
        ),
        "syuka_style_fit": {
            "daily_life_bridge": bool(fit.get("daily_life_bridge")),
            "hidden_cost_or_owner": bool(fit.get("hidden_cost_or_owner")),
            "institutional_absurdity": bool(fit.get("institutional_absurdity")),
            "known_brand_hook": bool(fit.get("known_brand_hook")),
            "too_moral_or_generic": bool(fit.get("too_moral_or_generic")),
        },
        "rule_disagreement": {
            "disagrees_with_rule": bool(rule_disagreement.get("disagrees_with_rule")),
            "reasons": _string_list(rule_disagreement.get("reasons")),
        },
    }


def _with_computed_rule_disagreement(
    payload: dict[str, Any],
    *,
    item: dict[str, Any],
) -> dict[str, Any]:
    raw_diagnostics = item.get("rule_diagnostics")
    diagnostics = raw_diagnostics if isinstance(raw_diagnostics, dict) else {}
    rule_main_candidate = bool(
        diagnostics.get("main_seed_candidate") or diagnostics.get("ready_seed_candidate")
    )
    llm_main_candidate = payload["llm_editorial_role"] in {
        "main_seed",
        "main_seed_candidate",
    }
    reasons = list(payload["rule_disagreement"].get("reasons") or [])
    disagrees = bool(payload["rule_disagreement"].get("disagrees_with_rule"))
    if rule_main_candidate and not llm_main_candidate:
        disagrees = True
        reasons.append(
            "룰은 main_seed_candidate로 보았지만 LLM은 "
            f"{payload['llm_editorial_role']}로 낮게 분류함"
        )
    if llm_main_candidate and not rule_main_candidate:
        disagrees = True
        reasons.append(
            "룰은 main seed 후보로 올리지 않았지만 LLM은 "
            f"{payload['llm_editorial_role']}로 평가함"
        )
    if (
        diagnostics.get("selection_lesson_role") == "suppress"
        and payload["llm_editorial_role"] not in {"reject", "evidence"}
    ):
        disagrees = True
        reasons.append("룰은 suppress였지만 LLM은 reject/evidence보다 높게 평가함")
    payload["rule_disagreement"] = {
        "disagrees_with_rule": disagrees,
        "reasons": reasons,
    }
    return payload


def judge_evidence_item(
    item: dict[str, Any],
    *,
    llm_client: LlmJsonClient,
    timeout_seconds: int = 120,
) -> dict[str, Any]:
    prompt = build_judge_prompt(item)
    text, raw_payload = llm_client.json_response(
        prompt,
        timeout_seconds=timeout_seconds,
        max_output_tokens=1400,
    )
    payload = _with_computed_rule_disagreement(
        normalize_judge_payload(parse_json_object(text)),
        item=item,
    )
    return {
        "story_bundle_id": item.get("story_bundle_id") or "",
        "visible_title": item.get("visible_title") or "",
        "board_score": item.get("board_score"),
        "rule_editorial_role": item.get("editorial_role") or "",
        "rule_diagnostics": item.get("rule_diagnostics") or {},
        "judge_status": "ok",
        "llm_model": getattr(llm_client, "model", ""),
        "response_id": raw_payload.get("id") if isinstance(raw_payload, dict) else None,
        **payload,
    }


def _error_judge_item(
    item: dict[str, Any],
    *,
    model: str,
    error: Exception,
) -> dict[str, Any]:
    return {
        "story_bundle_id": item.get("story_bundle_id") or "",
        "visible_title": item.get("visible_title") or "",
        "board_score": item.get("board_score"),
        "rule_editorial_role": item.get("editorial_role") or "",
        "judge_status": "error",
        "llm_model": model,
        "error_type": type(error).__name__,
        "llm_editorial_role": "reject",
        "llm_confidence": "low",
        "opening_question": "",
        "why_it_could_work": "",
        "why_it_might_fail": "",
        "required_evidence": [],
        "missing_evidence": [],
        "suggested_second_search_queries": [],
        "syuka_style_fit": {
            "daily_life_bridge": False,
            "hidden_cost_or_owner": False,
            "institutional_absurdity": False,
            "known_brand_hook": False,
            "too_moral_or_generic": True,
        },
        "rule_disagreement": {
            "disagrees_with_rule": False,
            "reasons": [type(error).__name__],
        },
    }


def _env_max_items(default: int) -> int:
    raw = os.environ.get("JIBI_LLM_JUDGE_MAX_ITEMS")
    if not raw:
        return default
    try:
        return int(raw)
    except ValueError:
        return default


def run_llm_editorial_judge(
    *,
    evidence_pack_path: Path,
    output_json: Path,
    output_md: Path,
    max_items: int = 10,
    model: str | None = None,
    enabled: bool | None = None,
    timeout_seconds: int = 120,
    llm_client: LlmJsonClient | None = None,
) -> dict[str, Any]:
    evidence_pack = json.loads(evidence_pack_path.read_text(encoding="utf-8"))
    items = [item for item in evidence_pack.get("items", []) if isinstance(item, dict)]
    active_model = jibi_llm_model(model)
    active = is_jibi_llm_enabled() if enabled is None else enabled
    max_count = _env_max_items(max_items)
    selected_items = items if max_count <= 0 else items[:max_count]
    rows: list[dict[str, Any]] = []
    if active:
        client = llm_client or OpenAIResponsesClient(model=active_model)
        for item in selected_items:
            try:
                rows.append(
                    judge_evidence_item(
                        item,
                        llm_client=client,
                        timeout_seconds=timeout_seconds,
                    )
                )
            except Exception as exc:
                rows.append(_error_judge_item(item, model=active_model, error=exc))
    payload = {
        "run_date": evidence_pack.get("run_date") or "",
        "evidence_pack_path": str(evidence_pack_path),
        "llm_judge_enabled": active,
        "llm_model": active_model,
        "requested_item_count": len(selected_items),
        "judged_item_count": len(rows),
        "role_counts": dict(Counter(row.get("llm_editorial_role") for row in rows)),
        "status_counts": dict(Counter(row.get("judge_status") for row in rows)),
        "rule_disagreement_count": sum(
            1
            for row in rows
            if isinstance(row.get("rule_disagreement"), dict)
            and row["rule_disagreement"].get("disagrees_with_rule")
        ),
        "items": rows,
    }
    write_llm_judge_report(payload=payload, output_json=output_json, output_md=output_md)
    return payload


def _table_cell(value: object, *, limit: int = 140) -> str:
    text = " ".join(str(value or "").split())
    if len(text) > limit:
        text = text[: limit - 3].rstrip() + "..."
    return text.replace("|", "\\|")


def write_llm_judge_report(
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
        f"# Jibi LLM Editorial Judge — {payload.get('run_date')}",
        "",
        "## Summary",
        "",
        f"- llm_judge_enabled: {str(payload.get('llm_judge_enabled')).lower()}",
        f"- llm_model: `{payload.get('llm_model')}`",
        f"- requested_item_count: {payload.get('requested_item_count', 0)}",
        f"- judged_item_count: {payload.get('judged_item_count', 0)}",
        f"- rule_disagreement_count: {payload.get('rule_disagreement_count', 0)}",
    ]
    for role, count in sorted(payload.get("role_counts", {}).items()):
        lines.append(f"- llm_role_{role}: {count}")
    if not payload.get("llm_judge_enabled"):
        lines.extend(
            [
                "",
                "LLM judge is report-only and was skipped. Set `JIBI_LLM_JUDGE=1` to run it.",
                "",
            ]
        )
    lines.extend(
        [
            "",
            "## Judged Items",
            "",
            (
                "| title | llm role | confidence | opening question | disagreement | "
                "missing evidence |"
            ),
            "| --- | --- | --- | --- | --- | --- |",
        ]
    )
    for row in payload.get("items", []):
        disagreement = row.get("rule_disagreement") or {}
        lines.append(
            "| "
            + " | ".join(
                [
                    _table_cell(row.get("visible_title")),
                    _table_cell(row.get("llm_editorial_role")),
                    _table_cell(row.get("llm_confidence")),
                    _table_cell(row.get("opening_question")),
                    _table_cell(
                        "; ".join(disagreement.get("reasons") or [])
                        if disagreement.get("disagrees_with_rule")
                        else "none"
                    ),
                    _table_cell("; ".join(row.get("missing_evidence") or [])),
                ]
            )
            + " |"
        )
    if not payload.get("items"):
        lines.append("| none | none | none | none | none | none |")
    lines.append("")
    output_md.write_text("\n".join(lines), encoding="utf-8")


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
    output_json: Annotated[
        Path | None,
        typer.Option("--output-json", help="LLM judge JSON output."),
    ] = None,
    output_md: Annotated[
        Path | None,
        typer.Option("--output-md", help="LLM judge Markdown output."),
    ] = None,
    max_items: Annotated[
        int,
        typer.Option("--max-items", help="Maximum evidence items to judge; 0 means all."),
    ] = 10,
    model: Annotated[
        str | None,
        typer.Option("--model", help="OpenAI model override; defaults to gpt-5-mini lane."),
    ] = None,
    force: Annotated[
        bool,
        typer.Option(
            "--force/--respect-env",
            help="Run even if JIBI_LLM_JUDGE is not set.",
        ),
    ] = False,
    timeout_seconds: Annotated[
        int,
        typer.Option("--timeout", help="OpenAI API timeout in seconds."),
    ] = 120,
) -> None:
    run_date = date_text or datetime.now(UTC).date().isoformat()
    evidence_path = evidence_pack_path or (
        paths.REPORTS_DIR / f"jibi_evidence_pack_{run_date}.json"
    )
    json_path = output_json or paths.REPORTS_DIR / f"jibi_llm_editorial_judge_{run_date}.json"
    md_path = output_md or paths.REPORTS_DIR / f"jibi_llm_editorial_judge_{run_date}.md"
    payload = run_llm_editorial_judge(
        evidence_pack_path=evidence_path,
        output_json=json_path,
        output_md=md_path,
        max_items=max_items,
        model=model,
        enabled=True if force else None,
        timeout_seconds=timeout_seconds,
    )
    console.print(
        "[green]Wrote Jibi LLM editorial judge report "
        f"({payload['judged_item_count']} judged; model={payload['llm_model']}) "
        f"to {json_path} and {md_path}.[/green]"
    )


if __name__ == "__main__":
    app()
