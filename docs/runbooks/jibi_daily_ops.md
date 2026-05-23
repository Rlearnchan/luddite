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
