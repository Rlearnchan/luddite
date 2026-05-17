# Codex Prompt: v0.9.4 Final Digest Polish before Google Sheet Append

현재 Luddite는 v0.9.3까지 반영되었다.

완료된 것:
- v0.9.3 리서치팩 문서 반영
- source/RSS 전략 문서화 및 config/sources.yaml 보강
- syuka-ops bridge는 read-only/search proxy 설계만 반영
- Google Sheet append는 기존 `주제 찾기`가 아니라 `jibi 후보` staging sheet 기준으로 정리
- jibi Daily Digest 품질 보정:
  - reject item은 Top Candidates에서 제외
  - 국내 대통령/정당 직접 평가만 hard reject
  - 해외 정치 구조 이슈는 editorial_review/gather_more_evidence 가능
  - send_to_anny는 evidence 충분성 기준으로 강화
  - why_interesting / possible_expansions 구체화
  - AI 미사용 라벨은 hard reject하지 않음
  - Sheet preview에 digest_date, collected_at, last_seen_at, duplicate_key, source_url_canonical 유지
- make lint, make test, make jibi-digest 통과

GPT Pro가 최신 산출물을 검토한 결과:
- 0.9.3은 통과로 봐도 된다.
- 다만 1.0 Google Sheet append 전에 아주 작은 0.9.4 polish를 권장한다.

검토 대상:
- outputs/daily_digest/2026-05-17.md
- outputs/daily_digest/2026-05-17_sheet_append_preview.csv
- data/candidates/jibi_scored_candidates.jsonl
- examples/articles/sample_articles.jsonl
- config/sources.yaml
- docs/status/current_product_direction.md

작업 1. Digest summary 문구 수정

현재 상단 요약:

- 바로 볼 만한 후보: 0개
- 자료 보강 필요: 5개
- 사람 검토 필요: 2개
- 킵 후보: 1개
- 제외/거절: 2개

문제:
`바로 볼 만한 후보`라는 표현은 오해를 부른다.
여기서 0개는 send_to_anny가 0개라는 뜻이지만, 실제 Top Candidates에는 볼 만한 후보가 8개 있다.

수정 권장:

- Top Candidates: 8개
- 즉시 스토리라인 후보: 0개
- 자료 보강 후보: 5개
- 사람 검토 후보: 2개
- 킵 후보: 1개
- 제외/거절: 2개

또는 `바로 볼 만한 후보`를 `즉시 anny 후보` / `즉시 스토리라인 후보`로 바꾼다.

작업 2. 영국 양당/개혁당 grade 보정

현재:
`영국 양당 지지율 동반 하락과 개혁당 부상`
- D · editorial_review · high risk · 25.6

이 후보는 reject는 아니지만 점수가 너무 낮다.

이 유형은 해외 정치 구조 이슈다.
단순 정당 평가가 아니라 아래로 확장 가능하다.

- 양당제 균열
- 지역 격차
- 포퓰리즘
- 경제 불만
- 채권시장/정책 리스크
- 노동자 계층 이동

권장:
- C 또는 B
- editorial_review 유지 가능
- risk는 high 또는 medium 가능

최소한 D는 피한다.

작업 3. why_interesting visible text에서 generic clause 줄이기

현재 일부 후보에 generic clause가 반복된다.

예:
- 시장/규제/산업 구조로 확장 가능
- 숫자나 통계로 증명할 여지가 있음

이 문구는 내부 scoring/debug reason에는 남겨도 좋지만,
digest에 보이는 `왜 보나`에는 후보별 구체 문장만 우선 표시한다.

권장:
- `why_interesting` = 사람에게 보이는 구체 문장
- `debug_reason` 또는 `score_reason` = generic scoring reason

예:
드론 비용 역전:
“값싼 드론 하나를 막기 위해 수백만 달러짜리 미사일을 태우는 구조라, 전쟁이 무기 성능보다 비용 교환비 싸움으로 바뀌는 장면을 보여준다.”

반바지/폭염:
“5월 폭염이 단순 날씨 뉴스가 아니라 회사 복장 규정, 전력 수요, 에어컨 비용, 쿨비즈 문화로 이어질 수 있다.”

작업 4. Source registry 상태 명시

현재 config/sources.yaml은 좋은 방향이다.
다만 rss_candidate에는 아직 실제 feed URL이 없다.

docs/status/current_product_direction.md 또는 docs/integrations/rss_source_strategy.md에 아래를 명확히 남겨라.

- rss_candidate는 아직 endpoint가 검증되지 않은 후보 상태다.
- RSS collector 구현 전 endpoint discovery / fetch test / parse test가 필요하다.
- fetch test를 통과한 뒤 rss_verified로 승격한다.
- subscription_manual은 자동 fetch하지 않는다.

작업 5. Sheet preview 정책 유지

현재 Sheet preview는 `jibi 후보` staging sheet 기준으로 좋다.
아래 컬럼을 유지한다.

- digest_date
- collected_at
- last_seen_at
- jibi_id
- duplicate_key
- source_url_canonical
- rank
- status
- 주제명
- 링크
- 출처
- source_type
- jibi_grade
- total_score
- recommended_action
- risk_level
- risk_flags
- why_interesting
- possible_expansions
- evidence_needed
- 중복후보
- reviewer
- review_result
- promoted_to_topic_finding
- notes

Rejected item은 기본 sheet preview에 넣지 않아도 된다.
필요하면 나중에 별도 rejected preview를 만들 수 있다.

작업 6. 아직 하지 말 것

이번 0.9.4에서는 아래를 하지 않는다.

- 실제 LLM API 호출
- RSS collector 구현
- Google Sheet API append 실제 구현
- Slack bot 구현
- syuka-ops 실제 DB 연동
- anny/piti production agent 구현
- full PPT generator
- image auto collection

완료 기준:
1. make lint 통과
2. make test 통과
3. make jibi-digest 실행 성공
4. digest summary 문구가 오해 없게 수정됨
5. 영국 양당/개혁당 후보가 D에서 C/B 계열로 보정됨
6. visible why_interesting의 generic 반복이 줄어듦
7. source registry 상태가 문서에 명확히 남음
8. Sheet preview 컬럼은 `jibi 후보` staging sheet 기준을 유지

그 다음 milestone:
Milestone 1.0 — Google Sheet `jibi 후보` append 실제 구현
