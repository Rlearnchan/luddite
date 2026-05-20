from pathlib import Path
from typing import Any

from luddite.agents.anny.slide_spec_experiment import (
    EXPERIMENT_CASES,
    build_slide_spec_experiment_prompt,
    run_experiment,
)


def test_slide_spec_experiment_fixture_mode_writes_case_artifacts(tmp_path: Path) -> None:
    output_root = tmp_path / "experiments"
    review_output_dir = tmp_path / "docs" / "reviews"

    manifests = run_experiment(
        output_root=output_root,
        review_output_dir=review_output_dir,
    )

    assert len(manifests) == 2
    assert all(manifest["mode"] == "fixture" for manifest in manifests)
    assert all(manifest["schema_valid"] is True for manifest in manifests)
    assert all(manifest["failure_modes"] == [] for manifest in manifests)
    assert all(manifest["ready_for_production_anny_agent"] is False for manifest in manifests)
    for case in EXPERIMENT_CASES:
        case_dir = output_root / case.case_id
        assert (case_dir / "raw_model_output.txt").exists()
        assert (case_dir / "parsed_piti_slide_spec.json").exists()
        assert (case_dir / "validation_report.md").exists()
        assert (case_dir / "visual_qa_report.md").exists()
        assert (case_dir / "comparison_against_adapter.md").exists()
        assert (review_output_dir / f"{case.case_id}_validation.md").exists()
        assert (review_output_dir / f"{case.case_id}_comparison.md").exists()
        comparison = (case_dir / "comparison_against_adapter.md").read_text(
            encoding="utf-8"
        )
        assert "adapter" in comparison
        assert "direct" in comparison
        assert "production readiness remains false" in comparison.lower()


def test_slide_spec_experiment_default_mode_does_not_call_api(tmp_path: Path) -> None:
    def fail_api(**_kwargs):
        raise AssertionError("API caller should not be used in fixture mode")

    manifests = run_experiment(
        case_id="ai_knowledge_institution",
        output_root=tmp_path / "experiments",
        review_output_dir=tmp_path / "reviews",
        api_caller=fail_api,
    )

    assert len(manifests) == 1
    assert manifests[0]["mode"] == "fixture"
    assert manifests[0]["model"] == "synthetic_fixture"


def test_slide_spec_experiment_live_api_failure_writes_error_artifacts(
    tmp_path: Path,
    monkeypatch: Any,
) -> None:
    monkeypatch.setenv("OPENAI_API_KEY", "test-key")

    def fail_api(**_kwargs):
        raise RuntimeError("simulated API outage")

    output_root = tmp_path / "experiments"
    review_output_dir = tmp_path / "reviews"
    manifests = run_experiment(
        case_id="ai_knowledge_institution",
        output_root=output_root,
        review_output_dir=review_output_dir,
        live_api=True,
        model="gpt-test",
        api_caller=fail_api,
    )

    manifest = manifests[0]
    case_dir = output_root / "ai_knowledge_institution"
    assert manifest["failure_modes"] == ["api_request_failed"]
    assert (case_dir / "raw_model_output.txt").exists()
    assert "simulated API outage" in (case_dir / "api_error.txt").read_text(
        encoding="utf-8"
    )
    assert not (case_dir / "parsed_piti_slide_spec.json").exists()
    assert (review_output_dir / "ai_knowledge_institution_validation.md").exists()
    assert (review_output_dir / "ai_knowledge_institution_comparison.md").exists()


def test_slide_spec_experiment_live_api_invalid_json_preserves_raw_output(
    tmp_path: Path,
    monkeypatch: Any,
) -> None:
    monkeypatch.setenv("OPENAI_API_KEY", "test-key")

    def invalid_json_api(**_kwargs):
        return "not json", {"id": "fake-response"}

    output_root = tmp_path / "experiments"
    manifests = run_experiment(
        case_id="ai_knowledge_institution",
        output_root=output_root,
        review_output_dir=tmp_path / "reviews",
        live_api=True,
        model="gpt-test",
        api_caller=invalid_json_api,
    )

    manifest = manifests[0]
    case_dir = output_root / "ai_knowledge_institution"
    assert manifest["failure_modes"] == ["invalid_json"]
    assert manifest["parse_status"].startswith("invalid_json")
    assert (case_dir / "raw_model_output.txt").read_text(encoding="utf-8") == "not json"
    assert (case_dir / "response_metadata.json").exists()
    assert not (case_dir / "parsed_piti_slide_spec.json").exists()
    assert "parse_status: invalid_json" in (
        case_dir / "validation_report.md"
    ).read_text(encoding="utf-8")


def test_slide_spec_experiment_prompt_states_direct_contract() -> None:
    prompt = build_slide_spec_experiment_prompt(
        input_bundle={"story_seed_title": "테스트"},
        evidence_pack={"source": "evidence"},
        manual_storyline={"sections": []},
        schema={"title": "PitiSlideSpecDeck"},
        visual_qa_summary="diagram_nodes_too_generic: 30",
        allowed_urls={"https://example.com/source"},
    )

    assert "piti_slide_spec_schema.json" in prompt
    assert "Piti will render this contract without re-inferring" in prompt
    assert "actor -> mechanism -> result" in prompt
    assert "Do not expose source URLs on screen" in prompt
