# Jibi To Piti Slideability Notes

Status date: 2026-05-20

Milestone 1.33 adds a rule-based `slideability` signal to Jibi scored
candidates and story seed clusters. Milestone 1.34 passes that signal into Anny
input bundles as `visual_planning_hint`. It is a review/planning signal only; it
does not hard reject candidates or change `send_to_anny` by itself.

## Why This Matters

The recent Piti renderer work showed that a topic can be narratively promising
yet visually weak. If Jibi selects candidates with no proof object, Piti has to
invent weak placeholders later. A stronger future pipeline should identify the
likely proof object at candidate time.

## Candidate Signal

Current Jibi `slideability` shape:

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
    "risks": ["too_abstract", "single_source"],
    "reason": "..."
  }
}
```

Current v0 likely proof object values:

- `diagram`
- `chart`
- `source_card`

`screenshotability` is kept as a separate signal because screenshots may inform
Anny/Piti planning, but `screenshot` is not a current Piti `proof_object.type`.

## Anny Bundle Context

Anny input bundles may include this top-level object:

```json
{
  "visual_planning_hint": {
    "slideability_score": 1.0,
    "visualizability": "high",
    "first_slide_idea": "...",
    "likely_proof_object_types": ["diagram", "chart", "source_card"],
    "visual_risks": ["single_source", "needs_official_data"],
    "reason": "...",
    "planning_note": "Jibi slideability is a planning hint only; it is not evidence and must not override source/fact-check guardrails."
  }
}
```

This field stays separate from `required_evidence`, `fact_check_tasks`, and
`official_source_tasks`. Anny may use it to plan proof-object direction, but not
to support claims.

## Rule-Based V0 Heuristics

- A candidate with clear numbers, rankings, time series, ratios, or market size
  usually has stronger chart/table potential.
- A candidate built around a vivid quote, official statement, or contested
  wording has quote/source-card potential.
- A candidate involving a product, place, person, institution, document,
  webpage, map, or imageable scene has screenshot/image potential.
- A candidate that explains a mechanism, tradeoff, process, or conflict can be
  diagrammable even without images.
- A candidate with only abstract claims and no concrete proof object should
  carry lower slideability unless the text itself is a strong calculation,
  question, or punchline.
- Policy, finance, market, budget, rate, investment, and official-statistics
  language adds `needs_official_data`, `policy_claim_risk`, or
  `market_claim_risk` as visual review risks.

## Non-Goal

Slideability is not a hard gate in v0. Existing Jibi scoring, ranking, and
`recommended_action` logic should remain stable while reports and Anny bundles
show whether a story seed is likely to become a diagram, chart, source card, or
screenshot.
