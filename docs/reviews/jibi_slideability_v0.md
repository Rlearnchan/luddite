# Jibi Slideability V0 Review Note

Status date: 2026-05-20

## Summary

Milestone 1.33 adds deterministic `slideability` scoring to Jibi candidate and
cluster outputs. This is a review signal only.

- No LLM/API call is added.
- Existing Jibi `recommended_action` logic is not hard-gated by slideability.
- Existing candidate collection, normalization, scoring, and clustering remain
  deterministic.
- Production Jibi/Anny/Piti readiness remains false.
- Broadcast readiness remains false.

## Field Shape

```json
{
  "slideability": {
    "score": 0.0,
    "visualizability": "low|medium|high",
    "chartability": "none|weak|strong",
    "diagramability": "none|weak|strong",
    "screenshotability": "none|weak|strong",
    "source_card_fit": "none|weak|strong",
    "first_slide_idea": "...",
    "likely_proof_object_types": ["diagram", "chart", "source_card"],
    "risks": ["single_source", "needs_official_data"],
    "reason": "..."
  }
}
```

Story seed handoff records also expose:

- `slideability_score`
- `first_slide_idea`
- `likely_proof_object_types`
- `visual_risks`

## Rule-Based Signals

The v0 scorer looks for:

- chartability: numbers, ratios, rankings, trends, budgets, rates, GDP,
  investment amounts, increase/decrease language
- diagramability: actor/context, mechanism/change, result/tension, policy,
  industry, finance, supply chain, process, conflict language
- source-card fit: clear source title, known institution/news source, source
  count, source URL presence
- screenshotability: article/report/page/table/figure/document cues
- risks: `too_abstract`, `single_source`, `needs_official_data`,
  `policy_claim_risk`, `market_claim_risk`, `no_clear_visual`

Generic fallback wording and generic evidence-needed strings are deliberately
discounted so a candidate does not look highly slideable only because the
pipeline asked for "numbers/statistics" later.

## Sample Output

Current generated report surfaces:

```text
outputs/reports/jibi_quality_2026-05-20.md
outputs/reports/jibi_clusters_2026-05-20.md
outputs/daily_digest/2026-05-20.md
outputs/daily_digest/2026-05-20_clusters.md
outputs/daily_digest/2026-05-20_story_seed_handoff.md
```

Observed v0 distribution after the current sample run:

```text
visualizability:
  high: 41
  medium: 49
  low: 0

chartability:
  strong: 19
  weak: 70
  none: 1

diagramability:
  strong: 8
  weak: 18
  none: 64
```

Top digest examples:

```text
생산적 금융과 정책자금 전환:
  slideability: high / diagram+chart+source_card
  first slide idea: structure diagram first, supporting chart for key numbers
  risks: single_source, needs_official_data, policy_claim_risk

AI 즉답 시대의 지식기관 역할:
  slideability: high / diagram+source_card
  first slide idea: actor -> mechanism -> result diagram
  risks: single_source
```

## Interpretation

The scorer is intentionally broad in v0. It is useful for showing whether a
candidate has an obvious chart, diagram, source-card, or screenshot path before
Anny/Piti work begins. It is not yet a candidate rejection mechanism.

Recommended next use:

1. Pass slideability into the Anny input bundle as context.
2. Compare Jibi slideability predictions against downstream Piti visual QA.
3. Consider a PPT contact-sheet QA surface after slide spec rendering.
