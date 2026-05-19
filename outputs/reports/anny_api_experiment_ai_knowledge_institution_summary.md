# Anny API Experiment Summary — AI Knowledge Institution

- generated_at: 2026-05-19
- scope: v1-v9 controlled API experiments
- case_id: anny_api_experiment_ai_knowledge_institution_v1
- topic: AI 즉답 시대의 지식기관 역할
- model: gpt-5-mini
- production_agent_implemented: false
- batch_api_experiment: false
- ready_for_api_experiment: true
- ready_for_production_agent: false
- ready_for_broadcast: false

## v1-v9 Results

| Run | Schema | Hygiene | Sections | Slides | Source URLs | Needs Source | Needs Fact Check | Key Beat Recall | Failure Modes | Source Hallucination | Do-not-claim | Counterpoint |
|---|---|---|---:|---:|---:|---:|---:|---:|---|---:|---:|---|
| v1 | true | false | 4 | 18 | 25 | 3 | 8 | 0.80 | key_beat_drift | 0 | 0 | true |
| v2 | true | false | 4 | 24 | 38 | 1 | 16 | 0.60 | key_beat_drift | 0 | 0 | true |
| v3 | true | false | 4 | 23 | 30 | 8 | 10 | 0.80 | unsupported_claim, key_beat_drift | 0 | 0 | true |
| v4 | true | false | 4 | 24 | 23 | 2 | 9 | 1.00 | unsupported_claim, needs_fact_check_removed_too_aggressively, key_beat_drift | 0 | 0 | true |
| v5 | true | false | 4 | 23 | 31 | 16 | 8 | 1.00 | unsupported_claim, needs_fact_check_removed_too_aggressively, key_beat_drift | 0 | 0 | true |
| v6 | true | false | 4 | 22 | 24 | 15 | 14 | 1.00 | unsupported_claim, needs_fact_check_removed_too_aggressively | 0 | 0 | true |
| v7 | true | false | 4 | 24 | 26 | 2 | 9 | 1.00 | unsupported_claim, needs_fact_check_removed_too_aggressively | 0 | 0 | true |
| v8 | true | false | 4 | 21 | 21 | 2 | 16 | 1.00 | unsupported_claim, needs_fact_check_removed_too_aggressively | 0 | 0 | true |
| v9 | true | false | 5 | 25 | 23 | 12 | 13 | 1.00 | needs_fact_check_removed_too_aggressively | 0 | 0 | true |

## Trend Summary

- schema_valid: all runs passed schema validation.
- hygiene_passed: no run passed hygiene fully; the remaining failure has narrowed.
- source_hallucination: stayed at 0 across all v1-v9 runs.
- do_not_claim violations: stayed at 0 across all v1-v9 runs.
- counterpoint: included across all runs.
- unsupported_claim: present in v3-v8, reduced to 0 in v9 after source-specific title and claim-bearing closing-question rules.
- key_beat_recall: unstable in v1-v3, reached 1.00 from v4 onward except validation drift details, and remains 1.00 in v9.
- needs_fact_check: rose after prompt patches, but v9 still misses conservative markers on several education/AI/institution-role slides.
- needs_source: increased in v9, showing the model is more willing to leave evidence gaps visible.
- section count: v1-v8 stayed at 4 sections; v9 produced 5 sections.

## Improvement Milestones

- rhetorical source rule: allowed pure title/rhetorical/bridge slides without over-flagging unsupported claims.
- key beat planning: added `section_plan` and `key_beat_coverage`.
- slide-level key beat commitment: added `covers_key_beats`.
- stable key beat IDs: removed invented role labels from `covers_key_beats`.
- key beat anchors: added `key_beat_anchors_used` and anchor phrase validation.
- source-specific title policy: required source URLs or `needs_source=true` for BBC/Royal Observatory/warns/says-like title phrasing.
- claim-bearing closing question rule: required source or `needs_source=true` when a closing question carries an education/cognition/institution-role premise.

## Remaining Failure Analysis

Remaining failure: `needs_fact_check_removed_too_aggressively`.

In v9, the validator flagged slides 5, 6, 7, 9, 11, and 20. The pattern is not source hallucination or guardrail violation; it is fact-check conservatism. The affected slides are mostly education, AI, and institution-role claims where the model attached or referenced evidence but did not keep `needs_fact_check=true`.

Observed slide types:

- `data`: OECD/GenAI education use framing.
- `explainer`: AI accessibility/personalization and domestic science-museum example framing.
- `counterpoint`: UNESCO/accessibility framing.
- `section_title`: school/museum/planetarium/institution-role framing.

Observed pattern:

- `fact_check_kind` was often absent, making the validator rely on text markers.
- Source refs were often absent or not enough to treat the claim as verified.
- The failure should remain a blocker for production output, but it is narrow enough that a different risk profile can now be tested.

Prompt implications:

- Continue requiring `needs_fact_check=true` for AI, education, cognition, learning, and institution-role claims even when sources are attached.
- Encourage explicit `fact_check_kind` on all education/institution-role slides.
- Do not treat source attachment as fact-check completion.

## Section Count Policy

The target remains 3-4 sections. v9 produced 5 sections, which is acceptable as an API-experiment warning but should not become the production default.

Policy:

- API experiment: 5 sections is a warning if other hygiene checks are stable.
- Production anny: 3-4 sections are the default hard target.
- 5 sections require explicit `section_plan` justification, such as a separate counterpoint or risk section that cannot be folded into the four-part arc.

## Readiness Gate

- ready_for_api_experiment: true
- ready_for_production_agent: false
- ready_for_broadcast: false

Rationale:

- The AI knowledge-institution API case is stable enough on schema, key beat recall, source hallucination, do-not-claim compliance, counterpoint inclusion, and unsupported-claim handling.
- It is not production-ready because fact-check conservatism is still incomplete and output variability has only been tested on one topic.

## Next Milestone Recommendation

Recommended next milestone: Milestone 1.17 — Productive Finance First API Experiment.

Why:

- AI knowledge-institution has been sufficiently stabilized for controlled API experiments.
- The next question is whether the same contract holds under a higher-risk policy/finance topic.
- Productive finance should stress-test `policy_effect_claim`, `investment_risk_claim`, `corporate_promo_risk`, official-evidence gaps, counterpoint/risk slides, and no-investment-advice rules.

Do not proceed yet to limited production Anny MVP. Production readiness remains false.
