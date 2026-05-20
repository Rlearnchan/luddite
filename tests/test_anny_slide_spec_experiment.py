import json
from copy import deepcopy
from pathlib import Path
from typing import Any

from luddite.agents.anny.slide_spec_experiment import (
    EXPERIMENT_CASES,
    _contract_diagnostics,
    _renderer_contract_diagnostics,
    _synthetic_fixture_output,
    build_slide_spec_experiment_prompt,
    run_experiment,
)
from luddite.agents.piti import render_visual_qa


def _visual_flag_count(path: Path, flag: str) -> int:
    payload = json.loads(path.read_text(encoding="utf-8"))
    deck = render_visual_qa.evaluate_slide_spec(path, payload, path.parent)
    return render_visual_qa._flag_counter([deck]).get(flag, 0)


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
        assert "diagram_quality_improved: true" in comparison
        assert "safety_regression_detected: false" in comparison
        assert "diagram_nodes_too_generic_delta" in comparison
        assert "visual_qa_review_delta" in comparison
        direct_diagram_flags = _visual_flag_count(
            case_dir / "parsed_piti_slide_spec.json",
            "diagram_nodes_too_generic",
        )
        adapter_diagram_flags = _visual_flag_count(
            case.adapter_slide_spec_path,
            "diagram_nodes_too_generic",
        )
        assert direct_diagram_flags < adapter_diagram_flags


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


def test_slide_spec_experiment_live_api_writes_separate_run_summary(
    tmp_path: Path,
    monkeypatch: Any,
) -> None:
    monkeypatch.setenv("OPENAI_API_KEY", "test-key")
    case = EXPERIMENT_CASES[0]

    def fixture_api(**_kwargs):
        return (
            json.dumps(_synthetic_fixture_output(case), ensure_ascii=False, indent=2),
            {"id": "fake-response", "usage": {"input_tokens": 10, "output_tokens": 20}},
        )

    output_root = tmp_path / "live"
    manifests = run_experiment(
        case_id=case.case_id,
        output_root=output_root,
        run_id="live_success",
        live_api=True,
        model="gpt-test",
        api_caller=fixture_api,
    )

    case_dir = output_root / "live_success" / case.case_id
    summary = output_root / "live_success" / "summary.md"
    assert len(manifests) == 1
    assert manifests[0]["mode"] == "live_api"
    assert manifests[0]["experiment_outcome"] == "success"
    assert manifests[0]["comparison_deltas"]["diagram_quality_improved"] is True
    assert (case_dir / "raw_model_output.txt").exists()
    assert (case_dir / "parsed_piti_slide_spec.json").exists()
    assert summary.exists()
    summary_text = summary.read_text(encoding="utf-8")
    assert "- mode: live" in summary_text
    assert "live_success" in summary_text
    assert "success" in summary_text
    assert "production readiness" in summary_text.lower()
    assert "section slide missing" in summary_text
    assert "diagram node arrows" in summary_text
    assert not (output_root / case.case_id).exists()


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
        run_id="failure_run",
        live_api=True,
        model="gpt-test",
        api_caller=fail_api,
    )

    manifest = manifests[0]
    case_dir = output_root / "failure_run" / "ai_knowledge_institution"
    assert manifest["failure_modes"] == ["api_request_failed"]
    assert manifest["experiment_outcome"] == "failure"
    assert (case_dir / "raw_model_output.txt").exists()
    assert "simulated API outage" in (case_dir / "api_error.txt").read_text(
        encoding="utf-8"
    )
    assert not (case_dir / "parsed_piti_slide_spec.json").exists()
    assert (output_root / "failure_run" / "summary.md").exists()
    assert not (review_output_dir / "failure_run").exists()


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
        run_id="invalid_json_run",
        live_api=True,
        model="gpt-test",
        api_caller=invalid_json_api,
    )

    manifest = manifests[0]
    case_dir = output_root / "invalid_json_run" / "ai_knowledge_institution"
    assert manifest["failure_modes"] == ["invalid_json"]
    assert manifest["experiment_outcome"] == "failure"
    assert manifest["parse_status"].startswith("invalid_json")
    assert (case_dir / "raw_model_output.txt").read_text(encoding="utf-8") == "not json"
    assert (case_dir / "response_metadata.json").exists()
    assert not (case_dir / "parsed_piti_slide_spec.json").exists()
    assert (output_root / "invalid_json_run" / "summary.md").exists()
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
    assert "at least 3 nodes" in prompt
    assert "short broadcast sentences" in prompt
    assert "Do not expose source URLs on screen" in prompt
    assert "Every sections[] object must include a non-empty slides array" in prompt
    assert "Allowed layout_intent values" in prompt
    assert "Never use layout_intent=hook" in prompt
    assert "fewer than 20" in prompt
    assert "Never remove needs_fact_check=true" in prompt
    assert "No diagram_nodes[] string contains ->" in prompt
    assert "Never output an empty deck" in prompt
    assert "Top-level slides[] must be non-empty" in prompt
    assert "article_quote requires non-empty quote_text" in prompt
    assert "Chart/table proof objects need data_hint" in prompt


def test_slide_spec_contract_diagnostics_catches_live_regression_patterns() -> None:
    case = EXPERIMENT_CASES[0]
    adapter = _synthetic_fixture_output(case)
    for slide in adapter["slides"]:
        slide["do_not_claim"] = slide.get("do_not_claim") or ["guardrail"]
    direct = deepcopy(adapter)
    direct["slides"] = direct["slides"][:8]
    for section in direct["sections"]:
        section.pop("slides", None)
    for slide in direct["slides"]:
        slide["source_refs"] = []
        slide["do_not_claim"] = []
        slide["needs_fact_check"] = False
        slide["required_before_broadcast"] = False
        proof = slide.get("proof_object", {})
        proof["source_url"] = None
        proof["image_url"] = None
    direct["slides"][0]["layout_intent"] = "hook"
    first_diagram = next(
        slide
        for slide in direct["slides"]
        if slide.get("proof_object", {}).get("type") == "diagram"
    )
    first_diagram["proof_object"]["diagram_nodes"] = [
        "사용자가 질문함 -> AI가 답함 -> 검증이 약해짐"
    ]

    diagnostics = _contract_diagnostics(direct, adapter)

    assert diagnostics["slide_count_too_compressed"] is True
    assert diagnostics["missing_sections_slides_count"] == len(direct["sections"])
    assert diagnostics["section_slide_ref_mismatch_count"] >= len(direct["slides"])
    assert diagnostics["layout_intent_invalid_enum_count"] == 1
    assert diagnostics["source_refs_removed_too_aggressively"] is True
    assert diagnostics["do_not_claim_removed_or_ignored"] is True
    assert diagnostics["top_level_slides_empty"] is False
    assert diagnostics["minimum_slide_count_failed"] is True
    assert diagnostics["needs_fact_check_delta_vs_adapter"] < 0
    assert diagnostics["required_before_broadcast_delta_vs_adapter"] <= 0
    assert diagnostics["diagram_nodes_with_arrow_count"] == 1


def test_slide_spec_empty_deck_is_live_failure(tmp_path: Path, monkeypatch: Any) -> None:
    monkeypatch.setenv("OPENAI_API_KEY", "test-key")
    case = EXPERIMENT_CASES[0]
    empty_deck = deepcopy(_synthetic_fixture_output(case))
    empty_deck["slides"] = []
    for section in empty_deck["sections"]:
        section["slides"] = []

    def empty_deck_api(**_kwargs):
        return json.dumps(empty_deck, ensure_ascii=False), {"id": "fake-response"}

    manifests = run_experiment(
        case_id=case.case_id,
        output_root=tmp_path / "live",
        run_id="empty_deck",
        live_api=True,
        model="gpt-test",
        api_caller=empty_deck_api,
    )

    manifest = manifests[0]
    assert manifest["experiment_outcome"] == "failure"
    assert manifest["top_level_slides_empty"] is True
    assert manifest["empty_sections_count"] == len(empty_deck["sections"])
    assert "top_level_slides_empty" in manifest["failure_modes"]
    assert "empty_sections" in manifest["failure_modes"]
    assert "minimum_slide_count_failed" in manifest["failure_modes"]
    assert "deck_has_no_renderable_slides" in manifest["failure_modes"]


def test_renderer_contract_diagnostics_catches_proof_failures() -> None:
    spec = {
        "slides": [
            {
                "slide_no": 1,
                "screen_headline": "차트 슬라이드",
                "screen_body": ["긴 설명 1", "긴 설명 2"],
                "proof_object": {"type": "chart", "display_title": "차트"},
            },
            {
                "slide_no": 2,
                "screen_headline": "인용 슬라이드",
                "screen_body": [],
                "proof_object": {"type": "article_quote", "quote_text": ""},
            },
            {
                "slide_no": 3,
                "screen_headline": "출처 슬라이드",
                "screen_body": [],
                "proof_object": {
                    "type": "source_card",
                    "display_title": "Reference material",
                },
            },
        ]
    }

    diagnostics = _renderer_contract_diagnostics(spec)

    assert diagnostics["chart_table_body_too_long_count"] == 1
    assert diagnostics["chart_table_body_too_long_slides"] == [1]
    assert diagnostics["article_quote_missing_quote_text_count"] == 1
    assert diagnostics["article_quote_missing_quote_text_slides"] == [2]
    assert diagnostics["source_card_generic_title_count"] == 1
    assert diagnostics["source_card_generic_title_slides"] == [3]
    assert diagnostics["proof_object_renderer_contract_failed"] is True
    assert diagnostics["renderer_failure_reasons"]
