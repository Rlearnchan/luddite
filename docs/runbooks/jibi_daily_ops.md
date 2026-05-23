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

This command runs fetch, import, normalize, score, cluster, render, then
`append-jibi-sheet --dry-run`. It does not append rows to Google Sheets and does
not call an LLM.

`import-articles --input-dir data/inbox/articles` imports every JSONL/CSV in
that directory, not only today's RSS file. For clean morning runs, archive old
inbox files or use a date-specific input directory until a stricter import
filter exists.

Manual equivalent:

```bash
make fetch-rss-articles
PYTHONPATH=src .venv/bin/python -m luddite import-articles --input-dir data/inbox/articles
make normalize-candidates
make score-candidates
make cluster-jibi-candidates
make render-daily-digest
PYTHONPATH=src .venv/bin/python -m luddite append-jibi-sheet --dry-run
```

## Google Sheet Dry-run

Dry-run from the latest sheet preview:

```bash
export LUDDITE_GOOGLE_SHEETS_DRY_RUN=true
PYTHONPATH=src .venv/bin/python -m luddite append-jibi-sheet
```

Dry-run reports:

- planned appended row count;
- duplicate skips using `duplicate_key` and `source_url_canonical`;
- missing or old header/schema state through `header_status`;
- sheet/header creation plan for a missing tab.

Dry-run never creates a sheet, updates row 1, or appends candidate rows.

## Real Append

Run real append only after reviewing the dry-run report:

```bash
PYTHONPATH=src .venv/bin/python -m luddite append-jibi-sheet --no-dry-run
```

Real append targets only `jibi 후보`, may update row 1 when the header is
missing or old, and appends only new candidate rows. It must never append
directly to `주제 찾기`.

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
- Dry-run reports the mismatch but does not update the sheet.
- Real append may update row 1 before appending rows.
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
