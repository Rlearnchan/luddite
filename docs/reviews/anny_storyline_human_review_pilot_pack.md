# Anny Human Review Pilot Pack

This pilot pack is for human review of compact Anny storyline samples. It is
not a production Anny release, not an API experiment, and not a broadcast-ready
script package.

## Review Samples

Read these compact samples first:

1. `outputs/samples/anny_storylines/compact/ai_knowledge_institution_manual_enriched.md`
2. `outputs/samples/anny_storylines/compact/productive_finance_manual_enriched.md`

Do not use this file as a product sample:

- `outputs/samples/anny_storylines/compact/productive_finance_api_v1.md`

That API output is for failure analysis only.

## Review Materials

- Guide: `docs/reviews/anny_storyline_sample_review_guide.md`
- Individual review form:
  `docs/reviews/anny_storyline_sample_review_template.md`
- Result storage template:
  `docs/reviews/results/anny_storyline_sample_review_YYYY-MM-DD.md`
- Summary template:
  `docs/reviews/anny_storyline_sample_review_summary_template.md`

## Pilot Instructions

1. Read the AI knowledge institution compact sample first.
2. Read the productive finance manual compact sample second.
3. Fill out one review result document per reviewer.
4. Treat `needs_source` and `needs_fact_check` as intentional review signals,
   not formatting noise.
5. Record whether the artifact feels more like a newsletter, storyline draft,
   or research memo.
6. After reviews are collected, summarize them with the summary template.

## Current Readiness

- ready_for_human_review_pilot: true
- ready_for_production_agent: false
- ready_for_broadcast: false

## Out Of Scope

This pilot does not include API re-runs, production Anny agent work, batch API
experiments, automatic web research, PPT generation, Slack, RSS scheduling,
syuka-ops integration, or Google Sheet automation.
