# 00. Luddite Project Charter

작성일: 2026-05-16
상태: v0.1 draft

## 1. 프로젝트 정의

**Luddite**는 슈카월드 리서치 업무를 보조하기 위한 에이전트 시스템이다. 목표는 리서처를 대체하는 것이 아니라, 반복적인 자료 수집·초안화·PPT 초안화 과정을 줄이고, 리서처가 더 빨리 좋은 판단을 하도록 돕는 것이다.

Luddite는 세 개의 이름 붙은 구성요소로 나뉜다.

| 이름 | 역할 | 핵심 산출물 |
|---|---|---|
| `jibi` | 국내외 언론·자료를 훑고 “슈카월드감” seed를 수집·선별 | `jibi_candidate`, daily digest |
| `anny` | `jibi` 후보와 기존 자료를 바탕으로 방송용 story outline 작성 | `anny_storyline` |
| `piti` | `anny`의 storyline을 슈카월드식 PPT 초안으로 변환 | `piti_deck_plan`, `.pptx` |

## 2. 한 줄 목표

> “많이 나온 뉴스”가 아니라 “방송으로 살아날 수 있는 이상한 seed”를 찾고, 이를 “슈카월드식 3~4단 구조”로 풀어, 출처 notes가 포함된 PPT 초안까지 만든다.

## 3. 세부 목표

### 3.1 jibi

- 주요 통신사, 국내 경제지, 해외 유력 매체, 공식자료, RSS를 주기적으로 확인한다.
- 기사 하나를 단순 저장하지 않고, 방송 확장 가능성을 평가한다.
- 후보별로 `why_shuka`, `possible_expansions`, `korea_bridge`, `punchline_candidate`, `risk_flags`를 기록한다.
- 매일 아침 사람이 훑을 수 있는 digest를 만든다.

### 3.2 anny

- 기사 요약이 아니라 방송용 storyline을 만든다.
- 기본 구조는 `엥? 하는 seed → 숫자/사건 증명 → 배경 설명 → 구조적 확장 → 한국/내부/밈 회수 → 마지막 질문`이다.
- 각 슬라이드 후보마다 headline, body, source_urls, image_urls, notes를 분리한다.
- 근거가 부족한 슬라이드는 `needs_fact_check`로 표시한다.

### 3.3 piti

- 16:9 PPTX 초안을 생성한다.
- 한 장에 한 메시지를 원칙으로 한다.
- 슬라이드별 speaker notes에 `[내용]`, `[이미지]` 출처를 넣는다.
- 이미지·차트는 첫 버전에서 placeholder로 둬도 된다.
- 최종 산출물은 사람이 쉽게 수정할 수 있어야 한다.

## 4. 비목표

Luddite의 초기 버전은 다음을 목표로 하지 않는다.

- 사람 검토 없이 방송 가능한 완성본 자동 제작
- 구독 매체 기사 전문의 장문 복사·저장
- 저작권 위험 이미지를 자동으로 방송용 이미지로 채택
- 민감정보가 들어간 내부 시트 전체를 LLM에 그대로 투입
- 정치·기업·의료·법률 고위험 이슈에 대한 무검증 단정
- 모든 Google Drive 자료의 전수 분석을 매번 수행

## 5. 성공 기준

### MVP 기준

- `storyline.zip`의 RTF 파일을 text/jsonl로 변환할 수 있다.
- 최신 PPT 8개에서 slide text, notes, URL, image source를 추출할 수 있다.
- Google Sheet `주제 찾기`를 읽고 후보 예시/미사용 이유를 가져올 수 있다.
- `jibi_candidate → anny_storyline → piti_deck_plan`의 JSON 계약이 동작한다.
- `전당포 주식회사` 또는 `코카콜라를 이기는 방법` 수준의 40~60장 draft deck을 생성할 수 있다.

### 실사용 기준

- 아침에 후보 10개 이내 digest를 낸다.
- 후보별로 “왜 슈카월드감인지”를 한 문단으로 설명한다.
- 사람이 선택한 후보 하나에 대해 3~4단 story outline을 생성한다.
- 생성된 PPT 초안은 출처 notes가 붙어 있고, 사람이 1차 편집 가능한 수준이다.

## 6. 사람의 역할

Luddite가 자동화하더라도 사람은 반드시 다음을 수행한다.

- seed 최종 선택
- 민감 주제 판단
- 주요 사실 검증
- 제목과 punchline 조정
- 이미지·캡처 저작권 검토
- 최종 방송 여부 판단

## 7. 우선순위

1. Parser와 corpus manifest 구축
2. 최신 PPT 8개와 storyline 43개에서 문법 추출
3. jibi 후보 스키마와 scoring prompt 구현
4. anny storyline schema 구현
5. piti PPT 초안 생성 구현
6. 평가셋과 regression test 구축

## 8. 핵심 철학

Luddite는 “정답 쓰는 AI”가 아니라 “리서처가 더 빨리 좋은 질문을 찾게 하는 도구”다. 슈카월드 콘텐츠의 핵심은 정답보다 **문제제기**, **전개**, **비유**, **한국식 회수**, **출처 관리**에 있다.
