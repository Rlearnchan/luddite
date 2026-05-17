# piti Roadmap / Renderer Spec

## 1. 역할 재정의

`piti`는 단기 1순위가 아니다. 하지만 장기적으로는 슈카월드 포맷이 고정적이므로 renderer fidelity가 중요하다.

사용자 기대:

```text
- 첫 목표: 텍스트와 notes가 제대로 들어간 초안
- 디자인 자동화: 가능하면 포맷을 정확히 맞추는 것이 중요
- speaker notes: 매우 중요, 출처 관리의 핵심
```

## 2. 초기 산출물

MVP:

```text
- PPTX 초안 또는 Google Slides 초안
- slide text
- speaker notes
- image placeholder
- 16:9 + 큰 글씨 + 기본 포맷
```

가장 중요한 것은 `예쁜 디자인`보다 다음이다.

```text
- notes 보존
- source/image 분리
- 슬라이드당 한 메시지
- 포맷 일관성
```

## 3. PPTX vs Google Slides

사용자 선호:

```text
공유는 Google Slides가 편하지만,
포맷 맞추기가 어렵다면 로컬 PPTX로 시작해도 됨.
```

추천 구현 순서:

```text
1. PPTX renderer 먼저
2. Drive 업로드/공유
3. 필요하면 Google Slides 변환 또는 API 조작
```

이유:

```text
- python-pptx/PPTX XML로 notes와 layout 제어가 상대적으로 명확함
- Google Slides는 공유는 편하지만 Office file/Slides API 변환 이슈가 있음
```

## 4. 이미지 처리

단기:

```text
- 실제 이미지는 사람이 선택
- GPT는 image prompt 또는 placeholder만 제안
- 기사 캡처 placeholder 가능
- image source는 notes에 유지
```

장기:

```text
- AI 생성 이미지 prompt 자동 제안
- 저작권-safe 이미지 후보 관리
- SNS/기사 캡처 시 익명화 필요 표시
```

## 5. format extraction 필요

과거/최신 PPT에서 추출해야 할 포맷 요소:

```text
- slide size
- font family/size
- title 위치
- body 위치
- section title layout
- quote slide layout
- data slide layout
- image placeholder layout
- notes convention
```

최신 PPT에서 확인된 notes 관습은 계속 유지해야 한다. 예: `전당포 주식회사`에는 slide별 `[내용]`, `[이미지]` 출처가 남아 있어 대표님이 원문 확인에 활용할 수 있다.

## 6. renderer MVP acceptance

```text
- deck_plan JSON을 받아 PPTX 생성
- slide_no 순서 유지
- headline/body 표시
- speaker notes에 [내용]/[이미지] 삽입
- image placeholder 생성
- source_urls/image_urls overlap 없음
- 사람이 열어 바로 수정 가능
```
