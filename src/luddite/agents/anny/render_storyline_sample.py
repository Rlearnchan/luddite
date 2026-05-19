"""Render anny storyline JSON artifacts into human-readable Markdown samples."""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Annotated, Any

import typer
from rich.console import Console

from luddite import paths

app = typer.Typer(no_args_is_help=False)
console = Console()

DEFAULT_SAMPLE_DIR = paths.OUTPUTS_DIR / "samples" / "anny_storylines"


@dataclass(frozen=True)
class StorylineSample:
    label: str
    input_path: Path
    output_path: Path
    description: str
    failure_manifest_path: Path | None = None


DEFAULT_SAMPLES = [
    StorylineSample(
        label="AI knowledge manual enriched",
        input_path=(
            paths.ANNY_STORYLINE_DRY_RUN_DIR
            / "ai_knowledge_institution_gpt_pro_storyline_enriched.json"
        ),
        output_path=DEFAULT_SAMPLE_DIR / "ai_knowledge_institution_manual_enriched.md",
        description="GPT Pro enriched manual dry-run sample.",
    ),
    StorylineSample(
        label="Productive finance manual enriched",
        input_path=(
            paths.ANNY_STORYLINE_DRY_RUN_DIR
            / "productive_finance_policy_gpt_pro_storyline_enriched.json"
        ),
        output_path=DEFAULT_SAMPLE_DIR / "productive_finance_manual_enriched.md",
        description="GPT Pro enriched manual dry-run sample.",
    ),
    StorylineSample(
        label="AI knowledge API v9",
        input_path=(
            paths.MODEL_DRY_RUNS_DIR
            / "anny_api_experiments"
            / "anny_api_experiment_ai_knowledge_institution_v9"
            / "parsed_storyline.json"
        ),
        output_path=DEFAULT_SAMPLE_DIR / "ai_knowledge_institution_api_v9.md",
        description="Controlled API experiment output, not production.",
        failure_manifest_path=(
            paths.MODEL_DRY_RUNS_DIR
            / "anny_api_experiments"
            / "anny_api_experiment_ai_knowledge_institution_v9"
            / "manifest.json"
        ),
    ),
    StorylineSample(
        label="Productive finance API v1",
        input_path=(
            paths.MODEL_DRY_RUNS_DIR
            / "anny_api_experiments"
            / "anny_api_experiment_productive_finance_policy_v1"
            / "parsed_storyline.json"
        ),
        output_path=DEFAULT_SAMPLE_DIR / "productive_finance_api_v1.md",
        description="Controlled API experiment output, not production.",
        failure_manifest_path=(
            paths.MODEL_DRY_RUNS_DIR
            / "anny_api_experiments"
            / "anny_api_experiment_productive_finance_policy_v1"
            / "manifest.json"
        ),
    ),
]


def _load_json(path: Path) -> dict[str, Any]:
    with path.open(encoding="utf-8") as source:
        payload = json.load(source)
    if not isinstance(payload, dict):
        raise ValueError(f"Expected JSON object at {path}")
    return payload


def _all_slides(storyline: dict[str, Any]) -> list[dict[str, Any]]:
    return [
        slide
        for section in storyline.get("sections", [])
        for slide in section.get("slides", [])
        if isinstance(slide, dict)
    ]


def _count_source_urls(storyline: dict[str, Any]) -> int:
    return sum(len(slide.get("source_urls", [])) for slide in _all_slides(storyline))


def _count_flag(storyline: dict[str, Any], field: str) -> int:
    return sum(1 for slide in _all_slides(storyline) if slide.get(field) is True)


def _body_lines(body: Any) -> list[str]:
    if isinstance(body, list):
        return [str(item) for item in body]
    if body is None:
        return []
    return [str(body)]


def _as_list(value: Any) -> list[Any]:
    return value if isinstance(value, list) else []


def _manifest_summary(path: Path | None) -> dict[str, Any]:
    if path is None or not path.exists():
        return {}
    return _load_json(path)


def render_storyline_markdown(
    storyline: dict[str, Any],
    *,
    label: str,
    description: str,
    manifest: dict[str, Any] | None = None,
) -> str:
    manifest = manifest or {}
    slides = _all_slides(storyline)
    lines = [
        f"# {storyline.get('title') or label}",
        "",
        "> 이 문서는 production Anny output이 아니라 manual/API dry-run sample입니다.",
        "> source attached는 fact-check complete를 의미하지 않습니다.",
        "",
        "## Summary",
        "",
        f"- label: {label}",
        f"- description: {description}",
        f"- sections: {len(storyline.get('sections', []))}",
        f"- slides: {len(slides)}",
        f"- source_urls: {_count_source_urls(storyline)}",
        f"- needs_source: {_count_flag(storyline, 'needs_source')}",
        f"- needs_fact_check: {_count_flag(storyline, 'needs_fact_check')}",
        f"- risk_flags: {_as_list(storyline.get('risk_flags'))}",
        f"- failure_modes: {manifest.get('failure_modes', [])}",
        f"- schema_valid: {manifest.get('schema_valid', 'n/a')}",
        f"- hygiene_passed: {manifest.get('hygiene_passed', 'n/a')}",
        "",
    ]
    required_fact_checks = _as_list(storyline.get("required_fact_checks"))
    if required_fact_checks:
        lines.extend(["## Required Fact Checks", ""])
        lines.extend(f"- {item}" for item in required_fact_checks)
        lines.append("")
    for section_index, section in enumerate(storyline.get("sections", []), start=1):
        section_title = section.get("section_title") or f"Section {section_index}"
        lines.extend([f"## Section {section_index}. {section_title}", ""])
        for local_order, slide in enumerate(section.get("slides", []), start=1):
            if not isinstance(slide, dict):
                continue
            slide_no = slide.get("slide_no") or local_order
            headline = slide.get("headline") or "(untitled)"
            lines.extend([f"### Slide {slide_no}. {headline}", ""])
            lines.extend(
                [
                    f"- type: {slide.get('slide_type')}",
                    f"- covers_key_beats: {_as_list(slide.get('covers_key_beats'))}",
                    f"- key_beat_anchors_used: {_as_list(slide.get('key_beat_anchors_used'))}",
                    f"- needs_source: {bool(slide.get('needs_source'))}",
                    f"- needs_fact_check: {bool(slide.get('needs_fact_check'))}",
                    f"- fact_check_kind: {slide.get('fact_check_kind')}",
                    f"- fact_check_priority: {slide.get('fact_check_priority')}",
                    f"- required_before_broadcast: {slide.get('required_before_broadcast')}",
                    "",
                    "Body:",
                ]
            )
            body = _body_lines(slide.get("body"))
            lines.extend(f"- {item}" for item in body) if body else lines.append("-")
            source_urls = _as_list(slide.get("source_urls"))
            if source_urls:
                lines.extend(["", "Sources:"])
                lines.extend(f"- {url}" for url in source_urls)
            source_refs = _as_list(slide.get("source_refs"))
            if source_refs:
                lines.extend(["", "Source refs:"])
                for ref in source_refs:
                    if not isinstance(ref, dict):
                        continue
                    lines.append(
                        "- "
                        f"{ref.get('role')}: {ref.get('use')} "
                        f"({ref.get('url')}, confidence={ref.get('confidence')}, "
                        f"manual_check_required={ref.get('manual_check_required')})"
                    )
            notes = slide.get("notes")
            if notes:
                lines.extend(["", "Notes:", str(notes)])
            if slide.get("slide_type") == "production_checklist":
                lines.extend(["", "_Internal production checklist, not a broadcast claim._"])
            lines.append("")
    return "\n".join(lines).rstrip() + "\n"


def render_storyline_sample(
    *,
    input_path: Path,
    output_path: Path,
    label: str,
    description: str,
    manifest_path: Path | None = None,
) -> Path:
    storyline = _load_json(input_path)
    manifest = _manifest_summary(manifest_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(
        render_storyline_markdown(
            storyline,
            label=label,
            description=description,
            manifest=manifest,
        ),
        encoding="utf-8",
    )
    return output_path


def render_default_samples(output_dir: Path = DEFAULT_SAMPLE_DIR) -> list[Path]:
    rendered: list[Path] = []
    for sample in DEFAULT_SAMPLES:
        output_path = output_dir / sample.output_path.name
        rendered.append(
            render_storyline_sample(
                input_path=sample.input_path,
                output_path=output_path,
                label=sample.label,
                description=sample.description,
                manifest_path=sample.failure_manifest_path,
            )
        )
    readme = output_dir / "README.md"
    readme.write_text(_samples_readme(rendered), encoding="utf-8")
    rendered.append(readme)
    return rendered


def _samples_readme(paths_rendered: list[Path]) -> str:
    names = {path.name for path in paths_rendered}
    lines = [
        "# Anny Storyline Samples",
        "",
        "These Markdown files are human-readable dry-run samples. They are not",
        "production Anny output and are not broadcast-ready scripts.",
        "",
        "Important interpretation rules:",
        "",
        "- `needs_source=true` means the slide still needs evidence before use.",
        "- `needs_fact_check=true` means attached sources are not enough for broadcast.",
        "- source attached does not mean fact-check complete.",
        "- API samples are controlled experiments, not a production agent.",
        "",
        "Recommended reading order:",
        "",
        "1. `ai_knowledge_institution_manual_enriched.md`",
        "2. `productive_finance_manual_enriched.md`",
        "3. `ai_knowledge_institution_api_v9.md`",
        "4. `productive_finance_api_v1.md`",
        "",
        "Generated files:",
        "",
    ]
    lines.extend(f"- `{name}`" for name in sorted(names))
    return "\n".join(lines) + "\n"


@app.callback(invoke_without_command=True)
def main(
    input_path: Annotated[
        Path | None,
        typer.Option("--input", help="Single storyline JSON to render."),
    ] = None,
    output_path: Annotated[
        Path | None,
        typer.Option("--output", help="Markdown output path for single render."),
    ] = None,
    manifest_path: Annotated[
        Path | None,
        typer.Option("--manifest", help="Optional validation manifest."),
    ] = None,
    output_dir: Annotated[
        Path,
        typer.Option("--output-dir", help="Default sample output directory."),
    ] = DEFAULT_SAMPLE_DIR,
) -> None:
    if input_path:
        if output_path is None:
            raise typer.BadParameter("--output is required with --input")
        rendered = render_storyline_sample(
            input_path=input_path,
            output_path=output_path,
            label=input_path.stem,
            description="Single rendered storyline sample.",
            manifest_path=manifest_path,
        )
        console.print(f"[green]Rendered {rendered}.[/green]")
        return
    rendered = render_default_samples(output_dir=output_dir)
    console.print(f"[green]Rendered {len(rendered)} anny storyline sample files.[/green]")


if __name__ == "__main__":
    app()
