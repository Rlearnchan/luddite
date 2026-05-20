"""Render deterministic visual QA reports for Piti slide specs."""

from __future__ import annotations

import json
import re
from collections import Counter
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Annotated, Any

import typer
from rich.console import Console

from luddite import paths

app = typer.Typer(no_args_is_help=False)
console = Console()

DEFAULT_INPUT_DIR = paths.PITI_SLIDE_SPECS_DIR
DEFAULT_OUTPUT_DIR = paths.OUTPUTS_DIR / "qa" / "piti_visual_qa"
DEFAULT_SUMMARY_PATH = DEFAULT_OUTPUT_DIR / "piti_visual_qa_summary.md"
DEFAULT_REVIEW_OUTPUT_DIR = paths.DOCS_DIR / "reviews" / "piti_visual_qa"

STRUCTURAL_LAYOUTS = {"title", "section_title", "appendix_checklist"}
GENERIC_SOURCE_CARD_TITLES = {
    "reference material",
    "source url carried from anny storyline.",
    "source attached from anny storyline.",
}
GENERIC_DIAGRAM_NODES = {
    "기존 검색",
    "AI 즉답",
    "비교·검증",
    "바로 답",
    "답 제공",
    "질문 훈련",
    "검증",
    "맥락",
    "질문",
    "안전한 금융",
    "성장 금융",
    "담보·단기",
    "장기·위험분담",
}
CONCRETE_ACTOR_MARKERS = {
    "ai 서비스",
    "ai 즉답 서비스",
    "사용자",
    "학생",
    "교사",
    "학교",
    "박물관",
    "천문관",
    "기관",
    "은행",
    "금융위",
    "금융위원회",
    "정부",
    "정책금융",
    "국민성장펀드",
    "기업",
    "산업",
    "service",
    "user",
    "student",
    "school",
    "museum",
    "bank",
    "government",
    "company",
}
MECHANISM_VERB_MARKERS = {
    "압축",
    "비교",
    "검증",
    "확인",
    "전환",
    "공급",
    "투자",
    "분담",
    "지원",
    "연결",
    "훈련",
    "축소",
    "확대",
    "바꾸",
    "줄",
    "늘",
    "compress",
    "compare",
    "verify",
    "fund",
    "support",
    "shift",
    "connect",
}
WEAK_EDGE_LABELS = {"", "arrow", "flow", "link", "to", "흐름", "연결"}
SEVERITY_RANK = {"BLOCKER": 3, "REVIEW": 2, "INFO": 1}
FLAG_METADATA = {
    "proof_object_missing_for_claim_slide": {
        "severity": "REVIEW",
        "reason": "claim or review-sensitive slide has no proof object.",
        "review_hint": "Add an explicit proof_object or confirm that this should remain text-only.",
    },
    "too_many_source_cards_in_sequence": {
        "severity": "REVIEW",
        "reason": "three or more source_card slides appear in sequence.",
        "review_hint": (
            "Check whether the sequence needs pacing, grouping, or a different "
            "visual proof type."
        ),
    },
    "diagram_nodes_too_generic": {
        "severity": "REVIEW",
        "reason": "diagram nodes are too abstract to guide an editable broadcast visual.",
        "review_hint": "Replace abstract labels with concrete actor -> mechanism -> result labels.",
    },
    "diagram_edges_missing_or_weak": {
        "severity": "REVIEW",
        "reason": "diagram edges are missing, unlabeled, or do not connect the node set clearly.",
        "review_hint": "Add labeled edges that explain what changes between the actor and result.",
    },
    "diagram_has_no_concrete_actor": {
        "severity": "REVIEW",
        "reason": "diagram nodes do not name a concrete actor, institution, user, or system.",
        "review_hint": (
            "Name the actor first, such as a service, institution, user, bank, "
            "or policy body."
        ),
    },
    "diagram_has_no_mechanism_verb": {
        "severity": "REVIEW",
        "reason": "diagram text does not show a mechanism verb that explains the change.",
        "review_hint": (
            "Add mechanism language such as compresses, verifies, funds, shifts, "
            "or distributes risk."
        ),
    },
    "diagram_nodes_need_broadcast_copy": {
        "severity": "REVIEW",
        "reason": "diagram node copy is placeholder-like rather than broadcast-facing.",
        "review_hint": "Rewrite node labels upstream so each box can stand alone on screen.",
    },
    "chart_without_data_hint": {
        "severity": "REVIEW",
        "reason": "chart/table proof object has no data_hint for manual chart review.",
        "review_hint": (
            "Add a short data_hint that tells the editor what data the chart "
            "should represent."
        ),
    },
    "source_card_display_title_too_generic": {
        "severity": "REVIEW",
        "reason": "source card display title is generic or repeats the slide headline.",
        "review_hint": (
            "Replace generic source-card display title with a human-readable article/report "
            "title or institution-specific evidence label."
        ),
    },
    "screen_body_empty_but_no_proof_object": {
        "severity": "REVIEW",
        "reason": "slide has no screen_body and no proof object to carry the visual meaning.",
        "review_hint": "Confirm whether the slide needs screen copy or an explicit proof_object.",
    },
    "overflow_notes_too_large": {
        "severity": "INFO",
        "reason": "overflow_notes has more than 3 items.",
        "review_hint": (
            "Check whether this is healthy screen compression or whether core logic "
            "disappeared from the slide."
        ),
    },
    "manual_insert_required_without_editor_instruction": {
        "severity": "REVIEW",
        "reason": "proof_object requires manual insertion, but no editor instruction is available.",
        "review_hint": (
            "Add a short editor_instruction describing what the editor should insert or verify."
        ),
    },
}


@dataclass(frozen=True)
class VisualQaFlag:
    flag: str
    severity: str
    reason: str
    review_hint: str


@dataclass(frozen=True)
class VisualQaSlide:
    slide_no: int
    screen_headline: str
    layout_intent: str
    proof_object_type: str
    screen_body_line_count: int
    overflow_notes_count: int
    needs_source: bool
    needs_fact_check: bool
    required_before_broadcast: bool
    manual_insert_required: bool
    editor_instruction_missing: bool
    flag_details: list[VisualQaFlag]

    @property
    def visual_qa_flags(self) -> list[str]:
        return [detail.flag for detail in self.flag_details]

    @property
    def highest_severity(self) -> str:
        if not self.flag_details:
            return "none"
        return max(
            (detail.severity for detail in self.flag_details),
            key=lambda severity: SEVERITY_RANK[severity],
        )


@dataclass(frozen=True)
class VisualQaDeck:
    deck_id: str
    input_path: Path
    output_path: Path
    slides: list[VisualQaSlide]

    @property
    def flag_count(self) -> int:
        return sum(len(slide.visual_qa_flags) for slide in self.slides)

    @property
    def flagged_slide_count(self) -> int:
        return sum(1 for slide in self.slides if slide.visual_qa_flags)


def _load_json(path: Path) -> dict[str, Any]:
    with path.open(encoding="utf-8") as source:
        payload = json.load(source)
    if not isinstance(payload, dict):
        raise ValueError(f"Expected JSON object at {path}")
    return payload


def _as_list(value: Any) -> list[Any]:
    return value if isinstance(value, list) else []


def _display_path(path: Path) -> str:
    try:
        return str(path.resolve().relative_to(paths.REPO_ROOT))
    except ValueError:
        return str(path)


def _normalize_text(value: Any) -> str:
    return re.sub(r"\s+", "", str(value or "")).strip().lower()


def _markdown_cell(value: Any) -> str:
    text = str(value if value is not None else "")
    text = text.replace("\n", "<br>")
    return text.replace("|", "\\|")


def _bool_text(value: bool) -> str:
    return "true" if value else "false"


def _proof_object(slide: dict[str, Any]) -> dict[str, Any]:
    proof = slide.get("proof_object")
    return proof if isinstance(proof, dict) else {}


def _proof_type(slide: dict[str, Any]) -> str:
    return str(_proof_object(slide).get("type") or "none")


def _slide_no(slide: dict[str, Any]) -> int:
    try:
        return int(slide.get("slide_no") or 0)
    except (TypeError, ValueError):
        return 0


def _sorted_slides(spec: dict[str, Any]) -> list[dict[str, Any]]:
    return sorted(
        [slide for slide in _as_list(spec.get("slides")) if isinstance(slide, dict)],
        key=_slide_no,
    )


def _source_card_run_slide_numbers(slides: list[dict[str, Any]]) -> set[int]:
    flagged: set[int] = set()
    run: list[int] = []
    for slide in slides:
        if _proof_type(slide) == "source_card":
            run.append(_slide_no(slide))
            continue
        if len(run) >= 3:
            flagged.update(run)
        run = []
    if len(run) >= 3:
        flagged.update(run)
    return flagged


def _has_claim_or_review_signal(slide: dict[str, Any]) -> bool:
    return bool(
        slide.get("needs_source")
        or slide.get("needs_fact_check")
        or slide.get("required_before_broadcast")
        or _as_list(slide.get("source_refs"))
        or _as_list(slide.get("risk_flags"))
        or _as_list(slide.get("do_not_claim"))
    )


def _diagram_nodes_too_generic(proof: dict[str, Any]) -> bool:
    nodes = [str(node).strip() for node in _as_list(proof.get("diagram_nodes"))]
    nodes = [node for node in nodes if node]
    normalized_nodes = [_normalize_text(node) for node in nodes]
    if len(nodes) < 3:
        return True
    if len(set(normalized_nodes)) < len(normalized_nodes):
        return True
    generic_nodes = {_normalize_text(node) for node in GENERIC_DIAGRAM_NODES}
    return all(node in generic_nodes for node in normalized_nodes)


def _diagram_edges_missing_or_weak(proof: dict[str, Any]) -> bool:
    nodes = {_normalize_text(node) for node in _as_list(proof.get("diagram_nodes"))}
    edges = [edge for edge in _as_list(proof.get("diagram_edges")) if isinstance(edge, dict)]
    if not edges:
        return True
    valid_edges = [
        edge
        for edge in edges
        if str(edge.get("from") or "").strip()
        and str(edge.get("to") or "").strip()
        and (
            not nodes
            or (
                _normalize_text(edge.get("from")) in nodes
                and _normalize_text(edge.get("to")) in nodes
            )
        )
    ]
    if not valid_edges:
        return True
    labels = [_normalize_text(edge.get("label")) for edge in valid_edges]
    return all(label in {_normalize_text(item) for item in WEAK_EDGE_LABELS} for label in labels)


def _diagram_has_no_concrete_actor(proof: dict[str, Any]) -> bool:
    nodes = [str(node).strip() for node in _as_list(proof.get("diagram_nodes"))]
    nodes = [node for node in nodes if node]
    if not nodes:
        return True
    generic_nodes = {_normalize_text(node) for node in GENERIC_DIAGRAM_NODES}
    if all(_normalize_text(node) in generic_nodes for node in nodes):
        return True
    joined = " ".join(nodes).lower()
    return not any(marker.lower() in joined for marker in CONCRETE_ACTOR_MARKERS)


def _diagram_has_no_mechanism_verb(proof: dict[str, Any]) -> bool:
    nodes = [str(node) for node in _as_list(proof.get("diagram_nodes"))]
    edge_labels = [
        str(edge.get("label") or "")
        for edge in _as_list(proof.get("diagram_edges"))
        if isinstance(edge, dict)
    ]
    text = " ".join([*nodes, *edge_labels]).lower()
    return not any(marker.lower() in text for marker in MECHANISM_VERB_MARKERS)


def _diagram_nodes_need_broadcast_copy(proof: dict[str, Any]) -> bool:
    nodes = [str(node).strip() for node in _as_list(proof.get("diagram_nodes"))]
    nodes = [node for node in nodes if node]
    if not nodes:
        return True
    generic_nodes = {_normalize_text(node) for node in GENERIC_DIAGRAM_NODES}
    if any(_normalize_text(node) in generic_nodes for node in nodes):
        return True
    return all(len(node) <= 6 and " " not in node for node in nodes)


def _flag_detail(flag: str) -> VisualQaFlag:
    metadata = FLAG_METADATA[flag]
    return VisualQaFlag(
        flag=flag,
        severity=metadata["severity"],
        reason=metadata["reason"],
        review_hint=metadata["review_hint"],
    )


def visual_qa_flags(
    slide: dict[str, Any],
    *,
    source_card_run_slides: set[int] | None = None,
) -> list[str]:
    """Return warning-only QA flags for one slide."""
    source_card_run_slides = source_card_run_slides or set()
    flags: list[str] = []
    proof = _proof_object(slide)
    proof_type = _proof_type(slide)
    layout_intent = str(slide.get("layout_intent") or "")
    screen_body = _as_list(slide.get("screen_body"))
    overflow_notes = _as_list(slide.get("overflow_notes"))
    slide_no = _slide_no(slide)

    if (
        proof_type == "none"
        and layout_intent not in STRUCTURAL_LAYOUTS
        and _has_claim_or_review_signal(slide)
    ):
        flags.append("proof_object_missing_for_claim_slide")
    if slide_no in source_card_run_slides:
        flags.append("too_many_source_cards_in_sequence")
    if proof_type == "diagram":
        nodes_too_generic = _diagram_nodes_too_generic(proof)
        if nodes_too_generic:
            flags.append("diagram_nodes_too_generic")
        if _diagram_edges_missing_or_weak(proof):
            flags.append("diagram_edges_missing_or_weak")
        if not nodes_too_generic and _diagram_has_no_concrete_actor(proof):
            flags.append("diagram_has_no_concrete_actor")
        if _diagram_has_no_mechanism_verb(proof):
            flags.append("diagram_has_no_mechanism_verb")
        if not nodes_too_generic and _diagram_nodes_need_broadcast_copy(proof):
            flags.append("diagram_nodes_need_broadcast_copy")
    if proof_type in {"chart", "table"} and not str(proof.get("data_hint") or "").strip():
        flags.append("chart_without_data_hint")
    if proof_type == "source_card":
        display_title = str(proof.get("display_title") or "").strip()
        normalized_title = _normalize_text(display_title)
        generic_titles = {_normalize_text(title) for title in GENERIC_SOURCE_CARD_TITLES}
        if (
            not display_title
            or normalized_title in generic_titles
            or normalized_title == _normalize_text(slide.get("screen_headline"))
        ):
            flags.append("source_card_display_title_too_generic")
    if not screen_body and proof_type == "none" and layout_intent not in {"title", "section_title"}:
        flags.append("screen_body_empty_but_no_proof_object")
    if len(overflow_notes) > 3:
        flags.append("overflow_notes_too_large")
    if proof.get("manual_insert_required") and not str(
        slide.get("editor_instruction") or ""
    ).strip():
        flags.append("manual_insert_required_without_editor_instruction")
    return flags


def visual_qa_flag_details(
    slide: dict[str, Any],
    *,
    source_card_run_slides: set[int] | None = None,
) -> list[VisualQaFlag]:
    return [
        _flag_detail(flag)
        for flag in visual_qa_flags(slide, source_card_run_slides=source_card_run_slides)
    ]


def evaluate_slide_spec(path: Path, spec: dict[str, Any], output_dir: Path) -> VisualQaDeck:
    slides = _sorted_slides(spec)
    source_card_run_slides = _source_card_run_slide_numbers(slides)
    deck_id = str(spec.get("deck_id") or path.stem)
    output_path = output_dir / f"{deck_id}.md"
    qa_slides = [
        VisualQaSlide(
            slide_no=_slide_no(slide),
            screen_headline=str(slide.get("screen_headline") or ""),
            layout_intent=str(slide.get("layout_intent") or ""),
            proof_object_type=_proof_type(slide),
            screen_body_line_count=len(_as_list(slide.get("screen_body"))),
            overflow_notes_count=len(_as_list(slide.get("overflow_notes"))),
            needs_source=bool(slide.get("needs_source")),
            needs_fact_check=bool(slide.get("needs_fact_check")),
            required_before_broadcast=bool(slide.get("required_before_broadcast")),
            manual_insert_required=bool(_proof_object(slide).get("manual_insert_required")),
            editor_instruction_missing=not str(slide.get("editor_instruction") or "").strip(),
            flag_details=visual_qa_flag_details(
                slide,
                source_card_run_slides=source_card_run_slides,
            ),
        )
        for slide in slides
    ]
    return VisualQaDeck(
        deck_id=deck_id,
        input_path=path,
        output_path=output_path,
        slides=qa_slides,
    )


def _flag_counter(decks: list[VisualQaDeck]) -> Counter[str]:
    counter: Counter[str] = Counter()
    for deck in decks:
        for slide in deck.slides:
            counter.update(slide.visual_qa_flags)
    return counter


def _severity_counter(decks: list[VisualQaDeck]) -> Counter[str]:
    counter: Counter[str] = Counter()
    for deck in decks:
        for slide in deck.slides:
            counter.update(detail.severity for detail in slide.flag_details)
    return counter


def _slide_priority_score(slide: VisualQaSlide) -> tuple[int, int, int, int, int, int, int]:
    flags = set(slide.visual_qa_flags)
    return (
        int(len(flags) >= 2),
        int(slide.required_before_broadcast),
        int(slide.needs_fact_check),
        int("manual_insert_required_without_editor_instruction" in flags),
        int("source_card_display_title_too_generic" in flags),
        int("overflow_notes_too_large" in flags),
        len(flags),
    )


def _primary_review_hint(slide: VisualQaSlide) -> str:
    if not slide.flag_details:
        return ""
    detail = max(
        slide.flag_details,
        key=lambda item: (
            SEVERITY_RANK[item.severity],
            item.flag != "overflow_notes_too_large",
        ),
    )
    return detail.review_hint


def _top_review_rows(decks: list[VisualQaDeck]) -> list[tuple[int, VisualQaDeck, VisualQaSlide]]:
    rows: list[tuple[VisualQaDeck, VisualQaSlide]] = [
        (deck, slide)
        for deck in decks
        for slide in deck.slides
        if slide.visual_qa_flags
    ]
    rows.sort(
        key=lambda row: (
            *[-score for score in _slide_priority_score(row[1])],
            row[0].deck_id,
            row[1].slide_no,
        )
    )
    return [(priority, deck, slide) for priority, (deck, slide) in enumerate(rows, start=1)]


def _append_top_review_queue(lines: list[str], decks: list[VisualQaDeck]) -> None:
    lines.extend(
        [
            "## Top Review Queue",
            "",
            "| priority | deck | slide | headline | severity | flags | review_hint |",
            "|---:|---|---:|---|---|---|---|",
        ]
    )
    rows = _top_review_rows(decks)
    if not rows:
        lines.append("| 0 | none | 0 | none | none | none | none |")
        return
    for priority, deck, slide in rows:
        lines.append(
            f"| {priority} | {_markdown_cell(deck.deck_id)} | {slide.slide_no} | "
            f"{_markdown_cell(slide.screen_headline)} | {slide.highest_severity} | "
            f"{_markdown_cell(', '.join(slide.visual_qa_flags))} | "
            f"{_markdown_cell(_primary_review_hint(slide))} |"
        )


def _append_flag_details(lines: list[str], decks: list[VisualQaDeck]) -> None:
    lines.extend(
        [
            "## Flag Details",
            "",
            "| deck | slide | flag | severity | reason | review_hint |",
            "|---|---:|---|---|---|---|",
        ]
    )
    has_details = False
    for deck in decks:
        for slide in deck.slides:
            for detail in slide.flag_details:
                has_details = True
                lines.append(
                    f"| {_markdown_cell(deck.deck_id)} | {slide.slide_no} | "
                    f"{detail.flag} | {detail.severity} | "
                    f"{_markdown_cell(detail.reason)} | "
                    f"{_markdown_cell(detail.review_hint)} |"
                )
    if not has_details:
        lines.append("| none | 0 | none | none | none | none |")


def _next_recommended_fix_area(counter: Counter[str]) -> list[str]:
    diagram_flags = sum(
        counter.get(flag, 0)
        for flag in (
            "diagram_nodes_too_generic",
            "diagram_edges_missing_or_weak",
            "diagram_has_no_concrete_actor",
            "diagram_has_no_mechanism_verb",
            "diagram_nodes_need_broadcast_copy",
        )
    )
    source_title_flags = counter.get("source_card_display_title_too_generic", 0)
    manual_insert_flags = counter.get("manual_insert_required_without_editor_instruction", 0)
    if diagram_flags >= max(source_title_flags, manual_insert_flags):
        return [
            "- Main weakness: diagram proof objects are still too generic.",
            (
                "- Recommended next fix: improve Anny/adapter diagram node "
                "generation, not Piti renderer."
            ),
            "- Do not treat overflow_notes_too_large as failure yet.",
        ]
    if source_title_flags >= manual_insert_flags:
        return [
            "- Main weakness: source card titles are still too generic.",
            "- Recommended next fix: improve upstream source-card display labels.",
            "- Do not synthesize source titles in the Piti renderer.",
        ]
    return [
        "- Main weakness: manually inserted proof objects lack editor instructions.",
        "- Recommended next fix: improve upstream editor_instruction coverage.",
        "- Keep QA flags warning-only until a human review workflow exists.",
    ]


def write_deck_report(deck: VisualQaDeck) -> None:
    deck.output_path.parent.mkdir(parents=True, exist_ok=True)
    lines = [
        f"# Piti Visual QA: {deck.deck_id}",
        "",
        f"- Generated at: {datetime.now(UTC).isoformat()}",
        f"- Input: {_display_path(deck.input_path)}",
        f"- Slides: {len(deck.slides)}",
        f"- Flagged slides: {deck.flagged_slide_count}",
        f"- QA flags: {deck.flag_count}",
        "- QA flags are review warnings only.",
        "- LLM/API calls: none",
        "- Image insertion/chart generation/Google Slides integration: none",
        "",
    ]
    _append_top_review_queue(lines, [deck])
    lines.extend(["", "## Review Queue", ""])
    flagged_slides = [slide for slide in deck.slides if slide.visual_qa_flags]
    if flagged_slides:
        for slide in flagged_slides:
            lines.append(
                "- slide {slide_no} [{severity}]: {headline} -- {flags}".format(
                    slide_no=slide.slide_no,
                    severity=slide.highest_severity,
                    headline=slide.screen_headline,
                    flags=", ".join(slide.visual_qa_flags),
                )
            )
    else:
        lines.append("- none")
    lines.append("")
    _append_flag_details(lines, [deck])
    lines.extend(
        [
            "",
            "## Slide QA",
            "",
            (
                "| slide_no | screen_headline | layout_intent | proof_object.type | "
                "screen_body lines | overflow_notes count | needs_source | "
                "needs_fact_check | required_before_broadcast | manual_insert_required | "
                "visual_qa_flags | visual_qa_severity |"
            ),
            "|---:|---|---|---|---:|---:|---|---|---|---|---|---|",
        ]
    )
    for slide in deck.slides:
        flags = ", ".join(slide.visual_qa_flags) if slide.visual_qa_flags else "none"
        lines.append(
            f"| {slide.slide_no} | {_markdown_cell(slide.screen_headline)} | "
            f"{_markdown_cell(slide.layout_intent)} | "
            f"{_markdown_cell(slide.proof_object_type)} | "
            f"{slide.screen_body_line_count} | {slide.overflow_notes_count} | "
            f"{_bool_text(slide.needs_source)} | {_bool_text(slide.needs_fact_check)} | "
            f"{_bool_text(slide.required_before_broadcast)} | "
            f"{_bool_text(slide.manual_insert_required)} | {_markdown_cell(flags)} | "
            f"{slide.highest_severity} |"
        )
    deck.output_path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def write_summary_report(path: Path, decks: list[VisualQaDeck]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    counter = _flag_counter(decks)
    severity_counter = _severity_counter(decks)
    lines = [
        "# Piti Visual QA Summary",
        "",
        f"- Generated at: {datetime.now(UTC).isoformat()}",
        f"- Decks: {len(decks)}",
        f"- Slides: {sum(len(deck.slides) for deck in decks)}",
        f"- Flagged slides: {sum(deck.flagged_slide_count for deck in decks)}",
        f"- QA flags: {sum(deck.flag_count for deck in decks)}",
        "- QA flags are review warnings only.",
        "- ready_for_piti_renderer_contract: true",
        "- ready_for_api_experiment: true",
        "- ready_for_production_anny_agent: false",
        "- ready_for_production_piti_agent: false",
        "- ready_for_broadcast: false",
        "",
        "## Decks",
        "",
        "| Deck | Slides | Flagged Slides | QA Flags | Report |",
        "|---|---:|---:|---:|---|",
    ]
    for deck in decks:
        lines.append(
            f"| {_markdown_cell(deck.deck_id)} | {len(deck.slides)} | "
            f"{deck.flagged_slide_count} | {deck.flag_count} | "
            f"{_markdown_cell(_display_path(deck.output_path))} |"
        )
    lines.extend(["", "## Flag Counts", ""])
    if counter:
        for flag, count in sorted(counter.items()):
            lines.append(f"- {flag}: {count}")
    else:
        lines.append("- none")
    lines.extend(["", "## Severity Counts", ""])
    if severity_counter:
        for severity in ("BLOCKER", "REVIEW", "INFO"):
            lines.append(f"- {severity}: {severity_counter.get(severity, 0)}")
    else:
        lines.append("- none")
    lines.append("")
    _append_top_review_queue(lines, decks)
    lines.extend(
        [
            "",
            "## Flag Explanations",
            "",
            "| flag | severity | reason | review_hint |",
            "|---|---|---|---|",
        ]
    )
    for flag, metadata in sorted(FLAG_METADATA.items()):
        lines.append(
            f"| {flag} | {metadata['severity']} | "
            f"{_markdown_cell(metadata['reason'])} | "
            f"{_markdown_cell(metadata['review_hint'])} |"
        )
    lines.extend(["", "## Next Recommended Fix Area", ""])
    lines.extend(_next_recommended_fix_area(counter))
    lines.extend(["", "## Review Queue", ""])
    any_flagged = False
    for deck in decks:
        for slide in deck.slides:
            if not slide.visual_qa_flags:
                continue
            any_flagged = True
            lines.append(
                "- {deck} slide {slide_no} [{severity}]: {headline} -- {flags}".format(
                    deck=deck.deck_id,
                    slide_no=slide.slide_no,
                    severity=slide.highest_severity,
                    headline=slide.screen_headline,
                    flags=", ".join(slide.visual_qa_flags),
                )
            )
    if not any_flagged:
        lines.append("- none")
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def render_visual_qa(
    *,
    input_dir: Path = DEFAULT_INPUT_DIR,
    output_dir: Path = DEFAULT_OUTPUT_DIR,
    summary_path: Path | None = None,
    review_output_dir: Path | None = None,
) -> list[VisualQaDeck]:
    if not input_dir.exists():
        raise FileNotFoundError(f"Piti slide spec input directory does not exist: {input_dir}")
    slide_spec_paths = sorted(input_dir.glob("*.json"))
    if not slide_spec_paths:
        raise FileNotFoundError(f"No Piti slide spec JSON files found in: {input_dir}")
    decks = [
        evaluate_slide_spec(path, _load_json(path), output_dir)
        for path in slide_spec_paths
    ]
    for deck in decks:
        write_deck_report(deck)
    write_summary_report(summary_path or output_dir / DEFAULT_SUMMARY_PATH.name, decks)
    if review_output_dir is not None:
        review_decks = [
            VisualQaDeck(
                deck_id=deck.deck_id,
                input_path=deck.input_path,
                output_path=review_output_dir / deck.output_path.name,
                slides=deck.slides,
            )
            for deck in decks
        ]
        for deck in review_decks:
            write_deck_report(deck)
        write_summary_report(review_output_dir / DEFAULT_SUMMARY_PATH.name, review_decks)
    return decks


@app.callback(invoke_without_command=True)
def main(
    input_dir: Annotated[
        Path,
        typer.Option("--input-dir", help="Directory of Piti slide spec JSON files."),
    ] = DEFAULT_INPUT_DIR,
    output_dir: Annotated[
        Path,
        typer.Option("--output-dir", help="Directory for visual QA Markdown reports."),
    ] = DEFAULT_OUTPUT_DIR,
    summary_path: Annotated[
        Path | None,
        typer.Option("--summary", help="Optional summary Markdown output path."),
    ] = None,
    review_output_dir: Annotated[
        Path | None,
        typer.Option(
            "--review-output-dir",
            help="Optional GitHub-visible review report mirror directory.",
        ),
    ] = DEFAULT_REVIEW_OUTPUT_DIR,
) -> None:
    """Render warning-only visual QA reports for Piti slide specs."""
    try:
        decks = render_visual_qa(
            input_dir=input_dir,
            output_dir=output_dir,
            summary_path=summary_path,
            review_output_dir=review_output_dir,
        )
    except (FileNotFoundError, OSError, ValueError, json.JSONDecodeError) as error:
        console.print(f"[red]{error}[/red]")
        raise typer.Exit(1) from error
    console.print(
        "[green]Wrote Piti visual QA reports for "
        f"{len(decks)} deck(s) to {output_dir}.[/green]"
    )
