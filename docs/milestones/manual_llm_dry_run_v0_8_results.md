# Manual LLM Dry Run v0.8 Results

Status date: 2026-05-17

GPT Pro generated manual dry-run outputs for:

- jibi seed eval sample
- anny `pawnshop_f88` reconstruction
- piti `pawnshop_f88` deck plan

The raw manual outputs and generated eval reports are stored under `outputs/`,
which remains generated/local and ignored by git.

## jibi

Command:

```bash
PYTHONPATH=src .venv/bin/python -m luddite eval-jibi-seeds \
  --cases outputs/model_dry_runs/jibi_seed_eval/gpt_pro_sample_cases.jsonl \
  --model-output outputs/model_dry_runs/jibi_seed_eval/gpt_pro_sample.jsonl
```

Result:

- Total cases: 6
- Passed: 6
- Failed: 0
- Missing output: none
- Average risk recall: 1.00
- Important risk misses: 0

Label band checks passed:

- positive: 2/2 with A/B
- produced_but_rejected: 2/2 with B/C
- pending_or_unknown: 1/1 with B
- rejected_or_not_pursued: 1/1 with D

## anny

Default command:

```bash
PYTHONPATH=src .venv/bin/python -m luddite eval-anny-reconstruction \
  --model-output outputs/model_dry_runs/anny_reconstruction
```

Default report result:

- Total cases: 2
- Passed: 2
- Failed: 0
- Average key beat recall: 1.00
- Average critical beat recall: 1.00
- Candidate source reporting: enabled

Important note:

Only `pawnshop_f88` was supplied by GPT Pro. The eval runner now marks
`pawnshop_f88` as `model_output` and `coca_cola_ambani` as `golden_fallback`, so
dry-run reports show clearly which cases came from GPT Pro and which were
deterministic fixture fallbacks.

Pawnshop-only check:

- Passed: 1/1
- schema_valid: true
- section_count_ok: true
- key_beat_recall: 1.00
- critical_beat_recall: 1.00
- source_integrity_ok: true
- source_image_overlap_count: 0
- required_fact_checks_present: true
- Warning: representative reconstruction has 22 slides, below standard-mode
  45-65 slide guidance.

## piti

Default command:

```bash
PYTHONPATH=src .venv/bin/python -m luddite eval-piti-deck-plan \
  --model-output outputs/model_dry_runs/piti_deck_plan
```

Default report result:

- Total decks: 2
- Passed: 2
- Failed: 0
- Candidate source reporting: enabled
- `golden_pawnshop_f88_deck_plan`: `model_output`
- `golden_coca_cola_ambani_deck_plan`: `golden_fallback`

Important note:

Only `golden_pawnshop_f88_deck_plan` was supplied by GPT Pro. The eval runner
now marks `golden_coca_cola_ambani_deck_plan` as `golden_fallback` in both JSONL
and Markdown reports.

Pawnshop-only check:

- Passed: 1/1
- schema_valid: true
- slide_no_integrity: true
- required_slide_types: true
- source_image_overlap_count: 0
- editability_ok: true
- source_note_integrity: true

Resolved issue:

Slide 8 uses a Wikipedia URL with a `#` fragment:

```text
https://en.wikipedia.org/wiki/Pawn_Stars#/media/File:Pawn_Stars_cast.png
```

The current URL extractor reads the notes URL as:

```text
https://en.wikipedia.org/wiki/Pawn_Stars
```

The image slot keeps the full fragment URL, so the eval runner treats them as
different URLs. This is a narrow URL normalization/eval hygiene issue, not a
fundamental deck-plan failure.

The eval runner now canonicalizes `image_slots.source_url` before comparing it
with notes URLs, so the GPT Pro deck plan passes.

## Eval hygiene patches

Completed:

- Canonicalize URLs before comparing notes URLs with `image_slots`.
- Report when an eval case used golden fallback because no model output was
  supplied.

## Decision

Proceed to Milestone 0.9: jibi Daily Digest MVP.

Reason:

- jibi dry run passed 6/6 with no missing outputs.
- anny `pawnshop_f88` reconstruction passed all required checks.
- piti `pawnshop_f88` deck plan now passes after URL canonicalization.
