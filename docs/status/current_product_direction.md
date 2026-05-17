# Current Product Direction after v0.9.4 Digest Polish

Status date: 2026-05-18

## Current checkpoint

Luddite is at the v0.7 eval harness checkpoint plus v0.8/v0.8.1 design
alignment, v0.9.3 jibi Daily Digest quality calibration, and v0.9.4 final
digest polish before Google Sheet append.

Completed:

- parser smoke stable
- corpus insight docs
- golden reconstruction fixtures
- `validate-golden`
- `eval-jibi-seeds`
- `eval-anny-reconstruction`
- `eval-piti-deck-plan`
- Manual LLM Dry Run
- jibi / anny / piti dry runs evaluable through the eval harness
- jibi source/RSS strategy documented
- syuka-ops bridge designed as a read-only/search proxy
- Google Sheet append direction moved to the `jibi 후보` staging sheet
- anny direction expanded to Article -> Candidate -> Cluster -> Story Seed -> Storyline
- BDC mode kept open as design, outside the MVP implementation scope
- v0.9.4 digest summary wording clarified so `send_to_anny=0` is not confused
  with zero useful Top Candidates
- visible `why_interesting` reduced generic scoring clauses; generic signals can
  live in `score_reason`

Not started:

- real LLM API calls
- jibi/anny/piti production agent implementation
- RSS collector
- Google Sheets API direct fetch
- Google Sheet append implementation
- Slack bot implementation
- full PPT generator
- image auto collection
- syuka-ops DB bridge

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
- `jibi` may append rows to a dedicated Google Sheet staging tab.
- Bot rows must stay separate from human-operated rows.
- Slack should start as a separate Luddite bot, not as a direct extension of
  `syuka-ops`.
- `syuka-ops` is the past-video metadata/transcript/view database; Luddite is
  the future-candidate discovery database.
- BDC is not an MVP target, but candidate/storyline schemas should leave room
  for `mode: normal | bdc`.

## Google Sheet append principles

- Target sheet: `jibi 후보`
- Keep existing `주제 찾기` as the human-operated sheet.
- Never overwrite human rows.
- `jibi` append is append-only for MVP.
- Humans mark `review_result` as blank, keep, promote, needs_more_evidence,
  editorial_review, or reject.
- Later, only `review_result=promote` rows may be promoted/copied to
  `주제 찾기`.
- Do not put subscription article full text in the visible sheet.
- Store link, short summary, `why_interesting`, `risk_flags`, and
  `recommended_action` instead.

Required staging metadata:

```text
digest_date
collected_at
last_seen_at
duplicate_key
source_url_canonical
```

## Source registry status

- `rss_candidate` entries are still unverified endpoint candidates.
- Before implementing the RSS collector, each candidate source needs endpoint
  discovery, fetch test, and parse test.
- A source should only move from `rss_candidate` to `rss_verified` after fetch
  and parse tests pass.
- `subscription_manual` sources must not be auto-fetched; use links and short
  summaries only.

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

Milestone 1.0: Google Sheet `jibi 후보` append implementation

Milestone 1.1: anny DB-based Storyline MVP

Milestone 1.2: syuka-ops similarity/performance bridge

Milestone 1.3: piti renderer MVP
