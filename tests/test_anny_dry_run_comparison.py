import json

from luddite.agents.anny.compare_dry_runs import compare_dry_runs
from luddite.utils.jsonl import write_jsonl


def _eval_record(case_id: str, *, needs_source: int, needs_fact_check: int) -> dict:
    return {
        "case_id": case_id,
        "section_count": 4,
        "slide_count": 24,
        "needs_source_count": needs_source,
        "needs_fact_check_count": needs_fact_check,
        "source_url_count": 3,
        "counterpoint_included": True,
        "korea_bridge_included": False,
        "do_not_claim_violations": [],
        "passed": True,
    }


def _hygiene_rows() -> list[dict]:
    return [
        {
            "slide_no": 1,
            "fact_check_kind": "policy_effect_claim",
            "fact_check_priority": "high",
            "required_before_broadcast": True,
        },
        {
            "slide_no": 2,
            "fact_check_kind": "production_checklist",
            "fact_check_priority": "high",
            "required_before_broadcast": True,
        },
    ]


def test_compare_dry_runs_writes_reports(tmp_path, monkeypatch) -> None:
    ai_eval = tmp_path / "ai_eval.jsonl"
    finance_eval = tmp_path / "finance_eval.jsonl"
    ai_hygiene = tmp_path / "ai_hygiene.jsonl"
    finance_hygiene = tmp_path / "finance_hygiene.jsonl"
    write_jsonl(ai_eval, [_eval_record("ai", needs_source=0, needs_fact_check=16)])
    write_jsonl(finance_eval, [_eval_record("finance", needs_source=14, needs_fact_check=17)])
    write_jsonl(ai_hygiene, _hygiene_rows())
    write_jsonl(finance_hygiene, _hygiene_rows())

    import luddite.agents.anny.compare_dry_runs as module

    patched_cases = [
        module.DryRunCase("AI", "education", "education risk", ai_eval, ai_hygiene),
        module.DryRunCase("Finance", "policy", "finance risk", finance_eval, finance_hygiene),
    ]
    monkeypatch.setattr(module, "DRY_RUN_CASES", patched_cases)
    comparison = tmp_path / "comparison.md"
    finance = tmp_path / "finance.md"
    finance_pack = tmp_path / "finance_pack.json"

    result = compare_dry_runs(
        comparison_report_path=comparison,
        finance_evidence_report_path=finance,
        finance_evidence_pack_path=finance_pack,
    )

    assert result["case_count"] == 2
    assert result["finance_evidence_pack_path"] == str(finance_pack)
    comparison_text = comparison.read_text(encoding="utf-8")
    assert "Anny Dry Run Comparison" in comparison_text
    assert "ready_for_prompt_design: true" in comparison_text
    finance_text = finance.read_text(encoding="utf-8")
    assert "국민성장펀드" in finance_text
    assert "full article bodies are not stored" in finance_text
    pack = json.loads(finance_pack.read_text(encoding="utf-8"))
    assert pack["full_article_text_stored"] is False
    assert "primary_official_source" in pack["categories"]
    assert pack["ready_for_evidence_fill"] is True
