"""Compare manual anny dry runs and summarize remaining evidence gaps."""

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
from luddite.utils.jsonl import read_jsonl

app = typer.Typer(no_args_is_help=False)
console = Console()

AI_EVAL_JSONL = paths.OUTPUTS_DIR / "eval" / "anny_storyline_dry_run" / "latest_enriched.jsonl"
FINANCE_EVAL_JSONL = (
    paths.OUTPUTS_DIR / "eval" / "anny_storyline_dry_run" / "productive_finance_policy.jsonl"
)
AI_HYGIENE_JSONL = (
    paths.ANNY_STORYLINE_DRY_RUN_DIR / "ai_knowledge_institution_source_hygiene.jsonl"
)
FINANCE_HYGIENE_JSONL = (
    paths.ANNY_STORYLINE_DRY_RUN_DIR / "productive_finance_policy_source_hygiene.jsonl"
)
DEFAULT_COMPARISON_REPORT = paths.REPORTS_DIR / "anny_dry_run_comparison.md"
DEFAULT_FINANCE_EVIDENCE_REPORT = (
    paths.REPORTS_DIR / "anny_evidence_enrichment_plan_productive_finance_policy.md"
)
DEFAULT_FINANCE_EVIDENCE_PACK = (
    paths.CANDIDATES_DIR / "anny_evidence_pack_productive_finance_policy.json"
)


@dataclass(frozen=True)
class DryRunCase:
    label: str
    topic_type: str
    risk_profile: str
    eval_jsonl: Path
    hygiene_jsonl: Path


DRY_RUN_CASES = [
    DryRunCase(
        label="AI 즉답 시대의 지식기관 역할",
        topic_type="education/AI/knowledge institution",
        risk_profile="education_research_claim + institution_quote_context",
        eval_jsonl=AI_EVAL_JSONL,
        hygiene_jsonl=AI_HYGIENE_JSONL,
    ),
    DryRunCase(
        label="생산적 금융과 정책자금 전환",
        topic_type="policy/finance/investment-risk",
        risk_profile="policy_effect_claim + investment_risk_claim",
        eval_jsonl=FINANCE_EVAL_JSONL,
        hygiene_jsonl=FINANCE_HYGIENE_JSONL,
    ),
]


def _load_eval(path: Path) -> dict[str, Any]:
    records = read_jsonl(path)
    if not records:
        raise ValueError(f"No eval records found: {path}")
    return records[0]


def _dist(rows: list[dict[str, Any]], key: str) -> dict[str, int]:
    return dict(sorted(Counter(str(row.get(key) or "unknown") for row in rows).items()))


def _has_kind(rows: list[dict[str, Any]], kind: str) -> bool:
    return any(row.get("fact_check_kind") == kind for row in rows)


def compare_dry_runs(
    *,
    comparison_report_path: Path = DEFAULT_COMPARISON_REPORT,
    finance_evidence_report_path: Path = DEFAULT_FINANCE_EVIDENCE_REPORT,
    finance_evidence_pack_path: Path = DEFAULT_FINANCE_EVIDENCE_PACK,
) -> dict[str, Any]:
    summaries = []
    for case in DRY_RUN_CASES:
        eval_result = _load_eval(case.eval_jsonl)
        hygiene_rows = read_jsonl(case.hygiene_jsonl)
        summaries.append(_case_summary(case, eval_result, hygiene_rows))
    comparison_report_path.parent.mkdir(parents=True, exist_ok=True)
    comparison_report_path.write_text(_comparison_markdown(summaries), encoding="utf-8")
    finance_evidence_report_path.parent.mkdir(parents=True, exist_ok=True)
    finance_evidence_pack = _finance_evidence_pack()
    finance_evidence_pack_path.parent.mkdir(parents=True, exist_ok=True)
    finance_evidence_pack_path.write_text(
        json.dumps(finance_evidence_pack, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    finance_evidence_report_path.write_text(
        _finance_plan_markdown(finance_evidence_pack_path),
        encoding="utf-8",
    )
    return {
        "comparison_report_path": str(comparison_report_path),
        "finance_evidence_report_path": str(finance_evidence_report_path),
        "finance_evidence_pack_path": str(finance_evidence_pack_path),
        "case_count": len(summaries),
    }


def _case_summary(
    case: DryRunCase, eval_result: dict[str, Any], hygiene_rows: list[dict[str, Any]]
) -> dict[str, Any]:
    return {
        "label": case.label,
        "topic_type": case.topic_type,
        "risk_profile": case.risk_profile,
        "section_count": eval_result.get("section_count"),
        "slide_count": eval_result.get("slide_count"),
        "needs_source_count": eval_result.get("needs_source_count"),
        "needs_fact_check_count": eval_result.get("needs_fact_check_count"),
        "source_url_count": eval_result.get("source_url_count"),
        "fact_check_kind_distribution": _dist(hygiene_rows, "fact_check_kind"),
        "fact_check_priority_distribution": _dist(hygiene_rows, "fact_check_priority"),
        "required_before_broadcast_count": sum(
            bool(row.get("required_before_broadcast")) for row in hygiene_rows
        ),
        "counterpoint_included": bool(eval_result.get("counterpoint_included")),
        "korea_bridge_included": bool(eval_result.get("korea_bridge_included")),
        "production_checklist_included": _has_kind(hygiene_rows, "production_checklist"),
        "do_not_claim_violation_count": len(eval_result.get("do_not_claim_violations", [])),
        "passed": bool(eval_result.get("passed")),
    }


def _comparison_markdown(summaries: list[dict[str, Any]]) -> str:
    lines = [
        "# Anny Dry Run Comparison",
        "",
        "## Summary Table",
        "",
        (
            "| Topic | Type | Risk Profile | Sections | Slides | Needs Source | "
            "Needs Fact Check | Source URLs | Broadcast Checks | Counterpoint | "
            "Korea Bridge | Production Checklist | Do-not-claim Violations | Passed |"
        ),
        "|---|---|---|---:|---:|---:|---:|---:|---:|---|---|---|---:|---|",
    ]
    for item in summaries:
        lines.append(
            "| {label} | {topic_type} | {risk_profile} | {section_count} | {slide_count} | "
            "{needs_source_count} | {needs_fact_check_count} | {source_url_count} | "
            "{required_before_broadcast_count} | {counterpoint_included} | "
            "{korea_bridge_included} | {production_checklist_included} | "
            "{do_not_claim_violation_count} | {passed} |".format(**item)
        )
    for item in summaries:
        lines.extend(
            [
                "",
                f"## {item['label']}",
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
                "",
            ]
        )
    lines.extend(
        [
            "## Common Strengths",
            "",
            "- Both dry runs preserve a 3-4 section representative outline.",
            "- Both distinguish attached sources from completed fact-checks.",
            (
                "- Both keep needs_source / needs_fact_check markers visible "
                "instead of inventing certainty."
            ),
            "- Both include counterpoint or risk discussion for sensitive topics.",
            "- Both separate rhetorical bridge slides from factual claims.",
            "- Both use slide-specific source_refs through the hygiene sidecar.",
            "- Key beat evaluation should use phrase-level aliases, not single-word matches.",
            "",
            "## Topic-Specific Weaknesses",
            "",
            (
                "- AI knowledge institution: source coverage is stronger, but "
                "education/인지 효과와 기관 역할 변화는 방송 전 수동 검증이 필요하다."
            ),
            (
                "- Productive finance policy: structure and guardrails pass, but "
                "source_url_count is low and many slides remain needs_source due "
                "to single-article basis."
            ),
            (
                "- Production checklist slides should later move to internal "
                "checklist, appendix, or notes rather than main PPT body."
            ),
            "",
            "## Production Readiness",
            "",
            "- ready_for_prompt_design: true",
            "- ready_for_production_agent: false",
            "- ready_for_broadcast: false",
            "",
            "Reason:",
            "- Two manual dry runs are sufficient to validate the prompt/eval contract.",
            (
                "- Evidence enrichment, model output variability, and failure handling "
                "are still needed before a production anny agent."
            ),
        ]
    )
    return "\n".join(lines) + "\n"


def _finance_evidence_items() -> dict[str, list[dict[str, Any]]]:
    return {
        "primary_official_source": [
            {
                "title": "국민성장펀드 성과점검 및 발전방향 세미나 공식자료",
                "url": None,
                "source": "금융위원회 / 산업은행",
                "source_type": "official_release",
                "short_summary": "금융위원장 발언 원문, 국민성장펀드 구조, 정책 목표 확인.",
                "role": "primary_official_source",
                "reliability": "high",
                "needs_manual_check": True,
            }
        ],
        "policy_mechanism": [
            {
                "title": "국민성장펀드 손실분담·민간 매칭 구조",
                "url": None,
                "source": "금융위원회 / 산업은행 / 기획재정부",
                "source_type": "official_or_policy_document",
                "short_summary": (
                    "정책자금, 민간자금, 보증·후순위 구조, 손실 발생 시 부담 순서 확인."
                ),
                "role": "policy_mechanism",
                "reliability": "high",
                "needs_manual_check": True,
            }
        ],
        "research_or_survey": [
            {
                "title": "AI·반도체 장기 투자 규모 관련 독립 자료",
                "url": None,
                "source": "한국은행 / 산업연구원 / OECD / 민간 리서치",
                "source_type": "research_or_survey",
                "short_summary": "첨단전략산업 투자 규모, 회수 기간, 자본집약도에 대한 독립 근거.",
                "role": "research_or_survey",
                "reliability": "medium",
                "needs_manual_check": True,
            }
        ],
        "counterpoint": [
            {
                "title": "정책금융 부작용과 관치금융 비판 사례",
                "url": None,
                "source": "국회/감사원/학술자료/언론 분석",
                "source_type": "counterpoint_analysis",
                "short_summary": (
                    "정책자금이 특정 기업 지원, 손실 전가, 비효율 투자로 흐를 수 "
                    "있다는 반대 관점."
                ),
                "role": "counterpoint",
                "reliability": "medium",
                "needs_manual_check": True,
            }
        ],
        "market_finance_view": [
            {
                "title": "금융권 건전성·위험분담 관점",
                "url": None,
                "source": "은행권/금융연구원/금융감독원 자료",
                "source_type": "market_finance_view",
                "short_summary": (
                    "은행 건전성, 예금자 보호, 위험가중자산, 정책 요구와 민간 금융 논리의 충돌."
                ),
                "role": "market_finance_view",
                "reliability": "medium",
                "needs_manual_check": True,
            }
        ],
        "visual_candidates": [
            {
                "title": "정책자금-민간자금-기업투자 흐름도",
                "url": None,
                "source": "manual_visual_plan",
                "source_type": "visual_candidate",
                "short_summary": (
                    "정책자금과 민간 매칭, 손실분담, 장기 위험자본 흐름을 도식화할 후보."
                ),
                "role": "visual_candidates",
                "reliability": "low",
                "needs_manual_check": True,
            }
        ],
    }


def _finance_evidence_pack() -> dict[str, Any]:
    return {
        "pack_id": "evidence_pack_productive_finance_policy",
        "story_seed_title": "생산적 금융과 정책자금 전환",
        "bundle_id": "anny_bundle_5c95ee31f95d",
        "case_id": "anny_dry_run_productive_finance_policy_v1",
        "status": "prep_only_url_pending",
        "full_article_text_stored": False,
        "categories": _finance_evidence_items(),
        "manual_research_checklist": [
            "금융위원회/산업은행/국민성장펀드 official material",
            "국민성장펀드 손실분담·민간 매칭 구조",
            "AI·반도체 장기 투자 규모 관련 official or independent material",
            "반대 관점: 관치금융, 정책금융 실패, 손실 전가, 비효율 투자",
            "금융권 관점: 건전성, 위험가중자산, 예금자 보호, 장기 위험자본 회피 이유",
        ],
        "ready_for_evidence_fill": True,
        "ready_for_prompt_design": True,
        "ready_for_production_agent": False,
        "ready_for_broadcast": False,
        "created_at": datetime.now(UTC).isoformat(),
    }


def _finance_plan_markdown(finance_evidence_pack_path: Path) -> str:
    evidence_items = [
        item
        for items in _finance_evidence_items().values()
        for item in items
    ]
    lines = [
        "# Finance Evidence Enrichment Plan — Productive Finance Policy",
        "",
        "## Current Interpretation",
        "",
        "- The second manual dry run validates structure and guardrails.",
        "- It is still single-article based and not broadcast-ready.",
        "- Source text/full article bodies are not stored here.",
        f"- Evidence fill pack: `{finance_evidence_pack_path}`",
        "",
        "## Required Evidence Items",
        "",
    ]
    for item in evidence_items:
        lines.extend(
            [
                f"### {item['title']}",
                "",
                f"- url: {item['url'] or 'null'}",
                f"- source: {item['source']}",
                f"- source_type: {item['source_type']}",
                f"- short summary: {item['short_summary']}",
                f"- role: {item['role']}",
                f"- reliability: {item['reliability']}",
                f"- needs_manual_check: {str(item['needs_manual_check']).lower()}",
                "",
            ]
        )
    lines.extend(
        [
            "## Must-Have Gaps",
            "",
            "- 금융위원회/산업은행/국민성장펀드 공식자료",
            "- 정책금융 손실분담 구조",
            "- AI·반도체 장기 투자 규모 관련 공식/독립 자료",
            "- 반대 관점: 관치금융, 정책금융 실패, 손실 전가 문제",
            "- 시장/금융권 관점 자료",
            "",
            "## Readiness",
            "",
            "- ready_for_prompt_design: true",
            "- ready_for_production_agent: false",
            "- ready_for_broadcast: false",
        ]
    )
    return "\n".join(lines) + "\n"


@app.callback(invoke_without_command=True)
def main(
    comparison_report_path: Annotated[
        Path,
        typer.Option("--comparison-report", help="Dry-run comparison Markdown output."),
    ] = DEFAULT_COMPARISON_REPORT,
    finance_evidence_report_path: Annotated[
        Path,
        typer.Option("--finance-report", help="Finance evidence plan Markdown output."),
    ] = DEFAULT_FINANCE_EVIDENCE_REPORT,
    finance_evidence_pack_path: Annotated[
        Path,
        typer.Option("--finance-pack", help="Finance evidence pack JSON output."),
    ] = DEFAULT_FINANCE_EVIDENCE_PACK,
) -> None:
    result = compare_dry_runs(
        comparison_report_path=comparison_report_path,
        finance_evidence_report_path=finance_evidence_report_path,
        finance_evidence_pack_path=finance_evidence_pack_path,
    )
    console.print(
        "[green]Wrote anny dry-run comparison "
        f"({result['case_count']} cases).[/green]"
    )


if __name__ == "__main__":
    app()
