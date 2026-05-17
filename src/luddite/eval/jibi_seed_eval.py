"""Evaluate jibi seed scoring outputs against golden seed cases.

This runner intentionally does not call an LLM. It can grade a supplied JSONL of
model outputs, or generate deterministic mock outputs that exercise the report
and rubric plumbing.
"""

from __future__ import annotations

import json
from collections import Counter
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Annotated, Any

import typer
from rich.console import Console

from luddite import paths
from luddite.utils.jsonl import write_jsonl

app = typer.Typer(no_args_is_help=False)
console = Console()

FIXTURE_PATH = paths.EVAL_DIR / "golden_cases" / "jibi_seed_eval_cases.jsonl"
OUTPUT_DIR = paths.OUTPUTS_DIR / "eval" / "jibi_seed_eval"
LATEST_JSONL = OUTPUT_DIR / "latest.jsonl"
LATEST_MD = OUTPUT_DIR / "latest.md"

IMPORTANT_RISK_FLAGS = {
    "political_sensitivity",
    "corporate_promo_risk",
    "investment_advice_risk",
    "crime_or_drug_sensitivity",
    "medical_claim_risk",
    "copyright_image_risk",
    "live_news_volatility",
    "single_source_dependency",
}

GRADE_BANDS = {
    "positive": {"ok": {"A", "B"}, "fail": {"C", "D"}},
    "produced_but_rejected": {
        "ok": {"B", "C"},
        "overrate": {"A"},
        "underrate": {"D"},
    },
    "pending_or_unknown": {
        "ok": {"B", "C"},
        "overconfident": {"A"},
        "underrate": {"D"},
    },
    "rejected_or_not_pursued": {"ok": {"C", "D"}, "fail": {"A", "B"}},
}

# TODO: Consider adding `editorial_review` as a recommended_action once a human
# review queue exists.
# TODO: Pending/unknown cases currently treat A as overconfident. Future evals
# may split out an `acceptable_overconfident` status for exceptionally strong
# pending cases with unusually deep evidence.


@dataclass
class EvalSummary:
    total: int
    passed: int
    failed: int
    risk_recall: float
    important_misses: int


def read_jsonl(path: Path) -> list[dict[str, Any]]:
    if not path.exists():
        return []
    rows: list[dict[str, Any]] = []
    for line in path.read_text(encoding="utf-8").splitlines():
        if line.strip():
            rows.append(json.loads(line))
    return rows


def load_cases(path: Path = FIXTURE_PATH) -> list[dict[str, Any]]:
    cases = read_jsonl(path)
    for index, case in enumerate(cases, start=1):
        case.setdefault("case_id", f"seed_case_{index:03d}")
        case.setdefault("case_type", "label_eval")
        case.setdefault("expected_action", "")
    return cases


def _mock_grade(case: dict[str, Any]) -> str:
    if case["case_type"] == "risk_probe":
        return "C"
    return {
        "positive": "B",
        "produced_but_rejected": "C",
        "pending_or_unknown": "B",
        "rejected_or_not_pursued": "D",
    }.get(case["expected_label"], "C")


def _mock_action(case: dict[str, Any], grade: str) -> str:
    if case.get("expected_action"):
        return case["expected_action"]
    return {
        "A": "send_to_anny",
        "B": "gather_more_evidence",
        "C": "keep_for_later",
        "D": "reject",
    }[grade]


def mock_outputs(cases: list[dict[str, Any]]) -> list[dict[str, Any]]:
    outputs: list[dict[str, Any]] = []
    for case in cases:
        grade = _mock_grade(case)
        outputs.append(
            {
                "case_id": case["case_id"],
                "title": case["title"],
                "label_guess": case["expected_label"],
                "final_grade": grade,
                "broadcast_potential": "high" if grade in {"A", "B"} else "medium",
                "risk_level": "high" if case.get("expected_risk_flags") else "low",
                "recommended_action": _mock_action(case, grade),
                "risk_flags": case.get("expected_risk_flags", []),
                "rationale": "Deterministic mock output for eval harness plumbing.",
            }
        )
    return outputs


def _grade_status(expected_label: str, final_grade: str) -> str:
    band = GRADE_BANDS.get(expected_label, {})
    for status, grades in band.items():
        if final_grade in grades:
            return status
    return "fail"


def _risk_recall(expected: list[str], actual: list[str]) -> float:
    if not expected:
        return 1.0
    return len(set(expected) & set(actual)) / len(set(expected))


def evaluate_case(case: dict[str, Any], output: dict[str, Any]) -> dict[str, Any]:
    expected_risks = case.get("expected_risk_flags", [])
    actual_risks = output.get("risk_flags", [])
    missing_risks = sorted(set(expected_risks) - set(actual_risks))
    important_missing = sorted(set(missing_risks) & IMPORTANT_RISK_FLAGS)
    risk_recall = _risk_recall(expected_risks, actual_risks)
    grade_status = _grade_status(case["expected_label"], output.get("final_grade", ""))
    action_match = (
        not case.get("expected_action")
        or output.get("recommended_action") == case.get("expected_action")
    )

    if case.get("case_type") == "risk_probe":
        passed = risk_recall >= 0.8 and not important_missing and action_match
        primary_status = "risk_probe_ok" if passed else "risk_probe_fail"
    else:
        passed = grade_status == "ok" and not important_missing
        primary_status = grade_status

    return {
        "case_id": case["case_id"],
        "title": case["title"],
        "case_type": case.get("case_type", "label_eval"),
        "expected_label": case["expected_label"],
        "model_label": output.get("label_guess"),
        "final_grade": output.get("final_grade"),
        "grade_status": grade_status,
        "primary_status": primary_status,
        "expected_action": case.get("expected_action"),
        "recommended_action": output.get("recommended_action"),
        "action_match": action_match,
        "expected_risk_flags": expected_risks,
        "model_risk_flags": actual_risks,
        "risk_recall": risk_recall,
        "missing_risk_flags": missing_risks,
        "important_missing_risk_flags": important_missing,
        "passed": passed,
    }


def _outputs_by_case_id(
    cases: list[dict[str, Any]],
    outputs: list[dict[str, Any]],
) -> dict[str, dict[str, Any]]:
    by_id = {output.get("case_id"): output for output in outputs}
    if all(case["case_id"] in by_id for case in cases):
        return by_id
    return {
        case["case_id"]: outputs[index]
        for index, case in enumerate(cases)
        if index < len(outputs)
    }


def evaluate_outputs(
    cases: list[dict[str, Any]],
    outputs: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    by_id = _outputs_by_case_id(cases, outputs)
    results: list[dict[str, Any]] = []
    for case in cases:
        output = by_id.get(case["case_id"])
        if output is None:
            results.append(
                {
                    "case_id": case["case_id"],
                    "title": case["title"],
                    "case_type": case.get("case_type", "label_eval"),
                    "expected_label": case["expected_label"],
                    "primary_status": "missing_output",
                    "risk_recall": 0,
                    "important_missing_risk_flags": case.get("expected_risk_flags", []),
                    "passed": False,
                }
            )
        else:
            results.append(evaluate_case(case, output))
    return results


def summarize(results: list[dict[str, Any]]) -> EvalSummary:
    total = len(results)
    passed = sum(1 for result in results if result.get("passed"))
    recalls = [float(result.get("risk_recall", 0)) for result in results]
    important_misses = sum(
        len(result.get("important_missing_risk_flags", [])) for result in results
    )
    return EvalSummary(
        total=total,
        passed=passed,
        failed=total - passed,
        risk_recall=sum(recalls) / len(recalls) if recalls else 0,
        important_misses=important_misses,
    )


def write_markdown_report(
    path: Path,
    results: list[dict[str, Any]],
    summary: EvalSummary,
    prompt_path: Path,
    model_output_path: Path | None,
) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    statuses = Counter(result.get("primary_status", "unknown") for result in results)
    labels = Counter(result.get("expected_label", "unknown") for result in results)
    case_types = Counter(result.get("case_type", "unknown") for result in results)

    lines = [
        "# jibi Seed Eval Report",
        "",
        f"- Generated at: {datetime.now(UTC).isoformat()}",
        f"- Fixture: `{FIXTURE_PATH}`",
        f"- Prompt: `{prompt_path}`",
        f"- Model output: `{model_output_path or 'deterministic mock output'}`",
        f"- Total cases: {summary.total}",
        f"- Passed: {summary.passed}",
        f"- Failed: {summary.failed}",
        f"- Average risk recall: {summary.risk_recall:.2f}",
        f"- Important risk misses: {summary.important_misses}",
        "",
        "## Label Mix",
        "",
    ]
    for label, count in labels.most_common():
        lines.append(f"- {label}: {count}")

    lines.extend(["", "## Case Types", ""])
    for case_type, count in case_types.most_common():
        lines.append(f"- {case_type}: {count}")

    lines.extend(["", "## Status Counts", ""])
    for status, count in statuses.most_common():
        lines.append(f"- {status}: {count}")

    lines.extend(
        [
            "",
            "## Case Results",
            "",
            "| Case | Type | Expected | Grade | Status | Risk Recall | Missing Important Risks |",
            "|---|---|---|---|---|---:|---|",
        ]
    )
    for result in results:
        missing = ", ".join(result.get("important_missing_risk_flags", [])) or "-"
        title = str(result.get("title", "")).replace("|", "\\|")
        row_template = (
            "| {title} | {case_type} | {expected} | {grade} | {status} | "
            "{recall:.2f} | {missing} |"
        )
        lines.append(
            row_template.format(
                title=title,
                case_type=result.get("case_type", ""),
                expected=result.get("expected_label", ""),
                grade=result.get("final_grade", "-"),
                status=result.get("primary_status", ""),
                recall=float(result.get("risk_recall", 0)),
                missing=missing,
            )
        )
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def run_eval(
    cases_path: Path = FIXTURE_PATH,
    prompt_path: Path = paths.PROMPTS_DIR / "jibi" / "seed_scorer.md",
    model_output_path: Path | None = None,
    output_jsonl: Path = LATEST_JSONL,
    output_md: Path = LATEST_MD,
) -> list[dict[str, Any]]:
    cases = load_cases(cases_path)
    outputs = read_jsonl(model_output_path) if model_output_path else mock_outputs(cases)
    results = evaluate_outputs(cases, outputs)
    summary = summarize(results)

    output_jsonl.parent.mkdir(parents=True, exist_ok=True)
    write_jsonl(output_jsonl, results)
    write_markdown_report(output_md, results, summary, prompt_path, model_output_path)
    return results


@app.callback(invoke_without_command=True)
def main(
    cases: Annotated[
        Path,
        typer.Option("--cases", help="jibi seed eval JSONL fixture."),
    ] = FIXTURE_PATH,
    prompt: Annotated[
        Path,
        typer.Option("--prompt", help="jibi seed scorer prompt path."),
    ] = paths.PROMPTS_DIR / "jibi" / "seed_scorer.md",
    model_output: Annotated[
        Path | None,
        typer.Option("--model-output", help="Optional model output JSONL to grade."),
    ] = None,
    output_jsonl: Annotated[
        Path,
        typer.Option("--output-jsonl", help="Evaluation JSONL output path."),
    ] = LATEST_JSONL,
    output_md: Annotated[
        Path,
        typer.Option("--output-md", help="Markdown report output path."),
    ] = LATEST_MD,
) -> None:
    """Run the jibi seed scoring eval without calling an LLM."""
    results = run_eval(cases, prompt, model_output, output_jsonl, output_md)
    summary = summarize(results)
    console.print(
        f"[green]Wrote jibi seed eval report to {output_md} "
        f"({summary.passed}/{summary.total} passed).[/green]"
    )
    raise typer.Exit(0 if summary.failed == 0 else 1)


if __name__ == "__main__":
    app()
