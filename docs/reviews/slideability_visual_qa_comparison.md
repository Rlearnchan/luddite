# Slideability vs Piti Visual QA Comparison

- Generated for: 2026-05-20
- Purpose: calibrate Jibi slideability / Anny visual planning hints against downstream Piti slide specs and visual QA.
- Review-only: this report does not change Jibi scoring, recommended_action, handoff gates, Anny prompts, or Piti rendering.
- LLM/API calls: none
- Production readiness remains false.
- Broadcast readiness remains false.

## Summary

- compared cases: 2
- slideability_prediction_quality mixed: 2

## Case Alignment

| case | predicted proof types | actual proof counts | proof_type_match | chartability | diagramability | source_card | risk_alignment | prediction_quality | notes |
|---|---|---|---|---|---|---|---|---|---|
| AI 즉답 시대의 지식기관 역할 | diagram, source_card | chart:1, diagram:18, none:4, source_card:3 | strong | underprediction | low_quality_hit | hit | good | mixed | Predicted proof type appears downstream. Diagram was used, but visual QA still flags generic diagram nodes. Visual risks align with retained source/fact-check caution. |
| 생산적 금융과 정책자금 전환 | diagram, chart, source_card | article_quote:1, chart:4, diagram:12, none:6, source_card:1 | strong | hit | low_quality_hit | hit | good | mixed | Predicted proof type appears downstream. Diagram was used, but visual QA still flags generic diagram nodes. Visual risks align with retained source/fact-check caution. |

## Case Details

### AI 즉답 시대의 지식기관 역할

Jibi / Anny input side:

- deck_id: piti_slide_spec_ai_knowledge_institution
- input bundle matched: true
- slide spec: data/candidates/piti_slide_specs/ai_knowledge_institution_slide_spec.json
- slideability_score: 1.0
- visualizability: high
- first_slide_idea: Instant AI answers can trivialise human intelligence, warns Royal Observatory: actor -> mechanism -> result 구조 diagram
- likely_proof_object_types: diagram, source_card
- visual_risks: single_source
- reason: cluster best: chart=none; diagram=strong; source_card=strong; risks=single_source

Piti slide spec side:

- slide_count: 26
- section_count: 4
- proof_object_type_counts: chart:1, diagram:18, none:4, source_card:3
- diagram_count: 18
- chart/table_count: 1
- source_card_count: 3
- article_quote_count: 0
- text_only_count: 4
- needs_fact_check_count: 16
- required_before_broadcast_count: 0
- source_refs_count: 38
- do_not_claim_count: 0

Piti visual QA side:

- schema_valid: true
- render_passed: not_evaluated
- section_mapping_complete: true
- QA flag counts: diagram_nodes_too_generic:18, manual_insert_required_without_editor_instruction:6, overflow_notes_too_large:2, source_card_display_title_too_generic:3
- severity counts: INFO:2, REVIEW:27
- diagram_nodes_too_generic: 18
- manual_insert_required_without_editor_instruction: 6
- source_card_display_title_too_generic: 3
- overflow_notes_too_large: 2
- chart_table_body_too_long_count: 0
- article_quote_missing_quote_text_count: 0

Alignment:

- proof_type_match: strong
- chartability_alignment: underprediction
- diagramability_alignment: low_quality_hit
- source_card_alignment: hit
- risk_alignment: good
- slideability_prediction_quality: mixed
- risk_alignment_notes:
  - single_source: ok (expects source refs, source cards, or retained fact-check caution)
- notes: Predicted proof type appears downstream. Diagram was used, but visual QA still flags generic diagram nodes. Visual risks align with retained source/fact-check caution.

### 생산적 금융과 정책자금 전환

Jibi / Anny input side:

- deck_id: piti_slide_spec_productive_finance_policy
- input bundle matched: true
- slide spec: data/candidates/piti_slide_specs/productive_finance_policy_slide_spec.json
- slideability_score: 1.0
- visualizability: high
- first_slide_idea: 이억원 "담보 및 단기수익 중심 금융 경쟁 앞서가기 어려워": 구조 diagram으로 시작하고 핵심 숫자는 보조 chart로 확인
- likely_proof_object_types: diagram, chart, source_card
- visual_risks: single_source, needs_official_data, policy_claim_risk
- reason: cluster best: chart=strong; diagram=strong; source_card=strong; risks=single_source, needs_official_data, policy_claim_risk

Piti slide spec side:

- slide_count: 24
- section_count: 4
- proof_object_type_counts: article_quote:1, chart:4, diagram:12, none:6, source_card:1
- diagram_count: 12
- chart/table_count: 4
- source_card_count: 1
- article_quote_count: 1
- text_only_count: 6
- needs_fact_check_count: 17
- required_before_broadcast_count: 17
- source_refs_count: 48
- do_not_claim_count: 0

Piti visual QA side:

- schema_valid: true
- render_passed: not_evaluated
- section_mapping_complete: true
- QA flag counts: diagram_nodes_too_generic:12, manual_insert_required_without_editor_instruction:3, overflow_notes_too_large:1
- severity counts: INFO:1, REVIEW:15
- diagram_nodes_too_generic: 12
- manual_insert_required_without_editor_instruction: 3
- source_card_display_title_too_generic: 0
- overflow_notes_too_large: 1
- chart_table_body_too_long_count: 0
- article_quote_missing_quote_text_count: 1

Alignment:

- proof_type_match: strong
- chartability_alignment: hit
- diagramability_alignment: low_quality_hit
- source_card_alignment: hit
- risk_alignment: good
- slideability_prediction_quality: mixed
- risk_alignment_notes:
  - single_source: ok (expects source refs, source cards, or retained fact-check caution)
  - needs_official_data: ok (expects needs_fact_check or required_before_broadcast to remain)
  - policy_claim_risk: ok (expects do_not_claim or fact-check caution to remain)
- notes: Predicted proof type appears downstream. Diagram was used, but visual QA still flags generic diagram nodes. Visual risks align with retained source/fact-check caution.

## Interpretation

- This comparison is for calibration only.
- Slideability is still not a candidate rejection signal.
- A good result means the hint can keep flowing into Anny input bundles.
- A weak result means the rule-based slideability heuristic needs calibration.
- Scoring weight changes should wait until downstream visual QA linkage is better understood.

## Next Recommended Check

- Compare these results against future Anny direct slide specs, not only adapter-built specs.
- Track whether high diagramability reduces generic diagram-node warnings.
- Consider a PPT contact sheet QA surface after rendered draft decks.
