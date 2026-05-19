import json
from pathlib import Path

from pptx import Presentation

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
    style_path.write_text(
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
    assert result["font_size_downgraded_slides"]
    assert result["slides_with_text_placeholder_overlap"] == []
    assert result["parse_back_slide_count"] == 4
    assert parsed["slide_count"] == 4
    notes_text = "\n".join(slide["notes"] for slide in parsed["slides"])
    assert "style_profile_loaded: True" in notes_text
    assert "visual_plan" in notes_text
    visible_text = "\n".join(slide["visible_text"] for slide in parsed["slides"])
    assert "diagram candidate" not in visible_text
