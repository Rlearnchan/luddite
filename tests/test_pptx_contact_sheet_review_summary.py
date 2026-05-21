from pathlib import Path

from luddite.analysis.summarize_pptx_contact_sheet_review import (
    parse_contact_sheet_report,
    summarize_contact_sheet_review,
)


def _write_contact_sheet_report(path: Path, rows: list[str], deck_id: str = "deck") -> None:
    path.write_text(
        "\n".join(
            [
                f"# PPTX Contact Sheet QA: {deck_id}",
                "",
                "## Slide Review",
                "",
                (
                    "| slide_no | thumbnail | screen_headline | layout_intent | "
                    "proof_object.type | visual QA flags | contact_sheet_review_status | "
                    "readability_status | layout_status | broadcast_fit_status | "
                    "style_fit_status | readability_note | layout_note | broadcast_note | "
                    "style_note | fix_request |"
                ),
                "|---:|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|",
                *rows,
            ]
        )
        + "\n",
        encoding="utf-8",
    )


def test_parse_contact_sheet_report_reads_manual_review_fields(tmp_path: Path) -> None:
    report = tmp_path / "deck_contact_sheet.md"
    _write_contact_sheet_report(
        report,
        [
            (
                "| 1 | thumbs/slide-01.png | Headline | diagram | diagram | - | "
                "review | review | unchecked | ok | unchecked | Trim body |  |  |  | "
                "Trim body to one line. |"
            )
        ],
        deck_id="fixture_deck",
    )

    slides = parse_contact_sheet_report(report)

    assert len(slides) == 1
    assert slides[0].deck_id == "fixture_deck"
    assert slides[0].slide_no == 1
    assert slides[0].contact_sheet_review_status == "review"
    assert slides[0].readability_status == "review"
    assert slides[0].fix_request == "Trim body to one line."


def test_review_summary_handles_unstarted_manual_review(tmp_path: Path) -> None:
    input_dir = tmp_path / "contact_sheet"
    input_dir.mkdir()
    _write_contact_sheet_report(
        input_dir / "deck_a_contact_sheet.md",
        [
            (
                "| 1 | thumbs/slide-01.png | Headline A | diagram | diagram | - | "
                "unchecked | unchecked | unchecked | unchecked | unchecked |  |  |  |  |  |"
            )
        ],
        deck_id="deck_a",
    )
    _write_contact_sheet_report(
        input_dir / "deck_b_contact_sheet.md",
        [
            (
                "| 1 | thumbs/slide-01.png | Headline B | diagram | diagram | - | "
                "unchecked | unchecked | unchecked | unchecked | unchecked |  |  |  |  |  |"
            )
        ],
        deck_id="deck_b",
    )

    summary_path = tmp_path / "summary.md"
    pack_path = tmp_path / "pack.md"
    docs_summary_path = tmp_path / "docs_summary.md"
    summary = summarize_contact_sheet_review(
        input_dir=input_dir,
        summary_output_path=summary_path,
        review_pack_output_path=pack_path,
        docs_summary_output_path=docs_summary_path,
    )

    assert len(summary.slides) == 2
    summary_text = summary_path.read_text(encoding="utf-8")
    assert "total_slides: 2" in summary_text
    assert "unchecked_slides: 2" in summary_text
    assert "manual_review_status: manual review not started" in summary_text
    assert "No human note/fix_request issues have been classified yet" in summary_text
    assert docs_summary_path.exists()
    pack_text = pack_path.read_text(encoding="utf-8")
    assert "No Review/Fail Slides Yet" in pack_text


def test_review_summary_classifies_notes_and_suggests_owner(tmp_path: Path) -> None:
    input_dir = tmp_path / "contact_sheet"
    input_dir.mkdir()
    _write_contact_sheet_report(
        input_dir / "deck_contact_sheet.md",
        [
            (
                "| 1 | thumbs/slide-01.png | Text-heavy slide | diagram | diagram | - | "
                "review | review | unchecked | unchecked | unchecked | "
                "Too much text |  |  |  | Trim body to one line. |"
            ),
            (
                "| 2 | thumbs/slide-02.png | Broken layout | diagram | diagram | - | "
                "fail | unchecked | fail | unchecked | unchecked |  | "
                "Layout clutter and overlap |  |  | Rebuild layout spacing. |"
            ),
        ],
        deck_id="reviewed_deck",
    )

    summary_path = tmp_path / "summary.md"
    pack_path = tmp_path / "pack.md"
    summarize_contact_sheet_review(
        input_dir=input_dir,
        summary_output_path=summary_path,
        review_pack_output_path=pack_path,
        docs_summary_output_path=None,
    )

    summary_text = summary_path.read_text(encoding="utf-8")
    assert "manual_review_status: in_progress" in summary_text
    assert "review_slides: 1" in summary_text
    assert "fail_slides: 1" in summary_text
    assert "| copy_too_long | 1 | Anny slide spec / screen copy |" in summary_text
    assert "| layout_cluttered | 1 | Piti layout |" in summary_text
    assert "| readability_status | 1 | 0 | 1 | 0 |" in summary_text
    assert "| layout_status | 1 | 0 | 0 | 1 |" in summary_text

    pack_text = pack_path.read_text(encoding="utf-8")
    assert "Text-heavy slide" in pack_text
    assert "Broken layout" in pack_text
    assert "Anny slide spec / screen copy" in pack_text
    assert "Piti layout" in pack_text


def test_review_summary_handles_missing_reports_gracefully(tmp_path: Path) -> None:
    input_dir = tmp_path / "missing"
    summary_path = tmp_path / "summary.md"
    pack_path = tmp_path / "pack.md"

    summarize_contact_sheet_review(
        input_dir=input_dir,
        summary_output_path=summary_path,
        review_pack_output_path=pack_path,
        docs_summary_output_path=None,
    )

    summary_text = summary_path.read_text(encoding="utf-8")
    assert "report_count: 0" in summary_text
    assert "total_slides: 0" in summary_text
    assert "manual_review_status: manual review not started" in summary_text
    assert pack_path.exists()
