"""Validate golden reconstruction fixtures."""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Annotated, Any

import typer
from jsonschema import Draft202012Validator
from rich.console import Console
from rich.table import Table

from luddite import paths

app = typer.Typer(no_args_is_help=False)
console = Console()

SKIP_SOURCE_SLIDE_TYPES = {"title", "section_title"}


@dataclass
class ValidationIssue:
    path: Path
    message: str


def _load_json(path: Path) -> Any:
    with path.open(encoding="utf-8") as source:
        return json.load(source)


def _schema_validator(schema_name: str) -> Draft202012Validator:
    schema = _load_json(paths.SPECS_DIR / schema_name)
    return Draft202012Validator(schema)


def _fixture_paths(directory: Path) -> list[Path]:
    if not directory.exists():
        return []
    return sorted(directory.glob("*.json"))


def _issue(path: Path, message: str) -> ValidationIssue:
    return ValidationIssue(path=path, message=message)


def _validate_anny_storyline(path: Path, payload: dict[str, Any]) -> list[ValidationIssue]:
    issues: list[ValidationIssue] = []
    sections = payload.get("sections", [])
    if len(sections) < 3:
        issues.append(_issue(path, "sections count must be >= 3"))
    if not payload.get("required_fact_checks"):
        issues.append(_issue(path, "required_fact_checks must be present and non-empty"))
    if "risk_flags" not in payload:
        issues.append(_issue(path, "risk_flags must be present"))

    for section_index, section in enumerate(sections, start=1):
        for slide_index, slide in enumerate(section.get("slides", []), start=1):
            location = f"section {section_index} slide {slide_index}"
            for field in ("headline", "body", "notes"):
                if field not in slide:
                    issues.append(_issue(path, f"{location}: missing {field}"))
            source_urls = set(slide.get("source_urls", []))
            image_urls = set(slide.get("image_urls", []))
            overlap = source_urls & image_urls
            if overlap:
                issues.append(_issue(path, f"{location}: source/image URL overlap: {overlap}"))
            if slide.get("slide_type") not in SKIP_SOURCE_SLIDE_TYPES:
                has_source = bool(slide.get("source_urls"))
                allows_missing_source = bool(slide.get("needs_source"))
                if not has_source and not allows_missing_source:
                    issues.append(
                        _issue(
                            path,
                            f"{location}: factual slide needs source_urls or needs_source=true",
                        )
                    )
    return issues


def _validate_deck_plan(path: Path, payload: dict[str, Any]) -> list[ValidationIssue]:
    issues: list[ValidationIssue] = []
    slides = payload.get("slides", [])
    for index, slide in enumerate(slides, start=1):
        location = f"slide {index}"
        for field in ("headline", "body", "notes"):
            if field not in slide:
                issues.append(_issue(path, f"{location}: missing {field}"))
    return issues


def validate_golden(base_dir: Path = paths.EVAL_DIR / "golden_cases") -> list[ValidationIssue]:
    issues: list[ValidationIssue] = []
    anny_validator = _schema_validator("anny_storyline_schema.json")
    deck_validator = _schema_validator("deck_schema.json")

    anny_dir = base_dir / "anny_storylines"
    deck_dir = base_dir / "deck_plans"
    anny_paths = _fixture_paths(anny_dir)
    deck_paths = _fixture_paths(deck_dir)

    if not anny_paths:
        issues.append(_issue(anny_dir, "no anny storyline fixtures found"))
    if not deck_paths:
        issues.append(_issue(deck_dir, "no deck plan fixtures found"))

    for path in anny_paths:
        payload = _load_json(path)
        for error in sorted(anny_validator.iter_errors(payload), key=str):
            issues.append(_issue(path, f"schema: {error.message}"))
        if not list(anny_validator.iter_errors(payload)):
            issues.extend(_validate_anny_storyline(path, payload))

    for path in deck_paths:
        payload = _load_json(path)
        for error in sorted(deck_validator.iter_errors(payload), key=str):
            issues.append(_issue(path, f"schema: {error.message}"))
        if not list(deck_validator.iter_errors(payload)):
            issues.extend(_validate_deck_plan(path, payload))

    return issues


def _print_issues(issues: list[ValidationIssue]) -> None:
    if not issues:
        console.print("[green]Golden fixtures passed validation.[/green]")
        return

    table = Table(title="Golden Fixture Validation Issues")
    table.add_column("File")
    table.add_column("Issue")
    for issue in issues:
        table.add_row(str(issue.path.relative_to(paths.REPO_ROOT)), issue.message)
    console.print(table)


@app.callback(invoke_without_command=True)
def main(
    base_dir: Annotated[
        Path,
        typer.Option("--base-dir", help="Golden cases directory."),
    ] = paths.EVAL_DIR / "golden_cases",
) -> None:
    """Validate golden reconstruction fixtures."""
    issues = validate_golden(base_dir)
    _print_issues(issues)
    raise typer.Exit(1 if issues else 0)


if __name__ == "__main__":
    app()
