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
from luddite.parsers.parse_pptx import parse_presentation
from luddite.utils.urls import canonicalize_url

app = typer.Typer(no_args_is_help=False)
console = Console()

SLIDE_W = 13.333
SLIDE_H = 7.5

DEFAULT_REPORT_PATH = (
    paths.REPORTS_DIR / f"piti_pptx_render_report_{date.today().isoformat()}.md"
)
DEFAULT_STYLE_PROFILE_PATH = paths.STYLE_PROFILES_DIR / "syukaworld_ppt_style_profile.json"


@dataclass(frozen=True)
class PptxRenderCase:
    deck_plan_path: Path
    output_path: Path
    style_profile_path: Path | None = None


@dataclass(frozen=True)
class PptxStyle:
    profile_path: Path | None
    loaded: bool
    slide_width_in: float
    slide_height_in: float
    font_family: str
    fallback_font: str
    accent: RGBColor
    layout_patterns: dict[str, dict[str, Any]]
    raw_profile: dict[str, Any]


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

STYLED_CASES = [
    PptxRenderCase(
        deck_plan_path=paths.PITI_DECK_PLANS_DIR / "ai_knowledge_institution_deck_plan.json",
        output_path=paths.PPTX_OUTPUT_DIR / "ai_knowledge_institution_styled_draft.pptx",
        style_profile_path=DEFAULT_STYLE_PROFILE_PATH,
    ),
    PptxRenderCase(
        deck_plan_path=paths.PITI_DECK_PLANS_DIR / "productive_finance_policy_deck_plan.json",
        output_path=paths.PPTX_OUTPUT_DIR / "productive_finance_policy_styled_draft.pptx",
        style_profile_path=DEFAULT_STYLE_PROFILE_PATH,
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


def _rgb_from_hex(value: str | None, fallback: RGBColor) -> RGBColor:
    if not value or not value.startswith("#") or len(value) != 7:
        return fallback
    try:
        return RGBColor(
            int(value[1:3], 16),
            int(value[3:5], 16),
            int(value[5:7], 16),
        )
    except ValueError:
        return fallback


def _cm_to_in(value: float | int | None, fallback: float) -> float:
    if value is None:
        return fallback
    return round(float(value) / 2.54, 3)


def _style_font(profile: dict[str, Any]) -> str:
    font_resolution = profile.get("font_resolution") or {}
    return (
        font_resolution.get("fallback_font")
        or (font_resolution.get("resolved_font_candidates") or [None])[0]
        or "Malgun Gothic"
    )


def load_style_profile(path: Path | None) -> PptxStyle:
    if path is None or not path.exists():
        return PptxStyle(
            profile_path=path,
            loaded=False,
            slide_width_in=SLIDE_W,
            slide_height_in=SLIDE_H,
            font_family="Malgun Gothic",
            fallback_font="Malgun Gothic",
            accent=RGBColor(14, 121, 130),
            layout_patterns={},
            raw_profile={},
        )
    profile = _load_json(path)
    slide_size = profile.get("slide_size") or {}
    layout_patterns = profile.get("layout_patterns") or {}
    common_colors = profile.get("common_colors") or []
    accent_value = common_colors[0]["value"] if common_colors else "#FF0000"
    return PptxStyle(
        profile_path=path,
        loaded=True,
        slide_width_in=float(slide_size.get("width_in") or SLIDE_W),
        slide_height_in=float(slide_size.get("height_in") or SLIDE_H),
        font_family=_style_font(profile),
        fallback_font="Malgun Gothic",
        accent=_rgb_from_hex(accent_value, RGBColor(255, 0, 0)),
        layout_patterns=layout_patterns,
        raw_profile=profile,
    )


def _layout_box(
    style: PptxStyle,
    layout_type: str,
    fallback: tuple[float, float, float, float],
) -> tuple[float, float, float, float]:
    pattern = style.layout_patterns.get(layout_type) or {}
    return (
        _cm_to_in(pattern.get("x_cm_median"), fallback[0]),
        _cm_to_in(pattern.get("y_cm_median"), fallback[1]),
        _cm_to_in(pattern.get("w_cm_median"), fallback[2]),
        _cm_to_in(pattern.get("h_cm_median"), fallback[3]),
    )


def _layout_font_size(style: PptxStyle, layout_type: str, fallback: int) -> int:
    pattern = style.layout_patterns.get(layout_type) or {}
    value = pattern.get("font_size_pt_median")
    return int(round(float(value))) if value else fallback


def _layout_color(style: PptxStyle, layout_type: str, fallback: RGBColor) -> RGBColor:
    pattern = style.layout_patterns.get(layout_type) or {}
    return _rgb_from_hex(pattern.get("font_color_top"), fallback)


def _body_font_size(style: PptxStyle, body: list[str], fallback: int) -> int:
    if not style.loaded:
        return fallback
    max_len = max((len(line) for line in body), default=0)
    if len(body) > 4 or max_len > 95:
        return 20
    if len(body) > 2 or max_len > 65:
        return 24
    return 28


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
    style: PptxStyle | None = None,
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
        run.font.name = style.font_family if style and style.loaded else "Malgun Gothic"
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
    color: RGBColor = THEME["ink"],
    style: PptxStyle | None = None,
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
            run.font.name = style.font_family if style and style.loaded else "Malgun Gothic"
            run.font.size = Pt(font_size)
            run.font.color.rgb = color
    return shape


def _placeholder(
    slide: Any,
    slide_plan: dict[str, Any],
    left: float,
    top: float,
    width: float,
    height: float,
    *,
    style: PptxStyle | None = None,
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
    placeholder_fill = (
        RGBColor(245, 245, 245) if style and style.loaded else RGBColor(235, 241, 244)
    )
    placeholder_line = (
        RGBColor(190, 190, 190) if style and style.loaded else RGBColor(160, 174, 184)
    )
    _fill(shape, placeholder_fill)
    _line(shape, placeholder_line, 1.0)
    text = f"{label}\n{description}".strip()
    frame = shape.text_frame
    frame.clear()
    frame.word_wrap = True
    paragraph = frame.paragraphs[0]
    paragraph.text = text
    paragraph.alignment = PP_ALIGN.CENTER
    for run in paragraph.runs:
        run.font.name = style.font_family if style and style.loaded else "Malgun Gothic"
        run.font.size = Pt(16)
        run.font.color.rgb = THEME["muted"]


def _add_footer(slide: Any, slide_plan: dict[str, Any], style: PptxStyle) -> None:
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
        style=style,
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
        style=style,
    )


def _slide_background(slide: Any, *, dark: bool = False) -> None:
    bg = slide.background
    bg.fill.solid()
    bg.fill.fore_color.rgb = THEME["ink"] if dark else THEME["paper"]


def _render_title(slide: Any, slide_plan: dict[str, Any], style: PptxStyle) -> None:
    _slide_background(slide, dark=False if style.loaded else True)
    left, top, width, height = _layout_box(style, "title", (0.8, 1.35, 11.8, 1.7))
    headline_color = style.accent if style.loaded else THEME["light"]
    _textbox(
        slide,
        left,
        top,
        width,
        height,
        str(slide_plan.get("headline") or ""),
        font_size=_layout_font_size(style, "title", 38),
        bold=True,
        color=headline_color,
        style=style,
    )
    body = _body_lines(slide_plan)
    _body_box(
        slide,
        body,
        left + 0.1,
        min(top + 2.1, 6.2),
        min(width, 10.8),
        1.0,
        font_size=_body_font_size(style, body, 22),
        color=style.accent if style.loaded else THEME["ink"],
        style=style,
    )
    for shape in slide.shapes:
        if getattr(shape, "has_text_frame", False) and shape.text_frame.text:
            for paragraph in shape.text_frame.paragraphs:
                for run in paragraph.runs:
                    if not style.loaded and run.font.color.rgb == THEME["ink"]:
                        run.font.color.rgb = RGBColor(225, 233, 238)


def _render_section_title(slide: Any, slide_plan: dict[str, Any], style: PptxStyle) -> None:
    _slide_background(slide, dark=False)
    if not style.loaded:
        bar = slide.shapes.add_shape(1, Inches(0), Inches(0), Inches(13.333), Inches(7.5))
        _fill(bar, THEME["accent_dark"])
        _no_line(bar)
    left, top, width, height = _layout_box(style, "section_title", (0.85, 2.35, 11.6, 1.2))
    _textbox(
        slide,
        left,
        top,
        width,
        height,
        str(slide_plan.get("headline") or ""),
        font_size=_layout_font_size(style, "section_title", 34),
        bold=True,
        color=style.accent if style.loaded else THEME["light"],
        style=style,
    )
    body = _body_lines(slide_plan)
    _body_box(
        slide,
        body,
        left,
        min(top + 1.35, 6.2),
        min(width, 10.8),
        1.0,
        font_size=_body_font_size(style, body, 20),
        color=style.accent if style.loaded else THEME["ink"],
        style=style,
    )
    for shape in slide.shapes:
        if getattr(shape, "has_text_frame", False):
            for paragraph in shape.text_frame.paragraphs:
                for run in paragraph.runs:
                    if not style.loaded and run.font.color.rgb == THEME["ink"]:
                        run.font.color.rgb = RGBColor(226, 238, 241)


def _render_big_headline(slide: Any, slide_plan: dict[str, Any], style: PptxStyle) -> None:
    _slide_background(slide)
    left, top, width, height = _layout_box(style, "big_headline", (0.7, 1.0, 11.8, 1.4))
    _textbox(
        slide,
        left,
        top,
        width,
        height,
        str(slide_plan.get("headline") or ""),
        font_size=_layout_font_size(style, "big_headline", 34),
        bold=True,
        color=_layout_color(style, "big_headline", THEME["ink"]),
        style=style,
    )
    body = _body_lines(slide_plan)
    _body_box(
        slide,
        body,
        0.78,
        max(top + height + 0.35, 2.8),
        10.8,
        2.9,
        font_size=_body_font_size(style, body, 24),
        color=style.accent if style.loaded else THEME["ink"],
        style=style,
    )
    _placeholder(slide, slide_plan, 9.6, 4.8, 2.6, 1.2, style=style)


def _render_headline_body(slide: Any, slide_plan: dict[str, Any], style: PptxStyle) -> None:
    _slide_background(slide)
    left, top, width, height = _layout_box(style, "headline_body", (0.65, 1.75, 7.7, 4.7))
    headline_top = max(0.45, top - 0.95) if style.loaded else 0.55
    headline_color = _layout_color(style, "headline_body", THEME["ink"])
    _textbox(
        slide,
        left,
        headline_top,
        min(width, 12.0),
        0.75 if style.loaded else 0.9,
        str(slide_plan.get("headline") or ""),
        font_size=_layout_font_size(style, "headline_body", 28),
        bold=True,
        color=headline_color,
        style=style,
    )
    body = _body_lines(slide_plan)
    _body_box(
        slide,
        body,
        left,
        top,
        width,
        height,
        font_size=_body_font_size(style, body, 20),
        color=headline_color if style.loaded else THEME["ink"],
        style=style,
    )
    if style.loaded:
        _placeholder(slide, slide_plan, 8.95, 1.55, 3.6, 4.65, style=style)
    else:
        _placeholder(slide, slide_plan, 8.55, 1.55, 4.05, 4.65, style=style)


def _render_quote(slide: Any, slide_plan: dict[str, Any], style: PptxStyle) -> None:
    _slide_background(slide)
    left, top, width, height = _layout_box(style, "quote", (0.8, 1.0, 11.7, 4.9))
    box = slide.shapes.add_shape(
        1,
        Inches(left),
        Inches(max(0.8, top - 0.75)),
        Inches(min(11.7, width + 0.6)),
        Inches(max(3.4, height + 2.2)),
    )
    _fill(box, THEME["light"])
    _line(box, THEME["line"], 1.2)
    _textbox(
        slide,
        left,
        max(1.0, top - 0.55),
        min(11.0, width),
        0.95,
        str(slide_plan.get("headline") or ""),
        font_size=_layout_font_size(style, "quote", 28),
        bold=True,
        color=_layout_color(style, "quote", THEME["ink"]),
        style=style,
    )
    body = _body_lines(slide_plan)
    _body_box(
        slide,
        body,
        left,
        top + 0.8,
        min(10.6, width),
        2.7,
        font_size=_body_font_size(style, body, 20),
        color=_layout_color(style, "quote", THEME["ink"]) if style.loaded else THEME["ink"],
        style=style,
    )


def _render_question(slide: Any, slide_plan: dict[str, Any], style: PptxStyle) -> None:
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
        color=style.accent if style.loaded else THEME["ink"],
        align=PP_ALIGN.CENTER,
        style=style,
    )
    body = _body_lines(slide_plan)
    _body_box(
        slide,
        body,
        1.55,
        3.2,
        10.2,
        2.2,
        font_size=_body_font_size(style, body, 23),
        color=style.accent if style.loaded else THEME["ink"],
        style=style,
    )


def _render_comparison(slide: Any, slide_plan: dict[str, Any], style: PptxStyle) -> None:
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
        color=style.accent if style.loaded else THEME["ink"],
        style=style,
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
    _body_box(
        slide,
        left_body,
        1.05,
        2.05,
        5.25,
        3.7,
        font_size=_body_font_size(style, left_body, 19),
        color=style.accent if style.loaded else THEME["ink"],
        style=style,
    )
    _body_box(
        slide,
        right_body,
        7.0,
        2.05,
        5.25,
        3.7,
        font_size=_body_font_size(style, right_body, 19),
        color=style.accent if style.loaded else THEME["ink"],
        style=style,
    )


def _render_placeholder_layout(slide: Any, slide_plan: dict[str, Any], style: PptxStyle) -> None:
    _slide_background(slide)
    layout_type = "image_heavy"
    if slide_plan.get("layout_type") == "chart_placeholder":
        layout_type = "chart"
    left, top, width, height = _layout_box(style, layout_type, (1.15, 1.65, 11.0, 3.0))
    _textbox(
        slide,
        left,
        max(0.45, top - 0.95),
        min(12.0, width),
        0.85,
        str(slide_plan.get("headline") or ""),
        font_size=_layout_font_size(style, layout_type, 27),
        bold=True,
        color=_layout_color(style, layout_type, THEME["ink"]),
        style=style,
    )
    _placeholder(slide, slide_plan, left, top, width, max(2.0, height), style=style)
    body = _body_lines(slide_plan)
    _body_box(
        slide,
        body,
        left,
        min(top + max(2.0, height) + 0.35, 5.4),
        min(11.0, width),
        1.35,
        font_size=_body_font_size(style, body, 17),
        color=style.accent if style.loaded else THEME["ink"],
        style=style,
    )


def _render_checklist(
    slide: Any,
    slide_plan: dict[str, Any],
    *,
    appendix: bool = False,
    style: PptxStyle,
) -> None:
    _slide_background(slide)
    prefix = "[내부 체크리스트] " if appendix else ""
    left, top, width, height = _layout_box(style, "checklist", (0.65, 0.55, 12.0, 0.85))
    _textbox(
        slide,
        left,
        top,
        width,
        height,
        prefix + str(slide_plan.get("headline") or ""),
        font_size=_layout_font_size(style, "checklist", 26),
        bold=True,
        color=THEME["warn"] if appendix else _layout_color(style, "checklist", THEME["ink"]),
        style=style,
    )
    body = _body_lines(slide_plan)
    _body_box(
        slide,
        body,
        0.9,
        max(top + height + 0.25, 1.65),
        11.4,
        4.9,
        font_size=_body_font_size(style, body, 18),
        color=style.accent if style.loaded and not appendix else THEME["ink"],
        style=style,
    )


def _render_slide(prs: Presentation, slide_plan: dict[str, Any], style: PptxStyle) -> None:
    slide = prs.slides.add_slide(prs.slide_layouts[6])
    layout_type = slide_plan.get("layout_type") or "headline_body"
    if layout_type == "title":
        _render_title(slide, slide_plan, style)
    elif layout_type == "section_title":
        _render_section_title(slide, slide_plan, style)
    elif layout_type == "big_headline":
        _render_big_headline(slide, slide_plan, style)
    elif layout_type == "quote":
        _render_quote(slide, slide_plan, style)
    elif layout_type in {"question", "closing_question"}:
        _render_question(slide, slide_plan, style)
    elif layout_type == "comparison":
        _render_comparison(slide, slide_plan, style)
    elif layout_type in {"chart_placeholder", "image_placeholder", "timeline"}:
        _render_placeholder_layout(slide, slide_plan, style)
    elif layout_type in {"checklist", "appendix_checklist"}:
        _render_checklist(
            slide,
            slide_plan,
            appendix=layout_type == "appendix_checklist",
            style=style,
        )
    else:
        _render_headline_body(slide, slide_plan, style)
    _add_footer(slide, slide_plan, style)
    _set_notes(slide, slide_plan, style)


def _note_json(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False, indent=2)


def _set_notes(slide: Any, slide_plan: dict[str, Any], style: PptxStyle) -> None:
    visual_plan = slide_plan.get("visual_plan") or {}
    copyright_risk = bool(visual_plan.get("copyright_risk"))
    lines = [
        f"slide_no: {slide_plan.get('slide_no')}",
        f"layout_type: {slide_plan.get('layout_type')}",
        f"style_profile_loaded: {style.loaded}",
        f"style_profile_path: {_display_path(style.profile_path) if style.profile_path else None}",
        f"applied_font_family: {style.font_family}",
        f"applied_fallback_font: {style.fallback_font}",
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


def _long_body_slides(deck_plan: dict[str, Any]) -> list[int]:
    slide_nos = []
    for slide in deck_plan.get("slides", []):
        body = _body_lines(slide)
        total_chars = sum(len(line) for line in body)
        if len(body) > 4 or total_chars > 220 or any(len(line) > 100 for line in body):
            slide_nos.append(int(slide.get("slide_no") or 0))
    return slide_nos


def _applied_layout_count(deck_plan: dict[str, Any], style: PptxStyle) -> int:
    if not style.loaded:
        return 0
    aliases = {
        "chart_placeholder": "chart",
        "image_placeholder": "image_heavy",
        "timeline": "image_heavy",
    }
    count = 0
    for slide in deck_plan.get("slides", []):
        layout_type = slide.get("layout_type") or "headline_body"
        key = aliases.get(layout_type, layout_type)
        if key in style.layout_patterns:
            count += 1
    return count


def _parse_back_counts(output_path: Path) -> dict[str, Any]:
    parsed = parse_presentation(output_path)
    notes_text = "\n".join(str(slide.get("notes") or "") for slide in parsed["slides"])
    notes_lower = notes_text.lower()
    return {
        "parse_back_slide_count": parsed.get("slide_count"),
        "parse_back_notes_slide_count": sum(
            1 for slide in parsed["slides"] if str(slide.get("notes") or "").strip()
        ),
        "parse_back_source_url_count": parsed.get("unique_url_count"),
        "parse_back_needs_source_count": notes_lower.count("needs_source: true"),
        "parse_back_needs_fact_check_count": notes_lower.count("needs_fact_check: true"),
    }


def render_deck_plan_to_pptx(
    deck_plan: dict[str, Any],
    output_path: Path,
    *,
    style_profile: PptxStyle | None = None,
) -> dict[str, Any]:
    validation = validate_deck_plan(deck_plan)
    style = style_profile or load_style_profile(None)
    prs = Presentation()
    prs.slide_width = Inches(style.slide_width_in)
    prs.slide_height = Inches(style.slide_height_in)
    for slide_plan in _ordered_slides(deck_plan):
        _render_slide(prs, slide_plan, style)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    prs.save(output_path)
    result = render_result(deck_plan, output_path, validation, style)
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
    style: PptxStyle,
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
    result = {
        "deck_id": deck_plan.get("deck_id"),
        "input_deck_plan_path": deck_plan.get("_input_path"),
        "output_pptx_path": _display_path(output_path),
        "style_profile_path": _display_path(style.profile_path) if style.profile_path else None,
        "style_profile_loaded": style.loaded,
        "applied_font_family": style.font_family,
        "applied_fallback_font": style.fallback_font,
        "applied_layout_count": _applied_layout_count(deck_plan, style),
        "slides_with_long_body": _long_body_slides(deck_plan),
        "slides_with_font_fallback": [],
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
    result.update(_parse_back_counts(output_path))
    if style.loaded and style.font_family != style.fallback_font:
        result["warnings"].append(
            "Font substitution cannot be detected in Python; visually verify "
            f"{style.font_family} vs {style.fallback_font} fallback."
        )
    return result


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
        "- Styled draft support: optional Syukaworld style profile",
        "- Production Piti agent: not implemented",
        "- Image auto collection/insertion: none",
        "- LLM/API calls: none",
        "",
        "## Decks",
        "",
        (
            "| Deck | Styled | Slides | Sections | Appendix | Needs Source | Needs Fact Check | "
            "Visuals | Long Body | Missing Notes | Overlap | PPTX | Passed |"
        ),
        "|---|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---|---|",
    ]
    for result in results:
        lines.append(
            "| {deck} | {styled} | {slides} | {sections} | {appendix} | {needs_source} | "
            "{needs_fact_check} | {visuals} | {long_body} | {missing_notes} | {overlap} | {pptx} | "
            "{passed} |".format(
                deck=result.get("deck_id"),
                styled="yes" if result.get("style_profile_loaded") else "no",
                slides=result.get("slide_count"),
                sections=result.get("section_count"),
                appendix=result.get("appendix_internal_slide_count"),
                needs_source=result.get("needs_source_count"),
                needs_fact_check=result.get("needs_fact_check_count"),
                visuals=result.get("visual_placeholder_count"),
                long_body=len(result.get("slides_with_long_body", [])),
                missing_notes=len(result.get("slides_with_missing_notes", [])),
                overlap=result.get("source_image_overlap_count"),
                pptx=result.get("output_pptx_path"),
                passed="yes" if result.get("passed") else "no",
            )
        )
    lines.extend(["", "## Style Profile Application", ""])
    for result in results:
        lines.extend(
            [
                f"### {result.get('deck_id')} -> {result.get('output_pptx_path')}",
                "",
                f"- style_profile_path: {result.get('style_profile_path')}",
                f"- style_profile_loaded: {result.get('style_profile_loaded')}",
                f"- applied_font_family: {result.get('applied_font_family')}",
                f"- applied_fallback_font: {result.get('applied_fallback_font')}",
                f"- applied_layout_count: {result.get('applied_layout_count')}",
                f"- slides_with_long_body: {result.get('slides_with_long_body')}",
                f"- slides_with_font_fallback: {result.get('slides_with_font_fallback')}",
                f"- parse_back_slide_count: {result.get('parse_back_slide_count')}",
                f"- parse_back_notes_slide_count: {result.get('parse_back_notes_slide_count')}",
                f"- parse_back_source_url_count: {result.get('parse_back_source_url_count')}",
                f"- parse_back_needs_source_count: {result.get('parse_back_needs_source_count')}",
                "- parse_back_needs_fact_check_count: "
                f"{result.get('parse_back_needs_fact_check_count')}",
                "",
            ]
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


def render_default_decks(
    report_path: Path = DEFAULT_REPORT_PATH,
    *,
    style_profile_path: Path | None = DEFAULT_STYLE_PROFILE_PATH,
) -> list[Path]:
    output_paths: list[Path] = []
    results: list[dict[str, Any]] = []
    cases = [
        *DEFAULT_CASES,
        *[
            PptxRenderCase(
                deck_plan_path=case.deck_plan_path,
                output_path=case.output_path,
                style_profile_path=style_profile_path,
            )
            for case in STYLED_CASES
        ],
    ]
    for case in cases:
        deck_plan = _load_json(case.deck_plan_path)
        deck_plan["_input_path"] = str(case.deck_plan_path.relative_to(paths.REPO_ROOT))
        style = load_style_profile(case.style_profile_path)
        result = render_deck_plan_to_pptx(deck_plan, case.output_path, style_profile=style)
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
    style_profile_path: Annotated[
        Path | None,
        typer.Option(
            "--style-profile",
            help="Optional Syukaworld style profile JSON for styled output.",
        ),
    ] = DEFAULT_STYLE_PROFILE_PATH,
) -> None:
    """Render deck plan JSON into editable PPTX skeletons."""
    if input_path:
        if output_path is None:
            raise typer.BadParameter("--output is required with --input")
        deck_plan = _load_json(input_path)
        deck_plan["_input_path"] = str(input_path)
        style = load_style_profile(style_profile_path)
        result = render_deck_plan_to_pptx(deck_plan, output_path, style_profile=style)
        console.print(
            f"[green]Rendered {output_path} "
            f"(slides={result['slide_count']}, passed={result['passed']}).[/green]"
        )
        raise typer.Exit(0 if result["passed"] else 1)
    rendered = render_default_decks(report_path=report_path, style_profile_path=style_profile_path)
    console.print(f"[green]Rendered {len(rendered)} Piti PPTX artifacts.[/green]")


if __name__ == "__main__":
    app()
