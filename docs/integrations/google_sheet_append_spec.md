# Google Sheet Append Spec for jibi MVP

## Purpose

`jibi` should participate in the team's shared topic collection workflow by
appending candidate rows to a dedicated staging tab in the shared Google Sheet.

## Operating principle

The spreadsheet remains shared, but `jibi` should not write directly into the
human-operated `주제 찾기` tab during the MVP.

`jibi` may append rows to a staging tab. Humans can review those rows and promote
selected candidates into `주제 찾기`.

## Target sheet

Initial target:

```text
Jibi
```

Promotion target:

```text
주제 찾기
```

## Staging distinction

The dedicated `Jibi` tab should still preserve bot metadata:

- dedicated `jibi_id`
- `status`
- `digest_date`
- `collected_at`
- `last_seen_at`
- `duplicate_key`
- `source_url_canonical`
- `recommended_action` field
- `review_result`
- `promoted_to_topic_finding`

## Append behavior

Allowed:
- append new candidate rows to `Jibi`
- add bot metadata in appropriate columns
- write concise reason/summary
- skip duplicate candidates based on `duplicate_key` or `source_url_canonical`
- generate an append report after every run

Not allowed:
- overwrite human rows
- edit human labels
- mark final adoption status
- write directly to `주제 찾기` in the MVP
- insert subscription article full text into visible sheet
- delete existing rows
- update `last_seen_at` in 1.0; duplicate rows are skipped only

## Hard MVP rules

- Target only the `Jibi` staging sheet for bot append.
- Keep the existing `주제 찾기` sheet human-centered.
- Promote selected rows from `Jibi` to `주제 찾기` only after human review.
- Treat the sheet as append-only for the MVP.
- Never overwrite, reorder, relabel, or silently update human rows.
- Do not implement status updates in the append MVP; design that separately after the team has used bot rows.
- Do not place full subscription article text in the visible sheet.
- Prefer links, short summaries, `why_interesting`, `risk_flags`, and `recommended_action`.

## Milestone 1.0 command

Auth mode:

```text
service_account
```

Service account is the default and recommended path for automation. Before the
first real append, add the service account email as an editor on the shared
spreadsheet. The service account JSON file must stay local and must never be
committed to git.

Committed config is limited to `config/google_sheets.example.yaml`, which uses
placeholders only. Real values should be supplied by environment variables or
the gitignored `config/google_sheets.local.yaml`.

Required environment variables for production append:

```bash
LUDDITE_GOOGLE_SPREADSHEET_ID=...
LUDDITE_GOOGLE_TARGET_SHEET="Jibi"
GOOGLE_APPLICATION_CREDENTIALS=/absolute/path/to/service-account.json
```

`LUDDITE_GOOGLE_SERVICE_ACCOUNT_JSON` can be used instead of
`GOOGLE_APPLICATION_CREDENTIALS`.

Credential fallback inside the local ignored config:

```bash
service_account_json_path: /absolute/path/to/service-account.json
```

Config precedence:

```text
1. CLI args
2. environment variables
3. config/google_sheets.local.yaml
4. config/google_sheets.example.yaml defaults
```

OAuth is a fallback only if the shared spreadsheet cannot invite a service
account.

Dry-run first:

```bash
make append-jibi-sheet
luddite append-jibi-sheet --preview-csv outputs/daily_digest/YYYY-MM-DD_sheet_append_preview.csv --dry-run
```

Actual append requires a spreadsheet id from `--spreadsheet-id`,
`LUDDITE_GOOGLE_SPREADSHEET_ID`, or the ignored local config. Dry-run can still
produce a local report without a spreadsheet id.

Target sheet defaults to:

```text
Jibi
```

The command creates the target sheet if missing, creates the header row if
missing, appends only non-duplicate preview rows, and writes a report under
`outputs/reports/`.

First real run sequence:

```text
1. dry-run against the real spreadsheet
2. append a 1-2 row test CSV
3. inspect `Jibi`
4. append the full daily preview
5. rerun the same preview to confirm duplicate skip
```

Duplicate policy:

```text
duplicate_key match -> skip
source_url_canonical match -> skip
last_seen_at update -> future work, not 1.0
```

## Bundle review board mode

For the MVP research-team evaluation phase, `Jibi` can be reused as a
current-day bundle review board. This is intentionally sheet-native: reviewers
write directly in the same shared tab instead of using a new tool.

The renderer writes:

```text
outputs/daily_digest/YYYY-MM-DD_bundle_review_sheet.csv
```

Dry-run a board replacement:

```bash
luddite append-jibi-sheet \
  --preview-csv outputs/daily_digest/YYYY-MM-DD_bundle_review_sheet.csv \
  --schema bundle_review \
  --replace-existing \
  --dry-run
```

Actual replacement is explicit and should be used only for `Jibi`:

```bash
JIBI_SHEET_SCHEMA=bundle_review JIBI_APPEND_MODE=staging_replace make jibi-manual-update
```

This clears and rewrites the target tab with the day's bundle rows. The old
append-only candidate CSV remains available for audit and rollback.
Before a real bundle-board replacement, the appender checks `리뷰-성원`,
`리뷰-동찬`, and `리뷰-형찬`. If any reviewer comment exists, replacement is
blocked unless `JIBI_ALLOW_REVIEW_OVERWRITE=1` or `--allow-review-overwrite` is
explicitly used. Existing board rows are snapshotted locally first:

```text
outputs/reports/jibi_review_board_snapshot_YYYY-MM-DD.json
```

After reviewers add one-line notes, summarize the board without writing to
Google Sheets:

```bash
luddite summarize-jibi-review-board
```

Reviewer notes should start with a light tag such as `seed`, `evidence`,
`merge`, `needs`, `reject`, or `unclear`; the summary command also accepts
simple Korean aliases such as `방송`, `근거`, `묶기`, `보강`, `별로`, and `애매`.

## Suggested `Jibi` columns

Keep the first 25 columns in this exact order for backward compatibility with
existing reviewed rows. Add slideability fields only at the far right.

```text
digest_date
collected_at
last_seen_at
jibi_id
duplicate_key
source_url_canonical
rank
status
주제명
링크
출처
source_type
jibi_grade
total_score
recommended_action
risk_level
risk_flags
why_interesting
possible_expansions
evidence_needed
중복후보
reviewer
review_result
promoted_to_topic_finding
notes
slideability_score
slideability
first_slide_idea
likely_proof_object_types
visual_risks
```

## Subscription source display rule

Visible sheet should contain:

- title
- source
- URL
- short summary / why_interesting
- risk_flags
- recommended_action
- short excerpt only if needed

Do not put full subscription article text in the visible sheet.
