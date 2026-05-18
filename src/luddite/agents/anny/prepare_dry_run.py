"""Prepare manual anny storyline dry-run inputs without calling an LLM."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Annotated, Any

import typer
from rich.console import Console

from luddite import paths
from luddite.utils.jsonl import read_jsonl

app = typer.Typer(no_args_is_help=False)
console = Console()

CASES_PATH = paths.EVAL_DIR / "golden_cases" / "anny_dry_run_cases.json"
DEFAULT_CASE_ID = "anny_dry_run_ai_knowledge_institution_v1"
DEFAULT_INPUT_BUNDLE_JSON = (
    paths.ANNY_STORYLINE_DRY_RUN_DIR / "ai_knowledge_institution_input_bundle.json"
)
DEFAULT_STORYLINE_JSON = (
    paths.ANNY_STORYLINE_DRY_RUN_DIR / "ai_knowledge_institution_gpt_pro_storyline.json"
)


def _load_json(path: Path) -> Any:
    with path.open(encoding="utf-8") as source:
        return json.load(source)


def prepare_anny_dry_run(
    *,
    case_id: str = DEFAULT_CASE_ID,
    cases_path: Path = CASES_PATH,
    bundles_path: Path = paths.ANNY_INPUT_BUNDLES_JSONL,
    output_bundle_path: Path = DEFAULT_INPUT_BUNDLE_JSON,
    expected_storyline_path: Path = DEFAULT_STORYLINE_JSON,
) -> dict[str, Any]:
    cases = _load_json(cases_path)["cases"]
    case = next((item for item in cases if item["case_id"] == case_id), None)
    if case is None:
        raise ValueError(f"Unknown dry-run case_id: {case_id}")
    bundles = read_jsonl(bundles_path) if bundles_path.exists() else []
    bundle = next((item for item in bundles if item["bundle_id"] == case["bundle_id"]), None)
    if bundle is None:
        raise ValueError(f"Bundle {case['bundle_id']} not found in {bundles_path}")

    output_bundle_path.parent.mkdir(parents=True, exist_ok=True)
    output_bundle_path.write_text(
        json.dumps(bundle, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    expected_storyline_path.parent.mkdir(parents=True, exist_ok=True)
    return {
        "case_id": case_id,
        "bundle_id": bundle["bundle_id"],
        "input_bundle_path": str(output_bundle_path),
        "expected_storyline_path": str(expected_storyline_path),
    }


@app.callback(invoke_without_command=True)
def main(
    case_id: Annotated[
        str,
        typer.Option("--case-id", help="Dry-run case id to prepare."),
    ] = DEFAULT_CASE_ID,
    cases_path: Annotated[
        Path,
        typer.Option("--cases", help="Anny dry-run cases JSON path."),
    ] = CASES_PATH,
    bundles_path: Annotated[
        Path,
        typer.Option("--bundles", help="Anny input bundles JSONL path."),
    ] = paths.ANNY_INPUT_BUNDLES_JSONL,
    output_bundle_path: Annotated[
        Path,
        typer.Option("--output-bundle", help="Single input bundle JSON output path."),
    ] = DEFAULT_INPUT_BUNDLE_JSON,
    expected_storyline_path: Annotated[
        Path,
        typer.Option("--expected-storyline", help="Expected GPT Pro storyline JSON path."),
    ] = DEFAULT_STORYLINE_JSON,
) -> None:
    result = prepare_anny_dry_run(
        case_id=case_id,
        cases_path=cases_path,
        bundles_path=bundles_path,
        output_bundle_path=output_bundle_path,
        expected_storyline_path=expected_storyline_path,
    )
    console.print(
        "[green]Prepared anny dry-run input bundle at "
        f"{result['input_bundle_path']}.[/green]"
    )
    console.print(f"[cyan]Expected manual output path: {result['expected_storyline_path']}[/cyan]")


if __name__ == "__main__":
    app()
