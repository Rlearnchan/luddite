# Current Product Direction after v0.8.1

Status date: 2026-05-17

## Current checkpoint

Luddite is at the v0.7 eval harness checkpoint plus v0.8/v0.8.1 design
alignment.

Completed:

- parser smoke stable
- corpus insight docs
- golden reconstruction fixtures
- `validate-golden`
- `eval-jibi-seeds`
- `eval-anny-reconstruction`
- `eval-piti-deck-plan`

Not started:

- real LLM API calls
- jibi/anny/piti production agent implementation
- RSS collector
- Google Sheets API direct fetch
- Google Sheet append implementation
- Slack bot implementation
- full PPT generator
- image auto collection

## Product priority

Short-term implementation priority:

1. jibi Daily Digest MVP
2. Google Sheet append
3. Luddite Slack bot
4. anny DB-based storyline
5. syuka-ops similarity/performance bridge
6. piti renderer/PPTX draft

## Key design changes

- The first real user-facing goal is not automatic PPT creation. It is research
  topic selection support.
- The first demo is a daily morning digest of 10 candidate topics.
- `jibi` collects every day.
- Humans may collect less on Wednesday/Thursday/Friday because PPT production is
  heavier then, but the bot has no such limitation.
- `jibi` may append rows directly to the Google Sheet.
- Bot rows must be visually distinguishable from human rows.
- Slack should start as a separate Luddite bot, not as a direct extension of
  `syuka-ops`.

## Google Sheet append principles

- Target sheet: `주제 찾기`
- Mark `jibi` rows with `source`, `작성자`, or equivalent field.
- Visually distinguish bot rows with background color, muted font, highlight, or
  a similar style.
- Never overwrite human rows.
- `jibi` append is append-only for MVP.
- Status updates require a later explicit design.
- Do not put subscription article full text in the visible sheet.
- Store link, short summary, `why_interesting`, `risk_flags`, and
  `recommended_action` instead.

## Slack bot principles

- Luddite starts as a separate Slack bot.
- `syuka-ops` remains the system for past video, transcript, thumbnail, and
  metadata search.
- Luddite is for future candidate discovery, topic selection, and storyline
  requests.
- Long-term, Luddite may query syuka-ops DB/API for past video similarity and
  view-performance proxy.

MVP commands:

```text
/luddite today
/luddite search <keyword>
/luddite candidate <candidate_id>
/luddite help
```

Later buttons:

```text
Keep
Needs more evidence
Editorial review
Reject
Request storyline
```

## Next milestones

Milestone 0.8: Manual LLM Dry Run

- jibi 6 cases
- anny `pawnshop_f88` 1 case
- piti `pawnshop_f88` 1 case
- no API calls
- save GPT Pro manual outputs as JSON/JSONL and run existing eval runners

Milestone 0.9: jibi Daily Digest MVP

- daily collection
- weekday morning digest
- 10 human-facing candidates
- Markdown report
- Google Sheet append preparation
- later Slack bot integration

Milestone 1.0: Google Sheet / Slack output integration

Milestone 1.1: anny DB-based Storyline MVP

Milestone 1.2: syuka-ops similarity/performance bridge

Milestone 1.3: piti renderer MVP
