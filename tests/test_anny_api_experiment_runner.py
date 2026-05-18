from pathlib import Path

from luddite import paths
from luddite.agents.anny.api_experiment_runner import (
    build_api_experiment_prompt,
    run_api_experiment,
    validate_api_experiment_raw_output,
    write_api_v1_v2_comparison_report,
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


def test_rhetorical_title_and_closing_slides_without_claims_are_allowed(tmp_path) -> None:
    result = _run_fixture(tmp_path, "rhetorical_source_rule_raw.txt")

    assert result.schema_valid is True
    assert "unsupported_claim" not in result.failure_modes
    assert "counterpoint_missing" not in result.failure_modes


def test_rhetorical_slide_with_factual_claim_still_requires_source(tmp_path) -> None:
    result = _run_fixture(tmp_path, "rhetorical_factual_claim_raw.txt")

    assert result.schema_valid is True
    assert "unsupported_claim" in result.failure_modes
    assert "needs_fact_check_removed_too_aggressively" in result.failure_modes


def test_production_checklist_without_sources_is_allowed(tmp_path) -> None:
    result = _run_fixture(tmp_path, "production_checklist_source_rule_raw.txt")

    assert result.schema_valid is True
    assert "unsupported_claim" not in result.failure_modes
    assert result.failure_modes == ["key_beat_drift"]


def test_manifest_and_report_are_generated(tmp_path) -> None:
    result = _run_fixture(tmp_path, "source_hallucination_raw.txt")
    manifest_text = result.manifest_path.read_text(encoding="utf-8")
    report_text = result.report_path.read_text(encoding="utf-8")

    assert "source_hallucination" in manifest_text
    assert "allowed_url_count" in report_text
    assert "raw_model_output_retained: true" in report_text


def test_run_api_experiment_with_fake_caller_generates_artifacts(tmp_path, monkeypatch) -> None:
    monkeypatch.setenv("OPENAI_API_KEY", "test-key")
    monkeypatch.setenv("LUDDITE_ANNY_API_MODEL", "gpt-5-mini")

    raw_text = (FIXTURE_DIR / "valid_ai_knowledge_storyline_raw.txt").read_text(
        encoding="utf-8"
    )

    def fake_caller(**kwargs):
        assert kwargs["model"] == "gpt-5-mini"
        assert kwargs["temperature"] == 0.2
        assert "Allowed Source URLs" in kwargs["prompt"]
        return raw_text, {"id": "resp_fixture", "output_text": raw_text}

    result = run_api_experiment(
        run_id="anny_api_experiment_test",
        input_bundle_path=INPUT_BUNDLE,
        evidence_pack_path=EVIDENCE_PACK,
        prompt_file_path=paths.PROMPTS_DIR / "anny/storyline_writer.md",
        manual_storyline_path=(
            paths.ANNY_STORYLINE_DRY_RUN_DIR
            / "ai_knowledge_institution_gpt_pro_storyline_enriched.json"
        ),
        comparison_report_path=tmp_path / "comparison.md",
        experiment_root=tmp_path / "experiments",
        api_caller=fake_caller,
    )

    experiment_dir = Path(result["experiment_dir"])
    assert result["model"] == "gpt-5-mini"
    assert result["schema_valid"] is True
    assert result["hygiene_passed"] is True
    assert (experiment_dir / "input_bundle.json").exists()
    assert (experiment_dir / "evidence_pack.json").exists()
    assert (experiment_dir / "prompt.md").exists()
    assert (experiment_dir / "raw_model_output.txt").exists()
    assert (experiment_dir / "parsed_storyline.json").exists()
    assert (experiment_dir / "validation_report.md").exists()
    assert (experiment_dir / "manifest.json").exists()
    assert (tmp_path / "comparison.md").exists()


def test_run_api_experiment_requires_env_key(tmp_path, monkeypatch) -> None:
    import luddite.agents.anny.api_experiment_runner as module

    monkeypatch.setattr(module, "ENV_FILES", [])
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    monkeypatch.setenv("LUDDITE_ANNY_API_MODEL", "gpt-5-mini")

    try:
        run_api_experiment(
            run_id="anny_api_experiment_missing_key",
            experiment_root=tmp_path / "experiments",
            comparison_report_path=tmp_path / "comparison.md",
            api_caller=lambda **_: ("{}", {}),
        )
    except RuntimeError as exc:
        assert "OPENAI_API_KEY" in str(exc)
    else:
        raise AssertionError("Expected missing OPENAI_API_KEY error")


def test_run_api_experiment_records_api_request_failure(tmp_path, monkeypatch) -> None:
    monkeypatch.setenv("OPENAI_API_KEY", "test-key")
    monkeypatch.setenv("LUDDITE_ANNY_API_MODEL", "gpt-5-mini")

    def failing_caller(**kwargs):
        raise RuntimeError("timeout")

    result = run_api_experiment(
        run_id="anny_api_experiment_timeout",
        input_bundle_path=INPUT_BUNDLE,
        evidence_pack_path=EVIDENCE_PACK,
        prompt_file_path=paths.PROMPTS_DIR / "anny/storyline_writer.md",
        manual_storyline_path=(
            paths.ANNY_STORYLINE_DRY_RUN_DIR
            / "ai_knowledge_institution_gpt_pro_storyline_enriched.json"
        ),
        comparison_report_path=tmp_path / "comparison.md",
        experiment_root=tmp_path / "experiments",
        api_caller=failing_caller,
    )

    experiment_dir = Path(result["experiment_dir"])
    assert result["failure_modes"] == ["api_request_failed"]
    assert (experiment_dir / "raw_model_output.txt").exists()
    assert not (experiment_dir / "parsed_storyline.json").exists()
    assert "api_request_failed" in (experiment_dir / "manifest.json").read_text(
        encoding="utf-8"
    )


def test_run_api_experiment_loads_gitignored_env_file(tmp_path, monkeypatch) -> None:
    import luddite.agents.anny.api_experiment_runner as module

    env_file = tmp_path / ".env.local"
    env_file.write_text(
        "OPENAI_API_KEY=test-key-from-file\nLUDDITE_ANNY_API_MODEL=gpt-5-mini\n",
        encoding="utf-8",
    )
    monkeypatch.setattr(module, "ENV_FILES", [env_file])
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    monkeypatch.delenv("LUDDITE_ANNY_API_MODEL", raising=False)
    raw_text = (FIXTURE_DIR / "valid_ai_knowledge_storyline_raw.txt").read_text(
        encoding="utf-8"
    )

    def fake_caller(**kwargs):
        assert kwargs["api_key"] == "test-key-from-file"
        assert kwargs["model"] == "gpt-5-mini"
        return raw_text, {"id": "resp_fixture", "output_text": raw_text}

    result = run_api_experiment(
        run_id="anny_api_experiment_env_file",
        input_bundle_path=INPUT_BUNDLE,
        evidence_pack_path=EVIDENCE_PACK,
        prompt_file_path=paths.PROMPTS_DIR / "anny/storyline_writer.md",
        manual_storyline_path=(
            paths.ANNY_STORYLINE_DRY_RUN_DIR
            / "ai_knowledge_institution_gpt_pro_storyline_enriched.json"
        ),
        comparison_report_path=tmp_path / "comparison.md",
        experiment_root=tmp_path / "experiments",
        api_caller=fake_caller,
    )

    assert result["schema_valid"] is True


def test_build_api_experiment_prompt_contains_allowed_urls_and_schema() -> None:
    input_bundle = {"candidate_articles": [{"url": "https://example.com/a"}]}
    evidence_pack = {"primary_article": {"url": "https://example.com/b"}}
    prompt = build_api_experiment_prompt(
        input_bundle=input_bundle,
        evidence_pack=evidence_pack,
        prompt_text="base prompt",
        schema={"title": "Schema"},
        allowed_urls={"https://example.com/a", "https://example.com/b"},
    )

    assert "base prompt" in prompt
    assert "https://example.com/a" in prompt
    assert "https://example.com/b" in prompt
    assert "Output Schema JSON" in prompt


def test_write_api_v1_v2_comparison_report(tmp_path) -> None:
    v1 = tmp_path / "v1"
    v2 = tmp_path / "v2"
    v1.mkdir()
    v2.mkdir()
    raw = (FIXTURE_DIR / "valid_ai_knowledge_storyline_raw.txt").read_text(
        encoding="utf-8"
    )
    (v1 / "parsed_storyline.json").write_text(raw, encoding="utf-8")
    (v2 / "parsed_storyline.json").write_text(raw, encoding="utf-8")
    manifest = {
        "model": "gpt-5-mini",
        "failure_modes": [],
        "schema_valid": True,
        "hygiene_passed": True,
        "hallucinated_urls": [],
        "do_not_claim_violations": [],
    }
    (v1 / "manifest.json").write_text(__import__("json").dumps(manifest), encoding="utf-8")
    (v2 / "manifest.json").write_text(__import__("json").dumps(manifest), encoding="utf-8")
    report = tmp_path / "comparison.md"

    result = write_api_v1_v2_comparison_report(
        v1_dir=v1,
        v2_dir=v2,
        comparison_report_path=report,
    )

    assert result["v1"]["manifest"]["model"] == "gpt-5-mini"
    text = report.read_text(encoding="utf-8")
    assert "v1/v2 Comparison" in text
    assert "ready_for_production_agent=false" in text
