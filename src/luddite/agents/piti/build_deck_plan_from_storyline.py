"""Build Piti deck plans from existing Anny storyline JSON artifacts."""

from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import UTC, date, datetime
from pathlib import Path
from typing import Annotated, Any

import typer
from jsonschema import Draft202012Validator
from rich.console import Console

from luddite import paths
from luddite.utils.urls import canonicalize_url

app = typer.Typer(no_args_is_help=False)
console = Console()


@dataclass(frozen=True)
class DeckPlanCase:
    deck_id: str
    source_storyline_path: Path
    output_path: Path
    priority: int


DEFAULT_CASES = [
    DeckPlanCase(
        deck_id="ai_knowledge_institution",
        source_storyline_path=(
            paths.ANNY_STORYLINE_DRY_RUN_DIR
            / "ai_knowledge_institution_gpt_pro_storyline_enriched.json"
        ),
        output_path=paths.PITI_DECK_PLANS_DIR / "ai_knowledge_institution_deck_plan.json",
        priority=1,
    ),
    DeckPlanCase(
        deck_id="productive_finance_policy",
        source_storyline_path=(
            paths.ANNY_STORYLINE_DRY_RUN_DIR
            / "productive_finance_policy_gpt_pro_storyline_enriched.json"
        ),
        output_path=paths.PITI_DECK_PLANS_DIR / "productive_finance_policy_deck_plan.json",
        priority=2,
    ),
]

DEFAULT_REPORT_PATH = (
    paths.REPORTS_DIR / f"piti_deck_plan_report_{date.today().isoformat()}.md"
)

LAYOUT_BY_STORYLINE_TYPE = {
    "title": "title",
    "section_title": "section_title",
    "hook": "big_headline",
    "explainer": "headline_body",
    "quote": "quote",
    "data": "chart_placeholder",
    "comparison": "comparison",
    "image_centered": "image_placeholder",
    "bridge": "question",
    "punchline": "big_headline",
    "closing_question": "closing_question",
    "source_heavy": "checklist",
    "counterpoint": "comparison",
    "risk": "comparison",
    "production_checklist": "appendix_checklist",
    "rhetorical": "question",
}

ALLOWED_LAYOUT_TYPES = {
    "title",
    "section_title",
    "big_headline",
    "headline_body",
    "quote",
    "question",
    "comparison",
    "timeline",
    "chart_placeholder",
    "image_placeholder",
    "checklist",
    "closing_question",
    "appendix_checklist",
}


def _load_json(path: Path) -> dict[str, Any]:
    with path.open(encoding="utf-8") as source:
        payload = json.load(source)
    if not isinstance(payload, dict):
        raise ValueError(f"Expected JSON object at {path}")
    return payload


def _write_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )


def _display_path(path: Path | None) -> str | None:
    if path is None:
        return None
    resolved = path.resolve()
    try:
        return str(resolved.relative_to(paths.REPO_ROOT))
    except ValueError:
        return str(path)


def _body_lines(body: Any) -> list[str]:
    if isinstance(body, list):
        return [str(item) for item in body]
    if body is None:
        return []
    return [str(body)]


def _as_list(value: Any) -> list[Any]:
    return value if isinstance(value, list) else []


def _layout_type(slide_type: str) -> str:
    layout_type = LAYOUT_BY_STORYLINE_TYPE.get(slide_type, "headline_body")
    if layout_type not in ALLOWED_LAYOUT_TYPES:
        return "headline_body"
    return layout_type


def _visual_kind(slide: dict[str, Any], layout_type: str) -> str:
    if slide.get("image_urls"):
        return "photo_candidate"
    if layout_type == "chart_placeholder":
        return "chart_candidate"
    if layout_type in {"comparison", "question"}:
        return "diagram"
    if layout_type in {"image_placeholder", "title", "section_title"}:
        return "manual"
    if layout_type in {"checklist", "appendix_checklist"}:
        return "none"
    return "manual"


def _visual_plan(slide: dict[str, Any], layout_type: str) -> dict[str, Any]:
    kind = _visual_kind(slide, layout_type)
    image_urls = [str(url) for url in _as_list(slide.get("image_urls")) if url]
    source_urls = [str(url) for url in _as_list(slide.get("source_urls")) if url]
    copyright_risk = bool(image_urls) or "copyright_image_risk" in _as_list(
        slide.get("risk_flags")
    )
    if kind == "none":
        description = "No visual required at deck-plan stage."
    elif kind == "chart_candidate":
        description = "Chart or simple number card candidate; no chart is rendered yet."
    elif kind == "diagram":
        description = "Simple comparison/question diagram candidate for manual design."
    elif image_urls:
        description = "Image placeholder candidate from storyline image_urls."
    else:
        description = "Manual visual placeholder; choose asset during later Piti/PPT work."
    return {
        "kind": kind,
        "description": description,
        "source_note": "; ".join(source_urls[:2]) if source_urls else None,
        "copyright_risk": copyright_risk,
        "manual_check_required": kind != "none" or copyright_risk,
        "prompt_if_ai_image": None,
    }


def _image_slots(slide: dict[str, Any]) -> list[dict[str, Any]]:
    slots: list[dict[str, Any]] = []
    for index, url in enumerate(_as_list(slide.get("image_urls")), start=1):
        if not url:
            continue
        slots.append(
            {
                "slot_id": f"image_{index}",
                "source_url": str(url),
                "description": "Image candidate carried from Anny storyline.",
                "copyright_risk": True,
                "manual_check_required": True,
            }
        )
    return slots


def _speaker_notes(slide: dict[str, Any], edit_notes: list[str]) -> str:
    lines: list[str] = []
    original_notes = str(slide.get("notes") or "").strip()
    if original_notes:
        lines.append(original_notes)
    for url in _as_list(slide.get("source_urls")):
        if url:
            lines.append(f"[내용] {url}")
    for url in _as_list(slide.get("image_urls")):
        if url:
            lines.append(f"[이미지] {url}")
    if slide.get("needs_source"):
        lines.append("[TODO] needs_source=true: source must be added or verified.")
    if slide.get("needs_fact_check"):
        lines.append("[TODO] needs_fact_check=true: claim must be manually checked.")
    if edit_notes:
        lines.append("[편집 메모] " + " / ".join(edit_notes))
    return "\n".join(lines)


def _edit_notes(body: list[str], slide_type: str, layout_type: str) -> list[str]:
    notes: list[str] = []
    if len(body) > 3 and layout_type not in {"checklist", "appendix_checklist"}:
        notes.append("consider_split: more than three body bullets")
    if sum(len(item) for item in body) > 320:
        notes.append("one_message_warning: body is dense for a single slide")
    if any(len(item) > 160 for item in body):
        notes.append("line_length_warning: shorten body line before PPT rendering")
    if slide_type == "production_checklist":
        notes.append("internal_appendix: keep out of main broadcast deck body")
    return notes


def _deck_slide(
    slide: dict[str, Any],
    *,
    global_slide_no: int,
    section_no: int,
    local_order: int,
) -> dict[str, Any]:
    slide_type = str(slide.get("slide_type") or "explainer")
    layout_type = _layout_type(slide_type)
    body = _body_lines(slide.get("body"))
    edit_notes = _edit_notes(body, slide_type, layout_type)
    speaker_notes = _speaker_notes(slide, edit_notes)
    return {
        "slide_no": global_slide_no,
        "section_no": section_no,
        "local_order": local_order,
        "source_slide_refs": [slide.get("slide_no") or global_slide_no],
        "slide_type": slide_type,
        "layout_type": layout_type,
        "layout": layout_type,
        "headline": str(slide.get("headline") or "(untitled)"),
        "body": body,
        "visual_plan": _visual_plan(slide, layout_type),
        "image_slots": _image_slots(slide),
        "source_urls": [str(url) for url in _as_list(slide.get("source_urls")) if url],
        "image_urls": [str(url) for url in _as_list(slide.get("image_urls")) if url],
        "speaker_notes": speaker_notes,
        "notes": speaker_notes,
        "needs_source": bool(slide.get("needs_source")),
        "needs_fact_check": bool(slide.get("needs_fact_check")),
        "required_before_broadcast": bool(slide.get("required_before_broadcast")),
        "fact_check_kind": slide.get("fact_check_kind"),
        "fact_check_priority": slide.get("fact_check_priority"),
        "risk_flags": _as_list(slide.get("risk_flags")),
        "edit_notes": edit_notes,
    }


def build_deck_plan_from_storyline(
    storyline: dict[str, Any],
    *,
    deck_id: str,
    source_storyline_path: Path | None = None,
    length_mode: str = "representative_storyboard",
) -> dict[str, Any]:
    sections: list[dict[str, Any]] = []
    flat_slides: list[dict[str, Any]] = []
    global_slide_no = 0
    for section_no, section in enumerate(storyline.get("sections", []), start=1):
        section_slides: list[dict[str, Any]] = []
        for local_order, slide in enumerate(section.get("slides", []), start=1):
            if not isinstance(slide, dict):
                continue
            global_slide_no += 1
            deck_slide = _deck_slide(
                slide,
                global_slide_no=global_slide_no,
                section_no=section_no,
                local_order=local_order,
            )
            flat_slides.append(deck_slide)
            section_slides.append(deck_slide)
        sections.append(
            {
                "section_no": section_no,
                "section_title": str(section.get("section_title") or f"Section {section_no}"),
                "purpose": section.get("purpose"),
                "target_slide_count": len(section_slides),
                "slides": section_slides,
            }
        )
    return {
        "deck_id": f"piti_deck_plan_{deck_id}",
        "source_storyline_id": storyline.get("storyline_id"),
        "source_storyline_path": _display_path(source_storyline_path),
        "title": str(storyline.get("title") or deck_id),
        "theme": "syuka_default_v0",
        "length_mode": length_mode,
        "target_slide_count": len(flat_slides),
        "sections": sections,
        "slides": flat_slides,
        "risk_flags": _as_list(storyline.get("risk_flags")),
        "required_fact_checks": _as_list(storyline.get("required_fact_checks")),
        "notes": (
            "Generated from Anny storyline for Piti deck-plan/storyboard review. "
            "This is not a PPTX and not broadcast-ready."
        ),
        "generation_options": {
            "aspect_ratio": "16:9",
            "default_font": "Malgun Gothic",
            "default_body_pt": 28,
            "render_pptx": False,
        },
        "created_at": datetime.now(UTC).isoformat(),
    }


def _schema_validator() -> Draft202012Validator:
    return Draft202012Validator(_load_json(paths.SPECS_DIR / "deck_schema.json"))


def _source_image_overlap_count(deck_plan: dict[str, Any]) -> int:
    count = 0
    for slide in deck_plan.get("slides", []):
        source_urls = {
            canonicalize_url(str(url))
            for url in slide.get("source_urls", [])
            if str(url).strip()
        }
        image_urls = {
            canonicalize_url(str(url))
            for url in slide.get("image_urls", [])
            if str(url).strip()
        }
        if source_urls & image_urls:
            count += 1
    return count


def validate_deck_plan(deck_plan: dict[str, Any]) -> dict[str, Any]:
    schema_errors = [error.message for error in _schema_validator().iter_errors(deck_plan)]
    slide_numbers = [slide.get("slide_no") for slide in deck_plan.get("slides", [])]
    slide_no_integrity = slide_numbers == list(range(1, len(slide_numbers) + 1))
    speaker_notes_missing = [
        slide.get("slide_no")
        for slide in deck_plan.get("slides", [])
        if not str(slide.get("speaker_notes") or "").strip()
    ]
    production_checklist_not_appendix = [
        slide.get("slide_no")
        for slide in deck_plan.get("slides", [])
        if slide.get("slide_type") == "production_checklist"
        and slide.get("layout_type") != "appendix_checklist"
    ]
    source_image_overlap_count = _source_image_overlap_count(deck_plan)
    split_warnings = [
        f"slide {slide.get('slide_no')}: {note}"
        for slide in deck_plan.get("slides", [])
        for note in slide.get("edit_notes", [])
        if "warning" in note or "consider_split" in note
    ]
    visual_warnings = [
        f"slide {slide.get('slide_no')}: visual plan requires manual check"
        for slide in deck_plan.get("slides", [])
        if slide.get("visual_plan", {}).get("manual_check_required")
    ]
    passed = (
        not schema_errors
        and slide_no_integrity
        and not speaker_notes_missing
        and not production_checklist_not_appendix
        and source_image_overlap_count == 0
    )
    return {
        "deck_id": deck_plan.get("deck_id"),
        "schema_valid": not schema_errors,
        "schema_errors": schema_errors,
        "slide_count": len(deck_plan.get("slides", [])),
        "section_count": len(deck_plan.get("sections", [])),
        "slide_no_integrity": slide_no_integrity,
        "speaker_notes_missing": speaker_notes_missing,
        "source_image_overlap_count": source_image_overlap_count,
        "production_checklist_not_appendix": production_checklist_not_appendix,
        "needs_source_count": sum(
            1 for slide in deck_plan.get("slides", []) if slide.get("needs_source")
        ),
        "needs_fact_check_count": sum(
            1 for slide in deck_plan.get("slides", []) if slide.get("needs_fact_check")
        ),
        "production_checklist_count": sum(
            1
            for slide in deck_plan.get("slides", [])
            if slide.get("slide_type") == "production_checklist"
            or slide.get("layout_type") == "appendix_checklist"
        ),
        "warnings": [*split_warnings, *visual_warnings],
        "passed": passed,
    }


def write_deck_plan_report(path: Path, results: list[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    passed_count = sum(1 for result in results if result.get("passed"))
    lines = [
        "# Piti Deck Plan Build Report",
        "",
        f"- Generated at: {datetime.now(UTC).isoformat()}",
        f"- Decks: {len(results)}",
        f"- Passed: {passed_count}",
        f"- Failed: {len(results) - passed_count}",
        "- Full PPT generator: not implemented in this milestone",
        "- LLM/API calls: none",
        "",
        "## Decks",
        "",
        (
            "| Deck | Slides | Sections | Schema | Notes | Overlap | "
            "Needs Source | Needs Fact Check | Checklist | Passed |"
        ),
        "|---|---:|---:|---|---|---:|---:|---:|---:|---|",
    ]
    for result in results:
        lines.append(
            "| {deck} | {slides} | {sections} | {schema} | {notes} | {overlap} | "
            "{needs_source} | {needs_fact_check} | {checklist} | {passed} |".format(
                deck=result["deck_id"],
                slides=result["slide_count"],
                sections=result["section_count"],
                schema="yes" if result["schema_valid"] else "no",
                notes="yes" if not result["speaker_notes_missing"] else "no",
                overlap=result["source_image_overlap_count"],
                needs_source=result["needs_source_count"],
                needs_fact_check=result["needs_fact_check_count"],
                checklist=result["production_checklist_count"],
                passed="yes" if result["passed"] else "no",
            )
        )
    lines.extend(["", "## Warnings", ""])
    for result in results:
        warnings = result.get("warnings", [])
        if not warnings:
            lines.append(f"- {result['deck_id']}: none")
        else:
            for warning in warnings[:12]:
                lines.append(f"- {result['deck_id']}: {warning}")
            if len(warnings) > 12:
                lines.append(f"- {result['deck_id']}: ... +{len(warnings) - 12} more")
    lines.extend(
        [
            "",
            "## Readiness",
            "",
            "- ready_for_storyboard_review: true",
            "- ready_for_ppt_generation: false",
            "- ready_for_production_piti_agent: false",
            "- ready_for_broadcast: false",
        ]
    )
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def build_default_deck_plans(
    *,
    report_path: Path = DEFAULT_REPORT_PATH,
) -> list[Path]:
    output_paths: list[Path] = []
    results: list[dict[str, Any]] = []
    for case in DEFAULT_CASES:
        storyline = _load_json(case.source_storyline_path)
        deck_plan = build_deck_plan_from_storyline(
            storyline,
            deck_id=case.deck_id,
            source_storyline_path=case.source_storyline_path,
        )
        _write_json(case.output_path, deck_plan)
        output_paths.append(case.output_path)
        result = validate_deck_plan(deck_plan)
        result["priority"] = case.priority
        result["path"] = str(case.output_path.relative_to(paths.REPO_ROOT))
        results.append(result)
    write_deck_plan_report(report_path, results)
    output_paths.append(report_path)
    return output_paths


@app.callback(invoke_without_command=True)
def main(
    input_path: Annotated[
        Path | None,
        typer.Option("--input", help="Single Anny storyline JSON to convert."),
    ] = None,
    output_path: Annotated[
        Path | None,
        typer.Option("--output", help="Deck plan JSON output path for single conversion."),
    ] = None,
    deck_id: Annotated[
        str | None,
        typer.Option("--deck-id", help="Deck id for single conversion."),
    ] = None,
    report_path: Annotated[
        Path,
        typer.Option("--report", help="Markdown build report path for default conversions."),
    ] = DEFAULT_REPORT_PATH,
) -> None:
    """Build Piti deck plan JSON from Anny storyline JSON without rendering PPTX."""
    if input_path:
        if output_path is None:
            raise typer.BadParameter("--output is required with --input")
        storyline = _load_json(input_path)
        deck_plan = build_deck_plan_from_storyline(
            storyline,
            deck_id=deck_id or input_path.stem,
            source_storyline_path=input_path,
        )
        _write_json(output_path, deck_plan)
        result = validate_deck_plan(deck_plan)
        console.print(
            f"[green]Wrote {output_path} "
            f"(schema_valid={result['schema_valid']}, passed={result['passed']}).[/green]"
        )
        raise typer.Exit(0 if result["passed"] else 1)
    rendered = build_default_deck_plans(report_path=report_path)
    console.print(f"[green]Built {len(rendered)} Piti deck plan artifacts.[/green]")


if __name__ == "__main__":
    app()
