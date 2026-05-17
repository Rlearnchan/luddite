# Evidence Cluster and Story Seed Design

작성일: 2026-05-17  
상태: v0.9.3 draft

## 1. 문제의식

`anny`는 기사 하나를 받아 요약하는 도구가 아니다.
사용자 구상에 따르면 anny는 `jibi`가 누적한 뉴스 DB 속에서 관련 기사와 자료를 연결해
스토리라인을 제안해야 한다.

```text
Article → Candidate → Cluster → Story Seed → Storyline
```

## 2. Object Definitions

### Article

원천 기사/자료.

```json
{
  "article_id": "...",
  "title": "...",
  "url": "...",
  "source": "...",
  "published_at": "...",
  "raw_summary": "..."
}
```

### Candidate

jibi가 방송 가능성을 평가한 seed.

```json
{
  "candidate_id": "...",
  "title": "...",
  "seed_type": "absurd_foreign",
  "recommended_action": "gather_more_evidence",
  "possible_expansions": []
}
```

### Evidence Cluster

서로 연결된 후보/기사/공식자료 묶음.

```json
{
  "cluster_id": "...",
  "seed_candidate_ids": [],
  "supporting_articles": [],
  "official_sources": [],
  "statistics_needed": [],
  "chart_candidates": [],
  "past_video_matches": [],
  "risks": [],
  "story_archetype": "A_to_B_explainer"
}
```

### Story Seed

anny가 storyline으로 만들 수 있는 정리된 기획안.

```json
{
  "story_seed_id": "...",
  "title": "...",
  "one_liner": "...",
  "sections_proposal": [],
  "key_beats": [],
  "missing_evidence": []
}
```

## 3. Example: Cocaine Hippos → Campa Cola

```text
Article A: 코카인 하마 인도행
Article B: 암바니 동물센터
Article C: 릴라이언스/Jio 가격전쟁
Article D: 캄파콜라/인도 냉장고 유통망
```

Cluster:

```text
weird animal hook
→ Ambani family scale
→ Reliance market entry pattern
→ India cola war
→ punchline
```

이 흐름은 `코카콜라를 이기는 방법`형이다.

## 4. Cluster Creation Rules

초기 rule-based:

```text
same country
same named entity
same industry
same weird hook
same policy/event
within 30 days
```

LLM/embedding은 나중.

## 5. Cluster Score

```text
cluster_score =
  seed_strength
+ evidence_depth
+ source_diversity
+ key_number_presence
+ past_video_novelty
+ story_arc_clarity
- risk_penalty
- cooldown_penalty
```

## 6. anny Input Bundle

anny는 단일 candidate 대신 bundle을 받는다.

```json
{
  "seed_candidate": {},
  "related_candidates": [],
  "evidence_cluster": {},
  "past_video_matches": [],
  "reference_archetype": "...",
  "length_mode": "standard"
}
```

## 7. Missing Evidence

anny가 바로 작성하지 말고 research task를 남겨야 하는 경우:

```text
공식 통계 없음
단일 구독 기사 의존
날짜/환율/수치 불확실
이미지 출처 불명
민감 주제인데 반론 출처 없음
```

## 8. Milestone Use

0.9:

```text
possible_expansions / evidence_needed를 rule-based로 생성
```

1.1:

```text
evidence_cluster 생성
anny DB-based storyline MVP
```

1.2:

```text
syuka-ops past_video_matches 연결
```
