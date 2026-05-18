import json

from luddite import paths
from luddite.utils.schemas import validate_with_schema


def test_api_experiment_run_input_mode_is_valid() -> None:
    record = {
        "run_id": "anny_api_experiment_ai_knowledge_institution_v1",
        "bundle_id": "anny_bundle_09277535430e",
        "story_seed_title": "AI 즉답 시대의 지식기관 역할",
        "input_bundle_path": "outputs/model_dry_runs/anny_storyline/input.json",
        "evidence_pack_path": "data/candidates/evidence.json",
        "length_mode": "standard_representative_outline",
        "output_contract_version": "anny_mvp_storyline_v1.8",
        "prompt_version": "prompts/anny/storyline_writer.md",
        "mode": "api_experiment",
        "requested_by": "codex",
        "created_at": "2026-05-18T00:00:00+09:00",
    }

    assert validate_with_schema(record, "anny_run_input_schema.json") == []


def test_api_experiment_manifest_model_source_and_failure_modes_are_valid() -> None:
    record = {
        "run_id": "anny_api_experiment_ai_knowledge_institution_v1",
        "status": "failed",
        "input_bundle_path": "input_bundle.json",
        "evidence_pack_path": "evidence_pack.json",
        "output_storyline_path": "parsed_storyline.json",
        "eval_report_path": "validation_report.md",
        "model_source": "openai_api",
        "schema_valid": False,
        "hygiene_passed": False,
        "output_contract_version": "anny_mvp_storyline_v1.8",
        "prompt_version": "prompts/anny/storyline_writer.md",
        "validator_version": "anny_dry_run_eval_v1.8",
        "schema_version": "anny_run_manifest_schema_v1",
        "input_bundle_sha256": None,
        "evidence_pack_sha256": None,
        "output_storyline_sha256": None,
        "hygiene_sidecar_sha256": None,
        "prompt_file_sha256": None,
        "created_at": "2026-05-18T00:00:00+09:00",
        "notes": ["API experiment placeholder only; no call executed."],
        "raw_model_output_path": "raw_model_output.txt",
        "parsed_storyline_path": "parsed_storyline.json",
        "api_experiment_dir": (
            "outputs/model_dry_runs/anny_api_experiments/"
            "anny_api_experiment_ai_knowledge_institution_v1"
        ),
        "failure_modes": ["invalid_json", "source_hallucination"],
        "ready_for_api_experiment_prep": True,
        "ready_for_api_experiment": False,
        "ready_for_production_agent": False,
    }

    assert validate_with_schema(record, "anny_run_manifest_schema.json") == []


def test_failure_mode_schema_accepts_taxonomy_value() -> None:
    record = {
        "failure_mode": "needs_fact_check_removed_too_aggressively",
        "severity": "error",
        "description": "Caution markers were removed despite thin evidence.",
    }

    assert validate_with_schema(record, "anny_failure_mode_schema.json") == []


def test_api_experiment_case_is_registered() -> None:
    cases_path = paths.REPO_ROOT / "eval/golden_cases/anny_dry_run_cases.json"
    cases = json.loads(cases_path.read_text(encoding="utf-8"))["cases"]
    case = next(
        item
        for item in cases
        if item["case_id"] == "anny_api_experiment_ai_knowledge_institution_v1"
    )

    assert case["mode"] == "api_experiment"
    assert case["model_source"] == "openai_api"
    assert "raw_model_output.txt" in case["raw_model_output_path"]
    assert "source_urls는 input bundle" in "\n".join(case["evaluation_notes"])


def test_api_experiment_docs_cover_raw_output_and_repair_policy() -> None:
    failure_doc = (paths.REPO_ROOT / "docs/product/anny_failure_modes.md").read_text(
        encoding="utf-8"
    )
    contract_doc = (paths.REPO_ROOT / "docs/product/anny_output_contract.md").read_text(
        encoding="utf-8"
    )
    prompt = (paths.REPO_ROOT / "prompts/anny/storyline_writer.md").read_text(
        encoding="utf-8"
    )

    assert "raw_model_output.txt" in failure_doc
    assert "No automatic repair" in failure_doc
    assert "ready_for_api_experiment_prep: true" in contract_doc
    assert "candidate article URL" in prompt
