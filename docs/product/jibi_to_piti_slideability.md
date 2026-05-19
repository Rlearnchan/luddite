# Jibi To Piti Slideability Notes

Status date: 2026-05-19

Milestone 1.20 keeps Jibi scoring unchanged, but it records a later product
need: good story seeds should be evaluated not only for news value, but also for
how naturally they can become editable slides.

## Why This Matters

The recent Piti renderer work showed that a topic can be narratively promising
yet visually weak. If Jibi selects candidates with no proof object, Piti has to
invent weak placeholders later. A stronger future pipeline should identify the
likely proof object at candidate time.

## Future Candidate Signals

Possible future Jibi fields:

- `slideability_score`
- `visualizability_score`
- `proof_object_type`
- `proof_object_confidence`
- `chartability`
- `quoteability`
- `screenshotability`
- `diagramability`

Possible `proof_object_type` values:

- `chart`
- `table`
- `source_quote`
- `source_card`
- `screenshot`
- `image`
- `map`
- `person_photo`
- `logo`
- `diagram`
- `none`

## Scoring Heuristics To Consider Later

- A candidate with clear numbers, rankings, time series, ratios, or market size
  usually has stronger chart/table potential.
- A candidate built around a vivid quote, official statement, or contested
  wording has quote/source-card potential.
- A candidate involving a product, place, person, institution, document,
  webpage, map, or imageable scene has screenshot/image potential.
- A candidate that explains a mechanism, tradeoff, process, or conflict can be
  diagrammable even without images.
- A candidate with only abstract claims and no concrete proof object should
  carry lower slideability unless the text itself is a strong calculation,
  question, or punchline.

## Non-goal For Now

This memo does not change Jibi scoring in Milestone 1.20. It only records the
future direction so the current Anny-to-Piti screen contract has a place to plug
in candidate-stage visual signals later.
