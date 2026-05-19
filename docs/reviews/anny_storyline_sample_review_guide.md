# Anny Storyline Sample Review Guide

This guide is for human review of the compact Anny storyline samples. These
samples are not production Anny output, not broadcast-ready scripts, and not
fact-check complete.

## Start Here

Read these first:

1. `outputs/samples/anny_storylines/compact/ai_knowledge_institution_manual_enriched.md`
2. `outputs/samples/anny_storylines/compact/productive_finance_manual_enriched.md`

Use this form while reviewing:

- `docs/reviews/anny_storyline_sample_review_template.md`

Pilot pack and result templates:

- `docs/reviews/anny_storyline_human_review_pilot_pack.md`
- `docs/reviews/results/anny_storyline_sample_review_YYYY-MM-DD.md`
- `docs/reviews/anny_storyline_sample_review_summary_template.md`

## What The Samples Are

- `manual_enriched` samples are GPT Pro/manual dry-run storyline examples with
  evidence packs attached.
- `api_experiment` samples are controlled API experiment outputs. They are useful
  for model behavior review, not product demo material.
- Productive finance API v1 still has validator failures and should be treated
  as failure analysis.

## Compact vs Audit

- `outputs/samples/anny_storylines/compact/` is for research-team reading.
- Root-level files under `outputs/samples/anny_storylines/` are audit samples
  for development, validation, source hygiene, and failure analysis.

Compact samples show:

- Global slide number
- Headline
- Body
- 1-2 source URLs
- `needs_source`
- `needs_fact_check`
- Short notes

Audit samples additionally show:

- Full `source_refs`
- Key beat metadata
- Fact-check kind and priority details
- Hygiene metadata

## How To Interpret Checks

- `needs_source=true` means the slide still needs a source before use.
- `needs_fact_check=true` means attached sources are not enough for broadcast.
- Source attached does not mean fact-check complete.
- `required_before_broadcast=true` means a human must verify it before the
  material is used in a broadcast script.

## What Feedback We Need

Focus on whether this helps the research workflow:

- Does the storyline flow feel natural?
- Do the section and slide headlines feel usable?
- Are source/check markers helpful or distracting?
- Would this reduce research time?
- Which slides are strongest?
- Which slides should be cut or rewritten?
- Should this be framed as a newsletter, storyline draft, or research memo?
- What should Anny produce next?

Save one completed result per reviewer under `docs/reviews/results/`, then use
the summary template to consolidate common signals.

## Current Recommendation

The AI knowledge institution manual enriched sample is the best first sample to
show. The productive finance manual enriched sample is useful for internal
researchers, especially to evaluate source, counterpoint, and checklist handling.

Do not show productive finance API v1 as a product example. It is for developer
review and failure analysis.
