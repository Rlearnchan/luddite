# Jibi Source Experiment Pack

This is a report-only operating note for controlled source expansion. It does
not change `config/rss_collection_allowlist.yaml`, scoring thresholds, or the
visible `Jibi` sheet schema.

## Guardian Section Trial

Use only the section feeds already present in `config/sources.yaml`:

- `guardian_business`
- `guardian_technology`
- `guardian_environment`

Do not enable broad Guardian international/world/global-development/health
feeds for daily collection. For an experiment, generate a temporary allowlist
and command plan:

```bash
make jibi-source-experiment-guardian JIBI_DATE=2026-05-25
```

This writes a plan report under `outputs/reports/` and a temporary allowlist
under `outputs/experiments/guardian_sections_v1/YYYY-MM-DD/`. It does not edit
`config/rss_collection_allowlist.yaml` and does not write the Google Sheet.

The generated fetch command uses the temporary allowlist explicitly:

```bash
PYTHONPATH=src .venv/bin/python -m luddite fetch-rss-articles \
  --date 2026-05-25 \
  --allowlist-path outputs/experiments/guardian_sections_v1/2026-05-25/rss_collection_allowlist.yaml \
  --output outputs/experiments/guardian_sections_v1/2026-05-25/rss_2026-05-25.jsonl \
  --report outputs/experiments/guardian_sections_v1/2026-05-25/rss_ingest_2026-05-25.md \
  --skip-history
```

After rendering an experiment board, compare it against the baseline:

```bash
PYTHONPATH=src .venv/bin/python -m luddite compare-jibi-source-experiment \
  --date 2026-05-25 \
  --baseline-metadata outputs/daily_digest/2026-05-25_bundle_review_sheet_metadata.json \
  --experiment-metadata outputs/daily_digest/2026-05-25_guardian_experiment_metadata.json \
  --baseline-triage outputs/reports/jibi_board_triage_2026-05-25.json \
  --experiment-triage outputs/reports/jibi_board_triage_guardian_2026-05-25.json
```

The comparison report now includes triage-label, confidence, next-action,
syuka-similarity, promo/bulletin, and so-what distributions when triage metadata
is available. Source recommendations are advisory and include confidence plus
reasons such as `no_reviewed_rows_yet`, `syuka_duplicate_heavy`, or
`weak_audience_bridge`.

## Survey / Stat / Numbers Hooks

Treat these as manual or probe sources first:

- YouGov: survey signal and odd public-opinion hooks
- Pew Research: demographics and public-opinion numbers
- Gallup: public-opinion numbers
- Statista: chart evidence and numbers hooks
- Our World in Data: chart evidence and global context
- OECD/KOSIS: numbers evidence

These should not become ordinary daily RSS sources until the team sees whether
they create actual story seeds rather than detached chart trivia.

## Nikkei Asia

Nikkei Asia remains a high-value manual/subscription source. Use manual input or
a subscription-compliant workflow first. Do not auto-fetch unless terms and feed
access are verified.

## Guardrails

- Run source experiments as temporary batches.
- Keep source-role caps active.
- Compare baseline and experiment boards before changing defaults.
- Use review feedback and syuka similarity as advisory signals only.
- Do not auto-edit the allowlist based on one run.
- Run 2-3 more baseline days before changing scoring thresholds.
