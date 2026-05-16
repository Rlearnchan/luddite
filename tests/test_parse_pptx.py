import csv
import json

import pytest

from luddite import paths
from luddite.parsers.parse_pptx import parse_directory, parse_presentation


def _golden_cases() -> list[dict]:
    cases = []
    for path in sorted((paths.EVAL_DIR / "golden_cases").glob("golden_*.json")):
        with path.open(encoding="utf-8") as source:
            cases.append(json.load(source))
    return cases


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
