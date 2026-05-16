# Appendix. Storyline Pattern Catalog

작성일: 2026-05-16
상태: v0.1 draft

## 1. 목적

`storyline.zip`의 RTF 문서들은 anny에 가장 중요한 자료다. PPT가 최종 결과물이라면, storyline은 “초안 사고 과정”을 보여준다.

## 2. 현재 확인 요약

- RTF storyline 약 43개
- 평균 본문 길이 약 2천 자대
- URL 수 편차 큼
- 일부 문서는 URL 0개 또는 제목 정규화 필요
- `utm_source=chatgpt.com` 등 URL 정리가 필요한 경우 있음

## 3. 대표 제목군

```text
"신붓감 찾습니다", 급락하는 중국 혼인율
'야근한 만큼 돈 줘라', 포괄임금 오남용방지 지침 발표
관세와 가뭄으로 미국 소고기 가격 사상 최고 기록
급증하는 전력 수요, 호황을 맞은 전력산업
다시 떠오르는 한일 경제공동체 담론
민원 우려로 축구도 금지된 요즘 학교
백인 우월주의인가, 단순한 광고인가?
세계에서 가장 AI에 진심인 나라
스페이스X의 시가총액은 얼마가 적절할까?
중국 돼지고기 가격 폭락의 비밀
티라노사우루스의 비밀
```

## 4. 분류 체계

각 storyline을 다음 기준으로 태깅한다.

```text
seed_type:
  absurd_foreign
  life_change
  cost_asymmetry
  policy_market_shock
  political_fracture
  geopolitical_prequel
  industry_disruption
  science_technology
  animal_dinosaur
  labor_society
  food_agriculture

story_shape:
  A_to_B
  foreign_to_korea
  policy_to_market
  life_to_system
  history_to_today
  technology_to_punchline

quality_flags:
  strong_hook
  strong_korea_bridge
  source_rich
  source_poor
  needs_fact_check
  sensitive_topic
  likely_subtopic_only
```

## 5. 분석 항목

각 RTF에서 추출할 값:

```json
{
  "file_name": "...rtf",
  "title": "...",
  "plain_text_length": 2238,
  "url_count": 15,
  "section_count_estimated": 4,
  "seed_type": "life_change",
  "story_shape": "life_to_system",
  "has_korea_bridge": true,
  "has_punchline": true,
  "source_richness": "medium",
  "risk_flags": [],
  "summary": "..."
}
```

## 6. anny 학습 포인트

storyline 문서는 다음을 가르친다.

```text
- seed 하나를 어떤 순서로 키우는가
- 자료 링크를 어느 지점에 붙이는가
- 공식 자료와 기사 자료를 어떻게 섞는가
- 최종 PPT보다 거친 표현/아이디어가 어떻게 정리되는가
- 어떤 hook이 PPT까지 살아남는가
```

## 7. Codex 작업 항목

```text
[ ] RTF parser 안정화
[ ] URL 추출 및 canonicalization
[ ] 제목 정규화
[ ] section boundary 추정
[ ] storyline inventory 재생성
[ ] storyline_clusters.csv 생성
```
