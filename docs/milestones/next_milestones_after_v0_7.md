# Next Milestones after v0.7

## 1. 기존 추천의 수정

이전 추천은 `Manual LLM Dry Run`을 다음 단계로 두었다. 사용자 답변 기준으로는 여전히 유효하지만, 가장 중요한 장기 방향은 `jibi MVP`다.

따라서 다음 순서를 권장한다.

```text
Milestone 0.8: Manual LLM Dry Run
Milestone 0.9: jibi Daily Digest MVP
Milestone 1.0: Google Sheet / Slack output integration
Milestone 1.1: anny DB-based Storyline MVP
Milestone 1.2: syuka-ops similarity/performance bridge
Milestone 1.3: piti renderer MVP
```

## 2. Milestone 0.8: Manual LLM Dry Run

목표:

```text
실제 API/agent 없이 GPT Pro 수동 output을 model-output JSON으로 저장해 eval runner에 넣어본다.
```

범위:

```text
- jibi 6개 후보 평가
- anny pawnshop_f88 storyline 생성
- piti pawnshop_f88 deck plan 생성
```

이 단계는 prompt/schema/eval이 실제 모델 output을 잘 받는지 확인하는 smoke test다.

## 3. Milestone 0.9: jibi Daily Digest MVP

목표:

```text
매일 수집하고, 평일 아침 리서치팀이 볼 후보 10개 digest 생성.
```

첫 실사용 목표는 PPT 자동 제작이 아니라 리서치 주제 선별 보조다.

처음에는 production-grade RSS/24시간 collector가 없어도 된다.

입력 후보 source:

```text
- 수동 URL 목록
- Google Sheet 주제 찾기 미처리 row
- curated RSS subset
- 해외 주요 매체 RSS/검색 결과 일부
```

출력:

```text
- Markdown report
- Google Sheet append 준비
- Slack bot 연동 준비
```

## 4. Milestone 1.0: Google Sheet / Slack Output Integration

목표:

```text
jibi 후보를 실제 업무 공간에 붙인다.
```

Google Sheet:

```text
- 후보 row append
- source 또는 작성자 필드에 jibi 표시
- bot row 시각적 구분
- 사람 row overwrite 금지
- status update는 별도 설계
```

Slack:

```text
- Luddite 전용 bot
- /luddite today
- /luddite search <keyword>
- /luddite candidate <candidate_id>
- /luddite help
```

`syuka-ops`는 과거 영상/자막/메타데이터 검색용으로 두고, `Luddite`는 미래 후보 발굴/주제 선별/스토리라인 요청용 별도 bot으로 시작한다.

## 5. Milestone 1.1: anny DB-based Storyline MVP

목표:

```text
선택된 candidate 하나가 아니라, DB에 쌓인 관련 후보/evidence를 묶어 3~4단 storyline을 만든다.
```

핵심:

```text
- evidence cluster builder
- related item retrieval
- storyline Markdown + JSON
```

## 6. Milestone 1.2: syuka-ops Bridge

목표:

```text
과거 YouTube final title/view/transcript와 Luddite seed/storyline/PPT를 연결한다.
```

기대효과:

```text
- 조회수 proxy 개선
- 기존 래퍼토리 감지
- 비슷한 과거 영상 링크 제공
- final title 변환 학습
```

## 7. Milestone 1.3: piti Renderer MVP

목표:

```text
deck_plan -> PPTX 초안
```

핵심:

```text
- format fidelity
- speaker notes
- source/image separation
- image placeholder
```
