# Anny Direct Piti Slide Spec Comparison: ai_knowledge_institution

- generated_at: 2026-05-20T02:47:00.571425+00:00
- adapter_slide_spec: data/candidates/piti_slide_specs/ai_knowledge_institution_slide_spec.json
- direct_schema_valid: True
- direct_failure_modes: []
- QA flags are warning-only.
- diagram_quality_improved: true
- safety_regression_detected: false
- experiment_outcome: success

## Metrics

| Output | Slides | Sections | Proof Types | Text Only | Source Cards | Diagrams | Charts/Tables | Needs Fact Check | Required Before Broadcast | Source Refs | Do Not Claim | Visible URLs | Diagram Generic | Diagram Node Arrows | Manual Insert Missing Instruction | Generic Source Title | Overflow Notes Large | Severity Counts |
|---|---:|---:|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---|
| adapter | 26 | 4 | {'none': 4, 'diagram': 18, 'source_card': 3, 'chart': 1} | 4 | 3 | 18 | 1 | 16 | 0 | 38 | 0 | 0 | 18 | 0 | 6 | 3 | 2 | {'REVIEW': 27, 'INFO': 2} |
| direct | 26 | 4 | {'none': 4, 'diagram': 18, 'source_card': 3, 'chart': 1} | 4 | 3 | 18 | 1 | 16 | 0 | 38 | 0 | 0 | 0 | 0 | 6 | 3 | 2 | {'REVIEW': 9, 'INFO': 2} |

## Delta Summary

- diagram_nodes_too_generic_delta: -18
- manual_insert_required_without_editor_instruction_delta: 0
- source_card_display_title_too_generic_delta: 0
- overflow_notes_too_large_delta: 0
- visual_qa_review_delta: -18
- visual_qa_info_delta: 0
- visible_url_count_delta: 0
- slide_count_delta_vs_adapter: 0
- section_count_delta_vs_adapter: 0
- source_refs_delta_vs_adapter: 0
- needs_fact_check_delta_vs_adapter: 0
- required_before_broadcast_delta_vs_adapter: 0
- do_not_claim_delta_vs_adapter: 0
- diagram_nodes_with_arrow_count: 0
- missing_sections_slides_count: 0
- section_slide_ref_mismatch_count: 0
- layout_intent_invalid_enum_count: 0
- slide_count_too_compressed: false
- source_refs_removed_too_aggressively: false
- do_not_claim_removed_or_ignored: false
- safety_regression_detected: false
- diagram_quality_improved: true

## Conclusion

- diagram quality improved: true
- safety regression detected: false
- experiment outcome: success

### Contract Failure Reasons

- sections_slides_missing: False
- invalid_layout_intent: False
- deck_too_compressed: False
- safety_metadata_removed: False
- diagram_node_contains_arrow: False

### Better

- diagram_nodes_too_generic decreased
- manual insert instruction warnings did not increase
- source card generic title warnings did not increase
- no source/fact-check safety regression detected

### Worse

- none

### Remaining Before Production

- Direct slide spec experiment is not a production Anny agent.
- Production readiness remains false.
- Next prompt/contract work should verify schema shape, slide coverage, and safety metadata in live output.

### Next Prompt/Contract Suggestions

- Make diagram nodes concrete at Anny output time, not in the Piti renderer.
- Make schema shape explicit: every section needs slides[], and top-level slides must match.
- Preserve adapter-level slide coverage; do not over-compress representative decks.
- Require at least one actor, one mechanism verb, and one result node for diagrams.
- Keep source/fact-check flags conservative.
- Keep source_refs and do_not_claim guardrails unless the prompt supplies a clear reason.
- Forbid arrows inside diagram node text; relationships belong in diagram_edges.
- Keep overflow_notes_too_large as INFO until human review says otherwise.
