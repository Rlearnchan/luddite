# Codex Handoff after Design Interview

## 상태

Luddite v0.7 eval harness 완료 후, 사용자와 실제 사용 방식에 대한 설계 인터뷰를 진행했다.

핵심 결론:

```text
단기 최우선은 jibi daily digest MVP다.
PPT 생성은 장기 목표다.
```

## 반영해야 할 설계 수정

### 1. jibi 우선순위 상향

다음 구현은 가능하면 `jibi Daily Digest MVP` 중심으로 계획한다.

첫 데모:

```text
매일 아침 후보 10개 digest
```

### 2. output UI

초기 UI는 CLI가 아니라 Google Sheet + Slack 쪽이 업무에 잘 붙는다.

```text
- Google Sheet append
- Slack daily digest / query
- Markdown report는 debug/archive용
```

### 3. jibi scoring weight 수정

사용자 우선순위:

```text
조회수 가능성
> 자료 풍부함
> 숫자/통계
> 엥? hook
> 농담/밈
> 시의성
```

### 4. recommended_action 확장 고려

현재:

```text
send_to_anny
gather_more_evidence
keep_for_later
reject
```

추가 권장:

```text
editorial_review
```

이유: 정치/기업/의료/마약/선정성 소재는 자료를 더 모으는 문제가 아니라 사람 판단이 필요할 수 있음.

### 5. anny 입력 재정의

anny는 단일 주제 수동 입력보다, jibi DB에서 연결된 seed/evidence cluster를 기반으로 storyline을 제안해야 한다.

### 6. piti 기대치 조정

piti는 장기 목표지만, 구현할 때는 포맷 fidelity가 중요하다.

MVP는:

```text
텍스트 + notes + 기본 포맷이 맞는 PPTX 초안
```

## 다음 구현 추천

### Option A: Manual Dry Run 먼저

요금/검증상 안전한 단계.

```text
make eval-jibi-seeds --model-output manual_output.jsonl
make eval-anny-reconstruction --model-output manual_storyline_dir
make eval-piti-deck-plan --model-output manual_deck_dir
```

### Option B: jibi Daily Digest MVP 시작

사용자 가치가 가장 큼.

추천 순서:

```text
1. digest output schema 확정
2. 수동 URL/input 기반 jibi scoring pipeline
3. Markdown digest 생성
4. Google Sheet append
5. Slack posting/query
```

## 아직 하지 말 것

```text
- full RSS 24/7 collector
- Google Sheets API direct fetch 먼저 구현
- full PPT generator
- image auto collection
- production orchestration
```

먼저 작은 batch/digest를 만들고 업무에 붙여본 뒤 확장한다.
