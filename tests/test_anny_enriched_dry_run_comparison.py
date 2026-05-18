from luddite.agents.anny.compare_enriched_dry_runs import compare_enriched_dry_runs
from luddite.utils.jsonl import write_jsonl


def _eval_record(case_id: str, *, source_count: int, needs_source: int) -> dict:
    return {
        "case_id": case_id,
        "section_count": 4,
        "slide_count": 24,
        "baseline_source_url_count": 3,
        "source_url_count": source_count,
        "baseline_needs_source_count": 14,
        "needs_source_count": needs_source,
        "needs_fact_check_count": 17,
        "key_beat_recall": 1.0,
        "source_image_overlap_count": 0,
        "hygiene_contract_passed": True,
        "policy_finance_guardrails_passed": True,
        "counterpoint_included": True,
        "korea_bridge_included": True,
        "do_not_claim_violations": [],
        "passed": True,
    }


def _hygiene_rows() -> list[dict]:
    return [
        {
            "slide_no": 1,
            "fact_check_kind": "policy_effect_claim",
            "fact_check_priority": "high",
            "required_before_storyline": False,
            "required_before_broadcast": True,
            "source_refs": [{"url": "https://example.com", "role": "primary_article"}],
        },
        {
            "slide_no": 2,
            "fact_check_kind": "production_checklist",
            "fact_check_priority": "high",
            "required_before_storyline": True,
            "required_before_broadcast": True,
            "source_refs": [],
        },
    ]


def test_compare_enriched_dry_runs_writes_readiness_gate(tmp_path, monkeypatch) -> None:
    ai_eval = tmp_path / "ai_eval.jsonl"
    finance_eval = tmp_path / "finance_eval.jsonl"
    ai_hygiene = tmp_path / "ai_hygiene.jsonl"
    finance_hygiene = tmp_path / "finance_hygiene.jsonl"
    write_jsonl(ai_eval, [_eval_record("ai", source_count=38, needs_source=0)])
    write_jsonl(finance_eval, [_eval_record("finance", source_count=48, needs_source=1)])
    write_jsonl(ai_hygiene, _hygiene_rows())
    write_jsonl(finance_hygiene, _hygiene_rows())

    import luddite.agents.anny.compare_enriched_dry_runs as module

    monkeypatch.setattr(
        module,
        "ENRICHED_DRY_RUN_CASES",
        [
            module.EnrichedDryRunCase("AI", "education", "education risk", ai_eval, ai_hygiene),
            module.EnrichedDryRunCase(
                "Finance", "policy", "finance risk", finance_eval, finance_hygiene
            ),
        ],
    )
    report_path = tmp_path / "comparison.md"

    result = compare_enriched_dry_runs(report_path=report_path)

    assert result["case_count"] == 2
    assert result["all_passed"] is True
    text = report_path.read_text(encoding="utf-8")
    assert "Anny Enriched Dry Run Comparison" in text
    assert "ready_for_api_experiment: false" in text
    assert "ready_for_production_agent: false" in text
    assert "Failure Modes To Watch" in text
