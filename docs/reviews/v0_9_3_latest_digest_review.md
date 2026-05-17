# Luddite v0.9.3 Latest Digest Review

검토일: 2026-05-17  
대상 zip: `luddite_v0_9_3_latest_review_pack.zip`

## 결론

v0.9.3 산출물은 **1.0 Google Sheet `jibi 후보` append로 넘어가기 전 단계로 거의 충분**하다.

잘 된 점:

- reject item이 Top Candidates에서 빠지고 `Excluded / Rejected`로 분리됨
- 국내 대통령/정당 직접 평가 샘플은 reject 유지
- F88, AI 미사용 라벨, 코카인 하마 등 action이 이전보다 보수적이고 자연스러워짐
- `possible_expansions`가 비어 있지 않음
- Sheet preview가 `jibi 후보` staging sheet 기준 컬럼으로 정리됨
- duplicate 방지를 위한 `duplicate_key`, `source_url_canonical`, `last_seen_at` 등이 들어감
- source registry가 문서/런타임 registry로 쓸 수 있는 수준까지 확장됨

남은 보정 포인트:

1. `오늘의 추천` 문구가 약간 오해를 부른다.
2. 해외 정치 구조 이슈인 영국 양당/개혁당 후보가 아직 너무 낮게 평가된다.
3. `why_interesting`은 좋아졌지만 일부 generic clause가 뒤에 반복된다.
4. source registry는 아직 feed URL이 없으므로 RSS collector 전 endpoint 검증 단계가 필요하다.
5. Sheet preview는 현재 Top Candidates만 들어가는데, rejected item을 별도 rejected preview로 남길지 정책 결정이 필요하다.

## 1. Daily Digest 평가

현재 digest 상단 요약:

```text
- 바로 볼 만한 후보: 0개
- 자료 보강 필요: 5개
- 사람 검토 필요: 2개
- 킵 후보: 1개
- 제외/거절: 2개
```

문제는 `바로 볼 만한 후보`라는 표현이다. 여기서 0개는 `send_to_anny`가 0개라는 뜻으로 보이지만, 사용자가 기대하는 “볼 만한 후보”는 클릭해볼 만한 후보 전체다. 실제 Top Candidates에는 볼 만한 후보가 8개 있다.

권장 표현:

```text
- 즉시 스토리라인 후보: 0개
- 자료 보강 후보: 5개
- 사람 검토 후보: 2개
- 킵 후보: 1개
- 제외/거절: 2개
```

또는:

```text
오늘의 후보 요약
- Top Candidates: 8개
- 즉시 anny 후보: 0개
- 자료 보강: 5개
- 사람 검토: 2개
- 킵: 1개
- 제외/거절: 2개
```

## 2. Top Candidates 순위

현재 Top Candidates:

```text
1. 5월 폭염에 회사 반바지 허용 논쟁 재점화
2. 300달러 드론을 수백만 달러 미사일로 막는 비용 역전
3. 전력 수요 급증에 변압기 대기 기간 길어진다
4. AI 미사용 라벨을 붙이는 브랜드들
5. 베트남 전당포 F88, 메인 증시 이전 상장 추진
6. 콜롬비아 마약왕의 하마, 살처분 대신 인도행?
7. 미국인이 가장 좋아하는 공룡은 왜 늘 티라노일까
8. 영국 양당 지지율 동반 하락과 개혁당 부상
```

전반적으로 납득된다. 특히 반바지/폭염, 드론 비용 역전, 전력/변압기, F88, 코카인 하마는 모두 슈카월드식 확장 가능성이 있다.

다만 개인적으로는 `드론 비용 역전`이 1위, `반바지/폭염`이 2위여도 자연스럽다. 현재는 생활형 후보가 score 63.6으로 가장 높은데, 실제 방송 확장력은 드론 비용 역전이 더 강할 수 있다. 다만 sample input 기반 rule score이므로 blocking issue는 아니다.

## 3. Action / Grade 검토

### 적절한 것

- 반바지/폭염: `B · gather_more_evidence · low risk`
- 드론 비용 역전: `B · gather_more_evidence · low risk`
- 전력/변압기: `B · gather_more_evidence · low risk`
- AI 미사용 라벨: `C · gather_more_evidence · low risk`
- F88: `C · gather_more_evidence · medium risk`
- 코카인 하마: `C · editorial_review · high risk`
- 공룡/T-Rex: `C · keep_for_later · low risk`
- 대통령 발언/증시 급등락: `D · reject · high risk`
- 의료 스타트업/레이저 치료기: `D · reject · high risk`

대부분 괜찮다.

### 보정 권장: 영국 양당/개혁당

현재:

```text
D · editorial_review · high risk · 25.6
```

이 후보는 reject는 아니지만, 점수가 너무 낮다. 해외 정치 구조 이슈는 “정당/정치인 평가”가 아니라 다음 방향으로 확장 가능하다.

- 양당제 균열
- 지역 격차
- 포퓰리즘
- 경제 불만
- 채권시장/정책 리스크
- 노동자 계층 이동

권장:

```text
C 또는 B · editorial_review · high/medium risk
```

최소한 `D`보다는 `C`가 더 자연스럽다.

## 4. why_interesting 평가

확실히 이전보다 좋아졌다.

좋은 예:

```text
값싼 드론 하나를 막기 위해 수백만 달러짜리 미사일을 태우는 구조라, 전쟁이 무기 성능보다 비용 교환비 싸움으로 바뀌는 장면을 보여줌
```

```text
AI slop 피로감에서 출발해 진정성 마케팅, AI 표기 규제, 창작자 반발, 브랜드 신뢰 경쟁으로 확장 가능
```

하지만 일부 후보는 뒤에 generic clause가 아직 붙는다.

예:

```text
시장/규제/산업 구조로 확장 가능
숫자나 통계로 증명할 여지가 있음
```

권장:

- generic clause는 내부 scoring reason에는 남겨도 됨
- digest에 보이는 `왜 보나`에는 후보별 구체 문장만 표시
- 필요하면 `debug_reason`과 `why_interesting`을 분리

## 5. possible_expansions 평가

현재는 모든 Top Candidate에 3개 이상 들어가 있다. 매우 좋다.

F88:

```text
- 베트남 전당포 F88의 상장 도전
- 한국의 전당포 이미지와 급전 수요 변화
- 베트남 금융 접근성과 오토바이 담보대출
```

코카인 하마:

```text
- 파블로 에스코바르의 코카인 하마
- 콜롬비아의 처리 난점과 안락사 논란
- 암바니 가문의 동물센터 제안
```

다만 digest에는 3개만 보이고 JSON에는 4개 이상 있는 경우가 있다. 이건 좋다. Markdown은 압축 표시, JSON은 더 풍부하게 유지하는 방식이 적절하다.

## 6. Sheet preview 평가

현재 CSV shape:

```text
8 rows x 25 columns
```

컬럼:

```text
digest_date
collected_at
last_seen_at
jibi_id
duplicate_key
source_url_canonical
rank
status
주제명
링크
출처
source_type
jibi_grade
total_score
recommended_action
risk_level
risk_flags
why_interesting
possible_expansions
evidence_needed
중복후보
reviewer
review_result
promoted_to_topic_finding
notes
```

이 구조는 `jibi 후보` staging sheet로 적합하다.

권장 유지:

- preview에는 Top Candidates만 포함
- rejected는 기본 preview에 넣지 않아도 됨
- 필요하면 별도 `rejected_preview.csv`를 만들 수 있음

운영 흐름:

```text
jibi 후보 = append-only staging sheet
주제 찾기 = 사람이 promote한 운영 sheet
```

## 7. Source Registry 평가

source registry는 37개 source를 포함한다.

group 분포:

```text
korea_business: 9
official_evidence: 7
primary_wire: 6
premium_manual: 6
weird_culture_science: 5
workflow: 3
manual_input: 1
```

type 분포:

```text
manual: 12
rss_candidate: 8
subscription_manual: 7
official_release: 7
sheet: 2
slack: 1
```

방향은 좋다. 다만 현재 `rss_candidate`에는 실제 feed URL이 없다. 따라서 RSS collector 구현 전에 아래 단계를 먼저 둬야 한다.

```text
rss_candidate
→ endpoint discovery
→ fetch test
→ parse test
→ rss_verified
```

0.9.3에서는 문서/registry 수준이므로 문제 없음.

## 8. 다음 단계 판단

0.9.3은 통과로 봐도 된다.

다만 1.0 Google Sheet append 전에 최소 보정:

1. `오늘의 추천` 문구 수정
2. 영국 양당/개혁당 grade를 D에서 C/B로 올리는 rule 보정
3. digest visible why_interesting에서 generic clause 제거
4. source registry rss_candidate는 endpoint 없는 후보라는 사실을 docs/status에 명확히 남김

그 다음 1.0으로 넘어간다.

## 9. 1.0 진입 기준

아래가 충족되면 Google Sheet append 구현으로 넘어갈 수 있다.

- make test 통과
- make jibi-digest 통과
- digest에서 reject가 Top Candidates에 없음
- `jibi 후보` preview CSV 컬럼 확정
- duplicate_key/source_url_canonical 있음
- 정치 hard reject와 해외 구조 정치 구분 정상
- action 기준이 과하게 후하지 않음

현재는 거의 충족했으며, 작은 표현/점수 보정만 남았다.
