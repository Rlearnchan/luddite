# Manual LLM Dry Run v0.8

## Purpose

Milestone 0.8 checks whether GPT Pro or another manual LLM output can pass the
existing eval harness before any production agent or API integration is built.

This is not an agent implementation milestone. The goal is to save manually
created JSON/JSONL outputs in a local generated directory and run the existing
evaluators against them.

## Output location

Manual dry run outputs should be stored under:

```text
outputs/model_dry_runs/
  jibi_seed_eval/
  anny_reconstruction/
  piti_deck_plan/
```

The `outputs/` directory is generated/local and ignored by git. Do not commit
manual model outputs unless a later milestone explicitly asks for a curated
fixture.

Example files:

```text
outputs/model_dry_runs/jibi_seed_eval/gpt_pro_sample.jsonl
outputs/model_dry_runs/anny_reconstruction/pawnshop_f88_gpt_pro.json
outputs/model_dry_runs/piti_deck_plan/pawnshop_f88_gpt_pro.json
```

## jibi dry run

Select 6 samples from:

```text
eval/golden_cases/jibi_seed_eval_cases.jsonl
```

Recommended mix:

- positive: 2
- produced_but_rejected: 2
- pending_or_unknown: 1
- rejected_or_not_pursued: 1

Output path:

```text
outputs/model_dry_runs/jibi_seed_eval/gpt_pro_sample.jsonl
```

Evaluation command:

```bash
luddite eval-jibi-seeds --model-output outputs/model_dry_runs/jibi_seed_eval/gpt_pro_sample.jsonl
```

The output should follow the fields expected by the jibi seed eval runner,
including `final_grade`, `broadcast_potential`, `risk_level`,
`recommended_action`, and `risk_flags`.

## anny dry run

Case:

```text
pawnshop_f88
```

Reference fixture:

```text
eval/golden_cases/anny_storylines/golden_pawnshop_f88_storyline.json
```

Output path:

```text
outputs/model_dry_runs/anny_reconstruction/pawnshop_f88_gpt_pro.json
```

Evaluation command:

```bash
luddite eval-anny-reconstruction --model-output outputs/model_dry_runs/anny_reconstruction
```

The manual output should be a valid anny storyline JSON and should preserve the
core beats around F88, the pawnshop reveal, Vietnam credit access, motorcycle
collateral, and collection/regulation risk.

## piti dry run

Input:

```text
eval/golden_cases/anny_storylines/golden_pawnshop_f88_storyline.json
```

Output path:

```text
outputs/model_dry_runs/piti_deck_plan/pawnshop_f88_gpt_pro.json
```

Evaluation command:

```bash
luddite eval-piti-deck-plan --model-output outputs/model_dry_runs/piti_deck_plan
```

The manual output should be a valid deck plan JSON with stable slide numbers,
title and section slides, separated `source_urls` / `image_urls`, and speaker
notes that preserve `[내용]` and `[이미지]` style source handling.

## Not in scope

Do not implement these in Milestone 0.8:

- real LLM API calls
- jibi/anny/piti production agents
- RSS collector
- Google Sheets API direct fetch
- Google Sheet append implementation
- Slack bot implementation
- full PPT generator
- image auto collection
- syuka-ops integration

## Completion check

Milestone 0.8 is ready when:

- the manual output paths are documented
- GPT Pro/manual outputs can be saved locally under `outputs/model_dry_runs/`
- `make test` still passes
- existing eval runners can accept the saved manual outputs through their
  `--model-output` arguments
