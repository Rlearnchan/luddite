# Anny Direct Piti Slide Spec Comparison: productive_finance_policy

- generated_at: 2026-05-20T01:52:34.980761+00:00
- adapter_slide_spec: data/candidates/piti_slide_specs/productive_finance_policy_slide_spec.json
- direct_schema_valid: True
- direct_failure_modes: []
- QA flags are warning-only.
- diagram_quality_improved: true
- safety_regression_detected: false

## Metrics

| Output | Slides | Sections | Proof Types | Text Only | Source Cards | Diagrams | Charts/Tables | Needs Fact Check | Required Before Broadcast | Visible URLs | Diagram Generic | Manual Insert Missing Instruction | Generic Source Title | Overflow Notes Large | Severity Counts |
|---|---:|---:|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---|
| adapter | 24 | 4 | {'none': 6, 'chart': 4, 'diagram': 12, 'source_card': 1, 'article_quote': 1} | 6 | 1 | 12 | 4 | 17 | 17 | 0 | 12 | 3 | 0 | 1 | {'REVIEW': 15, 'INFO': 1} |
| direct | 24 | 4 | {'none': 6, 'chart': 4, 'diagram': 12, 'source_card': 1, 'article_quote': 1} | 6 | 1 | 12 | 4 | 17 | 17 | 0 | 0 | 3 | 0 | 1 | {'REVIEW': 3, 'INFO': 1} |

## Delta Summary

- diagram_nodes_too_generic_delta: -12
- manual_insert_required_without_editor_instruction_delta: 0
- source_card_display_title_too_generic_delta: 0
- overflow_notes_too_large_delta: 0
- visual_qa_review_delta: -12
- visual_qa_info_delta: 0
- visible_url_count_delta: 0
- safety_regression_detected: false
- diagram_quality_improved: true

## Conclusion

- diagram quality improved: true
- safety regression detected: false

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
- Next prompt/contract work should target diagram actor -> mechanism -> result quality.

### Next Prompt/Contract Suggestions

- Make diagram nodes concrete at Anny output time, not in the Piti renderer.
- Require at least one actor, one mechanism verb, and one result node for diagrams.
- Keep source/fact-check flags conservative.
- Keep overflow_notes_too_large as INFO until human review says otherwise.
