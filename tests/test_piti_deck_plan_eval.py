import json
from pathlib import Path

from luddite.eval import piti_deck_plan_eval


def test_deck_plan_fixtures_load() -> None:
    fixtures = piti_deck_plan_eval.load_deck_plans()

    assert len(fixtures) >= 2
    assert all(path.exists() for path, _deck in fixtures)


def test_deck_plan_schema_validation() -> None:
    for path, deck in piti_deck_plan_eval.load_deck_plans():
        result = piti_deck_plan_eval.evaluate_deck_plan(path, deck)

        assert result["schema_valid"]


def test_slide_no_integrity_calculation() -> None:
    assert piti_deck_plan_eval._slide_no_integrity(
        {"slides": [{"slide_no": 1}, {"slide_no": 2}]}
    )
    assert not piti_deck_plan_eval._slide_no_integrity(
        {"slides": [{"slide_no": 1}, {"slide_no": 3}]}
    )


def test_source_note_integrity_calculation() -> None:
    ok_deck = {
        "slides": [
            {
                "slide_no": 1,
                "notes": "[내용] https://example.com/source\n[이미지] https://example.com/image",
                "image_slots": [{"source_url": "https://example.com/image"}],
            }
        ]
    }
    bad_deck = {
        "slides": [
            {
                "slide_no": 1,
                "notes": "[내용] https://example.com/source",
                "image_slots": [{"source_url": "https://example.com/image"}],
            }
        ]
    }

    assert piti_deck_plan_eval._source_note_integrity(ok_deck)[0]
    assert not piti_deck_plan_eval._source_note_integrity(bad_deck)[0]


def test_source_note_integrity_canonicalizes_image_slot_urls() -> None:
    deck = {
        "slides": [
            {
                "slide_no": 1,
                "notes": "[이미지] https://en.wikipedia.org/wiki/Pawn_Stars#/media/File:Pawn_Stars_cast.png",
                "image_slots": [
                    {
                        "source_url": (
                            "https://en.wikipedia.org/wiki/Pawn_Stars#/media/"
                            "File:Pawn_Stars_cast.png"
                        )
                    }
                ],
            }
        ]
    }

    assert piti_deck_plan_eval._source_note_integrity(deck)[0]


def test_source_image_overlap_detection() -> None:
    deck = {
        "slides": [
            {
                "notes": "[내용] https://example.com/a\n[이미지] https://example.com/a",
                "image_slots": [{"source_url": "https://example.com/a"}],
            }
        ]
    }

    assert piti_deck_plan_eval._source_image_overlap_count(deck) == 1


def test_piti_deck_plan_eval_writes_report(tmp_path) -> None:
    output_jsonl = tmp_path / "latest.jsonl"
    output_md = tmp_path / "latest.md"

    results = piti_deck_plan_eval.run_eval(
        output_jsonl=output_jsonl,
        output_md=output_md,
    )

    assert len(results) >= 2
    assert all(result["passed"] for result in results)
    assert output_jsonl.exists()
    assert output_md.exists()
    assert "piti Deck Plan Eval Report" in output_md.read_text(encoding="utf-8")
    assert output_jsonl.is_relative_to(Path(tmp_path))


def test_piti_deck_plan_eval_marks_golden_fallback(tmp_path) -> None:
    fixture_dir = tmp_path / "fixtures"
    model_dir = tmp_path / "model"
    fixture_dir.mkdir()
    model_dir.mkdir()
    deck = {
        "deck_id": "fallback_deck",
        "title": "Fallback",
        "theme": "test",
        "slides": [
            {
                "slide_no": 1,
                "slide_type": "title",
                "headline": "Title",
                "body": [],
                "notes": "",
                "image_slots": [],
            },
            {
                "slide_no": 2,
                "slide_type": "section_title",
                "headline": "A",
                "body": [],
                "notes": "",
                "image_slots": [],
            },
            {
                "slide_no": 3,
                "slide_type": "section_title",
                "headline": "B",
                "body": [],
                "notes": "",
                "image_slots": [],
            },
        ],
    }
    (fixture_dir / "fallback_deck.json").write_text(
        json.dumps(deck),
        encoding="utf-8",
    )

    output_jsonl = tmp_path / "latest.jsonl"
    output_md = tmp_path / "latest.md"
    results = piti_deck_plan_eval.run_eval(
        fixture_dir=fixture_dir,
        model_output_path=model_dir,
        output_jsonl=output_jsonl,
        output_md=output_md,
    )

    assert results[0]["candidate_source"] == "golden_fallback"
    assert "Golden Fallbacks" in output_md.read_text(encoding="utf-8")
