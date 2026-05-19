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
