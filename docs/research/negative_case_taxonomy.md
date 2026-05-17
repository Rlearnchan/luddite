# Negative / Non-Use Case Taxonomy

작성일: 2026-05-17  
상태: v0.9.3 draft

## 1. 목적

`jibi`는 좋은 후보만 배우면 안 된다. 실제 업무에서는 “제작할 만했지만 방송에서 밀린 소재”와
“애초에 버려야 할 소재”를 구분해야 한다.

## 2. Labels

### positive

실제 제작 및 방송 활용으로 이어진 후보.

### produced_but_rejected

제작할 만했지만 방송에서 사용되지 않았거나 밀린 후보.

중요:

```text
produced_but_rejected는 나쁜 소재가 아니다.
```

대체로 B/C grade가 적절하다.

### pending_or_unknown

제작 여부 또는 방송 활용 여부가 불확실한 후보. A로 단정하면 overconfident일 수 있다.

### rejected_or_not_pursued

제작하지 않았거나 seed 단계에서 약한 후보.

## 3. Failure Modes

| failure_mode | 설명 | 권장 action |
|---|---|---|
| `sub_item_only` | 이색적이지만 메인 분량 부족 | keep_for_later |
| `too_obvious_pattern` | 논쟁 구도가 너무 뻔함 | keep/reject |
| `single_company_frame` | 특정 기업 홍보/비판처럼 보임 | editorial_review/reject |
| `single_stock_investment_frame` | 투자 조언처럼 보임 | editorial_review/reject |
| `weak_structural_expansion` | 구조 문제로 커지지 않음 | keep/reject |
| `thin_evidence` | 근거/출처 부족 | gather_more_evidence |
| `sensitive_high_low_gain` | 위험은 큰데 방송 이득 낮음 | reject |
| `live_news_volatility` | 실시간 발언/속보라 검증 어려움 | editorial_review/reject |
| `political_direct_eval` | 국내 대통령/정당 직접 평가 | reject/blocked_policy |
| `recent_cooldown` | 최근 유사 주제 방송 | keep_for_later |
| `copyright_heavy` | 이미지/짤 의존 높음 | editorial_review |

## 4. produced_but_rejected Interpretation

예:

```text
알카트라즈 교도소 복원
- 이색 hook은 있으나 메인 확장성 약함
- keep_for_later가 적절

숏츠는 질병인가
- 생활/플랫폼 논쟁 가능
- 패턴이 뻔함
- 더 새로운 사례 필요

회사채 금리와 증자
- 구조는 좋음
- 특정 기업 사례가 너무 강하면 위험
```

## 5. Hard Reject vs Editorial Review

### hard reject

```text
국내 대통령/정당 직접 평가
근거 없는 의료/과학 충격 주장
특정 종목 투자 판단
출처 약한 선정적 소재
```

### editorial_review

```text
위험하지만 구조적 가치가 큰 소재
범죄/마약이지만 산업/시장/제도 이야기로 확장 가능
해외 정치가 경제/사회 구조로 연결
의료/과학 주제이나 공식자료로 검증 가능
```

## 6. jibi Scoring Use

`failure_mode`를 candidate에 붙이면 action이 좋아진다.

```json
{
  "failure_modes": ["single_company_frame", "thin_evidence"],
  "recommended_action": "gather_more_evidence"
}
```

## 7. Rule of Thumb

```text
위험하지만 좋다 → editorial_review
좋지만 근거 부족 → gather_more_evidence
재미있지만 서브급 → keep_for_later
위험하고 약하다 → reject
정책상 금지 → blocked_policy/reject
```
