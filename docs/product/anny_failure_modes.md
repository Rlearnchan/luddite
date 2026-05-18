# Anny API Experiment Failure Modes

Status date: 2026-05-18

Milestone 1.8 prepares failure handling for future API experiment outputs. It
does not implement an API caller and does not create a production anny agent.

## API Experiment Directory

Future API experiment runs should write one directory per run:

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

`raw_model_output.txt` must be retained even when JSON parsing fails. It is the
audit trail for diagnosing invalid JSON, missing fields, hallucinated sources,
or guardrail violations.

## Failure Taxonomy

- `invalid_json`: model output could not be parsed as JSON.
- `schema_error`: parsed JSON fails `specs/anny_storyline_schema.json`.
- `missing_required_fields`: required top-level, section, or slide fields are absent.
- `source_hallucination`: `source_urls` contains URLs not present in the input bundle or evidence pack.
- `unsupported_claim`: slide claim is not supported by attached `source_refs` or must stay marked for checking.
- `do_not_claim_violation`: output violates bundle `do_not_claim` or `avoid` guardrails.
- `source_image_overlap`: the same URL appears in both `source_urls` and `image_urls`.
- `counterpoint_missing`: sensitive topic omits counterpoint or risk discussion.
- `needs_fact_check_removed_too_aggressively`: model removes caution markers despite thin evidence or risky claims.
- `production_checklist_misused`: internal checklist material is treated as normal broadcast claim.
- `investment_advice_violation`: finance output reads like buy/sell/return/price prediction advice.
- `policy_promotion_violation`: policy/finance output sounds like product or government-policy promotion.
- `korea_bridge_overreach`: Korean bridge is used as the main proof or overgeneralized.
- `key_beat_drift`: required storyline beats are missing or replaced by a different story.
- `source_ref_role_mismatch`: `source_refs.role` or `source_refs.use` does not match the slide claim.
- `required_before_broadcast_missing`: sensitive claims lack broadcast-before verification flags.

## Evidence-Bound Rule

Anny must stay inside the input bundle and evidence pack:

- Do not invent facts, numbers, claims, or URLs.
- Use `source_urls` only from candidate article URLs or evidence-pack URLs.
- Do not generate, guess, or autocomplete new source URLs.
- Slide body claims must match the attached `source_refs.use`.
- If the evidence is thin, keep `needs_source` or `needs_fact_check`.

## Repair Policy

Initial policy:

- Invalid JSON or schema failure is recorded as failed.
- No automatic repair is applied.
- Save raw output, parsed output attempt if available, and validation report.

Allowed later, after a separate design pass:

- Minor JSON syntax repair may be considered if it does not change factual content.

Forbidden:

- Rewriting model factual claims or slide body text automatically.
- Adding or substituting sources that were not in the input bundle or evidence pack.
- Removing `needs_fact_check` automatically.
- Converting production checklist material into broadcast claims.

## First API Experiment Candidate

The first future API experiment should use the lower-risk AI/education case:

- `case_id`: `anny_api_experiment_ai_knowledge_institution_v1`
- input bundle: `AI 즉답 시대의 지식기관 역할`
- evidence pack: `AI 즉답 시대의 지식기관 역할`
- length mode: `standard_representative_outline`
- target slides: 20-30 representative slides

`생산적 금융과 정책자금 전환` remains the second API experiment candidate
because policy, finance, and investment-risk guardrails need a more conservative
first comparison.

## Readiness

- `ready_for_api_experiment_prep: true`
- `ready_for_api_experiment: false`
- `ready_for_production_agent: false`
- `ready_for_broadcast: false`
