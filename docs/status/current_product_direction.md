# Current Product Direction after Milestone 1.36

Status date: 2026-05-21

## Current Checkpoint

Luddite has a working deterministic scaffold for the current research-to-deck
path:

- `jibi -> anny -> piti` end-to-end scaffold exists.
- Anny dry-run/enriched storyline fixtures can be converted into
  `piti_slide_spec` JSON.
- `piti_slide_spec -> styled PPTX draft` rendering works for the two current
  sample decks.
- `luddite render-piti-visual-qa` writes warning-only visual QA reports to
  `outputs/qa/piti_visual_qa/` and GitHub-visible mirrors under
  `docs/reviews/piti_visual_qa/`.
- Piti visual QA now includes severity, flag reasons, review hints, top review
  queue prioritization, and next recommended fix area.
- `luddite run-anny-slide-spec-experiment` runs a controlled Anny direct
  `piti_slide_spec` experiment in fixture mode by default, without live API
  calls.
- The experiment writes per-case validation, visual QA, and adapter comparison
  reports for `ai_knowledge_institution` and `productive_finance_policy`.
- In fixture mode, direct slide-spec output now applies deterministic concrete
  diagram fixtures at the Anny/direct-output stage. This reduces generic
  diagram-node warnings without changing Piti renderer behavior.
- Live opt-in runs are separated under
  `outputs/model_dry_runs/anny_slide_spec_experiments_live/{run_id}/` and write
  a run-level `summary.md`.
- Milestone 1.29 ran the live opt-in experiment for both current cases. The
  run produced useful diagnostics, but both live cases were classified as
  `failure`.
- Milestone 1.30 strengthened the Anny direct prompt/contract around schema
  shape, slide coverage, safety metadata preservation, and diagram node text.
- The experiment validation/comparison reports now expose detailed contract
  diagnostics such as missing section slides, invalid layout intent, deck
  compression, removed source refs, and diagram node arrows.
- Milestone 1.31 strengthened the Anny direct prompt/contract around empty-deck
  prevention and renderer-specific proof-object requirements.
- The live validation/comparison reports now expose empty-deck and renderer
  diagnostics such as `top_level_slides_empty`, `empty_sections_count`,
  `minimum_slide_count_failed`, `deck_has_no_renderable_slides`,
  `chart_table_body_too_long_count`, `article_quote_missing_quote_text_count`,
  and `renderer_failure_reasons`.
- Milestone 1.32 confirmed that `sections[].slides[]` is a full slide-object
  array in `specs/piti_slide_spec_schema.json`, then fixed the Anny direct
  section mapping contract around that schema shape.
- The experiment reports now expose section mapping details such as
  `section_mapping_complete`, `top_level_slide_numbers`,
  `section_mapped_slide_numbers`, `missing_from_sections`,
  `duplicate_section_slide_refs`, `slides_missing_section_id`, and
  `slides_with_unknown_section_id`.
- Milestone 1.33 adds deterministic Jibi `slideability` scoring v0 to scored
  candidates, story seed clusters, handoff records, daily digest output, and
  Jibi review reports.
- `slideability` is a review/report signal only. It does not hard reject
  candidates, does not change `recommended_action`, and does not make
  production/broadcast readiness true.
- Milestone 1.34 passes Jibi slideability into Anny input bundles as
  top-level `visual_planning_hint`, separate from evidence and fact-check
  tasks.
- `visual_planning_hint` is planning context only. It is not evidence, cannot
  justify claims, and must not override `do_not_claim`, `needs_source`, or
  `needs_fact_check` guardrails.
- Milestone 1.35 adds a review-only comparison between Jibi/Anny
  slideability hints and downstream Piti slide specs / visual QA.
- Milestone 1.36 extends that comparison to include Anny direct live slide
  specs from `live_m132_20260520_all`, alongside adapter-built Piti specs.
- The comparison is calibration only. It does not change Jibi scoring,
  `recommended_action`, handoff gates, Anny prompts, or Piti rendering.
- The Piti renderer contract is now explicit: Piti does not infer, enrich, or
  rewrite meaning. Piti renders the provided `piti_slide_spec` only.
- The current PPTX output is a review draft, not a broadcast-ready deck.

The project is still not a production agent system:

- production Anny agent: not implemented
- production Piti agent: not implemented
- scheduler: not implemented
- Slack bot: not implemented
- image auto insertion: not implemented
- chart auto generation: not implemented
- Google Slides integration: not implemented
- broadcast handoff: not approved

## Readiness Flags

```text
ready_for_piti_renderer_contract=true
ready_for_api_experiment=true
ready_for_production_anny_agent=false
ready_for_production_piti_agent=false
ready_for_broadcast=false
```

Interpretation:

- `ready_for_piti_renderer_contract=true` means the explicit slide-spec
  contract is stable enough for deterministic renderer and QA work.
- `ready_for_api_experiment=true` means controlled Anny API experiments may
  continue against the current contracts and fixtures.
- The production-agent and broadcast flags remain false until human review,
  scheduling, source/fact-check operations, and final deck QA are designed and
  implemented.

## Direction

Piti's responsibility is intentionally narrow:

- Piti renders `piti_slide_spec`.
- Piti does not decide what a slide means.
- Piti does not rewrite the headline/body for meaning.
- Piti does not invent proof objects, charts, screenshots, images, or sources.
- Piti may surface renderer/visual QA warnings so a human can decide which
  slides need visual inspection.

The near-term goal is not prettier PPT. The goal is to expose the slides that a
human must review before any broadcast workflow is considered.

## Current Commands

```text
make build-piti-slide-specs
make validate-piti-slide-spec
make render-piti-slide-spec-pptx
make render-piti-visual-qa
make run-anny-slide-spec-experiment
make normalize-candidates
make score-candidates
make cluster-jibi-candidates
make render-daily-digest
make build-anny-input-bundles
make prepare-anny-input-bundles
make compare-slideability-visual-qa
```

Current fixture inputs:

```text
data/candidates/piti_slide_specs/ai_knowledge_institution_slide_spec.json
data/candidates/piti_slide_specs/productive_finance_policy_slide_spec.json
```

Current styled draft outputs:

```text
outputs/pptx/ai_knowledge_institution_slide_spec_styled_draft.pptx
outputs/pptx/productive_finance_policy_slide_spec_styled_draft.pptx
```

## Current Visual QA Status

Current GitHub-visible review reports:

```text
docs/reviews/piti_visual_qa/piti_visual_qa_summary.md
docs/reviews/piti_visual_qa/piti_slide_spec_ai_knowledge_institution.md
docs/reviews/piti_visual_qa/piti_slide_spec_productive_finance_policy.md
```

Current summary:

```text
Decks: 2
Slides: 50
Flagged slides: 33
QA flags: 45
Severity: BLOCKER 0, REVIEW 42, INFO 3
Main weakness: diagram proof objects are still too generic.
Recommended next fix: improve Anny/adapter diagram node generation, not Piti renderer.
```

Visual QA remains warning-only. No QA severity currently fails
`make render-piti-visual-qa`.

## Current Anny Direct Slide Spec Experiment

The direct slide-spec experiment asks whether Anny can output the
`piti_slide_spec` contract directly, instead of producing storyline JSON that
is later converted by the adapter.

Default mode is deterministic fixture/synthetic validation:

- no live API call
- no new external data collection
- no production agent behavior
- no changes to the Piti renderer's non-rewriting contract
- deterministic concrete diagram-node fixtures for the two current cases

Live API mode is opt-in only via `--live-api`. Default Make and test paths do
not call the API.

Primary outputs:

```text
outputs/model_dry_runs/anny_slide_spec_experiments/{case_id}/raw_model_output.txt
outputs/model_dry_runs/anny_slide_spec_experiments/{case_id}/parsed_piti_slide_spec.json
outputs/model_dry_runs/anny_slide_spec_experiments/{case_id}/validation_report.md
outputs/model_dry_runs/anny_slide_spec_experiments/{case_id}/visual_qa_report.md
outputs/model_dry_runs/anny_slide_spec_experiments/{case_id}/comparison_against_adapter.md
```

GitHub-visible review mirrors:

```text
docs/reviews/anny_slide_spec_experiments/{case_id}_validation.md
docs/reviews/anny_slide_spec_experiments/{case_id}_comparison.md
```

Live outputs are deliberately separated from fixture outputs:

```text
outputs/model_dry_runs/anny_slide_spec_experiments_live/{run_id}/{case_id}/raw_model_output.txt
outputs/model_dry_runs/anny_slide_spec_experiments_live/{run_id}/{case_id}/parsed_piti_slide_spec.json
outputs/model_dry_runs/anny_slide_spec_experiments_live/{run_id}/{case_id}/validation_report.md
outputs/model_dry_runs/anny_slide_spec_experiments_live/{run_id}/{case_id}/visual_qa_report.md
outputs/model_dry_runs/anny_slide_spec_experiments_live/{run_id}/{case_id}/comparison_against_adapter.md
outputs/model_dry_runs/anny_slide_spec_experiments_live/{run_id}/summary.md
```

Live review mirrors are off by default. Use `--mirror-live-review` only when a
live run should be copied under `docs/reviews/anny_slide_spec_experiments_live/`.

Live command examples:

```text
PYTHONPATH=src .venv/bin/python -m luddite run-anny-slide-spec-experiment --case-id ai_knowledge_institution --live-api
PYTHONPATH=src .venv/bin/python -m luddite run-anny-slide-spec-experiment --case-id productive_finance_policy --live-api
PYTHONPATH=src .venv/bin/python -m luddite run-anny-slide-spec-experiment --case-id all --live-api
```

Current fixture comparison:

```text
ai_knowledge_institution:
  adapter diagram_nodes_too_generic: 18
  direct diagram_nodes_too_generic: 0
  diagram_quality_improved: true
  safety_regression_detected: false

productive_finance_policy:
  adapter diagram_nodes_too_generic: 12
  direct diagram_nodes_too_generic: 0
  diagram_quality_improved: true
  safety_regression_detected: false
```

This is evidence that the direct-output contract can carry better diagram
copy when Anny provides it explicitly. It is still not evidence that production
Anny is ready, because fixture mode is deterministic and does not prove live
model behavior.

Current live run:

```text
run_id: live_m129_20260520_all
mode: live
model: gpt-5-mini-2025-08-07
outcome: failure for both cases
output_root: outputs/model_dry_runs/anny_slide_spec_experiments_live/live_m129_20260520_all/
review_note: docs/reviews/anny_slide_spec_experiments_live/live_m129_20260520_all_summary_review.md
```

Live comparison:

```text
ai_knowledge_institution:
  adapter diagram_nodes_too_generic: 18
  live diagram_nodes_too_generic: 0
  schema_valid: false
  render_passed: false
  safety_regression_detected: true
  diagram_quality_improved: false

productive_finance_policy:
  adapter diagram_nodes_too_generic: 12
  live diagram_nodes_too_generic: 0
  schema_valid: false
  render_passed: false
  safety_regression_detected: true
  diagram_quality_improved: false
```

Interpretation:

- The strengthened diagram prompt direction is promising: live output reduced
  `diagram_nodes_too_generic` to `0` in both cases.
- The live run is still a failure because schema/render validation failed and
  source/fact-check metadata was removed too aggressively.
- The direct Anny prompt/contract must next enforce schema shape, slide coverage,
  enum-only `layout_intent`, and conservative safety flag preservation.
- This live run does not make production Anny, production Piti, or broadcast
  readiness true.

Current contract-strengthening live rerun:

```text
run_id: live_m130_20260520_all
mode: live
model: gpt-5-mini-2025-08-07
outcome: failure for both cases
output_root: outputs/model_dry_runs/anny_slide_spec_experiments_live/live_m130_20260520_all/
review_note: docs/reviews/anny_slide_spec_experiments_live/live_m130_20260520_all_summary_review.md
```

M129 to M130 comparison:

```text
ai_knowledge_institution:
  schema_valid: false -> true
  render_passed: false -> true
  slide_count: 11 -> 0
  safety_regression_detected: true -> true
  diagram_nodes_too_generic: 0 -> 0
  interpretation: still failure; schema-valid empty deck was caught by contract diagnostics.

productive_finance_policy:
  schema_valid: false -> true
  render_passed: false -> false
  slide_count: 8 -> 24
  safety_regression_detected: true -> false
  diagram_nodes_too_generic: 0 -> 0
  diagram_nodes_with_arrow_count: 0
  interpretation: improved; coverage/safety/schema pass, but renderer contract issues remain.
```

The m130 live rerun is not a success, but it shows the strengthened contract is
useful: it caught an empty schema-valid AI deck and showed that the finance case
can preserve coverage and safety metadata under the new prompt.

Current empty-deck/render-contract live rerun:

```text
run_id: live_m131_20260520_all
mode: live
model: gpt-5-mini-2025-08-07
outcome: failure for both cases
output_root: outputs/model_dry_runs/anny_slide_spec_experiments_live/live_m131_20260520_all/
review_note: docs/reviews/anny_slide_spec_experiments_live/live_m131_20260520_all_summary_review.md
```

M129/M130/M131 comparison:

```text
ai_knowledge_institution:
  m129: schema_valid=false, render_passed=false, slide_count=11, safety_regression=true
  m130: schema_valid=true, render_passed=true, slide_count=0, safety_regression=true
  m131: schema_valid=true, render_passed=true, slide_count=0, safety_regression=true
  interpretation: still failure; schema-valid empty deck persists, but diagnostics are explicit.

productive_finance_policy:
  m129: schema_valid=false, render_passed=false, slide_count=8, safety_regression=true
  m130: schema_valid=true, render_passed=false, slide_count=24, safety_regression=false
  m131: schema_valid=true, render_passed=true, slide_count=24, safety_regression=false
  interpretation: improved; renderer proof failures cleared, coverage/safety stayed intact,
  but `sections[].slides` arrays are still empty and mismatched with top-level slides.
```

Milestone 1.31 interpretation:

- Finance moved from renderer failure to render pass while preserving 24-slide
  coverage and conservative safety metadata.
- Both live cases still fail because section slide arrays are empty or missing
  usable slide references.
- AI still emits a schema-valid empty deck, so empty-deck prevention is not yet
  solved for live output.
- `diagram_nodes_too_generic` remains `0` in both live cases, so the concrete
  diagram direction remains promising.
- This live rerun does not make production Anny, production Piti, or broadcast
  readiness true.

Current section-mapping live rerun:

```text
run_id: live_m132_20260520_all
mode: live
model: gpt-5-mini-2025-08-07
outcome: success for both cases
output_root: outputs/model_dry_runs/anny_slide_spec_experiments_live/live_m132_20260520_all/
review_note: docs/reviews/anny_slide_spec_experiments_live/live_m132_20260520_all_summary_review.md
```

Schema finding:

```text
sections[].slides[] is a full slide-object array using #/$defs/slide.
It is not a slide number or slide ID reference array.
Top-level slides[] and section-level sections[].slides[] must cover the same
slide_no and slide_id set.
```

M129/M130/M131/M132 comparison:

```text
ai_knowledge_institution:
  m129: schema_valid=false, render_passed=false, slide_count=11, section_mapping_complete=false, safety_regression=true
  m130: schema_valid=true, render_passed=true, slide_count=0, section_mapping_complete=false, safety_regression=true
  m131: schema_valid=true, render_passed=true, slide_count=0, section_mapping_complete=false, safety_regression=true
  m132: schema_valid=true, render_passed=true, slide_count=26, section_mapping_complete=true, safety_regression=false

productive_finance_policy:
  m129: schema_valid=false, render_passed=false, slide_count=8, section_mapping_complete=false, safety_regression=true
  m130: schema_valid=true, render_passed=false, slide_count=24, section_mapping_complete=false, safety_regression=false
  m131: schema_valid=true, render_passed=true, slide_count=24, section_mapping_complete=false, safety_regression=false
  m132: schema_valid=true, render_passed=true, slide_count=24, section_mapping_complete=true, safety_regression=false
```

Milestone 1.32 interpretation:

- AI no longer emits a schema-valid empty deck in the m132 live run.
- Finance now passes schema, render, safety, coverage, and section mapping.
- Both live cases have `section_mapping_complete=true`.
- Both live cases keep `diagram_nodes_too_generic=0`.
- This is meaningful controlled-experiment evidence, not production readiness.
- Production Anny, production Piti, and broadcast readiness remain false.

Live experiment outcomes are classified as:

- `success`: schema/render pass, no safety regression, and
  `diagram_nodes_too_generic` decreases versus adapter baseline.
- `partial_success`: schema/render pass and no safety regression, but diagram
  warnings do not decrease.
- `failure`: parse/schema/render failure or any source/fact-check safety
  regression.

## Current Jibi Slideability Status

Milestone 1.33 adds a rule-based `slideability` object to Jibi scored
candidates and story seed clusters:

```text
score: 0.0-1.0
visualizability: low|medium|high
chartability: none|weak|strong
diagramability: none|weak|strong
screenshotability: none|weak|strong
source_card_fit: none|weak|strong
first_slide_idea: short human-readable first-slide suggestion
likely_proof_object_types: diagram/chart/source_card
risks: too_abstract, single_source, needs_official_data, policy_claim_risk, market_claim_risk, no_clear_visual
reason: compact deterministic explanation
```

The v0 scorer is deterministic and does not call an LLM/API. It looks for
numeric/trend cues, actor-mechanism-result cues, explicit source/report cues,
and visual risks. It is intentionally separate from the existing Jibi score and
handoff gate.

Current generated sample reports expose slideability in:

```text
outputs/reports/jibi_quality_2026-05-20.md
outputs/reports/jibi_clusters_2026-05-20.md
outputs/daily_digest/2026-05-20.md
outputs/daily_digest/2026-05-20_clusters.md
outputs/daily_digest/2026-05-20_story_seed_handoff.md
```

GitHub-visible implementation note:

```text
docs/reviews/jibi_slideability_v0.md
docs/reviews/anny_input_bundle_slideability_v0.md
docs/reviews/slideability_visual_qa_comparison.md
```

## Current Anny Input Bundle Visual Planning Status

Anny input bundles may now include:

```text
visual_planning_hint:
  slideability_score: 0.0-1.0
  visualizability: low|medium|high
  first_slide_idea: tentative opening visual idea
  likely_proof_object_types: diagram/chart/source_card
  visual_risks: single_source, needs_official_data, policy_claim_risk, market_claim_risk, ...
  reason: deterministic Jibi slideability explanation
  planning_note: reminder that the hint is not evidence
```

Current representative examples:

```text
생산적 금융과 정책자금 전환:
  high / diagram+chart+source_card
  risks: single_source, needs_official_data, policy_claim_risk
  guardrails: needs_fact_check=true; official/numeric/source checks remain

AI 즉답 시대의 지식기관 역할:
  high / diagram+source_card
  risks: single_source
  guardrails: needs_fact_check=true; source/fact-check caution remains
```

## Current Slideability vs Visual QA Comparison

Current report outputs:

```text
outputs/reports/slideability_visual_qa_comparison_2026-05-21.md
docs/reviews/slideability_visual_qa_comparison.md
```

Current comparison result with Anny direct live run:

```text
direct_run_id: live_m132_20260520_all

AI 즉답 시대의 지식기관 역할:
  adapter:
    chartability_alignment: underprediction
    diagramability_alignment: low_quality_hit
    risk_alignment: good
    slideability_prediction_quality: mixed
  direct:
    chartability_alignment: underprediction
    diagramability_alignment: hit
    risk_alignment: good
    slideability_prediction_quality: good
    diagram_nodes_too_generic_delta: -18

생산적 금융과 정책자금 전환:
  adapter:
    chartability_alignment: hit
    diagramability_alignment: low_quality_hit
    risk_alignment: good
    slideability_prediction_quality: mixed
  direct:
    chartability_alignment: hit
    diagramability_alignment: hit
    risk_alignment: good
    slideability_prediction_quality: good
    diagram_nodes_too_generic_delta: -12
```

Interpretation:

- Jibi correctly predicted that both current cases need diagram/source-card
  proof objects, and finance also needs chart support.
- Adapter-built and direct Anny specs both preserve the predicted proof object
  families.
- Risk hints align with retained source/fact-check caution.
- The adapter-built specs still trigger `diagram_nodes_too_generic`, but the
  direct Anny live specs reduce those warnings to zero and move diagramability
  from `low_quality_hit` to `hit`.
- AI still has chart underprediction: Jibi did not predict chart, but both
  adapter and direct specs contain one chart slide.
- This supports keeping slideability as Anny input context, while calibrating
  chartability and diagram-quality heuristics before using slideability as a
  scoring weight.

## Next Work Order

1. Calibrate the rule-based slideability heuristic around chart
   underprediction and diagram-quality prediction, while keeping it review-only.
2. Consider a PPT contact-sheet QA surface for rendered draft decks.
3. Optionally run one more live Anny direct confirmation pass before widening
   the case set.
4. Keep using visual QA and comparison reports as warning-only review surfaces.
5. Later: production agent/scheduler/Slack/Slides work after contracts and
   review workflow mature

## Out Of Scope For The Next Milestone

- production Anny agent
- production Piti agent
- scheduler
- Slack bot
- automatic image insertion
- automatic chart generation
- Google Slides integration
- broadcast readiness claims
