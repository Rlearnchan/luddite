# Codex Handoff v0.8.1 — after design alignment

## Current baseline

Current implementation checkpoint is v0.7:

- parser smoke stable
- corpus insight docs reflected
- golden reconstruction fixtures available
- `jibi`, `anny`, `piti` eval runners available
- no production LLM/API agent implementation yet

Do not skip directly to production orchestration.

## New user decisions

### 1. Google Sheet append is allowed

`jibi` may write candidate rows directly to the shared Google Sheet.

Requirements:

- Bot-authored rows must be visually distinguishable from human rows.
- Use a dedicated marker column if available, or add one if schema allows.
- Also apply visible styling:
  - background highlight
  - muted font color or bot-specific color
  - author/source field such as `jibi`
- Do not overwrite human-authored rows.
- Do not edit existing rows except later status updates explicitly owned by `jibi`.

Initial target sheet:

- `주제 찾기`

Suggested bot columns:

```text
작성자/source: jibi
수집일/created_at
seed_type
score/final_grade
broadcast_potential
risk_level
recommended_action
why_interesting
possible_expansions
evidence_needed
risk_flags
source_url
```

If the current sheet schema should not be changed, append only to existing columns and put structured metadata in the reason/comment column.

### 2. Collection should run every day

Do not limit collection to Monday/Tuesday.

User context:
- humans do more collection/story work early week and PPT production mid/late week
- bot has no such limit
- therefore daily collection is valuable

MVP schedule:

```text
daily collection: every day
weekday digest: Monday-Friday morning
manual on-demand digest: anytime
```

Weekend collection may still store candidates in DB even if it does not send Slack digest.

### 3. Luddite Slack bot should be separate

Plan a separate Luddite bot instead of directly merging into `syuka-ops` Slack bot for MVP.

Rationale:

- syuka-ops handles past video metadata/transcript search
- Luddite handles future topic discovery and candidate/storyline workflow
- keeping bots separate reduces coupling at MVP stage

Long-term:
- Luddite may query syuka-ops DB/API for past video similarity and performance proxy
- Slack UX can later be consolidated if useful

## Next implementation path

### Milestone 0.8: Manual LLM Dry Run

Keep this short.

Goal:
- verify prompts and eval runners against actual/manual GPT outputs
- do not build a production API agent yet

Tasks:

1. jibi small dry run
   - choose 6 cases from `jibi_seed_eval_cases.jsonl`
   - run GPT manually with `prompts/jibi/seed_scorer.md`
   - save JSONL to `outputs/model_dry_runs/jibi_seed_eval/gpt_pro_sample.jsonl`
   - run `luddite eval-jibi-seeds --model-output ...`

2. anny small dry run
   - use `pawnshop_f88`
   - save GPT output to `outputs/model_dry_runs/anny_reconstruction/pawnshop_f88_gpt_pro.json`
   - run `luddite eval-anny-reconstruction --model-output ...`

3. piti small dry run
   - use `golden_pawnshop_f88_storyline.json`
   - save GPT output to `outputs/model_dry_runs/piti_deck_plan/pawnshop_f88_gpt_pro.json`
   - run `luddite eval-piti-deck-plan --model-output ...`

### Milestone 0.9: jibi Daily Digest MVP

This is the next real implementation priority.

Goal:
- produce 10 useful candidate topics per day
- write them to Google Sheet
- generate digest Markdown
- eventually send via Luddite Slack bot

MVP output:

```text
outputs/daily_digest/YYYY-MM-DD.md
data/candidates/YYYY-MM-DD.jsonl
optional Google Sheet append to 주제 찾기
```

Candidate count:

```text
source collection: many
stored candidates: 30-50/day
human-facing digest: 10/day
```

Scoring priority:

```text
1. broadcast/view potential proxy
2. evidence depth
3. numbers/statistics strength
4. weird hook
5. structural expansion
6. punchline/meme potential
7. timeliness
8. risk penalty
```

Recommended actions:

```text
send_to_anny
gather_more_evidence
keep_for_later
editorial_review
reject
```

`editorial_review` is required for risky-but-interesting topics.

## Do not do yet

- full production LLM agent orchestration
- RSS 24/7 collector with complex scheduling
- full PPT generator
- image auto collection
- Google Sheets API direct auth if simpler export/append path is not ready
- merging Luddite into syuka-ops Slack bot

## Done criteria for next Codex work

For v0.8 docs/checkpoint:
- docs are copied into repo
- README or status doc references the changed assumptions

For v0.9 jibi MVP planning:
- jibi daily digest spec updated
- Google Sheet append spec updated
- Luddite separate Slack bot plan documented
- no production API calls required yet
