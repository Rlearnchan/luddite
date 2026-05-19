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
RENDER_MODES = {"compact", "audit", "both"}


@dataclass(frozen=True)
class StorylineSample:
    label: str
    output_type: str
    input_path: Path
    output_path: Path
    description: str
    failure_manifest_path: Path | None = None


DEFAULT_SAMPLES = [
    StorylineSample(
        label="AI knowledge manual enriched",
        output_type="manual_enriched",
        input_path=(
            paths.ANNY_STORYLINE_DRY_RUN_DIR
            / "ai_knowledge_institution_gpt_pro_storyline_enriched.json"
        ),
        output_path=DEFAULT_SAMPLE_DIR / "ai_knowledge_institution_manual_enriched.md",
        description="GPT Pro enriched manual dry-run sample.",
    ),
    StorylineSample(
        label="Productive finance manual enriched",
        output_type="manual_enriched",
        input_path=(
            paths.ANNY_STORYLINE_DRY_RUN_DIR
            / "productive_finance_policy_gpt_pro_storyline_enriched.json"
        ),
        output_path=DEFAULT_SAMPLE_DIR / "productive_finance_manual_enriched.md",
        description="GPT Pro enriched manual dry-run sample.",
    ),
    StorylineSample(
        label="AI knowledge API v9",
        output_type="api_experiment",
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
        output_type="api_experiment",
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


def _story_seed_title(storyline: dict[str, Any], label: str) -> str:
    return str(storyline.get("title") or label)


def _summary_lines(
    storyline: dict[str, Any],
    *,
    label: str,
    output_type: str,
    description: str,
    manifest: dict[str, Any],
) -> list[str]:
    slides = _all_slides(storyline)
    return [
        "## Summary",
        "",
        f"- story_seed_title: {_story_seed_title(storyline, label)}",
        f"- label: {label}",
        f"- output_type: {output_type}",
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
        "- readiness: not production-ready",
        "",
    ]


def render_storyline_markdown(
    storyline: dict[str, Any],
    *,
    label: str,
    output_type: str,
    description: str,
    mode: str = "audit",
    manifest: dict[str, Any] | None = None,
) -> str:
    manifest = manifest or {}
    if mode not in {"compact", "audit"}:
        raise ValueError(f"Unsupported render mode: {mode}")
    story_seed_title = _story_seed_title(storyline, label)
    lines = [
        f"# {story_seed_title}",
        "",
        "> 이 문서는 production Anny output이 아니라 manual/API dry-run sample입니다.",
        "> source attached는 fact-check complete를 의미하지 않습니다.",
        "",
    ]
    lines.extend(
        _summary_lines(
            storyline,
            label=label,
            output_type=output_type,
            description=description,
            manifest=manifest,
        )
    )
    required_fact_checks = _as_list(storyline.get("required_fact_checks"))
    if required_fact_checks:
        lines.extend(["## Required Fact Checks", ""])
        lines.extend(f"- {item}" for item in required_fact_checks)
        lines.append("")
    if mode == "compact":
        lines.extend(_compact_sections(storyline))
        return "\n".join(lines).rstrip() + "\n"
    lines.extend(_audit_sections(storyline))
    return "\n".join(lines).rstrip() + "\n"


def _audit_sections(storyline: dict[str, Any]) -> list[str]:
    lines: list[str] = []
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
    return lines


def _compact_sections(storyline: dict[str, Any]) -> list[str]:
    lines: list[str] = []
    global_slide_no = 0
    for section_index, section in enumerate(storyline.get("sections", []), start=1):
        section_title = section.get("section_title") or f"Section {section_index}"
        lines.extend([f"## Section {section_index}. {section_title}", ""])
        for local_order, slide in enumerate(section.get("slides", []), start=1):
            if not isinstance(slide, dict):
                continue
            global_slide_no += 1
            headline = slide.get("headline") or "(untitled)"
            lines.extend([f"### {global_slide_no:02d}. {headline}", ""])
            if slide.get("slide_type"):
                lines.append(f"- type: {slide.get('slide_type')}")
            if local_order:
                lines.append(f"- section_slide: {local_order}")
            body = _body_lines(slide.get("body"))
            if body:
                lines.extend(["", "Body:"])
                lines.extend(f"- {item}" for item in body)
            lines.extend(_compact_sources(slide))
            lines.extend(_compact_check_lines(slide))
            note = _compact_note(slide.get("notes"))
            if note:
                lines.extend(["", f"Note: {note}"])
            if slide.get("slide_type") == "production_checklist":
                lines.extend(["", "_Internal production checklist, not a broadcast claim._"])
            lines.append("")
    return lines


def _compact_sources(slide: dict[str, Any]) -> list[str]:
    urls = [str(url) for url in _as_list(slide.get("source_urls")) if url]
    if not urls:
        return []
    visible = urls[:2]
    lines = ["", "Sources:"]
    lines.extend(f"- {url}" for url in visible)
    if len(urls) > len(visible):
        lines.append(f"- ... +{len(urls) - len(visible)} more")
    return lines


def _compact_check_lines(slide: dict[str, Any]) -> list[str]:
    checks = [
        f"needs_source={bool(slide.get('needs_source'))}",
        f"needs_fact_check={bool(slide.get('needs_fact_check'))}",
    ]
    if slide.get("required_before_broadcast") is not None:
        checks.append(f"before_broadcast={slide.get('required_before_broadcast')}")
    if slide.get("fact_check_kind"):
        checks.append(f"kind={slide.get('fact_check_kind')}")
    if slide.get("fact_check_priority"):
        checks.append(f"priority={slide.get('fact_check_priority')}")
    return ["", "Check:", f"- {', '.join(checks)}"]


def _compact_note(notes: Any, limit: int = 180) -> str:
    if not notes:
        return ""
    text = " ".join(str(notes).split())
    if len(text) <= limit:
        return text
    return text[: limit - 3].rstrip() + "..."


def render_storyline_sample(
    *,
    input_path: Path,
    output_path: Path,
    label: str,
    description: str,
    output_type: str = "single_render",
    mode: str = "audit",
    manifest_path: Path | None = None,
) -> Path:
    storyline = _load_json(input_path)
    manifest = _manifest_summary(manifest_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(
        render_storyline_markdown(
            storyline,
            label=label,
            output_type=output_type,
            description=description,
            mode=mode,
            manifest=manifest,
        ),
        encoding="utf-8",
    )
    return output_path


def render_default_samples(
    output_dir: Path = DEFAULT_SAMPLE_DIR,
    *,
    mode: str = "both",
) -> list[Path]:
    if mode not in RENDER_MODES:
        raise ValueError(f"Unsupported render mode: {mode}")
    rendered: list[Path] = []
    if mode in {"audit", "both"}:
        for sample in DEFAULT_SAMPLES:
            output_path = output_dir / sample.output_path.name
            rendered.append(
                render_storyline_sample(
                    input_path=sample.input_path,
                    output_path=output_path,
                    label=sample.label,
                    output_type=sample.output_type,
                    description=sample.description,
                    mode="audit",
                    manifest_path=sample.failure_manifest_path,
                )
            )
    if mode in {"compact", "both"}:
        compact_dir = output_dir / "compact"
        for sample in DEFAULT_SAMPLES:
            rendered.append(
                render_storyline_sample(
                    input_path=sample.input_path,
                    output_path=compact_dir / sample.output_path.name,
                    label=sample.label,
                    output_type=sample.output_type,
                    description=sample.description,
                    mode="compact",
                    manifest_path=sample.failure_manifest_path,
                )
            )
    readme = output_dir / "README.md"
    readme.write_text(_samples_readme(rendered, output_dir=output_dir), encoding="utf-8")
    rendered.append(readme)
    return rendered


def _samples_readme(paths_rendered: list[Path], *, output_dir: Path) -> str:
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
        "- Productive finance API v1 still has stricter-validator failures.",
        "",
        "Recommended reading order:",
        "",
        "1. `compact/ai_knowledge_institution_manual_enriched.md`",
        "2. `compact/productive_finance_manual_enriched.md`",
        "3. Audit samples in this directory are for development review.",
        "4. API samples are controlled experiments, not production examples.",
        "",
        "Usage guidance:",
        "",
        "- Use `compact/` for research-team reading.",
        "- Use root-level audit samples for validator and source-hygiene review.",
        (
            "- Do not present `productive_finance_api_v1.md` as a product example; "
            "it is failure analysis."
        ),
        "",
        "Generated files:",
        "",
    ]
    for path in sorted(paths_rendered, key=lambda item: str(item)):
        if path.name == "README.md":
            continue
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
    mode: Annotated[
        str,
        typer.Option("--mode", help="Render mode: compact, audit, or both."),
    ] = "both",
) -> None:
    if mode not in RENDER_MODES:
        raise typer.BadParameter("--mode must be compact, audit, or both")
    if input_path:
        if mode == "both":
            raise typer.BadParameter("--mode must be compact or audit with --input")
        if output_path is None:
            raise typer.BadParameter("--output is required with --input")
        rendered = render_storyline_sample(
            input_path=input_path,
            output_path=output_path,
            label=input_path.stem,
            output_type="single_render",
            description="Single rendered storyline sample.",
            mode=mode,
            manifest_path=manifest_path,
        )
        console.print(f"[green]Rendered {rendered}.[/green]")
        return
    rendered = render_default_samples(output_dir=output_dir, mode=mode)
    console.print(f"[green]Rendered {len(rendered)} anny storyline sample files.[/green]")


if __name__ == "__main__":
    app()
