# Piti Formatting Checklist

Milestone 1.19.5 defines explicit Syukaworld-style screen rules that override
raw style-profile frequency counts. The extractor can tell us what appeared
often, but the renderer must still decide what belongs on screen and what
belongs in speaker notes.

## Screen Rules v0.1

- Headline: 28pt, red `#FF0000`, top-left by default, one line preferred and
  two lines at most.
- Content slide headline position: use the reference-style top-left band by
  default. Avoid centered headline layouts except for title/section slides.
- Normal Korean body: black, 28pt baseline. Do not make ordinary Korean body
  red by default.
- Body length: keep screen body to roughly 2-3 lines. Four or more lines should
  raise a split/edit warning or move overflow into speaker notes.
- Quote bilingual mode: use only when English source text and Korean
  translation/interpretation are interleaved.
- Quote bilingual text: English line black 28pt, Korean translation line red
  28pt.
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

## Non-goals

- This is not a production Piti agent.
- This is not a final Syukaworld design clone.
- This does not collect or insert images automatically.
- This does not generate charts yet.
- This does not call an LLM or any API.
