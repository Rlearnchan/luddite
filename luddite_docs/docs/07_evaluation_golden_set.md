# 07. Evaluation & Golden Set

작성일: 2026-05-16
상태: v0.1 draft

## 1. 목적

Luddite는 감각이 중요한 시스템이다. 평가 기준 없이 구현하면 “그럴듯한 요약”은 만들지만 “방송용 storyline”은 만들지 못할 수 있다. 이 문서는 agent별 평가 기준과 golden set을 정의한다.

## 2. Golden set v0.1

최신 `20260517 방송용 (직원)` 폴더의 8개 PPT를 1차 golden set으로 사용한다.

| 그룹 | 파일 | 용도 |
|---|---|---|
| MVP 중형 | `전당포 주식회사_배형찬.pptx` | 구조가 선명한 55장 샘플 |
| MVP 중형 | `코카콜라를 이기는 방법_김성원.pptx` | A→B 전환형 샘플 |
| 생활형 | `슈승님의 은혜_김동찬.pptx` | 내부 밈→사회 변화 |
| 생활형 | `여름에 회사에서 반바지 입어도 되나요_김동찬.pptx` | 체감 이슈→직장문화 |
| 기술/말장난 | `요즘 뜨는 레이저 치료_김동찬.pptx` | 방산→한국→말장난 회수 |
| 대형 정책 | `국민도 주주가 되는가_배형찬.pptx` | 정책 원문 분해형 |
| 대형 정치 | `대혼돈의 영국_김동찬 김성원.pptx` | 정치체제 균열형 |
| 대형 지정학 | `미중 정상회담_김동찬.pptx` | 이벤트 프리퀄형 |

## 3. jibi 평가

### 3.1 평가 항목

| 항목 | 질문 | 점수 |
|---|---|---:|
| seed novelty | 흔한 뉴스가 아니라 새 조합인가? | 1~5 |
| hook strength | 제목만으로 “엥?”이 생기는가? | 1~5 |
| expandability | 3~4단 구조로 확장 가능한가? | 1~5 |
| evidence depth | 공식자료/통계/후속자료를 붙일 수 있는가? | 1~5 |
| korea bridge | 한국 시청자에게 번역 가능한가? | 1~5 |
| risk awareness | 위험 플래그를 잘 잡았는가? | 1~5 |
| digest usefulness | 사람이 바로 고를 수 있게 정리했는가? | 1~5 |

### 3.2 합격 기준

- 평균 4점 이상: strong candidate
- 평균 3점 이상: 검토 후보
- 평균 3점 미만: discard 또는 추가 수집

## 4. anny 평가

### 4.1 평가 항목

| 항목 | 질문 | 점수 |
|---|---|---:|
| structure | 3~4단 구성이 자연스러운가? | 1~5 |
| slide-readiness | PPT로 바로 옮길 headline인가? | 1~5 |
| source discipline | 각 주장에 source가 붙는가? | 1~5 |
| narrative rhythm | hook/배경/확장/회수의 리듬이 있는가? | 1~5 |
| korea bridge | 한국 연결이 자연스러운가? | 1~5 |
| ending | 질문/찝찝함/농담으로 잘 닫히는가? | 1~5 |
| risk handling | 근거 부족/민감 이슈를 표시하는가? | 1~5 |

### 4.2 실패 패턴

- 기사 요약 나열
- section title이 목차처럼 딱딱함
- headline이 방송 문장이 아님
- source가 섹션 마지막에만 몰림
- 한국 연결이 없거나 억지
- 결론이 투자 조언/정치 주장처럼 보임

## 5. piti 평가

### 5.1 평가 항목

| 항목 | 질문 | 점수 |
|---|---|---:|
| one-message-per-slide | 한 장에 한 메시지인가? | 1~5 |
| readable density | 28pt 기준으로 읽을 수 있는가? | 1~5 |
| source notes | speaker notes 출처가 있는가? | 1~5 |
| slide type fit | slide type과 layout이 맞는가? | 1~5 |
| editability | 사람이 수정하기 쉬운가? | 1~5 |
| section rhythm | 장 전환이 자연스러운가? | 1~5 |
| TODO reporting | 이미지/검증 TODO가 명확한가? | 1~5 |

### 5.2 자동 체크

- 총 slide 수
- notes 없는 slide 수
- source URL 수
- image placeholder 수
- body line 5줄 초과 slide 수
- headline 50자 초과 slide 수
- section title 수

## 6. Regression test

구현 후 매번 아래 테스트를 돌린다.

```text
1. parse_latest_ppts_test
   - 8개 PPT slide count가 기존 metrics와 ±1 이내인지
   - URL count가 기존 metrics와 크게 벗어나지 않는지

2. storyline_schema_test
   - generated storyline이 JSON Schema를 통과하는지

3. deck_plan_schema_test
   - piti deck plan이 JSON Schema를 통과하는지

4. source_notes_test
   - factual slide 중 source 누락 비율이 threshold 이하인지

5. golden_case_generation_test
   - 전당포/F88 seed로 40~70장 deck plan 생성 가능한지
```

## 7. Human review form

사람 검토자는 생성 결과마다 아래를 체크한다.

```text
- 이 seed를 실제로 보고 싶은가? Y/N
- 방송용 전개가 보이는가? 1~5
- 너무 요약문 같은가? 1~5
- 근거가 충분한가? 1~5
- 위험한 표현이 있는가? Y/N
- 가장 좋은 slide headline 3개
- 가장 어색한 slide headline 3개
- 사람이 고쳐야 할 부분
```

## 8. 초기 목표 점수

MVP에서는 완벽한 점수를 목표로 하지 않는다.

| Agent | MVP 목표 |
|---|---:|
| jibi | 좋은 후보 10개 중 사람이 2~3개 고를 수 있음 |
| anny | 선택 후보 1개에 대해 60% 이상 쓸만한 outline 생성 |
| piti | 사람이 편집 가능한 source notes 포함 PPT 초안 생성 |

## 9. Golden cases JSON

각 golden case는 `eval/golden_cases/*.json`으로 저장한다.

필드:

```json
{
  "case_id": "pawn_company_f88",
  "source_ppt": "전당포 주식회사_배형찬.pptx",
  "archetypes": ["company_as_window", "foreign_oddity"],
  "target_slide_count_range": [45, 65],
  "must_have_sections": ["상장", "전당포 이미지", "베트남 신용시장", "리스크"],
  "must_have_sources": ["seed article", "official/statistical source"],
  "evaluation_notes": "MVP reference case"
}
```
