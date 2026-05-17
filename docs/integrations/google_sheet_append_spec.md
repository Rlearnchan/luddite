# Google Sheet Append Spec for jibi MVP

## Purpose

`jibi` should participate in the team's shared topic collection workflow by appending candidate rows to the shared Google Sheet.

## Operating principle

The sheet remains a shared human+bot workspace.

`jibi` may append rows, but bot rows must be easy to distinguish and easy to ignore/delete.

## Target sheet

Initial target:

```text
주제 찾기
```

## Visual distinction

Use at least two of the following:

- dedicated `작성자` or `source` value: `jibi`
- background color/highlight for bot rows
- muted or distinct font color
- note/comment prefix: `[jibi]`
- separate `수집일` or `created_at` timestamp
- `recommended_action` field

## Append behavior

Allowed:
- append new candidate rows
- add bot metadata in appropriate columns
- write concise reason/summary

Not allowed:
- overwrite human rows
- edit human labels
- mark final adoption status
- insert subscription article full text into visible sheet

## Hard MVP rules

- Target only the `주제 찾기` sheet.
- Mark every bot row with `jibi` in a `source` or `작성자` style field.
- Use background color, font styling, highlight, or another visible cue so bot rows are distinguishable from human rows.
- Treat the sheet as append-only for the MVP.
- Never overwrite, reorder, relabel, or silently update human rows.
- Do not implement status updates in the append MVP; design that separately after the team has used bot rows.
- Do not place full subscription article text in the visible sheet.
- Prefer links, short summaries, `why_interesting`, `risk_flags`, and `recommended_action`.

## Suggested row payload

```json
{
  "title": "...",
  "source_url": "...",
  "source_name": "...",
  "published_at": "...",
  "jibi_collected_at": "...",
  "seed_type": "...",
  "final_grade": "A|B|C|D",
  "broadcast_potential": "high|medium|low",
  "risk_level": "high|medium|low",
  "recommended_action": "send_to_anny|gather_more_evidence|keep_for_later|editorial_review|reject",
  "why_interesting": "...",
  "possible_expansions": ["...", "..."],
  "evidence_needed": ["...", "..."],
  "risk_flags": ["...", "..."],
  "source": "jibi"
}
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
