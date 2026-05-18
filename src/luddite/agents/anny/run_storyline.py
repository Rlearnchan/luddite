"""Local anny storyline run contract scaffold.

This runner does not call an LLM. It validates manually prepared storyline JSON
against the current anny contract and writes run manifests/reports.
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Annotated, Any

import typer
from rich.console import Console

from luddite import paths
from luddite.eval.anny_dry_run_eval import validate_dry_run_storyline
from luddite.utils.schemas import validate_with_schema

app = typer.Typer(no_args_is_help=False)
console = Console()

RUN_INPUT_DIR = paths.MANIFESTS_DIR / "anny_run_inputs"
RUN_MANIFEST_DIR = paths.MANIFESTS_DIR / "anny_runs"
RUN_REPORT_DIR = paths.REPORTS_DIR / "anny_runs"


@dataclass(frozen=True)
class AnnyRunCase:
    run_id: str
    case_id: str
    bundle_id: str
    story_seed_title: str
    input_bundle_path: Path
    output_storyline_path: Path
    hygiene_jsonl_path: Path
    evidence_pack_path: Path | None
    length_mode: str = "standard_representative_outline"
    output_contract_version: str = "anny_mvp_storyline_v1.7"
    prompt_version: str = "prompts/anny/storyline_writer.md"
    mode: str = "manual"
    model_source: str = "manual_gpt_pro"
    baseline_storyline_path: Path | None = None
    require_enriched: bool = False


KNOWN_RUNS = [
    AnnyRunCase(
        run_id="anny_run_ai_knowledge_institution_manual_v1",
        case_id="anny_dry_run_ai_knowledge_institution_v1",
        bundle_id="anny_bundle_09277535430e",
        story_seed_title="AI 즉답 시대의 지식기관 역할",
        input_bundle_path=(
            paths.ANNY_STORYLINE_DRY_RUN_DIR
            / "ai_knowledge_institution_input_bundle.json"
        ),
        output_storyline_path=(
            paths.ANNY_STORYLINE_DRY_RUN_DIR
            / "ai_knowledge_institution_gpt_pro_storyline_enriched.json"
        ),
        baseline_storyline_path=(
            paths.ANNY_STORYLINE_DRY_RUN_DIR
            / "ai_knowledge_institution_gpt_pro_storyline.json"
        ),
        hygiene_jsonl_path=(
            paths.ANNY_STORYLINE_DRY_RUN_DIR
            / "ai_knowledge_institution_source_hygiene.jsonl"
        ),
        evidence_pack_path=paths.ANNY_EVIDENCE_PACK_AI_KNOWLEDGE_JSON,
        require_enriched=True,
    ),
    AnnyRunCase(
        run_id="anny_run_productive_finance_policy_manual_v1",
        case_id="anny_dry_run_productive_finance_policy_v1",
        bundle_id="anny_bundle_5c95ee31f95d",
        story_seed_title="생산적 금융과 정책자금 전환",
        input_bundle_path=(
            paths.ANNY_STORYLINE_DRY_RUN_DIR / "productive_finance_policy_input_bundle.json"
        ),
        output_storyline_path=(
            paths.ANNY_STORYLINE_DRY_RUN_DIR
            / "productive_finance_policy_gpt_pro_storyline.json"
        ),
        hygiene_jsonl_path=(
            paths.ANNY_STORYLINE_DRY_RUN_DIR
            / "productive_finance_policy_source_hygiene.jsonl"
        ),
        evidence_pack_path=(
            paths.CANDIDATES_DIR / "anny_evidence_pack_productive_finance_policy.json"
        ),
    ),
]


def _case_by_id(case_id: str) -> AnnyRunCase:
    for case in KNOWN_RUNS:
        if case.case_id == case_id or case.run_id == case_id:
            return case
    known = ", ".join(case.case_id for case in KNOWN_RUNS)
    raise ValueError(f"Unknown anny run case: {case_id}. Known: {known}")


def _now() -> str:
    return datetime.now(UTC).isoformat()


def _path_or_none(path: Path | None) -> str | None:
    return str(path) if path else None


def build_run_input(case: AnnyRunCase, *, requested_by: str, created_at: str) -> dict[str, Any]:
    return {
        "run_id": case.run_id,
        "bundle_id": case.bundle_id,
        "story_seed_title": case.story_seed_title,
        "input_bundle_path": str(case.input_bundle_path),
        "evidence_pack_path": _path_or_none(case.evidence_pack_path),
        "length_mode": case.length_mode,
        "output_contract_version": case.output_contract_version,
        "prompt_version": case.prompt_version,
        "mode": case.mode,
        "requested_by": requested_by,
        "created_at": created_at,
    }


def run_storyline_case(
    case: AnnyRunCase,
    *,
    requested_by: str = "codex",
    run_input_dir: Path = RUN_INPUT_DIR,
    manifest_dir: Path = RUN_MANIFEST_DIR,
    report_dir: Path = RUN_REPORT_DIR,
) -> dict[str, Any]:
    created_at = _now()
    run_input = build_run_input(case, requested_by=requested_by, created_at=created_at)
    input_schema_errors = validate_with_schema(run_input, "anny_run_input_schema.json")
    if input_schema_errors:
        raise ValueError(f"Invalid anny run input: {input_schema_errors}")

    run_input_dir.mkdir(parents=True, exist_ok=True)
    manifest_dir.mkdir(parents=True, exist_ok=True)
    report_dir.mkdir(parents=True, exist_ok=True)

    run_input_path = run_input_dir / f"{case.run_id}.json"
    manifest_path = manifest_dir / f"{case.run_id}.json"
    report_path = report_dir / f"{case.run_id}.md"
    run_input_path.write_text(
        json.dumps(run_input, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )

    if not case.output_storyline_path.exists():
        manifest = _pending_manifest(
            case,
            created_at=created_at,
            report_path=report_path,
        )
        _write_manifest(manifest_path, manifest)
        report_path.write_text(_report_markdown(case, manifest, None), encoding="utf-8")
        return {"manifest": manifest, "manifest_path": manifest_path, "report_path": report_path}

    eval_result = validate_dry_run_storyline(
        storyline_path=case.output_storyline_path,
        case_id=case.case_id,
        baseline_storyline_path=case.baseline_storyline_path,
        hygiene_jsonl_path=case.hygiene_jsonl_path,
        require_enriched=case.require_enriched,
        require_hygiene_contract=True,
    )
    manifest = _manifest_from_eval(
        case,
        eval_result,
        created_at=created_at,
        report_path=report_path,
    )
    _write_manifest(manifest_path, manifest)
    report_path.write_text(_report_markdown(case, manifest, eval_result), encoding="utf-8")
    return {
        "manifest": manifest,
        "eval_result": eval_result,
        "manifest_path": manifest_path,
        "report_path": report_path,
        "run_input_path": run_input_path,
    }


def _pending_manifest(
    case: AnnyRunCase, *, created_at: str, report_path: Path
) -> dict[str, Any]:
    return {
        "run_id": case.run_id,
        "status": "pending_manual_output",
        "input_bundle_path": str(case.input_bundle_path),
        "evidence_pack_path": _path_or_none(case.evidence_pack_path),
        "output_storyline_path": str(case.output_storyline_path),
        "eval_report_path": str(report_path),
        "model_source": case.model_source,
        "schema_valid": False,
        "hygiene_passed": False,
        "created_at": created_at,
        "notes": ["Manual storyline output is missing; no LLM API was called."],
    }


def _manifest_from_eval(
    case: AnnyRunCase,
    eval_result: dict[str, Any],
    *,
    created_at: str,
    report_path: Path,
) -> dict[str, Any]:
    status = "passed" if eval_result["passed"] else "failed"
    return {
        "run_id": case.run_id,
        "status": status,
        "input_bundle_path": str(case.input_bundle_path),
        "evidence_pack_path": _path_or_none(case.evidence_pack_path),
        "output_storyline_path": str(case.output_storyline_path),
        "eval_report_path": str(report_path),
        "model_source": case.model_source,
        "schema_valid": bool(eval_result["schema_valid"]),
        "hygiene_passed": bool(eval_result["hygiene_contract_passed"]),
        "created_at": created_at,
        "notes": [
            "Validated manually prepared storyline JSON.",
            "No production anny agent or LLM API call was used.",
            "ready_for_production_agent=false",
        ],
        "case_id": case.case_id,
        "section_count": eval_result["section_count"],
        "slide_count": eval_result["slide_count"],
        "source_image_overlap_count": eval_result["source_image_overlap_count"],
        "needs_source_count": eval_result["needs_source_count"],
        "needs_fact_check_count": eval_result["needs_fact_check_count"],
        "required_before_broadcast_count": sum(
            bool(record.get("required_before_broadcast"))
            for record in eval_result.get("hygiene_records", [])
        ),
        "counterpoint_included": bool(eval_result["counterpoint_included"]),
        "production_checklist_included": any(
            record.get("fact_check_kind") == "production_checklist"
            for record in eval_result.get("hygiene_records", [])
        ),
        "do_not_claim_violations": eval_result["do_not_claim_violations"],
    }


def _write_manifest(path: Path, manifest: dict[str, Any]) -> None:
    schema_errors = validate_with_schema(manifest, "anny_run_manifest_schema.json")
    if schema_errors:
        raise ValueError(f"Invalid anny run manifest: {schema_errors}")
    path.write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )


def _report_markdown(
    case: AnnyRunCase,
    manifest: dict[str, Any],
    eval_result: dict[str, Any] | None,
) -> str:
    lines = [
        f"# Anny Run Report — {case.story_seed_title}",
        "",
        f"- run_id: {case.run_id}",
        f"- case_id: {case.case_id}",
        f"- status: {manifest['status']}",
        f"- model_source: {case.model_source}",
        f"- input_bundle_path: {case.input_bundle_path}",
        f"- evidence_pack_path: {_path_or_none(case.evidence_pack_path)}",
        f"- output_storyline_path: {case.output_storyline_path}",
        "- llm_api_called: false",
        "- production_anny_agent: false",
        "",
        "## Readiness",
        "",
        "- ready_for_prompt_design: true",
        "- ready_for_manual_storyline: true",
        "- ready_for_api_experiment: false",
        "- ready_for_production_agent: false",
        "- ready_for_broadcast: false",
        "",
    ]
    if not eval_result:
        lines.extend(["## Eval", "", "- pending manual storyline output"])
        return "\n".join(lines) + "\n"
    lines.extend(
        [
            "## Eval",
            "",
            f"- schema_valid: {eval_result['schema_valid']}",
            f"- hygiene_passed: {eval_result['hygiene_contract_passed']}",
            f"- sections: {eval_result['section_count']}",
            f"- slides: {eval_result['slide_count']}",
            f"- source_image_overlap_count: {eval_result['source_image_overlap_count']}",
            f"- needs_source_count: {eval_result['needs_source_count']}",
            f"- needs_fact_check_count: {eval_result['needs_fact_check_count']}",
            f"- fact_check_marker_present: {eval_result['fact_check_marker_present']}",
            f"- counterpoint_included: {eval_result['counterpoint_included']}",
            f"- do_not_claim_violations: {eval_result['do_not_claim_violations']}",
            (
                "- policy_finance_guardrails_passed: "
                f"{eval_result['policy_finance_guardrails_passed']}"
            ),
            "",
            "## Contract Notes",
            "",
            "- Attached sources are not treated as completed fact-checks.",
            "- production_checklist is tracked as internal production material.",
            "- source_refs are validated through the hygiene sidecar.",
        ]
    )
    return "\n".join(lines) + "\n"


@app.callback(invoke_without_command=True)
def main(
    case_id: Annotated[
        str,
        typer.Option(
            "--case-id",
            help="Run a known case_id/run_id, or 'all' for the two manual dry runs.",
        ),
    ] = "all",
    requested_by: Annotated[
        str,
        typer.Option("--requested-by", help="Requester recorded in run input manifest."),
    ] = "codex",
) -> None:
    cases = KNOWN_RUNS if case_id == "all" else [_case_by_id(case_id)]
    results = [
        run_storyline_case(case, requested_by=requested_by)
        for case in cases
    ]
    passed = sum(1 for result in results if result["manifest"]["status"] == "passed")
    console.print(
        "[green]Wrote anny run manifests/reports "
        f"({passed}/{len(results)} passed).[/green]"
    )


if __name__ == "__main__":
    app()
