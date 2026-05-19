"""Render Piti deck plan JSON artifacts into human-readable storyboards."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Annotated, Any

import typer
from rich.console import Console

from luddite import paths
from luddite.agents.piti.build_deck_plan_from_storyline import DEFAULT_CASES

app = typer.Typer(no_args_is_help=False)
console = Console()


def _load_json(path: Path) -> dict[str, Any]:
    with path.open(encoding="utf-8") as source:
        payload = json.load(source)
    if not isinstance(payload, dict):
        raise ValueError(f"Expected JSON object at {path}")
    return payload


def _as_list(value: Any) -> list[Any]:
    return value if isinstance(value, list) else []


def _count_flag(deck_plan: dict[str, Any], field: str) -> int:
    return sum(1 for slide in deck_plan.get("slides", []) if slide.get(field) is True)


def _count_source_urls(deck_plan: dict[str, Any]) -> int:
    return sum(len(slide.get("source_urls", [])) for slide in deck_plan.get("slides", []))


def _production_checklist_count(deck_plan: dict[str, Any]) -> int:
    return sum(
        1
        for slide in deck_plan.get("slides", [])
        if slide.get("layout_type") == "appendix_checklist"
        or slide.get("slide_type") == "production_checklist"
    )


def _short_notes(notes: Any, limit: int = 240) -> str:
    if not notes:
        return ""
    text = " ".join(str(notes).split())
    if len(text) <= limit:
        return text
    return text[: limit - 3].rstrip() + "..."


def _source_lines(slide: dict[str, Any], *, limit: int = 3) -> list[str]:
    urls = [str(url) for url in _as_list(slide.get("source_urls")) if url]
    if not urls:
        return ["- none"]
    lines = [f"- {url}" for url in urls[:limit]]
    if len(urls) > limit:
        lines.append(f"- ... +{len(urls) - limit} more")
    return lines


def _visual_summary(slide: dict[str, Any]) -> str:
    visual_plan = slide.get("visual_plan") or {}
    if not isinstance(visual_plan, dict):
        return "none"
    kind = visual_plan.get("kind") or "none"
    description = visual_plan.get("description") or ""
    copyright_risk = visual_plan.get("copyright_risk")
    suffix = " (copyright check)" if copyright_risk else ""
    if description:
        return f"{kind}: {description}{suffix}"
    return f"{kind}{suffix}"


def render_deck_storyboard_markdown(deck_plan: dict[str, Any]) -> str:
    lines = [
        f"# {deck_plan.get('title', 'Piti Deck Storyboard')}",
        "",
        "> 이 결과물은 PPT 완성본이 아니라 deck storyboard입니다.",
        "> source attached는 fact-check complete를 의미하지 않습니다.",
        "> visual_plan은 실제 이미지가 아니라 후보/계획입니다.",
        "",
        "## Summary",
        "",
        f"- source storyline: {deck_plan.get('source_storyline_id')}",
        f"- sections: {len(deck_plan.get('sections', []))}",
        f"- planned slides: {len(deck_plan.get('slides', []))}",
        f"- source_urls: {_count_source_urls(deck_plan)}",
        f"- needs_source: {_count_flag(deck_plan, 'needs_source')}",
        f"- needs_fact_check: {_count_flag(deck_plan, 'needs_fact_check')}",
        f"- production checklist slides: {_production_checklist_count(deck_plan)}",
        f"- risk_flags: {_as_list(deck_plan.get('risk_flags'))}",
        "- readiness: not production-ready",
        "",
    ]
    required_fact_checks = _as_list(deck_plan.get("required_fact_checks"))
    if required_fact_checks:
        lines.extend(["## Required Fact Checks", ""])
        lines.extend(f"- {item}" for item in required_fact_checks)
        lines.append("")
    for section in deck_plan.get("sections", []):
        section_no = section.get("section_no")
        section_title = section.get("section_title") or f"Section {section_no}"
        lines.extend([f"## Section {section_no}. {section_title}", ""])
        purpose = section.get("purpose")
        if purpose:
            lines.extend([f"Purpose: {purpose}", ""])
        for slide in section.get("slides", []):
            headline = slide.get("headline") or "(untitled)"
            slide_no = slide.get("slide_no")
            lines.extend([f"### {slide_no:02d}. {headline}", ""])
            lines.extend(
                [
                    f"- layout: {slide.get('layout_type')}",
                    f"- slide_type: {slide.get('slide_type')}",
                    f"- source_slide_refs: {_as_list(slide.get('source_slide_refs'))}",
                    "",
                    "Body:",
                ]
            )
            body = _as_list(slide.get("body"))
            lines.extend(f"- {item}" for item in body) if body else lines.append("-")
            lines.extend(["", f"Visual: {_visual_summary(slide)}", "", "Sources:"])
            lines.extend(_source_lines(slide))
            edit_notes = _as_list(slide.get("edit_notes"))
            if edit_notes:
                lines.extend(["", "Edit notes:"])
                lines.extend(f"- {note}" for note in edit_notes)
            lines.extend(
                [
                    "",
                    "Flags:",
                    f"- needs_source: {bool(slide.get('needs_source'))}",
                    f"- needs_fact_check: {bool(slide.get('needs_fact_check'))}",
                    f"- required_before_broadcast: {bool(slide.get('required_before_broadcast'))}",
                ]
            )
            notes = _short_notes(slide.get("speaker_notes") or slide.get("notes"))
            if notes:
                lines.extend(["", f"Notes: {notes}"])
            if slide.get("layout_type") == "appendix_checklist":
                lines.extend(["", "_Internal appendix/checklist slide, not a main PPT claim._"])
            lines.append("")
    return "\n".join(lines).rstrip() + "\n"


def render_deck_storyboard(*, input_path: Path, output_path: Path) -> Path:
    deck_plan = _load_json(input_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(render_deck_storyboard_markdown(deck_plan), encoding="utf-8")
    return output_path


def _default_output_path(deck_plan_path: Path, output_dir: Path) -> Path:
    name = deck_plan_path.name.replace("_deck_plan.json", "_storyboard.md")
    return output_dir / name


def render_default_storyboards(output_dir: Path = paths.PITI_STORYBOARDS_DIR) -> list[Path]:
    rendered: list[Path] = []
    for case in DEFAULT_CASES:
        rendered.append(
            render_deck_storyboard(
                input_path=case.output_path,
                output_path=_default_output_path(case.output_path, output_dir),
            )
        )
    readme = output_dir / "README.md"
    readme.parent.mkdir(parents=True, exist_ok=True)
    readme.write_text(_storyboards_readme(rendered, output_dir=output_dir), encoding="utf-8")
    rendered.append(readme)
    return rendered


def _storyboards_readme(rendered: list[Path], *, output_dir: Path) -> str:
    lines = [
        "# Piti Storyboard Samples",
        "",
        "These files are deck storyboards generated from Anny manual/enriched storyline",
        "samples. They are not PPTX files, not Google Slides, and not broadcast-ready",
        "production decks.",
        "",
        "Important interpretation rules:",
        "",
        "- `source_urls` are evidence references, not completed fact-checks.",
        "- `needs_source` and `needs_fact_check` mark human follow-up work.",
        "- `visual_plan` is a visual direction only; no image was collected or inserted.",
        "- `production_checklist` slides are internal/appendix material.",
        "- Full PPT generation and production Piti agent are not implemented here.",
        "",
        "Recommended reading order:",
        "",
        "1. `ai_knowledge_institution_storyboard.md`",
        "2. `productive_finance_policy_storyboard.md`",
        "",
        "Generated files:",
        "",
    ]
    for path in sorted(rendered, key=lambda item: str(item)):
        try:
            display = path.relative_to(output_dir)
        except ValueError:
            display = Path(path.name)
        lines.append(f"- `{display}`")
    return "\n".join(lines) + "\n"


@app.callback(invoke_without_command=True)
def main(
    input_path: Annotated[
        Path | None,
        typer.Option("--input", help="Single Piti deck plan JSON to render."),
    ] = None,
    output_path: Annotated[
        Path | None,
        typer.Option("--output", help="Storyboard Markdown output path."),
    ] = None,
    output_dir: Annotated[
        Path,
        typer.Option("--output-dir", help="Default storyboard output directory."),
    ] = paths.PITI_STORYBOARDS_DIR,
) -> None:
    """Render Piti deck plan JSON as storyboard Markdown without making PPTX."""
    if input_path:
        if output_path is None:
            raise typer.BadParameter("--output is required with --input")
        rendered = render_deck_storyboard(input_path=input_path, output_path=output_path)
        console.print(f"[green]Rendered {rendered}.[/green]")
        return
    rendered = render_default_storyboards(output_dir=output_dir)
    console.print(f"[green]Rendered {len(rendered)} Piti storyboard files.[/green]")


if __name__ == "__main__":
    app()
