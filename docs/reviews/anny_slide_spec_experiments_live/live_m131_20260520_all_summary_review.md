# Live Anny Slide Spec Review: live_m131_20260520_all

## Run

- run_id: `live_m131_20260520_all`
- command: `PYTHONPATH=src .venv/bin/python -m luddite run-anny-slide-spec-experiment --case-id all --live-api --run-id live_m131_20260520_all --timeout 600`
- model: `gpt-5-mini-2025-08-07`
- output root: `outputs/model_dry_runs/anny_slide_spec_experiments_live/live_m131_20260520_all/`
- overall outcome: `failure`
- cases: `ai_knowledge_institution`, `productive_finance_policy`
- production readiness remains false.
- broadcast readiness remains false.

## Case Summary

| case | outcome | schema_valid | render_passed | slide_count | safety_regression_detected | diagram_nodes_too_generic | key failure |
|---|---|---:|---:|---:|---:|---:|---|
| `ai_knowledge_institution` | `failure` | true | true | 0 | true | 0 | schema-valid empty deck |
| `productive_finance_policy` | `failure` | true | true | 24 | false | 0 | empty `sections[].slides` arrays |

## M129/M130/M131 Comparison

| case | run | schema_valid | render_passed | slide_count | safety_regression_detected | diagram_nodes_too_generic | notes |
|---|---|---:|---:|---:|---:|---:|---|
| AI | m129 | false | false | 11 | true | 0 | schema/render failed and safety metadata dropped |
| AI | m130 | true | true | 0 | true | 0 | empty deck surfaced |
| AI | m131 | true | true | 0 | true | 0 | empty deck persists, diagnostics are clearer |
| Finance | m129 | false | false | 8 | true | 0 | schema/render failed and deck compressed |
| Finance | m130 | true | false | 24 | false | 0 | coverage/safety improved, renderer failed |
| Finance | m131 | true | true | 24 | false | 0 | renderer fixed, section slide arrays still empty |

## What Improved

- Finance now renders successfully.
- Finance preserves 24-slide coverage.
- Finance preserves `needs_fact_check`, `required_before_broadcast`, and source refs versus the adapter baseline.
- Renderer-specific proof diagnostics are clean in m131: no chart/table long body, no missing `article_quote.quote_text`, and no generic source-card title.
- Both cases keep `diagram_nodes_too_generic=0`, so the concrete diagram direction still looks useful.

## What Still Fails

- AI still returns a schema-valid empty deck.
- AI removes source/fact-check metadata too aggressively because it has no renderable slides.
- Both cases have section-level slide arrays that are empty or mismatched with top-level `slides[]`.
- Live success is still false.

## Best Live Signal

The finance case is the best signal from this run: it keeps the representative 24-slide deck, passes schema and render, avoids renderer proof-object failures, preserves safety metadata, and keeps generic diagram warnings at zero.

## Worst Live Signal

The AI case is the failure to study next: it passes schema and render only because the output is structurally valid but empty. The diagnostics correctly flag `top_level_slides_empty`, `empty_sections`, `minimum_slide_count_failed`, `representative_deck_compressed_to_empty`, and `deck_has_no_renderable_slides`.

## Next Prompt/Contract Fix

The next fix should focus on section mapping and non-empty slide duplication rules:

- Require every `sections[].slides` array to contain the actual slide objects for that section, not empty arrays.
- Make the expected relationship between top-level `slides[]` and `sections[].slides[]` concrete with an example shape.
- Keep the empty-deck failure diagnostics.
- Keep renderer proof-object diagnostics, because they helped confirm the finance renderer issue was resolved.
- Do not move this to Piti: Piti should continue rendering only the provided `piti_slide_spec`.

