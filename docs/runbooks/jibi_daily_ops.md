# Jibi Daily Ops Runbook

This runbook covers the Jibi MVP daily workflow. It produces candidate topics,
renders a Daily Digest, and stages rows in the Google Sheet `jibi 후보` tab for
human review.

## Local Setup

```bash
make setup
make test
make doctor
```

Set Google Sheet environment variables only on the local machine:

```bash
export LUDDITE_GOOGLE_SPREADSHEET_ID="1piIsrWAHqSWBk0PwouTK1DWccX3W0Sfqf3YUptXT8QU"
export LUDDITE_GOOGLE_TARGET_SHEET="jibi 후보"
export GOOGLE_APPLICATION_CREDENTIALS="/absolute/path/to/service-account.json"
```

The service account
`jibi-001@adept-rock-496700-r0.iam.gserviceaccount.com` must be an editor on the
spreadsheet. Never commit the JSON credential file or a local path to it.

## Sample Digest

Run the deterministic example-data path:

```bash
make jibi-digest
```

Expected outputs:

```text
outputs/daily_digest/YYYY-MM-DD.md
outputs/daily_digest/YYYY-MM-DD_sheet_append_preview.csv
outputs/reports/jibi_quality_YYYY-MM-DD.md
```

## Morning Checklist

1. Run `make jibi-mvp-rss-dry-run` or the manual equivalent.
2. Inspect `outputs/daily_digest/YYYY-MM-DD.md`.
3. Inspect `outputs/daily_digest/YYYY-MM-DD_sheet_append_preview.csv`.
4. Inspect `outputs/reports/jibi_sheet_append_YYYY-MM-DD.md`.
5. Confirm zero errors, expected duplicate skips, and safe `header_status`.
6. Run explicit real append only if needed.
7. Open `jibi 후보` and fill `review_result`, `notes`, and promotion fields
   manually.

## Manual One-shot Operating Loop

The preferred MVP operating mode is a manual one-shot command, not a scheduled
morning launchd job. Run it when the MacBook is on and you are ready to review
the output:

```bash
make jibi-manual-update
```

The default mode is dry-run. It fetches date-scoped RSS, imports only that file,
normalizes, scores, clusters, renders the Daily Digest, writes the report-only
content enrichment review, then runs `append-jibi-sheet --dry-run` pinned to
`outputs/daily_digest/YYYY-MM-DD_sheet_append_preview.csv`. The runner never
uses the append command's latest-preview fallback.

Use a specific date when needed:

```bash
make jibi-manual-update JIBI_DATE=2026-05-23
```

Logs are appended locally:

```text
~/Library/Logs/luddite/jibi_manual_YYYY-MM-DD.log
~/Library/Logs/luddite/jibi_manual_YYYY-MM-DD.err.log
```

Each run also writes a local manifest:

```text
outputs/reports/jibi_manual_update_YYYY-MM-DD.md
outputs/reports/jibi_manual_update_YYYY-MM-DD.json
```

The manifest records the append mode, target sheet, pinned preview CSV, digest
and report paths, content-enrichment status, append status, and log paths. It
does not include credential paths or article bodies.

The runner uses a lock directory at `/tmp/luddite-jibi-manual-update.lock` so
two runs cannot overlap. If fetch, import, normalize, score, cluster, or digest
rendering fails, the sheet append step is not attempted. Content enrichment is
diagnostic only: a failure is logged but does not block the sheet dry-run or
staging append.

To opt in to a real staging append, use:

```bash
JIBI_APPEND_MODE=staging_append \
LUDDITE_GOOGLE_TARGET_SHEET="jibi 후보" \
make jibi-manual-update
```

Safety gates:

- `JIBI_APPEND_MODE` defaults to `dry_run`.
- Accepted modes are `dry_run` and `staging_append`.
- `staging_append` may target only the exact `jibi 후보` tab.
- The runner refuses `주제 찾기` in any mode.
- The runner verifies the date-specific preview CSV exists before append.
- Unknown sources are not generically extracted during content enrichment unless
  `render-jibi-content-enrichment-review --allow-generic-extraction` is run
  manually outside the one-shot runner.

## Real Inbox Or RSS Dry-run

Use this when local article inbox files exist under `data/inbox/articles` or
when a one-shot RSS fetch should populate the inbox first.

```bash
make jibi-mvp-rss-dry-run
```

Rerun for a specific date:

```bash
make jibi-mvp-rss-dry-run JIBI_DATE=2026-05-23
```

This command runs fetch, import, normalize, score, cluster, render, then
`append-jibi-sheet --dry-run`. It does not append rows to Google Sheets and does
not call an LLM.

The Make target writes RSS items to
`data/inbox/articles/rss_$(JIBI_DATE).jsonl` and imports only that file with
`--input-file`. This keeps old inbox files from contaminating today's run.
Manual `import-articles --input-dir data/inbox/articles` still imports every
JSONL/CSV in that directory.

Manual equivalent:

```bash
PYTHONPATH=src .venv/bin/python -m luddite fetch-rss-articles \
  --date 2026-05-23 \
  --output data/inbox/articles/rss_2026-05-23.jsonl
PYTHONPATH=src .venv/bin/python -m luddite import-articles \
  --input-file data/inbox/articles/rss_2026-05-23.jsonl
make normalize-candidates
make score-candidates
make cluster-jibi-candidates
make render-daily-digest
PYTHONPATH=src .venv/bin/python -m luddite append-jibi-sheet --dry-run
```

The quality report includes a candidate funnel, source survival table, source
freshness, source quality flags, source skew warnings, near-miss review queue,
and conservative near-duplicate audit. Use the funnel to separate "there were no
good candidates" from "the gates were too strict." `top_count_too_low` means at
least 30 candidates were scored but fewer than 5 rendered as Top Candidates, so
check the near-miss queue and source survival warnings before changing
thresholds. `stale` RSS items are downranked or kept out of Top Candidates
conservatively; manual candidates with unknown freshness are not blocked only
because their published date is missing.

Read the calibration sections in this order:

1. `Operator Summary`: read the run health, primary bottleneck, and suggested
   operator action first.
2. `Candidate Funnel`: find the biggest drop before Top Candidates.
3. `Top Gate Reason Distribution`: compare all non-top candidates with the top
   20 near misses by score.
4. `What-if Gate Simulation`: compare report-only scenarios; runtime gates are
   unchanged.
5. `Source Allowlist Review Queue`: review suggested source actions; this
   command never edits `config/rss_collection_allowlist.yaml`.
6. `Generic Why Template Improvement Queue`: find concrete stories blocked by
   generic `why_interesting`.
7. `Near Miss Review Queue`: inspect high-score candidates before any append.

Do not change thresholds based on one run. A low Top count can still be
acceptable when the near-miss queue shows weak, stale, duplicate, or noisy
source material.

## Google Sheet Dry-run

Dry-run from the latest sheet preview:

```bash
export LUDDITE_GOOGLE_SHEETS_DRY_RUN=true
PYTHONPATH=src .venv/bin/python -m luddite append-jibi-sheet
```

Dry-run reports:

- planned appended row count;
- duplicate skips using `duplicate_key` and `source_url_canonical`;
- header state through `header_status`, `header_safe_to_update`, and
  `header_reason`;
- sheet/header creation plan for a missing tab.

Dry-run never creates a sheet, updates row 1, or appends candidate rows.

Safe dry-run header states:

- `ok`: current 30-column header is already present.
- `missing`: the tab is new or empty; safe only with zero errors.
- `legacy_25_upgrade_planned`: known legacy 25-column header; safe only with
  zero errors.
- `unsafe_mismatch`: do not real append. Inspect row 1 manually.

## Real Append

Run real append only after reviewing the dry-run report:

```bash
PYTHONPATH=src .venv/bin/python -m luddite append-jibi-sheet --no-dry-run
```

Real append targets only `jibi 후보`, may update row 1 when the header is
missing or the known legacy 25-column header, and appends only new candidate
rows. It must never append directly to `주제 찾기`.

Run real append only when the dry-run has zero errors and reports one of:
`ok`, `missing`, or `legacy_25_upgrade_planned`. If dry-run reports
`unsafe_mismatch`, real append is blocked and row 1 should be inspected
manually.

For the MVP team-evaluation phase, prefer `make jibi-manual-update` with
`JIBI_APPEND_MODE=staging_append` over calling `append-jibi-sheet --no-dry-run`
directly. The one-shot runner applies the target-sheet guard first and pins the
append to that run's date-specific preview CSV.

## Research Team Feedback Loop

Keep the sheet schema unchanged during the MVP evaluation. Ask reviewers to use
existing columns:

- `reviewer`: reviewer name or initials.
- `review_result`: one of `promote`, `keep`, `needs_more_evidence`,
  `editorial_review`, or `reject`.
- `promoted_to_topic_finding`: mark only after a candidate is manually promoted.
- `notes`: one-line reason, such as "good local analogy but needs Korean
  evidence" or "too generic for a segment seed."

Suggested rhythm:

1. Run the manual one-shot in dry-run mode for 2-3 days.
2. When reports look stable, run opt-in `staging_append` to `jibi 후보` once
   daily. Do not run hourly appends during MVP evaluation.
3. Let research teammates leave one-line `notes` for several days.
4. Analyze the feedback later before changing gates, source allowlists, or
   generic-why templates.

## Troubleshooting

Missing service-account JSON:

- Check `GOOGLE_APPLICATION_CREDENTIALS` or
  `LUDDITE_GOOGLE_SERVICE_ACCOUNT_JSON`.
- Confirm the path points to a local JSON file.
- Confirm the file is not committed to git.

Missing spreadsheet id:

- Set `LUDDITE_GOOGLE_SPREADSHEET_ID`.
- Dry-run without an id can still report planned rows from the preview CSV.
- Real append without an id exits with an error.

Schema mismatch:

- The expected header includes slideability fields:
  `slideability_score`, `slideability`, `first_slide_idea`,
  `likely_proof_object_types`, and `visual_risks`.
- `legacy_25_upgrade_planned` means a known old 25-column header can be upgraded
  safely if the dry-run has zero errors.
- `unsafe_mismatch` means the header is not recognized. Dry-run reports an
  error, and real append will not update row 1 or append rows.
- The first 25 columns preserve the old sheet order. Slideability fields are
  appended after `notes` so existing `reviewer`, `review_result`,
  `promoted_to_topic_finding`, and `notes` cells keep their meaning.

Duplicate skips:

- Existing rows with the same `duplicate_key` are skipped.
- Existing rows with the same `source_url_canonical` are skipped.
- Repeated rows inside the same preview CSV are also skipped.

No candidates:

- Check `outputs/reports/article_import_report.md` for empty or invalid input.
- Check `data/candidates/jibi_scored_candidates.jsonl`.
- Check `outputs/reports/jibi_quality_YYYY-MM-DD.md` for quality-gate filtering.
