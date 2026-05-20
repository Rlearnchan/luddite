"""Command line entrypoints for Luddite developer tooling."""

import typer

from luddite.agents.anny.api_experiment_runner import (
    app as anny_api_experiment_app,
)
from luddite.agents.anny.api_experiment_runner import (
    run_app as run_anny_api_experiment_app,
)
from luddite.agents.anny.build_input_bundle import app as build_anny_input_bundles_app
from luddite.agents.anny.compare_dry_runs import app as compare_anny_dry_runs_app
from luddite.agents.anny.compare_enriched_dry_runs import (
    app as compare_anny_enriched_dry_runs_app,
)
from luddite.agents.anny.plan_evidence_enrichment import app as plan_anny_evidence_app
from luddite.agents.anny.prepare_dry_run import app as prepare_anny_dry_run_app
from luddite.agents.anny.render_storyline_sample import (
    app as render_anny_storyline_sample_app,
)
from luddite.agents.anny.review_fact_check import app as review_anny_fact_check_app
from luddite.agents.anny.run_storyline import app as anny_run_storyline_app
from luddite.agents.anny.slide_spec_experiment import (
    app as anny_slide_spec_experiment_app,
)
from luddite.agents.jibi.append_to_sheet import app as append_jibi_sheet_app
from luddite.agents.jibi.cluster_candidates import app as cluster_jibi_candidates_app
from luddite.agents.jibi.daily_digest import app as jibi_digest_app
from luddite.agents.jibi.normalize_candidates import app as normalize_candidates_app
from luddite.agents.jibi.render_daily_digest import app as render_daily_digest_app
from luddite.agents.jibi.score_candidates import app as score_candidates_app
from luddite.agents.piti.build_deck_plan_from_storyline import (
    app as build_piti_deck_plan_app,
)
from luddite.agents.piti.build_slide_spec_from_storyline import (
    build_app as build_piti_slide_spec_app,
)
from luddite.agents.piti.build_slide_spec_from_storyline import (
    validate_app as validate_piti_slide_spec_app,
)
from luddite.agents.piti.render_deck_storyboard import app as render_piti_storyboard_app
from luddite.agents.piti.render_pptx import app as render_piti_pptx_app
from luddite.agents.piti.render_pptx import (
    slide_spec_app as render_piti_slide_spec_pptx_app,
)
from luddite.agents.piti.render_visual_qa import app as render_piti_visual_qa_app
from luddite.analysis.compare_slideability_visual_qa import (
    app as compare_slideability_visual_qa_app,
)
from luddite.analysis.extract_pptx_style import app as extract_pptx_style_app
from luddite.analysis.render_pptx_contact_sheet import app as render_pptx_contact_sheet_app
from luddite.collectors.manual_article_importer import app as import_articles_app
from luddite.collectors.rss_item_fetcher import app as fetch_rss_articles_app
from luddite.collectors.rss_probe import app as probe_rss_sources_app
from luddite.doctor import run_corpus_doctor, run_doctor
from luddite.eval.anny_dry_run_eval import app as anny_dry_run_eval_app
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
app.add_typer(anny_dry_run_eval_app, name="validate-anny-dry-run")
app.add_typer(piti_deck_plan_eval_app, name="eval-piti-deck-plan")
app.add_typer(import_articles_app, name="import-articles")
app.add_typer(fetch_rss_articles_app, name="fetch-rss-articles")
app.add_typer(normalize_candidates_app, name="normalize-candidates")
app.add_typer(score_candidates_app, name="score-candidates")
app.add_typer(cluster_jibi_candidates_app, name="cluster-jibi-candidates")
app.add_typer(build_anny_input_bundles_app, name="build-anny-input-bundles")
app.add_typer(prepare_anny_dry_run_app, name="prepare-anny-dry-run")
app.add_typer(plan_anny_evidence_app, name="plan-anny-evidence")
app.add_typer(review_anny_fact_check_app, name="review-anny-fact-check")
app.add_typer(compare_anny_dry_runs_app, name="compare-anny-dry-runs")
app.add_typer(compare_anny_enriched_dry_runs_app, name="compare-anny-enriched-dry-runs")
app.add_typer(anny_api_experiment_app, name="validate-anny-api-experiment")
app.add_typer(run_anny_api_experiment_app, name="run-anny-api-experiment")
app.add_typer(anny_run_storyline_app, name="anny-run-storyline")
app.add_typer(anny_slide_spec_experiment_app, name="run-anny-slide-spec-experiment")
app.add_typer(render_anny_storyline_sample_app, name="render-anny-storyline-sample")
app.add_typer(build_piti_deck_plan_app, name="build-piti-deck-plan")
app.add_typer(build_piti_slide_spec_app, name="build-piti-slide-spec")
app.add_typer(validate_piti_slide_spec_app, name="validate-piti-slide-spec")
app.add_typer(render_piti_storyboard_app, name="render-piti-storyboard")
app.add_typer(render_piti_pptx_app, name="render-piti-pptx")
app.add_typer(render_piti_slide_spec_pptx_app, name="render-piti-slide-spec-pptx")
app.add_typer(render_piti_visual_qa_app, name="render-piti-visual-qa")
app.add_typer(compare_slideability_visual_qa_app, name="compare-slideability-visual-qa")
app.add_typer(render_pptx_contact_sheet_app, name="render-pptx-contact-sheet")
app.add_typer(extract_pptx_style_app, name="extract-pptx-style")
app.add_typer(render_daily_digest_app, name="render-daily-digest")
app.add_typer(jibi_digest_app, name="jibi-digest")
app.add_typer(append_jibi_sheet_app, name="append-jibi-sheet")
app.add_typer(probe_rss_sources_app, name="probe-rss-sources")


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
