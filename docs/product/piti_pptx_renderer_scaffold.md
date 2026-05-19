# Piti PPTX Renderer Scaffold

Milestone 1.19 adds a local renderer that turns `piti_deck_plan` JSON into
editable `.pptx` skeletons.

This is not a production Piti agent and not a finished Syukaworld-style deck.
The goal is only to see how an Anny storyline and Piti deck plan unfold as
actual PowerPoint slides before investing in high-fidelity layout work.

## What It Does

- Loads deck plans from `data/candidates/piti_deck_plans/`.
- Creates editable 16:9 PowerPoint files under `outputs/pptx/`.
- Preserves section and slide order, except internal production checklist slides
  are moved to the end and labeled as internal checklist material.
- Renders headline, body, and visual placeholders as editable text boxes.
- Writes source URLs, image URLs, fact-check flags, edit notes, visual plan, and
  copyright risk into speaker notes.
- Produces a render report under `outputs/reports/`.

## What It Does Not Do

- It does not generate a broadcast-ready PPT.
- It does not implement a production Piti agent.
- It does not collect or insert images.
- It does not generate charts.
- It does not call an LLM or any external API.
- It does not upload to Google Slides or Drive.

## Source And Notes Policy

Speaker notes are the most important contract in this scaffold. Every slide
should preserve:

- `source_urls`
- `image_urls`
- `speaker_notes`
- `needs_source`
- `needs_fact_check`
- `required_before_broadcast`
- `edit_notes`
- `visual_plan`
- copyright risk notes

Source attached still does not mean fact-check complete. Slides marked
`needs_fact_check=true` require human review before broadcast.

## Layouts

The renderer supports the current deck-plan layout types:

- `title`
- `section_title`
- `big_headline`
- `headline_body`
- `quote`
- `question`
- `comparison`
- `timeline`
- `chart_placeholder`
- `image_placeholder`
- `checklist`
- `closing_question`
- `appendix_checklist`

These are simple skeleton layouts. They are intentionally editable rather than
visually final.

## Future Steps

1. Style profile extraction from reference Syukaworld decks.
2. Layout tuning for stronger section rhythm and visual hierarchy.
3. Image/capture workflow with copyright checks.
4. Chart generation for data-heavy slides.
5. Google Slides/Drive sharing.
6. Production Piti agent design after renderer and review loops stabilize.

## Readiness

- `ready_for_ppt_generation`: true, scaffold only
- `ready_for_production_piti_agent`: false
- `ready_for_broadcast`: false
