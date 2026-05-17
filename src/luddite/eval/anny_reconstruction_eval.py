"""Evaluate anny storyline reconstruction against golden structural beats.

This runner intentionally does not call an LLM. Without model output, it grades
the golden storyline fixtures themselves as deterministic mock candidates. Later
LLM outputs can be supplied as a JSON file or directory and graded by the same
rubric.
"""

from __future__ import annotations

import json
from collections import Counter
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Annotated, Any

import typer
from jsonschema import Draft202012Validator
from rich.console import Console

from luddite import paths
from luddite.utils.jsonl import write_jsonl

app = typer.Typer(no_args_is_help=False)
console = Console()

CASES_PATH = paths.EVAL_DIR / "golden_cases" / "anny_reconstruction_eval_cases.json"
OUTPUT_DIR = paths.OUTPUTS_DIR / "eval" / "anny_reconstruction_eval"
LATEST_JSONL = OUTPUT_DIR / "latest.jsonl"
LATEST_MD = OUTPUT_DIR / "latest.md"
SKIP_SOURCE_SLIDE_TYPES = {"title", "section_title"}


@dataclass
class EvalSummary:
    total: int
    passed: int
    failed: int
    average_key_beat_recall: float
    average_critical_beat_recall: float
    warnings: int


def _load_json(path: Path) -> Any:
    with path.open(encoding="utf-8") as source:
        return json.load(source)


def load_cases(path: Path = CASES_PATH) -> list[dict[str, Any]]:
    return list(_load_json(path))


def _schema_validator() -> Draft202012Validator:
    return Draft202012Validator(_load_json(paths.SPECS_DIR / "anny_storyline_schema.json"))


def _repo_path(path: str | Path) -> Path:
    path = Path(path)
    if path.is_absolute():
        return path
    return paths.REPO_ROOT / path


def _story_text(storyline: dict[str, Any]) -> str:
    values: list[str] = [storyline.get("title", ""), storyline.get("one_liner", "")]
    for section in storyline.get("sections", []):
        values.append(section.get("section_title", ""))
        values.append(section.get("purpose", "") or "")
        for slide in section.get("slides", []):
            values.append(slide.get("headline", ""))
            values.extend(slide.get("body", []))
    return "\n".join(str(value) for value in values if value).lower()


def key_beat_recall(
    storyline: dict[str, Any],
    key_beats: list[dict[str, Any] | str],
) -> tuple[float, list[str], list[str]]:
    text = _story_text(storyline)
    matched: list[str] = []
    missing: list[str] = []
    for beat in key_beats:
        if isinstance(beat, str):
            label = beat
            aliases = [beat]
        else:
            label = beat["label"]
            aliases = beat.get("aliases", [label])
        if any(alias.lower() in text for alias in aliases):
            matched.append(label)
        else:
            missing.append(label)
    recall = len(matched) / len(key_beats) if key_beats else 1.0
    return recall, matched, missing


def _source_integrity(storyline: dict[str, Any]) -> tuple[bool, list[str]]:
    issues: list[str] = []
    for section_index, section in enumerate(storyline.get("sections", []), start=1):
        for slide_index, slide in enumerate(section.get("slides", []), start=1):
            if slide.get("slide_type") in SKIP_SOURCE_SLIDE_TYPES:
                continue
            if slide.get("source_urls") or slide.get("needs_source"):
                continue
            issues.append(f"section {section_index} slide {slide_index}: missing source")
    return not issues, issues


def _source_image_overlap_count(storyline: dict[str, Any]) -> int:
    count = 0
    for section in storyline.get("sections", []):
        for slide in section.get("slides", []):
            if set(slide.get("source_urls", [])) & set(slide.get("image_urls", [])):
                count += 1
    return count


def _fact_check_hygiene(storyline: dict[str, Any]) -> tuple[bool, list[str]]:
    warnings: list[str] = []
    required_present = bool(storyline.get("required_fact_checks"))
    needs_markers = [
        slide
        for section in storyline.get("sections", [])
        for slide in section.get("slides", [])
        if slide.get("needs_fact_check") or slide.get("needs_source")
    ]
    if not required_present:
        warnings.append("required_fact_checks missing")
    if not needs_markers:
        warnings.append("no needs_fact_check/needs_source markers present")
    return required_present, warnings


def _compression_warnings(
    storyline: dict[str, Any],
    expected_length_mode: str,
    fixture_mode: str | None = None,
) -> list[str]:
    slide_count = sum(len(section.get("slides", [])) for section in storyline.get("sections", []))
    ranges = {
        "short": (25, 35),
        "standard": (45, 65),
        "deep": (80, 110),
    }
    low, high = ranges.get(expected_length_mode, ranges["standard"])
    if low <= slide_count <= high:
        return []
    if fixture_mode == "representative_reconstruction":
        severity = "warning"
    elif fixture_mode == "full_reconstruction":
        severity = "strict warning"
    else:
        severity = "warning"
    return [
        f"{expected_length_mode} mode usually expects {low}-{high} slides; "
        f"candidate has {slide_count}. This is a {severity} for {fixture_mode or 'default'}."
    ]


def evaluate_storyline(
    case: dict[str, Any],
    storyline: dict[str, Any],
    schema_validator: Draft202012Validator | None = None,
) -> dict[str, Any]:
    schema_validator = schema_validator or _schema_validator()
    schema_errors = [error.message for error in schema_validator.iter_errors(storyline)]
    schema_valid = not schema_errors
    section_count = len(storyline.get("sections", []))
    section_count_ok = (
        case["required_sections_min"] <= section_count <= case["required_sections_max"]
    )
    recall, matched_beats, missing_beats = key_beat_recall(
        storyline,
        case.get("key_beats", []),
    )
    critical_recall, matched_critical_beats, missing_critical_beats = key_beat_recall(
        storyline,
        case.get("critical_beats", []),
    )
    source_integrity_ok, source_issues = _source_integrity(storyline)
    overlap_count = _source_image_overlap_count(storyline)
    fact_checks_present, fact_check_warnings = _fact_check_hygiene(storyline)
    warnings = [
        *schema_errors,
        *source_issues,
        *fact_check_warnings,
        *_compression_warnings(
            storyline,
            case.get("expected_length_mode", "standard"),
            case.get("fixture_mode"),
        ),
    ]
    if missing_critical_beats:
        warnings.append(f"missing critical beats: {', '.join(missing_critical_beats)}")
    passed = (
        schema_valid
        and section_count_ok
        and recall >= 0.70
        and critical_recall >= 0.80
        and source_integrity_ok
        and overlap_count == 0
        and fact_checks_present
    )
    return {
        "case_id": case["case_id"],
        "expected_archetype": case.get("expected_archetype"),
        "expected_length_mode": case.get("expected_length_mode"),
        "fixture_mode": case.get("fixture_mode"),
        "schema_valid": schema_valid,
        "schema_errors": schema_errors,
        "section_count": section_count,
        "section_count_ok": section_count_ok,
        "key_beat_recall": recall,
        "matched_key_beats": matched_beats,
        "missing_key_beats": missing_beats,
        "critical_beat_recall": critical_recall,
        "matched_critical_beats": matched_critical_beats,
        "missing_critical_beats": missing_critical_beats,
        "source_integrity_ok": source_integrity_ok,
        "source_integrity_issues": source_issues,
        "source_image_overlap_count": overlap_count,
        "required_fact_checks_present": fact_checks_present,
        "warnings": warnings,
        "passed": passed,
    }


def _model_outputs_from_path(path: Path | None) -> dict[str, dict[str, Any]]:
    if path is None:
        return {}
    if path.is_file():
        payload = _load_json(path)
        if isinstance(payload, list):
            return {item["case_id"]: item for item in payload}
        case_id = payload.get("case_id") or payload.get("storyline_id")
        return {case_id: payload}
    outputs: dict[str, dict[str, Any]] = {}
    for file_path in sorted(path.glob("*.json")):
        payload = _load_json(file_path)
        case_id = payload.get("case_id") or payload.get("storyline_id") or file_path.stem
        outputs[case_id] = payload
    return outputs


def _candidate_for_case(
    case: dict[str, Any],
    model_outputs: dict[str, dict[str, Any]],
) -> dict[str, Any]:
    candidate = model_outputs.get(case["case_id"])
    if candidate and "sections" in candidate:
        return candidate
    if candidate and "storyline" in candidate:
        return candidate["storyline"]
    return _load_json(_repo_path(case["golden_storyline_path"]))


def summarize(results: list[dict[str, Any]]) -> EvalSummary:
    total = len(results)
    passed = sum(1 for result in results if result.get("passed"))
    recalls = [float(result.get("key_beat_recall", 0)) for result in results]
    critical_recalls = [
        float(result.get("critical_beat_recall", 1.0)) for result in results
    ]
    warnings = sum(len(result.get("warnings", [])) for result in results)
    return EvalSummary(
        total=total,
        passed=passed,
        failed=total - passed,
        average_key_beat_recall=sum(recalls) / len(recalls) if recalls else 0,
        average_critical_beat_recall=(
            sum(critical_recalls) / len(critical_recalls) if critical_recalls else 0
        ),
        warnings=warnings,
    )


def write_markdown_report(
    path: Path,
    results: list[dict[str, Any]],
    summary: EvalSummary,
    cases_path: Path,
    model_output_path: Path | None,
) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    status_counts = Counter("passed" if result.get("passed") else "failed" for result in results)
    lines = [
        "# anny Reconstruction Eval Report",
        "",
        f"- Generated at: {datetime.now(UTC).isoformat()}",
        f"- Cases: `{cases_path}`",
        f"- Model output: `{model_output_path or 'deterministic golden fixture candidates'}`",
        f"- Total cases: {summary.total}",
        f"- Passed: {summary.passed}",
        f"- Failed: {summary.failed}",
        f"- Average key beat recall: {summary.average_key_beat_recall:.2f}",
        f"- Average critical beat recall: {summary.average_critical_beat_recall:.2f}",
        f"- Warnings: {summary.warnings}",
        "",
        "## Status Counts",
        "",
    ]
    for status, count in status_counts.items():
        lines.append(f"- {status}: {count}")

    lines.extend(
        [
            "",
            "## Case Results",
            "",
            (
                "| Case | Schema | Sections | Key Beat Recall | Critical Recall | Source OK | "
                "Overlaps | Fact Checks | Passed |"
            ),
            "|---|---|---:|---:|---:|---|---:|---|---|",
        ]
    )
    for result in results:
        row_template = (
            "| {case} | {schema} | {sections} | {recall:.2f} | {critical:.2f} | {source} | "
            "{overlaps} | {checks} | {passed} |"
        )
        lines.append(
            row_template.format(
                case=result["case_id"],
                schema="yes" if result["schema_valid"] else "no",
                sections=result["section_count"],
                recall=float(result["key_beat_recall"]),
                critical=float(result["critical_beat_recall"]),
                source="yes" if result["source_integrity_ok"] else "no",
                overlaps=result["source_image_overlap_count"],
                checks="yes" if result["required_fact_checks_present"] else "no",
                passed="yes" if result["passed"] else "no",
            )
        )

    lines.extend(["", "## Missing Beats", ""])
    for result in results:
        missing = ", ".join(result.get("missing_key_beats", [])) or "-"
        lines.append(f"- {result['case_id']}: {missing}")

    lines.extend(["", "## Missing Critical Beats", ""])
    for result in results:
        missing = ", ".join(result.get("missing_critical_beats", [])) or "-"
        lines.append(f"- {result['case_id']}: {missing}")

    lines.extend(["", "## Warnings", ""])
    for result in results:
        warnings = result.get("warnings", [])
        if not warnings:
            lines.append(f"- {result['case_id']}: none")
        else:
            for warning in warnings:
                lines.append(f"- {result['case_id']}: {warning}")

    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def run_eval(
    cases_path: Path = CASES_PATH,
    model_output_path: Path | None = None,
    output_jsonl: Path = LATEST_JSONL,
    output_md: Path = LATEST_MD,
) -> list[dict[str, Any]]:
    cases = load_cases(cases_path)
    model_outputs = _model_outputs_from_path(model_output_path)
    schema_validator = _schema_validator()
    results = [
        evaluate_storyline(
            case,
            _candidate_for_case(case, model_outputs),
            schema_validator,
        )
        for case in cases
    ]
    summary = summarize(results)
    output_jsonl.parent.mkdir(parents=True, exist_ok=True)
    write_jsonl(output_jsonl, results)
    write_markdown_report(output_md, results, summary, cases_path, model_output_path)
    return results


@app.callback(invoke_without_command=True)
def main(
    cases: Annotated[
        Path,
        typer.Option("--cases", help="anny reconstruction eval case JSON."),
    ] = CASES_PATH,
    model_output: Annotated[
        Path | None,
        typer.Option("--model-output", help="Optional model output JSON file or directory."),
    ] = None,
    output_jsonl: Annotated[
        Path,
        typer.Option("--output-jsonl", help="Evaluation JSONL output path."),
    ] = LATEST_JSONL,
    output_md: Annotated[
        Path,
        typer.Option("--output-md", help="Markdown report output path."),
    ] = LATEST_MD,
) -> None:
    """Run the anny reconstruction eval without calling an LLM."""
    results = run_eval(cases, model_output, output_jsonl, output_md)
    summary = summarize(results)
    console.print(
        f"[green]Wrote anny reconstruction eval report to {output_md} "
        f"({summary.passed}/{summary.total} passed).[/green]"
    )
    raise typer.Exit(0 if summary.failed == 0 else 1)


if __name__ == "__main__":
    app()
