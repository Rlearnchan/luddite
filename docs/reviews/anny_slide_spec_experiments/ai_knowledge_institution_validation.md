# Anny Direct Piti Slide Spec Validation: ai_knowledge_institution

- generated_at: 2026-05-20T03:11:47.030220+00:00
- mode: fixture
- raw_model_output: outputs/model_dry_runs/anny_slide_spec_experiments/ai_knowledge_institution/raw_model_output.txt
- parsed_piti_slide_spec: outputs/model_dry_runs/anny_slide_spec_experiments/ai_knowledge_institution/parsed_piti_slide_spec.json
- parse_status: parsed
- schema_valid: True
- validation_passed: True
- render_passed: True
- failure_modes: []
- source_hallucination_count: 0
- do_not_claim_violation_count: 0
- unsupported_claim_count: 0
- needs_fact_check_removed_too_aggressively: False
- required_before_broadcast_removed_too_aggressively: False
- source_refs_removed_too_aggressively: False
- do_not_claim_removed_or_ignored: False
- missing_required_schema_paths: []
- invalid_enum_values: []
- top_level_slides_empty: False
- missing_sections_slides_count: 0
- empty_sections_count: 0
- sections_with_empty_slides: []
- section_slide_ref_mismatch_count: 0
- minimum_slide_count_failed: False
- representative_deck_compressed_to_empty: False
- deck_has_no_renderable_slides: False
- slide_count_delta_vs_adapter: 0
- section_count_delta_vs_adapter: 0
- source_refs_delta_vs_adapter: 0
- needs_fact_check_delta_vs_adapter: 0
- required_before_broadcast_delta_vs_adapter: 0
- do_not_claim_delta_vs_adapter: 0
- diagram_nodes_with_arrow_count: 0
- chart_table_body_too_long_count: 0
- chart_table_body_too_long_slides: []
- article_quote_missing_quote_text_count: 0
- article_quote_missing_quote_text_slides: []
- source_card_generic_title_count: 3
- proof_object_renderer_contract_failed: False
- renderer_failure_reasons: []
- renderer_suggested_prompt_fix: Replace generic source-card titles with article/report titles.
- visible_url_count: 0
- source_card_repeated_headline_count: 0
- proof_text_overlap_count: 0
- chart_body_text_leak_count: 0
- screen_body_explanatory_sentence_count: 0
- visual_qa_severity_counts: {'REVIEW': 9, 'INFO': 2}
- QA flags are warning-only.
- ready_for_production_anny_agent: false
- ready_for_production_piti_agent: false
- ready_for_broadcast: false

## Render Result

- rendered: True
- render_passed: True
- output_pptx_path: outputs/model_dry_runs/anny_slide_spec_experiments/ai_knowledge_institution/direct_piti_slide_spec_draft.pptx

## Slide Spec Issues

- none

## Contract Diagnostics

- top_level_slides_empty: false
- sections_slides_missing: false
- empty_sections: false
- invalid_layout_intent: false
- deck_too_compressed: false
- minimum_slide_count_failed: false
- representative_deck_compressed_to_empty: false
- deck_has_no_renderable_slides: false
- safety_metadata_removed: false
- diagram_node_contains_arrow: false
- proof_object_renderer_contract_failed: false

## Schema Error Details

- none

## Renderer Failure Diagnostics

- chart_table_body_too_long: 0 slides []
- article_quote_missing_quote_text: 0 slides []
- source_card_generic_title: 3 slides [3, 11, 24]
- renderer_failure_reasons: []
- suggested_prompt_fix: Replace generic source-card titles with article/report titles.

## Visual QA Flag Counts

- manual_insert_required_without_editor_instruction: 6
- overflow_notes_too_large: 2
- source_card_display_title_too_generic: 3
