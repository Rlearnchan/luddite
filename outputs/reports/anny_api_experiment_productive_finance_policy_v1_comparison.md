# Anny API Experiment Comparison — Productive Finance Policy

- generated_at: 2026-05-19T01:12:50.304459+00:00
- case_id: anny_api_experiment_productive_finance_policy_v1
- manual_case_id: anny_dry_run_productive_finance_policy_v1
- api_storyline_path: outputs/model_dry_runs/anny_api_experiments/anny_api_experiment_productive_finance_policy_v1/parsed_storyline.json
- manual_storyline_path: outputs/model_dry_runs/anny_storyline/productive_finance_policy_gpt_pro_storyline_enriched.json
- model: gpt-5-mini
- failure_modes: ['unsupported_claim', 'key_beat_drift']
- schema_valid: True
- hygiene_passed: False
- source_hallucination_count: 0
- do_not_claim_violations: []
- policy_finance_guardrail_errors: []
- policy_finance_guardrail_passed: True
- unsupported_claim_details: [{'slide_no': 1, 'headline': '생산적 금융과 정책자금 전환', 'slide_type': 'title', 'fact_check_kind': None, 'body_excerpt': '이억원 금융위원장의 경고에서 시작한 토론: 금융은 안전하게 빌려주는 산업인가, 위험을 나눠 성장에 베팅하는 산업인가?', 'reason': 'empty_source_urls_without_needs_source', 'source_urls_present': False, 'needs_source': False, 'needs_fact_check': False, 'triggered_marker': '경고', 'triggered_marker_type': 'source_specific', 'is_source_specific': True, 'is_institution_role_claim': False, 'recommended_fix': 'add_source_url', 'message': 'slide 1 has empty source_urls without needs_source=true'}, {'slide_no': 3, 'headline': '금융은 안전하게 돈을 빌려주는 산업인가, 성장 위험을 나눠지는 산업인가?', 'slide_type': 'rhetorical', 'fact_check_kind': None, 'body_excerpt': '방송이 던질 근본 질문을 명확히 한다.', 'reason': 'empty_source_urls_without_needs_source', 'source_urls_present': False, 'needs_source': False, 'needs_fact_check': False, 'triggered_marker': '명', 'triggered_marker_type': 'factual_claim', 'is_source_specific': False, 'is_institution_role_claim': False, 'recommended_fix': 'set_needs_source_true_and_needs_fact_check_true', 'message': 'slide 3 has empty source_urls without needs_source=true'}, {'slide_no': 6, 'headline': '국민참여형 펀드 상품구조(시각 자료 후보)', 'slide_type': 'image_centered', 'fact_check_kind': None, 'body_excerpt': '판매/손실분담/재정 후순위 등 구조를 카드뉴스형 시각자료로 정리한 후보.', 'reason': 'empty_source_urls_without_needs_source', 'source_urls_present': False, 'needs_source': False, 'needs_fact_check': False, 'triggered_marker': None, 'triggered_marker_type': None, 'is_source_specific': False, 'is_institution_role_claim': False, 'recommended_fix': 'rewrite_as_rhetorical_question', 'message': 'slide 6 has empty source_urls without needs_source=true'}, {'slide_no': 21, 'headline': '정책·실무 확인 리스트(방송 전 필수)', 'slide_type': 'data', 'fact_check_kind': None, 'body_excerpt': '1) 후보 기사(이억원 발언) 원문 전문 확인 2) 국민성장펀드 운용지침·공모문서(재정투입 규모·손실분담 비율) 원문 확보 3) 은행 규제(Basel) 적용 사례·위험가중자산 영향 자료 확보 4) 반대 사례(관치금융·손실전가) 추가 출처 확보', 'reason': 'empty_source_urls_without_needs_source', 'source_urls_present': False, 'needs_source': False, 'needs_fact_check': True, 'triggered_marker': '발언', 'triggered_marker_type': 'source_specific', 'is_source_specific': True, 'is_institution_role_claim': False, 'recommended_fix': 'add_source_url', 'message': 'slide 21 has empty source_urls without needs_source=true'}]
- key_beat_coverage_errors: ['key_beat_anchor_phrase_not_in_text:AI/반도체 투자와 장기 위험자본 필요:slide_8', 'key_beat_anchor_phrase_not_in_text:금융권이 어디까지 위험을 나눌 수 있는가:slide_15', 'key_beat_anchor_phrase_not_in_text:금융권이 어디까지 위험을 나눌 수 있는가:slide_20', 'key_beat_covered_but_not_in_slide_text:AI/반도체 투자와 장기 위험자본 필요', 'key_beat_covered_but_not_in_slide_text:국민성장펀드/정책금융 논쟁', 'key_beat_covered_but_not_in_slide_text:금융권이 어디까지 위험을 나눌 수 있는가', 'key_beat_covered_but_not_in_slide_text:반대 관점/리스크', 'weak_key_beat_mapping:담보·단기수익 중심 금융의 한계:coverage_ref_missing_in_covers', 'weak_key_beat_mapping:AI/반도체 투자와 장기 위험자본 필요:coverage_ref_missing_in_covers', 'weak_key_beat_mapping:국민성장펀드/정책금융 논쟁:coverage_ref_missing_in_covers', 'weak_key_beat_mapping:금융권이 어디까지 위험을 나눌 수 있는가:coverage_ref_missing_in_covers', 'weak_key_beat_mapping:반대 관점/리스크:coverage_ref_missing_in_covers']

## Metrics

| Output | Sections | Slides | Source URLs | Needs Source | Needs Fact Check | Counterpoint | Source/Image Overlap | Key Beat Recall |
|---|---:|---:|---:|---:|---:|---|---:|---:|
| Manual enriched | 4 | 24 | 48 | 1 | 17 | True | 0 | 1.00 |
| API experiment | 4 | 22 | 25 | 0 | 17 | True | 0 | 0.80 |

## Qualitative Notes

- This is a controlled API experiment, not a production anny agent.
- Failure is acceptable if failure modes are recorded and raw output is retained.
- API output must remain evidence-bound to the input bundle/evidence pack.
- Policy/finance guardrails pass only if no investment advice, policy promotion, or missing broadcast-check metadata is detected.
- ready_for_production_agent: false
