# Jibi Review Board Format Contract

This document locks the current reviewer-facing `Jibi` Google Sheet format.
Treat changes here as product changes, not incidental rendering tweaks.

## Sheet Shape

Use a single tab named `Jibi`.

Rows 1-4 contain the Jibi greeting and daily summary. Row 5 is blank. The table
header starts below the intro, and code must locate the header row instead of
assuming row 1.

Visible columns are fixed in this order:

```text
일시
제목
점수
메인 링크
서브 링크
설명
참고
리뷰-성원
리뷰-동찬
리뷰-형찬
ID
```

## Writing Style

- `제목` is always Korean, including translated English-source stories.
- `제목` should read as a reviewer-facing question or explanatory story frame.
- `점수` uses the compact format `B · 68점`.
- `설명` is prose, not machine labels. It should explain:
  - why this item was selected,
  - what story it could become,
  - what still needs evidence or a sharper frame.
- `설명` must not include internal labels such as `merged_seed`, `evidence_only`,
  `story_bundle`, or `generic_why`.
- `설명` must not include syuka-ops similar video metadata.
- `참고` is for auxiliary context only. Put syuka-ops similar video title/date,
  view count, like count, and overlap note here.
- `서브 링크` stays short. Use it for bundled supporting/evidence links only.

## syuka-ops Reference Format

When syuka-ops finds a useful adjacent or duplicate past-video match, write it in
`참고` like this:

```text
관련 과거 영상: 유럽이 40°C 폭염을 에어컨 없이 버텨야하는 이유 (2025-07-10, 조회 34.1만, 좋아요 3,523) · 배경/인접 주제
```

If the match is weak or not useful for reviewers, leave `참고` blank.
