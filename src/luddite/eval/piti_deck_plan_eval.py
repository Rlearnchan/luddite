"""Evaluate piti deck plan fixtures for source hygiene and editability.

This runner intentionally does not call an LLM. Without model output, it grades
the golden deck plan fixtures themselves as deterministic candidates.
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
from luddite.utils.urls import canonicalize_url, extract_urls

app = typer.Typer(no_args_is_help=False)
console = Console()

DECK_FIXTURE_DIR = paths.EVAL_DIR / "golden_cases" / "deck_plans"
OUTPUT_DIR = paths.OUTPUTS_DIR / "eval" / "piti_deck_plan_eval"
LATEST_JSONL = OUTPUT_DIR / "latest.jsonl"
LATEST_MD = OUTPUT_DIR / "latest.md"


@dataclass
class EvalSummary:
    total: int
    passed: int
    failed: int
    warnings: int


def _load_json(path: Path) -> Any:
    with path.open(encoding="utf-8") as source:
        return json.load(source)


def _schema_validator() -> Draft202012Validator:
    return Draft202012Validator(_load_json(paths.SPECS_DIR / "deck_schema.json"))


def load_deck_plans(directory: Path = DECK_FIXTURE_DIR) -> list[tuple[Path, dict[str, Any]]]:
    return [(path, _load_json(path)) for path in sorted(directory.glob("*.json"))]


def _model_outputs_from_path(path: Path | None) -> dict[str, dict[str, Any]]:
    if path is None:
        return {}
    if path.is_file():
        payload = _load_json(path)
        if isinstance(payload, list):
            return {item["deck_id"]: item for item in payload}
        return {payload["deck_id"]: payload}
    return {
        payload["deck_id"]: payload
        for payload in (_load_json(file_path) for file_path in sorted(path.glob("*.json")))
    }


def _notes_urls(slide: dict[str, Any]) -> set[str]:
    return set(extract_urls(slide.get("notes", "")))


def _image_slot_urls(slide: dict[str, Any]) -> set[str]:
    return {
        canonicalize_url(slot.get("source_url", ""))
        for slot in slide.get("image_slots", [])
        if slot.get("source_url")
    }


def _content_note_urls(slide: dict[str, Any]) -> set[str]:
    urls: set[str] = set()
    for line in slide.get("notes", "").splitlines():
        if "[내용" in line:
            urls.update(extract_urls(line))
    return urls


def _image_note_urls(slide: dict[str, Any]) -> set[str]:
    urls: set[str] = set()
    for line in slide.get("notes", "").splitlines():
        if "[이미지" in line:
            urls.update(extract_urls(line))
    return urls


def _slide_no_integrity(deck_plan: dict[str, Any]) -> bool:
    slide_numbers = [slide.get("slide_no") for slide in deck_plan.get("slides", [])]
    return slide_numbers == list(range(1, len(slide_numbers) + 1))


def _required_slide_types(deck_plan: dict[str, Any]) -> tuple[bool, dict[str, int]]:
    counts = Counter(slide.get("slide_type") for slide in deck_plan.get("slides", []))
    ok = counts["title"] >= 1 and counts["section_title"] >= 2
    return ok, dict(counts)


def _source_note_integrity(deck_plan: dict[str, Any]) -> tuple[bool, list[str]]:
    issues: list[str] = []
    for slide in deck_plan.get("slides", []):
        notes = slide.get("notes", "")
        notes_urls = _notes_urls(slide)
        content_urls = _content_note_urls(slide)
        image_urls = _image_slot_urls(slide) | _image_note_urls(slide)
        if content_urls and not any("[내용" in line for line in notes.splitlines()):
            issues.append(f"slide {slide.get('slide_no')}: content URL missing [내용] label")
        for url in content_urls:
            if url not in notes_urls:
                issues.append(f"slide {slide.get('slide_no')}: content URL missing from notes")
        for url in image_urls:
            has_image_label = any(
                url in extract_urls(line) and "[이미지" in line for line in notes.splitlines()
            )
            if url not in notes_urls:
                issues.append(f"slide {slide.get('slide_no')}: image URL missing from notes")
            elif not has_image_label:
                issues.append(f"slide {slide.get('slide_no')}: image URL missing [이미지] label")
    return not issues, issues


def _source_image_overlap_count(deck_plan: dict[str, Any]) -> int:
    count = 0
    for slide in deck_plan.get("slides", []):
        if _content_note_urls(slide) & (_image_slot_urls(slide) | _image_note_urls(slide)):
            count += 1
    return count


def _image_slot_warnings(deck_plan: dict[str, Any]) -> list[str]:
    warnings: list[str] = []
    for slide in deck_plan.get("slides", []):
        image_notes = _image_note_urls(slide)
        if image_notes and not slide.get("image_slots"):
            warnings.append(f"slide {slide.get('slide_no')}: image notes without image_slots")
    return warnings


def _editability(deck_plan: dict[str, Any]) -> tuple[bool, list[str]]:
    issues: list[str] = []
    warnings: list[str] = []
    for slide in deck_plan.get("slides", []):
        slide_no = slide.get("slide_no")
        if "headline" not in slide:
            issues.append(f"slide {slide_no}: missing headline")
        if not isinstance(slide.get("body"), list):
            issues.append(f"slide {slide_no}: body must be list")
        if "notes" not in slide:
            issues.append(f"slide {slide_no}: missing notes")
        for line in slide.get("body", []):
            if len(str(line)) > 180:
                warnings.append(f"slide {slide_no}: body line is long")
        if slide.get("slide_type") in {"quote", "data"} and len(slide.get("body", [])) > 4:
            warnings.append(f"slide {slide_no}: {slide.get('slide_type')} slide is dense")
    return not issues, [*issues, *warnings]


def _section_pacing_warnings(deck_plan: dict[str, Any]) -> list[str]:
    slides = deck_plan.get("slides", [])
    section_count = sum(1 for slide in slides if slide.get("slide_type") == "section_title")
    if section_count < 2:
        return ["section_title count is low"]
    if section_count > max(3, len(slides) // 4):
        return ["section_title count is high"]
    gaps: list[int] = []
    last_section = 1
    for slide in slides:
        if slide.get("slide_type") == "section_title":
            gaps.append(slide.get("slide_no", 0) - last_section)
            last_section = slide.get("slide_no", 0)
    if any(gap > 18 for gap in gaps):
        return ["long stretch without section_title"]
    return []


def evaluate_deck_plan(path: Path, deck_plan: dict[str, Any]) -> dict[str, Any]:
    schema_errors = [error.message for error in _schema_validator().iter_errors(deck_plan)]
    schema_valid = not schema_errors
    slide_no_ok = _slide_no_integrity(deck_plan)
    required_types_ok, slide_type_counts = _required_slide_types(deck_plan)
    source_notes_ok, source_note_issues = _source_note_integrity(deck_plan)
    overlap_count = _source_image_overlap_count(deck_plan)
    editability_ok, editability_notes = _editability(deck_plan)
    editability_warnings = [
        note
        for note in editability_notes
        if not note.startswith("slide") or "missing" not in note
    ]
    warnings = [
        *schema_errors,
        *_image_slot_warnings(deck_plan),
        *_section_pacing_warnings(deck_plan),
        *editability_warnings,
    ]
    passed = (
        schema_valid
        and slide_no_ok
        and required_types_ok
        and source_notes_ok
        and overlap_count == 0
        and editability_ok
    )
    return {
        "deck_id": deck_plan.get("deck_id", path.stem),
        "file": (
            str(path.relative_to(paths.REPO_ROOT))
            if path.is_absolute() and path.is_relative_to(paths.REPO_ROOT)
            else str(path)
        ),
        "schema_valid": schema_valid,
        "schema_errors": schema_errors,
        "slide_count": len(deck_plan.get("slides", [])),
        "slide_no_integrity": slide_no_ok,
        "required_slide_types": required_types_ok,
        "slide_type_counts": slide_type_counts,
        "source_note_integrity": source_notes_ok,
        "source_note_issues": source_note_issues,
        "source_image_overlap_count": overlap_count,
        "editability_ok": editability_ok,
        "editability_notes": editability_notes,
        "warnings": warnings,
        "passed": passed,
    }


def summarize(results: list[dict[str, Any]]) -> EvalSummary:
    total = len(results)
    passed = sum(1 for result in results if result.get("passed"))
    warnings = sum(len(result.get("warnings", [])) for result in results)
    return EvalSummary(total=total, passed=passed, failed=total - passed, warnings=warnings)


def write_markdown_report(path: Path, results: list[dict[str, Any]], summary: EvalSummary) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    lines = [
        "# piti Deck Plan Eval Report",
        "",
        f"- Generated at: {datetime.now(UTC).isoformat()}",
        f"- Total decks: {summary.total}",
        f"- Passed: {summary.passed}",
        f"- Failed: {summary.failed}",
        f"- Warnings: {summary.warnings}",
        "",
        "## Deck Results",
        "",
        (
            "| Deck | Candidate | Slides | Schema | Slide Nos | Required Types | Source Notes | "
            "Overlaps | Editability | Passed |"
        ),
        "|---|---|---:|---|---|---|---|---:|---|---|",
    ]
    for result in results:
        row_template = (
            "| {deck} | {candidate} | {slides} | {schema} | {numbers} | {types} | {sources} | "
            "{overlaps} | {edit} | {passed} |"
        )
        lines.append(
            row_template.format(
                deck=result["deck_id"],
                candidate=result.get("candidate_source", "unknown"),
                slides=result["slide_count"],
                schema="yes" if result["schema_valid"] else "no",
                numbers="yes" if result["slide_no_integrity"] else "no",
                types="yes" if result["required_slide_types"] else "no",
                sources="yes" if result["source_note_integrity"] else "no",
                overlaps=result["source_image_overlap_count"],
                edit="yes" if result["editability_ok"] else "no",
                passed="yes" if result["passed"] else "no",
            )
        )
    lines.extend(["", "## Warnings", ""])
    for result in results:
        warnings = result.get("warnings", [])
        if not warnings:
            lines.append(f"- {result['deck_id']}: none")
        else:
            for warning in warnings:
                lines.append(f"- {result['deck_id']}: {warning}")
    fallback_results = [
        result for result in results if result.get("candidate_source") == "golden_fallback"
    ]
    if fallback_results:
        lines.extend(["", "## Golden Fallbacks", ""])
        for result in fallback_results:
            lines.append(
                f"- {result['deck_id']}: no model output supplied; evaluated golden fixture."
            )
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def run_eval(
    fixture_dir: Path = DECK_FIXTURE_DIR,
    model_output_path: Path | None = None,
    output_jsonl: Path = LATEST_JSONL,
    output_md: Path = LATEST_MD,
) -> list[dict[str, Any]]:
    model_outputs = _model_outputs_from_path(model_output_path)
    fixtures = load_deck_plans(fixture_dir)
    results = []
    for path, deck in fixtures:
        deck_id = deck.get("deck_id")
        candidate = model_outputs.get(deck_id, deck)
        result = evaluate_deck_plan(path, candidate)
        if model_output_path is None:
            result["candidate_source"] = "golden_fixture"
        elif deck_id in model_outputs:
            result["candidate_source"] = "model_output"
        else:
            result["candidate_source"] = "golden_fallback"
            result["warnings"].append("no model output supplied; evaluated golden fixture")
        results.append(result)
    summary = summarize(results)
    output_jsonl.parent.mkdir(parents=True, exist_ok=True)
    write_jsonl(output_jsonl, results)
    write_markdown_report(output_md, results, summary)
    return results


@app.callback(invoke_without_command=True)
def main(
    fixture_dir: Annotated[
        Path,
        typer.Option("--fixture-dir", help="Deck plan fixture directory."),
    ] = DECK_FIXTURE_DIR,
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
    """Run the piti deck plan eval without calling an LLM."""
    results = run_eval(fixture_dir, model_output, output_jsonl, output_md)
    summary = summarize(results)
    console.print(
        f"[green]Wrote piti deck plan eval report to {output_md} "
        f"({summary.passed}/{summary.total} passed).[/green]"
    )
    raise typer.Exit(0 if summary.failed == 0 else 1)


if __name__ == "__main__":
    app()
