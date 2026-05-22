# Jibi MVP Start - 2026-05-22

## Decision

Implement the Jibi MVP first. The existing `jibi -> anny -> piti` spine remains
only as a contract and smoke-test surface during this milestone.

## Non-goals

- Production Anny agent
- Production Piti agent
- Scheduler or 24/7 collector
- Slack bot
- Automatic image insertion
- Automatic chart generation
- Google Slides integration
- Broadcast readiness

## MVP Definition Of Done

- `make test` passes.
- `make jibi-digest` produces the example Daily Digest and sheet preview.
- A real-operation dry-run path can ingest from `data/inbox/articles` and/or a
  one-shot RSS fetch.
- `append-jibi-sheet --dry-run` authenticates with the service account, reads
  the `jibi 후보` tab, reports header/schema status and duplicate skips, and
  does not write to the sheet.
- `append-jibi-sheet --no-dry-run` appends only new candidate rows to
  `jibi 후보`.
- Duplicate protection uses `duplicate_key` and `source_url_canonical`.
- The sheet schema includes slideability fields:
  `slideability_score`, `slideability`, `first_slide_idea`,
  `likely_proof_object_types`, and `visual_risks`.
- No workflow in this milestone appends directly to `주제 찾기`.

## Google Sheet Target

- Spreadsheet name: `슈카월드_리서치`
- Spreadsheet id: `1piIsrWAHqSWBk0PwouTK1DWccX3W0Sfqf3YUptXT8QU`
- Staging tab: `jibi 후보`
- Service account writer:
  `jibi-001@adept-rock-496700-r0.iam.gserviceaccount.com`

Keep real credential files out of git. Store the service account JSON locally
and point to it with an environment variable:

```bash
export LUDDITE_GOOGLE_SPREADSHEET_ID="1piIsrWAHqSWBk0PwouTK1DWccX3W0Sfqf3YUptXT8QU"
export LUDDITE_GOOGLE_TARGET_SHEET="jibi 후보"
export GOOGLE_APPLICATION_CREDENTIALS="/absolute/path/to/service-account.json"
```

`LUDDITE_GOOGLE_SERVICE_ACCOUNT_JSON` can be used instead of
`GOOGLE_APPLICATION_CREDENTIALS`.

## Manual Commands

Example digest:

```bash
make jibi-digest
```

Google Sheet dry-run from the latest preview:

```bash
export LUDDITE_GOOGLE_SHEETS_DRY_RUN=true
PYTHONPATH=src .venv/bin/python -m luddite append-jibi-sheet
```

Explicit real append:

```bash
PYTHONPATH=src .venv/bin/python -m luddite append-jibi-sheet --no-dry-run
```

The real append command is intentionally explicit. Do not add a Make target that
performs a real append by default.
