# Codex Handoff: Research Pack v0.9.3

## 목적

GPT Pro가 RSS/source strategy와 syuka-ops bridge plan을 리서치했다.
이 문서 묶음을 repo에 반영하고, 0.9.3 jibi digest 품질 보정과 다음 구현 준비에 사용한다.

## 전달 파일

```text
luddite_research_pack_v0_9_3.zip
```

포함 문서:

```text
docs/integrations/rss_source_strategy.md
docs/integrations/syuka_ops_bridge_plan.md
docs/integrations/google_sheet_jibi_candidates_schema.md
docs/research/negative_case_taxonomy.md
docs/product/evidence_cluster_and_story_seed_design.md
docs/product/bdc_mode_design.md
docs/milestones/codex_handoff_research_pack_v0_9_3.md
config/source_registry_recommendation_v0_9_3.yaml
```

## 작업 1. 문서 반영

위 파일을 repo에 반영한다.

README 또는 `docs/status/current_product_direction.md`에는 다음을 짧게 추가한다.

```text
jibi 0.9.x 다음 과제:
- source/RSS 전략 문서화 완료
- syuka-ops bridge는 read-only/search proxy로 설계
- Google Sheet append는 `jibi 후보` staging sheet 기준
- anny는 Article → Candidate → Cluster → Story Seed → Storyline 흐름으로 확장
```

## 작업 2. 0.9.3 digest 품질 보정 유지

이전 GPT Pro review의 0.9.3 보정사항을 계속 반영한다.

핵심:

```text
- reject item은 Top Candidates에 넣지 않음
- 국내 대통령/정당 직접 평가는 hard reject
- 해외 정치 구조 이슈는 editorial_review/gather_more_evidence
- send_to_anny는 evidence 충분성 기준 강화
- possible_expansions는 비우지 않음
- why_interesting은 seed_type별 generic 문장을 줄이고 후보별 구체 문장 사용
- Sheet preview는 `jibi 후보` staging sheet 기준
```

## 작업 3. source registry 보강

기존 `config/sources.yaml`이 있다면 아래 문서를 참고해 정리한다.

```text
config/source_registry_recommendation_v0_9_3.yaml
docs/integrations/rss_source_strategy.md
```

아직 실제 RSS collector를 구현하지 않는다.

단, 향후 검증을 위해 다음 구조를 준비할 수 있다.

```text
rss_candidate → fetch test 통과 → rss_verified
subscription_manual은 자동 fetch 금지
official_release는 seed보다 evidence용
```

## 작업 4. syuka-ops bridge는 문서만 반영

아직 syuka-ops DB 연동 코드를 구현하지 않는다.

문서상 다음 방향만 확정한다.

```text
Phase 1: read-only SQLite bridge
Phase 2: syuka-ops export bridge
Phase 3: API/Slack integration
```

추후 Luddite candidate에는 아래 필드를 붙일 수 있다.

```text
past_video_matches
past_performance_proxy
recent_cooldown_risk
```

## 작업 5. 아직 하지 말 것

```text
- 실제 LLM API 호출
- RSS collector 구현
- syuka-ops 실제 DB 연동
- Google Sheet API append 실제 구현
- Slack bot 구현
- full PPT generator
- image auto collection
```

## 완료 기준

1. 문서 반영
2. source registry recommendation file 반영
3. README/status에 짧은 방향 업데이트
4. make test 통과
