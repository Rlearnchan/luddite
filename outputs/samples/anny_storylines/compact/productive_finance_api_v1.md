# 생산적 금융으로의 전환: 담보·단기수익에서 장기 위험분담으로?

> 이 문서는 production Anny output이 아니라 manual/API dry-run sample입니다.
> source attached는 fact-check complete를 의미하지 않습니다.

## Summary

- story_seed_title: 생산적 금융으로의 전환: 담보·단기수익에서 장기 위험분담으로?
- label: Productive finance API v1
- output_type: api_experiment
- description: Controlled API experiment output, not production.
- sections: 4
- slides: 22
- source_urls: 25
- needs_source: 0
- needs_fact_check: 17
- risk_flags: ['single_source_dependency', 'official_evidence_missing', 'policy_effect_uncertainty', 'investment_advice_risk', 'needs_human_review']
- failure_modes: ['unsupported_claim', 'policy_finance_guardrail_violation', 'key_beat_drift']
- schema_valid: True
- hygiene_passed: False
- readiness: not production-ready

## Required Fact Checks

- 원문 전문 확인 (이억원 발언 원문 및 맥락)
- 숫자/통계 원자료 확인 (150조·기간·판매규모 등)
- 공식 보도자료/세미나 자료 확인 (운용지침·공모자료)
- 반대 사례 또는 리스크 자료 추가 확보 (관치금융 우려 근거)

## Section 1. Seed & 문제 제기

### 01. 생산적 금융과 정책자금 전환

- type: title
- section_slide: 1

Body:
- 이억원 금융위원장의 경고에서 시작한 토론: 금융은 안전하게 빌려주는 산업인가, 위험을 나눠 성장에 베팅하는 산업인가?

Check:
- needs_source=False, needs_fact_check=False

Note: title / no factual claim. Rhetorical framing only.

### 02. 담보·단기수익 — 이억원 "담보 및 단기수익 중심 금융 경쟁 앞서가기 어려워"

- type: hook
- section_slide: 2

Body:
- 담보·단기수익 중심 금융의 한계를 지적한 발언을 출발점으로 삼는다.

Sources:
- https://news.einfomax.co.kr/news/articleView.html?idxno=4415444

Check:
- needs_source=False, needs_fact_check=True

Note: fact_check_priority: high. 원문 전문 확인 필요(후보 기사). fact_check_kind: institution_quote_context. required_before_broadcast: 원문 확인 및 발언 맥락 점검.

### 03. 금융은 안전하게 돈을 빌려주는 산업인가, 성장 위험을 나눠지는 산업인가?

- type: rhetorical
- section_slide: 3

Body:
- 방송이 던질 근본 질문을 명확히 한다.

Check:
- needs_source=False, needs_fact_check=False

Note: rhetorical bridge / no factual claim. 순수 질문형으로 source 없이 허용.

### 04. 핵심 관찰: 세계적 경쟁은 AI·반도체·배터리에 장기자본을 요구한다

- type: explainer
- section_slide: 4

Body:
- 정책담당자들이 '생산적 투자'로 금융 역할 이동을 주문하는 배경을 요약한다.

Sources:
- https://news.einfomax.co.kr/news/articleView.html?idxno=4415444

Check:
- needs_source=False, needs_fact_check=True

Note: 지원 근거로 후보 기사 인용. fact_check_priority: medium. 사실관계 보강을 위해 정책브리핑(국민성장펀드) 자료 연결 필요.

## Section 2. 국민성장펀드: 설계와 숫자(공식 자료 중심)

### 05. 국민성장펀드: 5년간 150조 계획(공식)

- type: data
- section_slide: 1

Body:
- 국민성장펀드는 민관합동으로 '5년 150조원' 규모를 목표로 한다.

Sources:
- https://ngf.kdb.co.kr/GFMNMN00N00.act
- https://www.korea.kr/news/policyNewsView.do?newsId=148961201&pWise=main&pWiseMain=A4

Check:
- needs_source=False, needs_fact_check=True

Note: fact_check_priority: high. 수치 출처는 공식 페이지와 정책브리핑(국민성장펀드)이며 방송 전 숫자(150조·기간 등) 원자료 확인 필수.

### 06. 국민참여형 펀드 상품구조(시각 자료 후보)

- type: image_centered
- section_slide: 2

Body:
- 판매/손실분담/재정 후순위 등 구조를 카드뉴스형 시각자료로 정리한 후보.

Check:
- needs_source=False, needs_fact_check=False

Note: 이미지 출처: 정책브리핑 카드뉴스. visual candidate 사용 시 저작권·공식성 확인 필요.

### 07. 국민참여형: 판매·손실우선 부담 구조

- type: explainer
- section_slide: 3

Body:
- 공식 자료: 국민 모집액(예시), 재정 후순위 보강, 자펀드별 손실 우선 부담 규정 등을 확인할 수 있다.

Sources:
- https://www.korea.kr/news/policyNewsView.do?newsId=148963908&pWise=main&pWiseMain=R3
- https://m.korea.kr/briefing/pressReleaseView.do?newsId=156739847

Check:
- needs_source=False, needs_fact_check=True

Note: fact_check_priority: high. 슬라이드의 수치·비율(예: 모집액 6000억, 재정 1200억 등)은 원문 확인 필요.

### 08. 1차 프로젝트: AI·반도체·이차전지 등 7건(공식)

- type: data
- section_slide: 4

Body:
- 정책브리핑은 1차 프로젝트로 첨단전략산업을 명시한다.

Sources:
- https://m.korea.kr/news/policyNewsView.do?newsId=148956795

Check:
- needs_source=False, needs_fact_check=True

Note: fact_check_priority: medium. 프로젝트 목록·선정 기준은 보도자료 원문 확인 필요.

### 09. 정책 설계 핵심: 직접투자·간접투자·초저리대출의 혼합

- type: explainer
- section_slide: 5

Body:
- 공식 소개는 다양한 운용 수단(직접/간접/인프라/대출)을 통해 생태계 전반을 지원한다고 밝힌다.

Sources:
- https://ngf.kdb.co.kr/GFMNMN00N00.act
- https://m.korea.kr/briefing/pressReleaseView.do?newsId=156739847

Check:
- needs_source=False, needs_fact_check=True

Note: fact_check_priority: medium. 각 수단의 비중·선택기준은 운용사 공모자료 등으로 확인 필요.

### 10. 요약: 공식 자료가 말하는 '무엇'과 우리가 던질 '질문'

- type: bridge
- section_slide: 6

Body:
- 공식은 대규모 자금·혼합 운용·손실분담 설계를 제시한다. 그렇다면 실제로 '누가 긴 위험을 흡수'하는가?

Sources:
- https://m.korea.kr/briefing/pressReleaseView.do?newsId=156739847

Check:
- needs_source=False, needs_fact_check=True

Note: 방송 전 운용계약서·공모자료 등 추가 확인 권장.

## Section 3. 금융구조와 제약: 누가 긴 위험을 맡을 것인가

### 11. 은행은 왜 담보와 단기수익을 선호하나?

- type: section_title
- section_slide: 1

Body:
- 규제와 자본비용이 장기·고위험 투자를 제한한다.

Sources:
- https://www.bis.org/bcbs/basel3.htm

Check:
- needs_source=False, needs_fact_check=False

Note: section title with factual pointer to Basel framework. 사실관계는 BIS 문서로 근거 제시.

### 12. 담보·단기수익

- type: explainer
- section_slide: 2

Body:
- 은행은 담보가 확실하고 회수 가능성이 높은 단기 수익 모델을 선호한다(규제·자본비율 영향).

Sources:
- https://www.bis.org/bcbs/basel3.htm
- https://news.einfomax.co.kr/news/articleView.html?idxno=4415444

Check:
- needs_source=False, needs_fact_check=True

Note: fact_check_priority: medium. '담보 선호' 설명은 일반적 은행 관행과 규제 근거로 제시. 구체 수치(자본비율 영향)는 추가 확인 권장.

### 13. 규제 프레임워크가 장기투자를 어렵게 만든다

- type: explainer
- section_slide: 3

Body:
- Basel III 등의 규제가 위험가중자산(RWA)을 통해 장기·고위험 자산에 높은 자본비용을 부과한다.

Sources:
- https://www.bis.org/bcbs/basel3.htm

Check:
- needs_source=False, needs_fact_check=True

Note: fact_check_priority: high. 규제 효과의 구체적 수치(어떤 자산에 얼마나 적용되는지)는 전문가 확인 필요.

### 14. 국내 논의: '장기 투자 인내 자본' 필요제기

- type: quote
- section_slide: 4

Body:
- 언론·전문가는 은행 건전성 규제와 장기투자 사이의 긴장 관계를 지적해왔다.

Sources:
- https://www.donga.com/news/Economy/article/all/20251113/132765077/4

Check:
- needs_source=False, needs_fact_check=True

Note: 동아일보 보도는 관련 논의를 요약. 해당 기사 원문 확인 권장.

### 15. 누가 장기 위험을 흡수할 수 있나?

- type: data
- section_slide: 5

Body:
- 가능한 주체: 연기금·국부펀드·정책펀드(국민성장펀드)·민간 대형 운용사 등.
- 하지만 각 주체의 인센티브·제약(유동성·수익성 기대)이 다르다.

Sources:
- https://ngf.kdb.co.kr/GFMNMN00N00.act
- https://www.korea.kr/news/policyNewsView.do?newsId=148961201&pWise=main&pWiseMain=A4

Check:
- needs_source=False, needs_fact_check=True

Note: fact_check_priority: medium. 연기금·사모펀드 등 구체적 역할/규모는 추가 근거 필요.

### 16. 정책금융(국민성장펀드)은 시장의 '긴 위험'을 얼마나 메꿀 수 있나?

- type: bridge
- section_slide: 6

Body:
- 공적자금이 투입되면 민간 자금의 레버리지·참여를 유도할 수 있지만 경계도 분명하다.

Sources:
- https://m.korea.kr/briefing/pressReleaseView.do?newsId=156739847

Check:
- needs_source=False, needs_fact_check=True

Note: 정책효과는 단정 불가. required_before_broadcast: 운용지침·재정투입 한도·법적 구조 확인 필요.

### 17. 은행 관점의 현실적 제약

- type: explainer
- section_slide: 7

Body:
- 은행은 규제·예금자 보호·유동성 관리 때문에 장기·비담보 투자를 확대하기 어렵다.

Sources:
- https://www.bis.org/bcbs/basel3.htm
- https://www.donga.com/news/Economy/article/all/20251113/132765077/4

Check:
- needs_source=False, needs_fact_check=True

Note: fact_check_priority: medium. 은행 내부 정책·리스크관리 기준은 개별 은행 자료로 확인 권장.

## Section 4. 반대 관점·리스크 그리고 마무리

### 18. 리스크 — 반대 관점: 국민참여형 펀드의 논란

- type: counterpoint
- section_slide: 1

Body:
- 비판적 보도는 '개인판매·손실보전·관제상품화' 우려를 제기한다.

Sources:
- https://www.investchosun.com/m/article.html?contid=2026042180102

Check:
- needs_source=False, needs_fact_check=True

Note: fact_check_priority: high. 반대 논지는 실제 설계(손실우선·후순위 재정 등)를 바탕으로 제시되었는지 원문 확인 필요. fact_check_kind: policy_effect_claim.

### 19. 리스크 정리: 관치금융·손실사회화의 가능성

- type: risk
- section_slide: 2

Body:
- 정책자금이 민간 의사결정을 왜곡하거나 손실을 공적·사적 주체로 이전할 수 있다는 우려.
- 정책효과는 보수적으로 다뤄야 한다.

Sources:
- https://www.investchosun.com/m/article.html?contid=2026042180102
- https://m.korea.kr/briefing/pressReleaseView.do?newsId=156739847

Check:
- needs_source=False, needs_fact_check=True

Note: policy_effect_claim → required_before_broadcast: 구체적 손익분담 규정과 사례(해외·국내)를 확인해야 함.

### 20. 누가 긴 위험을 나누어야 하는가?

- type: comparison
- section_slide: 3

Body:
- 가능성 있는 조합: 정책펀드(초기 흡수) + 연기금·사모(중기) + 민간 투자(후속).
- 그러나 각 주체의 인센티브·법적 제약을 고려해야 한다.

Sources:
- https://ngf.kdb.co.kr/GFMNMN00N00.act
- https://www.korea.kr/news/policyNewsView.do?newsId=148961201&pWise=main&pWiseMain=A4

Check:
- needs_source=False, needs_fact_check=True

Note: 구체적 역할분담은 운용지침·법적 구조 확인 필요. fact_check_priority: medium.

### 21. 정책·실무 확인 리스트(방송 전 필수)

- type: data
- section_slide: 4

Body:
- 1) 후보 기사(이억원 발언) 원문 전문 확인
- 2) 국민성장펀드 운용지침·공모문서(재정투입 규모·손실분담 비율) 원문 확보
- 3) 은행 규제(Basel) 적용 사례·위험가중자산 영향 자료 확보
- 4) 반대 사례(관치금융·손실전가) 추가 출처 확보

Check:
- needs_source=False, needs_fact_check=True

Note: production checklist for newsroom. required_before_broadcast: 모든 항목에 대한 문서확인과 전문가 코멘트 필요. fact_check_priority: high.

### 22. 금융은 안전하게 빌려주는 산업인가, 위험을 나눠 성장에 베팅하는 산업인가?

- type: closing_question
- section_slide: 5

Body:
- 오늘 회차의 최종 질문 — 정책금융의 역할을 어떻게 설계해야 할까?

Check:
- needs_source=False, needs_fact_check=False

Note: 순수 질문형 closing. 다만 방송 전에는 위의 production checklist를 충족해야 함.
