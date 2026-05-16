# 03. jibi Seed Selection Playbook

작성일: 2026-05-16
상태: v0.1 draft

## 1. 역할 정의

`jibi`는 24/7 뉴스 수집기가 아니다. 핵심 역할은 **방송으로 살아날 가능성이 있는 seed를 발견하고 정리하는 것**이다.

좋은 `jibi` 후보는 기사 하나의 요약이 아니라, 다음 질문에 답해야 한다.

```text
이게 왜 이상한가?
어디까지 확장되는가?
한국 시청자가 왜 봐야 하는가?
어떤 숫자와 근거가 있는가?
어떤 위험이 있는가?
마지막에 어떤 질문으로 회수할 수 있는가?
```

## 2. 후보 수집 우선순위

### 2.1 1차 seed source

| 분류 | 예시 | 용도 |
|---|---|---|
| 주요 통신사 | Reuters, AP, 연합뉴스, Newsis | 사실관계 seed, 공식 발언 |
| 경제/금융 매체 | Bloomberg, FT, WSJ, 한국경제, 매일경제, 서울경제 | 시장 반응, 기업/산업 흐름 |
| 공식자료 | 정부, 중앙은행, World Bank, 통계청, ILO, OECD | 숫자 검증, 그래프 |
| 장문/해설 매체 | Economist, NYT, Guardian | 맥락과 해석 |
| 특이 소재 | 지역지, 과학/기술 블로그, 산업 보고서 | 이색 seed |

### 2.2 수집 제외 또는 낮은 우선순위

- 단순 신제품 출시
- 특정 기업 PR 문구에 가까운 기사
- 하루짜리 속보로 끝날 가능성이 큰 기사
- 출처가 약한 소셜미디어 루머
- 방송에서 다루기 민감한데 공익성이 낮은 소재
- 너무 많은 매체가 이미 똑같이 소비한 소재

## 3. Seed scoring

초기 점수는 다음 구조를 권장한다.

```text
seed_score =
  novelty
+ absurdity
+ expandability
+ evidence_depth
+ korea_bridge
+ visual_potential
+ punchline_potential
+ timing
- risk_penalty
- pure_promo_penalty
- too_live_news_penalty
```

각 항목은 1~5점으로 두고, penalty는 0~5점으로 둔다.

### 3.1 점수 정의

| 항목 | 1점 | 5점 |
|---|---|---|
| novelty | 흔한 뉴스 | 처음 듣는 조합 |
| absurdity | 예상 가능한 뉴스 | 제목만으로 “엥?” 발생 |
| expandability | 기사 요약으로 끝남 | 3~4단 확장 가능 |
| evidence_depth | 기사 1개뿐 | 공식자료/통계/과거사례 풍부 |
| korea_bridge | 한국 연결 없음 | 한국 기억/산업/생활로 자연 연결 |
| visual_potential | 그림 없음 | 차트/사진/짤/캡처 풍부 |
| punchline_potential | 딱딱하게 끝남 | 마지막 질문/농담 가능 |
| timing | 늦었거나 너무 이름 | 이번 주 방송에 적합 |

## 4. Seed type taxonomy

| seed_type | 설명 | 좋은 예시 |
|---|---|---|
| `anomaly` | 상식과 어긋나는 이상징후 | 스승의 날인데 카네이션이 안 팔림 |
| `policy_shock` | 정책 발언/제도가 시장이나 여론을 흔듦 | 국민배당금과 코스피 급락 |
| `market_reaction` | 가격/주가/금리/환율의 큰 반응 | 영국 정치 리스크와 국채금리 |
| `foreign_oddity` | 해외 이색 사건 | 코카인 하마 인도행 |
| `cost_inversion` | 비용 구조가 뒤집힘 | 300달러 드론 vs 수백만 달러 미사일 |
| `culture_shift` | 생활/직장/세대 문화 변화 | 반바지 출근, 스승의 날 변화 |
| `power_shift` | 정치/지정학 권력관계 변화 | 트럼프가 중국에 도움 요청 |
| `company_as_window` | 특정 회사로 산업/사회 구조를 설명 | 베트남 전당포 F88 |
| `wordplay_bridge` | 제목/단어의 중의성으로 확장 | 레이저 무기 → 피부과 레이저 |

## 5. 좋은 후보 예시

### 5.1 베트남 전당포 F88 상장

- seed: 베트남 최대 신세대 전당포가 HOSE 이전 상장을 추진
- 좋은 이유:
  - “전당포가 상장?”이라는 즉각적 의문
  - 매출 10배, 점포 900개 등 숫자 존재
  - 한국의 전당포 기억으로 번역 가능
  - 베트남 신용시장, 비공식 고용, 오토바이 담보대출로 확장
  - 창업자 서사와 추심 리스크가 있어 성공담으로 끝나지 않음

### 5.2 콜롬비아 코카인 하마 인도행

- seed: 파블로 에스코바르의 하마를 인도 암바니가 데려가려 함
- 좋은 이유:
  - 소재 자체가 이상하고 강함
  - 하마 문제에서 암바니 가문으로 전환 가능
  - 릴라이언스식 가격전쟁과 캄파콜라로 확장 가능
  - 마지막에 슈카콜라 농담으로 회수 가능

### 5.3 드론 방어 비용 역전

- seed: 값싼 드론을 비싼 미사일로 막는 국방비 비효율
- 좋은 이유:
  - 비용 구조가 직관적
  - EMP, 그물총, 샷건, 레이저 등 비교 가능
  - 각국 레이저 무기 경쟁으로 확장
  - 한국 천광, 한국 피부과 레이저로 회수 가능

## 6. 나쁜 후보 또는 감점 후보

### 6.1 단순 기업 홍보

```text
“OO기업, 신제품 출시”
```

감점 이유:

- 확장성이 낮다.
- 기업 PR로 보일 수 있다.
- 숫자/구조/반전이 없다.

### 6.2 너무 따끈따끈한 예측형 뉴스

```text
“OO시장이 곧 폭발적으로 커질 전망”
```

감점 이유:

- 예상/선동처럼 보일 수 있다.
- 근거가 보고서 한 개에 그칠 수 있다.
- 실패 시 리스크가 크다.

### 6.3 특정 민감집단 비판으로 읽힐 소재

감점 이유:

- 콘텐츠 의도가 구조 설명이어도 공격으로 소비될 수 있다.
- 외교/법무/평판 리스크가 있다.

## 7. Candidate schema

`jibi`는 후보마다 아래 구조를 생성한다.

```json
{
  "candidate_id": "2026-05-16-source-slug",
  "title": "...",
  "seed_url": "...",
  "source": "...",
  "published_at": "...",
  "collected_at": "...",
  "language": "ko/en/...",
  "summary": "3문장 요약",
  "seed_type": "foreign_oddity",
  "why_interesting": "제목만으로 왜 이상한지",
  "why_shuka": "슈카월드에서 살아날 이유",
  "possible_expansions": ["...", "..."],
  "korea_bridge": "...",
  "punchline_candidate": "...",
  "evidence_needed": ["공식 통계", "과거 사례"],
  "evidence_urls": ["..."],
  "risk_flags": ["copyright", "politics"],
  "scores": {
    "novelty": 4,
    "absurdity": 5,
    "expandability": 5,
    "evidence_depth": 4,
    "korea_bridge": 3,
    "visual_potential": 4,
    "punchline_potential": 5,
    "timing": 4,
    "risk_penalty": 1,
    "pure_promo_penalty": 0,
    "too_live_news_penalty": 0
  },
  "status": "collected"
}
```

## 8. Daily digest 출력

매일 아침 digest는 후보 10개 이내가 적정하다.

```text
오늘의 후보 10개

1. 베트남 전당포 F88, HOSE 이전 상장 추진
   - seed_type: company_as_window / foreign_oddity
   - 왜 슈카월드감인가: 전당포라는 낡은 이미지와 신흥국 금융 성장의 결합
   - 예상 전개: F88 → 전당포란 → 베트남 신용시장 → 오토바이 담보대출 → 추심 리스크
   - 필요한 추가자료: 베트남 비공식 고용률, 오토바이 보급률, F88 실적
   - 위험: 단일 기사 의존, 현지 규제 확인 필요
```

## 9. Human review 상태

후보 상태는 다음으로 관리한다.

| status | 의미 |
|---|---|
| `collected` | 수집됨 |
| `shortlisted` | 사람이 검토할 후보 |
| `researching` | 추가자료 수집 중 |
| `storyline_requested` | anny로 넘김 |
| `discarded` | 버림 |
| `used` | 방송/자료에 사용됨 |

## 10. 구현 우선순위

1. RSS/news collector
2. URL canonicalizer
3. candidate normalizer
4. scoring prompt
5. daily digest renderer
6. Sheet/Notion feedback loop
