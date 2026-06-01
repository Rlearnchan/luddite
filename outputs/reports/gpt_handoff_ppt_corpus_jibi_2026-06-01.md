# GPT Pro Handoff — PPT Corpus + Jibi Dry Run — 2026-06-01

## Context

This handoff is for reviewing the current Luddite work before it is treated as ready for broader use.

Current branch:

- `codex-ppt-corpus-review`
- code commit already pushed: `084e80c Add Syukaworld PPT corpus pipeline`
- handoff date: `2026-06-01`

## What Changed

Implemented a canonical `ppt_corpus` layer while keeping the existing `ppt_learning` pipeline as a compatibility surface.

Important code paths:

- `src/luddite/ppt/corpus.py`
- `src/luddite/ppt/learning.py`
- `tests/test_ppt_corpus.py`
- `tests/test_ppt_learning.py`
- `src/luddite/cli.py`

New canonical CLI commands:

- `build-ppt-corpus-drive-manifest`
- `build-ppt-corpus-inventory`
- `extract-ppt-corpus-slides`
- `build-ppt-corpus-quality-report`
- `build-ppt-corpus-insight-reports`

Canonical output paths:

- `data/ppt_corpus/drive_ppt_inventory.jsonl`
- `data/ppt_corpus/extracted/deck_manifest.jsonl`
- `data/ppt_corpus/extracted/slides.jsonl`
- `data/ppt_corpus/extracted/links.jsonl`
- `data/ppt_corpus/extracted/media_manifest.jsonl`
- `outputs/reports/ppt_corpus/*`
- `docs/insights/*`

Raw PPT archives and generated extraction JSONL are ignored by default.

## Verification Already Run

```bash
PYTHONPATH=src ./.venv/bin/python -m pytest tests/test_ppt_corpus.py tests/test_ppt_learning.py
```

Result:

- `18 passed`

```bash
./.venv/bin/ruff check src/luddite/ppt/corpus.py src/luddite/cli.py tests/test_ppt_corpus.py tests/test_ppt_learning.py
./.venv/bin/ruff check src/luddite/ppt/learning.py tests/test_ppt_learning.py
```

Result:

- passed

CLI smoke:

- `PYTHONPATH=src ./.venv/bin/python -m luddite.cli --help`
- `build-ppt-corpus-inventory` generated a smoke inventory under `/tmp/luddite-ppt-corpus-smoke`
- `build_ppt_corpus_insight_reports(...)` generated smoke reports under `/tmp/luddite-ppt-corpus-smoke`

Important limitation:

- Full canonical `extract-ppt-corpus-slides` over all 773 PPT files has not yet been run.
- The smoke insight report used existing `outputs/ppt_learning` extraction artifacts.

## Jibi Dry Run — 2026-06-01

Command run:

```bash
make jibi-review-board-refresh-with-syuka JIBI_DATE=2026-06-01
```

Safety result:

- `append_mode=dry_run`
- `sheet_schema=bundle_review`
- `sheet_replace_status=not_requested`
- `sheet_mode=none`
- Google Sheet was not written or replaced.

Collection result:

- RSS sources: `13`
- articles fetched: `536`
- normalized candidates: `536`
- scored candidates: `536`
- clusters: `252`
- rendered board rows: `10`
- syuka probe: `usable`

Key generated artifacts:

- `outputs/daily_digest/2026-06-01.md`
- `outputs/daily_digest/2026-06-01_bundle_review_sheet.csv`
- `outputs/daily_digest/2026-06-01_bundle_review_sheet_metadata.json`
- `outputs/reports/jibi_manual_update_2026-06-01.md`
- `outputs/reports/jibi_sheet_append_2026-06-01_bundle_review_sheet.md`
- `outputs/reports/jibi_syuka_refresh_2026-06-01.md`
- `outputs/reports/jibi_board_score_2026-06-01.md`
- `outputs/reports/jibi_selection_calibration_2026-06-01.md`
- `outputs/reports/jibi_anny_handoff_2026-06-01.md`
- `outputs/reports/jibi_content_enrichment_2026-06-01.md`
- `outputs/reports/rss_ingest_2026-06-01.md`

## Jibi Review Points

Please inspect the 2026-06-01 board before any Sheet upload.

Notable signals:

- `main_seed_count=0`
- `sub_block_count=9`
- `evidence_count=1`
- `suppress_candidate_count=3`
- `support_missing_count=2`
- `syuka_false_positive_risk_count=9`
- topic concentration warning: AI/energy-heavy board

Specific concerns:

- The run may now be too conservative: no `main_seed` candidates survived calibration.
- `syuka_false_positive_risk_count=9` may be too high or too broad.
- `Anthropic’s alliance with pope on AI harms...` received `sports_primary_downrank`; this looks suspicious and should be checked for false-positive lesson matching.
- `platform_hidden_cost_bonus` promoted both Naver drone/physical AI and free-delivery/platform-cost items by `+5`; check whether those boosts are justified.
- `[제2026-11호] 국내외 자산 토큰화...` was dropped from `55` to `0` with `past_video_new_angle`; check whether this is fair or overly suppressive.
- The selected board has several AI/heat/energy adjacent items; decide whether topic diversity should be active for this run.

## PPT Corpus Review Points

Please inspect whether the chosen architecture is acceptable:

- Is it okay that `ppt_corpus` is canonical while `ppt_learning` remains as compatibility?
- Should the large `ppt_learning.py` compatibility layer be split in a follow-up PR?
- Are the canonical schemas enough for Jibi/Anny/Piti reports?
- Should full canonical PPT extraction be run now, or should we first review the existing `ppt_learning` outputs?
- Should `docs/insights/*` be committed only after full extraction, or generated report-only for now?

## Non-Goals Still Respected

- No Google Sheet replace.
- No Google Sheet append.
- No Google Drive original edits.
- No syuka-ops DB writes.
- No production Jibi scoring or Anny/Piti contract change from PPT corpus insights yet.
