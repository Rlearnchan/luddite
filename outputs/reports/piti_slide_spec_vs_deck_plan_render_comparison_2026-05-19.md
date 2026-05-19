# Piti Slide Spec vs Deck Plan Render Comparison

- Generated at: 2026-05-19T12:39:16.842603+00:00
- Purpose: compare legacy deck_plan rendering against Piti slide_spec rendering.
- Production Piti agent: not implemented
- Image insertion/chart generation: none

## Summary

| Deck | Baseline Text Only | Slide Spec Text Only | Baseline Proof Objects | Slide Spec Proof Objects | Baseline Screen Lines | Slide Spec Screen Lines | Baseline URLs In Notes | Slide Spec URLs In Notes | Baseline Overlap | Slide Spec Overlap |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| piti_slide_spec_ai_knowledge_institution | 9 | 8 | 17 | 18 | 30 | 33 | 8 | 8 | 0 | 0 |
| piti_slide_spec_productive_finance_policy | 6 | 6 | 18 | 18 | 19 | 18 | 11 | 11 | 0 | 0 |

## Details

### piti_slide_spec_ai_knowledge_institution

- baseline_deck_plan_path: data/candidates/piti_deck_plans/ai_knowledge_institution_deck_plan.json
- slide_spec_path: data/candidates/piti_slide_specs/ai_knowledge_institution_slide_spec.json
- baseline_metrics: {'slide_count': 26, 'proof_object_type_counts': {'source_card': 11, 'diagram': 5, 'chart': 1}, 'proof_object_slide_count': 17, 'text_only_slide_count': 9, 'screen_body_line_total': 30, 'needs_fact_check_count': 16, 'visible_url_count': 0, 'source_url_count_in_notes': 8, 'source_card_repeated_headline_count': 0, 'chart_body_text_leak_count': 0, 'proof_text_overlap_count': 0, 'dense_slide_count': 0}
- slide_spec_metrics: {'slide_count': 26, 'proof_object_type_counts': {'source_card': 17, 'chart': 1}, 'proof_object_slide_count': 18, 'text_only_slide_count': 8, 'screen_body_line_total': 33, 'needs_fact_check_count': 16, 'visible_url_count': 0, 'source_url_count_in_notes': 8, 'source_card_repeated_headline_count': 0, 'chart_body_text_leak_count': 0, 'proof_text_overlap_count': 0, 'dense_slide_count': 0}

### piti_slide_spec_productive_finance_policy

- baseline_deck_plan_path: data/candidates/piti_deck_plans/productive_finance_policy_deck_plan.json
- slide_spec_path: data/candidates/piti_slide_specs/productive_finance_policy_slide_spec.json
- baseline_metrics: {'slide_count': 24, 'proof_object_type_counts': {'source_card': 7, 'diagram': 9, 'chart': 1, 'article_quote': 1}, 'proof_object_slide_count': 18, 'text_only_slide_count': 6, 'screen_body_line_total': 19, 'needs_fact_check_count': 17, 'visible_url_count': 0, 'source_url_count_in_notes': 11, 'source_card_repeated_headline_count': 0, 'chart_body_text_leak_count': 0, 'proof_text_overlap_count': 0, 'dense_slide_count': 1}
- slide_spec_metrics: {'slide_count': 24, 'proof_object_type_counts': {'chart': 4, 'source_card': 10, 'diagram': 3, 'article_quote': 1}, 'proof_object_slide_count': 18, 'text_only_slide_count': 6, 'screen_body_line_total': 18, 'needs_fact_check_count': 17, 'visible_url_count': 0, 'source_url_count_in_notes': 11, 'source_card_repeated_headline_count': 0, 'chart_body_text_leak_count': 0, 'proof_text_overlap_count': 0, 'dense_slide_count': 2}

## Readiness

- ready_for_piti_renderer_contract: true
- ready_for_production_piti_agent: false
- ready_for_broadcast: false
