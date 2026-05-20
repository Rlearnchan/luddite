# Slideability vs Piti Visual QA Comparison

- Generated for: 2026-05-21
- Purpose: calibrate Jibi slideability / Anny visual planning hints against downstream Piti slide specs and visual QA.
- Review-only: this report does not change Jibi scoring, recommended_action, handoff gates, Anny prompts, or Piti rendering.
- LLM/API calls: none
- Production readiness remains false.
- Broadcast readiness remains false.
- Direct comparison enabled: true
- direct_run_id: live_m132_20260520_all
- direct_run_root: outputs/model_dry_runs/anny_slide_spec_experiments_live/live_m132_20260520_all

## Summary

- compared cases: 2
- adapter_slideability_prediction_quality mixed: 2
- direct_slideability_prediction_quality good: 2

## Case Alignment

| case | predicted proof types | adapter proof counts | adapter diagramability | direct proof counts | direct diagramability | direct delta | adapter risk | direct risk | adapter quality | direct quality | notes |
|---|---|---|---|---|---|---|---|---|---|---|---|
| AI 즉답 시대의 지식기관 역할 | diagram, source_card | chart:1, diagram:18, none:4, source_card:3 | low_quality_hit | chart:1, diagram:16, none:6, source_card:3 | hit | diagram_nodes_too_generic -18; review -20 | good | good | mixed | good | Predicted proof type appears downstream. Diagram was used, but visual QA still flags generic diagram nodes. Visual risks align with retained source/fact-check caution. Direct: Predicted proof type appears downstream. Diagram was used without generic-node warnings. Visual risks align with retained source/fact-check caution. |
| 생산적 금융과 정책자금 전환 | diagram, chart, source_card | article_quote:1, chart:4, diagram:12, none:6, source_card:1 | low_quality_hit | article_quote:1, chart:4, diagram:12, none:5, source_card:2 | hit | diagram_nodes_too_generic -12; review -9 | good | good | mixed | good | Predicted proof type appears downstream. Diagram was used, but visual QA still flags generic diagram nodes. Visual risks align with retained source/fact-check caution. Direct: Predicted proof type appears downstream. Diagram was used without generic-node warnings. Visual risks align with retained source/fact-check caution. |

## Case Details

### AI 즉답 시대의 지식기관 역할

Jibi / Anny input side:

- case_id: ai_knowledge_institution
- deck_id: piti_slide_spec_ai_knowledge_institution
- input bundle matched: true
- slideability_score: 1.0
- visualizability: high
- first_slide_idea: Instant AI answers can trivialise human intelligence, warns Royal Observatory: actor -> mechanism -> result 구조 diagram
- likely_proof_object_types: diagram, source_card
- visual_risks: single_source
- reason: cluster best: chart=none; diagram=strong; source_card=strong; risks=single_source

Adapter slide spec side:

- slide spec: data/candidates/piti_slide_specs/ai_knowledge_institution_slide_spec.json
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

Adapter visual QA / contract side:

- schema_valid: true
- render_passed: not_evaluated
- section_mapping_complete: true
- safety_regression_detected: not_evaluated
- experiment_outcome: -
- QA flag counts: diagram_nodes_too_generic:18, manual_insert_required_without_editor_instruction:6, overflow_notes_too_large:2, source_card_display_title_too_generic:3
- severity counts: INFO:2, REVIEW:27
- diagram_nodes_too_generic: 18
- manual_insert_required_without_editor_instruction: 6
- source_card_display_title_too_generic: 3
- overflow_notes_too_large: 2
- chart_table_body_too_long_count: 0
- article_quote_missing_quote_text_count: 0

Adapter alignment:

- adapter_proof_type_match: strong
- adapter_chartability_alignment: underprediction
- adapter_diagramability_alignment: low_quality_hit
- adapter_source_card_alignment: hit
- adapter_risk_alignment: good
- adapter_slideability_prediction_quality: mixed
- risk_alignment_notes:
  - single_source: ok (expects source refs, source cards, or retained fact-check caution)

Direct slide spec side:

- slide spec: outputs/model_dry_runs/anny_slide_spec_experiments_live/live_m132_20260520_all/ai_knowledge_institution/parsed_piti_slide_spec.json
- slide_count: 26
- section_count: 4
- proof_object_type_counts: chart:1, diagram:16, none:6, source_card:3
- diagram_count: 16
- chart/table_count: 1
- source_card_count: 3
- article_quote_count: 0
- text_only_count: 6
- needs_fact_check_count: 16
- required_before_broadcast_count: 0
- source_refs_count: 38
- do_not_claim_count: 21

Direct visual QA / contract side:

- schema_valid: true
- render_passed: true
- section_mapping_complete: true
- safety_regression_detected: false
- experiment_outcome: success
- QA flag counts: diagram_has_no_concrete_actor:4, diagram_has_no_mechanism_verb:3
- severity counts: REVIEW:7
- diagram_nodes_too_generic: 0
- manual_insert_required_without_editor_instruction: 0
- source_card_display_title_too_generic: 0
- overflow_notes_too_large: 0
- chart_table_body_too_long_count: 0
- article_quote_missing_quote_text_count: 0

Direct alignment:

- direct_proof_type_match: strong
- direct_chartability_alignment: underprediction
- direct_diagramability_alignment: hit
- direct_source_card_alignment: hit
- direct_risk_alignment: good
- direct_slideability_prediction_quality: good
- risk_alignment_notes:
  - single_source: ok (expects source refs, source cards, or retained fact-check caution)

Direct vs adapter delta:

- direct_vs_adapter_delta: diagram_nodes_too_generic -18; review -20
- did_direct_reduce_diagram_generic: true
- did_direct_preserve_predicted_proof_types: true
- did_direct_preserve_visual_risks: true
- did_direct_improve_prediction_quality: true

### 생산적 금융과 정책자금 전환

Jibi / Anny input side:

- case_id: productive_finance_policy
- deck_id: piti_slide_spec_productive_finance_policy
- input bundle matched: true
- slideability_score: 1.0
- visualizability: high
- first_slide_idea: 이억원 "담보 및 단기수익 중심 금융 경쟁 앞서가기 어려워": 구조 diagram으로 시작하고 핵심 숫자는 보조 chart로 확인
- likely_proof_object_types: diagram, chart, source_card
- visual_risks: single_source, needs_official_data, policy_claim_risk
- reason: cluster best: chart=strong; diagram=strong; source_card=strong; risks=single_source, needs_official_data, policy_claim_risk

Adapter slide spec side:

- slide spec: data/candidates/piti_slide_specs/productive_finance_policy_slide_spec.json
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

Adapter visual QA / contract side:

- schema_valid: true
- render_passed: not_evaluated
- section_mapping_complete: true
- safety_regression_detected: not_evaluated
- experiment_outcome: -
- QA flag counts: diagram_nodes_too_generic:12, manual_insert_required_without_editor_instruction:3, overflow_notes_too_large:1
- severity counts: INFO:1, REVIEW:15
- diagram_nodes_too_generic: 12
- manual_insert_required_without_editor_instruction: 3
- source_card_display_title_too_generic: 0
- overflow_notes_too_large: 1
- chart_table_body_too_long_count: 0
- article_quote_missing_quote_text_count: 1

Adapter alignment:

- adapter_proof_type_match: strong
- adapter_chartability_alignment: hit
- adapter_diagramability_alignment: low_quality_hit
- adapter_source_card_alignment: hit
- adapter_risk_alignment: good
- adapter_slideability_prediction_quality: mixed
- risk_alignment_notes:
  - single_source: ok (expects source refs, source cards, or retained fact-check caution)
  - needs_official_data: ok (expects needs_fact_check or required_before_broadcast to remain)
  - policy_claim_risk: ok (expects do_not_claim or fact-check caution to remain)

Direct slide spec side:

- slide spec: outputs/model_dry_runs/anny_slide_spec_experiments_live/live_m132_20260520_all/productive_finance_policy/parsed_piti_slide_spec.json
- slide_count: 24
- section_count: 4
- proof_object_type_counts: article_quote:1, chart:4, diagram:12, none:5, source_card:2
- diagram_count: 12
- chart/table_count: 4
- source_card_count: 2
- article_quote_count: 1
- text_only_count: 5
- needs_fact_check_count: 17
- required_before_broadcast_count: 17
- source_refs_count: 48
- do_not_claim_count: 192

Direct visual QA / contract side:

- schema_valid: true
- render_passed: true
- section_mapping_complete: true
- safety_regression_detected: false
- experiment_outcome: success
- QA flag counts: diagram_has_no_concrete_actor:4, diagram_has_no_mechanism_verb:2
- severity counts: REVIEW:6
- diagram_nodes_too_generic: 0
- manual_insert_required_without_editor_instruction: 0
- source_card_display_title_too_generic: 0
- overflow_notes_too_large: 0
- chart_table_body_too_long_count: 0
- article_quote_missing_quote_text_count: 0

Direct alignment:

- direct_proof_type_match: strong
- direct_chartability_alignment: hit
- direct_diagramability_alignment: hit
- direct_source_card_alignment: hit
- direct_risk_alignment: good
- direct_slideability_prediction_quality: good
- risk_alignment_notes:
  - single_source: ok (expects source refs, source cards, or retained fact-check caution)
  - needs_official_data: ok (expects needs_fact_check or required_before_broadcast to remain)
  - policy_claim_risk: ok (expects do_not_claim or fact-check caution to remain)

Direct vs adapter delta:

- direct_vs_adapter_delta: diagram_nodes_too_generic -12; review -9
- did_direct_reduce_diagram_generic: true
- did_direct_preserve_predicted_proof_types: true
- did_direct_preserve_visual_risks: true
- did_direct_improve_prediction_quality: true

## Interpretation

- This comparison is for calibration only.
- Slideability is still not a candidate rejection signal.
- A good result means the hint can keep flowing into Anny input bundles.
- A weak result means the rule-based slideability heuristic needs calibration.
- Direct Anny comparison helps separate Jibi prediction quality from adapter-built slide spec limitations.
- Scoring weight changes should wait until downstream visual QA linkage is better understood.

## Next Recommended Check

- Calibrate chart underprediction and diagram-quality signals.
- Track whether direct Anny output keeps reducing generic diagram-node warnings.
- Consider a PPT contact sheet QA surface after rendered draft decks.
