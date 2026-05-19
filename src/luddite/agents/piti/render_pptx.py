"""Render Piti deck plans into editable draft PPTX skeletons."""

from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import UTC, date, datetime
from pathlib import Path
from typing import Annotated, Any

import typer
from pptx import Presentation
from pptx.dml.color import RGBColor
from pptx.enum.text import PP_ALIGN
from pptx.util import Inches, Pt
from rich.console import Console

from luddite import paths
from luddite.agents.piti.build_deck_plan_from_storyline import validate_deck_plan
from luddite.utils.urls import canonicalize_url

app = typer.Typer(no_args_is_help=False)
console = Console()

SLIDE_W = 13.333
SLIDE_H = 7.5

DEFAULT_REPORT_PATH = (
    paths.REPORTS_DIR / f"piti_pptx_render_report_{date.today().isoformat()}.md"
)


@dataclass(frozen=True)
class PptxRenderCase:
    deck_plan_path: Path
    output_path: Path


DEFAULT_CASES = [
    PptxRenderCase(
        deck_plan_path=paths.PITI_DECK_PLANS_DIR / "ai_knowledge_institution_deck_plan.json",
        output_path=paths.PPTX_OUTPUT_DIR / "ai_knowledge_institution_draft.pptx",
    ),
    PptxRenderCase(
        deck_plan_path=paths.PITI_DECK_PLANS_DIR / "productive_finance_policy_deck_plan.json",
        output_path=paths.PPTX_OUTPUT_DIR / "productive_finance_policy_draft.pptx",
    ),
]


def _display_path(path: Path) -> str:
    try:
        return str(path.resolve().relative_to(paths.REPO_ROOT))
    except ValueError:
        return str(path)

THEME = {
    "ink": RGBColor(24, 28, 35),
    "muted": RGBColor(86, 96, 112),
    "line": RGBColor(210, 216, 224),
    "paper": RGBColor(248, 249, 250),
    "accent": RGBColor(14, 121, 130),
    "accent_dark": RGBColor(15, 86, 96),
    "warn": RGBColor(191, 111, 36),
    "light": RGBColor(255, 255, 255),
}


def _load_json(path: Path) -> dict[str, Any]:
    with path.open(encoding="utf-8") as source:
        payload = json.load(source)
    if not isinstance(payload, dict):
        raise ValueError(f"Expected JSON object at {path}")
    return payload


def _as_list(value: Any) -> list[Any]:
    return value if isinstance(value, list) else []


def _body_lines(slide: dict[str, Any]) -> list[str]:
    return [str(item) for item in _as_list(slide.get("body")) if str(item).strip()]


def _fill(shape: Any, color: RGBColor) -> None:
    shape.fill.solid()
    shape.fill.fore_color.rgb = color


def _line(shape: Any, color: RGBColor = THEME["line"], width: float = 1.0) -> None:
    shape.line.color.rgb = color
    shape.line.width = Pt(width)


def _no_line(shape: Any) -> None:
    shape.line.fill.background()


def _textbox(
    slide: Any,
    left: float,
    top: float,
    width: float,
    height: float,
    text: str = "",
    *,
    font_size: int = 24,
    bold: bool = False,
    color: RGBColor = THEME["ink"],
    align: PP_ALIGN | None = None,
) -> Any:
    shape = slide.shapes.add_textbox(Inches(left), Inches(top), Inches(width), Inches(height))
    frame = shape.text_frame
    frame.clear()
    frame.word_wrap = True
    paragraph = frame.paragraphs[0]
    paragraph.text = text
    if align is not None:
        paragraph.alignment = align
    for run in paragraph.runs:
        run.font.name = "Malgun Gothic"
        run.font.size = Pt(font_size)
        run.font.bold = bold
        run.font.color.rgb = color
    return shape


def _body_box(
    slide: Any,
    body: list[str],
    left: float,
    top: float,
    width: float,
    height: float,
    *,
    font_size: int = 22,
) -> Any:
    shape = slide.shapes.add_textbox(Inches(left), Inches(top), Inches(width), Inches(height))
    frame = shape.text_frame
    frame.clear()
    frame.word_wrap = True
    if not body:
        paragraph = frame.paragraphs[0]
        paragraph.text = ""
        return shape
    for index, line in enumerate(body):
        paragraph = frame.paragraphs[0] if index == 0 else frame.add_paragraph()
        paragraph.text = line
        paragraph.level = 0
        paragraph.space_after = Pt(8)
        for run in paragraph.runs:
            run.font.name = "Malgun Gothic"
            run.font.size = Pt(font_size)
            run.font.color.rgb = THEME["ink"]
    return shape


def _placeholder(
    slide: Any,
    slide_plan: dict[str, Any],
    left: float,
    top: float,
    width: float,
    height: float,
) -> None:
    visual_plan = slide_plan.get("visual_plan") or {}
    kind = visual_plan.get("kind") or "manual"
    if kind == "none":
        return
    label_by_kind = {
        "photo_candidate": "[이미지 후보]",
        "chart_candidate": "[차트 후보]",
        "diagram": "[비교 도식]",
        "screenshot_candidate": "[스크린샷 후보]",
        "ai_image_prompt": "[AI 이미지 프롬프트 후보]",
        "manual": "[수동 삽입 필요]",
    }
    label = label_by_kind.get(kind, "[수동 삽입 필요]")
    description = str(visual_plan.get("description") or "")
    shape = slide.shapes.add_shape(
        1,
        Inches(left),
        Inches(top),
        Inches(width),
        Inches(height),
    )
    _fill(shape, RGBColor(235, 241, 244))
    _line(shape, RGBColor(160, 174, 184), 1.25)
    text = f"{label}\n{description}".strip()
    frame = shape.text_frame
    frame.clear()
    frame.word_wrap = True
    paragraph = frame.paragraphs[0]
    paragraph.text = text
    paragraph.alignment = PP_ALIGN.CENTER
    for run in paragraph.runs:
        run.font.name = "Malgun Gothic"
        run.font.size = Pt(16)
        run.font.color.rgb = THEME["muted"]


def _add_footer(slide: Any, slide_plan: dict[str, Any]) -> None:
    flags = []
    if slide_plan.get("needs_source"):
        flags.append("needs_source")
    if slide_plan.get("needs_fact_check"):
        flags.append("needs_fact_check")
    if slide_plan.get("required_before_broadcast"):
        flags.append("before_broadcast")
    flag_text = " | ".join(flags) if flags else "draft skeleton"
    _textbox(
        slide,
        0.45,
        7.12,
        10.8,
        0.22,
        flag_text,
        font_size=8,
        color=THEME["muted"],
    )
    _textbox(
        slide,
        11.6,
        7.12,
        1.25,
        0.22,
        f"{slide_plan.get('slide_no', ''):02}",
        font_size=8,
        color=THEME["muted"],
        align=PP_ALIGN.RIGHT,
    )


def _slide_background(slide: Any, *, dark: bool = False) -> None:
    bg = slide.background
    bg.fill.solid()
    bg.fill.fore_color.rgb = THEME["ink"] if dark else THEME["paper"]


def _render_title(slide: Any, slide_plan: dict[str, Any]) -> None:
    _slide_background(slide, dark=True)
    _textbox(
        slide,
        0.8,
        1.35,
        11.8,
        1.7,
        str(slide_plan.get("headline") or ""),
        font_size=38,
        bold=True,
        color=THEME["light"],
    )
    _body_box(slide, _body_lines(slide_plan), 0.85, 3.45, 10.8, 1.4, font_size=22)
    for shape in slide.shapes:
        if getattr(shape, "has_text_frame", False) and shape.text_frame.text:
            for paragraph in shape.text_frame.paragraphs:
                for run in paragraph.runs:
                    if run.font.color.rgb == THEME["ink"]:
                        run.font.color.rgb = RGBColor(225, 233, 238)


def _render_section_title(slide: Any, slide_plan: dict[str, Any]) -> None:
    _slide_background(slide, dark=False)
    bar = slide.shapes.add_shape(1, Inches(0), Inches(0), Inches(13.333), Inches(7.5))
    _fill(bar, THEME["accent_dark"])
    _no_line(bar)
    _textbox(
        slide,
        0.85,
        2.35,
        11.6,
        1.2,
        str(slide_plan.get("headline") or ""),
        font_size=34,
        bold=True,
        color=THEME["light"],
    )
    _body_box(slide, _body_lines(slide_plan), 0.9, 3.75, 10.8, 1.0, font_size=20)
    for shape in slide.shapes:
        if getattr(shape, "has_text_frame", False):
            for paragraph in shape.text_frame.paragraphs:
                for run in paragraph.runs:
                    if run.font.color.rgb == THEME["ink"]:
                        run.font.color.rgb = RGBColor(226, 238, 241)


def _render_big_headline(slide: Any, slide_plan: dict[str, Any]) -> None:
    _slide_background(slide)
    _textbox(
        slide,
        0.7,
        1.0,
        11.8,
        1.4,
        str(slide_plan.get("headline") or ""),
        font_size=34,
        bold=True,
        color=THEME["ink"],
    )
    _body_box(slide, _body_lines(slide_plan), 0.78, 2.8, 10.8, 2.9, font_size=24)
    _placeholder(slide, slide_plan, 9.6, 4.8, 2.6, 1.2)


def _render_headline_body(slide: Any, slide_plan: dict[str, Any]) -> None:
    _slide_background(slide)
    _textbox(
        slide,
        0.65,
        0.55,
        7.7,
        0.9,
        str(slide_plan.get("headline") or ""),
        font_size=28,
        bold=True,
    )
    _body_box(slide, _body_lines(slide_plan), 0.75, 1.75, 7.2, 4.7, font_size=20)
    _placeholder(slide, slide_plan, 8.55, 1.55, 4.05, 4.65)


def _render_quote(slide: Any, slide_plan: dict[str, Any]) -> None:
    _slide_background(slide)
    box = slide.shapes.add_shape(1, Inches(0.8), Inches(1.0), Inches(11.7), Inches(4.9))
    _fill(box, THEME["light"])
    _line(box, THEME["line"], 1.2)
    _textbox(
        slide,
        1.1,
        1.25,
        11.0,
        1.0,
        str(slide_plan.get("headline") or ""),
        font_size=28,
        bold=True,
    )
    _body_box(slide, _body_lines(slide_plan), 1.18, 2.55, 10.6, 2.7, font_size=20)


def _render_question(slide: Any, slide_plan: dict[str, Any]) -> None:
    _slide_background(slide)
    _textbox(
        slide,
        1.0,
        1.35,
        11.3,
        1.4,
        str(slide_plan.get("headline") or ""),
        font_size=32,
        bold=True,
        align=PP_ALIGN.CENTER,
    )
    _body_box(slide, _body_lines(slide_plan), 1.55, 3.2, 10.2, 2.2, font_size=23)


def _render_comparison(slide: Any, slide_plan: dict[str, Any]) -> None:
    _slide_background(slide)
    _textbox(
        slide,
        0.65,
        0.55,
        12.0,
        0.85,
        str(slide_plan.get("headline") or ""),
        font_size=27,
        bold=True,
    )
    body = _body_lines(slide_plan)
    midpoint = max(1, (len(body) + 1) // 2)
    left_body = body[:midpoint]
    right_body = body[midpoint:]
    left = slide.shapes.add_shape(1, Inches(0.8), Inches(1.75), Inches(5.75), Inches(4.45))
    right = slide.shapes.add_shape(1, Inches(6.75), Inches(1.75), Inches(5.75), Inches(4.45))
    _fill(left, THEME["light"])
    _fill(right, RGBColor(239, 246, 247))
    _line(left)
    _line(right, RGBColor(170, 202, 206))
    _body_box(slide, left_body, 1.05, 2.05, 5.25, 3.7, font_size=19)
    _body_box(slide, right_body, 7.0, 2.05, 5.25, 3.7, font_size=19)


def _render_placeholder_layout(slide: Any, slide_plan: dict[str, Any]) -> None:
    _slide_background(slide)
    _textbox(
        slide,
        0.65,
        0.5,
        12.0,
        0.85,
        str(slide_plan.get("headline") or ""),
        font_size=27,
        bold=True,
    )
    _placeholder(slide, slide_plan, 1.15, 1.65, 11.0, 3.0)
    _body_box(slide, _body_lines(slide_plan), 1.15, 4.95, 11.0, 1.35, font_size=17)


def _render_checklist(slide: Any, slide_plan: dict[str, Any], *, appendix: bool = False) -> None:
    _slide_background(slide)
    prefix = "[내부 체크리스트] " if appendix else ""
    _textbox(
        slide,
        0.65,
        0.55,
        12.0,
        0.85,
        prefix + str(slide_plan.get("headline") or ""),
        font_size=26,
        bold=True,
        color=THEME["warn"] if appendix else THEME["ink"],
    )
    _body_box(slide, _body_lines(slide_plan), 0.9, 1.65, 11.4, 4.9, font_size=18)


def _render_slide(prs: Presentation, slide_plan: dict[str, Any]) -> None:
    slide = prs.slides.add_slide(prs.slide_layouts[6])
    layout_type = slide_plan.get("layout_type") or "headline_body"
    if layout_type == "title":
        _render_title(slide, slide_plan)
    elif layout_type == "section_title":
        _render_section_title(slide, slide_plan)
    elif layout_type == "big_headline":
        _render_big_headline(slide, slide_plan)
    elif layout_type == "quote":
        _render_quote(slide, slide_plan)
    elif layout_type in {"question", "closing_question"}:
        _render_question(slide, slide_plan)
    elif layout_type == "comparison":
        _render_comparison(slide, slide_plan)
    elif layout_type in {"chart_placeholder", "image_placeholder", "timeline"}:
        _render_placeholder_layout(slide, slide_plan)
    elif layout_type in {"checklist", "appendix_checklist"}:
        _render_checklist(slide, slide_plan, appendix=layout_type == "appendix_checklist")
    else:
        _render_headline_body(slide, slide_plan)
    _add_footer(slide, slide_plan)
    _set_notes(slide, slide_plan)


def _note_json(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False, indent=2)


def _set_notes(slide: Any, slide_plan: dict[str, Any]) -> None:
    visual_plan = slide_plan.get("visual_plan") or {}
    copyright_risk = bool(visual_plan.get("copyright_risk"))
    lines = [
        f"slide_no: {slide_plan.get('slide_no')}",
        f"layout_type: {slide_plan.get('layout_type')}",
        f"source_slide_refs: {_note_json(_as_list(slide_plan.get('source_slide_refs')))}",
        "",
        "source_urls:",
    ]
    lines.extend(f"- {url}" for url in _as_list(slide_plan.get("source_urls")))
    lines.append("image_urls:")
    lines.extend(f"- {url}" for url in _as_list(slide_plan.get("image_urls")))
    lines.extend(
        [
            "",
            "flags:",
            f"- needs_source: {bool(slide_plan.get('needs_source'))}",
            f"- needs_fact_check: {bool(slide_plan.get('needs_fact_check'))}",
            f"- required_before_broadcast: {bool(slide_plan.get('required_before_broadcast'))}",
            f"- copyright_risk: {copyright_risk}",
            "",
            "visual_plan:",
            _note_json(visual_plan),
            "",
            "edit_notes:",
        ]
    )
    lines.extend(f"- {note}" for note in _as_list(slide_plan.get("edit_notes")))
    if slide_plan.get("layout_type") == "appendix_checklist":
        lines.extend(["", "internal_note: appendix/internal checklist, not a broadcast slide"])
    if copyright_risk:
        lines.extend(["", "image_note: 이미지 저작권 확인 필요"])
    speaker_notes = str(slide_plan.get("speaker_notes") or "").strip()
    if speaker_notes:
        lines.extend(["", "speaker_notes:", speaker_notes])
    notes_frame = slide.notes_slide.notes_text_frame
    notes_frame.text = "\n".join(lines)


def _ordered_slides(deck_plan: dict[str, Any]) -> list[dict[str, Any]]:
    slides = list(deck_plan.get("slides", []))
    appendix = [
        slide
        for slide in slides
        if slide.get("slide_type") == "production_checklist"
        or slide.get("layout_type") == "appendix_checklist"
    ]
    main = [slide for slide in slides if slide not in appendix]
    return [*main, *appendix]


def render_deck_plan_to_pptx(deck_plan: dict[str, Any], output_path: Path) -> dict[str, Any]:
    validation = validate_deck_plan(deck_plan)
    prs = Presentation()
    prs.slide_width = Inches(SLIDE_W)
    prs.slide_height = Inches(SLIDE_H)
    for slide_plan in _ordered_slides(deck_plan):
        _render_slide(prs, slide_plan)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    prs.save(output_path)
    result = render_result(deck_plan, output_path, validation)
    return result


def _source_image_overlap_count(deck_plan: dict[str, Any]) -> int:
    count = 0
    for slide in deck_plan.get("slides", []):
        sources = {
            canonicalize_url(str(url))
            for url in _as_list(slide.get("source_urls"))
            if str(url).strip()
        }
        images = {
            canonicalize_url(str(url))
            for url in _as_list(slide.get("image_urls"))
            if str(url).strip()
        }
        if sources & images:
            count += 1
    return count


def render_result(
    deck_plan: dict[str, Any],
    output_path: Path,
    validation: dict[str, Any],
) -> dict[str, Any]:
    slides = deck_plan.get("slides", [])
    appendix_count = sum(
        1
        for slide in slides
        if slide.get("slide_type") == "production_checklist"
        or slide.get("layout_type") == "appendix_checklist"
    )
    visual_placeholder_count = sum(
        1
        for slide in slides
        if (slide.get("visual_plan") or {}).get("kind") not in {None, "none"}
    )
    missing_notes = [
        slide.get("slide_no")
        for slide in slides
        if not str(slide.get("speaker_notes") or slide.get("notes") or "").strip()
    ]
    return {
        "deck_id": deck_plan.get("deck_id"),
        "input_deck_plan_path": deck_plan.get("_input_path"),
        "output_pptx_path": _display_path(output_path),
        "slide_count": len(slides),
        "section_count": len(deck_plan.get("sections", [])),
        "appendix_internal_slide_count": appendix_count,
        "needs_source_count": sum(1 for slide in slides if slide.get("needs_source")),
        "needs_fact_check_count": sum(1 for slide in slides if slide.get("needs_fact_check")),
        "visual_placeholder_count": visual_placeholder_count,
        "slides_with_missing_notes": missing_notes,
        "source_image_overlap_count": _source_image_overlap_count(deck_plan),
        "schema_valid": validation.get("schema_valid"),
        "warnings": validation.get("warnings", []),
        "passed": (
            output_path.exists()
            and not missing_notes
            and _source_image_overlap_count(deck_plan) == 0
        ),
    }


def write_render_report(path: Path, results: list[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    passed = sum(1 for result in results if result.get("passed"))
    lines = [
        "# Piti PPTX Render Report",
        "",
        f"- Generated at: {datetime.now(UTC).isoformat()}",
        f"- Rendered deck count: {len(results)}",
        f"- Passed: {passed}",
        f"- Failed: {len(results) - passed}",
        "- Renderer type: scaffold PPTX skeleton",
        "- Production Piti agent: not implemented",
        "- Image auto collection/insertion: none",
        "- LLM/API calls: none",
        "",
        "## Decks",
        "",
        (
            "| Deck | Slides | Sections | Appendix | Needs Source | Needs Fact Check | "
            "Visual Placeholders | Missing Notes | Overlap | PPTX | Passed |"
        ),
        "|---|---:|---:|---:|---:|---:|---:|---:|---:|---|---|",
    ]
    for result in results:
        lines.append(
            "| {deck} | {slides} | {sections} | {appendix} | {needs_source} | "
            "{needs_fact_check} | {visuals} | {missing_notes} | {overlap} | {pptx} | "
            "{passed} |".format(
                deck=result.get("deck_id"),
                slides=result.get("slide_count"),
                sections=result.get("section_count"),
                appendix=result.get("appendix_internal_slide_count"),
                needs_source=result.get("needs_source_count"),
                needs_fact_check=result.get("needs_fact_check_count"),
                visuals=result.get("visual_placeholder_count"),
                missing_notes=len(result.get("slides_with_missing_notes", [])),
                overlap=result.get("source_image_overlap_count"),
                pptx=result.get("output_pptx_path"),
                passed="yes" if result.get("passed") else "no",
            )
        )
    lines.extend(["", "## Warnings", ""])
    for result in results:
        warnings = result.get("warnings", [])
        if not warnings:
            lines.append(f"- {result.get('deck_id')}: none")
        else:
            for warning in warnings[:12]:
                lines.append(f"- {result.get('deck_id')}: {warning}")
            if len(warnings) > 12:
                lines.append(f"- {result.get('deck_id')}: ... +{len(warnings) - 12} more")
    lines.extend(
        [
            "",
            "## Readiness",
            "",
            "- ready_for_ppt_generation: true (scaffold only)",
            "- ready_for_production_piti_agent: false",
            "- ready_for_broadcast: false",
        ]
    )
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def render_default_decks(report_path: Path = DEFAULT_REPORT_PATH) -> list[Path]:
    output_paths: list[Path] = []
    results: list[dict[str, Any]] = []
    for case in DEFAULT_CASES:
        deck_plan = _load_json(case.deck_plan_path)
        deck_plan["_input_path"] = str(case.deck_plan_path.relative_to(paths.REPO_ROOT))
        result = render_deck_plan_to_pptx(deck_plan, case.output_path)
        result["input_deck_plan_path"] = str(case.deck_plan_path.relative_to(paths.REPO_ROOT))
        results.append(result)
        output_paths.append(case.output_path)
    write_render_report(report_path, results)
    output_paths.append(report_path)
    return output_paths


@app.callback(invoke_without_command=True)
def main(
    input_path: Annotated[
        Path | None,
        typer.Option("--input", help="Single Piti deck plan JSON to render."),
    ] = None,
    output_path: Annotated[
        Path | None,
        typer.Option("--output", help="PPTX output path for single render."),
    ] = None,
    report_path: Annotated[
        Path,
        typer.Option("--report", help="Markdown render report path for default renders."),
    ] = DEFAULT_REPORT_PATH,
) -> None:
    """Render deck plan JSON into editable PPTX skeletons."""
    if input_path:
        if output_path is None:
            raise typer.BadParameter("--output is required with --input")
        deck_plan = _load_json(input_path)
        deck_plan["_input_path"] = str(input_path)
        result = render_deck_plan_to_pptx(deck_plan, output_path)
        console.print(
            f"[green]Rendered {output_path} "
            f"(slides={result['slide_count']}, passed={result['passed']}).[/green]"
        )
        raise typer.Exit(0 if result["passed"] else 1)
    rendered = render_default_decks(report_path=report_path)
    console.print(f"[green]Rendered {len(rendered)} Piti PPTX artifacts.[/green]")


if __name__ == "__main__":
    app()
