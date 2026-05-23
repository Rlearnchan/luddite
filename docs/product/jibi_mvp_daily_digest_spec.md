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

`editorial_review`는 정치/기업/의료/마약/선정성/투자 소재처럼 방송 가능성은 있으나 사람이 먼저 판단해야 하는 후보에 사용한다.

직접 대통령/정당/지지율 평가 프레임은 `editorial_review`가 아니라 `reject` 또는 정책상 block 처리한다.

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
# Luddite Daily Digest — YYYY-MM-DD

## 오늘의 추천

- 바로 볼 만한 후보: N개
- 자료 보강 필요: N개
- 사람 검토 필요: N개
- 킵 후보: N개
- 제외/거절: N개

## Top Candidates

### 1. 베트남 전당포가 상장한다고?

`B · gather_more_evidence · medium risk`

왜 보나:
- 낯선 전당포 회사가 숫자로 증명되는 성장 스토리를 갖고 있음.

확장:
- F88 상장
- 한국 전당포 기억
- 베트남 신용시장과 오토바이 담보대출

필요:
- 베트남 은행 접근성
- F88 공시
- 현지 규제/추심 리스크

## Excluded / Rejected

- 대통령/정당 직접 평가 소재: direct_president_party_evaluation
```

Reject 또는 block 후보는 Top Candidates slot을 차지하지 않는다. 필요하면 `Excluded / Rejected` 섹션에 짧게 남긴다.

## 8. Google Sheet output

MVP append target은 기존 `주제 찾기` 탭이 아니라 같은 공유 문서 안의 새 staging 탭이다.

추천 탭:

```text
jibi 후보
```

운영 원칙:

```text
jibi 후보 -> human review -> selected rows promoted/copied to 주제 찾기
```

`주제 찾기`는 사람 중심 운영 sheet로 유지한다.

`jibi 후보` 추천 컬럼:

```text
수집일
jibi_id
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
slideability_score
slideability
first_slide_idea
likely_proof_object_types
visual_risks
```

status 예:

```text
new
```

review_result 예:

```text
keep
promote
needs_more_evidence
editorial_review
reject
```
