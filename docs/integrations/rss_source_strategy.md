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

## 6. Dedupe

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

0.9.x에서는 RSS 구현 전 source registry만 정리한다.

1. `config/sources.yaml` schema 확정
2. feed endpoint 검증 command 추가
3. validated endpoint만 `rss_verified`로 승격
4. 구독 매체는 `subscription_manual`
5. official sources는 seed보다 evidence cluster에 붙인다

## 11. Initial Source Registry

초안은 `config/source_registry_recommendation_v0_9_3.yaml` 참고.
