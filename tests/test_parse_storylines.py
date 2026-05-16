import pytest

from luddite import paths
from luddite.parsers.parse_storylines import parse_directory, parse_storyline_file


def test_parse_storyline_file_from_temp_rtf(tmp_path) -> None:
    source = tmp_path / "sample.rtf"
    source.write_text(
        r"{\rtf1\ansi 1. Hook https://example.com/a?utm_source=x\par 2. Body 한국 연결}",
        encoding="utf-8",
    )

    record = parse_storyline_file(source)

    assert record["parse_status"] == "parsed"
    assert record["title"] == "sample"
    assert record["urls"] == ["https://example.com/a"]
    assert record["has_korea_bridge"] is True


@pytest.mark.corpus
def test_parse_storylines_raw_corpus(tmp_path) -> None:
    output = tmp_path / "parsed_storylines.jsonl"
    records = parse_directory(paths.STORYLINE_RAW_DIR, output)

    assert output.exists()
    assert len(records) == 43
    assert all(record["parse_status"] == "parsed" for record in records)
    assert sum(record["url_count"] for record in records) > 0
    assert all(record["plain_text"] for record in records)
