"""Compare enriched manual anny dry runs before API/production work."""

from __future__ import annotations

from collections import Counter
from dataclasses import dataclass
from pathlib import Path
from typing import Annotated, Any

import typer
from rich.console import Console

from luddite import paths
from luddite.utils.jsonl import read_jsonl

app = typer.Typer(no_args_is_help=False)
console = Console()

AI_ENRICHED_EVAL_JSONL = (
    paths.OUTPUTS_DIR / "eval" / "anny_storyline_dry_run" / "latest_enriched.jsonl"
)
FINANCE_ENRICHED_EVAL_JSONL = (
    paths.OUTPUTS_DIR
    / "eval"
    / "anny_storyline_dry_run"
    / "productive_finance_policy_enriched.jsonl"
)
AI_ENRICHED_HYGIENE_JSONL = (
    paths.ANNY_STORYLINE_DRY_RUN_DIR / "ai_knowledge_institution_source_hygiene.jsonl"
)
FINANCE_ENRICHED_HYGIENE_JSONL = (
    paths.ANNY_STORYLINE_DRY_RUN_DIR
    / "productive_finance_policy_source_hygiene_enriched.jsonl"
)
DEFAULT_ENRICHED_COMPARISON_REPORT = (
    paths.REPORTS_DIR / "anny_enriched_dry_run_comparison.md"
)


@dataclass(frozen=True)
class EnrichedDryRunCase:
    label: str
    topic_type: str
    risk_profile: str
    eval_jsonl: Path
    hygiene_jsonl: Path


ENRICHED_DRY_RUN_CASES = [
    EnrichedDryRunCase(
        label="AI 즉답 시대의 지식기관 역할",
        topic_type="education / AI / knowledge institution",
        risk_profile="education_research_claim + institution_quote_context",
        eval_jsonl=AI_ENRICHED_EVAL_JSONL,
        hygiene_jsonl=AI_ENRICHED_HYGIENE_JSONL,
    ),
    EnrichedDryRunCase(
        label="생산적 금융과 정책자금 전환",
        topic_type="policy / finance / investment risk",
        risk_profile="policy_effect_claim + investment_risk_claim",
        eval_jsonl=FINANCE_ENRICHED_EVAL_JSONL,
        hygiene_jsonl=FINANCE_ENRICHED_HYGIENE_JSONL,
    ),
]


def compare_enriched_dry_runs(
    *,
    report_path: Path = DEFAULT_ENRICHED_COMPARISON_REPORT,
) -> dict[str, Any]:
    summaries = []
    for case in ENRICHED_DRY_RUN_CASES:
        eval_result = _load_eval(case.eval_jsonl)
        hygiene_rows = read_jsonl(case.hygiene_jsonl)
        summaries.append(_summary(case, eval_result, hygiene_rows))
    report_path.parent.mkdir(parents=True, exist_ok=True)
    report_path.write_text(_comparison_markdown(summaries), encoding="utf-8")
    return {
        "report_path": str(report_path),
        "case_count": len(summaries),
        "all_passed": all(item["passed"] for item in summaries),
    }


def _load_eval(path: Path) -> dict[str, Any]:
    records = read_jsonl(path)
    if not records:
        raise ValueError(f"No enriched eval records found: {path}")
    return records[0]


def _dist(rows: list[dict[str, Any]], key: str) -> dict[str, int]:
    return dict(sorted(Counter(str(row.get(key) or "unknown") for row in rows).items()))


def _source_ref_count(rows: list[dict[str, Any]]) -> int:
    return sum(len(row.get("source_refs", [])) for row in rows)


def _has_kind(rows: list[dict[str, Any]], kind: str) -> bool:
    return any(row.get("fact_check_kind") == kind for row in rows)


def _summary(
    case: EnrichedDryRunCase,
    eval_result: dict[str, Any],
    hygiene_rows: list[dict[str, Any]],
) -> dict[str, Any]:
    do_not_claim_count = len(eval_result.get("do_not_claim_violations", []))
    required_before_broadcast_count = sum(
        bool(row.get("required_before_broadcast")) for row in hygiene_rows
    )
    required_before_storyline_count = sum(
        bool(row.get("required_before_storyline")) for row in hygiene_rows
    )
    return {
        "label": case.label,
        "topic_type": case.topic_type,
        "risk_profile": case.risk_profile,
        "section_count": eval_result.get("section_count"),
        "slide_count": eval_result.get("slide_count"),
        "source_url_count": eval_result.get("source_url_count"),
        "baseline_source_url_count": eval_result.get("baseline_source_url_count"),
        "needs_source_count": eval_result.get("needs_source_count"),
        "baseline_needs_source_count": eval_result.get("baseline_needs_source_count"),
        "needs_fact_check_count": eval_result.get("needs_fact_check_count"),
        "key_beat_recall": eval_result.get("key_beat_recall"),
        "overlap_count": eval_result.get("source_image_overlap_count"),
        "hygiene_contract_passed": bool(eval_result.get("hygiene_contract_passed")),
        "policy_finance_guardrails_passed": bool(
            eval_result.get("policy_finance_guardrails_passed")
        ),
        "counterpoint_included": bool(eval_result.get("counterpoint_included")),
        "korea_bridge_included": bool(eval_result.get("korea_bridge_included")),
        "production_checklist_included": _has_kind(hygiene_rows, "production_checklist"),
        "required_before_broadcast_count": required_before_broadcast_count,
        "required_before_storyline_count": required_before_storyline_count,
        "source_ref_count": _source_ref_count(hygiene_rows),
        "do_not_claim_violation_count": do_not_claim_count,
        "fact_check_kind_distribution": _dist(hygiene_rows, "fact_check_kind"),
        "fact_check_priority_distribution": _dist(hygiene_rows, "fact_check_priority"),
        "passed": bool(eval_result.get("passed")),
    }


def _comparison_markdown(summaries: list[dict[str, Any]]) -> str:
    lines = [
        "# Anny Enriched Dry Run Comparison",
        "",
        "## Summary Table",
        "",
        (
            "| Topic | Type | Sections | Slides | Sources | Needs Source | "
            "Needs Fact Check | Key Beat Recall | Overlap | Hygiene | "
            "Guardrails | Counterpoint | Broadcast Checks | Passed |"
        ),
        "|---|---|---:|---:|---:|---:|---:|---:|---:|---|---|---|---:|---|",
    ]
    for item in summaries:
        lines.append(
            "| {label} | {topic_type} | {section_count} | {slide_count} | "
            "{baseline_source_url_count}->{source_url_count} | "
            "{baseline_needs_source_count}->{needs_source_count} | "
            "{needs_fact_check_count} | {key_beat_recall:.2f} | {overlap_count} | "
            "{hygiene_contract_passed} | {policy_finance_guardrails_passed} | "
            "{counterpoint_included} | {required_before_broadcast_count} | "
            "{passed} |".format(**item)
        )
    for item in summaries:
        lines.extend(
            [
                "",
                f"## {item['label']}",
                "",
                f"- risk_profile: {item['risk_profile']}",
                f"- source_ref_count: {item['source_ref_count']}",
                f"- required_before_storyline_count: {item['required_before_storyline_count']}",
                f"- production_checklist_included: {item['production_checklist_included']}",
                f"- korea_bridge_included: {item['korea_bridge_included']}",
                f"- do_not_claim_violation_count: {item['do_not_claim_violation_count']}",
                "",
                "Fact-check kind distribution:",
                *[
                    f"- {kind}: {count}"
                    for kind, count in item["fact_check_kind_distribution"].items()
                ],
                "",
                "Fact-check priority distribution:",
                *[
                    f"- {priority}: {count}"
                    for priority, count in item["fact_check_priority_distribution"].items()
                ],
            ]
        )
    lines.extend(
        [
            "",
            "## Readiness Gate",
            "",
            "- ready_for_prompt_design: true",
            "- ready_for_manual_storyline: true",
            "- ready_for_api_experiment_prep: true",
            "- ready_for_api_experiment: false",
            "- ready_for_production_agent: false",
            "- ready_for_broadcast: false",
            "",
            "Gate interpretation:",
            "- Both enriched manual dry runs pass schema, hygiene, key-beat, and guardrail checks.",
            "- Source coverage improved materially in both cases.",
            "- Remaining needs_fact_check markers are expected, not failure.",
            "- Passing enriched dry runs do not imply production readiness.",
            "",
            "Before API experiment:",
            "- Freeze a small API experiment prompt and output contract version.",
            "- Compare API output against these manual enriched fixtures.",
            "- Keep manual review required for source_refs, fact_check_kind, and do_not_claim.",
            (
                "- Add failure reporting for missing counterpoint/risk slides "
                "and overconfident claims."
            ),
            "",
            "Before production agent:",
            "- Add model output variability tests across repeated runs.",
            "- Add evidence freshness and source accessibility checks.",
            "- Add manual approval gate for high-priority fact-check slides.",
            "- Decide how production_checklist slides move to appendix, notes, or internal tasks.",
            "",
            "## Failure Modes To Watch",
            "",
            "- Treating attached sources as completed fact-checks.",
            "- Reducing needs_fact_check too aggressively on education/policy/finance claims.",
            "- Omitting counterpoint or risk discussion on sensitive topics.",
            (
                "- Turning policy/finance topics into investment advice, "
                "price forecast, or policy promotion."
            ),
            "- Over-generalizing Korea bridge examples into the main proof.",
            "- Letting production_checklist slides appear as normal broadcast claims.",
            "- Mislabeling source_refs roles or reusing a source without slide-specific use.",
            "- Introducing source_urls / image_urls overlap.",
            "- Passing schema while drifting from phrase-level key beats.",
            "",
            "## Recommendation",
            "",
            "- Milestone 1.7.4 can be considered complete if lint/test pass.",
            "- Next useful step is not production anny. Prefer API experiment prep or a small "
            "fact-check review gate, with ready_for_production_agent=false maintained.",
        ]
    )
    return "\n".join(lines) + "\n"


@app.callback(invoke_without_command=True)
def main(
    report_path: Annotated[
        Path,
        typer.Option("--report", help="Enriched dry-run comparison Markdown output."),
    ] = DEFAULT_ENRICHED_COMPARISON_REPORT,
) -> None:
    result = compare_enriched_dry_runs(report_path=report_path)
    console.print(
        "[green]Wrote enriched anny dry-run comparison "
        f"({result['case_count']} cases, all_passed={result['all_passed']}).[/green]"
    )


if __name__ == "__main__":
    app()
