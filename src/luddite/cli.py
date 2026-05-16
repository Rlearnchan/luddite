"""Command line entrypoints for Luddite developer tooling."""

import typer

from luddite.doctor import run_corpus_doctor, run_doctor
from luddite.parsers.build_corpus_manifest import app as build_corpus_manifest_app
from luddite.parsers.corpus_smoke import app as corpus_smoke_app
from luddite.parsers.fetch_sheets import app as fetch_sheets_app
from luddite.parsers.parse_pptx import app as parse_pptx_app
from luddite.parsers.parse_storylines import app as parse_storylines_app

app = typer.Typer(no_args_is_help=True)
app.add_typer(parse_storylines_app, name="parse-storylines")
app.add_typer(parse_pptx_app, name="parse-pptx")
app.add_typer(fetch_sheets_app, name="fetch-sheets")
app.add_typer(build_corpus_manifest_app, name="build-corpus-manifest")
app.add_typer(corpus_smoke_app, name="corpus-smoke")


@app.callback()
def main() -> None:
    """Luddite developer tooling."""


@app.command()
def doctor() -> None:
    """Verify repo structure and dependencies without requiring raw corpus files."""
    raise typer.Exit(0 if run_doctor() else 1)


@app.command("doctor-corpus")
def doctor_corpus() -> None:
    """Verify expected local raw corpus counts."""
    raise typer.Exit(0 if run_corpus_doctor() else 1)


if __name__ == "__main__":
    app()
