# RSS / Source Strategy for jibi v0.9.3

작성일: 2026-05-17  
상태: research/design draft

## 1. 목적

`jibi`의 단기 목표는 “뉴스를 많이 긁는 것”이 아니라, 리서치팀이 아침에 실제로 클릭해볼 만한
슈카월드 후보 seed 10개를 안정적으로 제안하는 것이다.

따라서 source 전략은 다음 원칙을 따른다.

```text
해외 seed 우선 → 국내 연결/공식자료 보강 → 리서치팀 digest
```

사용자 우선순위:

```text
조회수 가능성 proxy
→ 자료의 풍부함
→ 숫자/통계
→ 엥? 하는 hook
→ 농담/밈 회수
→ 시의성
```

## 2. Source Type

`config/sources.yaml`의 source type은 아래처럼 분리한다.

| type | 의미 | 구현 우선순위 |
|---|---|---:|
| `rss_verified` | 실제 fetch 테스트를 통과한 RSS/Atom/JSON Feed | 높음 |
| `rss_candidate` | 알려진 feed 후보이나 아직 검증 필요 | 중간 |
| `subscription_manual` | 구독 매체. 자동 fetch 대신 사람이 링크/요약 입력 | 높음 |
| `manual` | 사람이 넣는 공개 URL/기사 | 높음 |
| `google_news_query` | Google News RSS query. broad discovery용, 최종 출처 아님 | 중간 |
| `official_release` | 정부/기관/통계/공시. seed보다 fact-check/evidence용 | 높음 |
| `sheet` | 기존 Google Sheet 또는 manual export | 높음 |
| `slack` | 나중에 Slack으로 들어오는 사용자 입력 | 낮음 |

## 3. Source Group

### 3.1 primary_wire

목적: 전 세계 breaking seed, geopolitical / economy / unusual story seed 탐색.

후보:

```text
Reuters
AP
BBC
Guardian
NPR
Le Monde
```

주의:

- Reuters/AP는 “source quality”는 높지만 공개 RSS endpoint는 안정성을 매번 검증해야 한다.
- BBC/Guardian/NPR/Le Monde류는 RSS/section feed가 비교적 다루기 쉬운 편이다.
- Le Monde의 RSS 안내처럼 일부 매체는 RSS 사용을 개인/비상업적 용도로 제한하거나 별도 허가를 요구할 수 있다. 내부 업무라도 terms 확인이 필요하다.

### 3.2 premium_manual

목적: 좋은 seed, 깊은 맥락, 숫자/그래프, 글로벌 트렌드.

후보:

```text
Bloomberg
Financial Times
Wall Street Journal
New York Times
Economist
Nikkei Asia
```

운영 원칙:

- 자동 전문 fetch는 하지 않는다.
- visible digest에는 링크 + 짧은 요약만 둔다.
- 구독 원문 전문을 Google Sheet visible area에 넣지 않는다.
- 필요하면 사람이 링크를 열어 확인한다.
- `subscription_source_only` risk flag를 붙일 수 있다.

### 3.3 korea_business

목적: 국내 연결, 한국 시장/정책/기업/생활 이슈 보강.

후보:

```text
연합뉴스
연합인포맥스
한국경제
매일경제
서울경제
조선비즈
중앙일보
동아일보
뉴스1
뉴시스
```

운영 원칙:

- 국내 이슈 seed는 정치 직접 평가를 피한다.
- 정책/시장/생활 구조로 확장될 수 있을 때만 상위 노출한다.
- 국내 대통령/정당 직접 평가 프레임은 hard reject 또는 blocked policy.

### 3.4 official_evidence

목적: anny / fact-check / numbers 보강.

후보:

```text
한국은행
통계청 / KOSIS
금융감독원
공정거래위원회
기상청
World Bank
IMF
OECD
UN Data / Population Division
FRED
Eurostat
IEA
ILO / ILOSTAT
```

운영 원칙:

- seed 발견보다는 evidence cluster에 붙인다.
- 공식자료가 붙으면 `evidence_depth`와 `numbers_strength`를 올린다.
- 공식자료가 없고 단일 기사만 있으면 `gather_more_evidence`.

### 3.5 weird_culture_science

목적: `엥?` hook, 동물/생활문화/과학/트렌드 seed.

후보:

```text
The Conversation
Atlas Obscura
Guardian science / animals / environment
AP oddities / science
Euronews culture / environment
Our World in Data
YouGov
Pew Research
Gallup
```

운영 원칙:

- 단발성 weird news는 `keep_for_later`.
- 시장/사회/산업/제도 구조로 커질 때 상위 노출.
- 코카인 하마 → 암바니 → 인도 콜라 전쟁처럼 “A로 시작해서 B를 설명”하면 높은 점수.

## 4. Collection Cadence

### Daily background collection

jibi는 모든 요일 수집한다.

```text
00:30 KST  overnight global pass
07:30 KST  weekday morning digest build
12:30 KST  domestic / official pass
18:30 KST  domestic close / US pre-market pass
```

MVP에서는 scheduler를 구현하지 않는다. 문서상 목표만 둔다.

### Weekday morning digest

```text
월~금 오전: Top Candidates 10개 digest
```

주말은 수집은 하되 digest 발송은 옵션으로 둔다.

## 5. Feed Fetch Policy

RSS/Atom/JSON feed fetcher 구현 시 지켜야 할 원칙:

```text
- source별 fetch interval / backoff
- etag / last_modified 저장
- 304 Not Modified 처리
- user-agent 명시
- timeout / retry 제한
- feed parse failure 기록
- source health report
- full article scrape 금지 by default
- feed item title/summary/url/published 중심 저장
```

ETag/If-None-Match는 변경되지 않은 feed를 다시 받을 때 304 Not Modified를 받을 수 있게 해 네트워크와 source 부담을 줄이는 표준적인 캐싱 방식이다.

## 5.1 Milestone 1.1 RSS Probe

1.1은 24/7 RSS collector가 아니라 endpoint discovery / fetch test / parse
test까지만 수행한다.

```text
make probe-rss-sources
luddite probe-rss-sources --limit 3 --timeout 5
```

기본 safe mode:

```text
- rss_candidate만 검사
- subscription_manual skip
- manual skip
- official_evidence / official_release skip unless explicit flag
- config/sources.yaml 자동 수정 금지
```

출력:

```text
outputs/reports/rss_probe_YYYY-MM-DD.md
data/manifests/rss_probe_results.jsonl
```

Probe 결과가 `promote_to_rss_verified`로 나오더라도 source registry 승격은
사람이 report와 약관 리스크를 확인한 뒤 수동으로 한다. `feed_url`이 없는
source는 homepage 기준 후보 path(`/rss`, `/rss.xml`, `/feed`, `/feed.xml`,
`/atom.xml`, `/feeds`, `/news/rss`, `/world/rss`, `/business/rss`,
`/economy/rss`)를 제한적으로 시도하며, 이 경우 report에
`terms_check_required`를 남긴다.

## 5.2 Milestone 1.1.1 Feed Discovery Quality

1.1.1은 여전히 collector가 아니다. 목적은 `rss_candidate` endpoint 검증
품질을 높이고, 기술 검증과 운영 수집 허용을 분리하는 것이다.

Source registry는 아래 필드를 지원한다.

```text
feed_url_candidates
verified_feed_url
terms_check_required
collection_enabled
last_probe_status
last_probe_at
failure_reason
```

운영 해석:

```text
status=rss_verified        fetch + parse 기술 검증 통과
collection_enabled=false   실제 운영 수집은 아직 꺼짐
terms_check_required=true  약관/사용 범위 확인 필요
```

따라서 The Guardian / Atlas Obscura처럼 fetch+parse가 성공한 source도 약관
확인 전에는 다음 형태가 권장된다.

```yaml
status: rss_verified
verified_feed_url: <successful feed url>
terms_check_required: true
collection_enabled: false
```

1.1.1 probe는 homepage HTML에서 feed autodiscovery도 시도한다.

```html
<link rel="alternate" type="application/rss+xml" href="...">
<link rel="alternate" type="application/atom+xml" href="...">
```

상대경로는 absolute URL로 변환한다. homepage fetch도 timeout을 적용하며,
autodiscovery 실패는 `failure_reason`에 남긴다.

Known path 후보는 다음까지 확장한다.

```text
/rss
/rss.xml
/feed
/feed.xml
/atom.xml
/feeds
/feeds/rss
/news/rss
/news/rss.xml
/world/rss
/world/rss.xml
/business/rss
/business/rss.xml
/economy/rss
/economy/rss.xml
/international/rss
/international/rss.xml
```

선택적으로 `--write-suggested-patch`를 사용하면
`outputs/reports/rss_probe_suggested_sources_patch.yaml`에 수동 적용용 승격
초안을 생성한다. 이 파일은 자동 적용되지 않는다.

## 5.3 Milestone 1.1.2 Terms / Enablement Gate

1.1.2는 기술적으로 확인된 feed를 source registry에 수동 반영하되,
운영 수집은 계속 꺼두는 단계다.

검토 문서와 allowlist:

```text
docs/integrations/rss_terms_enablement_review.md
config/rss_collection_allowlist.yaml
```

1.2 RSS item ingestion에 들어가기 위한 조건:

```text
- collection_enabled=true source가 최소 2-3개
- terms_check_required source는 확인 전 true로 켜지지 않음
- 저장 범위는 title/url/published_at/source/short summary 중심
- 기사 전문 저장 금지
- source_url_canonical / duplicate_key 생성
- import-articles 파이프라인과 연결
```

기술 검증 반영 후에도 Le Monde는 개인/비전문/비집단 사용 조건 리스크가
있으므로 `collection_enabled=false`를 유지한다.

Source status model:

| status | 의미 |
|---|---|
| `rss_candidate` | 후보 endpoint, 아직 검증 안 됨 |
| `rss_verified` | fetch + parse test 통과 |
| `rss_failed` | endpoint 후보 실패. reason은 probe report에 기록 |
| `subscription_manual` | 구독 매체. 자동 fetch 금지 |
| `manual` | 사람이 링크 입력 |
| `official_evidence` | seed보다 evidence 보강용 |
| `disabled` | 임시 비활성 |

## 6. Dedupe

## 5.4 Milestone 1.2 RSS Item Ingestion MVP

1.2는 24/7 collector가 아니다. `config/rss_collection_allowlist.yaml`에서
`collection_enabled=true`인 source의 `verified_feed_url`을 한 번 fetch해서
기존 article inbox/import 흐름에 넣을 JSONL을 만드는 단계다.

명령:

```text
make fetch-rss-articles
luddite fetch-rss-articles --limit-per-source 20
luddite import-articles --input-dir data/inbox/articles
make jibi-digest
```

출력:

```text
data/inbox/articles/rss_YYYY-MM-DD.jsonl
outputs/reports/rss_ingest_YYYY-MM-DD.md
```

저장 범위:

```text
title
url / source_url_canonical
published_at
source / source_id
short feed summary only
collector=rss
duplicate_key
collected_at
tags
```

기사 전문 저장, 24/7 scheduling, Google Sheet 자동 append, Slack bot, LLM API
호출은 1.2 범위가 아니다.

1차 중복 제거:

```text
canonical_url
```

2차 중복 제거:

```text
title_normalized_hash
source + published_day + title_similarity
```

3차 story cluster:

```text
same named entities
same event
same numbers
same source article syndication
```

필수 필드:

```text
duplicate_key
source_url_canonical
first_seen_at
last_seen_at
seen_count
source_count
```

## 7. Candidate Source Priority

추천 초기 priority:

| source group | source role | jibi use |
|---|---|---|
| primary_wire | seed discovery | high |
| premium_manual | seed / context | high, manual |
| korea_business | domestic bridge | medium/high |
| official_evidence | evidence | high for anny |
| weird_culture_science | hook | medium/high |
| google_news_query | broad discovery | low/medium; not final source |

## 8. Digest Filtering

Top Candidates에는 아래 action만 포함한다.

```text
send_to_anny
gather_more_evidence
editorial_review
keep_for_later
```

아래 action은 별도 section으로 분리한다.

```text
reject
blocked_policy
```

## 9. Political Rule

Hard reject:

```text
국내 대통령/정당 직접 평가
특정 정당 지지/비판
국내 정치인 호불호/인성/가십
국내 정쟁성 실시간 발언
```

Editorial review:

```text
해외 정치 균열
선거 결과가 경제/사회 구조와 연결
포퓰리즘 / 지역 격차 / 채권시장 / 이민 / 노동자 계층 이동
```

## 10. Implementation Advice

0.9.x에서는 RSS 구현 전 source registry만 정리했다. 1.1부터 probe를
추가했고, 1.2부터는 collection_enabled=true인 검증 feed만 대상으로 하는
one-shot RSS item ingestion을 허용한다.

1. `config/sources.yaml` schema 확정
2. `rss_candidate`는 아직 endpoint가 검증되지 않은 후보 상태로 둔다
3. RSS collector 구현 전 endpoint discovery / fetch test / parse test를 수행한다
4. validated endpoint만 `rss_verified`로 승격
5. 구독 매체는 `subscription_manual`로 두고 자동 fetch하지 않는다
6. official sources는 seed보다 evidence cluster에 붙인다

## 12. Milestone 1.2.1 Ingest Gate

1.2.1의 허용 범위:

```text
make fetch-rss-articles
data/inbox/articles/rss_YYYY-MM-DD.jsonl
outputs/reports/rss_ingest_YYYY-MM-DD.md
```

운영 원칙:

- 24/7 collector나 scheduler는 아니다.
- Google Sheet 자동 append와 연결하지 않는다.
- feed summary/description만 저장하고 기사 전문은 저장하지 않는다.
- run 안에서 `duplicate_key`와 `source_url_canonical` 중복을 skip한다.
- report에는 source별 fetched/written/duplicate/failure/sample title을 남긴다.
- Top Candidates는 동일 source가 과도하게 쏠리지 않도록 기본 최대 3개로 제한한다.

1.2.1 smoke allowlist:

```text
enabled: BBC, NPR, Atlas Obscura, 연합인포맥스, 한국경제
disabled: Guardian, Le Monde, 매일경제, 한국은행, 정책브리핑, 연합뉴스
```

한국은행/정책브리핑은 evidence source라 계속 `collection_enabled=false`를 유지한다.
연합뉴스는 `retry_later` 상태로 남기고 manual input을 허용한다.

## 13. Milestone 1.2.2 Candidate Quality Gate

RSS item은 단일 feed item이므로 기본적으로 보수적으로 본다. Top Candidates
선정 순서는 다음과 같다.

```text
score -> quality gate -> action/reject filtering -> source balance -> Top Candidates
```

Top Candidates에서 제외하거나 강등하는 패턴:

```text
sports_only
accident_single_event
pure_place_listing
single_person_anecdote
generic_local_incident
live_politics_or_statement
single_stock_or_asset_frame
empty_summary
```

보정 원칙:

- BBC sport path/title은 기본 reject/downrank.
- NPR live politics는 editorial_review 이상으로 보수 처리.
- Atlas Obscura `/places/` 중심 place listing은 Top Candidates에서 제외.
- 연합인포맥스/한국경제의 단일 종목, 자금조달, 자산가격 기사는 투자/홍보 리스크를 붙인다.
- 한국경제처럼 empty summary가 많은 source는 title만으로 과대평가하지 않는다.
- `industry_disruption`은 공급망, 전력망, 데이터센터, 반도체, 배터리, 물류,
  규제, 생산 병목 같은 구조 신호가 있을 때만 부여한다.
- `cost_asymmetry`는 cheap-vs-expensive, drone-vs-missile, interceptor cost,
  budget exhaustion 같은 비용 교환비 신호가 있을 때만 부여한다.
- 품질 리포트는 `outputs/reports/jibi_quality_YYYY-MM-DD.md`에 쓴다.

## 14. Milestone 1.2.3 Editorial Scoring Polish

1.2.3에서는 넓은 `industry_disruption` 분류를 줄이고, editorial category를
더 좁게 붙인다.

```text
productive_finance_policy
industrial_policy_rnd
single_company_financing
market_rate_stress
ai_knowledge_institution
infrastructure_project_failure
climate_policy_conflict
```

보정 원칙:

- 단일 기업 자금조달/증자/상장/실적/종목성 item은
  `corporate_promo_risk`, `investment_advice_risk`, `single_company_frame`을 붙인다.
- Trump/immigration/DEI/election/president/administration frame은
  `political_sensitivity`로 보고 Top Candidate에 보수적으로 반영한다.
- 채권금리/환율/코인/단일 자산가격 item은 `market_rate_stress` 또는
  `single_stock_or_asset_frame`으로 보고 투자 조언 리스크를 붙인다.
- visible `why_interesting`은 scoring/debug reason이 아니라 후보별 editorial
  판단 문장이어야 한다.
- generic rationale만 가진 `other` 후보는 Top Candidates에서 제외한다.

## 15. Milestone 1.3 Evidence Cluster / Story Seed

1.3에서는 개별 RSS candidate를 바로 anny로 넘기지 않고, rule-based
cluster/story seed로 묶는다.

```text
Article -> Candidate -> Cluster -> Story Seed -> anny storyline later
```

출력:

```text
data/candidates/jibi_candidate_clusters.jsonl
data/candidates/anny_story_seed_handoff.jsonl
data/candidates/anny_input_bundles.jsonl
outputs/reports/jibi_clusters_YYYY-MM-DD.md
outputs/reports/anny_input_bundles_YYYY-MM-DD.md
outputs/daily_digest/YYYY-MM-DD_clusters.md
outputs/daily_digest/YYYY-MM-DD_story_seed_handoff.md
```

원칙:

- LLM API 호출 없이 `editorial_category`, `story_key`, title keyword, source,
  risk/action 정보를 이용해 obvious same-topic grouping만 수행한다.
- cluster 단위로 `ready_for_anny`, `needs_more_evidence`, `editorial_review`,
  `keep_for_later`, `reject` readiness를 판단한다.
- 1.3.1에서는 cluster마다 `quality_flags`, `handoff_priority`,
  `anny_handoff_ready`를 붙인다. 전체 cluster는 audit JSONL/report에 남기되,
  anny handoff에는 `needs_more_evidence`/`editorial_review` 중심의 named
  story seed만 노출한다.
- `generic_story_reason`, `singleton_thin_evidence`, `source_roundup_item`,
  `pure_politics_statement`, `no_korea_or_structure_bridge`가 붙은 약한
  `other` cluster는 human-facing handoff에서 숨긴다.
- schema에는 `official_evidence_needed`, `suggested_official_sources`,
  `past_video_matches`, `syuka_ops_query_terms`, `llm_enrichment_needed`를 미리 둔다.
- 1.4에서는 handoff record를 anny input bundle로 변환한다. Bundle은
  `core_question`, candidate articles, `suggested_story_structure`,
  `do_not_claim`, `needs_fact_check`를 포함하지만 full storyline은 아직 만들지 않는다.
- full anny storyline generation, embedding clustering, syuka-ops DB 연동은 아직 하지 않는다.

## 16. Initial Source Registry

초안은 `config/source_registry_recommendation_v0_9_3.yaml` 참고.
