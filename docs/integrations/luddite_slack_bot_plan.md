# Luddite Slack Bot MVP Plan

## Decision

Build Luddite as a separate Slack bot for MVP.

Do not merge directly into `syuka-ops` Slack bot yet.

## Rationale

`syuka-ops`:
- past video metadata
- transcripts
- thumbnails
- video search

`Luddite`:
- future topic discovery
- candidate scoring
- storyline requests
- digest delivery

Keeping them separate makes MVP easier and safer.

## Boundary with syuka-ops

Start with a dedicated Luddite bot.

`syuka-ops` remains the system of record for past videos, transcripts, metadata, thumbnails, search, and historical performance context.

`Luddite` owns future-facing workflows:

- candidate discovery
- topic selection support
- daily digest delivery
- candidate detail lookup
- storyline requests

Longer term, Luddite can call a `syuka-ops` DB/API bridge to fetch similar past videos, transcript matches, title history, and view-count proxies. That bridge should be integration work, not a reason to merge the first Slack bot into `syuka-ops`.

## MVP Slack features

Phase 1:

```text
/luddite today
/luddite search <keyword>
/luddite candidate <candidate_id>
/luddite help
```

Phase 2:

```text
/luddite keep <candidate_id>
/luddite reject <candidate_id>
/luddite storyline <candidate_id>
```

## Daily digest

Weekday morning digest can be sent to a configured channel or DM.

Digest should show 10 candidates:

```text
1. title
   grade / broadcast_potential / risk_level
   why interesting
   recommended action
   source link
```

## Human feedback buttons

If Slack interactive components are added:

- Keep
- Needs more evidence
- Editorial review
- Reject
- Request storyline

Feedback should later sync to DB and optionally Google Sheet.
