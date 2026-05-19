# Piti Formatting Checklist

Milestone 1.19.5 defines explicit Syukaworld-style screen rules that override
raw style-profile frequency counts. The extractor can tell us what appeared
often, but the renderer must still decide what belongs on screen and what
belongs in speaker notes.

## Screen Rules v0.1

- Headline: 28pt, red `#FF0000`, top-left by default, one line preferred and
  two lines at most. Ordinary content headlines are not bold by default.
- Content slide headline position: use the reference-style top-left band by
  default. Avoid centered headline layouts except for title/section slides.
- Normal Korean body: black, 28pt baseline. Do not make ordinary Korean body
  red by default.
- Body length: keep screen body to roughly 2-3 lines. Four or more lines should
  raise a split/edit warning or move overflow into speaker notes.
- Body line spacing: use 1.5 spacing for screen body text boxes. Do not apply
  this rule to headlines, title slides, section titles, chart/table titles,
  chart/table data labels, chart/table source labels, or speaker notes.
- Body vertical alignment: screen body boxes should be vertically centered
  inside their content area rather than hard top-anchored.
- Quote bilingual mode: use only when English source text and Korean
  translation/interpretation are interleaved.
- Quote bilingual text: English line black 28pt, Korean translation line red
  28pt, with 1.5 body line spacing unless a later quote-specific exception is
  needed.
- Section title: large title treatment is allowed, but do not force red unless
  a future explicit section-title rule says so.
- Chart/table title: black 28pt, bold, underline.
- Chart/table body and data labels: black/dark gray 18pt, bold.
- Chart/table source: black 20pt, underline, parenthesized, near lower right or
  lower center-right.
- Chart/table area: make the proof object large; numbers should be directly
  visible as labels when real chart generation is added later.
- Image-heavy slide: prefer image or screenshot area on the left half, with
  interpretation text on the right half.
- Manual visual placeholder: hide from the actual screen by default. Preserve
  the visual plan in speaker notes.
- Visible placeholders: show only compact labels for chart, diagram,
  screenshot, image, or AI-image candidates.
- Footer/debug labels: do not show `draft skeleton`, `needs_fact_check`, or
  slide numbers on styled screens. Keep them in notes and reports.
- Speaker notes: preserve long explanation, source URLs, image URLs,
  fact-check flags, visual plan, copyright risk, and overflow body lines.

## Screen Role Styling v0.1

- `actual_headline`: red `#FF0000`, 28pt, non-bold by default.
- `actual_body`: black, 28pt/adaptive, 1.5 line spacing, vertically centered.
- `quote_english`: black, 28pt.
- `quote_korean_translation`: red `#FF0000`, 28pt.
- `chart_title`: black, 28pt, bold, underline.
- `chart_data_label`: black or dark gray, 18pt, bold.
- `chart_source`: black, 20pt, underline, parenthesized.
- `proof_object_skeleton`: neutral gray/black proof area. It is a screen object,
  not a body paragraph.
- `editor_instruction`: blue `#0070C0`, 18-20pt, shown only when a screen note is
  useful. Prefer speaker notes for detailed editor instructions.
- `debug_or_internal_note`: blue `#0070C0` or hidden. Raw debug labels should not
  appear as ordinary screen copy.

Editor-facing phrases include `[수동 삽입]`, `[이미지 후보]`, `[차트 후보]`,
`[도식 후보]`, `[기사 캡처]`, `needs_fact_check`, `needs_source`,
`before_broadcast`, `split_recommended`, `edit_notes`, `copyright_risk`,
`manual_check_required`, and draft/scaffold/debug labels. If any of these appear
on screen, they must be blue and visually subordinate to the actual slide copy.

## Proof Object Rules v0.1

- A styled slide should usually have a proof object when the storyline points
  to an image, chart, table, article quote, screenshot, diagram, logo, map,
  person photo, or generated-image candidate.
- `visual_plan` is first mapped into a `proof_object`; the renderer then
  reserves a screen area for that proof object and keeps the detailed
  description in speaker notes.
- Proof object labels on screen stay short: `[이미지]`, `[차트]`, `[표]`,
  `[기사 캡처]`, `[도식]`, or similar. Long placeholder descriptions belong in
  notes.
- Image, logo, person-photo, screenshot, generated-image, article-quote, and
  diagram proof objects prefer a left-half proof area with interpretation text
  on the right.
- Chart and table proof objects use a large center chart/table area. The body
  text should not compete with the chart; detailed explanation moves to notes.
- Article quote slides may show a short source name or host on screen, but the
  source URL remains in speaker notes.
- Text-only slides remain allowed, but they should be deliberate. If a slide
  has no proof object, screen text should be especially short and use 1.5 line
  spacing.
- Proof object and text regions must not overlap. Styled drafts should fail the
  render hygiene check if an overlap is detected.

## Reference Layout Templates v0

- `chart_table_reference`: use for chart/table proof objects, numeric ranking,
  ratios, amounts, or data-heavy slides. The chart/table area should dominate
  the screen. Use a red story headline, black underlined chart title, editable
  axis/bar/data-label skeleton, and underlined source label.
- `image_left_quote_right`: use for image, logo, person-photo, screenshot,
  diagram, or generated-image proof objects. Reserve the left half for the
  proof object and keep the interpretation text on the right.
- `text_only_calculation`: use only when the text itself is the scene, such as
  a calculation, rhetorical turn, closing question, or tight logic step. Keep
  the body to 2-3 visible lines.
- `source_card_or_article_quote`: use for source-backed claims without a real
  screenshot yet. Render a compact source card on the left with source name and
  short title, keep URLs in notes, and place the interpretation text on the
  right.
- Source-backed manual slides should not remain text-only by default. Prefer a
  source card unless the slide is title/section/checklist/internal material.

## Surface Copy And Proof Object Cleanup v0.1

- `article_quote` is only for actual quotation slides: English/Korean quote
  pairs, explicit quote text, or a specific statement being shown as a quote.
- `source_card` is for source-backed claims where there is no quote on screen.
  Do not turn every source URL into an article quote.
- Source cards show source identity, a short source title, and optional source
  type. They must not repeat the slide headline or show long URLs on screen.
- Full URLs remain in speaker notes. On-screen source labels should be source
  names such as `BBC`, `Microsoft Research`, `금융위원회`, or `BIS`.
- Screen body copy should be compressed for broadcast rhythm. Explanatory,
  cautionary, source, or fact-check language belongs in speaker notes.
- Proof-object slides should usually show at most two body lines. Text-only
  slides may use up to three lines, with overflow moved to notes.
- Diagram placeholders must show a minimal two-box/arrow skeleton rather than
  only a `[도식]` label.
- Chart/table slides should not leak explanatory body copy into the chart area.
  The screen keeps chart title, chart skeleton/data labels, and source label;
  explanation moves to notes.
- Editor-facing labels such as `[인용]`, `[출처]`, `[도식]`, and `[차트]` should be
  small, blue, and subordinate to the proof object itself.

## Non-goals

- This is not a production Piti agent.
- This is not a final Syukaworld design clone.
- This does not collect or insert images automatically.
- This does not generate charts yet.
- This does not call an LLM or any API.
