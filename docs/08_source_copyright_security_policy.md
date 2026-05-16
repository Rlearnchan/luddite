# 08. Source, Copyright, and Security Policy

작성일: 2026-05-16
상태: v0.1 draft

## 1. 목적

Luddite는 언론 기사, 구독 매체, Google Drive, Notion, 내부 Sheet, PPT, 이미지 출처를 다룬다. 따라서 출처·저작권·보안 규칙을 명확히 해야 한다.

## 2. 최우선 원칙

```text
민감정보는 저장하지 않는다.
기사 전문은 복사하지 않는다.
이미지는 출처와 위험도를 표시한다.
사실 주장은 source를 남긴다.
최종 판단은 사람이 한다.
```

## 3. 민감정보 처리

### 3.1 절대 LLM prompt에 넣지 말 것

- 계정 ID
- 비밀번호/PW
- 전화번호
- 인증 담당자 정보
- 개인 이메일
- 내부 전용 접근 링크 중 외부 노출 위험이 있는 것
- 광고주/계약 관련 민감 정보

### 3.2 Redaction pattern

parser는 아래 패턴을 발견하면 마스킹한다.

```text
아이디: [REDACTED]
ID: [REDACTED]
비번: [REDACTED]
PW: [REDACTED]
비밀번호: [REDACTED]
전화: [REDACTED]
연락처: [REDACTED]
인증 담당자: [REDACTED]
```

### 3.3 로그 정책

- raw Sheet 전체를 로그에 남기지 않는다.
- redacted summary만 저장한다.
- LLM prompt와 response는 필요 최소한으로 저장한다.
- credential leak risk가 있으면 해당 산출물은 downstream으로 넘기지 않는다.

## 4. 기사와 구독 매체

### 4.1 허용

- URL 저장
- 짧은 핵심 quote
- 요약
- claim 단위 근거 연결
- 슬라이드 notes에 `[내용] URL` 기록

### 4.2 금지

- 기사 전문 복사
- 구독 기사 장문 발췌
- 여러 문단을 그대로 이어붙이기
- paywall 우회를 목적으로 한 저장

## 5. PPT speaker notes 출처 규칙

모든 슬라이드별 출처는 다음 형식을 따른다.

```text
[내용] https://...
[내용 2] https://...
[이미지] https://...
[이미지 2] GPT 생성
[TODO] 출처 확인 필요
```

## 6. 이미지 정책

| 이미지 유형 | 처리 |
|---|---|
| GPT 생성 | notes에 `GPT 생성` 표시 |
| 공식 기관 이미지 | URL 기록, 사용 조건 확인 |
| 언론사 사진 | 저작권 위험 flag, 원칙적으로 지양 |
| SNS 캡처 | ID/닉네임 가림 TODO |
| Wikimedia/Commons | license 확인 TODO |
| Getty/Shutterstock | 계약 조건 확인 필요, 자동 사용 금지 |
| 기사 캡처 | 내부 초안 가능, 최종 사용 전 사람 검토 |

## 7. 위험 주제 flags

다음 주제는 자동 생성 시 반드시 `risk_flags`를 붙인다.

```text
politics
sensitive_group
company_promo
company_attack
medical
legal
financial_advice
war_conflict
copyright_image
subscription_source
insufficient_evidence
```

## 8. 정치/사회 민감 이슈

정치/사회 이슈를 다룰 때는:

- 특정 진영 주장을 단정하지 않는다.
- 원문 발언과 해석을 분리한다.
- 여론/선거/지지율은 조사기관과 날짜를 명시한다.
- 풍자는 가능하지만 사실과 의견을 구분한다.

## 9. 의료/건강 이슈

- 치료 효과를 단정하지 않는다.
- 제품/시술 홍보처럼 보이지 않게 한다.
- 정부/학회/논문 등 근거를 확인한다.
- 개인 건강 조언으로 변환하지 않는다.

## 10. 금융/투자 이슈

- 매수/매도 추천을 하지 않는다.
- 정책/시장 구조 설명으로 한정한다.
- 수익률, 원금보장, 손실부담 표현은 정확히 검증한다.
- 개인 투자 판단은 시청자 책임임을 전제로 한다.

## 11. BDC 주의

BDC는 일반 콘텐츠보다 다음 위험이 크다.

- 광고주 홍보 과잉
- 서비스 설명 오류
- 법적 고지 누락
- 이해상충 오해

BDC 문서는 별도 flag를 갖는다.

```json
{
  "is_bdc": true,
  "advertiser": "...",
  "requires_marketing_review": true,
  "requires_legal_review": true
}
```

## 12. Implementation requirements

Codex는 다음을 구현해야 한다.

- `redact_sensitive_text(text)`
- `canonicalize_url(url)`
- `extract_source_notes(notes)`
- `detect_risk_flags(text, metadata)`
- `validate_no_credentials(payload)`
- `generate_source_report(deck_plan)`

## 13. Fail-safe

다음 조건에서는 산출물을 자동으로 보류한다.

- credential pattern 감지
- source가 없는 고위험 주장
- 구독 기사 전문 장문 포함
- 특정 집단에 대한 공격적 표현
- 이미지 출처가 없고 실제 이미지 삽입 요청
