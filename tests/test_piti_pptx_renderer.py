import json
from pathlib import Path

from pptx import Presentation
from pptx.dml.color import RGBColor

from luddite.agents.piti import build_deck_plan_from_storyline, render_pptx
from luddite.parsers.parse_pptx import parse_presentation


def _storyline() -> dict:
    return {
        "storyline_id": "pptx_storyline_test",
        "title": "PPTX 테스트",
        "sections": [
            {
                "section_title": "도입",
                "slides": [
                    {
                        "slide_no": 1,
                        "slide_type": "title",
                        "headline": "PPTX 테스트",
                        "body": ["수정 가능한 뼈대"],
                        "source_urls": [],
                        "image_urls": [],
                        "notes": "title notes",
                        "needs_source": False,
                        "needs_fact_check": False,
                    },
                    {
                        "slide_no": 2,
                        "slide_type": "explainer",
                        "headline": "출처가 있는 장표",
                        "body": ["본문 메시지 하나"],
                        "source_urls": ["https://example.com/source"],
                        "image_urls": [],
                        "notes": "source note",
                        "needs_source": True,
                        "needs_fact_check": True,
                        "required_before_broadcast": True,
                        "visual_plan": {
                            "kind": "diagram",
                            "description": "diagram candidate",
                            "copyright_risk": False,
                        },
                    },
                    {
                        "slide_no": 3,
                        "slide_type": "production_checklist",
                        "headline": "방송 전 체크",
                        "body": ["추가 확인"],
                        "source_urls": ["https://example.com/check"],
                        "image_urls": [],
                        "notes": "checklist note",
                        "needs_source": False,
                        "needs_fact_check": True,
                    },
                ],
            },
            {
                "section_title": "마무리",
                "slides": [
                    {
                        "slide_no": 4,
                        "slide_type": "closing_question",
                        "headline": "마지막 질문",
                        "body": ["무엇을 볼까"],
                        "source_urls": [],
                        "image_urls": [],
                        "notes": "closing note",
                        "needs_source": False,
                        "needs_fact_check": False,
                    }
                ],
            },
        ],
    }


def _deck_plan() -> dict:
    return build_deck_plan_from_storyline.build_deck_plan_from_storyline(
        _storyline(),
        deck_id="pptx_test",
    )


def _write_style_profile(path: Path) -> None:
    path.write_text(
        json.dumps(
            {
                "slide_size": {"width_in": 13.333, "height_in": 7.5},
                "common_colors": [{"value": "#FF0000", "count": 10}],
                "font_resolution": {"fallback_font": "맑은 고딕"},
                "layout_patterns": {
                    "title": {
                        "x_cm_median": 2.38,
                        "y_cm_median": 3.118,
                        "w_cm_median": 29.106,
                        "h_cm_median": 6.632,
                        "font_size_pt_median": 54.0,
                    },
                    "headline_body": {
                        "x_cm_median": 1.591,
                        "y_cm_median": 3.357,
                        "w_cm_median": 31.092,
                        "h_cm_median": 3.616,
                        "font_size_pt_median": 28.0,
                        "font_color_top": "#FF0000",
                    },
                },
            },
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )


def _runs_for_text(prs: Presentation, text: str):
    for slide in prs.slides:
        for shape in slide.shapes:
            if not getattr(shape, "has_text_frame", False):
                continue
            for paragraph in shape.text_frame.paragraphs:
                for run in paragraph.runs:
                    if text in run.text:
                        yield run


def _first_run_for_text(prs: Presentation, text: str):
    return next(_runs_for_text(prs, text))


def _minimal_deck(slide: dict) -> dict:
    return {
        "deck_id": "format_test",
        "title": "format test",
        "sections": [{"section_no": 1, "section_title": "test", "slides": [slide]}],
        "slides": [slide],
    }


def test_render_deck_plan_to_pptx_creates_editable_file(tmp_path: Path) -> None:
    output_path = tmp_path / "draft.pptx"

    result = render_pptx.render_deck_plan_to_pptx(_deck_plan(), output_path)
    prs = Presentation(str(output_path))

    assert output_path.exists()
    assert result["passed"]
    assert result["slide_count"] == 4
    assert len(prs.slides) == 4
    assert any(
        "PPTX 테스트" in shape.text
        for shape in prs.slides[0].shapes
        if hasattr(shape, "text")
    )


def test_rendered_pptx_notes_preserve_sources_and_flags(tmp_path: Path) -> None:
    output_path = tmp_path / "draft.pptx"
    render_pptx.render_deck_plan_to_pptx(_deck_plan(), output_path)

    parsed = parse_presentation(output_path)
    notes_text = "\n".join(slide["notes"] for slide in parsed["slides"])

    assert "https://example.com/source" in notes_text
    assert "needs_source: true" in notes_text.lower()
    assert "needs_fact_check: true" in notes_text.lower()
    assert "required_before_broadcast: true" in notes_text.lower()
    assert "visual_plan" in notes_text


def test_production_checklist_moves_to_end_and_is_marked_internal(tmp_path: Path) -> None:
    output_path = tmp_path / "draft.pptx"
    render_pptx.render_deck_plan_to_pptx(_deck_plan(), output_path)

    parsed = parse_presentation(output_path)
    last_slide = parsed["slides"][-1]

    assert "[내부 체크리스트]" in last_slide["visible_text"]
    assert "internal checklist" in last_slide["notes"].lower()


def test_render_report_created(tmp_path: Path) -> None:
    deck_path = tmp_path / "deck.json"
    output_path = tmp_path / "draft.pptx"
    report_path = tmp_path / "report.md"
    deck_plan = _deck_plan()
    deck_path.write_text(json.dumps(deck_plan, ensure_ascii=False), encoding="utf-8")
    loaded = json.loads(deck_path.read_text(encoding="utf-8"))
    result = render_pptx.render_deck_plan_to_pptx(loaded, output_path)

    render_pptx.write_render_report(report_path, [result])

    text = report_path.read_text(encoding="utf-8")
    assert "Piti PPTX Render Report" in text
    assert "ready_for_ppt_generation: true (scaffold only)" in text
    assert "Adaptive body font" in text


def test_render_deck_plan_to_pptx_applies_style_profile(tmp_path: Path) -> None:
    output_path = tmp_path / "styled.pptx"
    style_path = tmp_path / "style.json"
    _write_style_profile(style_path)

    style = render_pptx.load_style_profile(style_path)
    result = render_pptx.render_deck_plan_to_pptx(
        _deck_plan(),
        output_path,
        style_profile=style,
    )
    parsed = parse_presentation(output_path)

    assert result["style_profile_loaded"] is True
    assert result["applied_font_family"] == "맑은 고딕"
    assert result["applied_layout_count"] >= 1
    assert result["adaptive_font_applied"] is True
    assert result["visual_placeholder_shortened"] is True
    assert result["slides_with_text_placeholder_overlap"] == []
    assert result["headline_red_count"] > 0
    assert result["body_black_count"] > 0
    assert result["parse_back_slide_count"] == 4
    assert parsed["slide_count"] == 4
    notes_text = "\n".join(slide["notes"] for slide in parsed["slides"])
    assert "style_profile_loaded: True" in notes_text
    assert "visual_plan" in notes_text
    visible_text = "\n".join(slide["visible_text"] for slide in parsed["slides"])
    assert "diagram candidate" not in visible_text

    prs = Presentation(str(output_path))
    headline_run = _first_run_for_text(prs, "출처가 있는 장표")
    body_run = _first_run_for_text(prs, "본문 메시지 하나")
    assert headline_run.font.size.pt == 28
    assert headline_run.font.color.rgb == RGBColor(255, 0, 0)
    assert body_run.font.color.rgb == RGBColor(0, 0, 0)


def test_quote_bilingual_mode_uses_english_black_and_korean_red(tmp_path: Path) -> None:
    output_path = tmp_path / "quote.pptx"
    style_path = tmp_path / "style.json"
    _write_style_profile(style_path)
    slide = {
        "slide_no": 1,
        "layout_type": "quote",
        "slide_type": "quote",
        "headline": "영한 교차 인용",
        "body": [
            "They collectively held a record $160bn",
            "11월 말 기준 개인들이 보유한 미국 주식 규모는 1,600억달러",
        ],
        "source_urls": ["https://example.com/quote"],
        "image_urls": [],
        "speaker_notes": "quote notes",
        "visual_plan": {"kind": "none"},
    }

    render_pptx.render_deck_plan_to_pptx(
        _minimal_deck(slide),
        output_path,
        style_profile=render_pptx.load_style_profile(style_path),
    )

    prs = Presentation(str(output_path))
    english_run = _first_run_for_text(prs, "They collectively")
    korean_run = _first_run_for_text(prs, "11월 말 기준")
    assert english_run.font.size.pt == 28
    assert english_run.font.color.rgb == RGBColor(0, 0, 0)
    assert korean_run.font.size.pt == 28
    assert korean_run.font.color.rgb == RGBColor(255, 0, 0)


def test_chart_table_placeholder_uses_chart_typography(tmp_path: Path) -> None:
    output_path = tmp_path / "chart.pptx"
    style_path = tmp_path / "style.json"
    _write_style_profile(style_path)
    slide = {
        "slide_no": 1,
        "layout_type": "chart_placeholder",
        "slide_type": "data",
        "headline": "미국주식 보관금액 상위 10종목",
        "body": ["테슬라 264", "엔비디아 195"],
        "source_urls": ["https://example.com/seibro"],
        "image_urls": [],
        "speaker_notes": "chart notes",
        "visual_plan": {"kind": "chart_candidate"},
    }

    result = render_pptx.render_deck_plan_to_pptx(
        _minimal_deck(slide),
        output_path,
        style_profile=render_pptx.load_style_profile(style_path),
    )

    prs = Presentation(str(output_path))
    title_run = _first_run_for_text(prs, "미국주식 보관금액")
    data_run = _first_run_for_text(prs, "테슬라 264")
    source_run = _first_run_for_text(prs, "(출처:")
    assert result["chart_table_style_applied_count"] == 1
    assert title_run.font.size.pt == 28
    assert title_run.font.bold is True
    assert title_run.font.underline is True
    assert title_run.font.color.rgb == RGBColor(0, 0, 0)
    assert data_run.font.size.pt == 18
    assert data_run.font.bold is True
    assert source_run.font.size.pt == 20
    assert source_run.font.underline is True


def test_manual_placeholder_hidden_and_image_left_counted(tmp_path: Path) -> None:
    output_path = tmp_path / "image.pptx"
    style_path = tmp_path / "style.json"
    _write_style_profile(style_path)
    slides = [
        {
            "slide_no": 1,
            "layout_type": "headline_body",
            "slide_type": "explainer",
            "headline": "수동 이미지는 화면에 숨긴다",
            "body": ["본문은 검은색"],
            "source_urls": [],
            "image_urls": [],
            "speaker_notes": "manual visual",
            "visual_plan": {"kind": "manual", "description": "manual insert"},
        },
        {
            "slide_no": 2,
            "layout_type": "image_placeholder",
            "slide_type": "image",
            "headline": "이미지는 왼쪽에 둔다",
            "body": ["오른쪽에 해석을 둔다"],
            "source_urls": [],
            "image_urls": [],
            "speaker_notes": "image visual",
            "visual_plan": {"kind": "screenshot_candidate"},
        },
    ]
    deck = {"deck_id": "image_test", "sections": [{"slides": slides}], "slides": slides}

    result = render_pptx.render_deck_plan_to_pptx(
        deck,
        output_path,
        style_profile=render_pptx.load_style_profile(style_path),
    )
    parsed = parse_presentation(output_path)
    visible_text = "\n".join(slide["visible_text"] for slide in parsed["slides"])
    notes_text = "\n".join(slide["notes"] for slide in parsed["slides"])

    assert result["manual_placeholder_hidden_count"] == 1
    assert result["image_left_layout_count"] == 1
    assert "[수동" not in visible_text
    assert "manual_placeholder_hidden: True" in notes_text
