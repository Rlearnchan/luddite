# Live Anny Slide Spec Review: live_m130_20260520_all

Run date: 2026-05-20

## Run Summary

- run_id: `live_m130_20260520_all`
- mode: `live`
- model: `gpt-5-mini-2025-08-07`
- command: `PYTHONPATH=src .venv/bin/python -m luddite run-anny-slide-spec-experiment --case-id all --live-api --run-id live_m130_20260520_all --timeout 600`
- output root: `outputs/model_dry_runs/anny_slide_spec_experiments_live/live_m130_20260520_all/`
- cases: `ai_knowledge_institution`, `productive_finance_policy`
- overall outcome: `failure`
- production readiness remains false.

## M129 To M130 Comparison

| case | m129 schema | m130 schema | m129 render | m130 render | m129 slides | m130 slides | m129 safety regression | m130 safety regression | m129 diagram generic | m130 diagram generic |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| `ai_knowledge_institution` | false | true | false | true | 11 | 0 | true | true | 0 | 0 |
| `productive_finance_policy` | false | true | false | false | 8 | 24 | true | false | 0 | 0 |

## Case Outcomes

### ai_knowledge_institution

- outcome: `failure`
- schema_valid: true
- render_passed: true
- slide_count: 0, adapter baseline: 26
- missing_sections_slides_count: 4
- source_refs_delta_vs_adapter: -38
- needs_fact_check_delta_vs_adapter: -16
- failure modes: `sections_slides_missing`, `deck_too_compressed`, `needs_fact_check_removed_too_aggressively`, `source_refs_removed_too_aggressively`, `safety_metadata_removed`

Interpretation: schema validity alone is not enough. The model emitted an empty
deck shape that passed JSON schema but failed the stronger experiment contract.
The new diagnostics correctly expose this as a contract failure.

### productive_finance_policy

- outcome: `failure`
- schema_valid: true
- render_passed: false
- slide_count: 24, adapter baseline: 24
- source_refs_delta_vs_adapter: 0
- needs_fact_check_delta_vs_adapter: 0
- required_before_broadcast_delta_vs_adapter: 0
- diagram_nodes_too_generic: 0
- diagram_nodes_with_arrow_count: 0
- safety_regression_detected: false
- failure modes: `piti_render_failed`

Interpretation: this is a real improvement over m129. The live model preserved
slide coverage and safety metadata, kept concrete diagram nodes, and avoided
arrow chains inside diagram node text. It still failed renderer validation:
slide 2 has too much chart/table body text, and slide 15 is an article quote
without quote text.

## What Improved

- The prompt/contract reinforcement improved failure visibility.
- New validation reports now show `missing_sections_slides_count`,
  `slide_count_delta_vs_adapter`, `source_refs_delta_vs_adapter`,
  `needs_fact_check_delta_vs_adapter`, `required_before_broadcast_delta_vs_adapter`,
  and `diagram_nodes_with_arrow_count`.
- Finance live output improved from compressed/safety-regressed failure to
  schema-valid, coverage-preserving, safety-preserving output with only renderer
  contract failures remaining.

## What Still Fails

- AI live output can still produce an empty schema-valid deck.
- Finance live output still violates renderer-level slide requirements.
- `diagram_quality_improved` remains false because success requires schema,
  render, safety, and visual QA improvement together.

## Next Recommended Fix Area

- Add stronger non-empty deck requirements to the live prompt and/or validator
  messaging: top-level `slides[]` must not be empty, section `slides[]` must not
  be empty, and slide count must remain close to adapter baseline.
- Add renderer-specific prompt warnings for chart/table body length and
  `article_quote` quote text.
- Consider a future live opt-in structured-output/schema mode for the experiment,
  without changing Piti's non-rewriting renderer contract.

