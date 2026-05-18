from pathlib import Path

from luddite.agents.anny.run_storyline import (
    AnnyRunCase,
    run_storyline_case,
    sha256_file,
    write_run_index,
)


def _case(tmp_path: Path, *, output_exists: bool = True) -> AnnyRunCase:
    input_bundle = tmp_path / "input_bundle.json"
    storyline = tmp_path / "storyline.json"
    hygiene = tmp_path / "hygiene.jsonl"
    evidence = tmp_path / "evidence.json"
    input_bundle.write_text("{}", encoding="utf-8")
    hygiene.write_text("", encoding="utf-8")
    evidence.write_text("{}", encoding="utf-8")
    if output_exists:
        storyline.write_text("{}", encoding="utf-8")
    return AnnyRunCase(
        run_id="anny_run_test_manual_v1",
        case_id="anny_dry_run_test_v1",
        bundle_id="anny_bundle_test",
        story_seed_title="테스트 스토리",
        input_bundle_path=input_bundle,
        output_storyline_path=storyline,
        hygiene_jsonl_path=hygiene,
        evidence_pack_path=evidence,
    )


def _eval_result() -> dict:
    return {
        "passed": True,
        "schema_valid": True,
        "hygiene_contract_passed": True,
        "section_count": 4,
        "slide_count": 24,
        "source_image_overlap_count": 0,
        "needs_source_count": 3,
        "needs_fact_check_count": 5,
        "hygiene_records": [
            {
                "slide_no": 1,
                "required_before_broadcast": True,
                "fact_check_kind": "production_checklist",
            }
        ],
        "counterpoint_included": True,
        "fact_check_marker_present": True,
        "do_not_claim_violations": [],
        "policy_finance_guardrails_passed": True,
    }


def test_run_storyline_case_writes_manifest_and_report(tmp_path, monkeypatch) -> None:
    import luddite.agents.anny.run_storyline as module

    monkeypatch.setattr(module, "validate_dry_run_storyline", lambda **_: _eval_result())
    result = run_storyline_case(
        _case(tmp_path),
        run_input_dir=tmp_path / "inputs",
        manifest_dir=tmp_path / "manifests",
        report_dir=tmp_path / "reports",
    )

    manifest = result["manifest"]
    assert manifest["status"] == "passed"
    assert manifest["schema_valid"] is True
    assert manifest["hygiene_passed"] is True
    assert manifest["output_contract_version"] == "anny_mvp_storyline_v1.7"
    assert manifest["validator_version"] == "anny_dry_run_eval_v1.7.1"
    assert manifest["input_bundle_sha256"] == sha256_file(_case(tmp_path).input_bundle_path)
    assert len(manifest["output_storyline_sha256"]) == 64
    assert manifest["production_checklist_included"] is True
    assert result["manifest_path"].exists()
    report = result["report_path"].read_text(encoding="utf-8")
    assert report.startswith("# Anny Run Report")
    assert "This run does not imply production readiness" in report
    assert "input_bundle_sha256" in report


def test_run_storyline_case_marks_missing_output_pending(tmp_path) -> None:
    result = run_storyline_case(
        _case(tmp_path, output_exists=False),
        run_input_dir=tmp_path / "inputs",
        manifest_dir=tmp_path / "manifests",
        report_dir=tmp_path / "reports",
    )

    assert result["manifest"]["status"] == "pending_manual_output"
    assert result["manifest"]["output_storyline_sha256"] is None
    assert "pending manual" in result["report_path"].read_text(encoding="utf-8")


def test_sha256_file_returns_none_for_missing_optional_file(tmp_path) -> None:
    assert sha256_file(None) is None
    assert sha256_file(tmp_path / "missing.json") is None


def test_write_run_index_records_runs(tmp_path) -> None:
    manifests = [
        {
            "run_id": "anny_run_test_manual_v1",
            "case_id": "case-a",
            "status": "passed",
            "model_source": "manual_gpt_pro",
            "input_bundle_path": "input.json",
            "output_storyline_path": "story.json",
            "eval_report_path": "report.md",
            "created_at": "2026-05-18T00:00:00+00:00",
            "schema_valid": True,
            "hygiene_passed": True,
        },
        {
            "run_id": "anny_run_other_manual_v1",
            "case_id": "case-b",
            "status": "failed",
            "model_source": "fixture",
            "input_bundle_path": "input2.json",
            "output_storyline_path": "story2.json",
            "eval_report_path": "report2.md",
            "created_at": "2026-05-18T00:00:01+00:00",
            "schema_valid": False,
            "hygiene_passed": False,
        },
    ]
    index_path = tmp_path / "index.jsonl"

    count = write_run_index(index_path, manifests)

    assert count == 2
    text = index_path.read_text(encoding="utf-8")
    assert "anny_run_test_manual_v1" in text
    assert '"ready_for_production_agent": false' in text
