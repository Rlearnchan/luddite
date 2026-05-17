# v0.8 Design Checkpoint

작성일: 2026-05-17
상태: design alignment draft

## 1. 현재 기술 상태

Codex 쪽은 v0.7 eval harness까지 완료했다.

완료된 축:

```text
jibi  -> seed scoring eval runner
anny  -> reconstruction eval runner
piti  -> deck plan eval runner
```

아직 하지 않은 것:

```text
- 실제 LLM API 호출
- jibi/anny/piti agent 본구현
- RSS 24/7 collector
- Google Sheets API direct fetch
- full PPT generator
- image auto collection
```

## 2. 사용자 답변으로 바뀐 핵심 방향

초기 구상은 `jibi -> anny -> piti` 전체 자동화였지만, 실제 업무상 단기 가치는 `jibi`에 가장 크다.

사용자 기준 1차 목표:

```text
매일 아침 또는 조회 시점에,
리서치팀이 클릭해보고 싶은 방송 후보 10개를 던져주는 도구.
```

즉 첫 데모는 PPT 생성이 아니다.

첫 데모 목표:

```text
월~금 아침 후보 digest
-> Google Sheet에 후보 적재
-> Slack에서 조회 가능
-> 각 후보에 왜 슈카월드감인지, 왜 위험한지, 무엇을 더 찾아야 하는지 표시
```

## 3. agent별 재정의

### jibi

기존: 뉴스 수집/선별 agent  
수정: 리서치팀의 `주제 찾기` 시트에 들어갈 후보를 자동 제안하는 운영 agent.

가장 중요한 가치:

```text
- 사람이 실제 클릭해보고 싶다.
- 미사용/보류 이유가 납득된다.
- 좋은데 위험한 소재를 무리하게 밀지 않는다.
```

### anny

기존: 특정 seed를 storyline으로 변환  
수정: `jibi`가 적재한 후보 DB에서 seed/evidence를 연결해 3~4단 storyline outline을 제안.

중요 출력:

```text
- Markdown outline
- 3~4단 구조
- slide-ready headline 후보
- 출처 링크
- needs_fact_check / needs_source
```

### piti

기존: 슈카월드 포맷 PPT 제작  
수정: 장기 목표. 다만 포맷 fidelity와 speaker notes 보존은 초반부터 설계에 반영.

MVP 기대:

```text
- 텍스트와 notes가 제대로 들어간 초안
- 16:9, 큰 글씨, 슈카월드 기본 포맷 반영
- image placeholder 중심
```

## 4. 운영 우선순위

```text
1. jibi daily digest MVP
2. Slack/Google Sheet output
3. manual LLM dry run, small all-agent sample
4. anny storyline MVP
5. syuka-ops 기반 성과/유사도 연결
6. piti renderer/PPTX 초안
7. RSS/Google Sheets API/Drive 자동화 확장
```

## 5. 절대 금지 원칙

가장 중요한 금지:

```text
- 그럴듯한데 출처 없는 말 만들기
- 민감한 주제를 무리하게 추천하기
```

이 둘은 일을 줄이는 게 아니라, 사람이 다시 검증하게 만들어 일을 두 배로 만든다.

기타 금지:

```text
- 내부 계정/광고주/미공개 주제/직원 관련 내부 정보 외부 노출
- 특정 정당/대통령 직접 평가 주제 추천
- 특정 기업 주식 추천처럼 보이는 표현
- 이미지 저작권 확정 판단
```
