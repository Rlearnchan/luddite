# Current Product Direction after Milestone 1.26

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

The Milestone 1.26 experiment asks whether Anny can output the
`piti_slide_spec` contract directly, instead of producing storyline JSON that
is later converted by the adapter.

Default mode is deterministic fixture/synthetic validation:

- no live API call
- no new external data collection
- no production agent behavior
- no changes to the Piti renderer's non-rewriting contract

Live API mode is opt-in only via `--live-api`.

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

The experiment's main measurement question is whether direct Anny
`piti_slide_spec` output can reduce `diagram_nodes_too_generic` without
increasing source/fact-check risk, generic source-card titles, or manual
insertion warnings. Fixture mode validates the harness; it is not evidence that
production Anny is ready.

## Next Work Order

1. Review direct Anny slide spec experiment deltas and refine the Anny
   prompt/contract for concrete diagram nodes.
2. Jibi slideability scoring
3. Later: production agent/scheduler/Slack/Slides work after contracts and
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
