# Anny Output Contract

Status date: 2026-05-18

This contract describes the manual-dry-run output shape that production anny
prompts must satisfy later. It is not a production anny agent spec yet, and it
does not authorize LLM API calls.

## Required Top-Level Fields

- `storyline_id`
- `title`
- `one_liner`
- `estimated_slide_count`
- `risk_flags`
- `required_fact_checks`
- `sections`

Optional but recommended:

- `case_id`
- `bundle_id`
- `story_seed_title`
- `section_plan`
- `key_beat_coverage`
- `do_not_claim`
- `avoid`
- `source_hygiene_path`

## Required Section Fields

- `section_title`
- `slides`

Optional but recommended:

- `purpose`
- `local_order`

## Required Slide Fields

- `slide_type`
- `headline`
- `body`
- `source_urls`
- `image_urls`
- `notes`
- `needs_fact_check`
- `needs_source`

Recommended slide fields for piti/eval handoff:

- `slide_no`
- `local_order`
- `covers_key_beats`
- `fact_check_priority`
- `fact_check_kind`
- `required_before_storyline`
- `required_before_broadcast`
- `source_refs`

## Hygiene Metadata

`fact_check_priority` values:

- `high`
- `medium`
- `low`

`fact_check_kind` values:

- `factual_claim`
- `institution_quote_context`
- `education_research_claim`
- `korea_bridge_claim`
- `policy_effect_claim`
- `investment_risk_claim`
- `production_checklist`
- `rhetorical_caution`
- `source_context`

`required_before_storyline` means the storyline should not be generated before
the evidence is available. `required_before_broadcast` means the dry run may
exist, but a person must verify the claim before broadcast use.

`source_refs` are slide-specific:

```yaml
source_refs:
  - url: ...
    role: primary_article
    use: Royal Observatory 발언 맥락
    confidence: medium
    manual_check_required: true
```

Do not treat an attached source as completed fact-checking. `source_urls` and
`image_urls` must stay separate; the same URL must not appear in both.

## Key Beat Planning

API experiment outputs should include a planning layer before the slides:

```yaml
section_plan:
  - section_title: AI가 바로 답을 주는 시대
    purpose: AI 즉답이 주는 편리함을 도입부에 배치한다.
    required_key_beats:
      - AI 즉답이 주는 편리함
    planned_slide_count: 5
```

After the slides, the output should explicitly report coverage:

```yaml
key_beat_coverage:
  - key_beat: AI 즉답이 주는 편리함
    covered: true
    slide_refs: [3, 4]
    coverage_note: 도입부에서 AI 즉답의 편리함을 설명했다.
```

Every required key beat must be allocated in `section_plan` and verified in
`key_beat_coverage`. If evidence is thin, keep the beat in the story and mark
the related slide with `needs_source` or `needs_fact_check`; do not silently
drop the beat. `covered=true` must point to real slide numbers whose headline
or body contains the beat or one of its accepted phrase-level aliases.

Each required key beat must also be assigned to at least one slide-level
`covers_key_beats` entry. This field is the slide's commitment; the later
`key_beat_coverage` block is only the self-check. A slide with
`covers_key_beats` must include at least one anchor phrase for that beat in its
headline or body. Validator failures may include `missing_covers_key_beats` or
`covers_key_beat_without_anchor_phrase`.

For API experiments, `covers_key_beats` should use stable beat ids, not human
labels. Source roles such as `Korean_bridge`, `source_context`, `risk`, or
`institution_example` are invalid in `covers_key_beats`; put them in
`source_refs.role`, notes, or risk metadata instead.

Slides that use `covers_key_beats` should also include `key_beat_anchors_used`,
an object list with `key_beat_id` and `anchor_phrase`. The anchor phrase must
come from the provided anchor list and must appear verbatim in the slide
headline or first body line.

## Section Count Policy

Representative API experiments should target 3-4 sections. A 5-section output
is acceptable as an API-experiment warning when the structure is otherwise
valid, but it should not be treated as the production default.

Production anny should use 3-4 sections by default. A 5-section structure needs
explicit justification in the `section_plan`, such as a distinct counterpoint or
risk section that cannot be folded into the normal four-part arc.

## Editorial Rules

- Anny is evidence-bound. Do not invent facts, numbers, claims, or URLs that are
  not present in the input bundle or evidence pack.
- `source_urls` must come from provided candidate article URLs or evidence-pack
  URLs. Do not generate or guess new URLs.
- Slide body claims must match the attached `source_refs.use`. If the match is
  weak, keep `needs_source` or `needs_fact_check`.
- Leave `needs_fact_check` / `needs_source` visible when evidence is thin.
- Sensitive AI, education, policy, finance, medical, and political claims must
  avoid certainty without evidence.
- Counterpoint or risk discussion is required for AI/education/policy/finance
  topics.
- `korea_bridge` is a supporting connection, not the main proof.
- Rhetorical bridges do not need excessive source refs, but they must not become
  factual claims.
- `production_checklist` slides are internal production material. They may later
  move to appendix, notes, or a checklist instead of the main PPT body.
- `do_not_claim` and `avoid` are hard guardrails.

## Anny-to-Piti Screen Contract

Milestone 1.20 introduces a Piti-ready slide spec contract. The current adapter
can convert existing Anny storyline JSON into this shape, but the long-term goal
is for Anny to emit these fields directly so Piti can focus on layout instead of
rewriting meaning.

Recommended slide-level fields for Piti handoff:

- `screen_headline`: the exact headline intended to appear on the slide.
- `screen_body`: the exact visible body copy, normally 0-3 short lines.
- `speaker_notes_expanded`: the longer explanation, evidence context, caveats,
  and production notes.
- `overflow_notes`: body/explanation lines that should not be placed on screen.
- `proof_object`: the screen evidence object Piti should place.
- `editor_instruction`: blue/editor-facing production instruction, not broadcast
  copy.
- `risk_notes`: optional risk-specific production notes.

`proof_object` should include:

- `type`: `none | source_card | article_quote | chart | table | diagram | image | screenshot | logo | person_photo`
- `screen_position`: `left_half | right_half | center_large | full_width_chart | none`
- `source_name`
- `display_title`
- `quote_text`
- `quote_translation`
- `source_url`
- `image_url`
- `chart_title`
- `chart_source_label`
- `data_hint`
- `diagram_nodes`
- `diagram_edges`
- `manual_insert_required`
- `copyright_risk`

Screen-copy rules:

- `screen_headline` and `screen_body` are what the audience sees.
- Explanatory, cautionary, source, and fact-check language belongs in
  `speaker_notes_expanded` or `overflow_notes`.
- `screen_body` should be 0-3 lines. If a slide needs more explanation, split it
  or move the explanation to notes.
- Source URL attached does not imply `article_quote`.
- Use `article_quote` only when there is actual quote text, English/Korean quote
  rhythm, or a specific statement to show as a quote.
- Use `source_card` when the slide is source-backed but not quoting text.
- `source_card.display_title` must not repeat `screen_headline`.
- `diagram` should provide `diagram_nodes` and `diagram_edges`; do not leave Piti
  with only a generic `[도식]` instruction.
- `chart`/`table` should provide `chart_title`, `chart_source_label`, and a
  short `data_hint`; explanatory chart notes belong in notes.

The contract schema is `specs/piti_slide_spec_schema.json`. The temporary
adapter command is:

```text
luddite build-piti-slide-spec
luddite validate-piti-slide-spec
```

This is not a production Anny agent and does not authorize LLM/API calls.

## Policy / Finance Guardrails

- Do not write investment advice.
- Do not make buy/sell/return/price/stock-price predictions.
- Do not make a policy product or financial company sound promoted.
- Do not claim policy effects are proven unless verified by strong evidence.
- `policy_effect_claim` should normally be `high` or `medium` priority and
  `required_before_broadcast=true`.
- `investment_risk_claim` must avoid price prediction language and must include
  risk framing.

## Readiness

- `ready_for_prompt_design: true`
- `ready_for_manual_storyline: true`
- `ready_for_api_experiment_prep: true`
- `ready_for_api_experiment: true`
- `ready_for_production_agent: false`
- `ready_for_broadcast: false`

The manual dry runs and the AI knowledge-institution API experiments validate
the prompt/eval contract enough for controlled API experiments. Production anny
still needs cross-topic variability checks, stronger fact-check conservatism,
and failure handling before it can be wired into the product.

## API Experiment Prep

Milestone 1.8 adds API experiment scaffolding only. It does not call an LLM API.

Run input `mode` values:

- `manual`
- `dry_run`
- `api_experiment`
- `api_future`

Manifest `model_source` values:

- `manual_gpt_pro`
- `openai_api`
- `fixture`

Future API experiment outputs should use this directory convention:

```text
outputs/model_dry_runs/anny_api_experiments/<run_id>/
```

Expected files:

- `input_bundle.json`
- `evidence_pack.json`
- `prompt.md`
- `raw_model_output.txt`
- `parsed_storyline.json`
- `validation_report.md`
- `manifest.json`

`raw_model_output.txt` must be preserved for failed runs. Invalid JSON or schema
failure is recorded as failure; the initial policy does not auto-repair model
output. See `docs/product/anny_failure_modes.md` for the failure taxonomy and
repair policy.

## Local Run Contract

Milestone 1.7 adds a local runner scaffold rather than a production agent.

Input schema: `specs/anny_run_input_schema.json`

Manifest schema: `specs/anny_run_manifest_schema.json`

Command:

```text
luddite anny-run-storyline
make anny-run-storyline
```

The runner validates manually prepared storyline JSON, calls the existing
dry-run validator, and writes run input/manifest/report files. It never calls an
LLM API.

Reproducibility fields:

- `input_bundle_sha256`
- `evidence_pack_sha256`
- `output_storyline_sha256`
- `hygiene_sidecar_sha256`
- `prompt_file_sha256`
- `output_contract_version`
- `prompt_version`
- `validator_version`
- `schema_version`

Run registry:

```text
data/manifests/anny_runs/index.jsonl
```

The index records run id, case id, title, status, model source, input/output
paths, report path, schema/hygiene pass state, and
`ready_for_production_agent=false`.
