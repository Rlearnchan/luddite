"""Fixture-based anny API experiment validation.

This module does not call an LLM API. It validates raw output fixtures as if
they came from a future API experiment, preserving the raw text and classifying
failure modes before any production agent exists.
"""

from __future__ import annotations

import json
import shutil
from collections.abc import Iterable
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Annotated, Any

import typer
from rich.console import Console

from luddite import paths
from luddite.eval.anny_dry_run_eval import (
    DO_NOT_CLAIM_PATTERNS,
    _source_image_overlap_count,
)
from luddite.utils.schemas import validate_with_schema
from luddite.utils.urls import canonicalize_url

app = typer.Typer(no_args_is_help=False)
console = Console()

DEFAULT_CASE_ID = "anny_api_experiment_ai_knowledge_institution_v1"
DEFAULT_INPUT_BUNDLE = (
    paths.ANNY_STORYLINE_DRY_RUN_DIR / "ai_knowledge_institution_input_bundle.json"
)
DEFAULT_EVIDENCE_PACK = paths.ANNY_EVIDENCE_PACK_AI_KNOWLEDGE_JSON
DEFAULT_OUTPUT_ROOT = paths.OUTPUTS_DIR / "eval" / "anny_api_experiment"
DEFAULT_EXPERIMENT_ROOT = paths.MODEL_DRY_RUNS_DIR / "anny_api_experiments"


@dataclass(frozen=True)
class ApiExperimentResult:
    fixture_name: str
    parse_status: str
    schema_valid: bool
    hygiene_passed: bool
    failure_modes: list[str]
    allowed_url_count: int
    used_url_count: int
    hallucinated_urls: list[str]
    repair_attempted: bool
    ready_for_api_experiment: bool
    report_path: Path
    manifest_path: Path
    experiment_dir: Path


def _load_json(path: Path) -> Any:
    with path.open(encoding="utf-8") as source:
        return json.load(source)


def _write_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def _walk_values(value: Any) -> Iterable[Any]:
    if isinstance(value, dict):
        for item in value.values():
            yield from _walk_values(item)
    elif isinstance(value, list):
        for item in value:
            yield from _walk_values(item)
    else:
        yield value


def _collect_allowed_urls(*payloads: dict[str, Any]) -> set[str]:
    urls: set[str] = set()
    for payload in payloads:
        for value in _walk_values(payload):
            if isinstance(value, str) and value.startswith(("http://", "https://")):
                urls.add(canonicalize_url(value))
    return urls


def _all_slides(storyline: dict[str, Any]) -> list[dict[str, Any]]:
    return [
        slide
        for section in storyline.get("sections", [])
        for slide in section.get("slides", [])
    ]


def _used_source_urls(storyline: dict[str, Any]) -> set[str]:
    urls: set[str] = set()
    for slide in _all_slides(storyline):
        for url in slide.get("source_urls", []):
            if url:
                urls.add(canonicalize_url(url))
        for source_ref in slide.get("source_refs", []):
            url = source_ref.get("url")
            if url:
                urls.add(canonicalize_url(url))
    return urls


def _empty_source_errors(storyline: dict[str, Any]) -> list[str]:
    errors = []
    for index, slide in enumerate(_all_slides(storyline), start=1):
        if not slide.get("source_urls") and not slide.get("needs_source"):
            errors.append(f"slide {index} has empty source_urls without needs_source=true")
    return errors


def _text_blob(storyline: dict[str, Any]) -> str:
    parts = [storyline.get("title", ""), storyline.get("one_liner", "")]
    for section in storyline.get("sections", []):
        parts.append(section.get("section_title", ""))
        for slide in section.get("slides", []):
            parts.append(slide.get("slide_type", ""))
            parts.append(slide.get("headline", ""))
            parts.extend(slide.get("body", []))
            parts.append(slide.get("notes", ""))
    return "\n".join(str(part) for part in parts if part)


def _counterpoint_included(storyline: dict[str, Any]) -> bool:
    text = _text_blob(storyline)
    return any(
        marker in text
        for marker in ["counterpoint", "반대 관점", "반론", "리스크", "접근성", "맞춤형"]
    )


def _do_not_claim_violations(storyline: dict[str, Any], input_bundle: dict[str, Any]) -> list[str]:
    text = _text_blob(storyline)
    patterns = list(DO_NOT_CLAIM_PATTERNS)
    patterns.extend(str(item) for item in input_bundle.get("do_not_claim", []))
    return [pattern for pattern in patterns if pattern and pattern in text]


def validate_api_experiment_raw_output(
    *,
    raw_output_path: Path,
    input_bundle_path: Path = DEFAULT_INPUT_BUNDLE,
    evidence_pack_path: Path = DEFAULT_EVIDENCE_PACK,
    experiment_dir: Path,
    report_path: Path,
    case_id: str = DEFAULT_CASE_ID,
) -> ApiExperimentResult:
    fixture_name = raw_output_path.stem
    experiment_dir.mkdir(parents=True, exist_ok=True)
    report_path.parent.mkdir(parents=True, exist_ok=True)
    raw_copy_path = experiment_dir / "raw_model_output.txt"
    parsed_path = experiment_dir / "parsed_storyline.json"
    manifest_path = experiment_dir / "manifest.json"
    shutil.copyfile(raw_output_path, raw_copy_path)

    input_bundle = _load_json(input_bundle_path)
    evidence_pack = _load_json(evidence_pack_path)
    allowed_urls = _collect_allowed_urls(input_bundle, evidence_pack)
    raw_text = raw_copy_path.read_text(encoding="utf-8")

    parse_status = "parsed"
    schema_valid = False
    hygiene_passed = False
    failure_modes: list[str] = []
    used_urls: set[str] = set()
    hallucinated_urls: list[str] = []
    schema_errors: list[str] = []
    empty_source_errors: list[str] = []
    do_not_claim_violations: list[str] = []
    source_image_overlap_count = 0
    counterpoint_included = False

    try:
        storyline = json.loads(raw_text)
    except json.JSONDecodeError as exc:
        storyline = None
        parse_status = f"invalid_json:{exc.msg}"
        failure_modes.append("invalid_json")

    if isinstance(storyline, dict):
        _write_json(parsed_path, storyline)
        schema_errors = validate_with_schema(storyline, "anny_storyline_schema.json")
        schema_valid = not schema_errors
        if schema_errors:
            failure_modes.append("schema_error")
        used_urls = _used_source_urls(storyline)
        hallucinated_urls = sorted(used_urls - allowed_urls)
        if hallucinated_urls:
            failure_modes.append("source_hallucination")
        source_image_overlap_count = _source_image_overlap_count(storyline)
        if source_image_overlap_count:
            failure_modes.append("source_image_overlap")
        empty_source_errors = _empty_source_errors(storyline)
        if empty_source_errors:
            failure_modes.append("unsupported_claim")
        counterpoint_included = _counterpoint_included(storyline)
        if not counterpoint_included:
            failure_modes.append("counterpoint_missing")
        do_not_claim_violations = _do_not_claim_violations(storyline, input_bundle)
        if do_not_claim_violations:
            failure_modes.append("do_not_claim_violation")

    failure_modes = list(dict.fromkeys(failure_modes))
    hygiene_passed = not failure_modes
    ready_for_api_experiment = hygiene_passed and schema_valid
    manifest = {
        "run_id": fixture_name,
        "case_id": case_id,
        "status": "passed" if ready_for_api_experiment else "failed",
        "input_bundle_path": str(input_bundle_path),
        "evidence_pack_path": str(evidence_pack_path),
        "raw_model_output_path": str(raw_copy_path),
        "parsed_storyline_path": str(parsed_path) if parsed_path.exists() else None,
        "api_experiment_dir": str(experiment_dir),
        "validation_report_path": str(report_path),
        "model_source": "fixture",
        "parse_status": parse_status,
        "schema_valid": schema_valid,
        "hygiene_passed": hygiene_passed,
        "failure_modes": failure_modes,
        "allowed_url_count": len(allowed_urls),
        "used_url_count": len(used_urls),
        "hallucinated_urls": hallucinated_urls,
        "repair_attempted": False,
        "ready_for_api_experiment_prep": True,
        "ready_for_api_experiment": ready_for_api_experiment,
        "ready_for_production_agent": False,
        "ready_for_broadcast": False,
        "created_at": datetime.now(UTC).isoformat(),
    }
    _write_json(manifest_path, manifest)
    report_path.write_text(
        _report_markdown(
            fixture_name=fixture_name,
            manifest=manifest,
            schema_errors=schema_errors,
            empty_source_errors=empty_source_errors,
            do_not_claim_violations=do_not_claim_violations,
            counterpoint_included=counterpoint_included,
        ),
        encoding="utf-8",
    )
    return ApiExperimentResult(
        fixture_name=fixture_name,
        parse_status=parse_status,
        schema_valid=schema_valid,
        hygiene_passed=hygiene_passed,
        failure_modes=failure_modes,
        allowed_url_count=len(allowed_urls),
        used_url_count=len(used_urls),
        hallucinated_urls=hallucinated_urls,
        repair_attempted=False,
        ready_for_api_experiment=ready_for_api_experiment,
        report_path=report_path,
        manifest_path=manifest_path,
        experiment_dir=experiment_dir,
    )


def _report_markdown(
    *,
    fixture_name: str,
    manifest: dict[str, Any],
    schema_errors: list[str],
    empty_source_errors: list[str],
    do_not_claim_violations: list[str],
    counterpoint_included: bool,
) -> str:
    lines = [
        f"# Anny API Experiment Fixture Report — {fixture_name}",
        "",
        f"- fixture_name: {fixture_name}",
        f"- parse_status: {manifest['parse_status']}",
        f"- schema_valid: {manifest['schema_valid']}",
        f"- hygiene_passed: {manifest['hygiene_passed']}",
        f"- failure_modes: {manifest['failure_modes']}",
        f"- allowed_url_count: {manifest['allowed_url_count']}",
        f"- used_url_count: {manifest['used_url_count']}",
        f"- hallucinated_urls: {manifest['hallucinated_urls']}",
        f"- repair_attempted: {str(manifest['repair_attempted']).lower()}",
        f"- counterpoint_included: {counterpoint_included}",
        f"- ready_for_api_experiment_prep: {manifest['ready_for_api_experiment_prep']}",
        f"- ready_for_api_experiment: {manifest['ready_for_api_experiment']}",
        f"- ready_for_production_agent: {manifest['ready_for_production_agent']}",
        f"- ready_for_broadcast: {manifest['ready_for_broadcast']}",
        "",
        "## Error Detail",
        "",
        f"- schema_errors: {schema_errors or []}",
        f"- empty_source_errors: {empty_source_errors or []}",
        f"- do_not_claim_violations: {do_not_claim_violations or []}",
        "",
        "## Policy",
        "",
        "- llm_api_called: false",
        "- repair_attempted: false",
        "- raw_model_output_retained: true",
    ]
    return "\n".join(lines) + "\n"


@app.callback(invoke_without_command=True)
def main(
    raw_output_path: Annotated[
        Path,
        typer.Option("--raw-output", help="Raw model output text fixture."),
    ],
    input_bundle_path: Annotated[
        Path,
        typer.Option("--input-bundle", help="Anny input bundle JSON."),
    ] = DEFAULT_INPUT_BUNDLE,
    evidence_pack_path: Annotated[
        Path,
        typer.Option("--evidence-pack", help="Evidence pack JSON."),
    ] = DEFAULT_EVIDENCE_PACK,
    output_root: Annotated[
        Path,
        typer.Option("--output-root", help="Validation report root."),
    ] = DEFAULT_OUTPUT_ROOT,
    experiment_root: Annotated[
        Path,
        typer.Option("--experiment-root", help="API experiment artifact root."),
    ] = DEFAULT_EXPERIMENT_ROOT,
    case_id: Annotated[str, typer.Option("--case-id")] = DEFAULT_CASE_ID,
) -> None:
    fixture_name = raw_output_path.stem
    result = validate_api_experiment_raw_output(
        raw_output_path=raw_output_path,
        input_bundle_path=input_bundle_path,
        evidence_pack_path=evidence_pack_path,
        experiment_dir=experiment_root / fixture_name,
        report_path=output_root / f"{fixture_name}.md",
        case_id=case_id,
    )
    if result.ready_for_api_experiment:
        console.print(f"[green]{fixture_name}: passed[/green]")
    else:
        console.print(f"[yellow]{fixture_name}: failed {result.failure_modes}[/yellow]")


if __name__ == "__main__":
    app()
