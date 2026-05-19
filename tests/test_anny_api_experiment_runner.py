import json
from pathlib import Path

from luddite import paths
from luddite.agents.anny.api_experiment_runner import (
    build_api_experiment_prompt,
    run_api_experiment,
    validate_api_experiment_raw_output,
    write_api_v1_to_v5_comparison_report,
    write_api_v1_to_v6_comparison_report,
    write_api_v1_to_v7_comparison_report,
    write_api_v1_to_v8_comparison_report,
    write_api_v1_to_v9_comparison_report,
    write_api_v1_v2_comparison_report,
    write_api_v1_v2_v3_comparison_report,
    write_api_v1_v2_v3_v4_comparison_report,
    write_productive_finance_claim_hygiene_review,
    write_v6_claim_hygiene_review,
)

FIXTURE_DIR = paths.REPO_ROOT / "tests/fixtures/anny_api_experiment"
INPUT_BUNDLE = (
    paths.ANNY_STORYLINE_DRY_RUN_DIR / "ai_knowledge_institution_input_bundle.json"
)
EVIDENCE_PACK = paths.ANNY_EVIDENCE_PACK_AI_KNOWLEDGE_JSON

FINANCE_INPUT_BUNDLE_PAYLOAD = {
    "story_seed_title": "생산적 금융과 정책자금 전환",
    "risk_flags": ["investment_advice_risk", "policy_effect_uncertainty"],
    "do_not_claim": ["투자 조언처럼 쓰지 말 것"],
}


def _run_fixture(tmp_path: Path, name: str):
    return validate_api_experiment_raw_output(
        raw_output_path=FIXTURE_DIR / name,
        input_bundle_path=INPUT_BUNDLE,
        evidence_pack_path=EVIDENCE_PACK,
        experiment_dir=tmp_path / "experiments" / name.replace(".txt", ""),
        report_path=tmp_path / "reports" / f"{name}.md",
    )


def _run_modified_valid_fixture(tmp_path: Path, modifier):
    payload = json.loads(
        (FIXTURE_DIR / "valid_ai_knowledge_storyline_raw.txt").read_text(
            encoding="utf-8"
        )
    )
    modifier(payload)
    raw_path = tmp_path / "modified_raw.txt"
    raw_path.write_text(json.dumps(payload, ensure_ascii=False), encoding="utf-8")
    return validate_api_experiment_raw_output(
        raw_output_path=raw_path,
        input_bundle_path=INPUT_BUNDLE,
        evidence_pack_path=EVIDENCE_PACK,
        experiment_dir=tmp_path / "experiments" / "modified",
        report_path=tmp_path / "reports" / "modified.md",
    )


def _run_modified_finance_fixture(tmp_path: Path, modifier):
    payload = json.loads(
        (FIXTURE_DIR / "valid_ai_knowledge_storyline_raw.txt").read_text(
            encoding="utf-8"
        )
    )
    modifier(payload)
    raw_path = tmp_path / "finance_modified_raw.txt"
    raw_path.write_text(json.dumps(payload, ensure_ascii=False), encoding="utf-8")
    input_bundle_path = tmp_path / "finance_input_bundle.json"
    input_bundle_path.write_text(
        json.dumps(FINANCE_INPUT_BUNDLE_PAYLOAD, ensure_ascii=False),
        encoding="utf-8",
    )
    evidence_pack_path = tmp_path / "finance_evidence_pack.json"
    evidence_pack_path.write_text(
        json.dumps({"source": {"url": "https://example.com/source"}}, ensure_ascii=False),
        encoding="utf-8",
    )
    return validate_api_experiment_raw_output(
        raw_output_path=raw_path,
        input_bundle_path=input_bundle_path,
        evidence_pack_path=evidence_pack_path,
        experiment_dir=tmp_path / "experiments" / "finance_modified",
        report_path=tmp_path / "reports" / "finance_modified.md",
        case_id="anny_api_experiment_productive_finance_policy_v1",
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


def test_missing_key_beat_coverage_fails(tmp_path) -> None:
    def remove_one(payload):
        payload["key_beat_coverage"] = payload["key_beat_coverage"][:-1]

    result = _run_modified_valid_fixture(tmp_path, remove_one)
    report = result.report_path.read_text(encoding="utf-8")

    assert "key_beat_drift" in result.failure_modes
    assert "missing_key_beat" in report


def test_covered_key_beat_requires_slide_refs(tmp_path) -> None:
    def clear_refs(payload):
        payload["key_beat_coverage"][0]["slide_refs"] = []

    result = _run_modified_valid_fixture(tmp_path, clear_refs)
    report = result.report_path.read_text(encoding="utf-8")

    assert "key_beat_drift" in result.failure_modes
    assert "weak_key_beat_mapping" in report


def test_key_beat_slide_refs_must_exist(tmp_path) -> None:
    def invalid_ref(payload):
        payload["key_beat_coverage"][0]["slide_refs"] = [999]

    result = _run_modified_valid_fixture(tmp_path, invalid_ref)
    report = result.report_path.read_text(encoding="utf-8")

    assert "key_beat_drift" in result.failure_modes
    assert "invalid_key_beat_slide_ref" in report


def test_key_beat_slide_refs_must_match_slide_text(tmp_path) -> None:
    def wrong_ref(payload):
        payload["key_beat_coverage"][0]["slide_refs"] = [3]

    result = _run_modified_valid_fixture(tmp_path, wrong_ref)
    report = result.report_path.read_text(encoding="utf-8")

    assert "key_beat_drift" in result.failure_modes
    assert "key_beat_covered_but_not_in_slide_text" in report


def test_required_key_beat_must_have_covers_key_beats_slide(tmp_path) -> None:
    def remove_covers(payload):
        for section in payload["sections"]:
            section["section_title"] = "정책금융 설명"
            for slide in section["slides"]:
                slide.pop("covers_key_beats", None)

    result = _run_modified_valid_fixture(tmp_path, remove_covers)
    report = result.report_path.read_text(encoding="utf-8")

    assert "key_beat_drift" in result.failure_modes
    assert "missing_covers_key_beats" in report


def test_covers_key_beats_requires_anchor_phrase(tmp_path) -> None:
    def remove_anchor(payload):
        payload["sections"][0]["slides"][0]["headline"] = "도입"
        payload["sections"][0]["slides"][0]["body"] = ["이야기를 시작한다."]

    result = _run_modified_valid_fixture(tmp_path, remove_anchor)
    report = result.report_path.read_text(encoding="utf-8")

    assert "key_beat_drift" in result.failure_modes
    assert "key_beat_anchor_phrase_not_in_text" in report


def test_covers_key_beats_requires_anchor_used_metadata(tmp_path) -> None:
    def remove_anchor_used(payload):
        payload["sections"][0]["slides"][0].pop("key_beat_anchors_used", None)

    result = _run_modified_valid_fixture(tmp_path, remove_anchor_used)
    report = result.report_path.read_text(encoding="utf-8")

    assert "key_beat_drift" in result.failure_modes
    assert "missing_key_beat_anchor_used" in report


def test_key_beat_anchor_used_must_be_allowed_phrase(tmp_path) -> None:
    def invalid_anchor(payload):
        payload["sections"][0]["slides"][0]["key_beat_anchors_used"] = [
            {"key_beat_id": "kb_ai_convenience", "anchor_phrase": "없는 앵커"}
        ]

    result = _run_modified_valid_fixture(tmp_path, invalid_anchor)
    report = result.report_path.read_text(encoding="utf-8")

    assert "key_beat_drift" in result.failure_modes
    assert "invalid_key_beat_anchor_phrase" in report


def test_invalid_covers_key_beats_value_fails(tmp_path) -> None:
    def invalid_cover(payload):
        payload["sections"][0]["slides"][0]["covers_key_beats"] = ["없는 비트"]

    result = _run_modified_valid_fixture(tmp_path, invalid_cover)
    report = result.report_path.read_text(encoding="utf-8")

    assert "key_beat_drift" in result.failure_modes
    assert "invalid_covers_key_beat_value" in report


def test_korea_bridge_in_covers_key_beats_fails(tmp_path) -> None:
    def invalid_cover(payload):
        payload["sections"][0]["slides"][0]["covers_key_beats"] = ["Korean_bridge"]

    result = _run_modified_valid_fixture(tmp_path, invalid_cover)
    report = result.report_path.read_text(encoding="utf-8")

    assert "key_beat_drift" in result.failure_modes
    assert "invalid_covers_key_beat_value" in report
    assert "Korean_bridge" in report


def test_key_beat_coverage_refs_must_align_with_covers_key_beats(tmp_path) -> None:
    def mismatch_cover(payload):
        payload["sections"][0]["slides"][0]["covers_key_beats"] = ["kb_thinking_process"]

    result = _run_modified_valid_fixture(tmp_path, mismatch_cover)
    report = result.report_path.read_text(encoding="utf-8")

    assert "key_beat_drift" in result.failure_modes
    assert "coverage_ref_missing_in_covers" in report


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


def test_title_with_source_specific_marker_without_source_fails(tmp_path) -> None:
    result = _run_fixture(tmp_path, "rhetorical_source_rule_raw.txt")
    parsed = result.experiment_dir / "parsed_storyline.json"
    import json

    payload = json.loads(parsed.read_text(encoding="utf-8"))
    payload["sections"][0]["slides"][0]["body"] = ["Royal Observatory warns about AI."]
    raw_path = tmp_path / "source_specific_title.txt"
    raw_path.write_text(json.dumps(payload, ensure_ascii=False), encoding="utf-8")
    result = validate_api_experiment_raw_output(
        raw_output_path=raw_path,
        input_bundle_path=INPUT_BUNDLE,
        evidence_pack_path=EVIDENCE_PACK,
        experiment_dir=tmp_path / "experiments" / "source_specific_title",
        report_path=tmp_path / "reports" / "source_specific_title.md",
    )

    assert "unsupported_claim" in result.failure_modes


def test_source_specific_title_with_needs_source_true_is_not_unsupported(tmp_path) -> None:
    result = _run_fixture(tmp_path, "rhetorical_source_rule_raw.txt")
    parsed = result.experiment_dir / "parsed_storyline.json"
    payload = json.loads(parsed.read_text(encoding="utf-8"))
    slide = payload["sections"][0]["slides"][0]
    slide["body"] = ["Royal Observatory warns about AI."]
    slide["needs_source"] = True
    raw_path = tmp_path / "source_specific_title_needs_source.txt"
    raw_path.write_text(json.dumps(payload, ensure_ascii=False), encoding="utf-8")
    result = validate_api_experiment_raw_output(
        raw_output_path=raw_path,
        input_bundle_path=INPUT_BUNDLE,
        evidence_pack_path=EVIDENCE_PACK,
        experiment_dir=tmp_path / "experiments" / "source_specific_title_needs_source",
        report_path=tmp_path / "reports" / "source_specific_title_needs_source.md",
    )

    assert "unsupported_claim" not in result.failure_modes


def test_title_with_source_specific_marker_and_source_passes(tmp_path) -> None:
    def sourced_title(payload):
        slide = payload["sections"][0]["slides"][0]
        slide["slide_type"] = "title"
        slide["body"] = ["Royal Observatory warns about AI."]
        slide["source_urls"] = [
            "https://www.bbc.com/news/articles/c2023l60370o?at_medium=RSS&at_campaign=rss"
        ]
        slide["needs_fact_check"] = True

    result = _run_modified_valid_fixture(tmp_path, sourced_title)

    assert "unsupported_claim" not in result.failure_modes


def test_pure_closing_question_without_factual_claim_passes(tmp_path) -> None:
    result = _run_fixture(tmp_path, "rhetorical_source_rule_raw.txt")

    assert "unsupported_claim" not in result.failure_modes


def test_closing_question_with_factual_premise_requires_source(tmp_path) -> None:
    result = _run_fixture(tmp_path, "rhetorical_source_rule_raw.txt")
    parsed = result.experiment_dir / "parsed_storyline.json"
    payload = json.loads(parsed.read_text(encoding="utf-8"))
    closing = next(
        slide
        for slide in payload["sections"][0]["slides"]
        if slide["slide_type"] == "closing_question"
    )
    closing["body"] = [
        "AI 학습이 생각하는 과정을 줄인다면, 지식기관은 무엇을 가르쳐야 할까?"
    ]
    raw_path = tmp_path / "closing_with_premise.txt"
    raw_path.write_text(json.dumps(payload, ensure_ascii=False), encoding="utf-8")
    result = validate_api_experiment_raw_output(
        raw_output_path=raw_path,
        input_bundle_path=INPUT_BUNDLE,
        evidence_pack_path=EVIDENCE_PACK,
        experiment_dir=tmp_path / "experiments" / "closing_with_premise",
        report_path=tmp_path / "reports" / "closing_with_premise.md",
    )

    assert "unsupported_claim" in result.failure_modes


def test_claim_bearing_closing_question_with_needs_source_passes_unsupported_check(
    tmp_path,
) -> None:
    result = _run_fixture(tmp_path, "rhetorical_source_rule_raw.txt")
    parsed = result.experiment_dir / "parsed_storyline.json"
    payload = json.loads(parsed.read_text(encoding="utf-8"))
    closing = next(
        slide
        for slide in payload["sections"][0]["slides"]
        if slide["slide_type"] == "closing_question"
    )
    closing["body"] = [
        "AI 학습이 생각하는 과정을 줄인다면, 지식기관은 무엇을 가르쳐야 할까?"
    ]
    closing["needs_source"] = True
    closing["needs_fact_check"] = True
    raw_path = tmp_path / "closing_with_premise_needs_source.txt"
    raw_path.write_text(json.dumps(payload, ensure_ascii=False), encoding="utf-8")
    result = validate_api_experiment_raw_output(
        raw_output_path=raw_path,
        input_bundle_path=INPUT_BUNDLE,
        evidence_pack_path=EVIDENCE_PACK,
        experiment_dir=tmp_path / "experiments" / "closing_with_premise_needs_source",
        report_path=tmp_path / "reports" / "closing_with_premise_needs_source.md",
    )

    assert "unsupported_claim" not in result.failure_modes
    assert "needs_fact_check_removed_too_aggressively" not in result.failure_modes


def test_claim_bearing_closing_question_without_fact_check_fails(tmp_path) -> None:
    result = _run_fixture(tmp_path, "rhetorical_source_rule_raw.txt")
    parsed = result.experiment_dir / "parsed_storyline.json"
    payload = json.loads(parsed.read_text(encoding="utf-8"))
    closing = next(
        slide
        for slide in payload["sections"][0]["slides"]
        if slide["slide_type"] == "closing_question"
    )
    closing["body"] = [
        "AI 학습이 생각하는 과정을 줄인다면, 지식기관은 무엇을 가르쳐야 할까?"
    ]
    closing["needs_source"] = True
    closing["needs_fact_check"] = False
    raw_path = tmp_path / "closing_with_premise_without_fact_check.txt"
    raw_path.write_text(json.dumps(payload, ensure_ascii=False), encoding="utf-8")
    result = validate_api_experiment_raw_output(
        raw_output_path=raw_path,
        input_bundle_path=INPUT_BUNDLE,
        evidence_pack_path=EVIDENCE_PACK,
        experiment_dir=tmp_path / "experiments" / "closing_with_premise_without_fact_check",
        report_path=tmp_path / "reports" / "closing_with_premise_without_fact_check.md",
    )

    assert "unsupported_claim" not in result.failure_modes
    assert "needs_fact_check_removed_too_aggressively" in result.failure_modes


def test_pure_section_title_question_without_source_passes(tmp_path) -> None:
    result = _run_fixture(tmp_path, "rhetorical_source_rule_raw.txt")
    parsed = result.experiment_dir / "parsed_storyline.json"
    payload = json.loads(parsed.read_text(encoding="utf-8"))
    section_title = payload["sections"][0]["slides"][3]
    section_title["slide_type"] = "section_title"
    section_title["headline"] = "학교와 지식기관은 무엇을 해야 하나?"
    section_title["body"] = ["섹션 질문으로 다음 흐름을 연다."]
    section_title["source_urls"] = []
    section_title["needs_source"] = False
    section_title["needs_fact_check"] = False
    raw_path = tmp_path / "pure_section_title_question.txt"
    raw_path.write_text(json.dumps(payload, ensure_ascii=False), encoding="utf-8")
    result = validate_api_experiment_raw_output(
        raw_output_path=raw_path,
        input_bundle_path=INPUT_BUNDLE,
        evidence_pack_path=EVIDENCE_PACK,
        experiment_dir=tmp_path / "experiments" / "pure_section_title_question",
        report_path=tmp_path / "reports" / "pure_section_title_question.md",
    )

    assert "unsupported_claim" not in result.failure_modes


def test_section_title_institution_role_claim_without_source_fails(tmp_path) -> None:
    result = _run_fixture(tmp_path, "rhetorical_source_rule_raw.txt")
    parsed = result.experiment_dir / "parsed_storyline.json"
    payload = json.loads(parsed.read_text(encoding="utf-8"))
    section_title = payload["sections"][0]["slides"][3]
    section_title["slide_type"] = "section_title"
    section_title["headline"] = "지식기관의 역할 변화"
    section_title["body"] = ["AI 시대에는 질문하는 능력이 핵심이 된다."]
    section_title["source_urls"] = []
    section_title["needs_source"] = False
    section_title["needs_fact_check"] = False
    raw_path = tmp_path / "section_title_role_claim.txt"
    raw_path.write_text(json.dumps(payload, ensure_ascii=False), encoding="utf-8")
    result = validate_api_experiment_raw_output(
        raw_output_path=raw_path,
        input_bundle_path=INPUT_BUNDLE,
        evidence_pack_path=EVIDENCE_PACK,
        experiment_dir=tmp_path / "experiments" / "section_title_role_claim",
        report_path=tmp_path / "reports" / "section_title_role_claim.md",
    )
    report_text = result.report_path.read_text(encoding="utf-8")

    assert "unsupported_claim" in result.failure_modes
    assert "triggered_marker" in report_text
    assert "institution_role" in report_text


def test_section_title_role_claim_with_needs_source_passes_unsupported_check(
    tmp_path,
) -> None:
    result = _run_fixture(tmp_path, "rhetorical_source_rule_raw.txt")
    parsed = result.experiment_dir / "parsed_storyline.json"
    payload = json.loads(parsed.read_text(encoding="utf-8"))
    section_title = payload["sections"][0]["slides"][3]
    section_title["slide_type"] = "section_title"
    section_title["headline"] = "지식기관의 역할 변화"
    section_title["body"] = ["AI 시대에는 질문하는 능력이 핵심이 된다."]
    section_title["source_urls"] = []
    section_title["needs_source"] = True
    section_title["needs_fact_check"] = False
    raw_path = tmp_path / "section_title_role_claim_needs_source.txt"
    raw_path.write_text(json.dumps(payload, ensure_ascii=False), encoding="utf-8")
    result = validate_api_experiment_raw_output(
        raw_output_path=raw_path,
        input_bundle_path=INPUT_BUNDLE,
        evidence_pack_path=EVIDENCE_PACK,
        experiment_dir=tmp_path / "experiments" / "section_title_role_claim_needs_source",
        report_path=tmp_path / "reports" / "section_title_role_claim_needs_source.md",
    )

    assert "unsupported_claim" not in result.failure_modes


def test_rhetorical_slide_with_factual_claim_still_requires_source(tmp_path) -> None:
    result = _run_fixture(tmp_path, "rhetorical_factual_claim_raw.txt")

    assert result.schema_valid is True
    assert "unsupported_claim" in result.failure_modes
    assert "needs_fact_check_removed_too_aggressively" in result.failure_modes


def test_institution_role_claim_with_needs_fact_check_passes_fact_check_rule(
    tmp_path,
) -> None:
    result = _run_fixture(tmp_path, "rhetorical_source_rule_raw.txt")
    parsed = result.experiment_dir / "parsed_storyline.json"
    payload = json.loads(parsed.read_text(encoding="utf-8"))
    slide = payload["sections"][0]["slides"][0]
    slide["slide_type"] = "explainer"
    slide["headline"] = "지식기관의 역할 변화"
    slide["body"] = ["학교와 박물관은 질문 설계와 출처 평가를 가르치는 역할로 이동할 수 있다."]
    slide["source_urls"] = [
        "https://www.unesco.org/en/articles/ai-competency-framework-students"
    ]
    slide["source_refs"] = [
        {
            "url": "https://www.unesco.org/en/articles/ai-competency-framework-students",
            "role": "institution_example",
            "use": "AI competency framework context",
            "confidence": "medium",
            "manual_check_required": True,
        }
    ]
    slide["needs_fact_check"] = True
    raw_path = tmp_path / "institution_role_fact_checked.txt"
    raw_path.write_text(json.dumps(payload, ensure_ascii=False), encoding="utf-8")
    result = validate_api_experiment_raw_output(
        raw_output_path=raw_path,
        input_bundle_path=INPUT_BUNDLE,
        evidence_pack_path=EVIDENCE_PACK,
        experiment_dir=tmp_path / "experiments" / "institution_role_fact_checked",
        report_path=tmp_path / "reports" / "institution_role_fact_checked.md",
    )

    assert "needs_fact_check_removed_too_aggressively" not in result.failure_modes


def test_source_refs_do_not_remove_institution_fact_check_requirement(tmp_path) -> None:
    result = _run_fixture(tmp_path, "rhetorical_source_rule_raw.txt")
    parsed = result.experiment_dir / "parsed_storyline.json"
    payload = json.loads(parsed.read_text(encoding="utf-8"))
    slide = payload["sections"][0]["slides"][0]
    slide["slide_type"] = "explainer"
    slide["headline"] = "지식기관의 역할 변화"
    slide["body"] = ["학교와 박물관은 질문 설계와 출처 평가를 가르치는 역할로 이동할 수 있다."]
    slide["source_urls"] = [
        "https://www.unesco.org/en/articles/ai-competency-framework-students"
    ]
    slide["source_refs"] = [
        {
            "url": "https://www.unesco.org/en/articles/ai-competency-framework-students",
            "role": "institution_example",
            "use": "AI competency framework context",
            "confidence": "medium",
            "manual_check_required": True,
        }
    ]
    slide["needs_fact_check"] = False
    raw_path = tmp_path / "institution_role_source_ref_without_fact_check.txt"
    raw_path.write_text(json.dumps(payload, ensure_ascii=False), encoding="utf-8")
    result = validate_api_experiment_raw_output(
        raw_output_path=raw_path,
        input_bundle_path=INPUT_BUNDLE,
        evidence_pack_path=EVIDENCE_PACK,
        experiment_dir=tmp_path / "experiments" / "institution_role_source_ref_without_fact_check",
        report_path=tmp_path / "reports" / "institution_role_source_ref_without_fact_check.md",
    )

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


def test_unsupported_claim_detail_is_reported(tmp_path) -> None:
    result = _run_fixture(tmp_path, "rhetorical_factual_claim_raw.txt")
    report_text = result.report_path.read_text(encoding="utf-8")

    assert "unsupported_claim" in result.failure_modes
    assert "unsupported_claim_details" in report_text
    assert "body_excerpt" in report_text
    assert "empty_source_urls_without_needs_source" in report_text


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
    case = {
        "expected_key_beats": [
            {
                "id": "kb_finance",
                "label": "생산적 금융",
                "anchor_phrases": ["정책금융"],
            }
        ],
        "evaluation_notes": ["투자 조언처럼 쓰지 말 것"],
    }
    prompt = build_api_experiment_prompt(
        input_bundle=input_bundle,
        evidence_pack=evidence_pack,
        prompt_text="base prompt",
        schema={"title": "Schema"},
        allowed_urls={"https://example.com/a", "https://example.com/b"},
        case=case,
    )

    assert "base prompt" in prompt
    assert "https://example.com/a" in prompt
    assert "https://example.com/b" in prompt
    assert "Output Schema JSON" in prompt
    assert "kb_finance" in prompt
    assert "투자 조언처럼 쓰지 말 것" in prompt


def test_finance_policy_guardrail_violation_is_reported(tmp_path) -> None:
    payload = json.loads(
        (FIXTURE_DIR / "valid_ai_knowledge_storyline_raw.txt").read_text(
            encoding="utf-8"
        )
    )
    payload["sections"][0]["slides"][0]["headline"] = "추천 종목처럼 매수 의견을 제시"
    raw_path = tmp_path / "finance_raw.txt"
    raw_path.write_text(json.dumps(payload, ensure_ascii=False), encoding="utf-8")
    input_bundle_path = tmp_path / "finance_input_bundle.json"
    input_bundle_path.write_text(
        json.dumps(
            {
                "story_seed_title": "생산적 금융과 정책자금 전환",
                "risk_flags": ["investment_advice_risk", "policy_effect_uncertainty"],
                "do_not_claim": ["투자 조언처럼 쓰지 말 것"],
            },
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )
    evidence_pack_path = tmp_path / "finance_evidence_pack.json"
    evidence_pack_path.write_text(
        json.dumps(
            {
                "source": {"url": "https://www.bbc.com/news/articles/c2023l60370o"}
            },
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )

    result = validate_api_experiment_raw_output(
        raw_output_path=raw_path,
        input_bundle_path=input_bundle_path,
        evidence_pack_path=evidence_pack_path,
        experiment_dir=tmp_path / "experiments" / "finance",
        report_path=tmp_path / "reports" / "finance.md",
        case_id="anny_api_experiment_productive_finance_policy_v1",
    )

    manifest = json.loads(result.manifest_path.read_text(encoding="utf-8"))
    report = result.report_path.read_text(encoding="utf-8")
    assert "policy_finance_guardrail_violation" in result.failure_modes
    assert any(
        "investment_advice_violation" in item
        for item in manifest["policy_finance_guardrail_errors"]
    )
    assert "investment_advice_risk:매수" in manifest["do_not_claim_violations"]
    assert "policy_finance_guardrail_errors" in report


def test_finance_covers_key_beats_unknown_value_fails(tmp_path) -> None:
    def modifier(payload):
        slide = payload["sections"][0]["slides"][0]
        slide["covers_key_beats"] = ["policy_source"]
        slide["key_beat_anchors_used"] = [
            {"key_beat_id": "policy_source", "anchor_phrase": "정책금융"}
        ]

    result = _run_modified_finance_fixture(tmp_path, modifier)
    report = result.report_path.read_text(encoding="utf-8")

    assert "key_beat_drift" in result.failure_modes
    assert "invalid_covers_key_beat_value" in report


def test_finance_key_beat_id_with_anchor_phrase_can_pass_anchor_rule(tmp_path) -> None:
    def modifier(payload):
        payload["sections"] = payload["sections"][:1]
        payload["sections"][0]["slides"] = payload["sections"][0]["slides"][:1]
        slide = payload["sections"][0]["slides"][0]
        slide["headline"] = "담보 중심 금융의 한계"
        slide["body"] = ["담보와 단기수익 중심 금융의 한계를 묻는다."]
        slide["covers_key_beats"] = ["kb_finance_short_term_limit"]
        slide["key_beat_anchors_used"] = [
            {"key_beat_id": "kb_finance_short_term_limit", "anchor_phrase": "담보"}
        ]
        payload["key_beat_coverage"] = [
            {
                "key_beat_id": "kb_finance_short_term_limit",
                "covered": True,
                "slide_refs": [1],
                "coverage_note": "담보 anchor present.",
            }
        ]

    result = _run_modified_finance_fixture(tmp_path, modifier)
    report = result.report_path.read_text(encoding="utf-8")

    assert "invalid_covers_key_beat_value" not in report
    assert "key_beat_anchor_phrase_not_in_text" not in report


def test_finance_key_beat_id_without_anchor_phrase_fails(tmp_path) -> None:
    def modifier(payload):
        slide = payload["sections"][0]["slides"][0]
        slide["headline"] = "금융의 질문"
        slide["body"] = ["성장 자금 배분을 묻는다."]
        slide["covers_key_beats"] = ["kb_finance_short_term_limit"]
        slide["key_beat_anchors_used"] = [
            {"key_beat_id": "kb_finance_short_term_limit", "anchor_phrase": "담보"}
        ]

    result = _run_modified_finance_fixture(tmp_path, modifier)
    report = result.report_path.read_text(encoding="utf-8")

    assert "key_beat_drift" in result.failure_modes
    assert "key_beat_anchor_phrase_not_in_text" in report


def test_policy_effect_claim_without_source_fails(tmp_path) -> None:
    def modifier(payload):
        slide = payload["sections"][0]["slides"][0]
        slide["slide_type"] = "explainer"
        slide["headline"] = "정책금융은 성장 효과를 낼 수 있는가"
        slide["body"] = ["국민성장펀드 구조와 정책 효과를 설명한다."]
        slide["source_urls"] = []
        slide["needs_source"] = False
        slide["needs_fact_check"] = True
        slide["fact_check_kind"] = "policy_effect_claim"

    result = _run_modified_finance_fixture(tmp_path, modifier)
    manifest = json.loads(result.manifest_path.read_text(encoding="utf-8"))

    assert "unsupported_claim" in result.failure_modes
    assert any(
        item["triggered_marker_type"] == "policy_finance"
        for item in manifest["unsupported_claim_details"]
    )


def test_investment_risk_claim_without_fact_check_fails(tmp_path) -> None:
    def modifier(payload):
        slide = payload["sections"][0]["slides"][0]
        slide["headline"] = "금융권 부담과 손실분담"
        slide["body"] = ["금융권 부담과 손실분담 구조를 다룬다."]
        slide["source_urls"] = ["https://example.com/source"]
        slide["needs_source"] = False
        slide["needs_fact_check"] = False
        slide["required_before_broadcast"] = True
        slide["fact_check_kind"] = "investment_risk_claim"

    result = _run_modified_finance_fixture(tmp_path, modifier)

    assert "policy_finance_guardrail_violation" in result.failure_modes


def test_finance_production_checklist_is_internal_not_normal_claim(tmp_path) -> None:
    def modifier(payload):
        slide = payload["sections"][0]["slides"][0]
        slide["slide_type"] = "production_checklist"
        slide["headline"] = "정책·실무 확인 리스트"
        slide["body"] = ["국민성장펀드 운용지침과 공모문서 확인."]
        slide["source_urls"] = []
        slide["needs_source"] = False
        slide["needs_fact_check"] = True
        slide["fact_check_kind"] = "production_checklist"

    result = _run_modified_finance_fixture(tmp_path, modifier)

    assert "unsupported_claim" not in result.failure_modes


def test_finance_counterpoint_or_risk_discussion_missing_is_reported(tmp_path) -> None:
    def modifier(payload):
        for section in payload["sections"]:
            section["section_title"] = "정책금융 설명"
            for slide in section["slides"]:
                slide["slide_type"] = "explainer"
                slide["headline"] = "정책금융 설명"
                slide["body"] = ["국민성장펀드 구조를 설명한다."]
                slide["source_urls"] = ["https://example.com/source"]
                slide["needs_fact_check"] = True
                slide["notes"] = ""

    result = _run_modified_finance_fixture(tmp_path, modifier)
    manifest = json.loads(result.manifest_path.read_text(encoding="utf-8"))

    assert "policy_finance_guardrail_violation" in result.failure_modes
    assert "finance risk/counterpoint discussion missing" in manifest[
        "policy_finance_guardrail_errors"
    ]


def test_write_productive_finance_claim_hygiene_review(tmp_path) -> None:
    raw = (FIXTURE_DIR / "valid_ai_knowledge_storyline_raw.txt").read_text(
        encoding="utf-8"
    )
    storyline_path = tmp_path / "parsed_storyline.json"
    manifest_path = tmp_path / "manifest.json"
    storyline_path.write_text(raw, encoding="utf-8")
    manifest = {
        "failure_modes": ["unsupported_claim", "key_beat_drift"],
        "unsupported_claim_details": [
            {
                "slide_no": 1,
                "headline": "국민성장펀드 구조",
                "slide_type": "explainer",
                "fact_check_kind": "policy_effect_claim",
                "body_excerpt": "정책금융과 손실분담 구조",
                "reason": "empty_source_urls_without_needs_source",
                "source_urls_present": False,
                "needs_source": False,
                "needs_fact_check": False,
                "triggered_marker": "정책금융",
                "triggered_marker_type": "policy_finance",
                "recommended_fix": "set_needs_source_true_and_needs_fact_check_true",
            }
        ],
        "key_beat_coverage_errors": ["missing_covers_key_beats:정책금융"],
    }
    manifest_path.write_text(json.dumps(manifest), encoding="utf-8")
    report = tmp_path / "claim_hygiene.md"

    result = write_productive_finance_claim_hygiene_review(
        storyline_path=storyline_path,
        manifest_path=manifest_path,
        report_path=report,
    )

    assert result["reviewed"][0]["classification"] == "policy_effect_claim_without_source"
    text = report.read_text(encoding="utf-8")
    assert "Productive Finance v1 Claim Hygiene Review" in text
    assert "missing_covers_key_beats" in text
    assert "ready_for_production_agent: false" in text


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


def test_write_v6_claim_hygiene_review(tmp_path) -> None:
    raw = (FIXTURE_DIR / "valid_ai_knowledge_storyline_raw.txt").read_text(
        encoding="utf-8"
    )
    storyline_path = tmp_path / "parsed_storyline.json"
    manifest_path = tmp_path / "manifest.json"
    storyline_path.write_text(raw, encoding="utf-8")
    manifest = {
        "failure_modes": ["unsupported_claim"],
        "unsupported_claim_details": [
            {
                "slide_no": 1,
                "headline": "Royal Observatory warns about AI",
                "slide_type": "title",
                "fact_check_kind": None,
                "body_excerpt": "BBC warning frame",
                "reason": "empty_source_urls_without_needs_source",
                "source_urls_present": False,
                "needs_source": False,
                "needs_fact_check": False,
            }
        ],
    }
    manifest_path.write_text(json.dumps(manifest), encoding="utf-8")
    report = tmp_path / "claim_hygiene.md"

    result = write_v6_claim_hygiene_review(
        storyline_path=storyline_path,
        manifest_path=manifest_path,
        report_path=report,
    )

    assert result["reviewed"][0]["recommended_action"] == "require_source_url"
    text = report.read_text(encoding="utf-8")
    assert "source_specific_title_or_bridge" in text
    assert "ready_for_production_agent: false" in text


def test_write_api_v1_v2_v3_comparison_report(tmp_path) -> None:
    raw = (FIXTURE_DIR / "valid_ai_knowledge_storyline_raw.txt").read_text(
        encoding="utf-8"
    )
    manifest = {
        "model": "gpt-5-mini",
        "failure_modes": [],
        "schema_valid": True,
        "hygiene_passed": True,
        "hallucinated_urls": [],
        "do_not_claim_violations": [],
        "key_beat_coverage_errors": [],
    }
    run_dirs = []
    for name in ["v1", "v2", "v3"]:
        run_dir = tmp_path / name
        run_dir.mkdir()
        (run_dir / "parsed_storyline.json").write_text(raw, encoding="utf-8")
        (run_dir / "manifest.json").write_text(
            json.dumps(manifest),
            encoding="utf-8",
        )
        run_dirs.append(run_dir)
    report = tmp_path / "comparison.md"

    result = write_api_v1_v2_v3_comparison_report(
        v1_dir=run_dirs[0],
        v2_dir=run_dirs[1],
        v3_dir=run_dirs[2],
        comparison_report_path=report,
    )

    assert result["v3"]["manifest"]["model"] == "gpt-5-mini"
    text = report.read_text(encoding="utf-8")
    assert "v1/v2/v3 Comparison" in text
    assert "Key Beat Coverage" in text
    assert "ready_for_production_agent=false" in text


def test_write_api_v1_v2_v3_v4_comparison_report(tmp_path) -> None:
    raw = (FIXTURE_DIR / "valid_ai_knowledge_storyline_raw.txt").read_text(
        encoding="utf-8"
    )
    manifest = {
        "model": "gpt-5-mini",
        "failure_modes": [],
        "schema_valid": True,
        "hygiene_passed": True,
        "hallucinated_urls": [],
        "do_not_claim_violations": [],
        "unsupported_claim_details": [],
        "key_beat_coverage_errors": [],
    }
    run_dirs = []
    for name in ["v1", "v2", "v3", "v4"]:
        run_dir = tmp_path / name
        run_dir.mkdir()
        (run_dir / "parsed_storyline.json").write_text(raw, encoding="utf-8")
        (run_dir / "manifest.json").write_text(
            json.dumps(manifest),
            encoding="utf-8",
        )
        run_dirs.append(run_dir)
    report = tmp_path / "comparison.md"

    result = write_api_v1_v2_v3_v4_comparison_report(
        v1_dir=run_dirs[0],
        v2_dir=run_dirs[1],
        v3_dir=run_dirs[2],
        v4_dir=run_dirs[3],
        comparison_report_path=report,
    )

    assert result["v4"]["manifest"]["model"] == "gpt-5-mini"
    text = report.read_text(encoding="utf-8")
    assert "v1/v2/v3/v4 Comparison" in text
    assert "Covers Key Beats" in text
    assert "Unsupported Claim Detail" in text
    assert "ready_for_production_agent=false" in text


def test_write_api_v1_to_v5_comparison_report(tmp_path) -> None:
    raw = (FIXTURE_DIR / "valid_ai_knowledge_storyline_raw.txt").read_text(
        encoding="utf-8"
    )
    manifest = {
        "model": "gpt-5-mini",
        "failure_modes": [],
        "schema_valid": True,
        "hygiene_passed": True,
        "hallucinated_urls": [],
        "do_not_claim_violations": [],
        "unsupported_claim_details": [],
        "key_beat_coverage_errors": [],
    }
    run_dirs = []
    for name in ["v1", "v2", "v3", "v4", "v5"]:
        run_dir = tmp_path / name
        run_dir.mkdir()
        (run_dir / "parsed_storyline.json").write_text(raw, encoding="utf-8")
        (run_dir / "manifest.json").write_text(
            json.dumps(manifest),
            encoding="utf-8",
        )
        run_dirs.append(run_dir)
    report = tmp_path / "comparison.md"

    result = write_api_v1_to_v5_comparison_report(
        v1_dir=run_dirs[0],
        v2_dir=run_dirs[1],
        v3_dir=run_dirs[2],
        v4_dir=run_dirs[3],
        v5_dir=run_dirs[4],
        comparison_report_path=report,
    )

    assert result["v5"]["manifest"]["model"] == "gpt-5-mini"
    text = report.read_text(encoding="utf-8")
    assert "v1/v2/v3/v4/v5 Comparison" in text
    assert "stable covers_key_beats ids" in text
    assert "ready_for_production_agent=false" in text


def test_write_api_v1_to_v6_comparison_report(tmp_path) -> None:
    raw = (FIXTURE_DIR / "valid_ai_knowledge_storyline_raw.txt").read_text(
        encoding="utf-8"
    )
    manifest = {
        "model": "gpt-5-mini",
        "failure_modes": [],
        "schema_valid": True,
        "hygiene_passed": True,
        "hallucinated_urls": [],
        "do_not_claim_violations": [],
        "unsupported_claim_details": [],
        "key_beat_coverage_errors": [],
    }
    run_dirs = []
    for name in ["v1", "v2", "v3", "v4", "v5", "v6"]:
        run_dir = tmp_path / name
        run_dir.mkdir()
        (run_dir / "parsed_storyline.json").write_text(raw, encoding="utf-8")
        (run_dir / "manifest.json").write_text(
            json.dumps(manifest),
            encoding="utf-8",
        )
        run_dirs.append(run_dir)
    report = tmp_path / "comparison.md"

    result = write_api_v1_to_v6_comparison_report(
        v1_dir=run_dirs[0],
        v2_dir=run_dirs[1],
        v3_dir=run_dirs[2],
        v4_dir=run_dirs[3],
        v5_dir=run_dirs[4],
        v6_dir=run_dirs[5],
        comparison_report_path=report,
    )

    assert result["v6"]["manifest"]["model"] == "gpt-5-mini"
    text = report.read_text(encoding="utf-8")
    assert "v1 to v6 Comparison" in text
    assert "Key Beat Anchors Used" in text
    assert "key_beat_anchors_used" in text
    assert "ready_for_production_agent=false" in text


def test_write_api_v1_to_v7_comparison_report(tmp_path) -> None:
    raw = (FIXTURE_DIR / "valid_ai_knowledge_storyline_raw.txt").read_text(
        encoding="utf-8"
    )
    manifest = {
        "model": "gpt-5-mini",
        "failure_modes": [],
        "schema_valid": True,
        "hygiene_passed": True,
        "hallucinated_urls": [],
        "do_not_claim_violations": [],
        "unsupported_claim_details": [],
        "key_beat_coverage_errors": [],
    }
    run_dirs = []
    for name in ["v1", "v2", "v3", "v4", "v5", "v6", "v7"]:
        run_dir = tmp_path / name
        run_dir.mkdir()
        (run_dir / "parsed_storyline.json").write_text(raw, encoding="utf-8")
        (run_dir / "manifest.json").write_text(
            json.dumps(manifest),
            encoding="utf-8",
        )
        run_dirs.append(run_dir)
    report = tmp_path / "comparison.md"

    result = write_api_v1_to_v7_comparison_report(
        v1_dir=run_dirs[0],
        v2_dir=run_dirs[1],
        v3_dir=run_dirs[2],
        v4_dir=run_dirs[3],
        v5_dir=run_dirs[4],
        v6_dir=run_dirs[5],
        v7_dir=run_dirs[6],
        comparison_report_path=report,
    )

    assert result["v7"]["manifest"]["model"] == "gpt-5-mini"
    text = report.read_text(encoding="utf-8")
    assert "v1 to v7 Comparison" in text
    assert "claim hygiene/fact-check conservatism" in text
    assert "ready_for_production_agent=false" in text


def test_write_api_v1_to_v8_comparison_report(tmp_path) -> None:
    raw = (FIXTURE_DIR / "valid_ai_knowledge_storyline_raw.txt").read_text(
        encoding="utf-8"
    )
    manifest = {
        "model": "gpt-5-mini",
        "failure_modes": [],
        "schema_valid": True,
        "hygiene_passed": True,
        "hallucinated_urls": [],
        "do_not_claim_violations": [],
        "unsupported_claim_details": [
            {
                "slide_no": 1,
                "slide_type": "section_title",
                "headline": "지식기관의 역할 변화",
                "triggered_marker": "역할 변화",
                "recommended_fix": "set_needs_source_true",
            }
        ],
        "key_beat_coverage_errors": [],
    }
    run_dirs = []
    for name in ["v1", "v2", "v3", "v4", "v5", "v6", "v7", "v8"]:
        run_dir = tmp_path / name
        run_dir.mkdir()
        (run_dir / "parsed_storyline.json").write_text(raw, encoding="utf-8")
        (run_dir / "manifest.json").write_text(
            json.dumps(manifest),
            encoding="utf-8",
        )
        run_dirs.append(run_dir)
    report = tmp_path / "comparison.md"

    result = write_api_v1_to_v8_comparison_report(
        v1_dir=run_dirs[0],
        v2_dir=run_dirs[1],
        v3_dir=run_dirs[2],
        v4_dir=run_dirs[3],
        v5_dir=run_dirs[4],
        v6_dir=run_dirs[5],
        v7_dir=run_dirs[6],
        v8_dir=run_dirs[7],
        comparison_report_path=report,
    )

    assert result["v8"]["manifest"]["model"] == "gpt-5-mini"
    text = report.read_text(encoding="utf-8")
    assert "v1 to v8 Comparison" in text
    assert "section_title claim hygiene" in text
    assert "marker=역할 변화" in text
    assert "ready_for_production_agent=false" in text


def test_write_api_v1_to_v9_comparison_report(tmp_path) -> None:
    raw = (FIXTURE_DIR / "valid_ai_knowledge_storyline_raw.txt").read_text(
        encoding="utf-8"
    )
    manifest = {
        "model": "gpt-5-mini",
        "failure_modes": [],
        "schema_valid": True,
        "hygiene_passed": True,
        "hallucinated_urls": [],
        "do_not_claim_violations": [],
        "unsupported_claim_details": [
            {
                "slide_no": 1,
                "slide_type": "closing_question",
                "headline": "교육의 핵심 질문",
                "triggered_marker": "인지",
                "recommended_fix": "set_needs_source_true_and_needs_fact_check_true",
            }
        ],
        "key_beat_coverage_errors": [],
    }
    run_dirs = []
    for name in ["v1", "v2", "v3", "v4", "v5", "v6", "v7", "v8", "v9"]:
        run_dir = tmp_path / name
        run_dir.mkdir()
        (run_dir / "parsed_storyline.json").write_text(raw, encoding="utf-8")
        (run_dir / "manifest.json").write_text(
            json.dumps(manifest),
            encoding="utf-8",
        )
        run_dirs.append(run_dir)
    report = tmp_path / "comparison.md"

    result = write_api_v1_to_v9_comparison_report(
        v1_dir=run_dirs[0],
        v2_dir=run_dirs[1],
        v3_dir=run_dirs[2],
        v4_dir=run_dirs[3],
        v5_dir=run_dirs[4],
        v6_dir=run_dirs[5],
        v7_dir=run_dirs[6],
        v8_dir=run_dirs[7],
        v9_dir=run_dirs[8],
        comparison_report_path=report,
    )

    assert result["v9"]["manifest"]["model"] == "gpt-5-mini"
    text = report.read_text(encoding="utf-8")
    assert "v1 to v9 Comparison" in text
    assert "final claim hygiene" in text
    assert "set_needs_source_true_and_needs_fact_check_true" in text
    assert "ready_for_production_agent=false" in text
