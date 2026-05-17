"""End-to-end local/manual jibi Daily Digest pipeline."""

from __future__ import annotations

from pathlib import Path
from typing import Annotated

import typer
from rich.console import Console

from luddite import paths
from luddite.agents.jibi.normalize_candidates import normalize_candidates
from luddite.agents.jibi.render_daily_digest import render_daily_digest
from luddite.agents.jibi.score_candidates import score_candidates
from luddite.collectors.manual_article_importer import import_articles

app = typer.Typer(no_args_is_help=False)
console = Console()


def run_jibi_digest(
    input_dir: Path = paths.ARTICLE_INBOX_DIR,
    digest_date: str | None = None,
    limit: int = 10,
) -> tuple[Path, Path]:
    import_articles(input_dir=input_dir)
    normalize_candidates()
    score_candidates()
    md_path, csv_path, _top = render_daily_digest(digest_date=digest_date, limit=limit)
    return md_path, csv_path


@app.callback(invoke_without_command=True)
def main(
    input_dir: Annotated[
        Path,
        typer.Option("--input-dir", help="Directory containing article JSONL/CSV files."),
    ] = paths.ARTICLE_INBOX_DIR,
    digest_date: Annotated[
        str | None,
        typer.Option("--date", help="Digest date in YYYY-MM-DD."),
    ] = None,
    limit: Annotated[int, typer.Option("--limit", help="Number of candidates.")] = 10,
) -> None:
    md_path, csv_path = run_jibi_digest(input_dir=input_dir, digest_date=digest_date, limit=limit)
    console.print(f"[green]jibi digest ready: {md_path}[/green]")
    console.print(f"[green]Sheet append preview: {csv_path}[/green]")


if __name__ == "__main__":
    app()
