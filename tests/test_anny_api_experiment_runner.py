from pathlib import Path

from luddite import paths
from luddite.agents.anny.api_experiment_runner import (
    validate_api_experiment_raw_output,
)

FIXTURE_DIR = paths.REPO_ROOT / "tests/fixtures/anny_api_experiment"
INPUT_BUNDLE = (
    paths.ANNY_STORYLINE_DRY_RUN_DIR / "ai_knowledge_institution_input_bundle.json"
)
EVIDENCE_PACK = paths.ANNY_EVIDENCE_PACK_AI_KNOWLEDGE_JSON


def _run_fixture(tmp_path: Path, name: str):
    return validate_api_experiment_raw_output(
        raw_output_path=FIXTURE_DIR / name,
        input_bundle_path=INPUT_BUNDLE,
        evidence_pack_path=EVIDENCE_PACK,
        experiment_dir=tmp_path / "experiments" / name.replace(".txt", ""),
        report_path=tmp_path / "reports" / f"{name}.md",
    )


def test_valid_api_experiment_fixture_passes(tmp_path) -> None:
    result = _run_fixture(tmp_path, "valid_ai_knowledge_storyline_raw.txt")

    assert result.parse_status == "parsed"
    assert result.schema_valid is True
    assert result.hygiene_passed is True
    assert result.failure_modes == []
    assert result.used_url_count == 3
    assert result.hallucinated_urls == []
    assert result.repair_attempted is False
    assert (result.experiment_dir / "raw_model_output.txt").exists()
    assert (result.experiment_dir / "parsed_storyline.json").exists()
    assert result.report_path.exists()


def test_invalid_json_fixture_records_invalid_json_without_repair(tmp_path) -> None:
    result = _run_fixture(tmp_path, "invalid_json_raw.txt")

    assert result.schema_valid is False
    assert "invalid_json" in result.failure_modes
    assert result.repair_attempted is False
    assert (result.experiment_dir / "raw_model_output.txt").exists()
    assert not (result.experiment_dir / "parsed_storyline.json").exists()
    assert "repair_attempted: false" in result.report_path.read_text(encoding="utf-8")


def test_source_hallucination_fixture_is_detected(tmp_path) -> None:
    result = _run_fixture(tmp_path, "source_hallucination_raw.txt")

    assert result.schema_valid is True
    assert "source_hallucination" in result.failure_modes
    assert "https://example.com/invented-ai-education-source" in result.hallucinated_urls
    assert result.ready_for_api_experiment is False


def test_missing_counterpoint_fixture_is_detected(tmp_path) -> None:
    result = _run_fixture(tmp_path, "missing_counterpoint_raw.txt")

    assert result.schema_valid is True
    assert "counterpoint_missing" in result.failure_modes
    assert "source_hallucination" not in result.failure_modes


def test_manifest_and_report_are_generated(tmp_path) -> None:
    result = _run_fixture(tmp_path, "source_hallucination_raw.txt")
    manifest_text = result.manifest_path.read_text(encoding="utf-8")
    report_text = result.report_path.read_text(encoding="utf-8")

    assert "source_hallucination" in manifest_text
    assert "allowed_url_count" in report_text
    assert "raw_model_output_retained: true" in report_text
