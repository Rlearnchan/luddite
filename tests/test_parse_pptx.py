import csv
import json

import pytest

from luddite import paths
from luddite.parsers.parse_pptx import parse_directory, parse_presentation
from luddite.utils.security import extract_source_notes, redact_sensitive_text


def _golden_cases() -> list[dict]:
    cases = []
    for path in sorted((paths.EVAL_DIR / "golden_cases").glob("golden_*.json")):
        with path.open(encoding="utf-8") as source:
            cases.append(json.load(source))
    return cases


def test_extract_source_notes_accepts_loose_labels() -> None:
    notes = "\n".join(
        [
            "이미지 - https://example.com/image-source",
            "사진: https://example.com/photo-source",
            "[내용] https://example.com/content-source",
        ]
    )

    source_notes = extract_source_notes(notes)

    assert len(source_notes) == 3
    assert source_notes[0]["is_image"]
    assert source_notes[1]["is_image"]
    assert not source_notes[2]["is_image"]


def test_redaction_does_not_mask_url_query_ids() -> None:
    url = "https://play.google.com/store/apps/dev?id=123456789"

    assert redact_sensitive_text(url) == url


@pytest.mark.corpus
def test_parse_pptx_golden_cases() -> None:
    cases = _golden_cases()
    assert cases

    for case in cases:
        deck_path = paths.LATEST_PPT_RAW_DIR / case["source_file"]
        record = parse_presentation(deck_path)

        assert record["parse_status"] == "parsed"
        assert record["slide_count"] == case["target_slide_count"]
        assert record["url_count"] > 0
        assert record["slides_with_urls"] > 0
        assert len(record["slides"]) == case["target_slide_count"]
        assert any(slide["notes"] for slide in record["slides"])


@pytest.mark.corpus
def test_parse_latest_ppts_against_metrics(tmp_path) -> None:
    output = tmp_path / "parsed_latest_ppts.jsonl"
    records = parse_directory(paths.LATEST_PPT_RAW_DIR, output)
    by_file = {record["file_name"]: record for record in records}

    with (paths.DOCS_DIR / "appendix" / "ppt_metrics.csv").open(encoding="utf-8-sig") as source:
        metrics = list(csv.DictReader(source))

    assert len(records) == 8
    for row in metrics:
        record = by_file[row["file"]]
        assert record["slide_count"] == int(row["slides"])
        assert abs(record["url_count"] - int(row["urls"])) <= 1
        assert record["slides_with_urls"] == int(row["slides_with_urls"])
