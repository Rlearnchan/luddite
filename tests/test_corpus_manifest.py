from luddite.parsers.build_corpus_manifest import build_and_write_manifest
from luddite.utils.jsonl import read_jsonl


def test_build_corpus_manifest(tmp_path) -> None:
    output = tmp_path / "corpus_manifest.jsonl"
    items = build_and_write_manifest(output)

    assert output.exists()
    assert len(items) >= 51
    assert all(item["validation_status"] == "passed" for item in items)

    written = read_jsonl(output)
    assert len(written) == len(items)
    assert sum(1 for item in written if item["type"] == "rtf") == 43
    assert sum(1 for item in written if item["type"] == "pptx") >= 8
