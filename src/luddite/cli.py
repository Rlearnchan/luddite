"""Command line entrypoints for Luddite developer tooling."""

import typer

from luddite.agents.jibi.append_to_sheet import app as append_jibi_sheet_app
from luddite.agents.jibi.daily_digest import app as jibi_digest_app
from luddite.agents.jibi.normalize_candidates import app as normalize_candidates_app
from luddite.agents.jibi.render_daily_digest import app as render_daily_digest_app
from luddite.agents.jibi.score_candidates import app as score_candidates_app
from luddite.collectors.manual_article_importer import app as import_articles_app
from luddite.doctor import run_corpus_doctor, run_doctor
from luddite.eval.anny_reconstruction_eval import app as anny_reconstruction_eval_app
from luddite.eval.jibi_seed_eval import app as jibi_seed_eval_app
from luddite.eval.piti_deck_plan_eval import app as piti_deck_plan_eval_app
from luddite.eval.validate_golden import app as validate_golden_app
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
app.add_typer(validate_golden_app, name="validate-golden")
app.add_typer(jibi_seed_eval_app, name="eval-jibi-seeds")
app.add_typer(anny_reconstruction_eval_app, name="eval-anny-reconstruction")
app.add_typer(piti_deck_plan_eval_app, name="eval-piti-deck-plan")
app.add_typer(import_articles_app, name="import-articles")
app.add_typer(normalize_candidates_app, name="normalize-candidates")
app.add_typer(score_candidates_app, name="score-candidates")
app.add_typer(render_daily_digest_app, name="render-daily-digest")
app.add_typer(jibi_digest_app, name="jibi-digest")
app.add_typer(append_jibi_sheet_app, name="append-jibi-sheet")


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
