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
jibi 후보
```

Promotion target:

```text
주제 찾기
```

## Staging distinction

The dedicated `jibi 후보` tab should still preserve bot metadata:

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
- append new candidate rows to `jibi 후보`
- add bot metadata in appropriate columns
- write concise reason/summary

Not allowed:
- overwrite human rows
- edit human labels
- mark final adoption status
- write directly to `주제 찾기` in the MVP
- insert subscription article full text into visible sheet

## Hard MVP rules

- Target only the `jibi 후보` staging sheet for bot append.
- Keep the existing `주제 찾기` sheet human-centered.
- Promote selected rows from `jibi 후보` to `주제 찾기` only after human review.
- Treat the sheet as append-only for the MVP.
- Never overwrite, reorder, relabel, or silently update human rows.
- Do not implement status updates in the append MVP; design that separately after the team has used bot rows.
- Do not place full subscription article text in the visible sheet.
- Prefer links, short summaries, `why_interesting`, `risk_flags`, and `recommended_action`.

## Suggested `jibi 후보` columns

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
