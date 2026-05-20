# Live Anny Slide Spec Review: live_m129_20260520_all

Run date: 2026-05-20

## Run Summary

- run_id: `live_m129_20260520_all`
- mode: `live`
- model: `gpt-5-mini-2025-08-07`
- command: `PYTHONPATH=src .venv/bin/python -m luddite run-anny-slide-spec-experiment --case-id all --live-api --run-id live_m129_20260520_all --timeout 600`
- output root: `outputs/model_dry_runs/anny_slide_spec_experiments_live/live_m129_20260520_all/`
- cases: `ai_knowledge_institution`, `productive_finance_policy`
- overall outcome: `failure`
- production readiness remains false.

## Case Outcomes

| case | outcome | schema_valid | render_passed | adapter diagram_nodes_too_generic | live diagram_nodes_too_generic | delta | safety_regression_detected | diagram_quality_improved |
|---|---|---:|---:|---:|---:|---:|---:|---:|
| `ai_knowledge_institution` | `failure` | false | false | 18 | 0 | -18 | true | false |
| `productive_finance_policy` | `failure` | false | false | 12 | 0 | -12 | true | false |

## What Improved

- The live model followed the strengthened diagram direction better than the adapter baseline.
- `diagram_nodes_too_generic` fell to `0` in both cases.
- No visible URL regression was detected.
- No source hallucination, `do_not_claim`, or unsupported-claim violation was counted.

Good live examples:

- AI case slide 4: `사용자(학생·관람객)가 AI에게 질문을 던짐 -> AI 서비스가 응답을 즉시 생성함 -> 사용자는 여러 출처 비교·검증 단계를 건너뛰기 쉬워짐 -> 학교·박물관은 질문·검증 훈련을 강화해야 함`
- Finance case slide 7: government/fiscal support, fund operator, and public investor roles are separated into a concrete loss-sharing diagram.

## What Failed

- Both cases failed schema validation and did not produce renderer-passing slide specs.
- `ai_knowledge_institution` omitted required `sections[].slides` arrays.
- `productive_finance_policy` used invalid `layout_intent=hook`; the schema only allows the explicit enum values.
- Both cases compressed the deck too aggressively:
  - AI case: adapter 26 slides -> live 11 slides
  - Finance case: adapter 24 slides -> live 8 slides
- Both cases removed fact-check/required-before-broadcast metadata too aggressively.
- Finance diagram nodes improved semantically, but some node strings still embed `->` inside the box text, which is awkward for broadcast diagram rendering.

Most failed live examples:

- AI case section objects: `slides` arrays are missing, so the object does not satisfy `piti_slide_spec_schema.json`.
- Finance case slide 2: `layout_intent` is `hook`, which is not a valid Piti layout intent.
- Finance case slide 8: source-backed claim content was left without an explicit proof object.

## Interpretation

This live run is useful but not successful. It suggests the diagram prompt direction is working, but the direct Anny prompt/contract is not strict enough on schema shape, slide coverage, and conservative safety metadata preservation.

The result does not justify production Anny readiness, production Piti readiness, or broadcast readiness.

## Next Prompt/Contract Fix Area

- Require schema-shaped output, not merely plausible JSON: every `section` must include a `slides` array, every array field must be an array, and layout intent must be enum-only.
- Preserve adapter-level coverage unless explicitly told otherwise; do not compress 24-26 slide representative decks into 8-11 slides.
- Preserve `needs_fact_check` and `required_before_broadcast` conservatively.
- Forbid `->` inside diagram node text; use it only as the relationship between nodes.
- Keep concrete actor/context -> mechanism/change -> result/tension diagram guidance.

