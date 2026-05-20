# Live Anny Slide Spec Review: live_m132_20260520_all

## Run

- run_id: `live_m132_20260520_all`
- command: `PYTHONPATH=src .venv/bin/python -m luddite run-anny-slide-spec-experiment --case-id all --live-api --run-id live_m132_20260520_all --timeout 600`
- model: `gpt-5-mini-2025-08-07`
- output root: `outputs/model_dry_runs/anny_slide_spec_experiments_live/live_m132_20260520_all/`
- overall outcome: `success`
- cases: `ai_knowledge_institution`, `productive_finance_policy`
- production readiness remains false.
- broadcast readiness remains false.

## Schema Finding

`specs/piti_slide_spec_schema.json` requires `sections[].slides[]` to contain
full slide objects using `#/$defs/slide`. It does not define
`sections[].slides[]` as slide number references or slide ID references.

Therefore, a valid direct output must keep top-level `slides[]` and
section-level `sections[].slides[]` aligned over the same `slide_no` and
`slide_id` set.

## Case Summary

| case | outcome | schema_valid | render_passed | slide_count | section_mapping_complete | safety_regression_detected | diagram_nodes_too_generic |
|---|---|---:|---:|---:|---:|---:|---:|
| `ai_knowledge_institution` | `success` | true | true | 26 | true | false | 0 |
| `productive_finance_policy` | `success` | true | true | 24 | true | false | 0 |

## M129/M130/M131/M132 Comparison

| case | run | schema_valid | render_passed | slide_count | section_mapping_complete | safety_regression_detected | diagram_nodes_too_generic | notes |
|---|---|---:|---:|---:|---:|---:|---:|---|
| AI | m129 | false | false | 11 | false | true | 0 | schema/render failed and safety metadata dropped |
| AI | m130 | true | true | 0 | false | true | 0 | empty deck surfaced |
| AI | m131 | true | true | 0 | false | true | 0 | empty deck persisted, diagnostics clarified |
| AI | m132 | true | true | 26 | true | false | 0 | empty deck fixed and section mapping complete |
| Finance | m129 | false | false | 8 | false | true | 0 | schema/render failed and deck compressed |
| Finance | m130 | true | false | 24 | false | false | 0 | coverage/safety improved, renderer failed |
| Finance | m131 | true | true | 24 | false | false | 0 | renderer fixed, section mapping failed |
| Finance | m132 | true | true | 24 | true | false | 0 | section mapping complete and success |

## What Improved

- AI no longer emits a schema-valid empty deck.
- AI preserves 26-slide coverage and four sections.
- Finance preserves 24-slide coverage and four sections.
- Both cases pass schema validation and PPTX render validation.
- Both cases have `section_mapping_complete=true`.
- Both cases keep source/fact-check safety metadata conservative.
- Both cases keep `diagram_nodes_too_generic=0`.

## Remaining Caveats

- This is a controlled live experiment, not a production Anny agent.
- Live success does not imply broadcast readiness.
- Visual QA still reports review warnings, especially diagram actor/mechanism checks.
- The next decision is whether to run another live confirmation pass or move to
  Jibi slideability scoring.

## Next Step Recommendation

The section mapping contract appears fixed enough for the current two-case live
experiment. A reasonable next step is Jibi slideability scoring, while keeping
production Anny/Piti and broadcast readiness false.

