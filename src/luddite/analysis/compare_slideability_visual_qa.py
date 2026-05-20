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
DEFAULT_DIRECT_OUTPUT_ROOT = (
    paths.MODEL_DRY_RUNS_DIR / "anny_slide_spec_experiments_live"
)

CHART_TYPES = {"chart", "table"}
QUALITY_RANK = {"weak": 1, "mixed": 2, "good": 3}
DirectArtifacts = tuple[
    dict[str, Any] | None,
    Path | None,
    VisualQaDeck | None,
    dict[str, Any] | None,
    str | None,
]


@dataclass(frozen=True)
class ComparisonCase:
    story_seed_title: str
    case_id: str
    adapter_deck_id: str
    bundle: dict[str, Any] | None
    adapter_slide_spec: dict[str, Any] | None
    adapter_slide_spec_path: Path | None
    adapter_visual_qa_deck: VisualQaDeck | None
    adapter_warning: str | None = None
    direct_slide_spec: dict[str, Any] | None = None
    direct_slide_spec_path: Path | None = None
    direct_visual_qa_deck: VisualQaDeck | None = None
    direct_manifest: dict[str, Any] | None = None
    direct_warning: str | None = None


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


def _manifest_bool(manifest: dict[str, Any] | None, key: str, fallback: bool) -> bool:
    if manifest is None or key not in manifest:
        return fallback
    return bool(manifest.get(key))


def _manifest_value(manifest: dict[str, Any] | None, key: str, fallback: Any) -> Any:
    if manifest is None or key not in manifest:
        return fallback
    return manifest.get(key)


def _manifest_delta_value(manifest: dict[str, Any] | None, key: str, fallback: Any) -> Any:
    if manifest is None:
        return fallback
    deltas = manifest.get("comparison_deltas")
    if not isinstance(deltas, dict) or key not in deltas:
        return fallback
    return deltas.get(key)


def _spec_metrics(
    *,
    bundle: dict[str, Any] | None,
    slide_spec: dict[str, Any] | None,
    visual_qa_deck: VisualQaDeck | None,
    manifest: dict[str, Any] | None = None,
) -> dict[str, Any]:
    hint = _visual_hint(bundle)
    predicted = [str(item) for item in _as_list(hint.get("likely_proof_object_types"))]
    visual_risks = [str(item) for item in _as_list(hint.get("visual_risks"))]
    proof_counts = _proof_object_type_counts(slide_spec)
    flag_counts = _flag_counts(visual_qa_deck)
    severity_counts = _severity_counts(visual_qa_deck)
    proof_match = _proof_type_match(predicted, proof_counts)
    diagram_alignment = _diagramability_alignment(predicted, proof_counts, flag_counts)
    risk_alignment, risk_notes = _risk_alignment(
        visual_risks,
        spec=slide_spec,
        counts=proof_counts,
    )
    quality = _prediction_quality(proof_match, risk_alignment, diagram_alignment)
    chart_body_slides = _chart_table_body_too_long_slides(slide_spec)
    quote_missing_slides = _article_quote_missing_quote_text_slides(slide_spec)
    schema_valid = (
        validate_with_schema(slide_spec, "piti_slide_spec_schema.json") == []
        if slide_spec
        else False
    )
    section_mapping_complete = _section_mapping_complete(slide_spec)
    return {
        "hint": hint,
        "predicted_proof_types": predicted,
        "visual_risks": visual_risks,
        "proof_counts": proof_counts,
        "flag_counts": flag_counts,
        "severity_counts": severity_counts,
        "slide_count": len(_slides(slide_spec)),
        "section_count": len(_sections(slide_spec)),
        "diagram_count": proof_counts.get("diagram", 0),
        "chart_table_count": proof_counts.get("chart", 0) + proof_counts.get("table", 0),
        "source_card_count": proof_counts.get("source_card", 0),
        "article_quote_count": proof_counts.get("article_quote", 0),
        "text_only_count": proof_counts.get("none", 0),
        "needs_fact_check_count": _needs_fact_check_count(slide_spec),
        "required_before_broadcast_count": _required_before_broadcast_count(slide_spec),
        "source_refs_count": _source_refs_count(slide_spec),
        "do_not_claim_count": _do_not_claim_count(slide_spec),
        "chart_table_body_too_long_count": len(chart_body_slides),
        "chart_table_body_too_long_slides": chart_body_slides,
        "article_quote_missing_quote_text_count": len(quote_missing_slides),
        "article_quote_missing_quote_text_slides": quote_missing_slides,
        "section_mapping_complete": _manifest_bool(
            manifest,
            "section_mapping_complete",
            section_mapping_complete,
        ),
        "schema_valid": _manifest_bool(manifest, "schema_valid", schema_valid),
        "render_passed": _manifest_value(manifest, "render_passed", "not_evaluated"),
        "safety_regression_detected": _manifest_delta_value(
            manifest,
            "safety_regression_detected",
            "not_evaluated",
        ),
        "experiment_outcome": _manifest_value(manifest, "experiment_outcome", "-"),
        "source_hallucination_count": _manifest_value(
            manifest,
            "source_hallucination_count",
            0,
        ),
        "do_not_claim_violation_count": _manifest_value(
            manifest,
            "do_not_claim_violation_count",
            0,
        ),
        "unsupported_claim_count": _manifest_value(manifest, "unsupported_claim_count", 0),
        "visible_url_count": _manifest_value(manifest, "visible_url_count", 0),
        "proof_type_match": proof_match,
        "chartability_alignment": _chartability_alignment(predicted, proof_counts),
        "diagramability_alignment": diagram_alignment,
        "source_card_alignment": _source_card_alignment(predicted, proof_counts),
        "risk_alignment": risk_alignment,
        "risk_alignment_notes": risk_notes,
        "slideability_prediction_quality": quality,
    }


def _case_metrics(case: ComparisonCase) -> dict[str, Any]:
    return _spec_metrics(
        bundle=case.bundle,
        slide_spec=case.adapter_slide_spec,
        visual_qa_deck=case.adapter_visual_qa_deck,
    )


def _direct_metrics(case: ComparisonCase) -> dict[str, Any] | None:
    if case.direct_slide_spec is None and case.direct_visual_qa_deck is None:
        return None
    return _spec_metrics(
        bundle=case.bundle,
        slide_spec=case.direct_slide_spec,
        visual_qa_deck=case.direct_visual_qa_deck,
        manifest=case.direct_manifest,
    )


def _bundle_by_title(bundles: list[dict[str, Any]]) -> dict[str, dict[str, Any]]:
    return {str(bundle.get("story_seed_title") or ""): bundle for bundle in bundles}


def _case_id_from_adapter_path(path: Path) -> str:
    stem = path.stem
    suffix = "_slide_spec"
    if stem.endswith(suffix):
        return stem[: -len(suffix)]
    return stem


def _load_direct_artifacts(
    *,
    case_id: str,
    direct_run_root: Path,
    output_dir: Path,
) -> DirectArtifacts:
    if not direct_run_root.exists():
        return (
            None,
            None,
            None,
            None,
            f"Direct run root not found: {_display_path(direct_run_root)}",
        )
    case_dir = direct_run_root / case_id
    parsed_path = case_dir / "parsed_piti_slide_spec.json"
    manifest_path = case_dir / "manifest.json"
    if not parsed_path.exists():
        return (
            None,
            parsed_path,
            None,
            None,
            f"Direct slide spec not found: {_display_path(parsed_path)}",
        )
    try:
        spec = _load_json(parsed_path)
    except (OSError, ValueError, json.JSONDecodeError) as error:
        return None, parsed_path, None, None, str(error)
    manifest: dict[str, Any] | None = None
    if manifest_path.exists():
        try:
            manifest = _load_json(manifest_path)
        except (OSError, ValueError, json.JSONDecodeError) as error:
            manifest = None
            warning = f"Direct manifest unreadable: {error}"
        else:
            warning = None
    else:
        warning = f"Direct manifest not found: {_display_path(manifest_path)}"
    deck = evaluate_slide_spec(parsed_path, spec, output_dir / "direct")
    return spec, parsed_path, deck, manifest, warning


def _load_cases(
    *,
    bundles_path: Path,
    slide_specs_dir: Path,
    output_dir: Path,
    include_direct: bool,
    direct_run_root: Path,
) -> list[ComparisonCase]:
    bundles = read_jsonl(bundles_path) if bundles_path.exists() else []
    bundles_by_title = _bundle_by_title(bundles)
    cases: list[ComparisonCase] = []
    if not slide_specs_dir.exists():
        return [
            ComparisonCase(
                story_seed_title="missing_slide_specs",
                case_id="missing_slide_specs",
                adapter_deck_id="missing_slide_specs",
                bundle=None,
                adapter_slide_spec=None,
                adapter_slide_spec_path=None,
                adapter_visual_qa_deck=None,
                adapter_warning=f"Slide spec directory not found: {slide_specs_dir}",
            )
        ]
    for path in sorted(slide_specs_dir.glob("*.json")):
        case_id = _case_id_from_adapter_path(path)
        try:
            spec = _load_json(path)
        except (OSError, ValueError, json.JSONDecodeError) as error:
            cases.append(
                ComparisonCase(
                    story_seed_title=path.stem,
                    case_id=case_id,
                    adapter_deck_id=path.stem,
                    bundle=None,
                    adapter_slide_spec=None,
                    adapter_slide_spec_path=path,
                    adapter_visual_qa_deck=None,
                    adapter_warning=str(error),
                )
            )
            continue
        title = str(spec.get("story_seed_title") or path.stem)
        deck_id = str(spec.get("deck_id") or path.stem)
        deck = evaluate_slide_spec(path, spec, output_dir / "adapter")
        direct_spec = None
        direct_path = None
        direct_deck = None
        direct_manifest = None
        direct_warning = None
        if include_direct:
            (
                direct_spec,
                direct_path,
                direct_deck,
                direct_manifest,
                direct_warning,
            ) = _load_direct_artifacts(
                case_id=case_id,
                direct_run_root=direct_run_root,
                output_dir=output_dir,
            )
        cases.append(
            ComparisonCase(
                story_seed_title=title,
                case_id=case_id,
                adapter_deck_id=deck_id,
                bundle=bundles_by_title.get(title),
                adapter_slide_spec=spec,
                adapter_slide_spec_path=path,
                adapter_visual_qa_deck=deck,
                adapter_warning=(
                    None if title in bundles_by_title else "No matching Anny input bundle."
                ),
                direct_slide_spec=direct_spec,
                direct_slide_spec_path=direct_path,
                direct_visual_qa_deck=direct_deck,
                direct_manifest=direct_manifest,
                direct_warning=direct_warning,
            )
        )
    if not cases:
        cases.append(
            ComparisonCase(
                story_seed_title="missing_slide_specs",
                case_id="missing_slide_specs",
                adapter_deck_id="missing_slide_specs",
                bundle=None,
                adapter_slide_spec=None,
                adapter_slide_spec_path=None,
                adapter_visual_qa_deck=None,
                adapter_warning=f"No slide spec JSON files found in: {slide_specs_dir}",
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


def _bool_text(value: Any) -> str:
    if isinstance(value, bool):
        return str(value).lower()
    return str(value)


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
    if metrics["diagramability_alignment"] == "hit":
        notes.append("Diagram was used without generic-node warnings.")
    if metrics["risk_alignment"] == "good":
        notes.append("Visual risks align with retained source/fact-check caution.")
    elif metrics["risk_alignment"] == "mixed":
        notes.append("Some visual risks align with downstream caution, but not all.")
    return " ".join(notes)


def _delta(direct: dict[str, Any] | None, adapter: dict[str, Any], key: str) -> str:
    if direct is None:
        return "-"
    direct_value = direct.get(key)
    adapter_value = adapter.get(key)
    if not isinstance(direct_value, int) or not isinstance(adapter_value, int):
        return "-"
    delta = direct_value - adapter_value
    return f"{delta:+d}"


def _quality_improved(
    direct: dict[str, Any] | None,
    adapter: dict[str, Any],
) -> bool | None:
    if direct is None:
        return None
    direct_quality = str(direct.get("slideability_prediction_quality"))
    adapter_quality = str(adapter.get("slideability_prediction_quality"))
    return QUALITY_RANK.get(direct_quality, 0) > QUALITY_RANK.get(adapter_quality, 0)


def _preserved_predicted_types(
    direct: dict[str, Any] | None,
    predicted: list[str],
) -> bool | None:
    if direct is None:
        return None
    if not predicted:
        return False
    actual = _actual_visual_types(direct["proof_counts"])
    return all(proof_type in actual for proof_type in predicted)


def _direct_summary_metrics(
    direct: dict[str, Any] | None,
    adapter: dict[str, Any],
) -> dict[str, Any]:
    if direct is None:
        return {
            "direct_vs_adapter_delta": "-",
            "did_direct_reduce_diagram_generic": "-",
            "did_direct_preserve_predicted_proof_types": "-",
            "did_direct_preserve_visual_risks": "-",
            "did_direct_improve_prediction_quality": "-",
        }
    adapter_generic = _metric_flag_count(adapter, "diagram_nodes_too_generic")
    direct_generic = _metric_flag_count(direct, "diagram_nodes_too_generic")
    predicted = adapter["predicted_proof_types"]
    return {
        "direct_vs_adapter_delta": (
            "diagram_nodes_too_generic "
            f"{direct_generic - adapter_generic:+d}; "
            f"review {_delta(direct, adapter, 'review_count')}"
        ),
        "did_direct_reduce_diagram_generic": direct_generic < adapter_generic,
        "did_direct_preserve_predicted_proof_types": _preserved_predicted_types(
            direct,
            predicted,
        ),
        "did_direct_preserve_visual_risks": direct["risk_alignment"]
        in {"good", "not_applicable"},
        "did_direct_improve_prediction_quality": _quality_improved(direct, adapter),
    }


def _with_review_count(metrics: dict[str, Any]) -> dict[str, Any]:
    metrics["review_count"] = int(metrics["severity_counts"].get("REVIEW", 0))
    metrics["info_count"] = int(metrics["severity_counts"].get("INFO", 0))
    return metrics


def _case_metric_bundle(
    case: ComparisonCase,
) -> tuple[dict[str, Any], dict[str, Any] | None, dict[str, Any]]:
    adapter = _with_review_count(_case_metrics(case))
    direct = _direct_metrics(case)
    if direct is not None:
        direct = _with_review_count(direct)
    direct_summary = _direct_summary_metrics(direct, adapter)
    return adapter, direct, direct_summary


def _alignment_lines(prefix: str, metrics: dict[str, Any]) -> list[str]:
    return [
        f"- {prefix}_proof_type_match: {metrics['proof_type_match']}",
        f"- {prefix}_chartability_alignment: {metrics['chartability_alignment']}",
        f"- {prefix}_diagramability_alignment: {metrics['diagramability_alignment']}",
        f"- {prefix}_source_card_alignment: {metrics['source_card_alignment']}",
        f"- {prefix}_risk_alignment: {metrics['risk_alignment']}",
        (
            f"- {prefix}_slideability_prediction_quality: "
            f"{metrics['slideability_prediction_quality']}"
        ),
    ]


def _spec_detail_lines(
    *,
    label: str,
    path: Path | None,
    metrics: dict[str, Any],
) -> list[str]:
    manual_insert_missing = _metric_flag_count(
        metrics,
        "manual_insert_required_without_editor_instruction",
    )
    source_title_generic = _metric_flag_count(
        metrics,
        "source_card_display_title_too_generic",
    )
    return [
        f"{label} slide spec side:",
        "",
        f"- slide spec: {_display_path(path)}",
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
        f"{label} visual QA / contract side:",
        "",
        f"- schema_valid: {_bool_text(metrics['schema_valid'])}",
        f"- render_passed: {_bool_text(metrics['render_passed'])}",
        f"- section_mapping_complete: {_bool_text(metrics['section_mapping_complete'])}",
        f"- safety_regression_detected: {_bool_text(metrics['safety_regression_detected'])}",
        f"- experiment_outcome: {metrics['experiment_outcome']}",
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
        f"{label} alignment:",
        "",
        *_alignment_lines(label.lower().replace(" ", "_"), metrics),
        "- risk_alignment_notes:",
        *[f"  - {note}" for note in metrics["risk_alignment_notes"]],
    ]


def _write_report(
    path: Path,
    cases: list[ComparisonCase],
    *,
    include_direct: bool,
    direct_run_id: str | None,
    direct_run_root: Path,
) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    case_metrics = [(case, *_case_metric_bundle(case)) for case in cases]
    adapter_quality_counts = Counter(
        adapter["slideability_prediction_quality"] for _, adapter, _, _ in case_metrics
    )
    direct_quality_counts = Counter(
        direct["slideability_prediction_quality"]
        for _, _, direct, _ in case_metrics
        if direct is not None
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
        f"- Direct comparison enabled: {str(include_direct).lower()}",
        f"- direct_run_id: {direct_run_id or '-'}",
        f"- direct_run_root: {_display_path(direct_run_root) if include_direct else '-'}",
        "",
        "## Summary",
        "",
        f"- compared cases: {len(case_metrics)}",
        *[
            f"- adapter_slideability_prediction_quality {quality}: {count}"
            for quality, count in sorted(adapter_quality_counts.items())
        ],
        *[
            f"- direct_slideability_prediction_quality {quality}: {count}"
            for quality, count in sorted(direct_quality_counts.items())
        ],
        "",
        "## Case Alignment",
        "",
        (
            "| case | predicted proof types | adapter proof counts | "
            "adapter diagramability | direct proof counts | direct diagramability | "
            "direct delta | adapter risk | direct risk | adapter quality | "
            "direct quality | notes |"
        ),
        "|---|---|---|---|---|---|---|---|---|---|---|---|",
    ]
    for case, adapter, direct, direct_summary in case_metrics:
        direct_counts = _counter_text(direct["proof_counts"]) if direct else "-"
        direct_diagram = direct["diagramability_alignment"] if direct else "-"
        direct_risk = direct["risk_alignment"] if direct else "-"
        direct_quality = direct["slideability_prediction_quality"] if direct else "-"
        notes = _notes(adapter, case.adapter_warning)
        if direct is not None:
            notes += " Direct: " + _notes(direct, case.direct_warning)
        elif case.direct_warning:
            notes += f" Direct: {case.direct_warning}"
        lines.append(
            f"| {_markdown_cell(case.story_seed_title)} | "
            f"{_markdown_cell(_list_text(adapter['predicted_proof_types']))} | "
            f"{_markdown_cell(_counter_text(adapter['proof_counts']))} | "
            f"{adapter['diagramability_alignment']} | "
            f"{_markdown_cell(direct_counts)} | "
            f"{direct_diagram} | "
            f"{_markdown_cell(direct_summary['direct_vs_adapter_delta'])} | "
            f"{adapter['risk_alignment']} | "
            f"{direct_risk} | "
            f"{adapter['slideability_prediction_quality']} | "
            f"{direct_quality} | "
            f"{_markdown_cell(notes)} |"
        )
    lines.extend(["", "## Case Details", ""])
    for case, adapter, direct, direct_summary in case_metrics:
        hint = adapter["hint"]
        lines.extend(
            [
                f"### {case.story_seed_title}",
                "",
                "Jibi / Anny input side:",
                "",
                f"- case_id: {case.case_id}",
                f"- deck_id: {case.adapter_deck_id}",
                f"- input bundle matched: {str(case.bundle is not None).lower()}",
                f"- slideability_score: {hint.get('slideability_score', '-')}",
                f"- visualizability: {hint.get('visualizability', '-')}",
                f"- first_slide_idea: {hint.get('first_slide_idea', '-')}",
                f"- likely_proof_object_types: {_list_text(adapter['predicted_proof_types'])}",
                f"- visual_risks: {_list_text(adapter['visual_risks'])}",
                f"- reason: {hint.get('reason', '-')}",
                "",
                *_spec_detail_lines(
                    label="Adapter",
                    path=case.adapter_slide_spec_path,
                    metrics=adapter,
                ),
                "",
            ]
        )
        if direct is None:
            lines.extend(
                [
                    "Direct Anny slide spec side:",
                    "",
                    f"- warning: {case.direct_warning or 'not requested'}",
                    "",
                ]
            )
        else:
            lines.extend(
                [
                    *_spec_detail_lines(
                        label="Direct",
                        path=case.direct_slide_spec_path,
                        metrics=direct,
                    ),
                    "",
                    "Direct vs adapter delta:",
                    "",
                    (
                        "- direct_vs_adapter_delta: "
                        f"{direct_summary['direct_vs_adapter_delta']}"
                    ),
                    (
                        "- did_direct_reduce_diagram_generic: "
                        f"{_bool_text(direct_summary['did_direct_reduce_diagram_generic'])}"
                    ),
                    (
                        "- did_direct_preserve_predicted_proof_types: "
                        f"{_bool_text(direct_summary['did_direct_preserve_predicted_proof_types'])}"
                    ),
                    (
                        "- did_direct_preserve_visual_risks: "
                        f"{_bool_text(direct_summary['did_direct_preserve_visual_risks'])}"
                    ),
                    (
                        "- did_direct_improve_prediction_quality: "
                        f"{_bool_text(direct_summary['did_direct_improve_prediction_quality'])}"
                    ),
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
                "- Direct Anny comparison helps separate Jibi prediction quality "
                "from adapter-built slide spec limitations."
            ),
            (
                "- Scoring weight changes should wait until downstream visual QA "
                "linkage is better understood."
            ),
            "",
            "## Next Recommended Check",
            "",
            "- Calibrate chart underprediction and diagram-quality signals.",
            "- Track whether direct Anny output keeps reducing generic diagram-node warnings.",
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
    include_direct: bool = False,
    direct_run_id: str | None = None,
    direct_output_root: Path = DEFAULT_DIRECT_OUTPUT_ROOT,
) -> list[ComparisonCase]:
    should_include_direct = include_direct or bool(direct_run_id)
    direct_run_root = (
        direct_output_root / direct_run_id if direct_run_id else direct_output_root
    )
    cases = _load_cases(
        bundles_path=bundles_path,
        slide_specs_dir=slide_specs_dir,
        output_dir=output_path.parent,
        include_direct=should_include_direct,
        direct_run_root=direct_run_root,
    )
    _write_report(
        output_path,
        cases,
        include_direct=should_include_direct,
        direct_run_id=direct_run_id,
        direct_run_root=direct_run_root,
    )
    if review_output_path is not None:
        _write_report(
            review_output_path,
            cases,
            include_direct=should_include_direct,
            direct_run_id=direct_run_id,
            direct_run_root=direct_run_root,
        )
    return cases


@app.callback(invoke_without_command=True)
def main(
    bundles_path: Annotated[
        Path,
        typer.Option("--bundles", help="Anny input bundle JSONL path."),
    ] = paths.ANNY_INPUT_BUNDLES_JSONL,
    slide_specs_dir: Annotated[
        Path,
        typer.Option("--slide-specs-dir", help="Directory of adapter Piti slide specs."),
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
    include_direct: Annotated[
        bool,
        typer.Option(
            "--include-direct/--adapter-only",
            help="Compare adapter slide specs with Anny direct slide spec output.",
        ),
    ] = False,
    direct_run_id: Annotated[
        str | None,
        typer.Option("--direct-run-id", help="Anny direct live/fixture run id."),
    ] = None,
    direct_output_root: Annotated[
        Path,
        typer.Option(
            "--direct-output-root",
            help="Root containing Anny direct run output directories.",
        ),
    ] = DEFAULT_DIRECT_OUTPUT_ROOT,
) -> None:
    """Write a review-only slideability vs Piti visual QA comparison report."""
    try:
        cases = compare_slideability_visual_qa(
            bundles_path=bundles_path,
            slide_specs_dir=slide_specs_dir,
            output_path=output_path,
            review_output_path=review_output_path,
            include_direct=include_direct,
            direct_run_id=direct_run_id,
            direct_output_root=direct_output_root,
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
