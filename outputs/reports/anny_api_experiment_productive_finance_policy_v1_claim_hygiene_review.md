# Anny API Productive Finance v1 Claim Hygiene Review

- generated_at: 2026-05-19T01:26:04.681515+00:00
- storyline_path: /Users/bae/Documents/code/luddite/outputs/model_dry_runs/anny_api_experiments/anny_api_experiment_productive_finance_policy_v1/parsed_storyline.json
- manifest_path: /Users/bae/Documents/code/luddite/outputs/model_dry_runs/anny_api_experiments/anny_api_experiment_productive_finance_policy_v1/manifest.json
- failure_modes: ['unsupported_claim', 'policy_finance_guardrail_violation', 'key_beat_drift']
- reviewed_unsupported_claims: 4
- api_recalled: false
- ready_for_production_agent: false

## Slide Review

| Slide | Type | Classification | Recommended Action | Triggered Marker | Needs Source | Needs Fact Check | Headline |
|---:|---|---|---|---|---|---|---|
| 1 | title | source_specific_title_or_bridge | require_source_url | source_specific:경고 | False | False | 생산적 금융과 정책자금 전환 |
| 6 | image_centered | policy_effect_claim_without_source | set_needs_source_true | policy_finance:손실분담 | False | False | 국민참여형 펀드 상품구조(시각 자료 후보) |
| 21 | data | source_specific_title_or_bridge | require_source_url | source_specific:발언 | False | True | 정책·실무 확인 리스트(방송 전 필수) |
| 22 | closing_question | policy_effect_claim_without_source | set_needs_source_true | policy_finance:정책금융 | False | False | 금융은 안전하게 빌려주는 산업인가, 위험을 나눠 성장에 베팅하는 산업인가? |

## Detail

### Slide 1

- headline: 생산적 금융과 정책자금 전환
- slide_type: title
- fact_check_kind: None
- body_excerpt: 이억원 금융위원장의 경고에서 시작한 토론: 금융은 안전하게 빌려주는 산업인가, 위험을 나눠 성장에 베팅하는 산업인가?
- source_urls_present: False
- needs_source: False
- needs_fact_check: False
- reason: empty_source_urls_without_needs_source
- triggered_marker: 경고
- triggered_marker_type: source_specific
- recommended_fix: add_source_url
- classification: source_specific_title_or_bridge
- recommended_action: require_source_url

### Slide 6

- headline: 국민참여형 펀드 상품구조(시각 자료 후보)
- slide_type: image_centered
- fact_check_kind: None
- body_excerpt: 판매/손실분담/재정 후순위 등 구조를 카드뉴스형 시각자료로 정리한 후보.
- source_urls_present: False
- needs_source: False
- needs_fact_check: False
- reason: empty_source_urls_without_needs_source
- triggered_marker: 손실분담
- triggered_marker_type: policy_finance
- recommended_fix: set_needs_source_true_and_needs_fact_check_true
- classification: policy_effect_claim_without_source
- recommended_action: set_needs_source_true

### Slide 21

- headline: 정책·실무 확인 리스트(방송 전 필수)
- slide_type: data
- fact_check_kind: None
- body_excerpt: 1) 후보 기사(이억원 발언) 원문 전문 확인 2) 국민성장펀드 운용지침·공모문서(재정투입 규모·손실분담 비율) 원문 확보 3) 은행 규제(Basel) 적용 사례·위험가중자산 영향 자료 확보 4) 반대 사례(관치금융·손실전가) 추가 출처 확보
- source_urls_present: False
- needs_source: False
- needs_fact_check: True
- reason: empty_source_urls_without_needs_source
- triggered_marker: 발언
- triggered_marker_type: source_specific
- recommended_fix: add_source_url
- classification: source_specific_title_or_bridge
- recommended_action: require_source_url

### Slide 22

- headline: 금융은 안전하게 빌려주는 산업인가, 위험을 나눠 성장에 베팅하는 산업인가?
- slide_type: closing_question
- fact_check_kind: None
- body_excerpt: 오늘 회차의 최종 질문 — 정책금융의 역할을 어떻게 설계해야 할까?
- source_urls_present: False
- needs_source: False
- needs_fact_check: False
- reason: empty_source_urls_without_needs_source
- triggered_marker: 정책금융
- triggered_marker_type: policy_finance
- recommended_fix: set_needs_source_true_and_needs_fact_check_true
- classification: policy_effect_claim_without_source
- recommended_action: set_needs_source_true

## Key Beat Drift Detail

- invalid_covers_key_beat_value:slide_2:kb_collateral_short_term_limit
- key_beat_anchor_phrase_not_in_text:AI/반도체 투자와 장기 위험자본 필요:slide_8
- invalid_covers_key_beat_value:slide_12:kb_collateral_short_term_limit
- invalid_covers_key_beat_value:slide_15:kb_risk_sharing_boundary
- invalid_key_beat_anchor_phrase:관치금융/손실전가/정책금융 실패 가능성:slide_18
- invalid_covers_key_beat_value:slide_20:kb_risk_sharing_boundary
- missing_covers_key_beats:담보·단기수익 중심 금융의 한계
- missing_covers_key_beats:금융권이 어디까지 위험을 나눌 수 있는가
- missing_key_beat:담보·단기수익 중심 금융의 한계
- key_beat_covered_but_not_in_slide_text:AI/반도체 투자와 장기 위험자본 필요
- key_beat_covered_but_not_in_slide_text:국민성장펀드와 정책금융 논쟁
- missing_key_beat:금융권이 어디까지 위험을 나눌 수 있는가
- key_beat_covered_but_not_in_slide_text:관치금융/손실전가/정책금융 실패 가능성
- weak_key_beat_mapping:AI/반도체 투자와 장기 위험자본 필요:coverage_ref_missing_in_covers
- weak_key_beat_mapping:국민성장펀드와 정책금융 논쟁:coverage_ref_missing_in_covers
- weak_key_beat_mapping:관치금융/손실전가/정책금융 실패 가능성:coverage_ref_missing_in_covers

## Rule Interpretation

- Finance/policy source-specific title or bridge text needs a source URL.
- Policy mechanism, policy effect, investment risk, market finance, and fund-structure claims need source or needs_source=true.
- Policy/finance claims keep needs_fact_check=true even when a source URL is attached.
- Production checklist slides are internal preparation material, not normal broadcast claims.
- This report does not imply production readiness.
