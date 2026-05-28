# Luddite / Jibi 운영 실험 백서

- 작성일: 2026-05-28
- 대상 repo: https://github.com/Rlearnchan/luddite
- 현재 작업 축: MacBook Codex / luddite
- 명시적 제외: Windows Codex / syuka-ops 운영 자동화 수정
- 최신 관련 커밋:
  - `9f03b57 Tighten Jibi angle frame matching`
  - `df3d5aa Add Jibi story angle scoring`
  - `9ad5d69 Tighten Jibi replacement candidate quality`
  - `ab2b3ce Add Jibi topic diversity scoring`
  - `dbf2dd9 Refine Jibi board scoring and copy calibration`
  - `c1c159e Apply Jibi review-derived board adjustments`
  - `ef7bc61 Add Jibi hidden support intake`
  - `f11deba Link Jibi past video references`

이 문서는 GPT Pro 또는 외부 코드 리뷰어에게 Luddite/Jibi의 현재 위치를 설명하기 위한
정리 보고서다. 며칠 동안 커밋 단위 리뷰가 끊긴 상태이므로, 단일 PR 설명이 아니라
제품 취지, 현재 구현, 운영 실험 결과, 병목, 다음 의사결정 지점을 함께 정리한다.

## 1. 한 줄 요약

Luddite의 현재 중심은 완전 자동 PPT 제작기가 아니라, 매일 RSS/공식자료에서 방송 소재
후보를 뽑아 `Jibi` 구글 시트에 올리고, 리서치팀의 한 줄 리뷰를 받아 선별 감각을
보정하는 운영 실험이다.

Jibi는 이제 수집/정규화/중복제거/시트 게시/리뷰 회수/second-search/과거 영상 유사도
참고까지 연결되어 있다. 다만 가장 큰 병목은 여전히 **선별 로직**이다. 현재 로직은
점수, 규칙, source role, topic diversity, 과거 리뷰, syuka 유사도, story angle heuristic을
계층적으로 합산한다. 그러나 리서치팀이 원하는 것은 단순히 "주제가 중요하다"가 아니라
**슈카월드식으로 덜 뻔한 장면, 다른 렌즈, 의외의 질문으로 자랄 수 있는 후보**다.

이 지점부터는 키워드/규칙 기반 땜질의 한계가 보인다. LLM을 즉시 production 선별자로
쓰자는 뜻은 아니지만, 적어도 `report-only` 방식의 story angle 평가, 제목/설명 후보 생성,
프레임 전환 후보 제안에는 도입을 검토할 만한 시점에 왔다.

## 2. 프로젝트의 원래 취지

Luddite는 슈카월드 리서치 흐름을 돕기 위한 로컬 개발 프로젝트다. 큰 그림은 세 역할로
나뉜다.

```text
Jibi: 기사/자료 수집 및 후보 선별
Anny: 후보를 방송용 스토리라인으로 확장
Piti: 스토리라인을 PPT 초안/슬라이드 구조로 변환
```

현재 운영의 중심은 Jibi다. Jibi의 목표는 "자동으로 정답 주제를 뽑는 AI 편집자"가 아니다.
지금의 목표는 더 실험적이고 현실적이다.

```text
매일 들어오는 기사와 공식자료
-> 후보를 정규화하고 묶음 단위로 선별
-> Google Sheet `Jibi` 탭에 사람이 읽을 수 있는 리뷰보드로 게시
-> 리서치팀 3인이 짧게 평가
-> 평가를 다시 구조화해 다음 선별 기준 보정
```

즉 Jibi는 "발굴기"인 동시에 "선별 감각 학습 장치"다.

## 3. 현재 큰 그림에서의 위치

초기에는 Google Sheet append 안전성, header compatibility, 운영 시트 보호가 주요
문제였다. 지금은 그 단계는 지나왔다. 현재는 다음 단계다.

```text
완료:
- Sheet append/staging safety
- header backward compatibility
- unsafe header guard
- date-scoped RSS import
- source freshness report
- near-duplicate detection
- candidate funnel
- manual ops / review board
- reviewed-candidate guard
- syuka-ops snapshot read-only matching
- second-search / hidden support
- review feedback structuring
- board_score / topic diversity / angle lab

현재 병목:
- "좋은 방송 seed인가"를 판단하는 선별 감각
- 제목/설명 copy가 인간 편집자 수준으로 자연스럽고 설득력 있게 나오는가
- 후보가 단독 seed인지, sub-block인지, hook-only인지, evidence인지 구분하는 능력
- 과거 슈카월드 소재와의 중복/새 각도 판단

아직 본격화 전:
- Anny production storyline generation
- Piti production PPT generation
- LLM 기반 선별/프레이밍
- 장기 article DB / embedding DB
```

Jibi는 이미 Anny와 맞닿는 지점까지 왔다. "무엇을 찾을까"에서 "어떤 이야기로 바꿀 수
있나"로 넘어가고 있기 때문이다. 이 전환은 제품적으로 좋은 신호지만, 동시에 규칙 기반
선별의 한계를 드러내는 지점이기도 하다.

## 4. 현재 운영 흐름

표준 수동 운영은 다음과 같다.

```bash
make jibi-review-board-refresh-with-syuka JIBI_DATE=YYYY-MM-DD
```

이 명령은 대략 다음 일을 한다.

1. RSS/공식자료를 날짜 단위로 수집한다.
2. article history와 중복 정보를 반영한다.
3. 후보를 정규화한다.
4. 후보 점수를 계산한다.
5. 유사 후보를 story bundle로 묶는다.
6. Jibi review board CSV/metadata를 만든다.
7. syuka-ops local snapshot을 read-only로 조회해 과거 유사 영상을 붙인다.
8. 다시 리뷰보드를 렌더한다.

실제 Google Sheet 교체는 별도 명령으로 한다.

```bash
make jibi-review-board-replace-with-syuka JIBI_DATE=YYYY-MM-DD
```

리뷰를 받은 뒤에는 다음으로 요약한다.

```bash
make jibi-review-feedback JIBI_DATE=YYYY-MM-DD
```

관련 주요 산출물:

```text
outputs/daily_digest/YYYY-MM-DD_bundle_review_sheet.csv
outputs/daily_digest/YYYY-MM-DD_bundle_review_sheet_metadata.json
outputs/reports/jibi_quality_YYYY-MM-DD.md
outputs/reports/jibi_board_score_YYYY-MM-DD.md/json
outputs/reports/jibi_review_feedback_YYYY-MM-DD.md/json
outputs/reports/jibi_hidden_support_intake_YYYY-MM-DD.md/json
outputs/reports/jibi_syuka_refresh_YYYY-MM-DD.md/json
```

## 5. Google Sheet 리뷰보드

현재 `Jibi` 구글 시트는 단일 탭 리뷰보드다. 여러 탭으로 나누지 않고, 상단 안내문과
후보 표를 같은 탭에 둔다.

보이는 컬럼은 고정되어 있다.

```text
일시
제목
점수
메인 링크
서브 링크
설명
과거 영상
리뷰-성원
리뷰-동찬
리뷰-형찬
ID
```

중요한 제품 원칙:

- `제목`은 항상 한국어로 적는다. 해외 기사도 번역/의역한다.
- `점수`는 `B · 68점` 형식이다.
- `설명`은 내부 라벨이 아니라 사람이 읽는 자연스러운 문단이어야 한다.
- `과거 영상`에는 syuka-ops로 찾은 슈카월드 과거 영상 제목, 날짜, 조회수, 좋아요 수,
  중복/인접 여부를 넣는다.
- syuka 과거 영상 정보는 `설명`에 섞지 않는다.
- 리뷰팀은 각자 한 줄 리뷰를 남긴다.
- 리뷰가 시작된 뒤 같은 날 보드는 원칙적으로 다시 replace하지 않는다.

리뷰보드 format contract:

```text
docs/product/jibi_review_board_format_contract.md
```

## 6. 데이터와 수집 상태

현재 Jibi는 다음 source들을 중심으로 수집한다.

- 연합뉴스 RSS
- 정책브리핑
- 한국은행, 특히 BOK 이슈노트
- Guardian sections
- The Conversation
- BBC/NPR 등 일부 해외 source

연합뉴스와 Guardian은 최근 실험에서 중요한 역할을 했다. 연합뉴스는 한국어 public wire로
많은 후보를 공급하지만, 보도자료성/기업 단신/행사성 후보가 섞인다. Guardian은 해외
생활경제, climate, technology, business 소재를 공급하지만 제품 리뷰, opinion/letter,
이미 익숙한 AI 담론이 섞인다.

한국은행/BOK 이슈노트는 시드 확률이 높은 source지만, 발행 주기가 길고 리서치팀이 이미
인지하는 경우도 많다. 그래서 Jibi에서 제외하면 Anny/Piti로 이어질 기회를 잃을 수 있지만,
이미 리뷰된 주제는 반복 게시하지 않도록 reviewed-candidate guard가 필요하다.

현재 full article body를 장기 저장하지는 않는다. RSS 제목/요약/링크와 일부 보강 검색
결과를 중심으로 움직인다. 기사 본문 접근 가능성은 실험적으로 확인했지만, 장기 DB화는
아직 하지 않았다.

## 7. syuka-ops 활용 방식

syuka-ops는 Windows/Docker 운영 프로젝트이며, luddite에서는 local snapshot을 read-only로
참고한다. luddite가 syuka-ops DB를 수정하지 않는다.

현재 활용:

- 후보 title/query terms를 syuka snapshot에 검색
- 슈카월드 과거 영상만 대상으로 제한
- 머니코믹스 등 다른 채널은 제외
- 유사 영상 제목, 날짜, 조회수, 좋아요 수를 `과거 영상` 컬럼에 표시
- duplicate/adjacent/background 성격을 참고 신호로 사용

syuka 신호는 자동 승인/거절 신호가 아니다. 예를 들어 과거 영상과 닮았다는 것은 두 가지로
해석될 수 있다.

```text
나쁜 경우: 이미 같은 이야기를 했다 -> 중복/뒷북
좋은 경우: 과거에 먹힌 소재의 새 업데이트다 -> 후속/인접 소재
```

현재 로직은 duplicate이면 board_score에서 감점하고, adjacent이면 약간 가점을 준다. 그러나
"과거 영상과 닮았지만 새로운 각도인가" 판단은 여전히 불완전하다.

관련 문서:

```text
docs/integrations/syuka_ops_bridge_plan.md
docs/status/jibi_operating_experiment_2026-05-25.md
```

## 8. 리서치팀 리뷰에서 드러난 기대

리서치팀이 원하는 것은 단순히 "중요한 주제"가 아니다. 리뷰를 종합하면 다음과 같다.

### 8.1 원하는 것

- 단독 seed가 될 만한 큰 소재
- 한 단 또는 초반 hook으로 쓸 수 있는 가벼운 소재
- 익숙한 주제라도 새 각도나 구체 사례가 있는 후보
- 생활 속 문제의식에서 출발해 구조로 확장되는 후보
- "이걸 보니 이런 질문을 던질 수 있겠다"는 후보
- 숫자, 제도, 사례, 시각화 가능성이 붙는 후보
- 슈카월드 과거 영상과 연결되지만 단순 반복은 아닌 후보

예시로 긍정적이었던 방향:

- 페라리 전기차: 단독 seed는 애매하지만 초반 hook 가능
- AI 역사 브이로그: AI 거대담론이 아니라 "편하게 즐기는 AI" 쪽이면 sub-block 가능
- 배달로봇: 생활 속 문제의식은 있으나 정책/통계/한국 연결 필요
- 미끼매물/중개보수: 생활 속 공감 문제로 좋으나 이미 익숙한 프레임 주의

### 8.2 싫어하는 것

- 교과서식 설명
- 너무 거대한 담론
- "AI가 세상을 바꾼다" 같은 추상적 주제
- 스포츠 단독 주제
- 이미 많이 다룬 생활물가 주제의 단순 반복
- 단일 기업/투자 뉴스처럼 보이는 후보
- 회의/협약/행사/모집 공지 자체를 seed처럼 올리는 것
- 과거에 했던 소재를 새 각도 없이 다시 올리는 것
- 링크만 더 붙이면 자동으로 살아날 것처럼 처리하는 것

2026-05-27 리뷰 피드백 요약:

```text
- Total rows: 10
- 리뷰-성원: 7/10
- 리뷰-동찬: 10/10
- 리뷰-형찬: 10/10
- too_familiar: 8
- needs_supporting_links: 3
- weak_audience_bridge: 2
- positive promising_hook: 17
- editorial_role main_seed: 0
- editorial_role sub_block: 7
- editorial_role hook_only: 3
```

즉 리뷰팀은 후보들을 완전 reject하지는 않았지만, 대부분을 `main_seed`가 아니라 `sub_block` 또는
`hook_only`로 봤다. 이 점이 현재 선별 병목의 핵심이다.

## 9. 현재 선별 로직: 구체적 구조

현재 선별은 크게 두 층이다.

```text
candidate total_score
-> story bundle
-> review board board_score
```

`total_score`는 후보 자체의 기본 점수다. 기사/자료 단위에서 broadcast potential,
source, risk 등을 반영한다.

`board_score`는 리뷰보드 게시용 점수다. "점수는 높은데 보드에 올리면 안 되는 후보"를
내리고, "점수는 낮지만 리뷰할 가치가 있는 후보"를 올리기 위해 추가된 레이어다.

핵심 구현 파일:

```text
src/luddite/agents/jibi/render_daily_digest.py
src/luddite/agents/jibi/score_candidates.py
src/luddite/agents/jibi/seed_quality.py
src/luddite/agents/jibi/review_feedback.py
src/luddite/agents/jibi/review_board_copy.py
```

### 9.1 기본 board_score

대표 후보의 `total_score`에서 시작한다.

가점:

- standalone seed
- seed with supporting links
- conditional/bundle seed
- strong/conditional so-what
- second-search supporting links
- syuka adjacent context
- story angle shift

감점:

- evidence-only
- demote/reject
- weak audience bridge
- promo/program/event bulletin
- market/security-specific frame
- public wire인데 system frame이 약함
- single-company frame
- source/cluster/title mismatch
- syuka duplicate
- reviewed-before/rejected-before/promoted-before
- topic diversity overflow
- generic frame risk
- review-derived downrank

### 9.2 hard block

다음은 리뷰보드 primary row에서 강하게 제외된다.

- 제품 리뷰 / shopping guide
- 이미 reject/downrank 판정된 후보
- 부고/모친상/별세 등 방송 소재로 부적절한 후보
- source/title/cluster mismatch
- 이미 리뷰된 rejected_before 후보

### 9.3 reviewed-candidate guard

리서치팀이 이미 본 후보는 기본적으로 suppress한다.

- `reviewed_before`: 기본 suppress
- `promoted_before`: 후속 뉴스나 새 각도 없으면 suppress
- `rejected_before`: 훨씬 강하게 suppress

2026-05-27에서는 예를 들어:

- 청년 노동시장/쉬었음: promoted_before라 suppress
- 자산 토큰화: rejected_before라 suppress
- 생산 부문 자금 흐름: reviewed_before라 suppress

### 9.4 source role cap

source role별 과도한 쏠림을 막기 위한 cap이 있다.

초기 cap 개념:

```text
research_note: 3
policy_release: 2
public_wire: 3
academic_explainer: 2
market_wire: 1
section_news: 3
```

다만 보드를 10개 채우기 위해 cap에 걸린 후보가 backfill될 수 있다. 이 때문에 낮은 점수의
후보가 들어오는 현상이 있다.

### 9.5 topic diversity

AI 후보 과밀을 막기 위해 topic family를 계산하고, 현재는 `ai_tech`를 제한 family로 본다.

2026-05-27 최신 로컬 run 기준:

```text
use_topic_diversity: true
selected_topic_family_counts:
- ai_tech: 3
- consumer_life: 5
- energy_climate: 4
- industry_supply_chain: 3
- labor_work: 3
- markets_finance: 4
```

문제는 현재 topic diversity가 `ai_tech` 중심으로만 제어되고, energy/climate, consumer/life,
markets/finance 쏠림은 warning으로만 남는다는 점이다.

### 9.6 Angle Lab / story angle scoring

최근 추가된 레이어다.

목적:

- "AI가 청년 고용을 바꾼다"처럼 큰 단어만 있고 장면/구조 전환이 없는 후보를 내린다.
- 비용 전가, 행정 책임, 전력망, 생활 규제 비용처럼 다른 렌즈가 잡히는 후보를 올린다.
- Anny로 넘길 수 있는 `frame_options`를 metadata/report에 남긴다.

현재 계산:

```text
generic_frame_risk: low | medium | high
generic_frame_reasons:
  - broad_ai_topic
  - abstract_youth_labor_question
  - generic_energy_price_question
  - abstract_policy_support_question
  - generic_export_or_growth_question
  - no_specific_scene
  - no_mechanism_shift
  - no_frame_shift

angle_shift_score: 0-5
frame_options:
  - frame
  - role_hint
  - reasons
  - needs
```

중요한 최근 수정:

처음에는 생성된 `why_interesting` / `possible_expansions`도 Angle Lab이 읽었다. 그런데 이전
템플릿 오분류가 남아 있으면 원문과 무관한 프레임이 붙는 문제가 생겼다. 예를 들어
`CJ온스타일 대화형 AI 유입` 후보에 예전 "배달비/수수료" 설명이 남아 있어서 무료배달
프레임이 잘못 붙었다. 이를 막기 위해 Angle Lab은 이제 원문 `title`, `summary`, `seed_type`,
`source_role_class`, `bundle_title`, `story_fingerprint`, `storyline_fit` 중심으로만 본다.

이 수정은 중요하다. 규칙 기반 프레임 전환이 생성문을 다시 먹으면 overfitting이 누적되기
때문이다.

## 10. 2026-05-27 최신 로컬 선별 결과

최신 커밋 기준으로 로컬 재계산한 결과다. Google Sheet replace는 하지 않았다.

```text
1. 폭염이 에어컨과 물놀이 물가를 올릴 때 — B · 88점
2. 전기요금은 왜 전쟁과 가스값을 따라 움직이나 — B · 85점
3. AI도 월 구독료를 받기 시작했다 — B · 84점
4. AI가 공무원 보고서와 현장 치안에 들어올 때 — B · 81점
5. 그린벨트에 사는 사람들은 왜 생활비 보조를 받나 — B · 76점
6. 잔디깎이 소음에도 비용이 붙는 시대 — B · 74점
7. 노노갈등 속 고개 든 삼성전자 분사론 — C · 52점
8. 전기차 공장 붐 이후 누가 비용을 떠안나 — B · 72점
9. AI 데이터센터는 전력 먹는 공장인가 — B · 68점
10. 해외 충격은 생활비로 어떻게 번지나 — C · 57점
```

이 결과는 "완성도 높은 10개"라기보다, 현재 규칙들이 어떤 후보를 살리고 죽이는지 보여주는
실험판이다. 특히 7번과 10번은 강한 후보라기보다 source role cap/backfill 영향이 남아 있다.

최근 리뷰에서 사용자와 Codex가 함께 확인한 핵심 문제:

- 1~10도 여전히 질문이 뻔하다.
- 11~20에 숨겨진 A급이 있던 것도 아니다.
- 후보군 전체가 "뻔한 질문으로 포장된 B/C급"을 많이 만든다.
- 따라서 단순 cap 조정이 아니라, 낯섦/구체성/새 질문/프레임 전환을 봐야 한다.

## 11. 현재 불편감과 선별 병목

### 11.1 리서치팀이 원하는 것과 현재 시스템의 차이

리서치팀은 "좋은 주제명"을 원하는 게 아니라, 방송으로 키웠을 때 살아나는 **장면과
질문**을 원한다.

예를 들어:

```text
약한 방향:
AI가 청년 고용을 바꾸나?

조금 나아 보이지만 여전히 같은 말:
AI 때문에 첫 직장 사무직이 사라지면, 청년은 어디서 경력을 시작하나?

실제로 필요한 방향:
회사 막내가 사라지면 회사는 누구를 키우나?
AI가 신입의 실수할 기회를 없애면 조직의 도제 시스템은 어떻게 바뀌나?
```

즉 "문장을 더 구체적으로 쓰기"가 아니라, 이야기의 주어와 렌즈를 바꿔야 한다.

현재 규칙 기반 `Angle Lab`은 이 문제를 일부 반영하기 시작했지만, 여전히 인간 편집자의
과감한 전환과는 거리가 있다.

### 11.2 10개를 채우는 문제

후보군이 약한 날에도 10개를 채우면 Jibi의 품질이 낮아 보인다. 실제로 리서치팀 피드백은
많은 후보를 `main_seed`가 아니라 `sub_block` 또는 `hook_only`로 봤다.

검토할 방향:

- 강한 후보가 6개면 6개만 올리는 variable board size
- 나머지는 `보류 후보`나 `sub-block queue`로 report-only 표시
- Google Sheet에는 "오늘은 강한 후보만 6개"라고 안내

### 11.3 second-search / hidden support의 위치

리뷰 후 second-search를 돌리면, 기존 메인 링크 후보는 reviewed-candidate guard 때문에 다음
보드에서 suppress된다. 따라서 second-search 결과를 곧바로 다음 primary board에 올리는 것은
개념적으로 애매하다.

현재 더 적절한 위치:

- 메인 링크는 그대로 리뷰받는다.
- hidden support는 비공개 report-only로 준비한다.
- 리뷰어가 "자료가 더 있으면 좋겠다"고 한 후보에 대해, hidden support가 실제로 도움이
됐는지 나중에 평가한다.
- 이 결과를 Anny/후속 pack에 쓰거나, 재상정 queue에만 넣는다.

즉 hidden support는 primary selection을 rescue하는 장치가 아니라, **후속 구성 가능성 검증
장치**에 가깝다.

### 11.4 syuka 유사도 판단

과거 영상 체크는 살아 있고 도움이 된다. 다만 현재는 여전히 신호 해석이 어렵다.

예:

- 비슷한 과거 영상이 있으면 duplicate 위험
- 하지만 과거에 먹힌 소재의 새 angle이면 오히려 useful context
- 조회수/좋아요 수는 관심도 힌트지만 자동 선별 근거로 쓰기 어렵다.

현재는 syuka 유사도 정보를 `과거 영상` 컬럼에 보여주고, duplicate이면 board_score 감점,
adjacent이면 약한 가점 정도로 처리한다. 다음 단계에서는 "same story", "adjacent theme",
"past hit with new update", "wrong channel/false positive"를 더 잘 나눠야 한다.

### 11.5 rule accumulation의 위험

현재 선별 로직은 점점 많은 규칙을 쌓아가고 있다.

- source role cap
- topic diversity
- reviewed suppression
- market risk
- promo/event bulletin
- sports primary downrank
- AI grand discourse downrank
- casual AI use-case bonus
- past topic overlap downrank
- generic frame risk
- angle shift score

각각은 실제 문제를 해결하기 위해 생겼지만, 전체적으로는 "왜 이 후보가 뽑혔는가"를 사람이
추론하기 어려워질 위험이 있다. Jibi가 뽑은 10개에 불편감이 생겼을 때, 어떤 규칙이 잘못된
것인지도 복잡해진다.

이것이 LLM 도입 검토가 자연스러운 이유다.

## 12. LLM 도입 검토

현재는 LLM API를 호출하지 않는다. 이 원칙은 운영 안정성, 비용, 재현성 측면에서 합리적이었다.
그러나 지금 병목은 단순 키워드 추출보다 훨씬 편집적이다.

LLM이 필요한 이유:

- "뻔한 주제"와 "다른 렌즈"의 차이는 키워드만으로 잡기 어렵다.
- source title/summary만으로도 좋은 프레임 후보를 여러 개 제안할 수 있다.
- 리서치팀 리뷰 문장의 뉘앙스를 더 잘 구조화할 수 있다.
- 후보 설명 문장을 사람이 읽을 만한 수준으로 만들 수 있다.
- Anny로 넘어갈 `frame_options`를 생성하는 데 적합하다.

다만 LLM을 바로 production gate로 쓰면 안 된다. 추천 도입 방식은 단계적이다.

### 12.1 1단계: report-only LLM story angle advisor

입력:

```json
{
  "title": "...",
  "summary": "...",
  "source": "...",
  "source_role": "...",
  "existing_score": 64,
  "review_history": "... optional",
  "syuka_matches": "... optional"
}
```

출력:

```json
{
  "literal_frame": "...",
  "why_it_is_obvious": "...",
  "angle_options": [
    {
      "frame": "...",
      "story_role": "main_seed|sub_block|hook_only|evidence",
      "why_less_obvious": "...",
      "needs": ["number", "case", "past video check"]
    }
  ],
  "do_not_use_as_primary_reason": "...",
  "reviewer_facing_summary": "..."
}
```

처음에는 selection을 바꾸지 않고 report에만 남긴다.

### 12.2 2단계: LLM copy draft

현재 `review_board_copy.py`는 사람이 읽을 수 있는 설명을 만들지만, 템플릿 냄새가 남는다.
LLM을 copy draft에만 쓰면 위험이 낮다.

원칙:

- 원문 title/summary/link 안의 사실만 사용
- 없는 숫자나 세부 사실 생성 금지
- syuka 과거 영상 정보는 `설명`이 아니라 `과거 영상` 컬럼에만 사용
- 후보의 역할을 main_seed/sub_block/hook_only/evidence로 분명히 표시
- 내부 라벨은 숨김

### 12.3 3단계: LLM-assisted selection comparison

LLM이 고른 Top N과 기존 board_score Top N을 비교한다.

평가:

- 리서치팀 리뷰와 어느 쪽이 더 잘 맞는가
- LLM이 high-score지만 뻔한 후보를 잘 내리는가
- LLM이 낮은 점수지만 신선한 hook을 찾는가
- hallucination 없이 source 근거를 유지하는가

이 단계에서도 Google Sheet selection default로 바로 쓰지 않는다.

### 12.4 4단계: Anny 연결

Jibi가 안정적으로 `angle_options`를 만들면, Anny는 그중 하나를 받아 스토리라인으로 확장한다.

즉 Jibi와 Anny의 연결점은 다음이다.

```text
Jibi candidate
-> frame_options / angle_options
-> Anny storyline seed
-> evidence plan
-> Piti slide structure
```

지금은 이 연결점에 도달한 상태라고 볼 수 있다.

## 13. 현재 코드 리뷰에서 특히 봐야 할 파일

GPT Pro에게 코드 리뷰를 요청한다면 아래 파일을 우선 보게 하면 좋다.

```text
README.md
docs/product/jibi_review_board_format_contract.md
docs/status/jibi_operating_experiment_2026-05-25.md

src/luddite/agents/jibi/render_daily_digest.py
src/luddite/agents/jibi/review_board_copy.py
src/luddite/agents/jibi/review_feedback.py
src/luddite/agents/jibi/score_candidates.py
src/luddite/agents/jibi/seed_quality.py
src/luddite/agents/jibi/board_support_search.py
src/luddite/agents/jibi/hidden_support_search.py
src/luddite/agents/jibi/hidden_support_intake.py
src/luddite/agents/jibi/syuka_refresh.py

tests/test_daily_digest_renderer.py
tests/test_jibi_review_feedback.py
tests/test_jibi_hidden_support_intake.py
tests/test_jibi_board_support_search.py
```

최근 산출물:

```text
outputs/reports/jibi_board_score_2026-05-27.md/json
outputs/reports/jibi_review_feedback_2026-05-27.md/json
outputs/reports/jibi_hidden_support_intake_2026-05-27.md/json
outputs/daily_digest/2026-05-27_bundle_review_sheet.csv
outputs/daily_digest/2026-05-27_bundle_review_sheet_metadata.json
```

## 14. GPT Pro에게 묻고 싶은 핵심 질문

1. 현재 Jibi의 선별 로직은 너무 많은 규칙이 누적되어 있지 않은가?
2. `board_score`와 `total_score`의 책임 분리가 적절한가?
3. `Angle Lab`이 Anny 연결점으로서 적절한 추상화인가?
4. "뻔한 질문"을 규칙 기반으로 잡는 현재 방식은 어디까지 유지할 수 있는가?
5. LLM을 도입한다면 selection, copy, story angle, review inference 중 어디부터가 가장 안전한가?
6. Google Sheet 리뷰보드에는 10개를 고정으로 올리는 게 나은가, 품질 기준 미달이면 6-8개만 올리는 게 나은가?
7. second-search/hidden support는 primary selection에 반영해야 하는가, 아니면 follow-up pack 전용으로 남겨야 하는가?
8. syuka past-video similarity는 duplicate guard인지, adjacent context인지, performance prior인지 어떻게 분리해야 하는가?
9. Jibi -> Anny handoff contract를 지금 정의해야 하는가?
10. 현재 코드 구조에서 `render_daily_digest.py`가 너무 많은 책임을 갖고 있지 않은가?

## 15. 다음 작업 제안

### 15.1 즉시 할 수 있는 작은 패치

- variable board size 도입 검토
- `Angle Lab`을 별도 모듈로 분리
- `board_score` 계산 이유를 더 사람이 읽기 좋게 report
- topic diversity를 ai_tech 외에도 consumer_life/energy_climate에 약하게 확장
- source role cap과 topic cap의 상호작용 report 강화
- reviewed suppress와 second-search reconsideration queue를 더 명확히 분리

### 15.2 LLM 실험 패치

`Jibi LLM Story Angle Advisor`를 report-only로 만든다.

입력은 현재 candidate metadata + title/summary + syuka match + review history로 제한한다.
출력은 JSON schema로 강제한다. Google Sheet selection은 바꾸지 않는다.

비교 리포트:

```text
rule_based_frame_options
llm_frame_options
reviewer_feedback_alignment
hallucination_or_unverified_claims
operator_pick
```

### 15.3 Anny 연결 준비

Jibi metadata에 다음을 안정적으로 남긴다.

```text
literal_frame
angle_options
story_role
required_evidence
past_video_context
reviewer_objections
```

Anny는 이 중 하나를 골라:

```text
opening hook
background
mechanism
numbers/evidence
counterargument
Korea bridge
slide outline
```

로 확장한다.

## 16. 결론

Jibi는 이제 단순 RSS 수집기나 Google Sheet append 스크립트가 아니다. 운영 시트 안전성,
manual run, review board, review feedback, syuka reference, second-search, hidden support,
board_score까지 연결된 실험 시스템이 되었다.

그러나 지금 가장 중요한 병목은 선별 감각이다. 리서치팀은 Jibi가 고른 후보를 보고
"이 주제가 중요하냐"보다 "이걸 슈카월드식으로 새롭고 재미있게 풀 수 있냐"를 판단한다.
현재 규칙 기반 로직은 그 요구를 따라가기 위해 계속 패치되고 있지만, 규칙 누적의 복잡성과
overfitting 위험이 커지고 있다.

따라서 다음 큰 방향은 둘 중 하나다.

```text
1. deterministic scoring을 더 정돈해, Jibi를 안정적 운영 도구로 유지한다.
2. report-only LLM angle advisor를 붙여, 프레임 전환과 copy 품질을 실험한다.
```

개인적인 판단으로는 이제 2번을 검토할 시점이다. LLM을 최종 선별자로 쓰자는 뜻이 아니라,
리서치팀이 실제로 요구하는 "덜 뻔한 렌즈"와 "Anny로 넘어갈 이야기 씨앗"을 후보별로
제안하게 만들고, 기존 규칙 기반 board_score와 비교하는 방식이 가장 안전하다.

