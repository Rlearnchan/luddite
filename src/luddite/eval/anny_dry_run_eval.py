"""Validate manual anny storyline dry-run outputs."""

from __future__ import annotations

import json
from datetime import UTC, datetime
from pathlib import Path
from typing import Annotated, Any

import typer
from rich.console import Console

from luddite import paths
from luddite.eval.anny_reconstruction_eval import key_beat_recall
from luddite.utils.jsonl import read_jsonl, write_jsonl
from luddite.utils.schemas import validate_with_schema
from luddite.utils.urls import canonicalize_url

app = typer.Typer(no_args_is_help=False)
console = Console()

CASES_PATH = paths.EVAL_DIR / "golden_cases" / "anny_dry_run_cases.json"
DEFAULT_CASE_ID = "anny_dry_run_ai_knowledge_institution_v1"
DEFAULT_STORYLINE_JSON = (
    paths.ANNY_STORYLINE_DRY_RUN_DIR / "ai_knowledge_institution_gpt_pro_storyline.json"
)
DEFAULT_ENRICHED_STORYLINE_JSON = (
    paths.ANNY_STORYLINE_DRY_RUN_DIR
    / "ai_knowledge_institution_gpt_pro_storyline_enriched.json"
)
OUTPUT_DIR = paths.OUTPUTS_DIR / "eval" / "anny_storyline_dry_run"
DEFAULT_REPORT = OUTPUT_DIR / "latest.md"
DEFAULT_JSONL = OUTPUT_DIR / "latest.jsonl"
DEFAULT_HYGIENE_JSONL = (
    paths.ANNY_STORYLINE_DRY_RUN_DIR
    / "ai_knowledge_institution_source_hygiene.jsonl"
)
REPRESENTATIVE_SLIDE_RANGE = (20, 30)

DO_NOT_CLAIM_PATTERNS = [
    "교육 효과가 입증됐다",
    "인지 능력이 떨어진다",
    "인간 지능을 망친다",
    "AI는 무조건",
    "AI는 반드시",
    "매수해야 한다",
    "매도해야 한다",
    "수익률이 보장된다",
    "주가가 오른다",
    "정책 효과가 입증됐다",
    "반드시 성공한다",
]

REQUIRED_HYGIENE_FIELDS = [
    "fact_check_priority",
    "fact_check_kind",
    "required_before_storyline",
    "required_before_broadcast",
    "source_refs",
]


def _load_json(path: Path) -> Any:
    with path.open(encoding="utf-8") as source:
        return json.load(source)


def _case_by_id(cases_path: Path, case_id: str) -> dict[str, Any]:
    payload = _load_json(cases_path)
    for case in payload["cases"]:
        if case["case_id"] == case_id:
            return case
    raise ValueError(f"Unknown dry-run case_id: {case_id}")


def _all_slides(storyline: dict[str, Any]) -> list[dict[str, Any]]:
    return [
        slide
        for section in storyline.get("sections", [])
        for slide in section.get("slides", [])
    ]


def _source_image_overlap_count(storyline: dict[str, Any]) -> int:
    count = 0
    for slide in _all_slides(storyline):
        source_urls = {
            canonicalize_url(url) for url in slide.get("source_urls", []) if url
        }
        image_urls = {
            canonicalize_url(url) for url in slide.get("image_urls", []) if url
        }
        if source_urls & image_urls:
            count += 1
    return count


def _has_fact_check_marker(storyline: dict[str, Any]) -> bool:
    if storyline.get("required_fact_checks"):
        return True
    return any(
        slide.get("needs_fact_check") or slide.get("needs_source")
        for slide in _all_slides(storyline)
    )


def _source_url_count(storyline: dict[str, Any]) -> int:
    return sum(len(slide.get("source_urls", [])) for slide in _all_slides(storyline))


def _needs_source_count(storyline: dict[str, Any]) -> int:
    return sum(1 for slide in _all_slides(storyline) if slide.get("needs_source"))


def _needs_fact_check_count(storyline: dict[str, Any]) -> int:
    return sum(1 for slide in _all_slides(storyline) if slide.get("needs_fact_check"))


def _contains_any(storyline: dict[str, Any], patterns: list[str]) -> bool:
    text = _text_blob(storyline)
    return any(pattern in text for pattern in patterns)


def _text_blob(storyline: dict[str, Any]) -> str:
    parts = [storyline.get("title", ""), storyline.get("one_liner", "")]
    for section in storyline.get("sections", []):
        parts.append(section.get("section_title", ""))
        parts.append(section.get("purpose", "") or "")
        for slide in section.get("slides", []):
            parts.append(slide.get("headline", ""))
            parts.extend(slide.get("body", []))
            parts.append(slide.get("notes", ""))
    return "\n".join(str(part) for part in parts if part)


def _do_not_claim_violations(storyline: dict[str, Any]) -> list[str]:
    text = _text_blob(storyline)
    return [pattern for pattern in DO_NOT_CLAIM_PATTERNS if pattern in text]


def validate_dry_run_storyline(
    *,
    storyline_path: Path = DEFAULT_STORYLINE_JSON,
    cases_path: Path = CASES_PATH,
    case_id: str = DEFAULT_CASE_ID,
    baseline_storyline_path: Path | None = None,
    hygiene_jsonl_path: Path | None = None,
    require_enriched: bool = False,
    require_hygiene_contract: bool = False,
) -> dict[str, Any]:
    case = _case_by_id(cases_path, case_id)
    storyline = _load_json(storyline_path)
    schema_errors = validate_with_schema(storyline, "anny_storyline_schema.json")
    section_count = len(storyline.get("sections", []))
    section_count_ok = (
        case["expected_sections_min"] <= section_count <= case["expected_sections_max"]
    )
    slide_count = len(_all_slides(storyline))
    slide_count_ok = REPRESENTATIVE_SLIDE_RANGE[0] <= slide_count <= REPRESENTATIVE_SLIDE_RANGE[1]
    recall, matched_beats, missing_beats = key_beat_recall(
        storyline,
        case.get("expected_key_beats", []),
    )
    overlap_count = _source_image_overlap_count(storyline)
    fact_check_marker_present = _has_fact_check_marker(storyline)
    claim_violations = _do_not_claim_violations(storyline)
    source_url_count = _source_url_count(storyline)
    needs_source_count = _needs_source_count(storyline)
    needs_fact_check_count = _needs_fact_check_count(storyline)
    counterpoint_included = _contains_any(
        storyline,
        [
            "counterpoint",
            "반대 관점",
            "접근성",
            "personalized learning",
            "맞춤형",
            "리스크",
            "반론",
        ],
    )
    korea_bridge_included = _contains_any(
        storyline,
        ["한국", "정책브리핑", "AI 디지털교과서", "국립광주과학관", "국립과학관"],
    )
    baseline_metrics: dict[str, Any] = {}
    enriched_checks_passed = True
    if baseline_storyline_path:
        baseline = _load_json(baseline_storyline_path)
        baseline_source_url_count = _source_url_count(baseline)
        baseline_needs_source_count = _needs_source_count(baseline)
        baseline_metrics = {
            "baseline_storyline_path": str(baseline_storyline_path),
            "baseline_source_url_count": baseline_source_url_count,
            "baseline_needs_source_count": baseline_needs_source_count,
            "source_urls_increased": source_url_count > baseline_source_url_count,
            "needs_source_decreased": needs_source_count < baseline_needs_source_count,
        }
        enriched_checks_passed = (
            baseline_metrics["source_urls_increased"]
            and baseline_metrics["needs_source_decreased"]
            and counterpoint_included
        )
    elif require_enriched:
        enriched_checks_passed = counterpoint_included and source_url_count > 0
    hygiene_result = validate_hygiene_contract(
        hygiene_jsonl_path,
        expected_slide_count=slide_count,
        require_hygiene_contract=require_hygiene_contract,
    )
    policy_finance_result = validate_policy_finance_guardrails(
        storyline,
        case_id=case_id,
        hygiene_records=hygiene_result.get("hygiene_records", []),
    )
    passed = (
        not schema_errors
        and section_count_ok
        and slide_count_ok
        and recall >= 0.70
        and overlap_count == 0
        and fact_check_marker_present
        and not claim_violations
        and (enriched_checks_passed if require_enriched or baseline_storyline_path else True)
        and hygiene_result["hygiene_contract_passed"]
        and policy_finance_result["policy_finance_guardrails_passed"]
    )
    return {
        "case_id": case_id,
        "storyline_path": str(storyline_path),
        "schema_valid": not schema_errors,
        "schema_errors": schema_errors,
        "section_count": section_count,
        "section_count_ok": section_count_ok,
        "slide_count": slide_count,
        "slide_count_ok": slide_count_ok,
        "key_beat_recall": recall,
        "matched_key_beats": matched_beats,
        "missing_key_beats": missing_beats,
        "source_image_overlap_count": overlap_count,
        "source_url_count": source_url_count,
        "needs_source_count": needs_source_count,
        "needs_fact_check_count": needs_fact_check_count,
        "counterpoint_included": counterpoint_included,
        "korea_bridge_included": korea_bridge_included,
        **baseline_metrics,
        "fact_check_marker_present": fact_check_marker_present,
        "do_not_claim_violations": claim_violations,
        "enriched_checks_passed": enriched_checks_passed,
        **hygiene_result,
        **policy_finance_result,
        "passed": passed,
    }


def validate_hygiene_contract(
    hygiene_jsonl_path: Path | None,
    *,
    expected_slide_count: int,
    require_hygiene_contract: bool,
) -> dict[str, Any]:
    if not hygiene_jsonl_path:
        return {
            "hygiene_jsonl_path": None,
            "hygiene_record_count": 0,
            "hygiene_required": require_hygiene_contract,
            "hygiene_contract_passed": not require_hygiene_contract,
            "hygiene_contract_errors": (
                ["hygiene sidecar path missing"] if require_hygiene_contract else []
            ),
            "hygiene_records": [],
        }
    if not hygiene_jsonl_path.exists():
        return {
            "hygiene_jsonl_path": str(hygiene_jsonl_path),
            "hygiene_record_count": 0,
            "hygiene_required": require_hygiene_contract,
            "hygiene_contract_passed": not require_hygiene_contract,
            "hygiene_contract_errors": (
                [f"hygiene sidecar not found: {hygiene_jsonl_path}"]
                if require_hygiene_contract
                else []
            ),
            "hygiene_records": [],
        }
    records = read_jsonl(hygiene_jsonl_path)
    errors = hygiene_contract_errors(records, expected_slide_count=expected_slide_count)
    return {
        "hygiene_jsonl_path": str(hygiene_jsonl_path),
        "hygiene_record_count": len(records),
        "hygiene_required": require_hygiene_contract,
        "hygiene_contract_passed": not errors,
        "hygiene_contract_errors": errors,
        "hygiene_records": records,
    }


def hygiene_contract_errors(
    records: list[dict[str, Any]], *, expected_slide_count: int
) -> list[str]:
    errors = []
    if len(records) != expected_slide_count:
        errors.append(
            f"hygiene record count {len(records)} != slide count {expected_slide_count}"
        )
    for index, record in enumerate(records, start=1):
        missing = [field for field in REQUIRED_HYGIENE_FIELDS if field not in record]
        if missing:
            errors.append(f"slide {record.get('slide_no', index)} missing fields: {missing}")
        if record.get("fact_check_priority") not in {"high", "medium", "low"}:
            errors.append(f"slide {record.get('slide_no', index)} invalid priority")
        if not isinstance(record.get("required_before_broadcast"), bool):
            errors.append(f"slide {record.get('slide_no', index)} missing broadcast gate")
        if not isinstance(record.get("required_before_storyline"), bool):
            errors.append(f"slide {record.get('slide_no', index)} missing storyline gate")
        for source_ref in record.get("source_refs", []):
            for field in ["url", "role", "use", "confidence", "manual_check_required"]:
                if field not in source_ref:
                    errors.append(
                        f"slide {record.get('slide_no', index)} source_ref missing {field}"
                    )
    return errors


def validate_policy_finance_guardrails(
    storyline: dict[str, Any], *, case_id: str, hygiene_records: list[dict[str, Any]]
) -> dict[str, Any]:
    text = _text_blob(storyline)
    finance_topic = (
        "productive_finance_policy" in case_id
        or any(marker in text for marker in ["정책금융", "국민성장펀드", "투자", "금융"])
    )
    errors: list[str] = []
    if finance_topic:
        banned = [
            "매수해야 한다",
            "매도해야 한다",
            "수익률이 보장된다",
            "주가가 오른다",
            "정책 효과가 입증됐다",
            "금융상품을 추천",
        ]
        errors.extend([f"finance banned claim: {pattern}" for pattern in banned if pattern in text])
        policy_records = [
            record
            for record in hygiene_records
            if record.get("fact_check_kind") == "policy_effect_claim"
        ]
        for record in policy_records:
            if record.get("fact_check_priority") not in {"high", "medium"}:
                errors.append(
                    f"slide {record.get('slide_no')} policy_effect_claim priority too low"
                )
            if not record.get("required_before_broadcast"):
                errors.append(
                    f"slide {record.get('slide_no')} policy_effect_claim missing broadcast gate"
                )
        if "리스크" not in text and "반론" not in text and "counterpoint" not in text:
            errors.append("finance/policy storyline missing risk discussion or counterpoint")
    return {
        "policy_finance_topic": finance_topic,
        "policy_finance_guardrails_passed": not errors,
        "policy_finance_guardrail_errors": errors,
    }


def write_report(path: Path, result: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    schema_errors = [f"- {item}" for item in result["schema_errors"]] or ["- none"]
    claim_violations = [
        f"- {item}" for item in result["do_not_claim_violations"]
    ] or ["- none"]
    hygiene_errors = [
        f"- {item}" for item in result["hygiene_contract_errors"]
    ] or ["- none"]
    policy_finance_errors = [
        f"- {item}" for item in result["policy_finance_guardrail_errors"]
    ] or ["- none"]
    lines = [
        "# Anny Dry Run Eval Report",
        "",
        f"- generated_at: {datetime.now(UTC).isoformat()}",
        f"- case_id: {result['case_id']}",
        f"- storyline_path: {result['storyline_path']}",
        f"- schema_valid: {result['schema_valid']}",
        f"- section_count: {result['section_count']}",
        f"- section_count_ok: {result['section_count_ok']}",
        f"- slide_count: {result['slide_count']}",
        f"- slide_count_ok: {result['slide_count_ok']}",
        f"- key_beat_recall: {result['key_beat_recall']:.2f}",
        f"- source_image_overlap_count: {result['source_image_overlap_count']}",
        f"- source_url_count: {result['source_url_count']}",
        f"- needs_source_count: {result['needs_source_count']}",
        f"- needs_fact_check_count: {result['needs_fact_check_count']}",
        f"- counterpoint_included: {result['counterpoint_included']}",
        f"- korea_bridge_included: {result['korea_bridge_included']}",
        f"- fact_check_marker_present: {result['fact_check_marker_present']}",
        f"- enriched_checks_passed: {result['enriched_checks_passed']}",
        f"- hygiene_contract_passed: {result['hygiene_contract_passed']}",
        f"- policy_finance_topic: {result['policy_finance_topic']}",
        f"- policy_finance_guardrails_passed: {result['policy_finance_guardrails_passed']}",
        f"- passed: {result['passed']}",
        (
            "- production_readiness: "
            f"{'evidence_enriched_dry_run_passed' if result['passed'] else 'not_ready'}"
        ),
        "",
        "## Enriched Comparison",
        "",
        f"- baseline_storyline_path: {result.get('baseline_storyline_path', 'n/a')}",
        f"- baseline_source_url_count: {result.get('baseline_source_url_count', 'n/a')}",
        f"- baseline_needs_source_count: {result.get('baseline_needs_source_count', 'n/a')}",
        f"- source_urls_increased: {result.get('source_urls_increased', 'n/a')}",
        f"- needs_source_decreased: {result.get('needs_source_decreased', 'n/a')}",
        f"- remaining_evidence_gaps: needs_fact_check={result['needs_fact_check_count']}",
        "",
        "## Hygiene Contract",
        "",
        f"- hygiene_jsonl_path: {result['hygiene_jsonl_path']}",
        f"- hygiene_record_count: {result['hygiene_record_count']}",
        f"- hygiene_required: {result['hygiene_required']}",
        f"- hygiene_contract_passed: {result['hygiene_contract_passed']}",
        "",
        "## Hygiene Contract Errors",
        "",
        *hygiene_errors,
        "",
        "## Policy / Finance Guardrails",
        "",
        f"- policy_finance_topic: {result['policy_finance_topic']}",
        f"- policy_finance_guardrails_passed: {result['policy_finance_guardrails_passed']}",
        "",
        "## Policy / Finance Guardrail Errors",
        "",
        *policy_finance_errors,
        "",
        "## Interpretation",
        "",
        "- This GPT Pro output is a story-structure dry run based on the existing input bundle.",
        "- It is not a completed research packet or broadcast-ready script.",
        (
            "- Evidence enrichment is improved, but remaining needs_fact_check "
            "slides still require cautious wording."
        ),
        (
            "- Production anny generation should wait for one more review of "
            "fact-check and source framing."
        ),
        "",
        "## Matched Key Beats",
        "",
        *[f"- {item}" for item in result["matched_key_beats"]],
        "",
        "## Missing Key Beats",
        "",
        *[f"- {item}" for item in result["missing_key_beats"]],
        "",
        "## Schema Errors",
        "",
        *schema_errors,
        "",
        "## Do Not Claim Violations",
        "",
        *claim_violations,
    ]
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def write_jsonl_report(path: Path, result: dict[str, Any]) -> None:
    write_jsonl(path, [result])


@app.callback(invoke_without_command=True)
def main(
    storyline_path: Annotated[
        Path,
        typer.Option("--storyline", help="Manual GPT Pro storyline JSON path."),
    ] = DEFAULT_STORYLINE_JSON,
    baseline_storyline_path: Annotated[
        Path | None,
        typer.Option("--baseline-storyline", help="Baseline storyline for enriched comparison."),
    ] = None,
    hygiene_jsonl_path: Annotated[
        Path | None,
        typer.Option("--hygiene-jsonl", help="Fact-check/source hygiene sidecar JSONL."),
    ] = None,
    cases_path: Annotated[
        Path,
        typer.Option("--cases", help="Anny dry-run cases JSON path."),
    ] = CASES_PATH,
    case_id: Annotated[
        str,
        typer.Option("--case-id", help="Dry-run case id."),
    ] = DEFAULT_CASE_ID,
    report: Annotated[
        Path,
        typer.Option("--report", help="Markdown eval report path."),
    ] = DEFAULT_REPORT,
    output_jsonl: Annotated[
        Path,
        typer.Option("--output-jsonl", help="JSONL eval result path."),
    ] = DEFAULT_JSONL,
    allow_missing: Annotated[
        bool,
        typer.Option(
            "--allow-missing/--no-allow-missing",
            help="Exit 0 if output is not ready yet.",
        ),
    ] = True,
    require_enriched: Annotated[
        bool,
        typer.Option(
            "--require-enriched/--no-require-enriched",
            help="Require enriched checks such as more sources and fewer source gaps.",
        ),
    ] = False,
    require_hygiene_contract: Annotated[
        bool,
        typer.Option(
            "--require-hygiene-contract/--no-require-hygiene-contract",
            help="Require fact-check/source hygiene sidecar contract.",
        ),
    ] = False,
) -> None:
    if not storyline_path.exists():
        report.parent.mkdir(parents=True, exist_ok=True)
        report.write_text(
            "\n".join(
                [
                    "# Anny Dry Run Eval Report",
                    "",
                    f"- case_id: {case_id}",
                    f"- storyline_path: {storyline_path}",
                    "- status: pending_manual_gpt_pro_output",
                    "",
                ]
            ),
            encoding="utf-8",
        )
        write_jsonl_report(
            output_jsonl,
            {
                "case_id": case_id,
                "storyline_path": str(storyline_path),
                "status": "pending_manual_gpt_pro_output",
                "passed": False,
            },
        )
        console.print(f"[yellow]Manual storyline output is pending: {storyline_path}[/yellow]")
        raise typer.Exit(0 if allow_missing else 1)
    result = validate_dry_run_storyline(
        storyline_path=storyline_path,
        cases_path=cases_path,
        case_id=case_id,
        baseline_storyline_path=baseline_storyline_path,
        hygiene_jsonl_path=hygiene_jsonl_path,
        require_enriched=require_enriched,
        require_hygiene_contract=require_hygiene_contract,
    )
    write_report(report, result)
    write_jsonl_report(output_jsonl, result)
    console.print(f"[green]Wrote anny dry-run eval report to {report}.[/green]")
    raise typer.Exit(0 if result["passed"] else 1)


if __name__ == "__main__":
    app()
