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
from jsonschema import Draft202012Validator
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
LAYOUT_INTENTS = (
    "title",
    "section_title",
    "text_only_calculation",
    "headline_body",
    "source_card_or_article_quote",
    "image_left_quote_right",
    "chart_table_reference",
    "diagram",
    "closing_question",
    "appendix_checklist",
)
DIAGRAM_ARROW_MARKERS = ("->", "→", "=>")
GENERIC_SOURCE_CARD_TITLE_TEXTS = {
    "reference material",
    "source url carried from anny storyline.",
    "source attached from anny storyline.",
}


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


def _schema_path(path_parts: Any) -> str:
    path = "$"
    for part in path_parts:
        if isinstance(part, int):
            path += f"[{part}]"
        else:
            path += f".{part}"
    return path


def _schema_child_path(parent_path: str, child: str) -> str:
    return f"{parent_path}.{child}" if parent_path != "$" else f"$.{child}"


def _missing_required_property(message: str) -> str | None:
    parts = message.split("'")
    if len(parts) >= 3 and "required property" in message:
        return parts[1]
    return None


def _schema_error_details(spec: dict[str, Any]) -> dict[str, Any]:
    schema = _load_json(paths.SPECS_DIR / "piti_slide_spec_schema.json")
    validator = Draft202012Validator(schema)
    details: list[dict[str, Any]] = []
    missing_paths: list[str] = []
    invalid_enums: list[dict[str, Any]] = []
    errors = sorted(
        validator.iter_errors(spec),
        key=lambda error: (_schema_path(error.path), error.message),
    )
    for error in errors:
        path = _schema_path(error.path)
        detail = {
            "path": path,
            "validator": error.validator,
            "message": error.message,
        }
        details.append(detail)
        if error.validator == "required":
            missing = _missing_required_property(error.message)
            if missing:
                missing_paths.append(_schema_child_path(path, missing))
        if error.validator == "enum":
            invalid_enums.append(
                {
                    "path": path,
                    "value": error.instance,
                    "allowed": list(error.validator_value),
                }
            )
    return {
        "details": details,
        "missing_required_schema_paths": list(dict.fromkeys(missing_paths)),
        "invalid_enum_values": invalid_enums,
    }


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


def _count_source_refs(spec: dict[str, Any]) -> int:
    return sum(len(_as_list(slide.get("source_refs"))) for slide in _all_slides(spec))


def _count_do_not_claim_items(spec: dict[str, Any]) -> int:
    return sum(len(_as_list(slide.get("do_not_claim"))) for slide in _all_slides(spec))


def _diagram_nodes_with_arrow_count(spec: dict[str, Any]) -> int:
    count = 0
    for slide in _all_slides(spec):
        proof = _proof(slide)
        for node in _as_list(proof.get("diagram_nodes")):
            node_text = str(node)
            if any(marker in node_text for marker in DIAGRAM_ARROW_MARKERS):
                count += 1
    return count


def _invalid_layout_intents(spec: dict[str, Any]) -> list[dict[str, Any]]:
    invalid: list[dict[str, Any]] = []
    for slide in _all_slides(spec):
        value = str(slide.get("layout_intent") or "")
        if value not in LAYOUT_INTENTS:
            invalid.append(
                {
                    "slide_no": _slide_no(slide),
                    "slide_id": slide.get("slide_id"),
                    "layout_intent": value,
                    "allowed": list(LAYOUT_INTENTS),
                }
            )
    return invalid


def _slide_identity(slide: dict[str, Any]) -> tuple[str | None, int | None]:
    slide_id = str(slide.get("slide_id") or "").strip() or None
    slide_no = _slide_no(slide) or None
    return slide_id, slide_no


def _entry_matches_top_level(
    entry: Any,
    *,
    top_slide_ids: set[str],
    top_slide_nos: set[int],
) -> bool:
    if isinstance(entry, dict):
        slide_id, slide_no = _slide_identity(entry)
        return bool((slide_id and slide_id in top_slide_ids) or (slide_no in top_slide_nos))
    if isinstance(entry, int):
        return entry in top_slide_nos
    entry_text = str(entry).strip()
    return bool(
        entry_text in top_slide_ids
        or (entry_text.isdigit() and int(entry_text) in top_slide_nos)
    )


def _section_slide_reference_diagnostics(spec: dict[str, Any]) -> dict[str, Any]:
    sections = [section for section in _as_list(spec.get("sections")) if isinstance(section, dict)]
    top_slides = _all_slides(spec)
    top_identities = [_slide_identity(slide) for slide in top_slides]
    top_slide_ids = {slide_id for slide_id, _slide_no_value in top_identities if slide_id}
    top_slide_nos = {slide_no for _slide_id, slide_no in top_identities if slide_no}
    represented_ids: set[str] = set()
    represented_nos: set[int] = set()
    missing_sections_slides_count = 0
    empty_sections_count = 0
    sections_with_empty_slides: list[str] = []
    mismatch_count = 0

    for section in sections:
        slide_refs = section.get("slides")
        section_label = str(section.get("section_id") or section.get("section_no") or "")
        if not isinstance(slide_refs, list):
            missing_sections_slides_count += 1
            continue
        if not slide_refs:
            missing_sections_slides_count += 1
            empty_sections_count += 1
            sections_with_empty_slides.append(section_label)
            continue
        for entry in slide_refs:
            if not _entry_matches_top_level(
                entry,
                top_slide_ids=top_slide_ids,
                top_slide_nos=top_slide_nos,
            ):
                mismatch_count += 1
                continue
            if isinstance(entry, dict):
                slide_id, slide_no = _slide_identity(entry)
                if slide_id:
                    represented_ids.add(slide_id)
                if slide_no:
                    represented_nos.add(slide_no)
            elif isinstance(entry, int):
                represented_nos.add(entry)
            else:
                entry_text = str(entry).strip()
                if entry_text in top_slide_ids:
                    represented_ids.add(entry_text)
                elif entry_text.isdigit():
                    represented_nos.add(int(entry_text))

    for slide in top_slides:
        slide_id, slide_no = _slide_identity(slide)
        if slide_id and slide_id in represented_ids:
            continue
        if slide_no and slide_no in represented_nos:
            continue
        mismatch_count += 1

    return {
        "missing_sections_slides_count": missing_sections_slides_count,
        "empty_sections_count": empty_sections_count,
        "sections_with_empty_slides": sections_with_empty_slides,
        "section_slide_ref_mismatch_count": mismatch_count,
    }


def _contract_diagnostics(parsed: dict[str, Any], adapter_spec: dict[str, Any]) -> dict[str, Any]:
    adapter_slide_count = len(_all_slides(adapter_spec))
    direct_slide_count = len(_all_slides(parsed))
    adapter_section_count = len(_as_list(adapter_spec.get("sections")))
    direct_section_count = len(_as_list(parsed.get("sections")))
    adapter_source_refs = _count_source_refs(adapter_spec)
    direct_source_refs = _count_source_refs(parsed)
    adapter_do_not_claim = _count_do_not_claim_items(adapter_spec)
    direct_do_not_claim = _count_do_not_claim_items(parsed)
    adapter_needs_fact_check = _count_bool(adapter_spec, "needs_fact_check")
    direct_needs_fact_check = _count_bool(parsed, "needs_fact_check")
    adapter_required = _count_bool(adapter_spec, "required_before_broadcast")
    direct_required = _count_bool(parsed, "required_before_broadcast")
    section_refs = _section_slide_reference_diagnostics(parsed)
    invalid_layouts = _invalid_layout_intents(parsed)
    diagram_arrow_count = _diagram_nodes_with_arrow_count(parsed)
    slide_count_delta = direct_slide_count - adapter_slide_count
    source_refs_delta = direct_source_refs - adapter_source_refs
    needs_fact_check_delta = direct_needs_fact_check - adapter_needs_fact_check
    required_delta = direct_required - adapter_required
    do_not_claim_delta = direct_do_not_claim - adapter_do_not_claim
    top_level_slides_empty = direct_slide_count == 0
    minimum_slide_count_failed = bool(
        24 <= adapter_slide_count <= 26 and direct_slide_count < 20
    )
    return {
        **section_refs,
        "top_level_slides_empty": top_level_slides_empty,
        "slide_count_delta_vs_adapter": slide_count_delta,
        "section_count_delta_vs_adapter": direct_section_count - adapter_section_count,
        "source_refs_delta_vs_adapter": source_refs_delta,
        "needs_fact_check_delta_vs_adapter": needs_fact_check_delta,
        "required_before_broadcast_delta_vs_adapter": required_delta,
        "do_not_claim_delta_vs_adapter": do_not_claim_delta,
        "adapter_slide_count": adapter_slide_count,
        "direct_slide_count": direct_slide_count,
        "adapter_section_count": adapter_section_count,
        "direct_section_count": direct_section_count,
        "adapter_source_refs_count": adapter_source_refs,
        "direct_source_refs_count": direct_source_refs,
        "adapter_do_not_claim_count": adapter_do_not_claim,
        "direct_do_not_claim_count": direct_do_not_claim,
        "invalid_layout_intents": invalid_layouts,
        "layout_intent_invalid_enum_count": len(invalid_layouts),
        "diagram_nodes_with_arrow_count": diagram_arrow_count,
        "slide_count_too_compressed": bool(
            adapter_slide_count >= 20 and direct_slide_count < 20
        ),
        "minimum_slide_count_failed": minimum_slide_count_failed,
        "representative_deck_compressed_to_empty": bool(
            24 <= adapter_slide_count <= 26 and top_level_slides_empty
        ),
        "deck_has_no_renderable_slides": top_level_slides_empty,
        "source_refs_removed_too_aggressively": source_refs_delta < 0,
        "do_not_claim_removed_or_ignored": do_not_claim_delta < 0,
    }


def _text_only_slide_count(spec: dict[str, Any]) -> int:
    return sum(1 for slide in _all_slides(spec) if _proof_type(slide) == "none")


def _chart_table_count(spec: dict[str, Any]) -> int:
    return sum(1 for slide in _all_slides(spec) if _proof_type(slide) in {"chart", "table"})


def _normalized_text(value: Any) -> str:
    return "".join(str(value or "").lower().split())


def _chart_table_body_too_long_slides(spec: dict[str, Any]) -> list[int]:
    return [
        _slide_no(slide)
        for slide in _all_slides(spec)
        if _proof_type(slide) in {"chart", "table"}
        and len(_as_list(slide.get("screen_body"))) > 1
    ]


def _article_quote_missing_quote_text_slides(spec: dict[str, Any]) -> list[int]:
    return [
        _slide_no(slide)
        for slide in _all_slides(spec)
        if _proof_type(slide) == "article_quote"
        and not str(_proof(slide).get("quote_text") or "").strip()
    ]


def _source_card_generic_title_slides(spec: dict[str, Any]) -> list[int]:
    generic_titles = {_normalized_text(title) for title in GENERIC_SOURCE_CARD_TITLE_TEXTS}
    slides: list[int] = []
    for slide in _all_slides(spec):
        if _proof_type(slide) != "source_card":
            continue
        proof = _proof(slide)
        title = str(proof.get("display_title") or "").strip()
        normalized_title = _normalized_text(title)
        if (
            not title
            or normalized_title in generic_titles
            or normalized_title == _normalized_text(slide.get("screen_headline"))
        ):
            slides.append(_slide_no(slide))
    return slides


def _renderer_contract_diagnostics(spec: dict[str, Any]) -> dict[str, Any]:
    chart_slides = _chart_table_body_too_long_slides(spec)
    quote_slides = _article_quote_missing_quote_text_slides(spec)
    source_title_slides = _source_card_generic_title_slides(spec)
    reasons: list[str] = []
    if chart_slides:
        reasons.append(
            "chart/table slides have too much screen_body; move explanation to notes"
        )
    if quote_slides:
        reasons.append("article_quote proof objects require non-empty quote_text")
    return {
        "chart_table_body_too_long_count": len(chart_slides),
        "chart_table_body_too_long_slides": chart_slides,
        "article_quote_missing_quote_text_count": len(quote_slides),
        "article_quote_missing_quote_text_slides": quote_slides,
        "source_card_generic_title_count": len(source_title_slides),
        "source_card_generic_title_slides": source_title_slides,
        "proof_object_renderer_contract_failed": bool(chart_slides or quote_slides),
        "renderer_failure_reasons": reasons,
        "renderer_suggested_prompt_fix": _renderer_suggested_prompt_fix(
            chart_slides=chart_slides,
            quote_slides=quote_slides,
            source_title_slides=source_title_slides,
        ),
    }


def _renderer_suggested_prompt_fix(
    *,
    chart_slides: list[int],
    quote_slides: list[int],
    source_title_slides: list[int],
) -> str:
    suggestions: list[str] = []
    if chart_slides:
        suggestions.append("Keep chart/table screen_body to 0-1 lines and move detail to notes.")
    if quote_slides:
        suggestions.append("Use article_quote only when quote_text is available.")
    if source_title_slides:
        suggestions.append("Replace generic source-card titles with article/report titles.")
    return " ".join(suggestions) if suggestions else "none"


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
        "source_refs_count": _count_source_refs(spec),
        "do_not_claim_count": _count_do_not_claim_items(spec),
        "needs_fact_check_count": _count_bool(spec, "needs_fact_check"),
        "required_before_broadcast_count": _count_bool(spec, "required_before_broadcast"),
        "visible_url_count": _visible_url_count(spec),
        "diagram_nodes_with_arrow_count": _diagram_nodes_with_arrow_count(spec),
        "chart_table_body_too_long_count": len(_chart_table_body_too_long_slides(spec)),
        "article_quote_missing_quote_text_count": len(
            _article_quote_missing_quote_text_slides(spec)
        ),
        "source_card_generic_title_count": len(_source_card_generic_title_slides(spec)),
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
        or manifest.get("source_refs_removed_too_aggressively", False)
        or manifest.get("do_not_claim_removed_or_ignored", False)
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
        or manifest.get("failure_modes")
        or deltas.get("safety_regression_detected")
    ):
        return "failure"
    if deltas.get("diagram_quality_improved"):
        return "success"
    return "partial_success"


def _adapter_coverage_summary(adapter_spec: dict[str, Any]) -> dict[str, Any]:
    sections = []
    for section in _as_list(adapter_spec.get("sections")):
        if not isinstance(section, dict):
            continue
        section_slides = []
        for slide in _as_list(section.get("slides")):
            if not isinstance(slide, dict):
                continue
            proof = _proof(slide)
            section_slides.append(
                {
                    "slide_id": slide.get("slide_id"),
                    "slide_no": slide.get("slide_no"),
                    "layout_intent": slide.get("layout_intent"),
                    "screen_headline": slide.get("screen_headline"),
                    "proof_object_type": proof.get("type"),
                    "needs_fact_check": slide.get("needs_fact_check"),
                    "required_before_broadcast": slide.get(
                        "required_before_broadcast"
                    ),
                    "source_refs_count": len(_as_list(slide.get("source_refs"))),
                    "do_not_claim_count": len(_as_list(slide.get("do_not_claim"))),
                }
            )
        sections.append(
            {
                "section_id": section.get("section_id"),
                "section_no": section.get("section_no"),
                "section_title": section.get("section_title"),
                "slide_count": len(section_slides),
                "slides": section_slides,
            }
        )
    return {
        "slide_count": len(_all_slides(adapter_spec)),
        "section_count": len(_as_list(adapter_spec.get("sections"))),
        "needs_fact_check_count": _count_bool(adapter_spec, "needs_fact_check"),
        "required_before_broadcast_count": _count_bool(
            adapter_spec,
            "required_before_broadcast",
        ),
        "source_refs_count": _count_source_refs(adapter_spec),
        "do_not_claim_count": _count_do_not_claim_items(adapter_spec),
        "sections": sections,
    }


def build_slide_spec_experiment_prompt(
    *,
    input_bundle: dict[str, Any],
    evidence_pack: dict[str, Any],
    manual_storyline: dict[str, Any],
    schema: dict[str, Any],
    visual_qa_summary: str,
    allowed_urls: set[str],
    adapter_spec: dict[str, Any] | None = None,
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
            "Do not output merely plausible JSON; output the exact schema object.",
            "Every top-level required field must be present.",
            "Never output an empty deck.",
            "Top-level slides[] must be non-empty.",
            "Every sections[] object must include a non-empty slides array.",
            "Every section must contain at least one slide.",
            "Do not satisfy schema by outputting empty arrays.",
            "Every section slide object must correspond to a top-level slides[] object.",
            "Array fields must be arrays, not null.",
            "Use only schema-valid enum strings.",
            f"Allowed layout_intent values: {', '.join(LAYOUT_INTENTS)}.",
            "Never use layout_intent=hook or any new layout value.",
            (
                "Use the adapter/manual storyline as the slide coverage baseline; "
                "do not compress 24-26 representative slides into fewer than 20."
            ),
            "If the adapter/manual storyline has 24-26 slides, output at least 20 slides.",
            (
                "Preserve section count, key beats, counterpoints, caution slides, "
                "and appendix/checklist slides."
            ),
            "Separate broadcast screen copy from notes.",
            "screen_headline must be broadcast-facing.",
            "screen_body must be short; move explanation, evidence, and caution to notes.",
            "Use speaker_notes_expanded or overflow_notes for long reasoning.",
            "Every slide must provide an explicit proof_object.",
            (
                "proof_object.type should be one of diagram, chart, table, source_card, "
                "article_quote, or none."
            ),
            "Chart/table proof objects need data_hint and 0-1 screen_body lines.",
            "Move chart/table explanation to overflow_notes or speaker_notes_expanded.",
            "article_quote requires non-empty quote_text; otherwise use source_card or diagram.",
            "Source-card display_title must be a specific article/report/institution label.",
            "Do not expose source URLs on screen; preserve them in source_refs or notes.",
            "Keep needs_source, needs_fact_check, and required_before_broadcast conservative.",
            (
                "Never remove needs_fact_check=true unless supplied evidence "
                "explicitly resolves the claim."
            ),
            (
                "Never remove required_before_broadcast=true unless the required "
                "check is explicitly satisfied."
            ),
            "Preserve source_refs and do_not_claim guardrails unless clearly irrelevant.",
            "If uncertain, keep the conservative safety flag.",
            "Do not make unchecked claims as screen copy.",
            "Do not violate do_not_claim.",
            "Include counterpoint or opposing questions when the topic requires it.",
            "## Diagram Requirements",
            "Avoid generic chain labels such as AI 즉답 -> 검증 -> 맥락.",
            "Avoid word-only chain labels such as 안전한 금융 -> 성장 금융.",
            "Prefer at least 3 nodes.",
            "Use actor -> mechanism -> result structure.",
            "Use short broadcast sentences, not abstract noun placeholders.",
            "Do not include -> inside any diagram_nodes[] string.",
            "Relationships belong in diagram_edges[].",
            "Include at least one concrete actor, institution, user, or system.",
            "Include at least one mechanism verb.",
            "Make each node imply actor/context, mechanism/change, or result/tension.",
            "Each diagram node should work as broadcast-facing box copy.",
            "Use meaningful edge labels; avoid labels like 흐름 or 연결.",
            "## Preflight Checklist Before Final JSON",
            "Top-level slides[] is non-empty.",
            "If baseline has 24-26 slides, output has at least 20 slides.",
            "Every section has slides[].",
            "No section has an empty slides array.",
            "Every section slide exists in top-level slides[].",
            "All major beats are preserved instead of summarized away.",
            "Only schema-valid layout_intent values are used.",
            "Approximate slide count is preserved.",
            "Every chart/table slide has data_hint and short screen_body.",
            "Every article_quote has non-empty quote_text.",
            "needs_fact_check and required_before_broadcast are conservative.",
            "source_refs and do_not_claim are preserved.",
            "No visible URLs appear in screen copy.",
            "No diagram_nodes[] string contains ->.",
            "Relationships are in diagram_edges[].",
            "Production readiness flags remain false.",
            "Do not print this checklist; final output is JSON only.",
            "## Adapter Piti Slide Spec Coverage Baseline",
            json.dumps(
                _adapter_coverage_summary(adapter_spec) if adapter_spec else {},
                ensure_ascii=False,
                indent=2,
            ),
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


def _apply_renderer_contract_fixtures(spec: dict[str, Any]) -> int:
    changed = 0
    for slide in _all_slides(spec):
        proof = _proof(slide)
        if proof.get("type") == "article_quote" and not str(
            proof.get("quote_text") or ""
        ).strip():
            proof["type"] = "source_card"
            proof["quote_translation"] = None
            proof["placeholder_reason"] = (
                "Direct fixture uses source_card because no actual quote_text is available."
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
    diagram_changes = _apply_concrete_diagram_fixtures(spec, case_id=case.case_id)
    renderer_contract_changes = _apply_renderer_contract_fixtures(spec)
    spec["notes"] = (
        "Synthetic fixture for Anny direct Piti slide spec experiment. "
        "This validates the direct-output harness without calling an API. "
        f"Concrete diagram fixture updates applied: {diagram_changes}; "
        f"renderer contract fixture updates applied: {renderer_contract_changes}; "
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
    schema_details = _schema_error_details(parsed)
    contract = _contract_diagnostics(parsed, adapter_spec)
    renderer_contract = _renderer_contract_diagnostics(parsed)
    if not validation.get("schema_valid"):
        failure_modes.append("schema_error")
    if contract["top_level_slides_empty"]:
        failure_modes.append("top_level_slides_empty")
    if contract["missing_sections_slides_count"]:
        failure_modes.append("sections_slides_missing")
    if contract["empty_sections_count"]:
        failure_modes.append("empty_sections")
    if contract["section_slide_ref_mismatch_count"]:
        failure_modes.append("section_slide_refs_mismatch")
    if contract["layout_intent_invalid_enum_count"]:
        failure_modes.append("invalid_layout_intent")
    if contract["slide_count_too_compressed"]:
        failure_modes.append("deck_too_compressed")
    if contract["minimum_slide_count_failed"]:
        failure_modes.append("minimum_slide_count_failed")
    if contract["representative_deck_compressed_to_empty"]:
        failure_modes.append("representative_deck_compressed_to_empty")
    if contract["deck_has_no_renderable_slides"]:
        failure_modes.append("deck_has_no_renderable_slides")
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
    if contract["source_refs_removed_too_aggressively"]:
        failure_modes.append("source_refs_removed_too_aggressively")
    if contract["do_not_claim_removed_or_ignored"]:
        failure_modes.append("do_not_claim_removed_or_ignored")
    if (
        needs_fact_check_removed
        or required_removed
        or contract["source_refs_removed_too_aggressively"]
        or contract["do_not_claim_removed_or_ignored"]
    ):
        failure_modes.append("safety_metadata_removed")
    if contract["diagram_nodes_with_arrow_count"]:
        failure_modes.append("diagram_node_contains_arrow")
    if renderer_contract["proof_object_renderer_contract_failed"]:
        failure_modes.append("proof_object_renderer_contract_failed")
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
        "schema_error_details": schema_details["details"],
        "missing_required_schema_paths": schema_details["missing_required_schema_paths"],
        "invalid_enum_values": schema_details["invalid_enum_values"],
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
        "source_refs_removed_too_aggressively": contract[
            "source_refs_removed_too_aggressively"
        ],
        "do_not_claim_removed_or_ignored": contract["do_not_claim_removed_or_ignored"],
        "screen_headline_missing_count": headline_missing_count,
        "top_level_slides_empty": contract["top_level_slides_empty"],
        "missing_sections_slides_count": contract["missing_sections_slides_count"],
        "empty_sections_count": contract["empty_sections_count"],
        "sections_with_empty_slides": contract["sections_with_empty_slides"],
        "section_slide_ref_mismatch_count": contract["section_slide_ref_mismatch_count"],
        "slide_count_delta_vs_adapter": contract["slide_count_delta_vs_adapter"],
        "section_count_delta_vs_adapter": contract["section_count_delta_vs_adapter"],
        "source_refs_delta_vs_adapter": contract["source_refs_delta_vs_adapter"],
        "needs_fact_check_delta_vs_adapter": contract["needs_fact_check_delta_vs_adapter"],
        "required_before_broadcast_delta_vs_adapter": contract[
            "required_before_broadcast_delta_vs_adapter"
        ],
        "do_not_claim_delta_vs_adapter": contract["do_not_claim_delta_vs_adapter"],
        "adapter_slide_count": contract["adapter_slide_count"],
        "direct_slide_count": contract["direct_slide_count"],
        "adapter_section_count": contract["adapter_section_count"],
        "direct_section_count": contract["direct_section_count"],
        "adapter_source_refs_count": contract["adapter_source_refs_count"],
        "direct_source_refs_count": contract["direct_source_refs_count"],
        "adapter_do_not_claim_count": contract["adapter_do_not_claim_count"],
        "direct_do_not_claim_count": contract["direct_do_not_claim_count"],
        "invalid_layout_intents": contract["invalid_layout_intents"],
        "layout_intent_invalid_enum_count": contract["layout_intent_invalid_enum_count"],
        "diagram_nodes_with_arrow_count": contract["diagram_nodes_with_arrow_count"],
        "slide_count_too_compressed": contract["slide_count_too_compressed"],
        "minimum_slide_count_failed": contract["minimum_slide_count_failed"],
        "representative_deck_compressed_to_empty": contract[
            "representative_deck_compressed_to_empty"
        ],
        "deck_has_no_renderable_slides": contract["deck_has_no_renderable_slides"],
        "chart_table_body_too_long_count": renderer_contract[
            "chart_table_body_too_long_count"
        ],
        "chart_table_body_too_long_slides": renderer_contract[
            "chart_table_body_too_long_slides"
        ],
        "article_quote_missing_quote_text_count": renderer_contract[
            "article_quote_missing_quote_text_count"
        ],
        "article_quote_missing_quote_text_slides": renderer_contract[
            "article_quote_missing_quote_text_slides"
        ],
        "source_card_generic_title_count": renderer_contract[
            "source_card_generic_title_count"
        ],
        "source_card_generic_title_slides": renderer_contract[
            "source_card_generic_title_slides"
        ],
        "proof_object_renderer_contract_failed": renderer_contract[
            "proof_object_renderer_contract_failed"
        ],
        "renderer_failure_reasons": renderer_contract["renderer_failure_reasons"],
        "renderer_suggested_prompt_fix": renderer_contract["renderer_suggested_prompt_fix"],
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
        (
            "- source_refs_removed_too_aggressively: "
            f"{manifest.get('source_refs_removed_too_aggressively', False)}"
        ),
        (
            "- do_not_claim_removed_or_ignored: "
            f"{manifest.get('do_not_claim_removed_or_ignored', False)}"
        ),
        f"- missing_required_schema_paths: {manifest.get('missing_required_schema_paths', [])}",
        f"- invalid_enum_values: {manifest.get('invalid_enum_values', [])}",
        f"- top_level_slides_empty: {manifest.get('top_level_slides_empty', False)}",
        (
            "- missing_sections_slides_count: "
            f"{manifest.get('missing_sections_slides_count', 0)}"
        ),
        f"- empty_sections_count: {manifest.get('empty_sections_count', 0)}",
        f"- sections_with_empty_slides: {manifest.get('sections_with_empty_slides', [])}",
        (
            "- section_slide_ref_mismatch_count: "
            f"{manifest.get('section_slide_ref_mismatch_count', 0)}"
        ),
        (
            "- minimum_slide_count_failed: "
            f"{manifest.get('minimum_slide_count_failed', False)}"
        ),
        (
            "- representative_deck_compressed_to_empty: "
            f"{manifest.get('representative_deck_compressed_to_empty', False)}"
        ),
        (
            "- deck_has_no_renderable_slides: "
            f"{manifest.get('deck_has_no_renderable_slides', False)}"
        ),
        f"- slide_count_delta_vs_adapter: {manifest.get('slide_count_delta_vs_adapter', 0)}",
        f"- section_count_delta_vs_adapter: {manifest.get('section_count_delta_vs_adapter', 0)}",
        f"- source_refs_delta_vs_adapter: {manifest.get('source_refs_delta_vs_adapter', 0)}",
        (
            "- needs_fact_check_delta_vs_adapter: "
            f"{manifest.get('needs_fact_check_delta_vs_adapter', 0)}"
        ),
        (
            "- required_before_broadcast_delta_vs_adapter: "
            f"{manifest.get('required_before_broadcast_delta_vs_adapter', 0)}"
        ),
        f"- do_not_claim_delta_vs_adapter: {manifest.get('do_not_claim_delta_vs_adapter', 0)}",
        f"- diagram_nodes_with_arrow_count: {manifest.get('diagram_nodes_with_arrow_count', 0)}",
        (
            "- chart_table_body_too_long_count: "
            f"{manifest.get('chart_table_body_too_long_count', 0)}"
        ),
        (
            "- chart_table_body_too_long_slides: "
            f"{manifest.get('chart_table_body_too_long_slides', [])}"
        ),
        (
            "- article_quote_missing_quote_text_count: "
            f"{manifest.get('article_quote_missing_quote_text_count', 0)}"
        ),
        (
            "- article_quote_missing_quote_text_slides: "
            f"{manifest.get('article_quote_missing_quote_text_slides', [])}"
        ),
        (
            "- source_card_generic_title_count: "
            f"{manifest.get('source_card_generic_title_count', 0)}"
        ),
        (
            "- proof_object_renderer_contract_failed: "
            f"{manifest.get('proof_object_renderer_contract_failed', False)}"
        ),
        f"- renderer_failure_reasons: {manifest.get('renderer_failure_reasons', [])}",
        (
            "- renderer_suggested_prompt_fix: "
            f"{manifest.get('renderer_suggested_prompt_fix', 'none')}"
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
    lines.extend(["", "## Contract Diagnostics", ""])
    diagnostic_keys = [
        "top_level_slides_empty",
        "sections_slides_missing",
        "empty_sections",
        "invalid_layout_intent",
        "deck_too_compressed",
        "minimum_slide_count_failed",
        "representative_deck_compressed_to_empty",
        "deck_has_no_renderable_slides",
        "safety_metadata_removed",
        "diagram_node_contains_arrow",
        "proof_object_renderer_contract_failed",
    ]
    failure_modes = set(manifest.get("failure_modes", []))
    for key in diagnostic_keys:
        lines.append(f"- {key}: {str(key in failure_modes).lower()}")
    lines.extend(["", "## Schema Error Details", ""])
    schema_details = manifest.get("schema_error_details", [])
    if schema_details:
        for detail in schema_details:
            lines.append(
                "- "
                f"{detail.get('path')}: {detail.get('message')} "
                f"({detail.get('validator')})"
            )
    else:
        lines.append("- none")
    lines.extend(["", "## Renderer Failure Diagnostics", ""])
    renderer_lines = [
        (
            "- chart_table_body_too_long: "
            f"{manifest.get('chart_table_body_too_long_count', 0)} "
            f"slides {manifest.get('chart_table_body_too_long_slides', [])}"
        ),
        (
            "- article_quote_missing_quote_text: "
            f"{manifest.get('article_quote_missing_quote_text_count', 0)} "
            f"slides {manifest.get('article_quote_missing_quote_text_slides', [])}"
        ),
        (
            "- source_card_generic_title: "
            f"{manifest.get('source_card_generic_title_count', 0)} "
            f"slides {manifest.get('source_card_generic_title_slides', [])}"
        ),
        f"- renderer_failure_reasons: {manifest.get('renderer_failure_reasons', [])}",
        f"- suggested_prompt_fix: {manifest.get('renderer_suggested_prompt_fix', 'none')}",
    ]
    lines.extend(renderer_lines)
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
    contract_delta_keys = [
        "slide_count_delta_vs_adapter",
        "section_count_delta_vs_adapter",
        "source_refs_delta_vs_adapter",
        "needs_fact_check_delta_vs_adapter",
        "required_before_broadcast_delta_vs_adapter",
        "do_not_claim_delta_vs_adapter",
        "diagram_nodes_with_arrow_count",
        "missing_sections_slides_count",
        "empty_sections_count",
        "section_slide_ref_mismatch_count",
        "layout_intent_invalid_enum_count",
        "chart_table_body_too_long_count",
        "article_quote_missing_quote_text_count",
        "source_card_generic_title_count",
    ]
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
        **{key: direct_manifest.get(key, 0) for key in contract_delta_keys},
        "slide_count_too_compressed": direct_manifest.get(
            "slide_count_too_compressed",
            False,
        ),
        "top_level_slides_empty": direct_manifest.get("top_level_slides_empty", False),
        "minimum_slide_count_failed": direct_manifest.get(
            "minimum_slide_count_failed",
            False,
        ),
        "representative_deck_compressed_to_empty": direct_manifest.get(
            "representative_deck_compressed_to_empty",
            False,
        ),
        "deck_has_no_renderable_slides": direct_manifest.get(
            "deck_has_no_renderable_slides",
            False,
        ),
        "source_refs_removed_too_aggressively": direct_manifest.get(
            "source_refs_removed_too_aggressively",
            False,
        ),
        "proof_object_renderer_contract_failed": direct_manifest.get(
            "proof_object_renderer_contract_failed",
            False,
        ),
        "do_not_claim_removed_or_ignored": direct_manifest.get(
            "do_not_claim_removed_or_ignored",
            False,
        ),
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
    failure_modes = set(direct_manifest.get("failure_modes", []))
    contract_failure_lines = [
        f"- top_level_slides_empty: {'top_level_slides_empty' in failure_modes}",
        f"- sections_slides_missing: {'sections_slides_missing' in failure_modes}",
        f"- empty_sections: {'empty_sections' in failure_modes}",
        f"- invalid_layout_intent: {'invalid_layout_intent' in failure_modes}",
        f"- deck_too_compressed: {'deck_too_compressed' in failure_modes}",
        f"- minimum_slide_count_failed: {'minimum_slide_count_failed' in failure_modes}",
        (
            "- representative_deck_compressed_to_empty: "
            f"{'representative_deck_compressed_to_empty' in failure_modes}"
        ),
        (
            "- deck_has_no_renderable_slides: "
            f"{'deck_has_no_renderable_slides' in failure_modes}"
        ),
        f"- safety_metadata_removed: {'safety_metadata_removed' in failure_modes}",
        f"- diagram_node_contains_arrow: {'diagram_node_contains_arrow' in failure_modes}",
        (
            "- proof_object_renderer_contract_failed: "
            f"{'proof_object_renderer_contract_failed' in failure_modes}"
        ),
    ]
    remaining = [
        "Direct slide spec experiment is not a production Anny agent.",
        "Production readiness remains false.",
        (
            "Next prompt/contract work should verify schema shape, slide coverage, "
            "and safety metadata in live output."
        ),
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
            "Source Refs | Do Not Claim | Visible URLs | Diagram Generic | "
            "Diagram Node Arrows | Chart Body Too Long | Quote Missing Text | "
            "Source Title Generic | Manual Insert Missing Instruction | "
            "Generic Source Title | Overflow Notes Large | Severity Counts |"
        ),
        (
            "|---|---:|---:|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|"
            "---:|---:|---:|---:|---:|---:|---:|---|"
        ),
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
            "### Contract Failure Reasons",
            "",
            *contract_failure_lines,
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
            (
                "- Make schema shape explicit: every section needs slides[], and "
                "top-level slides must match."
            ),
            "- Preserve adapter-level slide coverage; do not over-compress representative decks.",
            "- Require at least one actor, one mechanism verb, and one result node for diagrams.",
            "- Keep source/fact-check flags conservative.",
            (
                "- Keep source_refs and do_not_claim guardrails unless the prompt "
                "supplies a clear reason."
            ),
            "- Forbid arrows inside diagram node text; relationships belong in diagram_edges.",
            "- Forbid empty decks and empty section slide arrays.",
            "- Keep chart/table screen_body to 0-1 lines with data_hint.",
            "- Use article_quote only when quote_text is available.",
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
        cells: list[Any] = [label, 0, 0, {}, *([0] * 17), {}]
        return "| " + " | ".join(str(cell) for cell in cells) + " |"
    return (
        f"| {label} | {metrics.get('slide_count')} | {metrics.get('section_count')} | "
        f"{metrics.get('proof_object_type_counts')} | {metrics.get('text_only_slide_count')} | "
        f"{metrics.get('source_card_count')} | {metrics.get('diagram_count')} | "
        f"{metrics.get('chart_table_count')} | {metrics.get('needs_fact_check_count')} | "
        f"{metrics.get('required_before_broadcast_count')} | "
        f"{metrics.get('source_refs_count')} | {metrics.get('do_not_claim_count')} | "
        f"{metrics.get('visible_url_count')} | "
        f"{metrics.get('diagram_nodes_too_generic')} | "
        f"{metrics.get('diagram_nodes_with_arrow_count')} | "
        f"{metrics.get('chart_table_body_too_long_count')} | "
        f"{metrics.get('article_quote_missing_quote_text_count')} | "
        f"{metrics.get('source_card_generic_title_count')} | "
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
    manifest_models = {
        str(manifest.get("model"))
        for manifest in manifests
        if manifest.get("model") not in {None, "synthetic_fixture"}
    }
    model_label = model or (
        next(iter(manifest_models))
        if len(manifest_models) == 1
        else sorted(manifest_models) or ["env:LUDDITE_ANNY_API_MODEL"]
    )
    lines = [
        f"# Anny Direct Piti Slide Spec Live Summary: {run_id}",
        "",
        f"- run_id: {run_id}",
        f"- generated_at: {datetime.now(UTC).isoformat()}",
        "- mode: live",
        f"- model: {model_label}",
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
            "slide delta | top slides empty | section slide missing | empty sections | "
            "minimum slide failed | section ref mismatch | source refs delta | "
            "fact-check delta | broadcast-required delta | diagram node arrows | "
            "chart body too long | quote missing text | renderer failure reasons | review delta | "
            "info delta | safety regression | diagram improved |"
        ),
        (
            "|---|---|---|---|---|---:|---:|---|---:|---:|---:|---:|---:|---:|---:|"
            "---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---|---:|"
            "---:|---|---|"
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
            f"{manifest.get('slide_count_delta_vs_adapter', 0)} | "
            f"{manifest.get('top_level_slides_empty', False)} | "
            f"{manifest.get('missing_sections_slides_count', 0)} | "
            f"{manifest.get('empty_sections_count', 0)} | "
            f"{manifest.get('minimum_slide_count_failed', False)} | "
            f"{manifest.get('section_slide_ref_mismatch_count', 0)} | "
            f"{manifest.get('source_refs_delta_vs_adapter', 0)} | "
            f"{manifest.get('needs_fact_check_delta_vs_adapter', 0)} | "
            f"{manifest.get('required_before_broadcast_delta_vs_adapter', 0)} | "
            f"{manifest.get('diagram_nodes_with_arrow_count', 0)} | "
            f"{manifest.get('chart_table_body_too_long_count', 0)} | "
            f"{manifest.get('article_quote_missing_quote_text_count', 0)} | "
            f"{_markdown_cell(manifest.get('renderer_failure_reasons', []))} | "
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
        adapter_spec=adapter_spec,
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
