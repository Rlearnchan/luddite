# Anny Input Bundle Slideability Context Review

Status date: 2026-05-20

## Summary

Milestone 1.34 passes Jibi slideability into Anny input bundles as
`visual_planning_hint`.

This is planning context only:

- It is not evidence.
- It does not hard-gate Jibi candidates.
- It does not change existing `recommended_action` decisions.
- It does not weaken source/fact-check guardrails.
- It does not make production or broadcast readiness true.

## Bundle Field

`visual_planning_hint` is added at story-seed/bundle level, separate from
`candidate_articles`, `required_evidence`, `fact_check_tasks`, and
`official_source_tasks`.

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

## Representative Cases

### 생산적 금융과 정책자금 전환

```text
Visual planning hint: high / diagram+chart+source_card
First slide idea: 이억원 "담보 및 단기수익 중심 금융 경쟁 앞서가기 어려워": 구조 diagram으로 시작하고 핵심 숫자는 보조 chart로 확인
Visual risks: single_source, needs_official_data, policy_claim_risk
```

Guardrail status:

- `needs_fact_check=true`
- `required_evidence` still includes source/number/official-material checks.
- `fact_check_tasks` still includes original text, numeric source, official
  material, and risk/counterexample checks.
- `do_not_claim` still blocks policy-effect certainty and investment advice.

### AI 즉답 시대의 지식기관 역할

```text
Visual planning hint: high / diagram+source_card
First slide idea: Instant AI answers can trivialise human intelligence, warns Royal Observatory: actor -> mechanism -> result 구조 diagram
Visual risks: single_source
```

Guardrail status:

- `needs_fact_check=true`
- Source identity remains in candidate article metadata.
- The hint suggests an opening visual direction, not a claim.

## Prompt Guidance Added

Anny prompts now state:

- Slideability is a planning hint, not evidence.
- Do not claim anything based only on slideability.
- Use `likely_proof_object_types` for early proof-object direction.
- Use `first_slide_idea` as a tentative opening visual idea.
- Use `visual_risks` to keep caution/fact-check flags conservative.
- If slideability conflicts with source/fact-check guardrails, guardrails win.
- If slideability suggests chart/table but data is missing, keep
  `needs_source` or `needs_fact_check`.

## Next Recommended Check

Compare Jibi `visual_planning_hint` against downstream Piti visual QA:

- Did `likely_proof_object_types` predict the proof objects Anny/Piti actually
  used?
- Did high diagramability correlate with fewer generic diagram-node warnings?
- Did `visual_risks` correctly preserve source/fact-check caution?
