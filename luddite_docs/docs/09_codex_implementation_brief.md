# 09. Codex Implementation Brief

작성일: 2026-05-16
상태: v0.1 draft

## 1. 구현 원칙

Codex는 먼저 문서와 schema를 읽고 구현한다. 목표는 “한 번에 완성된 AI 에이전트”가 아니라, **자료를 안정적으로 읽고, 중간 산출물을 명확히 남기는 파이프라인**을 만드는 것이다.

## 2. 추천 디렉토리 구조

```text
luddite/
  docs/
  specs/
  prompts/
  data/
    sheets/
    storylines/
    ppt/
    notion/
    manifests/
    candidates/
  src/
    luddite/
      collectors/
      parsers/
      scoring/
      agents/
      ppt/
      eval/
      utils/
  outputs/
    daily_digest/
    decks/
    reports/
  eval/
    golden_cases/
    reports/
  tests/
```

## 3. Phase A: Corpus parser

### A1. `parse_storylines.py`

입력:

```text
data/storylines/*.rtf 또는 *.txt
```

출력:

```text
data/storylines/parsed_storylines.jsonl
```

기능:

- RTF → plain text
- title normalization
- URL extraction
- URL canonicalization
- section 추정
- word/char count
- source count

### A2. `parse_pptx.py`

입력:

```text
data/ppt/*.pptx
```

출력:

```text
data/ppt/parsed_ppts.jsonl
```

기능:

- slide visible text 추출
- speaker notes 추출
- notes 내 URL 추출
- media count 추출
- slide type heuristic
- section title heuristic

주의:

- `python-pptx`는 notes 처리가 제한될 수 있다.
- 필요하면 PPTX zip 내부의 `ppt/notesSlides/*.xml`, `ppt/slides/*.xml`을 직접 파싱한다.

### A3. `fetch_sheets.py`

입력:

```text
Google Sheet ID
```

출력:

```text
data/sheets/*.csv
```

기능:

- 지정 탭 fetch
- redaction
- row normalization
- positive/negative label 추정

### A4. `build_corpus_manifest.py`

출력:

```text
data/manifests/corpus_manifest.jsonl
```

## 4. Phase B: jibi MVP

### B1. Collector

- RSS feed reader
- site fetcher
- source registry
- duplicate detection

### B2. Candidate normalizer

- article → `jibi_candidate`
- seed_type 추정
- summary 생성
- URL canonicalization

### B3. Scoring

- rule-based pre-score
- LLM-based explanation
- risk flag detection

### B4. Daily digest

출력:

```text
outputs/daily_digest/YYYY-MM-DD.md
```

내용:

- 후보 10개 이내
- score
- why_shuka
- 예상 전개
- 필요한 추가자료
- risk

## 5. Phase C: anny MVP

### C1. Evidence cluster builder

입력:

```text
jibi_candidate
```

출력:

```text
evidence_cluster
```

기능:

- seed URL 주변 근거 정리
- 공식자료 필요 여부 표시
- missing evidence 생성

### C2. Storyline generator

입력:

```text
jibi_candidate + evidence_cluster + reference grammar
```

출력:

```text
anny_storyline.json
```

기능:

- archetype 선택
- section 생성
- slide headline/body/source 생성
- needs_fact_check 표시

## 6. Phase D: piti MVP

### D1. Deck plan builder

입력:

```text
anny_storyline.json
```

출력:

```text
piti_deck_plan.json
```

### D2. PPTX generator

기능:

- title slide
- section title slide
- text slide
- quote slide
- image placeholder
- speaker notes writer

출력:

```text
outputs/decks/*.pptx
outputs/reports/*_generation_report.md
```

## 7. Phase E: Eval

### E1. Golden parser test

- 최신 PPT 8개 slide count 확인
- URL count 확인
- notes extraction 확인

### E2. Schema validation

- 모든 JSON 산출물 schema 검증

### E3. Agent output review

- jibi candidate score report
- anny storyline report
- piti deck generation report

## 8. 초기 구현 순서

권장 순서:

```text
1. specs/*.json 작성/검증
2. parse_storylines.py
3. parse_pptx.py
4. build_corpus_manifest.py
5. fetch_sheets.py + redaction
6. jibi_candidate 생성기
7. daily_digest renderer
8. anny_storyline generator stub
9. piti_deck_plan builder
10. pptx generator MVP
```

## 9. 첫 번째 테스트 케이스

`전당포 주식회사`를 첫 테스트로 사용한다.

이유:

- 55장 중형 자료
- 구조가 선명함
- seed, 배경, 확장, 리스크가 모두 있음
- 출처 notes가 풍부함
- MVP가 처리하기 적당함

두 번째 테스트는 `코카콜라를 이기는 방법`으로 한다.

이유:

- A로 시작해서 B로 전환하는 구조
- 이미지/이색 소재/기업 이야기 혼합
- punchline 회수 테스트에 적합

## 10. Acceptance criteria

### Parser

- 최신 PPT 8개 모두 parse 가능
- slide count metrics가 기존과 큰 차이 없음
- notes URL 추출 가능
- storyline 43개 text/jsonl 변환 가능

### jibi

- candidate JSON schema 통과
- 10개 이하 digest 생성
- risk flag 포함

### anny

- 3개 이상 section 생성
- slide-ready headline 생성
- source와 notes 분리

### piti

- PPTX 생성 가능
- speaker notes 삽입 가능
- generation report 생성
- 사람이 열고 편집 가능

## 11. Codex에게 주는 주의사항

- 내부 Sheet에서 credential을 읽어도 출력하지 말 것.
- 구현 로그에 raw 민감정보를 남기지 말 것.
- LLM prompt는 `docs/02~05`의 압축된 원칙을 사용하고, 전체 PPT 원문을 매번 넣지 말 것.
- schema를 먼저 통과시키고 agent 로직을 붙일 것.
- 실패한 parse도 조용히 버리지 말고 manifest에 기록할 것.
