# jibi Daily Digest Scoring v0.9.2 + v0.9.3 Corrections

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
- real source link exists
- at least two independent sources or one official source exists
- low or medium risk
- concrete possible_expansions
- evidence_needed is not just generic source/number requests

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
- domestic party/president direct evaluation
- looks like stock recommendation or pure corporate promotion

Domestic president/party/approval-rating framing should be `reject` with
`blocked_reason: direct_president_party_evaluation`, not `editorial_review`.
The hard reject criterion is not "a party appears in the title." It is direct
evaluation of a domestic president, party, politician, or real-time partisan
statement.

Overseas political fracture can be `editorial_review` or
`gather_more_evidence` when it expands into economic/social structure such as
populism, regional gaps, bond markets, immigration, or working-class movement.

Risky and strong means `editorial_review`.

Risky and weak means `reject`.

Policy-blocked means `reject` or later `blocked_policy`.

Failure modes may use the v0.9.3 negative taxonomy:

- `sub_item_only`
- `too_obvious_pattern`
- `single_company_frame`
- `single_stock_investment_frame`
- `weak_structural_expansion`
- `thin_evidence`
- `sensitive_high_low_gain`
- `live_news_volatility`
- `political_direct_eval`
- `recent_cooldown`
- `copyright_heavy`

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

Required duplicate/append-only columns:

- `digest_date`
- `collected_at`
- `last_seen_at`
- `duplicate_key`
- `source_url_canonical`

## Current Caveats

- Rule-based Korean/English keyword matching is intentionally rough.
- `possible_expansions` is rule-based and should contain at least three strings.
- `evidence_needed` is rule-based and should be improved with real source
  quality signals later.
- The digest ranking is a research triage surface, not a final broadcast
  selection.
