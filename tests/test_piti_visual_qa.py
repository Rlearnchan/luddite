import json
from pathlib import Path

from luddite.agents.piti import render_visual_qa


def _proof(proof_type: str = "none", **overrides) -> dict:
    proof = {
        "type": proof_type,
        "screen_position": "none",
        "source_name": None,
        "display_title": None,
        "quote_text": None,
        "quote_translation": None,
        "source_url": None,
        "image_url": None,
        "chart_title": None,
        "chart_source_label": None,
        "data_hint": None,
        "diagram_nodes": [],
        "diagram_edges": [],
        "placeholder_reason": None,
        "manual_insert_required": False,
        "copyright_risk": False,
    }
    proof.update(overrides)
    return proof


def _slide(
    slide_no: int,
    *,
    layout_intent: str = "headline_body",
    proof: dict | None = None,
    screen_body: list[str] | None = None,
    overflow_notes: list[str] | None = None,
    editor_instruction: str | None = None,
    needs_source: bool = False,
    needs_fact_check: bool = False,
    required_before_broadcast: bool = False,
    source_refs: list[dict] | None = None,
    risk_flags: list[str] | None = None,
    do_not_claim: list[str] | None = None,
) -> dict:
    return {
        "slide_id": f"slide_{slide_no:02}",
        "slide_no": slide_no,
        "section_id": "section_01",
        "layout_intent": layout_intent,
        "screen_headline": f"Headline {slide_no}",
        "screen_body": screen_body if screen_body is not None else ["body"],
        "speaker_notes_expanded": "",
        "overflow_notes": overflow_notes or [],
        "proof_object": proof or _proof(),
        "editor_instruction": editor_instruction,
        "source_refs": source_refs or [],
        "risk_flags": risk_flags or [],
        "needs_source": needs_source,
        "needs_fact_check": needs_fact_check,
        "required_before_broadcast": required_before_broadcast,
        "do_not_claim": do_not_claim or [],
    }


def _spec(deck_id: str, slides: list[dict]) -> dict:
    return {
        "deck_id": deck_id,
        "story_seed_title": deck_id,
        "source_storyline_id": "storyline_test",
        "sections": [
            {
                "section_id": "section_01",
                "section_no": 1,
                "section_title": "Section",
                "slides": slides,
            }
        ],
        "slides": slides,
        "readiness": {
            "ready_for_piti_renderer": True,
            "ready_for_production_piti_agent": False,
            "ready_for_broadcast": False,
        },
        "notes": "test",
    }


def _write_spec(path: Path, spec: dict) -> None:
    path.write_text(json.dumps(spec, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def test_visual_qa_flags_cover_requested_warnings(tmp_path: Path) -> None:
    spec = _spec(
        "flag_deck",
        [
            _slide(1, proof=_proof(), needs_fact_check=True),
            _slide(
                2,
                proof=_proof(
                    "source_card",
                    display_title="Reference material",
                ),
            ),
            _slide(3, proof=_proof("source_card", display_title="Useful source title")),
            _slide(4, proof=_proof("source_card", display_title="Headline 4")),
            _slide(
                5,
                layout_intent="diagram",
                proof=_proof(
                    "diagram",
                    screen_position="center_large",
                    diagram_nodes=["기존 검색", "AI 즉답"],
                    diagram_edges=[{"from": "기존 검색", "to": "AI 즉답"}],
                    manual_insert_required=True,
                ),
                editor_instruction="Manually refine diagram.",
            ),
            _slide(
                6,
                layout_intent="chart_table_reference",
                proof=_proof("chart", screen_position="full_width_chart"),
                editor_instruction="Manually design chart.",
            ),
            _slide(7, proof=_proof(), screen_body=[]),
            _slide(8, proof=_proof(), overflow_notes=["a", "b", "c", "d"]),
            _slide(
                9,
                layout_intent="image_left_quote_right",
                proof=_proof(
                    "image",
                    screen_position="left_half",
                    manual_insert_required=True,
                ),
            ),
        ],
    )

    deck = render_visual_qa.evaluate_slide_spec(
        tmp_path / "flag_deck.json",
        spec,
        tmp_path / "reports",
    )
    flags = {
        flag
        for slide in deck.slides
        for flag in slide.visual_qa_flags
    }

    assert flags == {
        "proof_object_missing_for_claim_slide",
        "too_many_source_cards_in_sequence",
        "diagram_nodes_too_generic",
        "chart_without_data_hint",
        "source_card_display_title_too_generic",
        "screen_body_empty_but_no_proof_object",
        "overflow_notes_too_large",
        "manual_insert_required_without_editor_instruction",
    }
    assert "too_many_source_cards_in_sequence" in deck.slides[1].visual_qa_flags
    assert "too_many_source_cards_in_sequence" in deck.slides[2].visual_qa_flags
    assert "too_many_source_cards_in_sequence" in deck.slides[3].visual_qa_flags


def test_visual_qa_warnings_are_report_only(tmp_path: Path) -> None:
    input_dir = tmp_path / "input"
    output_dir = tmp_path / "qa"
    input_dir.mkdir()
    _write_spec(
        input_dir / "warnings.json",
        _spec("warnings", [_slide(1, proof=_proof(), needs_source=True)]),
    )

    decks = render_visual_qa.render_visual_qa(input_dir=input_dir, output_dir=output_dir)

    assert len(decks) == 1
    assert decks[0].flag_count == 1
    assert (output_dir / "warnings.md").exists()
    assert (output_dir / "piti_visual_qa_summary.md").exists()


def test_render_visual_qa_writes_two_deck_reports_and_summary(tmp_path: Path) -> None:
    input_dir = tmp_path / "input"
    output_dir = tmp_path / "qa"
    review_output_dir = tmp_path / "docs" / "reviews"
    input_dir.mkdir()
    _write_spec(input_dir / "deck_a.json", _spec("deck_a", [_slide(1)]))
    _write_spec(input_dir / "deck_b.json", _spec("deck_b", [_slide(1)]))

    decks = render_visual_qa.render_visual_qa(
        input_dir=input_dir,
        output_dir=output_dir,
        review_output_dir=review_output_dir,
    )

    assert [deck.deck_id for deck in decks] == ["deck_a", "deck_b"]
    assert (output_dir / "deck_a.md").exists()
    assert (output_dir / "deck_b.md").exists()
    assert (review_output_dir / "deck_a.md").exists()
    assert (review_output_dir / "deck_b.md").exists()
    assert (review_output_dir / "piti_visual_qa_summary.md").exists()
    summary_text = (output_dir / "piti_visual_qa_summary.md").read_text(encoding="utf-8")
    deck_text = (output_dir / "deck_a.md").read_text(encoding="utf-8")
    assert "Piti Visual QA Summary" in summary_text
    assert "| slide_no | screen_headline | layout_intent | proof_object.type |" in deck_text
    assert "screen_body lines" in deck_text
    assert "overflow_notes count" in deck_text
    assert "manual_insert_required" in deck_text
    assert "visual_qa_flags" in deck_text
