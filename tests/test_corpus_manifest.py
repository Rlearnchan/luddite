from pathlib import Path

from luddite import paths
from luddite.parsers.build_corpus_manifest import build_and_write_manifest
from luddite.utils.jsonl import read_jsonl


def test_build_corpus_manifest_without_raw_corpus(tmp_path, monkeypatch) -> None:
    empty_storylines = tmp_path / "storylines" / "raw"
    empty_latest = tmp_path / "ppt" / "latest" / "raw"
    empty_legacy = tmp_path / "ppt" / "legacy" / "raw"
    empty_sheets = tmp_path / "sheets" / "raw"
    for directory in (empty_storylines, empty_latest, empty_legacy, empty_sheets):
        directory.mkdir(parents=True)

    monkeypatch.setattr(paths, "STORYLINE_RAW_DIR", empty_storylines)
    monkeypatch.setattr(paths, "LATEST_PPT_RAW_DIR", empty_latest)
    monkeypatch.setattr(paths, "LEGACY_PPT_RAW_DIR", empty_legacy)
    monkeypatch.setattr(paths, "SHEETS_RAW_DIR", empty_sheets)

    output = tmp_path / "corpus_manifest.jsonl"
    items = build_and_write_manifest(output)

    assert output.exists()
    assert items == []
    assert read_jsonl(output) == []


def test_build_corpus_manifest_creates_output_directory(tmp_path) -> None:
    output = tmp_path / "nested" / "corpus_manifest.jsonl"
    items = build_and_write_manifest(output)

    assert output.exists()
    assert all(item["validation_status"] == "passed" for item in items)

    written = read_jsonl(output)
    assert len(written) == len(items)


def test_manifest_validation_failure_is_recorded(monkeypatch, tmp_path) -> None:
    sample = tmp_path / "bad.rtf"
    sample.write_text("sample", encoding="utf-8")

    def broken_item(
        path: Path,
        item_type: str,
        title: str,
        used_by: list[str],
        risk_flags: list[str] | None = None,
    ) -> dict:
        return {
            "corpus_id": "broken",
            "type": "not-valid",
            "title": title,
            "source": "local",
        }

    monkeypatch.setattr(paths, "STORYLINE_RAW_DIR", tmp_path)
    monkeypatch.setattr(paths, "LATEST_PPT_RAW_DIR", tmp_path / "missing-ppt")
    monkeypatch.setattr(paths, "LEGACY_PPT_RAW_DIR", tmp_path / "missing-legacy")
    monkeypatch.setattr(paths, "SHEETS_RAW_DIR", tmp_path / "missing-sheets")

    import luddite.parsers.build_corpus_manifest as manifest

    monkeypatch.setattr(manifest, "_item", broken_item)
    items = manifest.build_and_write_manifest(tmp_path / "manifest.jsonl")

    assert items[0]["validation_status"] == "failed"
    assert items[0]["validation_errors"]
