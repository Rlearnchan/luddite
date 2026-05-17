# BDC Mode Design

작성일: 2026-05-17  
상태: design draft

## 1. 목적

BDC는 일반 슈카월드 방송과 문법이 다르다. 당장 MVP 구현 대상은 아니지만,
schema와 prompt 설계에서 완전히 제외하면 나중에 붙이기 어렵다.

따라서 mode를 열어둔다.

```text
mode: normal | bdc
```

## 2. 일반 방송 vs BDC

| 항목 | 일반 방송 | BDC |
|---|---|---|
| 핵심 목표 | 시청자 흥미/구조 설명 | 산업 이슈에서 광고주 소구로 자연스럽게 연결 |
| 도입 | 강한 seed/hook | 광고주와 무관해 보이는 큰 산업/사회 이슈 |
| 중반 | 배경/구조/숫자 | 광고주 서비스가 등장할 수밖에 없는 맥락 |
| 후반 | 질문/리스크/punchline | 서비스 설명/소구 포인트 |
| 리스크 | 사실/저작권/민감도 | 법무/브랜드/광고 심의/과장 |
| 사람이 봐야 할 것 | 팩트/톤 | 광고주 의도/소구/과장 여부 |

## 3. BDC Storyline Pattern

```text
1. 일반적인 산업/사회 변화
2. 기존 방식의 불편/비효율/리스크
3. 새로운 서비스/기술이 필요한 이유
4. 광고주 서비스 등장
5. 구체적 기능/장점/주의사항
6. 일반 방송 톤으로 마무리
```

## 4. BDC jibi Candidate

BDC 후보는 일반 candidate와 다르게 표시한다.

```json
{
  "mode": "bdc",
  "advertiser": "...",
  "brand_safety_risk": "medium",
  "sponsor_claims_need_verification": true,
  "industry_bridge": "...",
  "service_bridge": "..."
}
```

## 5. BDC Risk Flags

```text
bdc_conflict
brand_safety_risk
advertiser_claim_risk
legal_review_needed
overly_promotional
```

## 6. What Not to Automate

```text
- 광고주 주장 검증 없이 단정
- 광고주 소구를 너무 숨겨서 기만적 구조 만들기
- 과장된 수익/효과 표현
- 법무/브랜드 리뷰 생략
```

## 7. Implementation Timing

MVP:

```text
normal mode only
```

Design:

```text
schema/prompt에 mode field는 남김
```

Later:

```text
BDC-specific storyline playbook
BDC-specific eval fixture
BDC-specific risk checker
```
