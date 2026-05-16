import pytest

from luddite import paths
from luddite.parsers.corpus_smoke import run_corpus_smoke


@pytest.mark.corpus
def test_corpus_smoke_writes_report(tmp_path) -> None:
    report = run_corpus_smoke(tmp_path / "parser_smoke_report.md")
    text = report.read_text(encoding="utf-8")

    assert "Parser Smoke Report" in text
    assert "File count: 43" in text
    assert "File count: 8" in text
    assert paths.STORYLINE_PARSED_JSONL.exists()
    assert paths.PPT_PARSED_JSONL.exists()
    assert paths.CORPUS_MANIFEST_JSONL.exists()
