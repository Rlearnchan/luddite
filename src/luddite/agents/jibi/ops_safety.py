"""Safety checks for manual Jibi operating runs."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Annotated

import typer
from rich.console import Console

app = typer.Typer(no_args_is_help=False)
console = Console()

DEFAULT_APPEND_MODE = "dry_run"
STAGING_APPEND_MODE = "staging_append"
STAGING_REPLACE_MODE = "staging_replace"
VALID_APPEND_MODES = {DEFAULT_APPEND_MODE, STAGING_APPEND_MODE, STAGING_REPLACE_MODE}
JIBI_STAGING_SHEET = "jibi 후보"
FORBIDDEN_TOPIC_SHEET = "주제 찾기"


@dataclass(frozen=True)
class JibiOpsSafetyConfig:
    append_mode: str = DEFAULT_APPEND_MODE
    target_sheet_name: str = JIBI_STAGING_SHEET

    @property
    def dry_run(self) -> bool:
        return self.append_mode == DEFAULT_APPEND_MODE

    @property
    def replace_existing(self) -> bool:
        return self.append_mode == STAGING_REPLACE_MODE


def normalize_append_mode(value: str | None) -> str:
    mode = (value or DEFAULT_APPEND_MODE).strip()
    if mode not in VALID_APPEND_MODES:
        raise ValueError(
            "JIBI_APPEND_MODE must be one of: "
            + ", ".join(sorted(VALID_APPEND_MODES))
        )
    return mode


def validate_ops_safety(
    *,
    append_mode: str | None = None,
    target_sheet_name: str | None = None,
) -> JibiOpsSafetyConfig:
    mode = normalize_append_mode(append_mode)
    sheet = (target_sheet_name or JIBI_STAGING_SHEET).strip()
    if sheet == FORBIDDEN_TOPIC_SHEET:
        raise ValueError("Jibi manual ops must never append to `주제 찾기`.")
    if mode in {STAGING_APPEND_MODE, STAGING_REPLACE_MODE} and sheet != JIBI_STAGING_SHEET:
        raise ValueError(
            "real Jibi sheet writes may only target the exact `jibi 후보` sheet."
        )
    return JibiOpsSafetyConfig(append_mode=mode, target_sheet_name=sheet)


@app.callback(invoke_without_command=True)
def main(
    append_mode: Annotated[
        str | None,
        typer.Option(
            "--append-mode",
            help="Manual ops append mode: dry_run or staging_append.",
        ),
    ] = None,
    target_sheet_name: Annotated[
        str | None,
        typer.Option(
            "--target-sheet",
            help="Google Sheet tab targeted by the manual ops runner.",
        ),
    ] = None,
) -> None:
    try:
        config = validate_ops_safety(
            append_mode=append_mode,
            target_sheet_name=target_sheet_name,
        )
    except ValueError as exc:
        console.print(f"[red]Jibi ops safety check failed: {exc}[/red]")
        raise typer.Exit(1) from exc
    console.print(
        "[green]Jibi ops safety check passed "
        f"(append_mode={config.append_mode}, "
        f"target_sheet={config.target_sheet_name}).[/green]"
    )


if __name__ == "__main__":
    app()
