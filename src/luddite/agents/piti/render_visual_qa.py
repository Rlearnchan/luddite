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
    visual_qa_flags: list[str]


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
    if proof_type == "diagram" and _diagram_nodes_too_generic(proof):
        flags.append("diagram_nodes_too_generic")
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
            visual_qa_flags=visual_qa_flags(
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
        "## Review Queue",
        "",
    ]
    flagged_slides = [slide for slide in deck.slides if slide.visual_qa_flags]
    if flagged_slides:
        for slide in flagged_slides:
            lines.append(
                "- slide {slide_no}: {headline} -- {flags}".format(
                    slide_no=slide.slide_no,
                    headline=slide.screen_headline,
                    flags=", ".join(slide.visual_qa_flags),
                )
            )
    else:
        lines.append("- none")
    lines.extend(
        [
            "",
            "## Slide QA",
            "",
            (
                "| slide_no | screen_headline | layout_intent | proof_object.type | "
                "screen_body lines | overflow_notes count | needs_source | "
                "needs_fact_check | required_before_broadcast | manual_insert_required | "
                "visual_qa_flags |"
            ),
            "|---:|---|---|---|---:|---:|---|---|---|---|---|",
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
            f"{_bool_text(slide.manual_insert_required)} | {_markdown_cell(flags)} |"
        )
    deck.output_path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def write_summary_report(path: Path, decks: list[VisualQaDeck]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    counter = _flag_counter(decks)
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
    lines.extend(["", "## Review Queue", ""])
    any_flagged = False
    for deck in decks:
        for slide in deck.slides:
            if not slide.visual_qa_flags:
                continue
            any_flagged = True
            lines.append(
                "- {deck} slide {slide_no}: {headline} -- {flags}".format(
                    deck=deck.deck_id,
                    slide_no=slide.slide_no,
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
