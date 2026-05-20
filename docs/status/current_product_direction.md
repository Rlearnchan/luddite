# Current Product Direction after Milestone 1.29

Status date: 2026-05-20

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

Live experiment outcomes are classified as:

- `success`: schema/render pass, no safety regression, and
  `diagram_nodes_too_generic` decreases versus adapter baseline.
- `partial_success`: schema/render pass and no safety regression, but diagram
  warnings do not decrease.
- `failure`: parse/schema/render failure or any source/fact-check safety
  regression.

## Next Work Order

1. Tighten Anny direct slide-spec prompt/contract for schema shape, slide
   coverage, layout enum compliance, and safety metadata preservation.
2. Re-run live opt-in after the contract fix and compare against
   `live_m129_20260520_all`.
3. Jibi slideability scoring
4. Later: production agent/scheduler/Slack/Slides work after contracts and
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
