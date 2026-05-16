from luddite import paths
from luddite.parsers.parse_storylines import parse_directory


def test_parse_storylines_raw_corpus(tmp_path) -> None:
    output = tmp_path / "parsed_storylines.jsonl"
    records = parse_directory(paths.STORYLINE_RAW_DIR, output)

    assert output.exists()
    assert len(records) == 43
    assert all(record["parse_status"] == "parsed" for record in records)
    assert sum(record["url_count"] for record in records) > 0
    assert all(record["plain_text"] for record in records)
