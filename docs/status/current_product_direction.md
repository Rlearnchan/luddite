# Current Product Direction after Milestone 1.22

Status date: 2026-05-20

## Current Checkpoint

Luddite has a working deterministic scaffold for the current research-to-deck
path:

- `jibi -> anny -> piti` end-to-end scaffold exists.
- Anny dry-run/enriched storyline fixtures can be converted into
  `piti_slide_spec` JSON.
- `piti_slide_spec -> styled PPTX draft` rendering works for the two current
  sample decks.
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

## Next Work Order

1. Piti visual QA
2. Anny direct Piti slide spec experiment
3. Jibi slideability scoring

Milestone 1.24 should add a deterministic Piti visual QA report:

- Input: `data/candidates/piti_slide_specs/*.json`
- Per-deck output: `outputs/qa/piti_visual_qa/{deck_id}.md`
- Summary output: `outputs/qa/piti_visual_qa/piti_visual_qa_summary.md`
- GitHub-visible review mirror:
  `docs/reviews/piti_visual_qa/{deck_id}.md` and
  `docs/reviews/piti_visual_qa/piti_visual_qa_summary.md`
- QA flags are review warnings only, not failure gates.
- No LLM/API calls, image insertion, chart generation, or Google Slides
  integration.

## Out Of Scope For The Next Milestone

- production Anny agent
- production Piti agent
- scheduler
- Slack bot
- automatic image insertion
- automatic chart generation
- Google Slides integration
- broadcast readiness claims
