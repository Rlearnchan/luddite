# jibi Daily Digest Scoring v0.9.2

## Scope

This scoring layer is still local/manual and rule-based.

It does not call an LLM, fetch RSS continuously, append to Google Sheets, post to
Slack, or generate an anny storyline.

## Weighted Score

The current total score is a 0-100 style proxy. It is intentionally not a final
editorial judgment.

| Factor | Weight |
|---|---:|
| broadcast_potential_proxy | 25 |
| evidence_depth | 20 |
| numbers_strength | 15 |
| weird_hook | 12 |
| structural_expansion | 12 |
| punchline_potential | 8 |
| timeliness | 5 |
| risk_penalty | -0 to -30 |

The user priority behind this order is:

1. view-potential proxy
2. source/evidence richness
3. numbers/statistics
4. "엥?" hook
5. structural expansion
6. joke/meme/punchline potential
7. timeliness
8. risk penalty

## Grade Bands

Initial bands:

- A: score >= 75
- B: score >= 55
- C: score >= 35
- D: score < 35

High risk can cap a weak score into D. A high-potential risky item should not be
discarded automatically; it should usually become `editorial_review`.

## Recommended Action

`send_to_anny`

- high potential
- enough evidence
- low or medium risk
- concrete possible_expansions

`gather_more_evidence`

- hook is strong
- evidence, numbers, or official sources are still thin
- structure is visible but support is weak

`editorial_review`

- potential is high
- risk is high
- political, corporate, medical, crime/drug, investment, or sensitive framing
  needs a person before it moves forward
- risky but strong items belong here

`keep_for_later`

- mildly interesting
- sub-candidate
- timing is not right yet
- could improve when paired with another seed

`reject`

- policy-blocked item
- source is weak
- verification burden is too high
- too one-off
- direct party/president evaluation
- looks like stock recommendation or pure corporate promotion

Direct president/party/approval-rating framing should be `reject` with
`blocked_reason: direct_president_party_evaluation`, not `editorial_review`.

Risky and strong means `editorial_review`.

Risky and weak means `reject`.

Policy-blocked means `reject` or later `blocked_policy`.

## Digest Display

Top Candidates may include:

- `send_to_anny`
- `gather_more_evidence`
- `editorial_review`
- `keep_for_later`

Rejected or blocked items must not occupy Top Candidates slots. They can be
shown in `Excluded / Rejected`.

## Sheet Output

The preview CSV is for the `jibi 후보` staging tab, not direct append to
`주제 찾기`.

Flow:

```text
jibi 후보 -> human review -> promote selected rows to 주제 찾기
```

## Current Caveats

- Rule-based Korean/English keyword matching is intentionally rough.
- `possible_expansions` is rule-based and should contain at least three strings.
- `evidence_needed` is rule-based and should be improved with real source
  quality signals later.
- The digest ranking is a research triage surface, not a final broadcast
  selection.
