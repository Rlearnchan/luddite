# AI 즉답 시대의 지식기관 역할

> 이 문서는 production Anny output이 아니라 manual/API dry-run sample입니다.
> source attached는 fact-check complete를 의미하지 않습니다.

## Summary

- label: AI knowledge API v9
- description: Controlled API experiment output, not production.
- sections: 5
- slides: 25
- source_urls: 23
- needs_source: 12
- needs_fact_check: 13
- risk_flags: ['official_evidence_missing', 'single_source_dependency']
- failure_modes: ['needs_fact_check_removed_too_aggressively']
- schema_valid: True
- hygiene_passed: False

## Required Fact Checks

- BBC / Royal Observatory 원문 전문 확인
- Royal Observatory 관계자 발언 맥락 확인
- 보조 기사 1건 이상 확보(독립 출처)
- OECD·UNESCO 인용 권고 문구 및 통계 원자료 확인
- 국내 AI 디지털교과서 도입 세부사항(범위·시행일) 확인
- 과학관·박물관 전시·프로그램 사용 허가 및 사진 출처 확인

## Section 1. Seed & Hook

### Slide 1. AI 즉답 시대의 지식기관 역할

- type: title
- covers_key_beats: []
- key_beat_anchors_used: []
- needs_source: False
- needs_fact_check: False
- fact_check_kind: None
- fact_check_priority: None
- required_before_broadcast: None

Body:
- 한 문장 요약: AI가 즉답을 주는 도구가 늘어날 때, 학교와 박물관은 무엇을 가르쳐야 할까?

Notes:
제목 슬라이드. 사실 주장 없음(rhetorical).

### Slide 2. AI 즉답의 편리함 — BBC: 'Instant AI answers can trivialise human intelligence'

- type: hook
- covers_key_beats: ['kb_ai_convenience']
- key_beat_anchors_used: [{'key_beat_id': 'kb_ai_convenience', 'anchor_phrase': 'AI 즉답의 편리함'}]
- needs_source: False
- needs_fact_check: True
- fact_check_kind: None
- fact_check_priority: None
- required_before_broadcast: None

Body:
- AI 즉답의 편리함
- BBC는 왕립천문대 관계자의 발언을 인용해 AI에 대한 '의존' 우려를 전했다.

Sources:
- https://www.bbc.com/news/articles/c2023l60370o?at_medium=RSS&at_campaign=rss

Notes:
Primary seed: BBC 기사 인용. 원문 전문 확인 필요(Manual). fact_check_priority=high; single_source_dependency 위험. production 참고용: BBC 본문 전문 확인 필요.

### Slide 3. 왕립천문대 발언의 의미

- type: explainer
- covers_key_beats: []
- key_beat_anchors_used: []
- needs_source: True
- needs_fact_check: True
- fact_check_kind: None
- fact_check_priority: None
- required_before_broadcast: None

Body:
- BBC가 전한 관측: 기관의 '풍부한 역사'는 인간 지식의 가치를 환기하고, AI에 대한 '의존'은 경계해야 한다는 취지.
- 이 발언은 교육·탐구 습관의 변화 가능성을 문제 제기하는 시드(seed)로 사용 가능.

Sources:
- https://www.bbc.com/news/articles/c2023l60370o?at_medium=RSS&at_campaign=rss

Notes:
BBC 원문 전문 및 발언 맥락 확인 필요(required_before_storyline). 단일 기사 기반이므로 보조 출처 필요.

## Section 2. 증거와 배경

### Slide 1. 생각하는 과정 — 생성형 AI와 정보 다양성

- type: explainer
- covers_key_beats: ['kb_thinking_process']
- key_beat_anchors_used: [{'key_beat_id': 'kb_thinking_process', 'anchor_phrase': '생각하는 과정'}]
- needs_source: False
- needs_fact_check: False
- fact_check_kind: None
- fact_check_priority: None
- required_before_broadcast: None

Body:
- 생각하는 과정
- Microsoft 연구는 생성형 AI가 이용자의 정보 탐색 방식과 접하는 정보의 '다양성'을 바꿀 수 있다고 분석한다.

Sources:
- https://www.microsoft.com/en-us/research/publication/from-searchable-to-non-searchable-generative-ai-and-information-diversity-in-online-information-seeking/

Notes:
Microsoft 연구를 근거로 '중간 과정(질문·비교·검증)'이 생략될 가능성을 제시. 연구결과의 해석은 보수적으로 다뤄야 함.

### Slide 2. OECD의 관점: GenAI는 튜터·파트너가 될 수 있다

- type: data
- covers_key_beats: []
- key_beat_anchors_used: []
- needs_source: False
- needs_fact_check: False
- fact_check_kind: None
- fact_check_priority: None
- required_before_broadcast: None

Body:
- OECD는 생성형 AI의 교육적 잠재력을 인정하면서도, 이익은 명확한 교육 원칙과 설계에 달려있다고 정리한다.

Sources:
- https://www.oecd.org/en/publications/oecd-digital-education-outlook-2026_062a7394-en.html

Notes:
OECD 보고서는 정책·교수 설계 관점의 근거로 유용. 구체 사례·숫자 확인은 필요.

### Slide 3. 접근성 — AI가 교육의 접근성과 개인화를 지원할 가능성

- type: explainer
- covers_key_beats: ['kb_counterpoint_access']
- key_beat_anchors_used: [{'key_beat_id': 'kb_counterpoint_access', 'anchor_phrase': '접근성'}]
- needs_source: False
- needs_fact_check: False
- fact_check_kind: None
- fact_check_priority: None
- required_before_broadcast: None

Body:
- 접근성
- UNESCO는 AI가 적절한 권리 보호·안전장치와 함께 적용될 때 교육 접근성과 개인화에 기여할 수 있다고 제시한다.

Sources:
- https://www.unesco.org/en/articles/ai-and-education-protecting-rights-learners

Notes:
Counterpoint: 접근성·개인화 가능성은 분명한 반론이다. 방송에서는 균형 있게 제시해야 함.

### Slide 4. UNESCO: 권리와 안전장치가 전제돼야 한다

- type: counterpoint
- covers_key_beats: []
- key_beat_anchors_used: []
- needs_source: False
- needs_fact_check: False
- fact_check_kind: None
- fact_check_priority: None
- required_before_broadcast: None

Body:
- UNESCO의 입장: AI는 기회이자 위험이며, 학습자의 권리·안전·포용을 고려한 적용이 필요하다.

Sources:
- https://www.unesco.org/en/articles/ai-and-education-protecting-rights-learners

Notes:
Counterpoint은 핵심: AI의 접근성 이점은 권리·안전 확보와 함께 논의되어야 함.

### Slide 5. 편리함과 지적 근육: 균형 문제

- type: bridge
- covers_key_beats: []
- key_beat_anchors_used: []
- needs_source: False
- needs_fact_check: False
- fact_check_kind: None
- fact_check_priority: None
- required_before_broadcast: None

Body:
- AI가 '바로 답'을 주는 편리함이 있는 반면, 사고의 중간 과정을 어떻게 유지할지 질문을 던져야 한다.

Notes:
전환용 브리지. 사실 주장 최소화(rhetorical bridge / no factual claim).

## Section 3. 지식기관의 대응

### Slide 1. 학교 / 박물관 / 천문관 / 지식기관의 역할

- type: section_title
- covers_key_beats: ['kb_institution_role']
- key_beat_anchors_used: [{'key_beat_id': 'kb_institution_role', 'anchor_phrase': '학교 / 박물관 / 천문관 / 지식기관의 역할'}]
- needs_source: False
- needs_fact_check: False
- fact_check_kind: None
- fact_check_priority: None
- required_before_broadcast: None

Body:
- 이 섹션은 지식기관이 실제로 어떤 방식으로 응답할 수 있는지를 다룬다.

Notes:
섹션 타이틀. 질문형 라벨로서 사실 주장 없음.

### Slide 2. BBC 인용: 왕립천문대의 경고

- type: quote
- covers_key_beats: []
- key_beat_anchors_used: []
- needs_source: True
- needs_fact_check: True
- fact_check_kind: None
- fact_check_priority: None
- required_before_broadcast: None

Body:
- BBC가 전한 발언: Paddy Rodgers는 관측소의 '풍부한 역사'가 인간 지식의 힘을 보여주며 AI에 대한 '의존'을 피해야 한다고 말했다.

Sources:
- https://www.bbc.com/news/articles/c2023l60370o?at_medium=RSS&at_campaign=rss

Notes:
발언의 정확한 맥락과 원문 확인 필요(required_before_storyline, required_before_broadcast). single_source_dependency 표시 고려.

### Slide 3. 국립과학관의 AI 전시(국내 사례)

- type: explainer
- covers_key_beats: []
- key_beat_anchors_used: []
- needs_source: False
- needs_fact_check: False
- fact_check_kind: None
- fact_check_priority: None
- required_before_broadcast: None

Body:
- 국립과학관 전시 소개는 '체험을 통한 학습' 방식이 AI 관련 역량 형성에 사용될 수 있음을 보여준다.

Sources:
- https://www.science.go.kr/eps/cntnts/772/moveCntnts.do

Notes:
전시 사례는 '체험형 교육'의 한 예시. 전시의 교육 효과를 단정하지 않음.

### Slide 4. 국내 정책: 2025년부터 AI 디지털교과서 도입(정책브리핑)

- type: explainer
- covers_key_beats: []
- key_beat_anchors_used: []
- needs_source: True
- needs_fact_check: True
- fact_check_kind: None
- fact_check_priority: None
- required_before_broadcast: None

Body:
- 한국 정부는 학교현장에 AI 디지털교과서 도입을 추진하고 있다(정책 공지).

Sources:
- https://www.korea.kr/news/policyNewsView.do?newsId=148912089

Notes:
정책 공지 출처를 제시. 구체 도입 범위·시행계획 등 원문 확인 필요(required_before_broadcast).

### Slide 5. 박물관·과학관의 역할 재정의

- type: explainer
- covers_key_beats: []
- key_beat_anchors_used: []
- needs_source: True
- needs_fact_check: True
- fact_check_kind: None
- fact_check_priority: None
- required_before_broadcast: None

Body:
- 체험·메이킹·질문 유도 중심의 프로그램은 '바로 답'이 아닌 탐구 과정 자체를 가르치는 장치가 될 수 있다.
- 구체적 프로그램 설계는 기관별로 다르므로 방송 전 사례 확인 필요.

Sources:
- https://www.sciencecenter.or.kr/kor/menu/sub.do?menuId=17_275

Notes:
기관별 프로그램은 사례 확인 필요. 교육 효과를 단정하지 않음.

### Slide 6. 관측소의 역사 교육 vs AI 즉답의 현재

- type: comparison
- covers_key_beats: []
- key_beat_anchors_used: []
- needs_source: True
- needs_fact_check: True
- fact_check_kind: None
- fact_check_priority: None
- required_before_broadcast: None

Body:
- 역사·맥락을 전달하는 기관의 역할은 AI의 즉답과 다른 가치를 제공한다는 점에서 보완적일 수 있다.

Sources:
- https://www.bbc.com/news/articles/c2023l60370o?at_medium=RSS&at_campaign=rss
- https://www.science.go.kr/eps/cntnts/772/moveCntnts.do

Notes:
비교는 개념적 전환을 돕기 위한 슬라이드. 발언 맥락/기관 프로그램은 추가 확인 필요.

### Slide 7. 실무 리스크: 의존·과장·단일출처 의존

- type: risk
- covers_key_beats: []
- key_beat_anchors_used: []
- needs_source: True
- needs_fact_check: True
- fact_check_kind: None
- fact_check_priority: None
- required_before_broadcast: None

Body:
- AI 의존으로 인한 '사고 과정 약화'는 확인된 사실이 아니라 우려이며, 보도·연구의 추가 검증이 필요하다.

Sources:
- https://www.bbc.com/news/articles/c2023l60370o?at_medium=RSS&at_campaign=rss
- https://www.microsoft.com/en-us/research/publication/from-searchable-to-non-searchable-generative-ai-and-information-diversity-in-online-information-seeking/

Notes:
방송 전 BBC 원문·Microsoft 연구의 해석·국내 사례 추가 확보 필요. risk_flags에 single_source_dependency 가능성.

## Section 4. 무엇을 가르칠 것인가?

### Slide 1. 무엇을 가르칠 것인가: 질문의 전환

- type: bridge
- covers_key_beats: ['kb_teach_question']
- key_beat_anchors_used: [{'key_beat_id': 'kb_teach_question', 'anchor_phrase': '무엇을 가르칠 것인가'}]
- needs_source: False
- needs_fact_check: False
- fact_check_kind: None
- fact_check_priority: None
- required_before_broadcast: None

Body:
- 무엇을 가르칠 것인가
- AI를 금지하거나 칭송하는 논쟁보다, 교육 목표와 교과 설계를 재검토하는 것이 필요하다.

Notes:
섹션 전환용 질문. 사실 주장 최소화. 방송 전 UNESCO 프레임 검토 권장.

### Slide 2. UNESCO의 AI 역량 프레임(학생용)

- type: explainer
- covers_key_beats: []
- key_beat_anchors_used: []
- needs_source: True
- needs_fact_check: True
- fact_check_kind: None
- fact_check_priority: None
- required_before_broadcast: None

Body:
- UNESCO는 학생들이 책임감 있고 창의적으로 AI를 활용할 수 있도록 역량을 교육할 것을 권고한다(프레임워크 제시).

Sources:
- https://www.unesco.org/en/articles/ai-competency-framework-students

Notes:
교육·역량 주장에 대해서는 보수적으로 다루어야 함. 기관 프레임은 방송 전 추가 검증 필요(required_before_broadcast).

### Slide 3. OECD 권고 요지: 명확한 교수원칙이 성과를 좌우한다

- type: explainer
- covers_key_beats: []
- key_beat_anchors_used: []
- needs_source: False
- needs_fact_check: False
- fact_check_kind: None
- fact_check_priority: None
- required_before_broadcast: None

Body:
- OECD는 생성형 AI의 잠재력이 실현되려면 명확한 교수 설계(피드백·비판적 사고 훈련 등)가 필요하다고 지적한다.

Sources:
- https://www.oecd.org/en/publications/oecd-digital-education-outlook-2026_062a7394-en.html

Notes:
OECD 권고를 방송용 요약으로 제시. 구체 권고사항은 원문 참조 필요.

### Slide 4. 실무 제안: 질문하기·검증하기·출처 가르치기

- type: explainer
- covers_key_beats: []
- key_beat_anchors_used: []
- needs_source: True
- needs_fact_check: True
- fact_check_kind: None
- fact_check_priority: None
- required_before_broadcast: None

Body:
- 교실과 기관에서 강조할 수 있는 실무 역량 예시: 좋은 질문 만들기, 중간 과정 기록, 출처 검증, 생성물의 한계 설명하기.
- 이것들은 AI를 보완적으로 활용하면서 '사고 과정'을 유지하도록 설계 가능한 요소들이다.

Sources:
- https://www.unesco.org/en/articles/ai-competency-framework-students
- https://www.oecd.org/en/publications/oecd-digital-education-outlook-2026_062a7394-en.html

Notes:
교육적 제안은 프레임을 바탕으로 한 제안적 목록. 교육 효과를 단정하지 않음.

### Slide 5. Counterpoint: 접근성·개인화의 기회도 놓치지 마라

- type: counterpoint
- covers_key_beats: []
- key_beat_anchors_used: []
- needs_source: False
- needs_fact_check: False
- fact_check_kind: None
- fact_check_priority: None
- required_before_broadcast: None

Body:
- UNESCO는 AI 활용이 올바르게 설계되면 교육 접근성과 개인화에서 이점을 줄 수 있다고 강조한다.
- 따라서 '금지'보다 '어떻게 가르칠지'가 핵심 질문이다.

Sources:
- https://www.unesco.org/en/articles/ai-and-education-protecting-rights-learners

Notes:
반대 관점(접근성·포용) 포함. 방송에서는 균형 있게 제시.

### Slide 6. 방송 전 확인 체크리스트

- type: production_checklist
- covers_key_beats: []
- key_beat_anchors_used: []
- needs_source: True
- needs_fact_check: True
- fact_check_kind: None
- fact_check_priority: None
- required_before_broadcast: None

Body:
- 1) BBC 원문 전문 및 Paddy Rodgers 발언 맥락 확인
- 2) BBC 외 보조 기사 최소 1건 확보
- 3) OECD·UNESCO에서 인용한 구체 권고 문구 확인
- 4) 국내 정책(디지털 교과서) 시행범위·시점 확인
- 5) 과학관·박물관 프로그램 사례(문서/사진) 확보 및 사용 동의 확인

Notes:
required_before_broadcast 항목 다수 존재함. 이 슬라이드는 제작용 체크리스트이며 방송 전 모두 확인 필요(required_before_broadcast).

_Internal production checklist, not a broadcast claim._

## Section 5. 마무리 & 질문

### Slide 1. 정보 생태계의 변화가 남긴 불확실성

- type: risk
- covers_key_beats: []
- key_beat_anchors_used: []
- needs_source: True
- needs_fact_check: True
- fact_check_kind: None
- fact_check_priority: None
- required_before_broadcast: None

Body:
- 즉답 도구의 확산은 정보 다양성·출처 검증 습관에 변화를 줄 수 있다는 연구·관찰이 있다.
- 그 범위와 영향은 추가 연구가 필요하다.

Sources:
- https://www.microsoft.com/en-us/research/publication/from-searchable-to-non-searchable-generative-ai-and-information-diversity-in-online-information-seeking/
- https://www.oecd.org/en/publications/oecd-digital-education-outlook-2026_062a7394-en.html

Notes:
교육 효과·인지 저하를 단정하지 않음. 추가 연구·통계 확인 필요.

### Slide 2. 제작 리스크: 단일 출처 의존 경고

- type: risk
- covers_key_beats: []
- key_beat_anchors_used: []
- needs_source: True
- needs_fact_check: True
- fact_check_kind: None
- fact_check_priority: None
- required_before_broadcast: None

Body:
- 이 스토리는 현재 BBC 기사(주요 시드)에 크게 의존함. 보조 기사와 공식 문서 확보가 필수이다.

Sources:
- https://www.bbc.com/news/articles/c2023l60370o?at_medium=RSS&at_campaign=rss

Notes:
single_source_dependency 리스크: 보조 기사 확보 필요.

### Slide 3. 청중 질문

- type: closing_question
- covers_key_beats: ['kb_teach_question']
- key_beat_anchors_used: [{'key_beat_id': 'kb_teach_question', 'anchor_phrase': '무엇을 가르칠 것인가'}]
- needs_source: False
- needs_fact_check: False
- fact_check_kind: None
- fact_check_priority: None
- required_before_broadcast: None

Body:
- AI가 답을 즉시 주는 시대에 학교와 지식기관은 무엇을 가르쳐야 하는가?

Notes:
순수 질문형 클로징. 사실 주장 없음. 방송 토론용 질문으로 사용.

### Slide 4. 짧은 결론 메모

- type: punchline
- covers_key_beats: []
- key_beat_anchors_used: []
- needs_source: True
- needs_fact_check: True
- fact_check_kind: None
- fact_check_priority: None
- required_before_broadcast: None

Body:
- AI는 '바로 답'을 준다. 지식기관은 '어떻게 질문하고 증명할지'를 가르쳐야 한다 — 결론은 행동으로 옮겨야 확인된다.

Sources:
- https://www.unesco.org/en/articles/ai-and-education-protecting-rights-learners

Notes:
결론은 가이드라인 수준. 방송 전 프레이밍·표현 점검 필요.
