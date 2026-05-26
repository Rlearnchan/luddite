# Jibi Reviewed Candidate Guard — 2026-05-27

Report-only guard for suppressing candidates that already received human review.

- allow_reviewed_candidates: false
- selected_count: 10
- suppressed_count: 2

## New Candidates

| title | story_fingerprint | history_status |
| --- | --- | --- |
| [제2025-37호] 생산 부문으로의 자금 흐름 전환과 성장 활력 | story_1ba23eaa67 | new |
| [제2025-36호] AI 전문인력 현황과 수급 불균형: 규모, 임금, 이동성 분석 | story_12220a440d | new |
| "서구 선진국 실질임금 감소 시작…인플레 압박 여파" | story_a6eeebaaa6 | new |
| 해외보험에 기댄 K우주산업…정부 "시장 키운다" | story_98df91e7c5 | new |
| [제2025-30호] AI 확산과 청년고용 위축: 연공편향(seniority-biased) 기술변화를 중심으로 | story_8a22f77af8 | new |
| 공공·민간 '쌍끌이'…시장에 비아파트 단기 신속 공급 신호 | story_b833a3ba60 | new |
| [영상] '스벅 사태' 일부 담당자, 휴대폰 제출 거부…"문구는 AI 참고" | story_6ba3cfc9e6 | new |
| 페라리, 첫 순수 전기차 '루체' 공개…가격 9.6억원 | story_2796a4579a | new |
| 日, 역대급 불볕더위 앞두고 산업현장 열사병 대책 '비상' | story_e8401d08bd | new |
| 'K뉴딜 아카데미' 참여청년 모집…10대 그룹들 운영계획 소개 | story_05227bed5c | new |

## Suppressed Reviewed Candidates

| title | previous_review_dates | reviewers | status | required_action | excerpt |
| --- | --- | --- | --- | --- | --- |
| 청년 노동시장 이탈 / 쉬었음 / 경제활동참가율 | 2026-05-25 | 형찬 | promoted_before | avoid_duplicate_review_unless_followup_news_changed | 자료는 조금 다르지만 청년 노동시장 주제, 특히 쉬었음 소재는 많이 다룬 바 있음. 최근 영상 제목으로는 "83~95년생의 삶을 추적해봤습니다.", "이제 근로소득으로는 부자가 될 수 없나" 정도가 있음. 즉, 좋... |
| [제2026-11호] 국내외 자산 토큰화 현황 및 향후 정책 과제 | 2026-05-25 | 형찬 | rejected_before | do_not_repost_without_new_hook_or_explicit_override | 이것도 재미가 없을 듯함. seed로 보기에는 약함. 조각투자를 교과서처럼 설명하면, "그래서 뭐" 반응이 나올 것임. |

## Reconsideration Rule

- Default: reviewed candidates are excluded from the next visible Jibi board.
- Override only with `JIBI_ALLOW_REVIEWED_CANDIDATES=1` after a new hook, new supporting links, or a clearly changed frame exists.
