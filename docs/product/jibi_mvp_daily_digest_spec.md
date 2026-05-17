# jibi MVP: Daily Digest Spec

## 1. 목표

`jibi`의 첫 MVP는 24/7 완전자동 수집기가 아니라, 리서치팀의 출근 시작점을 제공하는 daily digest다.

핵심 산출물:

```text
오늘의 슈카월드 후보 10개
```

## 2. 후보 개수

권장 흐름:

```text
raw collection: 100~300개
pre-filter: 30~50개
digest: 10개
human save/assign: 0~5개
```

`anny`로 넘기는 후보를 하루 1~3개로 고정하지 않는다. `anny`는 당일 후보뿐 아니라 DB에 쌓인 후보/evidence를 연결해 storyline을 짜야 한다.

## 3. 점수 기준 재정렬

사용자 우선순위:

```text
1. 조회수 가능성
2. 자료의 풍부함
3. 숫자/통계의 강함
4. 엥? 하는 이상함
5. 농담/밈 회수 가능성
6. 시의성
```

초기 scoring proposal:

```text
view_potential_proxy      25
source_richness           20
numbers_or_stats          15
weirdness_or_hook         12
structure_expansion       12
humor_or_punchline         8
timeliness                 5
risk_penalty             -0~30
```

주의: 조회수 가능성은 직접 예측하기 어렵다. 초기에는 아래 proxy로 본다.

```text
- 과거 슈카월드 channel category 성과
- title clickability
- 자료 밀도
- 숫자/그래프 가능성
- 기존 래퍼토리 연결
```

## 4. 후보 output schema 보강 제안

현재 `jibi_candidate`에 아래 필드 추가를 고려한다.

```json
{
  "broadcast_potential": "high | medium | low",
  "risk_level": "high | medium | low",
  "view_potential_proxy": "high | medium | low",
  "source_richness": "high | medium | low",
  "recommended_action": "send_to_anny | gather_more_evidence | keep_for_later | editorial_review | reject",
  "digest_reason": "사람이 클릭해야 하는 이유 1~2문장",
  "rejection_or_hold_reason": "보류/미사용 가능성 설명",
  "evidence_cluster_hints": ["..."],
  "related_existing_items": ["..."]
}
```

`editorial_review`는 다음 단계에서 추가하는 것을 권장한다. 정치/기업/의료/마약/선정성 소재는 단순 `gather_more_evidence`가 아니라 사람 판단이 필요할 수 있다.

## 5. risk policy

완전 금지:

```text
- 특정 정당/대통령 직접 평가
```

사람 검토 필요:

```text
- 이스라엘/팔레스타인
- 중국 기업 칭찬
- 특정 국내 기업 투자 판단
- 의료 효과 단정
- 선정적 소재
- 연예/스포츠
- 역사
- 범죄/마약 소재
```

## 6. source ratio

초기 권장:

```text
해외 seed 70%
국내 seed 30%
```

원칙:

```text
해외 seed 우선, 국내 연결은 나중.
```

단, 한국 이슈 자체가 seed인 경우에는 해외 사례가 background/contrast로 쓰인다.

## 7. digest format

Markdown/Slack 카드 예:

```md
## 1. 베트남 전당포가 상장한다고?

- grade: B+
- broadcast_potential: high
- risk_level: medium
- source_richness: high
- seed_type: absurd_foreign + finance
- 왜 클릭할 만한가: 낯선 전당포 회사가 숫자로 증명되는 성장 스토리를 갖고 있음.
- 가능한 전개: F88 상장 -> 한국 전당포 기억 -> 베트남 신용시장 -> 오토바이 담보대출 -> 규제 리스크
- 더 찾을 자료: 베트남 은행 접근성, F88 공시, 현지 규제
- risk: 단일 기사 의존, 금융/투자 오해
- action: gather_more_evidence
```

## 8. Google Sheet output

추천 컬럼:

```text
created_at
rank
title
seed_url
source
source_region
seed_type
broadcast_potential
risk_level
view_potential_proxy
source_richness
why_click
possible_expansions
korea_bridge
punchline_candidate
evidence_needed
risk_flags
recommended_action
status
owner
human_note
```

status 예:

```text
new
saved
assigned
storyline_requested
used
rejected
archived
```
