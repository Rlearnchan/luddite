# Storyline Pattern Catalog v0.2

작성일: 2026-05-17  
근거 자료: `data/storylines/parsed_storylines.jsonl`

## 1. 상태 요약

RTF storyline 43개가 모두 파싱되었다.

- 파일 수: 43
- URL 총합: 655
- URL 평균: 15.23
- URL 중앙값: 14
- URL 0개 파일: 1
- estimated section 평균: 3.28
- keyword-based Korea bridge: 25/43
- keyword-based punchline hint: 42/43

주의: `has_korea_bridge`, `has_punchline_hint`, `estimated_sections`는 smoke heuristic이다. editorial judgment로 직접 쓰면 안 된다.

## 2. URL 밀도 상위 storyline

|파일|URL|섹션|제목|
|---|---|---|---|
|관세와 가뭄으로 미국 소고기 가격 사상 최고 기록.rtf|45|7|관세와 가뭄으로 미국 소고기 가격 사상 최고 기록|
|민원 우려로 축구도 금지된 요즘 학교.rtf|38|5|민원 우려로 축구도 금지된 요즘 학교|
|무제 24.rtf|32|3|1. 그록의 머스크 VS GPT의 알트먼|
|백인 우월주의인가, 단순한 광고인가?.rtf|29|3|백인 우월주의인가, 단순한 광고인가?|
|무제 13.rtf|28|5|1. 크게 증가한 외국인 노동력|
|소득은 높지만, 부자가 될 수는 없다..rtf|27|4|소득은 높지만, 부자가 될 수는 없다.|
|무제 28.rtf|26|6|1. 다시 수출계의 슈퍼 루키로 떠오른 선박 업계와 그렇지 못한 문제아 석유화학 업계의 근황|
|무제 30.rtf|23|5|1. 트럼프 리스크까지 떠앉게 된 인텔 근황|
|다시 떠오르는 한일 경제공동체 담론.rtf|22|4|다시 떠오르는 한일 경제공동체 담론|
|무제 15.rtf|22|0|삼성 파운드리 부활 신호탄 쐈다… 테슬라와 22조 초대형 계약|


URL이 많다는 것은 evidence depth가 높다는 뜻이지만, 곧바로 방송 적합성을 의미하지는 않는다. `관세와 가뭄으로 미국 소고기 가격`처럼 숫자와 공급망/가격 전이가 붙는 주제는 강하지만, 너무 많은 자료가 한 storyline에 섞이면 `anny`가 3~4단으로 압축하는 작업이 필요하다.

## 3. URL 0개 storyline

|파일|URL|섹션|제목|
|---|---|---|---|
|무제 7.rtf|0|3|1. 2025년 6월 한국인이 가장 많이 사용하는 AI 챗봇은 ChatGPT가 아닌 제타|


URL 0개 파일은 곧바로 사용하지 말고, `anny`가 missing evidence task를 생성해야 한다.

## 4. storyline seed archetype 초안

### 4.1 생활/사회 변화형

예시:
- `'야근한 만큼 돈 줘라', 포괄임금 오남용방지 지침 발표`
- `분명 근로시간이 대폭 줄고 있는데도 수면 부족은 여전한 한국인들`
- `민원 우려로 축구도 금지된 요즘 학교`
- `소득은 높지만, 부자가 될 수는 없다`

문법:
```text
제도/생활 변화 → 개인 체감 → 과거와 비교 → 한국식 자조/질문
```

### 4.2 가격/공급망 충격형

예시:
- `관세와 가뭄으로 미국 소고기 가격 사상 최고 기록`
- `가공식품 관련주의 위기`
- `중국 돼지고기 가격 폭락의 비밀`
- `급증하는 전력 수요, 호황을 맞은 전력산업`

문법:
```text
가격 이상징후 → 원인 분해 → 산업/기업 영향 → 소비자 체감
```

### 4.3 정책/시장 충격형

예시:
- `대주주요건 10억으로 확대, 2025 세제 개편안`
- `늘어나는 재정 지출, 개선안은 있나`
- `트럼프 전세계 관세`
- `트럼프 "관세 환급 신청하지 않으면 내 편"`

문법:
```text
정책 발표 → 시장/사람 반응 → 원문 분해 → 의도와 부작용 질문
```

### 4.4 기술/AI/플랫폼형

예시:
- `모든 게시물 자동번역을 도입한 X`
- `그록의 머스크 VS GPT의 알트먼`
- `세계에서 가장 AI에 진심인 나라`
- `한국인이 가장 많이 사용하는 AI 챗봇은 ChatGPT가 아닌 제타`

문법:
```text
기술 변화 → 이상한 사용 사례 → 플랫폼/국가별 차이 → 한국식 회수
```

### 4.5 동물/과학/낭만형

예시:
- `티라노사우루스의 비밀`
- `침팬지들은 왜 어제의 동료를 죽였을까`
- `많은 미국인들은 가장 좋아하는 공룡이 없다`
- `중국 돼지고기 가격 폭락의 비밀`

문법:
```text
낭만/동물 hook → 과학/산업/통계 → 인간 사회와 연결
```

### 4.6 기업/산업 턴어라운드형

예시:
- `삼성 파운드리 부활 신호탄`
- `인텔 근황`
- `죽은 기업도 살리는 반도체 붐`
- `LG전자 희망퇴직`

문법:
```text
기업 이벤트 → 산업 구조 변화 → 숫자/시장 반응 → 홍보/비판 리스크 관리
```

## 5. anny 구현 시사점

1. RTF는 완성 슬라이드가 아니라 사고 과정이다. 그대로 PPT화하면 밀도가 과하다.
2. `anny`는 먼저 seed archetype을 고르고, 그다음 3~4개 section으로 압축해야 한다.
3. URL 많은 storyline은 evidence cluster로 분해하고, 핵심 seed URL과 보조 URL을 나눠야 한다.
4. URL 0개 또는 section 0개 파일은 `needs_fact_check`와 `missing_evidence`를 반드시 생성해야 한다.
5. parser의 keyword flags는 자동 판정이 아니라 prompt 입력용 hint로만 사용한다.

## 6. 권장 anny storyline schema 보강

각 storyline record에 사람이 보강할 필드:

```json
{
  "seed_type": "life_change | price_shock | policy_market | tech_platform | animal_science | industry_turnaround",
  "hook": "...",
  "core_question": "...",
  "section_plan": ["...", "...", "..."],
  "korea_bridge": "...",
  "punchline_or_closing": "...",
  "evidence_gaps": ["..."],
  "risk_notes": ["..."]
}
```

## 7. 다음 작업

- 상위 10개 storyline을 사람이 읽고 seed_type / hook / core_question을 수동 라벨링
- `전당포 주식회사`, `코카콜라를 이기는 방법` PPT와 유사한 storyline을 매칭해 “storyline → PPT” 변환 예시 만들기
- `anny/storyline_writer.md` prompt에 “URL 많은 storyline 압축 규칙” 추가
