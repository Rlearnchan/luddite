# Jibi Daily Ops Runbook

This runbook covers the Jibi MVP daily workflow. It produces candidate topics,
renders a Daily Digest, and stages rows in the Google Sheet `Jibi` tab for
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
export LUDDITE_GOOGLE_TARGET_SHEET="Jibi"
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
7. Open `Jibi` and fill the reviewer-specific columns manually.

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
two runs cannot overlap. The runner only removes the lock when the current
process acquired it, so a failed second run cannot delete another run's lock. If
fetch, import, normalize, score, cluster, or digest rendering fails, the sheet
append step is not attempted. Content enrichment is diagnostic only: a failure
is logged but does not block the sheet dry-run or staging append.

To opt in to a real staging append, use:

```bash
JIBI_APPEND_MODE=staging_append \
LUDDITE_GOOGLE_TARGET_SHEET="Jibi" \
make jibi-manual-update
```

Safety gates:

- `JIBI_APPEND_MODE` defaults to `dry_run`.
- Accepted modes are `dry_run`, `staging_append`, and `staging_replace`.
- `staging_append` may target only the exact `Jibi` tab.
- The runner refuses `주제 찾기` in any mode.
- The runner verifies the date-specific preview CSV exists before append.
- The runner removes only locks it owns.
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

Source-role handling is intentionally conservative during the manual MVP:

- Top Candidate selection now applies source-role soft caps after scoring and
  quality gates: `research_note` 3, `policy_release` 2, `public_wire` 3,
  `academic_explainer` 2, `market_wire` 1, and `section_news` 3. These caps do
  not change candidate scores or thresholds. If the caps would leave the Top
  list short, the report backfills and marks `cap_backfill_used`.
- The Conversation is enabled as a controlled academic-explainer experiment,
  not as an always-pass source.
- Guardian broad international/world feeds stay on hold. Prefer section feeds
  such as Business, Technology, and Environment when running a Guardian mix
  test.
- BOK Issue Notes are low-frequency research-note seed/evidence hybrids, so
  they use a longer freshness window and should be reviewed through the
  research-template queue rather than treated as stale RSS.
- Policy Briefing and ministry releases are evidence-default. They become seed
  candidates only when they show direct life impact, regulatory conflict,
  industrial mechanism, odd hook, visual proof object, or a material number with
  a structural signal. Dates, procedural numbers, meeting notices, coordination
  meetings, and agenda-only releases stay evidence unless there is a concrete
  life/industry/regulatory mechanism.
- Yonhap uses section feeds for the manual MVP. Economy, Industry, and
  International are enabled; Latest is held because its RSS lookback is short,
  while Market+ and Health remain guarded hold sources. Yonhap Industry near
  misses should be checked for public AI governance/enforcement, workplace AI,
  platform labor, and industrial labor conflict templates before holding the
  source.

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
6. `Source Mix Experiment Review`: check source-role distribution, cap warnings,
   and the human-review focus list before judging the day's source mix.
7. `Source Role Cap Status`: check whether official sources are overrepresented.
8. `Story Bundle Review`: review the suggested story bundle primary and
   supporting/evidence items before treating each row as a separate story.
9. `Storyline Fit Audit`: check whether Top items look like standalone seeds,
   evidence, or demote/reject cases.
10. `Generic Why Template Improvement Queue`: find concrete stories blocked by
   generic `why_interesting`.
11. `Near Miss Review Queue`: inspect high-score candidates before any append.

Do not change thresholds based on one run. A low Top count can still be
acceptable when the near-miss queue shows weak, stale, duplicate, or noisy
source material.

## Research-team Bundle Review

The daily digest and quality report show report-only story bundles. The renderer
also writes a sheet-native bundle review CSV:

```text
outputs/daily_digest/YYYY-MM-DD_bundle_review_sheet.csv
```

For team evaluation, the preferred visible sheet is the existing shared
`Jibi` tab reused as a current-day review board. This avoids making a new
tool for reviewers. The normal candidate append CSV is still generated for
audit/backward compatibility, but reviewers should usually see the bundle review
board instead of separate candidate rows.

Dry-run the board replacement:

```bash
make jibi-review-board-dry-run
```

When the dry-run report is clean and the team is ready to review in the shared
sheet, replace the current contents of `Jibi` with the day's bundle board:

```bash
make jibi-review-board-replace
```

`staging_replace` is explicit because it clears and rewrites the target tab. It
is allowed only for `Jibi`; the runner still refuses to write to `주제 찾기`.
If existing reviewer comments are present in `리뷰-성원`, `리뷰-동찬`, or
`리뷰-형찬`, a real replace stops by default and writes a local snapshot:

```text
outputs/reports/jibi_review_board_snapshot_YYYY-MM-DD_HHMMSS_xxxxxx.json
outputs/reports/jibi_review_board_history.jsonl
```

Only overwrite a reviewed board intentionally:

```bash
JIBI_ALLOW_REVIEW_OVERWRITE=1 make jibi-review-board-replace
```

Reviewers should read each row as one story bundle. Supporting/evidence items
are not shown as separate rows; they appear as `서브 링크` and in `설명`.
The `설명` cell includes source/title cues so the reviewer can see what raw
material the humanized title came from.

Ask reviewers to start each review with one lightweight tag:
`seed`, `evidence`, `merge`, `needs`, `reject`, or `unclear`.

Good one-line feedback examples:

- `seed — 청년 쉬었음 + 남성 경제활동참가율 묶으면 가능`
- `needs — 양파는 가격 데이터/산지 기사 필요`
- `evidence — 고유가 지원금 현황만으로는 보도자료 느낌`
- `merge — AI 드론/공공 AI 보고서와 묶어 AI 행정 주제로 보기`
- `reject — 단일기업 홍보/투자 이야기로 보임`

Current review columns in the shared sheet:

- `날짜`: 수집일자.
- `제목`: reviewer-facing bundle title.
- `점수`: Jibi ranking hint, e.g. `72점 · B · 자료 보강 필요`; not a command.
- `메인 링크`: primary source link.
- `서브 링크`: supporting/evidence source links, separated by ` | `.
- `설명`: why Jibi selected this bundle, how it could become a story, what is missing, and source/title cues.
- `리뷰-성원`, `리뷰-동찬`, `리뷰-형찬`: one-line reviewer notes.
- `ID`: stable review item id for later feedback analysis.

To widen the board during an experiment, keep the review format one-line and
raise only the board limit:

```bash
JIBI_REVIEW_BOARD_LIMIT=20 make jibi-review-board-dry-run
JIBI_REVIEW_BOARD_LIMIT=20 make jibi-review-board-replace
```

To let high-score near-misses provide supporting/evidence links, tune:

```bash
JIBI_BUNDLE_NEAR_MISS_LIMIT=10 make jibi-review-board-dry-run
```

Repeated stories are not automatically suppressed. If `설명` says a topic was
seen, reviewed, rejected, or seed-tagged before, treat that as a reappearance
hint and decide whether it is a genuinely new angle.

After reviewers write notes, summarize the current board without changing the
sheet:

```bash
make jibi-review-feedback
```

This writes:

```text
outputs/reports/jibi_review_feedback_YYYY-MM-DD.md
outputs/reports/jibi_review_feedback_YYYY-MM-DD.json
```

The summary reports reviewer completion counts, tag counts, raw one-line notes,
and rows where reviewers strongly disagree, such as `seed` vs `reject`.

For multi-day calibration, summarize the local review-board history archive:

```bash
make jibi-review-history-feedback
```

This writes:

```text
outputs/reports/jibi_feedback_calibration_YYYY-MM-DD.md
outputs/reports/jibi_feedback_calibration_YYYY-MM-DD.json
```

The calibration report is read-only. It combines `jibi_review_board_history.jsonl`
with candidate metadata where available, then reports reviewer completion by
date, tag counts, source/source-role/seed-type feedback, repeated
`story_fingerprint` rows, strong disagreement, and report-only recommendations.
It does not change scores, thresholds, source allowlists, or the visible `Jibi`
board.

The board description copy is generated by the Jibi review-board copy layer.
Each row should read like a short editor note: why the item appeared, how it
could grow into a Shuka-style story, and what evidence is missing. If a row
falls back to generic wording, treat that as a template-improvement signal
rather than as a reviewer instruction.

Guardian section feeds remain held by default. For a controlled experiment,
copy `config/rss_collection_allowlist.yaml` to a local temporary allowlist,
enable only `guardian_business`, `guardian_technology`, and
`guardian_environment` with moderate fetch limits, then pass that temporary
allowlist to `fetch-rss-articles` manually. Do not enable the broad Guardian
international/world feed for the normal daily run until the review-board history
loop has several days of data.

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

Real append targets only `Jibi`, may update row 1 when the header is
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

## Feedback Collection Readiness

Before asking the research team to review staged rows:

1. Run dry-run mode for 2-3 days.
2. Inspect the Daily Digest, quality report, content enrichment report, sheet
   append report, and manual summary for each run.
3. Use `JIBI_APPEND_MODE=staging_append` only once daily, not hourly, and only
   for `Jibi`.
4. Keep the sheet schema unchanged.
5. Ask reviewers to fill only their own review column.
6. Ask for one-line notes.
7. Do not change gates, source allowlists, or generic-why templates until
   several days of feedback exist.

## Research Team Feedback Loop

Keep the sheet schema unchanged during the MVP evaluation. Ask reviewers to use
only `리뷰-성원`, `리뷰-동찬`, and `리뷰-형찬`.

Suggested rhythm:

1. Run the manual one-shot in dry-run mode for 2-3 days.
2. When reports look stable, run opt-in `staging_append` to `Jibi` once
   daily. Do not run hourly appends during MVP evaluation.
3. Let research teammates leave one-line notes for several days.
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
