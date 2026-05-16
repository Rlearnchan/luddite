# 04. anny Storyline Playbook

작성일: 2026-05-16
상태: v0.1 draft

## 1. 역할 정의

`anny`는 기사 요약기가 아니라 **방송용 storyline 작가**다. `jibi`가 찾은 seed를 받아, 슈카월드식 3~4단 구성으로 풀고, 각 줄을 PPT 슬라이드로 옮길 수 있는 형태로 만든다.

## 2. anny의 기본 출력

`anny`는 두 종류의 산출물을 만든다.

### 2.1 Morning Brief

아침 뉴스레터 형식. 후보 3~5개를 사람이 빠르게 고를 수 있게 정리한다.

```text
- 오늘의 seed
- 왜 슈카월드감인가
- 3~4단 예상 구성
- 필요한 추가자료
- 리스크
- 예상 슬라이드 수
```

### 2.2 Slide-ready Storyline

선택된 후보 하나를 PPT로 옮길 수 있는 구조로 변환한다.

```text
section → slide → headline/body/source/notes
```

## 3. 기본 storyline 공식

```text
1. Hook: 엥? 하는 seed
2. Proof: 숫자/사건으로 seed의 중요성 증명
3. Translation: 시청자 배경지식 만들기
4. Expansion: 산업/정치/사회 구조로 확장
5. Bridge: 한국/내부/밈/시청자 체감 연결
6. Question: 마지막 질문 또는 찝찝한 결론
```

## 4. Section 구성 원칙

슈카월드 자료는 보통 3~4단으로 호흡을 나눈다.

### 4.1 중형 50~60장 구성

예: `전당포 주식회사`, `코카콜라를 이기는 방법`

```text
Section 1. 이상한 seed 소개
Section 2. 시청자 배경지식
Section 3. 구조적 확장
Section 4. 사람/리스크/회수
```

### 4.2 생활형 70~80장 구성

예: `슈승님의 은혜`, `여름에 회사에서 반바지 입어도 되나요`

```text
Section 1. 체감/내부 hook
Section 2. 기사로 확인되는 변화
Section 3. 해외/제도/문화 확장
Section 4. 한국/회사 내부 회수
```

### 4.3 대형 90~110장 구성

예: `국민도 주주가 되는가`, `대혼돈의 영국`, `미중 정상회담`

```text
Section 1. 시장/정치 이벤트
Section 2. 원문/결과 분해
Section 3. 구조적 배경
Section 4. 이해관계자/수혜자/리스크
Section 5. 마지막 질문
```

## 5. Slide-level 작성 규칙

각 슬라이드는 다음 조건을 만족해야 한다.

- headline은 하나의 메시지만 담는다.
- body는 1~4개 bullet 또는 짧은 문단으로 제한한다.
- 긴 원문 인용은 여러 슬라이드로 나눈다.
- 주장에는 source가 붙어야 한다.
- source는 본문과 분리해 `speaker_notes`에 넣는다.
- 사실 검증이 필요한 문장은 표시한다.

### 5.1 좋은 headline

```text
최근 상장에 도전하는 금융 회사가 있다
문제는 이 회사가 바로 “전당포”라는 점이다
베트남에서 오토바이는 단순 교통수단 이상인데요?
그건 자산 가격에 관한 얘기였고, 이번엔 “체제 전환”을 다룬다
```

### 5.2 나쁜 headline

```text
F88에 대한 설명
영국 정치 상황 요약
자료 조사 내용
추가 내용
```

나쁜 이유: 방송에서 말할 문장이 아니라 문서 목차에 가깝다.

## 6. Storyline JSON schema 초안

```json
{
  "storyline_id": "pawn_company_f88_20260517",
  "title": "전당포 주식회사",
  "subtitle": "상장에 도전하는 베트남 전당포",
  "one_liner": "베트남 전당포 F88의 상장 추진을 통해 신흥국 신용시장의 빈틈을 설명한다.",
  "archetypes": ["company_as_window", "foreign_oddity"],
  "estimated_slide_count": 55,
  "sections": [
    {
      "section_no": 1,
      "section_title": "상장에 도전하는 베트남 전당포",
      "section_intent": "hook_and_proof",
      "slides": [
        {
          "slide_no": 1,
          "slide_type": "title",
          "headline": "전당포 주식회사",
          "body": ["상장에 도전하는 베트남 전당포"],
          "source_urls": [],
          "image_urls": [],
          "speaker_notes": "",
          "needs_fact_check": false
        }
      ]
    }
  ],
  "risk_flags": [],
  "open_questions": []
}
```

## 7. Source handling

anny는 각 슬라이드에 source를 분리해서 기록한다.

```text
speaker_notes:
[내용] https://...
[내용 2] https://...
[이미지] https://...
```

규칙:

- 본문에 URL을 노출하지 않는 것을 기본으로 한다.
- notes에 URL을 남긴다.
- `GPT 생성` 이미지는 `[이미지] GPT 생성`으로 기록한다.
- 기사 원문 장문을 그대로 넣지 않고, 필요한 짧은 문장만 인용한다.

## 8. Fact-check handling

anny는 확신이 낮거나 추가 확인이 필요한 내용에 표시한다.

```json
{
  "headline": "한국에서도 비슷한 일이 있었을까?",
  "body": [],
  "needs_fact_check": true,
  "research_task": "한국 전당포 이용 감소와 대체 금융수단 자료 찾기",
  "source_urls": []
}
```

`needs_fact_check=true`인 슬라이드는 `piti`가 최종 PPT에 넣되, 표시 또는 TODO notes를 남긴다.

## 9. Storyline archetype별 작성법

### 9.1 `company_as_window`

```text
회사 소개
→ 성장 숫자
→ 왜 이 회사가 이상한지
→ 산업/국가 구조
→ 리스크
```

### 9.2 `foreign_oddity_to_industry`

```text
이상한 해외 사건
→ 사건 배경
→ 돈/권력/기업 등장
→ 산업 전략
→ 처음 소재로 회수
```

### 9.3 `policy_text_decomposition`

```text
시장 반응
→ 발언자/원문 소개
→ 원문 문장별 해석
→ 오해와 실제 의도 분리
→ 투자자/국민 관점 질문
```

### 9.4 `cost_inversion_tech`

```text
비용 비대칭 제시
→ 기존 대응의 한계
→ 신기술 후보
→ 각국 경쟁
→ 한국 연결
→ 제목 말장난 회수
```

### 9.5 `life_culture_shift`

```text
생활 체감
→ 기사로 확인
→ 해외 사례
→ 제도/문화 변화
→ 한국/회사 내부 회수
```

## 10. anny가 피해야 할 것

- 기사 내용을 순서대로 요약하기
- 모든 자료를 같은 비중으로 나열하기
- 출처 없이 단정하기
- 한국 연결을 억지로 붙이기
- 마지막 결론을 투자 조언처럼 쓰기
- 너무 많은 정보를 한 슬라이드에 넣기
- 제목만 재밌고 본문 구조가 없는 구성

## 11. anny MVP acceptance criteria

- `jibi_candidate` 하나를 입력받아 3개 이상 section을 생성한다.
- 각 section은 5개 이상의 slide draft를 가진다.
- 각 slide는 headline/body/source_urls/notes를 가진다.
- 최소 70% 이상의 factual slide에 source가 있다.
- `needs_fact_check`와 `risk_flags`를 생성한다.
- 예상 slide count가 주제 유형에 맞게 제안된다.
