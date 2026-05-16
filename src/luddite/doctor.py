"""Local environment checks for the Luddite scaffold."""

from __future__ import annotations

from dataclasses import dataclass
from importlib.util import find_spec
from pathlib import Path

from rich.console import Console
from rich.table import Table

from luddite import paths


@dataclass(frozen=True)
class Check:
    name: str
    ok: bool
    detail: str


EXPECTED_DIRS = [
    paths.DOCS_DIR,
    paths.DOCS_DIR / "appendix",
    paths.SPECS_DIR,
    paths.DATA_DIR,
    paths.STORYLINE_RAW_DIR,
    paths.LATEST_PPT_RAW_DIR,
    paths.LEGACY_PPT_RAW_DIR,
    paths.SHEETS_DIR,
    paths.SHEETS_RAW_DIR,
    paths.SHEETS_PARSED_DIR,
    paths.NOTION_DIR,
    paths.MANIFESTS_DIR,
    paths.PROMPTS_DIR / "jibi",
    paths.PROMPTS_DIR / "anny",
    paths.PROMPTS_DIR / "piti",
    paths.PROMPTS_DIR / "shared",
    paths.EVAL_DIR / "golden_cases",
    paths.EVAL_DIR / "reports",
]

EXPECTED_IMPORTS = [
    ("jsonschema", "jsonschema"),
    ("openpyxl", "openpyxl"),
    ("pydantic", "pydantic"),
    ("python-pptx", "pptx"),
    ("rich", "rich"),
    ("striprtf", "striprtf"),
    ("typer", "typer"),
]


def _count_files(directory: Path, pattern: str) -> int:
    if not directory.exists():
        return 0
    return sum(1 for path in directory.glob(pattern) if path.is_file())


def collect_checks() -> list[Check]:
    checks: list[Check] = []

    for directory in EXPECTED_DIRS:
        checks.append(
            Check(
                name=f"dir:{directory.relative_to(paths.REPO_ROOT)}",
                ok=directory.is_dir(),
                detail="exists" if directory.is_dir() else "missing",
            )
        )

    for label, import_name in EXPECTED_IMPORTS:
        spec = find_spec(import_name)
        checks.append(
            Check(
                name=f"import:{label}",
                ok=spec is not None,
                detail="available" if spec is not None else f"missing import {import_name}",
            )
        )

    storyline_count = _count_files(paths.STORYLINE_RAW_DIR, "*.rtf")
    checks.append(
        Check(
            name="corpus:storylines",
            ok=storyline_count == 43,
            detail=f"{storyline_count}/43 RTF files",
        )
    )

    latest_ppt_count = _count_files(paths.LATEST_PPT_RAW_DIR, "*.pptx")
    checks.append(
        Check(
            name="corpus:latest_ppt",
            ok=latest_ppt_count == 8,
            detail=f"{latest_ppt_count}/8 PPTX files",
        )
    )

    return checks


def run_doctor() -> bool:
    console = Console()
    checks = collect_checks()

    table = Table(title="Luddite Doctor")
    table.add_column("Check")
    table.add_column("Status")
    table.add_column("Detail")

    for check in checks:
        table.add_row(check.name, "OK" if check.ok else "FAIL", check.detail)

    console.print(table)
    return all(check.ok for check in checks)
