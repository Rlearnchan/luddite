"""Controlled Anny direct Piti slide spec experiment runner."""

from __future__ import annotations

import json
import shutil
from collections import Counter
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Annotated, Any

import typer
from rich.console import Console

from luddite import paths
from luddite.agents.anny.api_experiment_runner import (
    _collect_allowed_urls,
    _env_api_key,
    _env_model,
    _env_temperature,
    _run_openai_responses_api,
)
from luddite.agents.piti import render_pptx, render_visual_qa
from luddite.agents.piti.build_slide_spec_from_storyline import (
    build_piti_slide_spec_from_storyline,
    validate_piti_slide_spec,
)
from luddite.utils.urls import canonicalize_url, extract_urls

app = typer.Typer(no_args_is_help=False)
console = Console()

DEFAULT_OUTPUT_ROOT = paths.MODEL_DRY_RUNS_DIR / "anny_slide_spec_experiments"
DEFAULT_LIVE_OUTPUT_ROOT = paths.MODEL_DRY_RUNS_DIR / "anny_slide_spec_experiments_live"
DEFAULT_REVIEW_OUTPUT_DIR = paths.DOCS_DIR / "reviews" / "anny_slide_spec_experiments"
DEFAULT_LIVE_REVIEW_OUTPUT_DIR = (
    paths.DOCS_DIR / "reviews" / "anny_slide_spec_experiments_live"
)
DEFAULT_PROMPT_PATH = paths.PROMPTS_DIR / "anny" / "slide_spec_writer.md"
DEFAULT_STYLE_PROFILE_PATH = paths.STYLE_PROFILES_DIR / "syukaworld_ppt_style_profile.json"


@dataclass(frozen=True)
class SlideSpecExperimentCase:
    case_id: str
    story_seed_title: str
    input_bundle_path: Path
    evidence_pack_path: Path
    manual_storyline_path: Path
    adapter_slide_spec_path: Path


@dataclass(frozen=True)
class ConcreteDiagramFixture:
    nodes: tuple[str, str, str]
    edge_labels: tuple[str, str]


AI_SEARCH_COMPRESSION_DIAGRAM = ConcreteDiagramFixture(
    nodes=(
        "AI 즉답 서비스가 먼저 답을 제시함",
        "사용자가 검색·비교 과정을 건너뛰기 쉬워짐",
        "학교·박물관은 검증 훈련을 가르쳐야 함",
    ),
    edge_labels=("탐색 과정을 압축함", "검증 훈련을 요구함"),
)
KNOWLEDGE_INSTITUTION_ROLE_DIAGRAM = ConcreteDiagramFixture(
    nodes=(
        "AI 서비스가 기본 설명을 즉시 제공함",
        "학교·박물관의 답 제공 역할이 약해짐",
        "기관은 질문·검증 훈련을 설계해야 함",
    ),
    edge_labels=("설명 역할을 전환함", "훈련 역할을 확대함"),
)
LEARNING_VERIFICATION_DIAGRAM = ConcreteDiagramFixture(
    nodes=(
        "사용자가 AI 답을 그대로 받기 쉬움",
        "출처 비교와 검증 과정이 화면 밖으로 밀림",
        "수업은 질문과 확인 습관을 훈련해야 함",
    ),
    edge_labels=("비교 과정을 줄임", "검증 습관을 훈련함"),
)
OBSERVATORY_METHOD_DIAGRAM = ConcreteDiagramFixture(
    nodes=(
        "천문관이 별 이름 설명에 머무름",
        "AI가 기본 설명을 즉시 대체함",
        "기관은 관찰·질문하는 법을 보여줘야 함",
    ),
    edge_labels=("설명 역할을 전환함", "질문 방식을 훈련함"),
)
BANK_COLLATERAL_DIAGRAM = ConcreteDiagramFixture(
    nodes=(
        "은행은 담보 있는 대출을 선호함",
        "AI·반도체 투자는 회수 기간이 길고 담보가 약함",
        "정책금융의 위험분담 논쟁이 생김",
    ),
    edge_labels=("장기 투자와 충돌함", "위험분담을 요구함"),
)
POLICY_FINANCE_TIME_DIAGRAM = ConcreteDiagramFixture(
    nodes=(
        "정책금융이 시장보다 긴 시간을 보려 함",
        "은행은 손실 가능성을 먼저 계산함",
        "정부와 금융권의 위험분담 기준이 쟁점이 됨",
    ),
    edge_labels=("투자 시간을 늘림", "분담 기준을 요구함"),
)
GROWTH_POLICY_BOUNDARY_DIAGRAM = ConcreteDiagramFixture(
    nodes=(
        "은행은 예금자 돈을 보수적으로 운용함",
        "성장산업 투자는 실패 가능성을 안고 감",
        "정책은 좋은 위험과 보조금을 구분해야 함",
    ),
    edge_labels=("투자 위험을 드러냄", "정책 기준을 요구함"),
)
RISK_DISTRIBUTION_DIAGRAM = ConcreteDiagramFixture(
    nodes=(
        "국민성장펀드가 장기 자본을 공급함",
        "손실 가능성도 사회적으로 나뉨",
        "투자와 보조금 사이의 경계가 쟁점이 됨",
    ),
    edge_labels=("위험을 분담함", "정책 경계를 확인해야 함"),
)


CONCRETE_DIAGRAM_FIXTURES: dict[str, dict[int, ConcreteDiagramFixture]] = {
    "ai_knowledge_institution": {
        2: AI_SEARCH_COMPRESSION_DIAGRAM,
        4: AI_SEARCH_COMPRESSION_DIAGRAM,
        5: KNOWLEDGE_INSTITUTION_ROLE_DIAGRAM,
        6: LEARNING_VERIFICATION_DIAGRAM,
        8: AI_SEARCH_COMPRESSION_DIAGRAM,
        9: AI_SEARCH_COMPRESSION_DIAGRAM,
        10: LEARNING_VERIFICATION_DIAGRAM,
        12: AI_SEARCH_COMPRESSION_DIAGRAM,
        14: KNOWLEDGE_INSTITUTION_ROLE_DIAGRAM,
        15: KNOWLEDGE_INSTITUTION_ROLE_DIAGRAM,
        16: OBSERVATORY_METHOD_DIAGRAM,
        18: LEARNING_VERIFICATION_DIAGRAM,
        19: KNOWLEDGE_INSTITUTION_ROLE_DIAGRAM,
        21: LEARNING_VERIFICATION_DIAGRAM,
        22: LEARNING_VERIFICATION_DIAGRAM,
        23: OBSERVATORY_METHOD_DIAGRAM,
        25: LEARNING_VERIFICATION_DIAGRAM,
        26: LEARNING_VERIFICATION_DIAGRAM,
    },
    "productive_finance_policy": {
        3: BANK_COLLATERAL_DIAGRAM,
        4: BANK_COLLATERAL_DIAGRAM,
        5: BANK_COLLATERAL_DIAGRAM,
        9: BANK_COLLATERAL_DIAGRAM,
        10: POLICY_FINANCE_TIME_DIAGRAM,
        11: GROWTH_POLICY_BOUNDARY_DIAGRAM,
        16: GROWTH_POLICY_BOUNDARY_DIAGRAM,
        17: RISK_DISTRIBUTION_DIAGRAM,
        18: RISK_DISTRIBUTION_DIAGRAM,
        20: POLICY_FINANCE_TIME_DIAGRAM,
        22: RISK_DISTRIBUTION_DIAGRAM,
        24: RISK_DISTRIBUTION_DIAGRAM,
    },
}


EXPERIMENT_CASES = [
    SlideSpecExperimentCase(
        case_id="ai_knowledge_institution",
        story_seed_title="AI 즉답 시대의 지식기관 역할",
        input_bundle_path=(
            paths.ANNY_STORYLINE_DRY_RUN_DIR / "ai_knowledge_institution_input_bundle.json"
        ),
        evidence_pack_path=paths.ANNY_EVIDENCE_PACK_AI_KNOWLEDGE_JSON,
        manual_storyline_path=(
            paths.ANNY_STORYLINE_DRY_RUN_DIR
            / "ai_knowledge_institution_gpt_pro_storyline_enriched.json"
        ),
        adapter_slide_spec_path=(
            paths.PITI_SLIDE_SPECS_DIR / "ai_knowledge_institution_slide_spec.json"
        ),
    ),
    SlideSpecExperimentCase(
        case_id="productive_finance_policy",
        story_seed_title="생산적 금융과 정책자금 전환",
        input_bundle_path=(
            paths.ANNY_STORYLINE_DRY_RUN_DIR / "productive_finance_policy_input_bundle.json"
        ),
        evidence_pack_path=(
            paths.CANDIDATES_DIR / "anny_evidence_pack_productive_finance_policy.json"
        ),
        manual_storyline_path=(
            paths.ANNY_STORYLINE_DRY_RUN_DIR
            / "productive_finance_policy_gpt_pro_storyline_enriched.json"
        ),
        adapter_slide_spec_path=(
            paths.PITI_SLIDE_SPECS_DIR / "productive_finance_policy_slide_spec.json"
        ),
    ),
]


def _load_json(path: Path) -> Any:
    with path.open(encoding="utf-8") as source:
        return json.load(source)


def _write_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def _write_text(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


def _default_live_run_id() -> str:
    return f"live_{datetime.now(UTC).strftime('%Y%m%dT%H%M%SZ')}"


def _safe_run_id(run_id: str) -> str:
    cleaned = "".join(char if char.isalnum() or char in {"-", "_"} else "_" for char in run_id)
    return cleaned.strip("_") or _default_live_run_id()


def _display_path(path: Path) -> str:
    try:
        return str(path.resolve().relative_to(paths.REPO_ROOT))
    except ValueError:
        return str(path)


def _case_by_id(case_id: str) -> SlideSpecExperimentCase:
    for case in EXPERIMENT_CASES:
        if case.case_id == case_id:
            return case
    known = ", ".join(case.case_id for case in EXPERIMENT_CASES)
    raise ValueError(f"Unknown case_id: {case_id}. Known cases: {known}")


def _selected_cases(case_id: str) -> list[SlideSpecExperimentCase]:
    if case_id == "all":
        return EXPERIMENT_CASES
    return [_case_by_id(case_id)]


def _resolve_run_paths(
    *,
    live_api: bool,
    output_root: Path | None,
    review_output_dir: Path | None,
    run_id: str | None,
    mirror_live_review: bool,
) -> tuple[Path, Path | None, str | None]:
    if live_api:
        resolved_run_id = _safe_run_id(run_id or _default_live_run_id())
        run_root = (output_root or DEFAULT_LIVE_OUTPUT_ROOT) / resolved_run_id
        if mirror_live_review:
            review_root = review_output_dir or DEFAULT_LIVE_REVIEW_OUTPUT_DIR
            return run_root, review_root / resolved_run_id, resolved_run_id
        return run_root, None, resolved_run_id
    return output_root or DEFAULT_OUTPUT_ROOT, review_output_dir or DEFAULT_REVIEW_OUTPUT_DIR, None


def _as_list(value: Any) -> list[Any]:
    return value if isinstance(value, list) else []


def _all_slides(spec: dict[str, Any]) -> list[dict[str, Any]]:
    return [slide for slide in _as_list(spec.get("slides")) if isinstance(slide, dict)]


def _proof(slide: dict[str, Any]) -> dict[str, Any]:
    proof = slide.get("proof_object")
    return proof if isinstance(proof, dict) else {}


def _proof_type(slide: dict[str, Any]) -> str:
    return str(_proof(slide).get("type") or "none")


def _proof_type_counts(spec: dict[str, Any]) -> dict[str, int]:
    return dict(Counter(_proof_type(slide) for slide in _all_slides(spec)))


def _slide_text_fields(slide: dict[str, Any]) -> str:
    return "\n".join(
        [
            str(slide.get("screen_headline") or ""),
            *[str(item) for item in _as_list(slide.get("screen_body"))],
            *[str(item) for item in _as_list(slide.get("overflow_notes"))],
            str(slide.get("speaker_notes_expanded") or ""),
        ]
    )


def _visible_slide_text_fields(slide: dict[str, Any]) -> str:
    proof = _proof(slide)
    visible_parts = [
        str(slide.get("screen_headline") or ""),
        *[str(item) for item in _as_list(slide.get("screen_body"))],
        str(proof.get("display_title") or ""),
        str(proof.get("title") or ""),
        str(proof.get("quote_text") or ""),
        str(proof.get("quote_translation") or ""),
    ]
    for node in _as_list(proof.get("diagram_nodes")):
        visible_parts.append(str(node))
    for edge in _as_list(proof.get("diagram_edges")):
        if isinstance(edge, dict):
            visible_parts.extend(
                str(edge.get(key) or "") for key in ("from", "to", "label")
            )
    return "\n".join(visible_parts)


def _spec_text(spec: dict[str, Any]) -> str:
    return "\n".join(_slide_text_fields(slide) for slide in _all_slides(spec))


def _source_urls_from_spec(spec: dict[str, Any]) -> set[str]:
    urls: set[str] = set()
    for slide in _all_slides(spec):
        proof = _proof(slide)
        for key in ("source_url", "image_url"):
            value = proof.get(key)
            if value:
                urls.add(canonicalize_url(str(value)))
        for ref in _as_list(slide.get("source_refs")):
            if isinstance(ref, dict) and ref.get("url"):
                urls.add(canonicalize_url(str(ref["url"])))
        for url in extract_urls(_slide_text_fields(slide)):
            urls.add(canonicalize_url(url))
    return urls


def _visible_url_count(spec: dict[str, Any]) -> int:
    count = 0
    for slide in _all_slides(spec):
        visible = "\n".join(
            [
                str(slide.get("screen_headline") or ""),
                *[str(item) for item in _as_list(slide.get("screen_body"))],
            ]
        )
        count += len(extract_urls(visible))
    return count


def _do_not_claim_violations(spec: dict[str, Any], input_bundle: dict[str, Any]) -> list[str]:
    text = "\n".join(_visible_slide_text_fields(slide) for slide in _all_slides(spec))
    violations = [
        str(pattern)
        for pattern in _as_list(input_bundle.get("do_not_claim"))
        if str(pattern) and str(pattern) in text
    ]
    return list(dict.fromkeys(violations))


def _unsupported_claim_count(spec: dict[str, Any]) -> int:
    count = 0
    for slide in _all_slides(spec):
        layout = str(slide.get("layout_intent") or "")
        if layout in {"title", "section_title", "appendix_checklist"}:
            continue
        if not (slide.get("needs_fact_check") or slide.get("required_before_broadcast")):
            continue
        proof_source = str(_proof(slide).get("source_url") or "").strip()
        if not proof_source and not _as_list(slide.get("source_refs")):
            count += 1
    return count


def _screen_headline_missing_count(spec: dict[str, Any]) -> int:
    return sum(1 for slide in _all_slides(spec) if not str(slide.get("screen_headline") or ""))


def _count_bool(spec: dict[str, Any], key: str) -> int:
    return sum(1 for slide in _all_slides(spec) if slide.get(key))


def _text_only_slide_count(spec: dict[str, Any]) -> int:
    return sum(1 for slide in _all_slides(spec) if _proof_type(slide) == "none")


def _chart_table_count(spec: dict[str, Any]) -> int:
    return sum(1 for slide in _all_slides(spec) if _proof_type(slide) in {"chart", "table"})


def _slide_no(slide: dict[str, Any]) -> int:
    try:
        return int(slide.get("slide_no") or 0)
    except (TypeError, ValueError):
        return 0


def _visual_metrics(spec: dict[str, Any], *, pseudo_path: Path) -> dict[str, Any]:
    deck = render_visual_qa.evaluate_slide_spec(pseudo_path, spec, pseudo_path.parent)
    return {
        "flag_counts": dict(render_visual_qa._flag_counter([deck])),
        "severity_counts": dict(render_visual_qa._severity_counter([deck])),
        "flagged_slide_count": deck.flagged_slide_count,
        "qa_flag_count": deck.flag_count,
    }


def _spec_metrics(spec: dict[str, Any], *, pseudo_path: Path) -> dict[str, Any]:
    visual = _visual_metrics(spec, pseudo_path=pseudo_path)
    proof_counts = _proof_type_counts(spec)
    return {
        "slide_count": len(_all_slides(spec)),
        "section_count": len(_as_list(spec.get("sections"))),
        "proof_object_type_counts": proof_counts,
        "text_only_slide_count": _text_only_slide_count(spec),
        "source_card_count": proof_counts.get("source_card", 0),
        "diagram_count": proof_counts.get("diagram", 0),
        "chart_table_count": _chart_table_count(spec),
        "needs_fact_check_count": _count_bool(spec, "needs_fact_check"),
        "required_before_broadcast_count": _count_bool(spec, "required_before_broadcast"),
        "visible_url_count": _visible_url_count(spec),
        "visual_qa_flag_counts": visual["flag_counts"],
        "severity_counts": visual["severity_counts"],
        "diagram_nodes_too_generic": visual["flag_counts"].get(
            "diagram_nodes_too_generic",
            0,
        ),
        "manual_insert_required_without_editor_instruction": visual["flag_counts"].get(
            "manual_insert_required_without_editor_instruction",
            0,
        ),
        "source_card_display_title_too_generic": visual["flag_counts"].get(
            "source_card_display_title_too_generic",
            0,
        ),
        "overflow_notes_too_large": visual["flag_counts"].get("overflow_notes_too_large", 0),
    }


def _metric_delta(direct_metrics: dict[str, Any], adapter_metrics: dict[str, Any], key: str) -> int:
    return int(direct_metrics.get(key, 0) or 0) - int(adapter_metrics.get(key, 0) or 0)


def _severity_delta(
    direct_metrics: dict[str, Any],
    adapter_metrics: dict[str, Any],
    severity: str,
) -> int:
    direct_counts = direct_metrics.get("severity_counts", {})
    adapter_counts = adapter_metrics.get("severity_counts", {})
    return int(direct_counts.get(severity, 0) or 0) - int(
        adapter_counts.get(severity, 0) or 0
    )


def _response_usage(response_payload: dict[str, Any]) -> dict[str, Any]:
    usage = response_payload.get("usage")
    return usage if isinstance(usage, dict) else {}


def _safety_regression_detected(
    *,
    manifest: dict[str, Any],
    visible_url_delta: int,
) -> bool:
    return bool(
        manifest.get("source_hallucination_count", 0)
        or manifest.get("do_not_claim_violation_count", 0)
        or manifest.get("unsupported_claim_count", 0)
        or manifest.get("needs_fact_check_removed_too_aggressively", False)
        or manifest.get("required_before_broadcast_removed_too_aggressively", False)
        or manifest.get("visible_url_count", 0)
        or visible_url_delta > 0
    )


def _experiment_outcome(
    *,
    manifest: dict[str, Any],
    deltas: dict[str, Any],
) -> str:
    if (
        manifest.get("parse_status") != "parsed"
        or not manifest.get("schema_valid")
        or not manifest.get("render_passed")
        or deltas.get("safety_regression_detected")
    ):
        return "failure"
    if deltas.get("diagram_quality_improved"):
        return "success"
    return "partial_success"


def build_slide_spec_experiment_prompt(
    *,
    input_bundle: dict[str, Any],
    evidence_pack: dict[str, Any],
    manual_storyline: dict[str, Any],
    schema: dict[str, Any],
    visual_qa_summary: str,
    allowed_urls: set[str],
) -> str:
    base_prompt = (
        DEFAULT_PROMPT_PATH.read_text(encoding="utf-8")
        if DEFAULT_PROMPT_PATH.exists()
        else "# Anny Direct Piti Slide Spec Writer"
    )
    return "\n\n".join(
        [
            base_prompt,
            "## Controlled Experiment Wrapper",
            "This is a controlled experiment, not a production Anny agent.",
            "Return JSON only. Do not browse. Do not call tools. Do not invent sources.",
            "The output must satisfy specs/piti_slide_spec_schema.json.",
            "Piti will render this contract without re-inferring or rewriting meaning.",
            "Separate broadcast screen copy from notes.",
            "screen_headline must be broadcast-facing.",
            "screen_body must be short; move explanation, evidence, and caution to notes.",
            "Use speaker_notes_expanded or overflow_notes for long reasoning.",
            "Every slide must provide an explicit proof_object.",
            (
                "proof_object.type should be one of diagram, chart, table, source_card, "
                "article_quote, or none."
            ),
            "Do not expose source URLs on screen; preserve them in source_refs or notes.",
            "Keep needs_source, needs_fact_check, and required_before_broadcast conservative.",
            "Do not make unchecked claims as screen copy.",
            "Do not violate do_not_claim.",
            "Include counterpoint or opposing questions when the topic requires it.",
            "## Diagram Requirements",
            "Avoid generic nodes such as AI 즉답 -> 검증 -> 맥락.",
            "Avoid word-only nodes such as 안전한 금융 -> 성장 금융.",
            "Prefer at least 3 nodes.",
            "Use actor -> mechanism -> result structure.",
            "Use short broadcast sentences, not abstract noun placeholders.",
            "Include at least one concrete actor, institution, user, or system.",
            "Include at least one mechanism verb.",
            "Make each node imply actor/context, mechanism/change, or result/tension.",
            "Each diagram node should work as broadcast-facing box copy.",
            "Use meaningful edge labels; avoid labels like 흐름 or 연결.",
            "## Current Piti Visual QA Baseline",
            visual_qa_summary,
            "## Allowed Source URLs",
            "\n".join(f"- {url}" for url in sorted(allowed_urls)),
            "## Input Bundle JSON",
            json.dumps(input_bundle, ensure_ascii=False, indent=2),
            "## Evidence Pack JSON",
            json.dumps(evidence_pack, ensure_ascii=False, indent=2),
            "## Existing Enriched Manual Storyline JSON",
            json.dumps(manual_storyline, ensure_ascii=False, indent=2),
            "## Output Schema JSON",
            json.dumps(schema, ensure_ascii=False, indent=2),
        ]
    )


def _diagram_edges(fixture: ConcreteDiagramFixture) -> list[dict[str, str]]:
    return [
        {
            "from": fixture.nodes[0],
            "to": fixture.nodes[1],
            "label": fixture.edge_labels[0],
        },
        {
            "from": fixture.nodes[1],
            "to": fixture.nodes[2],
            "label": fixture.edge_labels[1],
        },
    ]


def _apply_concrete_diagram_fixtures(
    spec: dict[str, Any],
    *,
    case_id: str,
) -> int:
    fixtures = CONCRETE_DIAGRAM_FIXTURES.get(case_id, {})
    changed = 0
    for slide in _all_slides(spec):
        if _proof_type(slide) != "diagram":
            continue
        fixture = fixtures.get(_slide_no(slide))
        if not fixture:
            continue
        proof = _proof(slide)
        proof["diagram_nodes"] = list(fixture.nodes)
        proof["diagram_edges"] = _diagram_edges(fixture)
        proof["placeholder_reason"] = (
            "Direct fixture uses concrete actor -> mechanism -> result diagram copy."
        )
        changed += 1
    return changed


def _synthetic_fixture_output(case: SlideSpecExperimentCase) -> dict[str, Any]:
    storyline = _load_json(case.manual_storyline_path)
    spec = build_piti_slide_spec_from_storyline(
        storyline,
        deck_id=f"{case.case_id}_direct_fixture",
        source_storyline_path=case.manual_storyline_path,
    )
    changed = _apply_concrete_diagram_fixtures(spec, case_id=case.case_id)
    spec["notes"] = (
        "Synthetic fixture for Anny direct Piti slide spec experiment. "
        "This validates the direct-output harness without calling an API. "
        f"Concrete diagram fixture updates applied: {changed}; "
        "source/fact-check metadata preserved."
    )
    return spec


def _call_live_api(
    *,
    prompt: str,
    model: str | None,
    temperature: float | None,
    timeout_seconds: int,
    api_caller: Any | None,
) -> tuple[str, dict[str, Any], str, float]:
    api_key = _env_api_key()
    resolved_model = model or _env_model()
    resolved_temperature = _env_temperature() if temperature is None else temperature
    caller = api_caller or _run_openai_responses_api
    raw_text, response_payload = caller(
        api_key=api_key,
        model=resolved_model,
        prompt=prompt,
        temperature=resolved_temperature,
        timeout_seconds=timeout_seconds,
    )
    return raw_text, response_payload, resolved_model, resolved_temperature


def _validate_raw_slide_spec(
    *,
    raw_path: Path,
    parsed_path: Path,
    input_bundle: dict[str, Any],
    evidence_pack: dict[str, Any],
    manual_storyline: dict[str, Any],
    adapter_spec: dict[str, Any],
    render_output_path: Path,
    pseudo_path: Path,
) -> tuple[dict[str, Any] | None, dict[str, Any], dict[str, Any] | None]:
    raw_text = raw_path.read_text(encoding="utf-8")
    failure_modes: list[str] = []
    try:
        parsed = json.loads(raw_text)
    except json.JSONDecodeError as exc:
        manifest = {
            "parse_status": f"invalid_json:{exc.msg}",
            "schema_valid": False,
            "validation_passed": False,
            "render_passed": False,
            "failure_modes": ["invalid_json"],
            "ready_for_production_anny_agent": False,
            "ready_for_production_piti_agent": False,
            "ready_for_broadcast": False,
        }
        return None, manifest, None
    if not isinstance(parsed, dict):
        manifest = {
            "parse_status": "invalid_json:not_object",
            "schema_valid": False,
            "validation_passed": False,
            "render_passed": False,
            "failure_modes": ["invalid_json"],
            "ready_for_production_anny_agent": False,
            "ready_for_production_piti_agent": False,
            "ready_for_broadcast": False,
        }
        return None, manifest, None
    _write_json(parsed_path, parsed)
    validation = validate_piti_slide_spec(parsed)
    if not validation.get("schema_valid"):
        failure_modes.append("schema_error")
    allowed_urls = _collect_allowed_urls(input_bundle, evidence_pack, manual_storyline)
    used_urls = _source_urls_from_spec(parsed)
    hallucinated_urls = sorted(used_urls - allowed_urls)
    if hallucinated_urls:
        failure_modes.append("source_hallucination")
    do_not_claim_violations = _do_not_claim_violations(parsed, input_bundle)
    if do_not_claim_violations:
        failure_modes.append("do_not_claim_violation")
    unsupported_claim_count = _unsupported_claim_count(parsed)
    if unsupported_claim_count:
        failure_modes.append("unsupported_claim")
    adapter_needs_fact_check = _count_bool(adapter_spec, "needs_fact_check")
    direct_needs_fact_check = _count_bool(parsed, "needs_fact_check")
    needs_fact_check_removed = direct_needs_fact_check < adapter_needs_fact_check
    if needs_fact_check_removed:
        failure_modes.append("needs_fact_check_removed_too_aggressively")
    adapter_required = _count_bool(adapter_spec, "required_before_broadcast")
    direct_required = _count_bool(parsed, "required_before_broadcast")
    required_removed = direct_required < adapter_required
    if required_removed:
        failure_modes.append("required_before_broadcast_removed_too_aggressively")
    headline_missing_count = _screen_headline_missing_count(parsed)
    if headline_missing_count:
        failure_modes.append("screen_headline_missing")
    style = render_pptx.load_style_profile(DEFAULT_STYLE_PROFILE_PATH)
    render_result = render_pptx.render_slide_spec_to_pptx(
        parsed,
        render_output_path,
        style_profile=style,
    )
    if not render_result.get("passed"):
        failure_modes.append("piti_render_failed")
    visual_metrics = _visual_metrics(parsed, pseudo_path=pseudo_path)
    severity_counts = visual_metrics["severity_counts"]
    if severity_counts.get("BLOCKER", 0):
        failure_modes.append("visual_qa_blocker")
    manifest = {
        "parse_status": "parsed",
        "schema_valid": validation.get("schema_valid"),
        "validation_passed": validation.get("passed"),
        "render_passed": render_result.get("passed", False),
        "schema_errors": validation.get("schema_errors", []),
        "slide_spec_issues": validation.get("issues", []),
        "slide_spec_warnings": validation.get("warnings", []),
        "failure_modes": list(dict.fromkeys(failure_modes)),
        "source_hallucination_count": len(hallucinated_urls),
        "hallucinated_urls": hallucinated_urls,
        "do_not_claim_violation_count": len(do_not_claim_violations),
        "do_not_claim_violations": do_not_claim_violations,
        "unsupported_claim_count": unsupported_claim_count,
        "needs_fact_check_removed_too_aggressively": needs_fact_check_removed,
        "required_before_broadcast_removed_too_aggressively": required_removed,
        "screen_headline_missing_count": headline_missing_count,
        "visible_url_count": render_result.get("visible_url_count", 0),
        "source_card_repeated_headline_count": render_result.get(
            "source_card_repeated_headline_count",
            0,
        ),
        "proof_text_overlap_count": render_result.get("proof_text_overlap_count", 0),
        "chart_body_text_leak_count": render_result.get("chart_body_text_leak_count", 0),
        "screen_body_explanatory_sentence_count": render_result.get(
            "screen_body_explanatory_sentence_count",
            0,
        ),
        "visual_qa_flag_counts": visual_metrics["flag_counts"],
        "visual_qa_severity_counts": severity_counts,
        "ready_for_piti_renderer_contract": True,
        "ready_for_api_experiment": True,
        "ready_for_production_anny_agent": False,
        "ready_for_production_piti_agent": False,
        "ready_for_broadcast": False,
    }
    return parsed, manifest, render_result


def _write_validation_report(
    *,
    path: Path,
    case: SlideSpecExperimentCase,
    manifest: dict[str, Any],
    raw_path: Path,
    parsed_path: Path,
    render_result: dict[str, Any] | None,
    mode: str,
) -> None:
    lines = [
        f"# Anny Direct Piti Slide Spec Validation: {case.case_id}",
        "",
        f"- generated_at: {datetime.now(UTC).isoformat()}",
        f"- mode: {mode}",
        f"- raw_model_output: {_display_path(raw_path)}",
        f"- parsed_piti_slide_spec: {_display_path(parsed_path) if parsed_path.exists() else None}",
        f"- parse_status: {manifest.get('parse_status')}",
        f"- schema_valid: {manifest.get('schema_valid')}",
        f"- validation_passed: {manifest.get('validation_passed')}",
        f"- render_passed: {manifest.get('render_passed', False)}",
        f"- failure_modes: {manifest.get('failure_modes', [])}",
        f"- source_hallucination_count: {manifest.get('source_hallucination_count', 0)}",
        f"- do_not_claim_violation_count: {manifest.get('do_not_claim_violation_count', 0)}",
        f"- unsupported_claim_count: {manifest.get('unsupported_claim_count', 0)}",
        (
            "- needs_fact_check_removed_too_aggressively: "
            f"{manifest.get('needs_fact_check_removed_too_aggressively', False)}"
        ),
        (
            "- required_before_broadcast_removed_too_aggressively: "
            f"{manifest.get('required_before_broadcast_removed_too_aggressively', False)}"
        ),
        f"- visible_url_count: {manifest.get('visible_url_count', 0)}",
        (
            "- source_card_repeated_headline_count: "
            f"{manifest.get('source_card_repeated_headline_count', 0)}"
        ),
        f"- proof_text_overlap_count: {manifest.get('proof_text_overlap_count', 0)}",
        f"- chart_body_text_leak_count: {manifest.get('chart_body_text_leak_count', 0)}",
        (
            "- screen_body_explanatory_sentence_count: "
            f"{manifest.get('screen_body_explanatory_sentence_count', 0)}"
        ),
        f"- visual_qa_severity_counts: {manifest.get('visual_qa_severity_counts', {})}",
        "- QA flags are warning-only.",
        "- ready_for_production_anny_agent: false",
        "- ready_for_production_piti_agent: false",
        "- ready_for_broadcast: false",
        "",
        "## Render Result",
        "",
        f"- rendered: {bool(render_result)}",
        f"- render_passed: {render_result.get('passed') if render_result else False}",
        f"- output_pptx_path: {render_result.get('output_pptx_path') if render_result else None}",
        "",
        "## Slide Spec Issues",
        "",
    ]
    issues = manifest.get("slide_spec_issues", [])
    lines.extend(f"- {issue}" for issue in issues) if issues else lines.append("- none")
    lines.extend(["", "## Visual QA Flag Counts", ""])
    flag_counts = manifest.get("visual_qa_flag_counts", {})
    lines.extend(f"- {flag}: {count}" for flag, count in sorted(flag_counts.items()))
    if not flag_counts:
        lines.append("- none")
    _write_text(path, "\n".join(lines) + "\n")


def _write_comparison_report(
    *,
    path: Path,
    case: SlideSpecExperimentCase,
    adapter_spec: dict[str, Any],
    direct_spec: dict[str, Any] | None,
    direct_manifest: dict[str, Any],
) -> dict[str, Any]:
    adapter_metrics = _spec_metrics(
        adapter_spec,
        pseudo_path=case.adapter_slide_spec_path,
    )
    direct_metrics = (
        _spec_metrics(direct_spec, pseudo_path=path.with_suffix(".direct.json"))
        if direct_spec
        else {}
    )
    direct_flags = direct_metrics.get("visual_qa_flag_counts", {})
    adapter_flags = adapter_metrics.get("visual_qa_flag_counts", {})
    if direct_metrics:
        diagram_delta = direct_flags.get("diagram_nodes_too_generic", 0) - adapter_flags.get(
            "diagram_nodes_too_generic",
            0,
        )
        manual_delta = direct_flags.get(
            "manual_insert_required_without_editor_instruction",
            0,
        ) - adapter_flags.get("manual_insert_required_without_editor_instruction", 0)
        source_title_delta = direct_flags.get("source_card_display_title_too_generic", 0) - (
            adapter_flags.get("source_card_display_title_too_generic", 0)
        )
        overflow_delta = direct_flags.get("overflow_notes_too_large", 0) - adapter_flags.get(
            "overflow_notes_too_large",
            0,
        )
        review_delta = _severity_delta(direct_metrics, adapter_metrics, "REVIEW")
        info_delta = _severity_delta(direct_metrics, adapter_metrics, "INFO")
        visible_url_delta = _metric_delta(direct_metrics, adapter_metrics, "visible_url_count")
    else:
        diagram_delta = 0
        manual_delta = 0
        source_title_delta = 0
        overflow_delta = 0
        review_delta = 0
        info_delta = 0
        visible_url_delta = 0
    safety_regression_detected = _safety_regression_detected(
        manifest=direct_manifest,
        visible_url_delta=visible_url_delta,
    )
    schema_render_ok = bool(
        direct_spec
        and direct_manifest.get("schema_valid")
        and direct_manifest.get("render_passed")
    )
    diagram_quality_improved = bool(
        schema_render_ok and diagram_delta < 0 and not safety_regression_detected
    )
    deltas = {
        "diagram_nodes_too_generic_delta": diagram_delta,
        "manual_insert_required_without_editor_instruction_delta": manual_delta,
        "source_card_display_title_too_generic_delta": source_title_delta,
        "overflow_notes_too_large_delta": overflow_delta,
        "visual_qa_review_delta": review_delta,
        "visual_qa_info_delta": info_delta,
        "visible_url_count_delta": visible_url_delta,
        "safety_regression_detected": safety_regression_detected,
        "diagram_quality_improved": diagram_quality_improved,
    }
    outcome = _experiment_outcome(manifest=direct_manifest, deltas=deltas)
    improvements: list[str] = []
    regressions: list[str] = []
    if diagram_delta < 0:
        improvements.append("diagram_nodes_too_generic decreased")
    elif diagram_delta > 0:
        regressions.append("diagram_nodes_too_generic increased")
    if manual_delta <= 0:
        improvements.append("manual insert instruction warnings did not increase")
    else:
        regressions.append("manual insert instruction warnings increased")
    if source_title_delta <= 0:
        improvements.append("source card generic title warnings did not increase")
    else:
        regressions.append("source card generic title warnings increased")
    if safety_regression_detected:
        regressions.append("safety regression detected")
    else:
        improvements.append("no source/fact-check safety regression detected")
    if direct_manifest.get("failure_modes"):
        regressions.append("direct output has validation failure modes")
    remaining = [
        "Direct slide spec experiment is not a production Anny agent.",
        "Production readiness remains false.",
        "Next prompt/contract work should target diagram actor -> mechanism -> result quality.",
    ]
    lines = [
        f"# Anny Direct Piti Slide Spec Comparison: {case.case_id}",
        "",
        f"- generated_at: {datetime.now(UTC).isoformat()}",
        f"- adapter_slide_spec: {_display_path(case.adapter_slide_spec_path)}",
        f"- direct_schema_valid: {direct_manifest.get('schema_valid')}",
        f"- direct_failure_modes: {direct_manifest.get('failure_modes', [])}",
        "- QA flags are warning-only.",
        f"- diagram_quality_improved: {str(diagram_quality_improved).lower()}",
        f"- safety_regression_detected: {str(safety_regression_detected).lower()}",
        f"- experiment_outcome: {outcome}",
        "",
        "## Metrics",
        "",
        (
            "| Output | Slides | Sections | Proof Types | Text Only | Source Cards | "
            "Diagrams | Charts/Tables | Needs Fact Check | Required Before Broadcast | "
            "Visible URLs | Diagram Generic | Manual Insert Missing Instruction | "
            "Generic Source Title | Overflow Notes Large | Severity Counts |"
        ),
        "|---|---:|---:|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---|",
        _comparison_row("adapter", adapter_metrics),
        _comparison_row("direct", direct_metrics),
        "",
        "## Delta Summary",
        "",
    ]
    lines.extend(
        f"- {key}: {str(value).lower() if isinstance(value, bool) else value}"
        for key, value in deltas.items()
    )
    lines.extend(
        [
            "",
            "## Conclusion",
            "",
            f"- diagram quality improved: {str(diagram_quality_improved).lower()}",
            f"- safety regression detected: {str(safety_regression_detected).lower()}",
            f"- experiment outcome: {outcome}",
            "",
            "### Better",
            "",
        ]
    )
    lines.extend(f"- {item}" for item in improvements) if improvements else lines.append("- none")
    lines.extend(["", "### Worse", ""])
    lines.extend(f"- {item}" for item in regressions) if regressions else lines.append("- none")
    lines.extend(["", "### Remaining Before Production", ""])
    lines.extend(f"- {item}" for item in remaining)
    lines.extend(
        [
            "",
            "### Next Prompt/Contract Suggestions",
            "",
            "- Make diagram nodes concrete at Anny output time, not in the Piti renderer.",
            "- Require at least one actor, one mechanism verb, and one result node for diagrams.",
            "- Keep source/fact-check flags conservative.",
            "- Keep overflow_notes_too_large as INFO until human review says otherwise.",
        ]
    )
    _write_text(path, "\n".join(lines) + "\n")
    return {
        "adapter": adapter_metrics,
        "direct": direct_metrics,
        "deltas": deltas,
        "outcome": outcome,
    }


def _comparison_row(label: str, metrics: dict[str, Any]) -> str:
    if not metrics:
        return f"| {label} | 0 | 0 | {{}} | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | {{}} |"
    return (
        f"| {label} | {metrics.get('slide_count')} | {metrics.get('section_count')} | "
        f"{metrics.get('proof_object_type_counts')} | {metrics.get('text_only_slide_count')} | "
        f"{metrics.get('source_card_count')} | {metrics.get('diagram_count')} | "
        f"{metrics.get('chart_table_count')} | {metrics.get('needs_fact_check_count')} | "
        f"{metrics.get('required_before_broadcast_count')} | {metrics.get('visible_url_count')} | "
        f"{metrics.get('diagram_nodes_too_generic')} | "
        f"{metrics.get('manual_insert_required_without_editor_instruction')} | "
        f"{metrics.get('source_card_display_title_too_generic')} | "
        f"{metrics.get('overflow_notes_too_large')} | {metrics.get('severity_counts')} |"
    )


def _copy_review_reports(
    *,
    review_output_dir: Path | None,
    case_id: str,
    validation_report_path: Path,
    comparison_report_path: Path,
) -> None:
    if review_output_dir is None:
        return
    review_output_dir.mkdir(parents=True, exist_ok=True)
    shutil.copyfile(validation_report_path, review_output_dir / f"{case_id}_validation.md")
    shutil.copyfile(comparison_report_path, review_output_dir / f"{case_id}_comparison.md")


def _markdown_cell(value: Any) -> str:
    text = str(value if value is not None else "")
    return text.replace("\n", "<br>").replace("|", "\\|")


def _token_usage_summary(manifests: list[dict[str, Any]]) -> dict[str, Any]:
    total: Counter[str] = Counter()
    has_usage = False
    for manifest in manifests:
        usage = manifest.get("response_usage")
        if not isinstance(usage, dict) or not usage:
            continue
        has_usage = True
        for key, value in usage.items():
            if isinstance(value, (int, float)):
                total[key] += value
    return dict(total) if has_usage else {"usage": "not_collected"}


def _write_live_summary(
    *,
    path: Path,
    run_id: str,
    manifests: list[dict[str, Any]],
    output_root: Path,
    model: str | None,
) -> None:
    case_ids = [str(manifest.get("case_id")) for manifest in manifests]
    outcomes = Counter(
        str(manifest.get("experiment_outcome") or "failure") for manifest in manifests
    )
    lines = [
        f"# Anny Direct Piti Slide Spec Live Summary: {run_id}",
        "",
        f"- run_id: {run_id}",
        f"- generated_at: {datetime.now(UTC).isoformat()}",
        "- mode: live",
        f"- model: {model or 'env:LUDDITE_ANNY_API_MODEL'}",
        f"- case_ids: {case_ids}",
        f"- output_root: {_display_path(output_root)}",
        f"- outcomes: {dict(outcomes)}",
        f"- token_usage: {_token_usage_summary(manifests)}",
        "- total_cost: not_collected",
        "- QA flags are warning-only.",
        "- fixture mode validates deterministic expected behavior.",
        "- live mode observes actual model behavior.",
        "- fixture improvement does not mean production readiness.",
        "- live success does not mean broadcast readiness.",
        "- ready_for_production_anny_agent: false",
        "- ready_for_production_piti_agent: false",
        "- ready_for_broadcast: false",
        "",
        "## Success Criteria",
        "",
        "- success: schema/render pass, no safety regression, and diagram warnings decrease.",
        (
            "- partial_success: schema/render pass and no safety regression, "
            "but diagram warnings do not decrease."
        ),
        "- failure: parse/schema/render failure or any source/fact-check safety regression.",
        "",
        "## Case Results",
        "",
        (
            "| case | outcome | parse | schema | render | slides | sections | proof types | "
            "needs fact check | required before broadcast | source hallucinations | "
            "do_not_claim violations | unsupported claims | visible URLs | diagram generic | "
            "manual insert missing instruction | generic source title | overflow notes large | "
            "review delta | info delta | safety regression | diagram improved |"
        ),
        (
            "|---|---|---|---|---|---:|---:|---|---:|---:|---:|---:|---:|---:|---:|"
            "---:|---:|---:|---:|---|---|"
        ),
    ]
    for manifest in manifests:
        metrics = manifest.get("comparison_metrics", {})
        direct = metrics.get("direct", {}) if isinstance(metrics, dict) else {}
        deltas = manifest.get("comparison_deltas", {})
        direct_flags = direct.get("visual_qa_flag_counts", {}) if isinstance(direct, dict) else {}
        lines.append(
            f"| {_markdown_cell(manifest.get('case_id'))} | "
            f"{_markdown_cell(manifest.get('experiment_outcome'))} | "
            f"{_markdown_cell(manifest.get('parse_status'))} | "
            f"{manifest.get('schema_valid')} | {manifest.get('render_passed')} | "
            f"{direct.get('slide_count', 0)} | {direct.get('section_count', 0)} | "
            f"{_markdown_cell(direct.get('proof_object_type_counts', {}))} | "
            f"{direct.get('needs_fact_check_count', 0)} | "
            f"{direct.get('required_before_broadcast_count', 0)} | "
            f"{manifest.get('source_hallucination_count', 0)} | "
            f"{manifest.get('do_not_claim_violation_count', 0)} | "
            f"{manifest.get('unsupported_claim_count', 0)} | "
            f"{manifest.get('visible_url_count', 0)} | "
            f"{direct_flags.get('diagram_nodes_too_generic', 0)} | "
            f"{direct_flags.get('manual_insert_required_without_editor_instruction', 0)} | "
            f"{direct_flags.get('source_card_display_title_too_generic', 0)} | "
            f"{direct_flags.get('overflow_notes_too_large', 0)} | "
            f"{deltas.get('visual_qa_review_delta', 0)} | "
            f"{deltas.get('visual_qa_info_delta', 0)} | "
            f"{deltas.get('safety_regression_detected', False)} | "
            f"{deltas.get('diagram_quality_improved', False)} |"
        )
    _write_text(path, "\n".join(lines) + "\n")


def _write_failure_outputs(
    *,
    case: SlideSpecExperimentCase,
    experiment_dir: Path,
    validation_report_path: Path,
    comparison_report_path: Path,
    error: str,
    mode: str,
) -> dict[str, Any]:
    raw_path = experiment_dir / "raw_model_output.txt"
    _write_text(raw_path, "")
    _write_text(experiment_dir / "api_error.txt", error)
    manifest = {
        "case_id": case.case_id,
        "mode": mode,
        "status": "failed",
        "parse_status": "no_model_output",
        "schema_valid": False,
        "validation_passed": False,
        "render_passed": False,
        "failure_modes": ["api_request_failed"],
        "api_error": error,
        "raw_model_output_retained": True,
        "ready_for_production_anny_agent": False,
        "ready_for_production_piti_agent": False,
        "ready_for_broadcast": False,
        "created_at": datetime.now(UTC).isoformat(),
    }
    _write_validation_report(
        path=validation_report_path,
        case=case,
        manifest=manifest,
        raw_path=raw_path,
        parsed_path=experiment_dir / "parsed_piti_slide_spec.json",
        render_result=None,
        mode=mode,
    )
    adapter_spec = _load_json(case.adapter_slide_spec_path)
    comparison = _write_comparison_report(
        path=comparison_report_path,
        case=case,
        adapter_spec=adapter_spec,
        direct_spec=None,
        direct_manifest=manifest,
    )
    manifest.update(
        {
            "comparison_metrics": {
                "adapter": comparison["adapter"],
                "direct": comparison["direct"],
            },
            "comparison_deltas": comparison["deltas"],
            "experiment_outcome": comparison["outcome"],
        }
    )
    _write_json(experiment_dir / "manifest.json", manifest)
    return manifest


def run_case(
    *,
    case: SlideSpecExperimentCase,
    output_root: Path = DEFAULT_OUTPUT_ROOT,
    review_output_dir: Path | None = DEFAULT_REVIEW_OUTPUT_DIR,
    live_api: bool = False,
    model: str | None = None,
    temperature: float | None = None,
    timeout_seconds: int = 120,
    api_caller: Any | None = None,
) -> dict[str, Any]:
    experiment_dir = output_root / case.case_id
    experiment_dir.mkdir(parents=True, exist_ok=True)
    validation_report_path = experiment_dir / "validation_report.md"
    comparison_report_path = experiment_dir / "comparison_against_adapter.md"
    visual_report_path = experiment_dir / "visual_qa_report.md"
    raw_path = experiment_dir / "raw_model_output.txt"
    parsed_path = experiment_dir / "parsed_piti_slide_spec.json"
    render_output_path = experiment_dir / "direct_piti_slide_spec_draft.pptx"

    input_bundle = _load_json(case.input_bundle_path)
    evidence_pack = _load_json(case.evidence_pack_path)
    manual_storyline = _load_json(case.manual_storyline_path)
    schema = _load_json(paths.SPECS_DIR / "piti_slide_spec_schema.json")
    adapter_spec = _load_json(case.adapter_slide_spec_path)
    visual_summary = (
        (paths.DOCS_DIR / "reviews" / "piti_visual_qa" / "piti_visual_qa_summary.md")
        .read_text(encoding="utf-8")
        if (paths.DOCS_DIR / "reviews" / "piti_visual_qa" / "piti_visual_qa_summary.md").exists()
        else "No visual QA summary available."
    )
    allowed_urls = _collect_allowed_urls(input_bundle, evidence_pack, manual_storyline)
    prompt = build_slide_spec_experiment_prompt(
        input_bundle=input_bundle,
        evidence_pack=evidence_pack,
        manual_storyline=manual_storyline,
        schema=schema,
        visual_qa_summary=visual_summary,
        allowed_urls=allowed_urls,
    )
    _write_text(experiment_dir / "prompt.md", prompt)
    shutil.copyfile(case.input_bundle_path, experiment_dir / "input_bundle.json")
    shutil.copyfile(case.evidence_pack_path, experiment_dir / "evidence_pack.json")
    shutil.copyfile(case.manual_storyline_path, experiment_dir / "manual_storyline.json")
    shutil.copyfile(case.adapter_slide_spec_path, experiment_dir / "adapter_piti_slide_spec.json")
    response_usage: dict[str, Any] = {}
    if live_api:
        try:
            raw_text, response_payload, resolved_model, resolved_temperature = _call_live_api(
                prompt=prompt,
                model=model,
                temperature=temperature,
                timeout_seconds=timeout_seconds,
                api_caller=api_caller,
            )
        except Exception as exc:
            manifest = _write_failure_outputs(
                case=case,
                experiment_dir=experiment_dir,
                validation_report_path=validation_report_path,
                comparison_report_path=comparison_report_path,
                error=str(exc),
                mode="live_api",
            )
            _copy_review_reports(
                review_output_dir=review_output_dir,
                case_id=case.case_id,
                validation_report_path=validation_report_path,
                comparison_report_path=comparison_report_path,
            )
            return manifest
        _write_text(raw_path, raw_text)
        _write_json(experiment_dir / "response_metadata.json", response_payload)
        response_usage = _response_usage(response_payload)
        mode = "live_api"
        model_source = resolved_model
        temp = resolved_temperature
    else:
        direct_spec = _synthetic_fixture_output(case)
        _write_text(raw_path, json.dumps(direct_spec, ensure_ascii=False, indent=2) + "\n")
        mode = "fixture"
        model_source = "synthetic_fixture"
        temp = None

    parsed_spec, manifest, render_result = _validate_raw_slide_spec(
        raw_path=raw_path,
        parsed_path=parsed_path,
        input_bundle=input_bundle,
        evidence_pack=evidence_pack,
        manual_storyline=manual_storyline,
        adapter_spec=adapter_spec,
        render_output_path=render_output_path,
        pseudo_path=parsed_path,
    )
    manifest.update(
        {
            "case_id": case.case_id,
            "mode": mode,
            "model": model_source,
            "temperature": temp,
            "response_usage": response_usage,
            "raw_model_output_path": _display_path(raw_path),
            "parsed_piti_slide_spec_path": _display_path(parsed_path)
            if parsed_path.exists()
            else None,
            "validation_report_path": _display_path(validation_report_path),
            "visual_qa_report_path": _display_path(visual_report_path),
            "comparison_report_path": _display_path(comparison_report_path),
            "created_at": datetime.now(UTC).isoformat(),
        }
    )
    _write_validation_report(
        path=validation_report_path,
        case=case,
        manifest=manifest,
        raw_path=raw_path,
        parsed_path=parsed_path,
        render_result=render_result,
        mode=mode,
    )
    if parsed_spec:
        visual_deck = render_visual_qa.evaluate_slide_spec(
            parsed_path,
            parsed_spec,
            experiment_dir,
        )
        visual_deck = render_visual_qa.VisualQaDeck(
            deck_id=visual_deck.deck_id,
            input_path=visual_deck.input_path,
            output_path=visual_report_path,
            slides=visual_deck.slides,
        )
        render_visual_qa.write_deck_report(visual_deck)
    comparison = _write_comparison_report(
        path=comparison_report_path,
        case=case,
        adapter_spec=adapter_spec,
        direct_spec=parsed_spec,
        direct_manifest=manifest,
    )
    manifest.update(
        {
            "comparison_metrics": {
                "adapter": comparison["adapter"],
                "direct": comparison["direct"],
            },
            "comparison_deltas": comparison["deltas"],
            "experiment_outcome": comparison["outcome"],
        }
    )
    _write_json(experiment_dir / "manifest.json", manifest)
    _copy_review_reports(
        review_output_dir=review_output_dir,
        case_id=case.case_id,
        validation_report_path=validation_report_path,
        comparison_report_path=comparison_report_path,
    )
    return manifest


def run_experiment(
    *,
    case_id: str = "all",
    output_root: Path | None = None,
    review_output_dir: Path | None = None,
    run_id: str | None = None,
    live_api: bool = False,
    mirror_live_review: bool = False,
    model: str | None = None,
    temperature: float | None = None,
    timeout_seconds: int = 120,
    api_caller: Any | None = None,
) -> list[dict[str, Any]]:
    resolved_output_root, resolved_review_output_dir, resolved_run_id = _resolve_run_paths(
        live_api=live_api,
        output_root=output_root,
        review_output_dir=review_output_dir,
        run_id=run_id,
        mirror_live_review=mirror_live_review,
    )
    manifests = [
        run_case(
            case=case,
            output_root=resolved_output_root,
            review_output_dir=resolved_review_output_dir,
            live_api=live_api,
            model=model,
            temperature=temperature,
            timeout_seconds=timeout_seconds,
            api_caller=api_caller,
        )
        for case in _selected_cases(case_id)
    ]
    if live_api and resolved_run_id:
        summary_path = resolved_output_root / "summary.md"
        _write_live_summary(
            path=summary_path,
            run_id=resolved_run_id,
            manifests=manifests,
            output_root=resolved_output_root,
            model=model,
        )
        if mirror_live_review and resolved_review_output_dir:
            shutil.copyfile(summary_path, resolved_review_output_dir / "summary.md")
    return manifests


@app.callback(invoke_without_command=True)
def main(
    case_id: Annotated[
        str,
        typer.Option("--case-id", help="Case id to run, or 'all'."),
    ] = "all",
    output_root: Annotated[
        Path | None,
        typer.Option(
            "--output-root",
            help=(
                "Experiment output root. Fixture defaults to outputs/model_dry_runs/"
                "anny_slide_spec_experiments; live defaults to "
                "outputs/model_dry_runs/anny_slide_spec_experiments_live/{run_id}."
            ),
        ),
    ] = None,
    review_output_dir: Annotated[
        Path | None,
        typer.Option(
            "--review-output-dir",
            help=(
                "Review mirror directory. Fixture mirrors by default; live mirrors only "
                "with --mirror-live-review."
            ),
        ),
    ] = None,
    run_id: Annotated[
        str | None,
        typer.Option("--run-id", help="Live run id. Defaults to live_YYYYMMDDTHHMMSSZ."),
    ] = None,
    live_api: Annotated[
        bool,
        typer.Option("--live-api", help="Opt in to a live OpenAI API call."),
    ] = False,
    mirror_live_review: Annotated[
        bool,
        typer.Option(
            "--mirror-live-review",
            help="Mirror live validation/comparison/summary reports under docs/reviews.",
        ),
    ] = False,
    model: Annotated[
        str | None,
        typer.Option("--model", help="Optional model override for live API mode."),
    ] = None,
    temperature: Annotated[
        float | None,
        typer.Option("--temperature", help="Optional temperature override for live API mode."),
    ] = None,
    timeout_seconds: Annotated[
        int,
        typer.Option("--timeout", help="Live API timeout in seconds."),
    ] = 120,
) -> None:
    """Run controlled Anny direct Piti slide spec experiment."""
    try:
        manifests = run_experiment(
            case_id=case_id,
            output_root=output_root,
            review_output_dir=review_output_dir,
            run_id=run_id,
            live_api=live_api,
            mirror_live_review=mirror_live_review,
            model=model,
            temperature=temperature,
            timeout_seconds=timeout_seconds,
        )
    except ValueError as error:
        console.print(f"[red]{error}[/red]")
        raise typer.Exit(1) from error
    failed = sum(1 for manifest in manifests if manifest.get("failure_modes"))
    console.print(
        "[green]Ran Anny slide spec experiment for "
        f"{len(manifests)} case(s); failure_mode_cases={failed}.[/green]"
    )
