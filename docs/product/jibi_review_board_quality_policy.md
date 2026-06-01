# Jibi Review Board Quality Policy

This policy defines how Jibi should describe review-board readiness before any
operator replaces the live Google Sheet.

## Candidate Roles

`main_seed` is the editorial role already assigned to a selected row for Anny handoff.

`main_seed_candidate` is a report-only signal. It means the item may be strong
enough to anchor a story, but it can still require source checks, copy rewrite, or
past-video angle review.

`ready_seed_candidate` is stricter. It should only be true when the item is strong
enough to put near the top of today's board without hidden support gaps. Conditional
seeds, market-wire items without second-source support, generic visible copy, and
weak Syuka matches should not be ready.

## Support Status

`support_missing` should only block a main seed when the missing requirement is
critical. Optional support gaps are still useful for producers, but they should not
turn a strong candidate into a false negative.

Critical support includes requirements such as:

- `past_video_new_angle` for concrete past-Syuka overlap
- `policy_or_stat` when a story depends on an institutional claim
- `parallel_case` when a single example cannot carry the frame alone

## Syuka Similarity

Syuka similarity is diagnostic, not a blanket duplicate penalty.

`concrete_overlap` means a concrete entity, policy, mechanism, or past episode
overlaps with prior Syuka coverage. It can require a new angle before main-seed use.

`broad_adjacent` means the candidate shares a broad topic area, such as electricity
prices, heatwaves, cooling, AI adoption, or delivery fees. This should not block a
main seed by itself, but it also should not be counted as a positive readiness signal.

`weak_adjacent` means the match is based only on low-value shared terms such as
`line`, `오일`, `세종은`, `지금`, `stop`, or similarly weak tokens. Markdown reports
hide these terms and mark the match for human checking.

`false_positive` means the similarity match is probably not useful for editorial
deduplication. It should not create critical support missing.

## Generic Visible Copy

Generic visible copy is dangerous because it hides the fact that Jibi has not
actually narrowed the story. Examples include:

- `해외 후보, 한 가지 질문으로 더 좁혀볼 소재`
- `원문 하나만으로는 아직 결론을 내리기 이릅니다`
- `이 후보를 단독 주제로 만들려면`
- `추가 독립 출처 1개 이상`

Generic final visible copy should set `generic_visible_copy_warning=true`, should
not be `ready_seed_candidate`, and should appear in the quality floor exclusion
preview.

## Quality Floor

The quality floor is report-only until operators explicitly enable it. It should
show which rows would be hidden if a variable 6-10 row board were active.

When `JIBI_USE_QUALITY_FLOOR=1` or `--use-quality-floor` is set, Jibi still keeps
the live bundle review CSV at the requested row count. It only marks
`quality_floor_preview_only=true`, `would_hide_if_quality_floor_active`, and
quality-floor hidden reasons in metadata/reports. Actual row-count reduction is
deferred until article-body evidence and LLM judge reports prove that the row is
not merely weak from missing context. The operator preview remains available at
`outputs/reports/jibi_quality_floor_preview_YYYY-MM-DD.md`.

Rows may be excluded by the quality floor for:

- `generic_visible_copy_warning`
- `critical_support_missing`
- `selection_lesson_role=suppress`
- `editorial_role=evidence_low`
- `board_score<35`
- `ready_status=not_seed`
- `weak_adjacent_only_with_generic_copy`

Before the quality floor changes visible row count, Jibi should run multiple
report-only replays and show stable improvements across several dates.

## Operating Gate

Google Sheet replace remains forbidden unless an operator explicitly approves it
after reviewing:

- selection calibration report
- board score report
- Anny handoff
- bundle review metadata
- quality replay report across recent dates
