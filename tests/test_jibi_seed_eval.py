import json
from collections import Counter

from luddite import paths
from luddite.eval import jibi_seed_eval


def test_jibi_seed_eval_fixture_loads() -> None:
    cases = jibi_seed_eval.load_cases()
    labels = Counter(case["expected_label"] for case in cases)

    assert len(cases) == 30
    assert labels["positive"] == 10
    assert labels["produced_but_rejected"] == 8
    assert labels["pending_or_unknown"] == 7
    assert labels["rejected_or_not_pursued"] == 5


def test_grade_band_calculation() -> None:
    assert jibi_seed_eval._grade_status("positive", "A") == "ok"
    assert jibi_seed_eval._grade_status("positive", "D") == "fail"
    assert jibi_seed_eval._grade_status("produced_but_rejected", "A") == "overrate"
    assert jibi_seed_eval._grade_status("produced_but_rejected", "D") == "underrate"
    assert jibi_seed_eval._grade_status("pending_or_unknown", "A") == "overconfident"
    assert jibi_seed_eval._grade_status("rejected_or_not_pursued", "B") == "fail"


def test_risk_flag_recall_calculation() -> None:
    assert jibi_seed_eval._risk_recall([], []) == 1.0
    assert (
        jibi_seed_eval._risk_recall(
            ["political_sensitivity", "live_news_volatility"],
            ["political_sensitivity"],
        )
        == 0.5
    )


def test_risk_probe_uses_action_and_risk_over_label() -> None:
    case = {
        "case_id": "risk",
        "title": "risk probe",
        "case_type": "risk_probe",
        "expected_label": "pending_or_unknown",
        "expected_action": "hold_due_to_live_news_volatility",
        "expected_risk_flags": ["political_sensitivity", "live_news_volatility"],
    }
    output = {
        "case_id": "risk",
        "label_guess": "rejected_or_not_pursued",
        "final_grade": "A",
        "recommended_action": "hold_due_to_live_news_volatility",
        "risk_flags": ["political_sensitivity", "live_news_volatility"],
    }

    result = jibi_seed_eval.evaluate_case(case, output)

    assert result["passed"]
    assert result["primary_status"] == "risk_probe_ok"


def test_jibi_seed_eval_writes_markdown_report(tmp_path) -> None:
    output_jsonl = tmp_path / "latest.jsonl"
    output_md = tmp_path / "latest.md"

    results = jibi_seed_eval.run_eval(
        output_jsonl=output_jsonl,
        output_md=output_md,
    )

    assert len(results) == 30
    assert output_jsonl.exists()
    assert output_md.exists()
    assert "jibi Seed Eval Report" in output_md.read_text(encoding="utf-8")

    written = [
        json.loads(line)
        for line in output_jsonl.read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]
    assert len(written) == 30
    assert output_jsonl.is_relative_to(tmp_path)
    assert (paths.OUTPUTS_DIR / "eval" / "jibi_seed_eval").is_absolute()
