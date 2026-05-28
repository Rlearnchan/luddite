# Jibi -> Anny Handoff Contract v0

## Purpose

`jibi_anny_seed_v0` is a report-only handoff contract from Jibi review-board selection to Anny story planning.

It is designed to preserve Jibi's existing visible Google Sheet workflow while giving Anny a safer structured input surface.

## Non-goals

- This is not production LLM selection.
- This does not change visible Google Sheet columns.
- This does not make Anny output broadcast-ready by itself.
- This does not override source/fact-check guardrails.

## Payload shape

Top-level fields:

- `handoff_version`
- `run_date`
- `items`

Each item should include:

- `jibi_id`
- `story_bundle_id`
- `story_fingerprint`
- `title`
- `source`
- `url`
- `source_role`
- `total_score`
- `board_score`
- `board_score_reasons`
- `topic_families`
- `primary_topic_family`
- `editorial_role`
- `editorial_role_confidence`
- `why_not_main_seed`
- `angle_options`
- `required_evidence`
- `past_video_context`
- `reviewer_objections`
- `review_role_constraints`
- `review_positive_signals`

## Semantics

### `editorial_role`

Allowed values:

- `main_seed`
- `sub_block`
- `hook_only`
- `evidence`

`main_seed` must be conservative. A candidate should not become `main_seed` merely because it was previously classified as `standalone_seed`.

Main seed requires:

- sufficient board score
- `selection_bucket=primary_fit`
- no Syuka duplicate risk
- no rejected/promoted/reviewed history risk

### `reviewer_objections`

Negative-only reviewer or review-derived warnings.

Examples:

- `adjustment:sports_primary_downrank`
- `adjustment:ai_grand_discourse_downrank`
- `adjustment:past_topic_overlap_downrank`
- `adjustment:needs_new_angle`
- `failure:too_familiar`
- `failure:weak_audience_bridge`

Do not put positive or role-only signals here.

### `review_role_constraints`

Role constraints inferred from review feedback.

Examples:

- `hook_only`
- `sub_block`

These are not objections. They tell Anny how to use the item.

### `review_positive_signals`

Positive signals from reviewer feedback.

Examples:

- `specific_case_needed`
- strong hook potential
- useful concrete example

These should remain separate from objections.

### `angle_options`

Rule-based Story Angle / Angle Lab suggestions.

These are planning hints, not final story decisions.

### `required_evidence`

Evidence or source needs that Anny should preserve.

Anny must not invent missing evidence.

### `past_video_context`

Syuka past-video context.

Possible `match_type` values:

- `none`
- `same_story`
- `adjacent_theme`
- `false_positive`

This field is a review/planning signal, not an automatic reject/approve decision.

## Compatibility

The handoff contract is additive.

It should not:

- change visible Google Sheet columns
- change default selection behavior when `use_board_score=False`
- mutate board score when `use_topic_diversity=False`
- call production LLM/API

