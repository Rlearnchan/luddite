# 생산적 금융과 정책자금 전환

> 이 문서는 production Anny output이 아니라 manual/API dry-run sample입니다.
> source attached는 fact-check complete를 의미하지 않습니다.

## Summary

- story_seed_title: 생산적 금융과 정책자금 전환
- label: Productive finance manual enriched
- output_type: manual_enriched
- description: GPT Pro enriched manual dry-run sample.
- sections: 4
- slides: 24
- source_urls: 48
- needs_source: 1
- needs_fact_check: 17
- risk_flags: ['investment_advice_risk', 'policy_effect_uncertainty', 'needs_human_review']
- failure_modes: []
- schema_valid: n/a
- hygiene_passed: n/a
- readiness: not production-ready

## Required Fact Checks

- 금융위원회/산업은행 국민성장펀드 공식자료의 최신 원문과 수치 확인
- 국민참여형 펀드 손실 우선 부담 구조와 투자자 리스크 재확인
- AI·반도체 장기 투자 규모와 집행 현황 추가 확인
- 관치금융, 정책금융 실패, 손실 전가 논란 추가 counterpoint 보강
- 은행 건전성·위험가중자산·예금자 보호 관련 국내 감독자료 추가 확인

## Section 1. 안전한 금융의 본능과 새로운 질문

### Slide 1. 생산적 금융과 정책자금 전환

- type: title
- covers_key_beats: []
- key_beat_anchors_used: []
- needs_source: False
- needs_fact_check: False
- fact_check_kind: rhetorical_caution
- fact_check_priority: low
- required_before_broadcast: False

Body:
- 금융은 안전하게 돈을 빌려주는 산업인가
- 아니면 성장 위험을 나눠지는 산업인가

Notes:
방송용 전환/질문 slide. 사실 주장으로 과확장하지 말 것.

### Slide 2. 금융위원장이 던진 질문 하나

- type: hook
- covers_key_beats: []
- key_beat_anchors_used: []
- needs_source: False
- needs_fact_check: True
- fact_check_kind: institution_quote_context
- fact_check_priority: high
- required_before_broadcast: True

Body:
- “담보 및 단기수익 중심 금융 경쟁은 앞서가기 어렵다”는 문제 제기가 나왔다.
- 금융위원회 공식자료는 국민성장펀드가 5년간 150조 원, 2026년 30조 원 규모로 첨단산업 생태계에 자금을 공급하는 틀이라고 설명한다.
- 다만 이 발언과 정책 숫자가 곧 정책 성공을 뜻하는 것은 아니다.

Sources:
- https://news.einfomax.co.kr/news/articleView.html?idxno=4415444
- https://www.fsc.go.kr/no010101/86834?curPage=2&srchBeginDt=&srchCtgry=&srchEndDt=&srchKey=&srchText=

Source refs:
- primary_article: 이억원 금융위원장 발언과 후보 기사 맥락 (https://news.einfomax.co.kr/news/articleView.html?idxno=4415444, confidence=medium, manual_check_required=True)
- primary_official_source: 국민성장펀드 150조/2026년 30조 운용 방안과 투자 방식 확인 (https://www.fsc.go.kr/no010101/86834?curPage=2&srchBeginDt=&srchCtgry=&srchEndDt=&srchKey=&srchText=, confidence=high, manual_check_required=False)

Notes:
[내용] 연합인포맥스 후보 기사 + 금융위원회 공식자료. 발언 원문 맥락은 방송 전 재확인.

### Slide 3. 은행 입장에서는 담보가 제일 편하다

- type: explainer
- covers_key_beats: []
- key_beat_anchors_used: []
- needs_source: False
- needs_fact_check: True
- fact_check_kind: source_context
- fact_check_priority: medium
- required_before_broadcast: True

Body:
- 돈을 빌려줄 때 가장 쉬운 질문은 “담보가 있나?”다.
- 은행은 자본규제와 위험가중자산을 고려해야 하므로, 위험한 자산을 무한정 늘릴 수 없다.
- 그래서 장기 위험자본 논의는 은행의 본능을 비난하는 문제가 아니라 금융 시스템의 설계 문제에 가깝다.

Sources:
- https://www.bis.org/bcbs/basel3.htm
- https://www.donga.com/news/Economy/article/all/20251113/132765077/4

Source refs:
- market_finance_view: 은행 자본규제와 위험가중자산 논리 배경 (https://www.bis.org/bcbs/basel3.htm, confidence=high, manual_check_required=False)
- market_finance_view: 장기 인내자본과 은행 건전성 규제 국내 논의 (https://www.donga.com/news/Economy/article/all/20251113/132765077/4, confidence=medium, manual_check_required=True)

Notes:
[근거] BIS Basel III 프레임워크 + 국내 인내자본/건전성 규제 논의. 국내 감독규정은 방송 전 추가 확인.

### Slide 4. 그런데 AI 산업은 담보보다 시간이 먼저 필요하다

- type: bridge
- covers_key_beats: []
- key_beat_anchors_used: []
- needs_source: False
- needs_fact_check: True
- fact_check_kind: policy_effect_claim
- fact_check_priority: high
- required_before_broadcast: True

Body:
- AI와 반도체는 소프트웨어 개발비만의 문제가 아니라 설비, 전력, 공정, 인력, 공급망이 함께 필요한 산업이다.
- 정책자료는 국민성장펀드가 AI·반도체 같은 첨단전략산업에 장기 자금을 공급하려는 틀이라고 설명한다.
- 그래서 이 이야기는 “대출을 늘리자”보다 “누가 긴 위험을 나눌 것인가”에 가깝다.

Sources:
- https://www.korea.kr/news/policyNewsView.do?newsId=148961201&pWise=main&pWiseMain=A4
- https://m.korea.kr/news/policyNewsView.do?newsId=148956795
- https://www.fsc.go.kr/no010101/86834?curPage=2&srchBeginDt=&srchCtgry=&srchEndDt=&srchKey=&srchText=

Source refs:
- official_evidence: AI·반도체 집중 투자와 장기 인내자본 필요성 확인 (https://www.korea.kr/news/policyNewsView.do?newsId=148961201&pWise=main&pWiseMain=A4, confidence=high, manual_check_required=False)
- official_evidence: AI·반도체·이차전지 1차 메가프로젝트와 생산적 금융 정책 맥락 확인 (https://m.korea.kr/news/policyNewsView.do?newsId=148956795, confidence=high, manual_check_required=False)
- primary_official_source: 국민성장펀드 150조/2026년 30조 운용 방안과 투자 방식 확인 (https://www.fsc.go.kr/no010101/86834?curPage=2&srchBeginDt=&srchCtgry=&srchEndDt=&srchKey=&srchText=, confidence=high, manual_check_required=False)

Notes:
[근거] 국민성장펀드 AI·반도체 집중 투자 자료. 투자 효과 단정 금지.

### Slide 5. 금융은 원래 안전해야 하는가, 위험을 져야 하는가

- type: rhetorical
- covers_key_beats: []
- key_beat_anchors_used: []
- needs_source: False
- needs_fact_check: False
- fact_check_kind: rhetorical_caution
- fact_check_priority: low
- required_before_broadcast: False

Body:
- 너무 안전하면 성장산업이 돈을 못 받는다.
- 너무 위험하면 결국 손실을 누가 떠안느냐는 문제가 생긴다.
- 이 사이의 균형이 정책금융 논쟁의 본론이다.

Notes:
방송용 전환/질문 slide. 사실 주장으로 과확장하지 말 것.

## Section 2. AI·반도체 투자와 장기 위험자본

### Slide 6. AI·반도체 투자와 장기 위험자본

- type: section_title
- covers_key_beats: []
- key_beat_anchors_used: []
- needs_source: False
- needs_fact_check: False
- fact_check_kind: rhetorical_caution
- fact_check_priority: low
- required_before_broadcast: False

Body:
-

Notes:
방송용 전환/질문 slide. 사실 주장으로 과확장하지 말 것.

### Slide 7. AI가 소프트웨어만의 문제가 아니게 된 순간

- type: explainer
- covers_key_beats: []
- key_beat_anchors_used: []
- needs_source: False
- needs_fact_check: True
- fact_check_kind: policy_effect_claim
- fact_check_priority: high
- required_before_broadcast: True

Body:
- AI는 모델만으로 돌아가지 않는다.
- 반도체, 전력망, 데이터센터, 장비, 소재가 함께 필요하다.
- 공식자료가 “인내자본”을 말하는 이유도 이 산업이 긴 회수 기간과 대규모 선투자를 요구하기 때문이다.

Sources:
- https://www.korea.kr/news/policyNewsView.do?newsId=148961201&pWise=main&pWiseMain=A4
- https://m.korea.kr/news/policyNewsView.do?newsId=148956795

Source refs:
- official_evidence: AI·반도체 집중 투자와 장기 인내자본 필요성 확인 (https://www.korea.kr/news/policyNewsView.do?newsId=148961201&pWise=main&pWiseMain=A4, confidence=high, manual_check_required=False)
- official_evidence: AI·반도체·이차전지 1차 메가프로젝트와 생산적 금융 정책 맥락 확인 (https://m.korea.kr/news/policyNewsView.do?newsId=148956795, confidence=high, manual_check_required=False)

Notes:
[근거] AI·반도체 장기 투자와 1차 메가프로젝트 자료. 세부 투자 규모는 방송 전 재확인.

### Slide 8. 장기 투자에는 기다릴 수 있는 돈이 필요하다

- type: data
- covers_key_beats: []
- key_beat_anchors_used: []
- needs_source: False
- needs_fact_check: True
- fact_check_kind: policy_effect_claim
- fact_check_priority: high
- required_before_broadcast: True

Body:
- 첨단산업 투자는 회수 기간이 길고 실패 가능성도 크다.
- 정부는 국민성장펀드를 통해 장기 자금을 공급하겠다고 설명하지만, 그 자체가 수익을 보장한다는 말은 아니다.
- 여기서 “장기 위험자본”이라는 말은 가능성과 손실 가능성을 함께 본다는 뜻이다.

Sources:
- https://www.korea.kr/news/policyNewsView.do?newsId=148961201&pWise=main&pWiseMain=A4
- https://www.fsc.go.kr/no010101/86834?curPage=2&srchBeginDt=&srchCtgry=&srchEndDt=&srchKey=&srchText=

Source refs:
- official_evidence: AI·반도체 집중 투자와 장기 인내자본 필요성 확인 (https://www.korea.kr/news/policyNewsView.do?newsId=148961201&pWise=main&pWiseMain=A4, confidence=high, manual_check_required=False)
- primary_official_source: 국민성장펀드 150조/2026년 30조 운용 방안과 투자 방식 확인 (https://www.fsc.go.kr/no010101/86834?curPage=2&srchBeginDt=&srchCtgry=&srchEndDt=&srchKey=&srchText=, confidence=high, manual_check_required=False)

Notes:
[근거] 공식 정책자료. 수익률·정책 효과 단정 금지.

### Slide 9. 부동산 담보는 보이지만, 기술의 미래는 잘 안 보인다

- type: comparison
- covers_key_beats: []
- key_beat_anchors_used: []
- needs_source: False
- needs_fact_check: True
- fact_check_kind: source_context
- fact_check_priority: medium
- required_before_broadcast: True

Body:
- 공장, 토지, 건물은 담보로 잡기 쉽다.
- 하지만 초기 기술, 인력, 데이터, 공정 노하우는 평가하기 어렵다.
- 위험가중자산과 자본규제가 있는 은행 입장에서는 이런 불확실성이 비용이 된다.

Sources:
- https://www.bis.org/bcbs/basel3.htm
- https://www.donga.com/news/Economy/article/all/20251113/132765077/4

Source refs:
- market_finance_view: 은행 자본규제와 위험가중자산 논리 배경 (https://www.bis.org/bcbs/basel3.htm, confidence=high, manual_check_required=False)
- market_finance_view: 장기 인내자본과 은행 건전성 규제 국내 논의 (https://www.donga.com/news/Economy/article/all/20251113/132765077/4, confidence=medium, manual_check_required=True)

Notes:
[근거] BIS 위험가중자산/자본규제 배경 + 국내 건전성 규제 논의.

### Slide 10. 그래서 정책금융은 시장이 못 보는 시간을 보겠다는 말일 수 있다

- type: bridge
- covers_key_beats: []
- key_beat_anchors_used: []
- needs_source: False
- needs_fact_check: True
- fact_check_kind: policy_effect_claim
- fact_check_priority: high
- required_before_broadcast: True

Body:
- 정책금융의 명분은 민간이 감당하기 어려운 초기 위험을 나눠지는 것이다.
- 하지만 정책자금이 늘 좋은 결과를 만든다고 단정할 수는 없다.
- 정책금융은 성장의 마중물일 수도, 손실의 통로일 수도 있다.

Sources:
- https://www.fsc.go.kr/no010101/86834?curPage=2&srchBeginDt=&srchCtgry=&srchEndDt=&srchKey=&srchText=
- https://www.investchosun.com/m/article.html?contid=2026042180102

Source refs:
- primary_official_source: 국민성장펀드 150조/2026년 30조 운용 방안과 투자 방식 확인 (https://www.fsc.go.kr/no010101/86834?curPage=2&srchBeginDt=&srchCtgry=&srchEndDt=&srchKey=&srchText=, confidence=high, manual_check_required=False)
- counterpoint: 개인 판매, 손실 보전, 관제상품화, 손실 사회화 논란 확인 (https://www.investchosun.com/m/article.html?contid=2026042180102, confidence=medium, manual_check_required=True)

Notes:
[근거] 금융위원회 공식자료 + 정책금융/관제상품 counterpoint. 균형 유지.

### Slide 11. 이건 “은행이 더 착해져야 한다”는 얘기가 아니다

- type: rhetorical
- covers_key_beats: []
- key_beat_anchors_used: []
- needs_source: False
- needs_fact_check: False
- fact_check_kind: rhetorical_caution
- fact_check_priority: low
- required_before_broadcast: False

Body:
- 은행은 예금자의 돈을 지켜야 한다.
- 기업은 긴 투자금을 원한다.
- 국가는 전략산업을 키우고 싶다.
- 세 이해관계가 한 지점에서 충돌한다.

Notes:
방송용 전환/질문 slide. 사실 주장으로 과확장하지 말 것.

## Section 3. 국민성장펀드와 정책금융 논쟁

### Slide 12. 국민성장펀드와 정책금융 논쟁

- type: section_title
- covers_key_beats: []
- key_beat_anchors_used: []
- needs_source: False
- needs_fact_check: False
- fact_check_kind: rhetorical_caution
- fact_check_priority: low
- required_before_broadcast: False

Body:
-

Notes:
방송용 전환/질문 slide. 사실 주장으로 과확장하지 말 것.

### Slide 13. 국민성장펀드라는 이름이 붙으면 이야기는 더 어려워진다

- type: hook
- covers_key_beats: []
- key_beat_anchors_used: []
- needs_source: False
- needs_fact_check: True
- fact_check_kind: investment_risk_claim
- fact_check_priority: high
- required_before_broadcast: True

Body:
- 국민성장펀드는 민관합동 150조 원 규모로 첨단전략산업 생태계를 지원하겠다는 정책 틀이다.
- 국민참여형 펀드는 일반 국민 자금도 일부 모아 자펀드에 투자하는 구조로 설계됐다.
- 그래서 이름은 성장 이야기지만, 실제 방송에서는 투자자 리스크와 정책 책임을 함께 봐야 한다.

Sources:
- https://www.fsc.go.kr/no010101/86834?curPage=2&srchBeginDt=&srchCtgry=&srchEndDt=&srchKey=&srchText=
- https://ngf.kdb.co.kr/GFMNMN00N00.act
- https://www.korea.kr/news/policyNewsView.do?newsId=148963908&pWise=main&pWiseMain=R3

Source refs:
- primary_official_source: 국민성장펀드 150조/2026년 30조 운용 방안과 투자 방식 확인 (https://www.fsc.go.kr/no010101/86834?curPage=2&srchBeginDt=&srchCtgry=&srchEndDt=&srchKey=&srchText=, confidence=high, manual_check_required=False)
- primary_official_source: 한국산업은행 국민성장펀드 공식 소개와 운영 주체 확인 (https://ngf.kdb.co.kr/GFMNMN00N00.act, confidence=high, manual_check_required=False)
- policy_mechanism: 국민참여형 펀드 모집액, 재정 1200억 원, 자펀드별 손실 우선 부담 구조 확인 (https://www.korea.kr/news/policyNewsView.do?newsId=148963908&pWise=main&pWiseMain=R3, confidence=high, manual_check_required=False)

Notes:
[근거] 금융위원회/산업은행 공식자료. 정책상품 홍보처럼 보이지 않게 주의.

### Slide 14. 위험을 나눈다는 말은 손실 가능성도 나눈다는 뜻이다

- type: explainer
- covers_key_beats: []
- key_beat_anchors_used: []
- needs_source: False
- needs_fact_check: True
- fact_check_kind: investment_risk_claim
- fact_check_priority: high
- required_before_broadcast: True

Body:
- 국민참여형 펀드 자료는 재정이 각 자펀드에서 20% 범위의 손실을 우선 부담하는 구조를 설명한다.
- 이 장치는 투자자의 위험을 낮추려는 설계지만, 원금 손실 가능성이 사라진다는 뜻은 아니다.
- 손실을 누가, 어떤 순서로, 어디까지 부담하는지가 핵심 질문이다.

Sources:
- https://www.korea.kr/news/policyNewsView.do?newsId=148963908&pWise=main&pWiseMain=R3
- https://www.korea.kr/multi/visualNewsView.do?newsId=148964200&pWise=main&pWiseMain=K3

Source refs:
- policy_mechanism: 국민참여형 펀드 모집액, 재정 1200억 원, 자펀드별 손실 우선 부담 구조 확인 (https://www.korea.kr/news/policyNewsView.do?newsId=148963908&pWise=main&pWiseMain=R3, confidence=high, manual_check_required=False)
- visual_context: 국민참여형 국민성장펀드 상품구조도 후보 (https://www.korea.kr/multi/visualNewsView.do?newsId=148964200&pWise=main&pWiseMain=K3, confidence=high, manual_check_required=False)

Notes:
[근거] 정책브리핑 판매 구조와 카드뉴스. 투자 위험 표현은 반드시 보수적으로 유지.

### Slide 15. 정책금융의 어려움은 “누가 먼저 잃을 것인가”다

- type: quote
- covers_key_beats: []
- key_beat_anchors_used: []
- needs_source: False
- needs_fact_check: True
- fact_check_kind: policy_effect_claim
- fact_check_priority: high
- required_before_broadcast: True

Body:
- 정책금융의 어려움은 “돈을 넣을 것인가”보다 “손실이 나면 누가 먼저 감당할 것인가”다.
- 공식자료는 후순위 재정 보강을 설명하지만, 반대 관점은 손실 보전과 관제상품화 논란을 제기한다.
- 이 둘을 같이 봐야 정책금융 논쟁이 단순 찬반으로 흐르지 않는다.

Sources:
- https://www.korea.kr/news/policyNewsView.do?newsId=148963908&pWise=main&pWiseMain=R3
- https://m.korea.kr/briefing/pressReleaseView.do?newsId=156739847
- https://www.investchosun.com/m/article.html?contid=2026042180102

Source refs:
- policy_mechanism: 국민참여형 펀드 모집액, 재정 1200억 원, 자펀드별 손실 우선 부담 구조 확인 (https://www.korea.kr/news/policyNewsView.do?newsId=148963908&pWise=main&pWiseMain=R3, confidence=high, manual_check_required=False)
- policy_mechanism: 재정모펀드·공모펀드·자펀드 선정과 후순위 재정 보강 설계 확인 (https://m.korea.kr/briefing/pressReleaseView.do?newsId=156739847, confidence=high, manual_check_required=False)
- counterpoint: 개인 판매, 손실 보전, 관제상품화, 손실 사회화 논란 확인 (https://www.investchosun.com/m/article.html?contid=2026042180102, confidence=medium, manual_check_required=True)

Notes:
[근거] 정책 mechanism + counterpoint. 손실분담 수치와 구조는 방송 전 재확인.

### Slide 16. 성장산업을 돕는 것과 특정 기업을 밀어주는 것은 다르다

- type: comparison
- covers_key_beats: []
- key_beat_anchors_used: []
- needs_source: False
- needs_fact_check: True
- fact_check_kind: policy_effect_claim
- fact_check_priority: medium
- required_before_broadcast: True

Body:
- 공식자료는 AI, 반도체, 이차전지 등 첨단전략산업을 넓은 지원 대상으로 제시한다.
- 하지만 방송에서는 이것이 특정 기업 성공 보장이나 특정 상품 추천처럼 들리면 안 된다.
- 성장산업 지원과 특정 기업 밀어주기는 구분해서 다뤄야 한다.

Sources:
- https://m.korea.kr/news/policyNewsView.do?newsId=148956795
- https://www.fsc.go.kr/no010101/86834?curPage=2&srchBeginDt=&srchCtgry=&srchEndDt=&srchKey=&srchText=
- https://www.investchosun.com/m/article.html?contid=2026042180102

Source refs:
- official_evidence: AI·반도체·이차전지 1차 메가프로젝트와 생산적 금융 정책 맥락 확인 (https://m.korea.kr/news/policyNewsView.do?newsId=148956795, confidence=high, manual_check_required=False)
- primary_official_source: 국민성장펀드 150조/2026년 30조 운용 방안과 투자 방식 확인 (https://www.fsc.go.kr/no010101/86834?curPage=2&srchBeginDt=&srchCtgry=&srchEndDt=&srchKey=&srchText=, confidence=high, manual_check_required=False)
- counterpoint: 개인 판매, 손실 보전, 관제상품화, 손실 사회화 논란 확인 (https://www.investchosun.com/m/article.html?contid=2026042180102, confidence=medium, manual_check_required=True)

Notes:
[근거] 공식 지원대상 자료 + counterpoint. 기업 홍보/투자 조언 금지.

### Slide 17. 반대쪽 질문도 있다: 그럼 아무도 위험을 안 지면 어떻게 하나

- type: counterpoint
- covers_key_beats: []
- key_beat_anchors_used: []
- needs_source: False
- needs_fact_check: True
- fact_check_kind: policy_effect_claim
- fact_check_priority: medium
- required_before_broadcast: True

Body:
- 반대쪽 질문도 있다. 재정이 위험을 먼저 떠안으면 민간은 얼마나 책임 있게 투자할까.
- 또 은행과 금융회사는 건전성 규제, 위험가중자산, 예금자 보호 논리 안에서 움직인다.
- 그래서 아무도 위험을 안 지는 문제와, 누군가에게 위험을 떠넘기는 문제를 동시에 봐야 한다.

Sources:
- https://www.investchosun.com/m/article.html?contid=2026042180102
- https://www.bis.org/bcbs/basel3.htm
- https://www.donga.com/news/Economy/article/all/20251113/132765077/4

Source refs:
- counterpoint: 개인 판매, 손실 보전, 관제상품화, 손실 사회화 논란 확인 (https://www.investchosun.com/m/article.html?contid=2026042180102, confidence=medium, manual_check_required=True)
- market_finance_view: 은행 자본규제와 위험가중자산 논리 배경 (https://www.bis.org/bcbs/basel3.htm, confidence=high, manual_check_required=False)
- market_finance_view: 장기 인내자본과 은행 건전성 규제 국내 논의 (https://www.donga.com/news/Economy/article/all/20251113/132765077/4, confidence=medium, manual_check_required=True)

Notes:
[근거] counterpoint + BIS/국내 건전성 규제 논의. 추가 정책금융 실패 사례는 보강 필요.

### Slide 18. 결국 질문은 성장의 과실보다 위험의 배분이다

- type: bridge
- covers_key_beats: []
- key_beat_anchors_used: []
- needs_source: False
- needs_fact_check: True
- fact_check_kind: investment_risk_claim
- fact_check_priority: high
- required_before_broadcast: True

Body:
- 성장의 과실을 함께 나누자는 말은 듣기 좋다.
- 하지만 위험도 함께 나눠야 한다면, 손실이 발생했을 때 재정·운용사·투자자·금융권의 책임선이 중요해진다.
- 국민성장펀드 이야기는 결국 수익보다 위험 배분의 설계로 읽어야 한다.

Sources:
- https://www.korea.kr/news/policyNewsView.do?newsId=148963908&pWise=main&pWiseMain=R3
- https://www.investchosun.com/m/article.html?contid=2026042180102
- https://www.korea.kr/multi/visualNewsView.do?newsId=148964200&pWise=main&pWiseMain=K3

Source refs:
- policy_mechanism: 국민참여형 펀드 모집액, 재정 1200억 원, 자펀드별 손실 우선 부담 구조 확인 (https://www.korea.kr/news/policyNewsView.do?newsId=148963908&pWise=main&pWiseMain=R3, confidence=high, manual_check_required=False)
- counterpoint: 개인 판매, 손실 보전, 관제상품화, 손실 사회화 논란 확인 (https://www.investchosun.com/m/article.html?contid=2026042180102, confidence=medium, manual_check_required=True)
- visual_context: 국민참여형 국민성장펀드 상품구조도 후보 (https://www.korea.kr/multi/visualNewsView.do?newsId=148964200&pWise=main&pWiseMain=K3, confidence=high, manual_check_required=False)

Notes:
[근거] 국민참여형 펀드 구조 + counterpoint. 수익률 전망 금지.

## Section 4. 금융권은 어디까지 위험을 나눌 수 있는가

### Slide 19. 금융권은 어디까지 위험을 나눌 수 있는가

- type: section_title
- covers_key_beats: []
- key_beat_anchors_used: []
- needs_source: False
- needs_fact_check: False
- fact_check_kind: rhetorical_caution
- fact_check_priority: low
- required_before_broadcast: False

Body:
-

Notes:
방송용 전환/질문 slide. 사실 주장으로 과확장하지 말 것.

### Slide 20. 금융권에 “성장에 베팅하라”고 말하는 순간 생기는 문제

- type: explainer
- covers_key_beats: []
- key_beat_anchors_used: []
- needs_source: False
- needs_fact_check: True
- fact_check_kind: policy_effect_claim
- fact_check_priority: high
- required_before_broadcast: True

Body:
- 금융권에 성장산업 투자를 요구하면 곧바로 건전성 문제가 따라온다.
- 위험가중자산이 커지면 자본 부담도 커질 수 있고, 예금자 보호 논리와도 충돌할 수 있다.
- 따라서 생산적 금융은 구호가 아니라 자본규제와 위험분담 설계의 문제다.

Sources:
- https://www.bis.org/bcbs/basel3.htm
- https://www.donga.com/news/Economy/article/all/20251113/132765077/4

Source refs:
- market_finance_view: 은행 자본규제와 위험가중자산 논리 배경 (https://www.bis.org/bcbs/basel3.htm, confidence=high, manual_check_required=False)
- market_finance_view: 장기 인내자본과 은행 건전성 규제 국내 논의 (https://www.donga.com/news/Economy/article/all/20251113/132765077/4, confidence=medium, manual_check_required=True)

Notes:
[근거] BIS Basel III + 국내 인내자본 논의. 국내 감독자료 추가 확인 필요.

### Slide 21. 이 부분은 아직 숫자가 필요하다

- type: production_checklist
- covers_key_beats: []
- key_beat_anchors_used: []
- needs_source: False
- needs_fact_check: True
- fact_check_kind: production_checklist
- fact_check_priority: high
- required_before_broadcast: True

Body:
- 방송 전 숫자 체크리스트: 150조 원 전체 규모, 2026년 30조 원 운용, 국민참여형 6000억 원, 재정 1200억 원, 손실 우선 부담 20% 범위.
- 정책 효과가 아니라 구조를 설명하는 숫자로만 사용한다.
- 추가로 정책금융 실패 사례와 은행 건전성 자료를 더 확인하면 완성도가 올라간다.

Sources:
- https://www.fsc.go.kr/no010101/86834?curPage=2&srchBeginDt=&srchCtgry=&srchEndDt=&srchKey=&srchText=
- https://www.korea.kr/news/policyNewsView.do?newsId=148963908&pWise=main&pWiseMain=R3
- https://www.korea.kr/news/policyNewsView.do?newsId=148961201&pWise=main&pWiseMain=A4
- https://www.investchosun.com/m/article.html?contid=2026042180102
- https://www.bis.org/bcbs/basel3.htm

Source refs:
- primary_official_source: 국민성장펀드 150조/2026년 30조 운용 방안과 투자 방식 확인 (https://www.fsc.go.kr/no010101/86834?curPage=2&srchBeginDt=&srchCtgry=&srchEndDt=&srchKey=&srchText=, confidence=high, manual_check_required=False)
- policy_mechanism: 국민참여형 펀드 모집액, 재정 1200억 원, 자펀드별 손실 우선 부담 구조 확인 (https://www.korea.kr/news/policyNewsView.do?newsId=148963908&pWise=main&pWiseMain=R3, confidence=high, manual_check_required=False)
- official_evidence: AI·반도체 집중 투자와 장기 인내자본 필요성 확인 (https://www.korea.kr/news/policyNewsView.do?newsId=148961201&pWise=main&pWiseMain=A4, confidence=high, manual_check_required=False)
- counterpoint: 개인 판매, 손실 보전, 관제상품화, 손실 사회화 논란 확인 (https://www.investchosun.com/m/article.html?contid=2026042180102, confidence=medium, manual_check_required=True)
- market_finance_view: 은행 자본규제와 위험가중자산 논리 배경 (https://www.bis.org/bcbs/basel3.htm, confidence=high, manual_check_required=False)

Notes:
[제작체크] 숫자는 공식자료 기준으로 재확인. production checklist는 본문보다 notes/appendix 성격.

_Internal production checklist, not a broadcast claim._

### Slide 22. 투자 이야기로 들리지 않게 조심해야 한다

- type: risk
- covers_key_beats: []
- key_beat_anchors_used: []
- needs_source: False
- needs_fact_check: False
- fact_check_kind: rhetorical_caution
- fact_check_priority: low
- required_before_broadcast: False

Body:
- 이 주제는 곧바로 특정 산업·기업·펀드 투자 판단처럼 보일 수 있다.
- 그래서 수익률, 주가, 매수·매도, 유망종목식 표현은 피해야 한다.
- 핵심은 투자 추천이 아니라 위험을 누가 나누느냐는 제도 설계다.

Notes:
do_not_claim guardrail slide. 투자 조언 금지.

### Slide 23. 방송 전 꼭 채워야 할 자료

- type: production_checklist
- covers_key_beats: []
- key_beat_anchors_used: []
- needs_source: True
- needs_fact_check: True
- fact_check_kind: production_checklist
- fact_check_priority: high
- required_before_broadcast: True

Body:
- 방송 전 꼭 채워야 할 자료: 금융위/산은 공식 원문, 국민참여형 펀드 손실분담 구조, AI·반도체 장기 투자 규모, 관치금융/정책금융 실패 반론, 은행 건전성·위험가중자산 자료.
- 지금 evidence pack은 enriched dry run에는 충분하지만, 방송용 완성본에는 추가 counterpoint가 필요하다.

Sources:
- https://www.fsc.go.kr/no010101/86834?curPage=2&srchBeginDt=&srchCtgry=&srchEndDt=&srchKey=&srchText=
- https://ngf.kdb.co.kr/GFMNMN00N00.act
- https://www.korea.kr/news/policyNewsView.do?newsId=148963908&pWise=main&pWiseMain=R3
- https://www.investchosun.com/m/article.html?contid=2026042180102
- https://www.bis.org/bcbs/basel3.htm
- https://www.donga.com/news/Economy/article/all/20251113/132765077/4

Source refs:
- primary_official_source: 국민성장펀드 150조/2026년 30조 운용 방안과 투자 방식 확인 (https://www.fsc.go.kr/no010101/86834?curPage=2&srchBeginDt=&srchCtgry=&srchEndDt=&srchKey=&srchText=, confidence=high, manual_check_required=False)
- primary_official_source: 한국산업은행 국민성장펀드 공식 소개와 운영 주체 확인 (https://ngf.kdb.co.kr/GFMNMN00N00.act, confidence=high, manual_check_required=False)
- policy_mechanism: 국민참여형 펀드 모집액, 재정 1200억 원, 자펀드별 손실 우선 부담 구조 확인 (https://www.korea.kr/news/policyNewsView.do?newsId=148963908&pWise=main&pWiseMain=R3, confidence=high, manual_check_required=False)
- counterpoint: 개인 판매, 손실 보전, 관제상품화, 손실 사회화 논란 확인 (https://www.investchosun.com/m/article.html?contid=2026042180102, confidence=medium, manual_check_required=True)
- market_finance_view: 은행 자본규제와 위험가중자산 논리 배경 (https://www.bis.org/bcbs/basel3.htm, confidence=high, manual_check_required=False)
- market_finance_view: 장기 인내자본과 은행 건전성 규제 국내 논의 (https://www.donga.com/news/Economy/article/all/20251113/132765077/4, confidence=medium, manual_check_required=True)

Notes:
[제작체크] enriched dry run 후에도 방송 전 수동 검증 필요.

_Internal production checklist, not a broadcast claim._

### Slide 24. 금융은 위험을 피하는 기술인가, 좋은 위험을 고르는 기술인가

- type: closing_question
- covers_key_beats: []
- key_beat_anchors_used: []
- needs_source: False
- needs_fact_check: True
- fact_check_kind: policy_effect_claim
- fact_check_priority: medium
- required_before_broadcast: True

Body:
- 생산적 금융의 질문은 “정부 정책이 맞다/틀리다”가 아니다.
- 좋은 위험을 고르는 능력, 손실을 나누는 규칙, 금융권 건전성을 함께 설계할 수 있느냐는 질문이다.
- 국민성장펀드는 그 질문을 보여주는 한 사례일 뿐, 성공을 단정할 수는 없다.

Sources:
- https://www.fsc.go.kr/no010101/86834?curPage=2&srchBeginDt=&srchCtgry=&srchEndDt=&srchKey=&srchText=
- https://www.investchosun.com/m/article.html?contid=2026042180102
- https://www.bis.org/bcbs/basel3.htm

Source refs:
- primary_official_source: 국민성장펀드 150조/2026년 30조 운용 방안과 투자 방식 확인 (https://www.fsc.go.kr/no010101/86834?curPage=2&srchBeginDt=&srchCtgry=&srchEndDt=&srchKey=&srchText=, confidence=high, manual_check_required=False)
- counterpoint: 개인 판매, 손실 보전, 관제상품화, 손실 사회화 논란 확인 (https://www.investchosun.com/m/article.html?contid=2026042180102, confidence=medium, manual_check_required=True)
- market_finance_view: 은행 자본규제와 위험가중자산 논리 배경 (https://www.bis.org/bcbs/basel3.htm, confidence=high, manual_check_required=False)

Notes:
[마무리] 정책 찬반이 아니라 위험분담 설계의 질문으로 닫기.
