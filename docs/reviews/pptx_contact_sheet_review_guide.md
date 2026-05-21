# PPTX Contact Sheet Manual Review Guide

This guide is for human review of `luddite render-pptx-contact-sheet` outputs.
It is not an automated style judge, OCR pass, or broadcast approval.

## Review Status Values

Use these values in the per-slide contact sheet report:

```text
unchecked
ok
review
fail
```

Recommended meaning:

- `unchecked`: nobody has looked at this slide thumbnail yet.
- `ok`: the slide can stay as-is for the current draft review stage.
- `review`: the slide needs human discussion or a targeted edit request.
- `fail`: the slide is not acceptable even as a draft review surface.

## Slide-Level Checklist

For each slide thumbnail, check these fields:

```text
readability_status
layout_status
broadcast_fit_status
style_fit_status
readability_note
layout_note
broadcast_note
style_note
fix_request
```

Keep notes short and concrete. The goal is to make the next edit obvious.

## Readability

Check:

- Is there too much text on one slide?
- Is the red headline readable at thumbnail size?
- Is the body mostly one or two short lines?
- Are long explanations pushed to notes instead of the screen?
- Are diagram box labels short enough to fit?
- Are chart/table labels legible without reading a paragraph?

Set `readability_status=review` when the slide needs a copy trim or a clearer
headline. Use `fail` when the slide cannot be understood at thumbnail size.

## Layout

Check:

- Does the slide have one clear visual focus?
- Are text blocks and proof objects separated cleanly?
- Are diagram nodes aligned and readable?
- Are chart/table slides free of explanatory paragraph clutter?
- Are source cards not just repeating the headline?
- Is there enough breathing room around the main object?

Set `layout_status=review` when the structure is understandable but cluttered.
Use `fail` when the thumbnail looks broken, overlapping, or incoherent.

## Broadcast Fit

Check:

- Can the presenter open their mouth from this slide alone?
- Does the slide support a spoken beat rather than replace the script?
- Is the slide visual enough for a viewer who only glances at it?
- Does the slide avoid exposing raw URLs on screen?
- Are source/fact-check caveats still preserved where needed?
- Does the slide make clear why this beat exists in the story?

Set `broadcast_fit_status=review` when the slide has useful material but no
clear spoken beat. Use `fail` when the slide would confuse the audience.

## Style Fit

Check:

- Is the slide close to a "picture half / talk half" rhythm?
- Does the visual proof object carry the slide rather than decorate it?
- Is the screen copy direct, punchy, and broadcast-facing?
- Does the slide avoid generic placeholder diagrams?
- Does it feel like a working editorial draft rather than a generic template?

Set `style_fit_status=review` when the slide is serviceable but not yet
show-like. Use `fail` for template-like or visually empty slides.

## Common Fix Requests

Examples:

```text
Trim body to one line.
Replace generic diagram nodes with actor -> mechanism -> result labels.
Move explanatory sentence to speaker notes.
Use an institution-specific source card title.
Remove visible URL from screen copy.
Split this slide into visual proof + spoken explanation.
Add editor instruction for manual insert.
```

## Review Boundary

Do not use this checklist to declare broadcast readiness. This is a draft QA
surface. Production/broadcast readiness remains false until source review,
final deck QA, and human handoff workflow are defined.
