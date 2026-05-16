# 05. piti PPT Production Spec

작성일: 2026-05-16
상태: v0.1 draft

## 1. 역할 정의

`piti`는 `anny`의 storyline을 슈카월드식 PPT 초안으로 옮기는 구성요소다. 첫 버전의 목표는 완성품이 아니라 **편집 가능한 draft deck**이다.

## 2. 기본 형식

최신 PPT 8개 기준으로 우선 적용할 형식:

| 항목 | 기본값 |
|---|---|
| 화면비 | 16:9 와이드 |
| 배경 | 흰색 중심 |
| 폰트 | 맑은 고딕 계열 |
| 본문 크기 | 28pt 중심 |
| 원칙 | 한 장에 한 메시지 |
| 출처 | speaker notes에 `[내용]`, `[이미지]` |
| 이미지 | placeholder 가능 |

## 3. Slide type taxonomy

`piti`는 모든 slide를 아래 type 중 하나로 처리한다.

| slide_type | 용도 |
|---|---|
| `title` | 자료 제목 |
| `section_title` | 장 전환 |
| `hook` | 첫 의문/이상징후 |
| `explainer` | 배경 설명 |
| `quote` | 원문 인용 |
| `data_point` | 숫자/통계 한 가지 |
| `comparison` | 전후/국가/기업 비교 |
| `timeline` | 시간 흐름 |
| `image_centered` | 사진/짤 중심 |
| `chart_placeholder` | 차트가 필요한 자리 |
| `punchline` | 농담/회수 |
| `closing_question` | 마지막 질문 |

## 4. Layout rules

### 4.1 General text slide

```text
headline: 상단 또는 중앙 큰 문장
body: headline 아래 1~4줄
notes: source URLs
```

규칙:

- headline은 가능한 1~2줄.
- body가 5줄을 넘으면 slide를 쪼갠다.
- 원문 영어와 번역을 같이 넣을 경우 quote slide를 사용한다.

### 4.2 Section title slide

```text
제목
- 부제
```

예:

```text
전당포 주식회사
- 한국의 전당포 이미지
```

### 4.3 Quote slide

구성:

- 위쪽: 해석 headline
- 중앙: 원문 또는 핵심 quote
- 아래: 번역/해설
- notes: 원문 URL

긴 quote는 여러 장으로 나눈다.

### 4.4 Data point slide

구성:

- headline: 숫자가 말하는 의미
- body: 숫자 1~3개
- image/chart placeholder: 선택

예:

```text
점포 수는 약 900개에 이를 정도로 급성장했으며
- 50개 미만 → 약 900개
```

### 4.5 Image-centered slide

- 이미지가 장면을 설명할 때 사용한다.
- 사람이 후처리할 수 있도록 placeholder를 넣는다.
- notes에 `[이미지]` 출처를 남긴다.

## 5. Speaker notes 규칙

가장 중요한 구현 요구사항이다.

### 5.1 notes format

```text
[내용] https://...
[내용 2] https://...
[이미지] https://...
[이미지 2] GPT 생성
[TODO] 캡처 필요
```

### 5.2 notes 작성 원칙

- 모든 factual claim은 가능한 source를 가진다.
- 이미지 출처는 내용 출처와 분리한다.
- GPT 생성 이미지는 반드시 `GPT 생성`으로 표시한다.
- source가 없는 slide는 `source_missing=true`로 기록한다.

## 6. anny → piti 입력 구조

`piti`는 `anny_storyline`의 각 slide object를 받아 처리한다.

```json
{
  "slide_no": 12,
  "slide_type": "explainer",
  "headline": "한국에선 골목길 사금융으로 오랫동안 성업한 전당포",
  "body": [
    "서민들의 급전 창구",
    "근대적 전당업은 조선 말기 이후",
    "1961년 전당포영업법 제정"
  ],
  "source_urls": ["https://..."],
  "image_urls": ["GPT 생성"],
  "speaker_notes": "[내용] https://...
[이미지] GPT 생성"
}
```

## 7. PPT generation output

```text
outputs/
  decks/
    pawn_company_f88_draft.pptx
  deck_plans/
    pawn_company_f88_deck_plan.json
  reports/
    pawn_company_f88_generation_report.md
```

Generation report에는 다음을 포함한다.

- 총 slide 수
- source 누락 slide 수
- image placeholder 수
- `needs_fact_check` slide 수
- unsupported slide type
- 사람이 확인해야 할 TODO

## 8. 이미지 처리

초기 MVP에서는 이미지 자동 삽입보다 placeholder를 우선한다.

| image_source | 처리 |
|---|---|
| 공식 이미지 URL | placeholder + notes |
| 기사 이미지 | 저작권 위험 flag |
| Wikipedia/Commons | placeholder + license 확인 TODO |
| GPT 생성 | `GPT 생성` notes |
| chart 필요 | chart_placeholder |
| SNS 캡처 | 계정 가림 TODO |

## 9. 사람이 후처리할 영역

`piti`는 다음을 사람이 수정할 것으로 가정한다.

- 기사 캡처 이미지
- 사진 crop
- 차트 디자인
- 장면용 밈 이미지
- 폰트 미세 조정
- 문장 리듬
- 최종 출처 검수

## 10. MVP slide templates

초기에는 아래 5개 template만 구현해도 된다.

```text
1. title
2. section_title
3. text_basic
4. quote_basic
5. image_placeholder
```

이후 추가:

```text
6. comparison_two_column
7. chart_placeholder
8. timeline
9. closing_question
```

## 11. Quality checklist

PPT 생성 후 자동 점검:

- [ ] 전체 slide count가 estimated range에 들어가는가?
- [ ] title slide가 있는가?
- [ ] section_title이 3개 이상 있는가?
- [ ] body가 5줄 넘는 slide가 있는가?
- [ ] notes 없는 factual slide가 있는가?
- [ ] URL canonicalization이 되었는가?
- [ ] GPT 생성 이미지가 표시되었는가?
- [ ] source_missing report가 생성되었는가?

## 12. 구현상 주의

- Google Slides API보다 `.pptx` 직접 생성/수정 방식을 우선한다.
- Office `.pptx`는 native Google presentation API가 실패할 수 있다.
- speaker notes는 PPTX 내부 notes slide XML에 들어가므로 별도 writer가 필요하다.
- `python-pptx`는 notes 지원이 제한될 수 있어, 필요하면 OOXML 직접 패치를 고려한다.
