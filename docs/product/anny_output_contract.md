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
- `ready_for_api_experiment: false`
- `ready_for_production_agent: false`
- `ready_for_broadcast: false`

The two manual dry runs validate the prompt/eval contract, but production anny
still needs evidence enrichment, output variability checks, and failure handling.

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
