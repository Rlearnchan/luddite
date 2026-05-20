"""Compare Jibi slideability hints with downstream Piti visual QA.

This is a deterministic calibration report. It does not change Jibi scoring,
handoff gates, Anny prompts, or Piti rendering behavior.
"""

from __future__ import annotations

import json
from collections import Counter
from dataclasses import dataclass
from datetime import date
from pathlib import Path
from typing import Annotated, Any

import typer
from rich.console import Console

from luddite import paths
from luddite.agents.piti.render_visual_qa import VisualQaDeck, evaluate_slide_spec
from luddite.utils.jsonl import read_jsonl
from luddite.utils.schemas import validate_with_schema

app = typer.Typer(no_args_is_help=False)
console = Console()

DEFAULT_OUTPUT_PATH = paths.REPORTS_DIR / (
    f"slideability_visual_qa_comparison_{date.today().isoformat()}.md"
)
DEFAULT_REVIEW_PATH = paths.DOCS_DIR / "reviews" / "slideability_visual_qa_comparison.md"

PROOF_TYPES = {"diagram", "chart", "table", "source_card", "article_quote"}
CHART_TYPES = {"chart", "table"}


@dataclass(frozen=True)
class ComparisonCase:
    story_seed_title: str
    deck_id: str
    bundle: dict[str, Any] | None
    slide_spec: dict[str, Any] | None
    slide_spec_path: Path | None
    visual_qa_deck: VisualQaDeck | None
    warning: str | None = None


def _load_json(path: Path) -> dict[str, Any]:
    with path.open(encoding="utf-8") as source:
        payload = json.load(source)
    if not isinstance(payload, dict):
        raise ValueError(f"Expected JSON object at {path}")
    return payload


def _as_list(value: Any) -> list[Any]:
    return value if isinstance(value, list) else []


def _markdown_cell(value: Any) -> str:
    text = str(value if value is not None else "")
    return text.replace("\n", "<br>").replace("|", "\\|")


def _display_path(path: Path | None) -> str:
    if path is None:
        return "-"
    try:
        return str(path.resolve().relative_to(paths.REPO_ROOT))
    except ValueError:
        return str(path)


def _visual_hint(bundle: dict[str, Any] | None) -> dict[str, Any]:
    if not bundle:
        return {}
    hint = bundle.get("visual_planning_hint")
    return hint if isinstance(hint, dict) else {}


def _slides(spec: dict[str, Any] | None) -> list[dict[str, Any]]:
    if not spec:
        return []
    return [slide for slide in _as_list(spec.get("slides")) if isinstance(slide, dict)]


def _sections(spec: dict[str, Any] | None) -> list[dict[str, Any]]:
    if not spec:
        return []
    return [section for section in _as_list(spec.get("sections")) if isinstance(section, dict)]


def _proof_type(slide: dict[str, Any]) -> str:
    proof = slide.get("proof_object")
    if not isinstance(proof, dict):
        return "none"
    return str(proof.get("type") or "none")


def _proof_object_type_counts(spec: dict[str, Any] | None) -> Counter[str]:
    return Counter(_proof_type(slide) for slide in _slides(spec))


def _source_refs_count(spec: dict[str, Any] | None) -> int:
    return sum(len(_as_list(slide.get("source_refs"))) for slide in _slides(spec))


def _do_not_claim_count(spec: dict[str, Any] | None) -> int:
    return sum(len(_as_list(slide.get("do_not_claim"))) for slide in _slides(spec))


def _needs_fact_check_count(spec: dict[str, Any] | None) -> int:
    return sum(1 for slide in _slides(spec) if slide.get("needs_fact_check"))


def _required_before_broadcast_count(spec: dict[str, Any] | None) -> int:
    return sum(1 for slide in _slides(spec) if slide.get("required_before_broadcast"))


def _screen_body_len(slide: dict[str, Any]) -> int:
    return len(_as_list(slide.get("screen_body")))


def _chart_table_body_too_long_slides(spec: dict[str, Any] | None) -> list[int]:
    slides: list[int] = []
    for slide in _slides(spec):
        if _proof_type(slide) in CHART_TYPES and _screen_body_len(slide) > 1:
            slides.append(int(slide.get("slide_no") or 0))
    return slides


def _article_quote_missing_quote_text_slides(spec: dict[str, Any] | None) -> list[int]:
    slides: list[int] = []
    for slide in _slides(spec):
        proof = slide.get("proof_object")
        if not isinstance(proof, dict) or str(proof.get("type") or "") != "article_quote":
            continue
        if not str(proof.get("quote_text") or "").strip():
            slides.append(int(slide.get("slide_no") or 0))
    return slides


def _section_mapping_complete(spec: dict[str, Any] | None) -> bool:
    if not spec:
        return False
    top_level = {
        (str(slide.get("slide_id") or ""), int(slide.get("slide_no") or 0))
        for slide in _slides(spec)
    }
    mapped: list[tuple[str, int]] = []
    for section in _sections(spec):
        section_slides = [
            slide for slide in _as_list(section.get("slides")) if isinstance(slide, dict)
        ]
        if not section_slides:
            return False
        mapped.extend(
            (str(slide.get("slide_id") or ""), int(slide.get("slide_no") or 0))
            for slide in section_slides
        )
    mapped_set = set(mapped)
    return bool(top_level) and top_level == mapped_set and len(mapped) == len(mapped_set)


def _flag_counts(deck: VisualQaDeck | None) -> Counter[str]:
    counter: Counter[str] = Counter()
    if deck is None:
        return counter
    for slide in deck.slides:
        counter.update(slide.visual_qa_flags)
    return counter


def _severity_counts(deck: VisualQaDeck | None) -> Counter[str]:
    counter: Counter[str] = Counter()
    if deck is None:
        return counter
    for slide in deck.slides:
        counter.update(detail.severity for detail in slide.flag_details)
    return counter


def _actual_visual_types(counts: Counter[str]) -> set[str]:
    actual = {proof_type for proof_type, count in counts.items() if count and proof_type != "none"}
    if "table" in actual:
        actual.add("chart")
    return actual


def _dominant_type(counts: Counter[str]) -> str:
    filtered = Counter(
        {
            proof_type: count
            for proof_type, count in counts.items()
            if proof_type != "none" and count
        }
    )
    if not filtered:
        return "none"
    proof_type, _ = filtered.most_common(1)[0]
    return "chart" if proof_type == "table" else proof_type


def _proof_type_match(predicted: list[str], counts: Counter[str]) -> str:
    if not predicted:
        return "missing_hint"
    actual = _actual_visual_types(counts)
    if not actual:
        return "miss"
    dominant = _dominant_type(counts)
    first_predicted = predicted[0]
    if first_predicted == dominant:
        return "strong"
    if any(item in actual for item in predicted):
        return "partial"
    return "miss"


def _chartability_alignment(predicted: list[str], counts: Counter[str]) -> str:
    predicted_chart = "chart" in predicted
    actual_chart = counts.get("chart", 0) + counts.get("table", 0) > 0
    if predicted_chart and actual_chart:
        return "hit"
    if predicted_chart and not actual_chart:
        return "miss"
    if not predicted_chart and actual_chart:
        return "underprediction"
    return "not_predicted"


def _diagramability_alignment(
    predicted: list[str],
    counts: Counter[str],
    flag_counts: Counter[str],
) -> str:
    predicted_diagram = "diagram" in predicted
    actual_diagram = counts.get("diagram", 0) > 0
    if predicted_diagram and actual_diagram:
        if flag_counts.get("diagram_nodes_too_generic", 0):
            return "low_quality_hit"
        return "hit"
    if predicted_diagram and not actual_diagram:
        return "miss"
    if not predicted_diagram and actual_diagram:
        return "underprediction"
    return "not_predicted"


def _source_card_alignment(predicted: list[str], counts: Counter[str]) -> str:
    predicted_source_card = "source_card" in predicted
    actual_source_card = counts.get("source_card", 0) > 0
    if predicted_source_card and actual_source_card:
        return "hit"
    if predicted_source_card and not actual_source_card:
        return "miss"
    if not predicted_source_card and actual_source_card:
        return "underprediction"
    return "not_predicted"


def _risk_alignment(
    visual_risks: list[str],
    *,
    spec: dict[str, Any] | None,
    counts: Counter[str],
) -> tuple[str, list[str]]:
    if not visual_risks:
        return "not_applicable", ["No visual risks were supplied."]
    checks: list[tuple[str, bool, str]] = []
    needs_fact_check = _needs_fact_check_count(spec)
    required_before_broadcast = _required_before_broadcast_count(spec)
    source_refs = _source_refs_count(spec)
    do_not_claim = _do_not_claim_count(spec)
    if "single_source" in visual_risks:
        checks.append(
            (
                "single_source",
                source_refs > 0 or needs_fact_check > 0 or counts.get("source_card", 0) > 0,
                "expects source refs, source cards, or retained fact-check caution",
            )
        )
    if "needs_official_data" in visual_risks:
        checks.append(
            (
                "needs_official_data",
                needs_fact_check > 0 or required_before_broadcast > 0,
                "expects needs_fact_check or required_before_broadcast to remain",
            )
        )
    for risk in ("policy_claim_risk", "market_claim_risk"):
        if risk in visual_risks:
            checks.append(
                (
                    risk,
                    do_not_claim > 0 or needs_fact_check > 0 or required_before_broadcast > 0,
                    "expects do_not_claim or fact-check caution to remain",
                )
            )
    if not checks:
        return "not_applicable", ["No recognized visual risk types were supplied."]
    passed = sum(1 for _, ok, _ in checks if ok)
    notes = [
        f"{risk}: {'ok' if ok else 'missing'} ({expectation})"
        for risk, ok, expectation in checks
    ]
    if passed == len(checks):
        return "good", notes
    if passed:
        return "mixed", notes
    return "weak", notes


def _prediction_quality(
    proof_match: str,
    risk_alignment: str,
    diagram_alignment: str,
) -> str:
    if proof_match in {"strong", "partial"} and risk_alignment in {"good", "not_applicable"}:
        return "mixed" if diagram_alignment == "low_quality_hit" else "good"
    if proof_match in {"strong", "partial"} or risk_alignment == "good":
        return "mixed"
    return "weak"


def _case_metrics(case: ComparisonCase) -> dict[str, Any]:
    hint = _visual_hint(case.bundle)
    predicted = [str(item) for item in _as_list(hint.get("likely_proof_object_types"))]
    visual_risks = [str(item) for item in _as_list(hint.get("visual_risks"))]
    proof_counts = _proof_object_type_counts(case.slide_spec)
    flag_counts = _flag_counts(case.visual_qa_deck)
    severity_counts = _severity_counts(case.visual_qa_deck)
    proof_match = _proof_type_match(predicted, proof_counts)
    diagram_alignment = _diagramability_alignment(predicted, proof_counts, flag_counts)
    risk_alignment, risk_notes = _risk_alignment(
        visual_risks,
        spec=case.slide_spec,
        counts=proof_counts,
    )
    quality = _prediction_quality(proof_match, risk_alignment, diagram_alignment)
    chart_body_slides = _chart_table_body_too_long_slides(case.slide_spec)
    quote_missing_slides = _article_quote_missing_quote_text_slides(case.slide_spec)
    return {
        "hint": hint,
        "predicted_proof_types": predicted,
        "visual_risks": visual_risks,
        "proof_counts": proof_counts,
        "flag_counts": flag_counts,
        "severity_counts": severity_counts,
        "slide_count": len(_slides(case.slide_spec)),
        "section_count": len(_sections(case.slide_spec)),
        "diagram_count": proof_counts.get("diagram", 0),
        "chart_table_count": proof_counts.get("chart", 0) + proof_counts.get("table", 0),
        "source_card_count": proof_counts.get("source_card", 0),
        "article_quote_count": proof_counts.get("article_quote", 0),
        "text_only_count": proof_counts.get("none", 0),
        "needs_fact_check_count": _needs_fact_check_count(case.slide_spec),
        "required_before_broadcast_count": _required_before_broadcast_count(case.slide_spec),
        "source_refs_count": _source_refs_count(case.slide_spec),
        "do_not_claim_count": _do_not_claim_count(case.slide_spec),
        "chart_table_body_too_long_count": len(chart_body_slides),
        "chart_table_body_too_long_slides": chart_body_slides,
        "article_quote_missing_quote_text_count": len(quote_missing_slides),
        "article_quote_missing_quote_text_slides": quote_missing_slides,
        "section_mapping_complete": _section_mapping_complete(case.slide_spec),
        "schema_valid": (
            validate_with_schema(case.slide_spec, "piti_slide_spec_schema.json") == []
            if case.slide_spec
            else False
        ),
        "render_passed": "not_evaluated",
        "proof_type_match": proof_match,
        "chartability_alignment": _chartability_alignment(predicted, proof_counts),
        "diagramability_alignment": diagram_alignment,
        "source_card_alignment": _source_card_alignment(predicted, proof_counts),
        "risk_alignment": risk_alignment,
        "risk_alignment_notes": risk_notes,
        "slideability_prediction_quality": quality,
    }


def _bundle_by_title(bundles: list[dict[str, Any]]) -> dict[str, dict[str, Any]]:
    return {str(bundle.get("story_seed_title") or ""): bundle for bundle in bundles}


def _load_cases(
    *,
    bundles_path: Path,
    slide_specs_dir: Path,
    output_dir: Path,
) -> list[ComparisonCase]:
    bundles = read_jsonl(bundles_path) if bundles_path.exists() else []
    bundles_by_title = _bundle_by_title(bundles)
    cases: list[ComparisonCase] = []
    if not slide_specs_dir.exists():
        return [
            ComparisonCase(
                story_seed_title="missing_slide_specs",
                deck_id="missing_slide_specs",
                bundle=None,
                slide_spec=None,
                slide_spec_path=None,
                visual_qa_deck=None,
                warning=f"Slide spec directory not found: {slide_specs_dir}",
            )
        ]
    for path in sorted(slide_specs_dir.glob("*.json")):
        try:
            spec = _load_json(path)
        except (OSError, ValueError, json.JSONDecodeError) as error:
            cases.append(
                ComparisonCase(
                    story_seed_title=path.stem,
                    deck_id=path.stem,
                    bundle=None,
                    slide_spec=None,
                    slide_spec_path=path,
                    visual_qa_deck=None,
                    warning=str(error),
                )
            )
            continue
        title = str(spec.get("story_seed_title") or path.stem)
        deck_id = str(spec.get("deck_id") or path.stem)
        deck = evaluate_slide_spec(path, spec, output_dir)
        cases.append(
            ComparisonCase(
                story_seed_title=title,
                deck_id=deck_id,
                bundle=bundles_by_title.get(title),
                slide_spec=spec,
                slide_spec_path=path,
                visual_qa_deck=deck,
                warning=None if title in bundles_by_title else "No matching Anny input bundle.",
            )
        )
    if not cases:
        cases.append(
            ComparisonCase(
                story_seed_title="missing_slide_specs",
                deck_id="missing_slide_specs",
                bundle=None,
                slide_spec=None,
                slide_spec_path=None,
                visual_qa_deck=None,
                warning=f"No slide spec JSON files found in: {slide_specs_dir}",
            )
        )
    return cases


def _counter_text(counter: Counter[str]) -> str:
    if not counter:
        return "-"
    return ", ".join(f"{key}:{counter[key]}" for key in sorted(counter))


def _list_text(items: list[Any]) -> str:
    return ", ".join(str(item) for item in items) if items else "-"


def _metric_flag_count(metrics: dict[str, Any], flag: str) -> int:
    counter = metrics.get("flag_counts")
    if not isinstance(counter, Counter):
        return 0
    return counter.get(flag, 0)


def _notes(metrics: dict[str, Any], warning: str | None) -> str:
    notes: list[str] = []
    if warning:
        notes.append(warning)
    if metrics["proof_type_match"] in {"strong", "partial"}:
        notes.append("Predicted proof type appears downstream.")
    else:
        notes.append("Predicted proof type needs calibration.")
    if metrics["diagramability_alignment"] == "low_quality_hit":
        notes.append("Diagram was used, but visual QA still flags generic diagram nodes.")
    if metrics["risk_alignment"] == "good":
        notes.append("Visual risks align with retained source/fact-check caution.")
    elif metrics["risk_alignment"] == "mixed":
        notes.append("Some visual risks align with downstream caution, but not all.")
    return " ".join(notes)


def _write_report(path: Path, cases: list[ComparisonCase]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    case_metrics = [(case, _case_metrics(case)) for case in cases]
    quality_counts = Counter(
        metrics["slideability_prediction_quality"] for _, metrics in case_metrics
    )
    lines = [
        "# Slideability vs Piti Visual QA Comparison",
        "",
        f"- Generated for: {date.today().isoformat()}",
        (
            "- Purpose: calibrate Jibi slideability / Anny visual planning hints "
            "against downstream Piti slide specs and visual QA."
        ),
        (
            "- Review-only: this report does not change Jibi scoring, "
            "recommended_action, handoff gates, Anny prompts, or Piti rendering."
        ),
        "- LLM/API calls: none",
        "- Production readiness remains false.",
        "- Broadcast readiness remains false.",
        "",
        "## Summary",
        "",
        f"- compared cases: {len(case_metrics)}",
        *[
            f"- slideability_prediction_quality {quality}: {count}"
            for quality, count in sorted(quality_counts.items())
        ],
        "",
        "## Case Alignment",
        "",
        (
            "| case | predicted proof types | actual proof counts | proof_type_match | "
            "chartability | diagramability | source_card | risk_alignment | "
            "prediction_quality | notes |"
        ),
        "|---|---|---|---|---|---|---|---|---|---|",
    ]
    for case, metrics in case_metrics:
        lines.append(
            f"| {_markdown_cell(case.story_seed_title)} | "
            f"{_markdown_cell(_list_text(metrics['predicted_proof_types']))} | "
            f"{_markdown_cell(_counter_text(metrics['proof_counts']))} | "
            f"{metrics['proof_type_match']} | "
            f"{metrics['chartability_alignment']} | "
            f"{metrics['diagramability_alignment']} | "
            f"{metrics['source_card_alignment']} | "
            f"{metrics['risk_alignment']} | "
            f"{metrics['slideability_prediction_quality']} | "
            f"{_markdown_cell(_notes(metrics, case.warning))} |"
        )
    lines.extend(["", "## Case Details", ""])
    for case, metrics in case_metrics:
        hint = metrics["hint"]
        manual_insert_missing = _metric_flag_count(
            metrics,
            "manual_insert_required_without_editor_instruction",
        )
        source_title_generic = _metric_flag_count(
            metrics,
            "source_card_display_title_too_generic",
        )
        lines.extend(
            [
                f"### {case.story_seed_title}",
                "",
                "Jibi / Anny input side:",
                "",
                f"- deck_id: {case.deck_id}",
                f"- input bundle matched: {str(case.bundle is not None).lower()}",
                f"- slide spec: {_display_path(case.slide_spec_path)}",
                f"- slideability_score: {hint.get('slideability_score', '-')}",
                f"- visualizability: {hint.get('visualizability', '-')}",
                f"- first_slide_idea: {hint.get('first_slide_idea', '-')}",
                f"- likely_proof_object_types: {_list_text(metrics['predicted_proof_types'])}",
                f"- visual_risks: {_list_text(metrics['visual_risks'])}",
                f"- reason: {hint.get('reason', '-')}",
                "",
                "Piti slide spec side:",
                "",
                f"- slide_count: {metrics['slide_count']}",
                f"- section_count: {metrics['section_count']}",
                f"- proof_object_type_counts: {_counter_text(metrics['proof_counts'])}",
                f"- diagram_count: {metrics['diagram_count']}",
                f"- chart/table_count: {metrics['chart_table_count']}",
                f"- source_card_count: {metrics['source_card_count']}",
                f"- article_quote_count: {metrics['article_quote_count']}",
                f"- text_only_count: {metrics['text_only_count']}",
                f"- needs_fact_check_count: {metrics['needs_fact_check_count']}",
                (
                    "- required_before_broadcast_count: "
                    f"{metrics['required_before_broadcast_count']}"
                ),
                f"- source_refs_count: {metrics['source_refs_count']}",
                f"- do_not_claim_count: {metrics['do_not_claim_count']}",
                "",
                "Piti visual QA side:",
                "",
                f"- schema_valid: {str(metrics['schema_valid']).lower()}",
                f"- render_passed: {metrics['render_passed']}",
                f"- section_mapping_complete: {str(metrics['section_mapping_complete']).lower()}",
                f"- QA flag counts: {_counter_text(metrics['flag_counts'])}",
                f"- severity counts: {_counter_text(metrics['severity_counts'])}",
                (
                    "- diagram_nodes_too_generic: "
                    f"{metrics['flag_counts'].get('diagram_nodes_too_generic', 0)}"
                ),
                (
                    "- manual_insert_required_without_editor_instruction: "
                    f"{manual_insert_missing}"
                ),
                (
                    "- source_card_display_title_too_generic: "
                    f"{source_title_generic}"
                ),
                (
                    "- overflow_notes_too_large: "
                    f"{_metric_flag_count(metrics, 'overflow_notes_too_large')}"
                ),
                (
                    "- chart_table_body_too_long_count: "
                    f"{metrics['chart_table_body_too_long_count']}"
                ),
                (
                    "- article_quote_missing_quote_text_count: "
                    f"{metrics['article_quote_missing_quote_text_count']}"
                ),
                "",
                "Alignment:",
                "",
                f"- proof_type_match: {metrics['proof_type_match']}",
                f"- chartability_alignment: {metrics['chartability_alignment']}",
                f"- diagramability_alignment: {metrics['diagramability_alignment']}",
                f"- source_card_alignment: {metrics['source_card_alignment']}",
                f"- risk_alignment: {metrics['risk_alignment']}",
                f"- slideability_prediction_quality: {metrics['slideability_prediction_quality']}",
                "- risk_alignment_notes:",
                *[f"  - {note}" for note in metrics["risk_alignment_notes"]],
                f"- notes: {_notes(metrics, case.warning)}",
                "",
            ]
        )
    lines.extend(
        [
            "## Interpretation",
            "",
            "- This comparison is for calibration only.",
            "- Slideability is still not a candidate rejection signal.",
            "- A good result means the hint can keep flowing into Anny input bundles.",
            "- A weak result means the rule-based slideability heuristic needs calibration.",
            (
                "- Scoring weight changes should wait until downstream visual QA "
                "linkage is better understood."
            ),
            "",
            "## Next Recommended Check",
            "",
            (
                "- Compare these results against future Anny direct slide specs, "
                "not only adapter-built specs."
            ),
            "- Track whether high diagramability reduces generic diagram-node warnings.",
            "- Consider a PPT contact sheet QA surface after rendered draft decks.",
        ]
    )
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def compare_slideability_visual_qa(
    *,
    bundles_path: Path = paths.ANNY_INPUT_BUNDLES_JSONL,
    slide_specs_dir: Path = paths.PITI_SLIDE_SPECS_DIR,
    output_path: Path = DEFAULT_OUTPUT_PATH,
    review_output_path: Path | None = DEFAULT_REVIEW_PATH,
) -> list[ComparisonCase]:
    cases = _load_cases(
        bundles_path=bundles_path,
        slide_specs_dir=slide_specs_dir,
        output_dir=output_path.parent,
    )
    _write_report(output_path, cases)
    if review_output_path is not None:
        _write_report(review_output_path, cases)
    return cases


@app.callback(invoke_without_command=True)
def main(
    bundles_path: Annotated[
        Path,
        typer.Option("--bundles", help="Anny input bundle JSONL path."),
    ] = paths.ANNY_INPUT_BUNDLES_JSONL,
    slide_specs_dir: Annotated[
        Path,
        typer.Option("--slide-specs-dir", help="Directory of Piti slide spec JSON files."),
    ] = paths.PITI_SLIDE_SPECS_DIR,
    output_path: Annotated[
        Path,
        typer.Option("--output", help="Markdown comparison report path."),
    ] = DEFAULT_OUTPUT_PATH,
    review_output_path: Annotated[
        Path | None,
        typer.Option(
            "--review-output",
            help="Optional GitHub-visible Markdown mirror path.",
        ),
    ] = DEFAULT_REVIEW_PATH,
) -> None:
    """Write a review-only slideability vs Piti visual QA comparison report."""
    try:
        cases = compare_slideability_visual_qa(
            bundles_path=bundles_path,
            slide_specs_dir=slide_specs_dir,
            output_path=output_path,
            review_output_path=review_output_path,
        )
    except (OSError, ValueError, json.JSONDecodeError) as error:
        console.print(f"[red]{error}[/red]")
        raise typer.Exit(1) from error
    console.print(
        "[green]Wrote slideability vs visual QA comparison for "
        f"{len(cases)} case(s) to {output_path}.[/green]"
    )


if __name__ == "__main__":
    app()
