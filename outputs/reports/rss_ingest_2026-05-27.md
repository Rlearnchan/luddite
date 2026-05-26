# RSS Ingest Report — 2026-05-27

## Summary

- sources considered: 47
- sources enabled: 10
- sources fetched: 10
- sources skipped: 37
- raw feed items: 703
- unique URLs written: 457
- items written: 457
- duplicate URL appearances: 33
- duplicates skipped: 33
- failures: 0
- output status: `written`
- output preserved reason: ``
- output: `data/inbox/articles/rss_2026-05-27.jsonl`

## Article History

- run_id: `rss_2026-05-27_20260526T1428030`
- previous_run_id: `rss_2026-05-27_20260526T1426521`
- current URLs: 457
- known before: 1397
- known after: 1397
- new to history: 0
- returning known: 457
- previous run URLs: 457
- new since previous run: 0
- dropped since previous run: 0
- percent new since previous run: 0.00%
- percent dropped since previous run: 0.00%
- churn label: `low_churn`
- history ledger: `/Users/bae/Documents/code/luddite/data/candidates/jibi_article_history.jsonl`
- run ledger: `/Users/bae/Documents/code/luddite/data/candidates/jibi_article_runs.jsonl`

### Cadence Recommendation

- recommendation: one_visible_board_per_day_is_enough
- reason: RSS churn is low versus the previous run
- guardrail: use evening runs for observation only, not board replacement

### Source Delta

| source | current | new_to_history | new_since_previous | dropped_since_previous |
| --- | ---: | ---: | ---: | ---: |
| BBC News | 20 | 0 | 0 | 0 |
| NPR | 10 | 0 | 0 | 0 |
| The Conversation | 20 | 0 | 0 | 0 |
| 연합뉴스 경제 | 120 | 0 | 0 | 0 |
| 연합뉴스 산업 | 89 | 0 | 0 | 0 |
| 연합뉴스 세계 | 118 | 0 | 0 | 0 |
| 연합인포맥스 | 20 | 0 | 0 | 0 |
| 정책브리핑 | 20 | 0 | 0 | 0 |
| 한국경제 | 20 | 0 | 0 | 0 |
| 한국은행 | 20 | 0 | 0 | 0 |

### New Since Previous Run Examples

- none

### Dropped Since Previous Run Examples

- none

## Per Source

### manual — Manual Input

- feed_url: ``
- section_name: ``
- fetch_limit: 
- collection_enabled: False
- status: `manual`
- fetch_status: `not_fetched`
- parse_status: `not_parsed`
- item_count: 0
- items_written: 0
- duplicate_skipped: 0
- duplicate_examples:
- failure_count: 0
- oldest_published_at: ``
- newest_published_at: ``
- sample_titles:
- skipped_reason: `skipped_status:manual`
- failure_reason: ``

### google_sheet_jibi_candidates — Google Sheet Jibi

- feed_url: ``
- section_name: ``
- fetch_limit: 
- collection_enabled: False
- status: `sheet`
- fetch_status: `not_fetched`
- parse_status: `not_parsed`
- item_count: 0
- items_written: 0
- duplicate_skipped: 0
- duplicate_examples:
- failure_count: 0
- oldest_published_at: ``
- newest_published_at: ``
- sample_titles:
- skipped_reason: `collection_enabled_false`
- failure_reason: ``

### google_sheet_topic_finding — Google Sheet 주제 찾기

- feed_url: ``
- section_name: ``
- fetch_limit: 
- collection_enabled: False
- status: `sheet`
- fetch_status: `not_fetched`
- parse_status: `not_parsed`
- item_count: 0
- items_written: 0
- duplicate_skipped: 0
- duplicate_examples:
- failure_count: 0
- oldest_published_at: ``
- newest_published_at: ``
- sample_titles:
- skipped_reason: `collection_enabled_false`
- failure_reason: ``

### reuters_manual — Reuters

- feed_url: ``
- section_name: ``
- fetch_limit: 
- collection_enabled: False
- status: `subscription_manual`
- fetch_status: `not_fetched`
- parse_status: `not_parsed`
- item_count: 0
- items_written: 0
- duplicate_skipped: 0
- duplicate_examples:
- failure_count: 0
- oldest_published_at: ``
- newest_published_at: ``
- sample_titles:
- skipped_reason: `skipped_status:subscription_manual`
- failure_reason: ``

### ap_rss_candidate — Associated Press

- feed_url: ``
- section_name: ``
- fetch_limit: 
- collection_enabled: False
- status: `rss_candidate`
- fetch_status: `not_fetched`
- parse_status: `not_parsed`
- item_count: 0
- items_written: 0
- duplicate_skipped: 0
- duplicate_examples:
- failure_count: 0
- oldest_published_at: ``
- newest_published_at: ``
- sample_titles:
- skipped_reason: `collection_enabled_false`
- failure_reason: ``

### bbc_rss_candidate — BBC News

- feed_url: `https://feeds.bbci.co.uk/news/rss.xml`
- section_name: ``
- fetch_limit: 
- collection_enabled: True
- status: `rss_verified`
- fetch_status: `fetched`
- parse_status: `parsed`
- item_count: 33
- items_written: 20
- duplicate_skipped: 0
- duplicate_examples:
- failure_count: 0
- oldest_published_at: `Wed, 30 Apr 2025 14:04:28 GMT`
- newest_published_at: `Tue, 26 May 2026 14:20:56 GMT`
- sample_titles:
  - Sentences of boys spared custody over rape referred to Court of Appeal
  - Iran condemns US strikes as 'gross violation' of ceasefire
  - 'Bullying' and 'overbearing' behaviour behind abrupt BP chairman removal
- skipped_reason: ``
- failure_reason: ``

### guardian_rss_candidate — The Guardian

- feed_url: `https://www.theguardian.com/international/rss`
- section_name: ``
- fetch_limit: 
- collection_enabled: False
- status: `rss_verified`
- fetch_status: `not_fetched`
- parse_status: `not_parsed`
- item_count: 0
- items_written: 0
- duplicate_skipped: 0
- duplicate_examples:
- failure_count: 0
- oldest_published_at: ``
- newest_published_at: ``
- sample_titles:
- skipped_reason: `collection_enabled_false`
- failure_reason: ``

### guardian_business — The Guardian Business

- feed_url: `https://www.theguardian.com/business/rss`
- section_name: ``
- fetch_limit: 
- collection_enabled: False
- status: `rss_verified`
- fetch_status: `not_fetched`
- parse_status: `not_parsed`
- item_count: 0
- items_written: 0
- duplicate_skipped: 0
- duplicate_examples:
- failure_count: 0
- oldest_published_at: ``
- newest_published_at: ``
- sample_titles:
- skipped_reason: `collection_enabled_false`
- failure_reason: ``

### guardian_technology — The Guardian Technology

- feed_url: `https://www.theguardian.com/technology/rss`
- section_name: ``
- fetch_limit: 
- collection_enabled: False
- status: `rss_verified`
- fetch_status: `not_fetched`
- parse_status: `not_parsed`
- item_count: 0
- items_written: 0
- duplicate_skipped: 0
- duplicate_examples:
- failure_count: 0
- oldest_published_at: ``
- newest_published_at: ``
- sample_titles:
- skipped_reason: `collection_enabled_false`
- failure_reason: ``

### guardian_environment — The Guardian Environment

- feed_url: `https://www.theguardian.com/environment/rss`
- section_name: ``
- fetch_limit: 
- collection_enabled: False
- status: `rss_verified`
- fetch_status: `not_fetched`
- parse_status: `not_parsed`
- item_count: 0
- items_written: 0
- duplicate_skipped: 0
- duplicate_examples:
- failure_count: 0
- oldest_published_at: ``
- newest_published_at: ``
- sample_titles:
- skipped_reason: `collection_enabled_false`
- failure_reason: ``

### npr_rss_candidate — NPR

- feed_url: `https://feeds.npr.org/1002/rss.xml`
- section_name: ``
- fetch_limit: 
- collection_enabled: True
- status: `rss_verified`
- fetch_status: `fetched`
- parse_status: `parsed`
- item_count: 10
- items_written: 10
- duplicate_skipped: 0
- duplicate_examples:
- failure_count: 0
- oldest_published_at: `Mon, 25 May 2026 21:51:45 -0400`
- newest_published_at: `Tue, 26 May 2026 09:32:50 -0400`
- sample_titles:
  - Prospects fade for imminent end to Iran war as attacks restart
  - Texas GOP voters vote in race that could shape future of the party -- and the Senate
  - Therapists are using AI to take notes. Is it a useful tool or a breach of trust?
- skipped_reason: ``
- failure_reason: ``

### lemonde_rss_candidate — Le Monde

- feed_url: `https://www.lemonde.fr/rss/une.xml`
- section_name: ``
- fetch_limit: 
- collection_enabled: False
- status: `rss_verified`
- fetch_status: `not_fetched`
- parse_status: `not_parsed`
- item_count: 0
- items_written: 0
- duplicate_skipped: 0
- duplicate_examples:
- failure_count: 0
- oldest_published_at: ``
- newest_published_at: ``
- sample_titles:
- skipped_reason: `collection_enabled_false`
- failure_reason: ``

### bloomberg_manual — Bloomberg

- feed_url: ``
- section_name: ``
- fetch_limit: 
- collection_enabled: False
- status: `subscription_manual`
- fetch_status: `not_fetched`
- parse_status: `not_parsed`
- item_count: 0
- items_written: 0
- duplicate_skipped: 0
- duplicate_examples:
- failure_count: 0
- oldest_published_at: ``
- newest_published_at: ``
- sample_titles:
- skipped_reason: `skipped_status:subscription_manual`
- failure_reason: ``

### ft_manual — Financial Times

- feed_url: ``
- section_name: ``
- fetch_limit: 
- collection_enabled: False
- status: `subscription_manual`
- fetch_status: `not_fetched`
- parse_status: `not_parsed`
- item_count: 0
- items_written: 0
- duplicate_skipped: 0
- duplicate_examples:
- failure_count: 0
- oldest_published_at: ``
- newest_published_at: ``
- sample_titles:
- skipped_reason: `skipped_status:subscription_manual`
- failure_reason: ``

### wsj_manual — Wall Street Journal

- feed_url: ``
- section_name: ``
- fetch_limit: 
- collection_enabled: False
- status: `subscription_manual`
- fetch_status: `not_fetched`
- parse_status: `not_parsed`
- item_count: 0
- items_written: 0
- duplicate_skipped: 0
- duplicate_examples:
- failure_count: 0
- oldest_published_at: ``
- newest_published_at: ``
- sample_titles:
- skipped_reason: `skipped_status:subscription_manual`
- failure_reason: ``

### nyt_manual — New York Times

- feed_url: ``
- section_name: ``
- fetch_limit: 
- collection_enabled: False
- status: `subscription_manual`
- fetch_status: `not_fetched`
- parse_status: `not_parsed`
- item_count: 0
- items_written: 0
- duplicate_skipped: 0
- duplicate_examples:
- failure_count: 0
- oldest_published_at: ``
- newest_published_at: ``
- sample_titles:
- skipped_reason: `skipped_status:subscription_manual`
- failure_reason: ``

### economist_manual — The Economist

- feed_url: ``
- section_name: ``
- fetch_limit: 
- collection_enabled: False
- status: `subscription_manual`
- fetch_status: `not_fetched`
- parse_status: `not_parsed`
- item_count: 0
- items_written: 0
- duplicate_skipped: 0
- duplicate_examples:
- failure_count: 0
- oldest_published_at: ``
- newest_published_at: ``
- sample_titles:
- skipped_reason: `skipped_status:subscription_manual`
- failure_reason: ``

### nikkei_asia_manual — Nikkei Asia

- feed_url: ``
- section_name: ``
- fetch_limit: 
- collection_enabled: False
- status: `subscription_manual`
- fetch_status: `not_fetched`
- parse_status: `not_parsed`
- item_count: 0
- items_written: 0
- duplicate_skipped: 0
- duplicate_examples:
- failure_count: 0
- oldest_published_at: ``
- newest_published_at: ``
- sample_titles:
- skipped_reason: `skipped_status:subscription_manual`
- failure_reason: ``

### yonhap_rss_candidate — 연합뉴스

- feed_url: `https://www.yna.co.kr/rss/news.xml`
- section_name: `latest`
- fetch_limit: 
- collection_enabled: False
- status: `rss_verified`
- fetch_status: `not_fetched`
- parse_status: `not_parsed`
- item_count: 0
- items_written: 0
- duplicate_skipped: 0
- duplicate_examples:
- failure_count: 0
- oldest_published_at: ``
- newest_published_at: ``
- sample_titles:
- skipped_reason: `collection_enabled_false`
- failure_reason: ``

### yonhap_international_rss_candidate — 연합뉴스 세계

- feed_url: `https://www.yna.co.kr/rss/international.xml`
- section_name: `international`
- fetch_limit: 
- collection_enabled: False
- status: `rss_verified`
- fetch_status: `not_fetched`
- parse_status: `not_parsed`
- item_count: 0
- items_written: 0
- duplicate_skipped: 0
- duplicate_examples:
- failure_count: 0
- oldest_published_at: ``
- newest_published_at: ``
- sample_titles:
- skipped_reason: `collection_enabled_false`
- failure_reason: ``

### yonhap_economy — 연합뉴스 경제

- feed_url: `https://www.yna.co.kr/rss/economy.xml`
- section_name: `economy`
- fetch_limit: 120
- collection_enabled: True
- status: `rss_verified`
- fetch_status: `fetched`
- parse_status: `parsed`
- item_count: 120
- items_written: 120
- duplicate_skipped: 0
- duplicate_examples:
- failure_count: 0
- oldest_published_at: `Tue, 26 May 2026 10:28:47 +0900`
- newest_published_at: `Tue, 26 May 2026 21:01:22 +0900`
- sample_titles:
  - 3기신도시 남양주왕숙2 첫 공급서 특공 세자릿수 경쟁률
  - 국민성장펀드 이틀 만에 97.5% 팔려…은행, 온·오프라인 완판
  - 라클라체자이드파인 무순위 청약 경쟁률 최고 1천726대 1
- skipped_reason: ``
- failure_reason: ``

### yonhap_industry — 연합뉴스 산업

- feed_url: `https://www.yna.co.kr/rss/industry.xml`
- section_name: `industry`
- fetch_limit: 120
- collection_enabled: True
- status: `rss_verified`
- fetch_status: `fetched`
- parse_status: `parsed`
- item_count: 120
- items_written: 89
- duplicate_skipped: 31
- duplicate_examples:
  - 내년 최저임금 2차심의…사용자 "업종 구분" 근로자 "도급 적용"(종합) — https://www.yna.co.kr/view/AKR20260526133651530
  - 'T+1 결제주기 단축' 토론회…핵심은 '속도보다 안정적 이행' — https://www.yna.co.kr/view/AKR20260526161400008
  - 스타벅스, 선불카드 전액 환불…'카드깡' 방지차 충전 제한 병행(종합) — https://www.yna.co.kr/view/AKR20260526125252030
- failure_count: 0
- oldest_published_at: `Tue, 26 May 2026 11:09:33 +0900`
- newest_published_at: `Tue, 26 May 2026 19:24:58 +0900`
- sample_titles:
  - 내년 최저임금 2차심의…사용자 "업종 구분" 근로자 "도급 적용"(종합)
  - 'T+1 결제주기 단축' 토론회…핵심은 '속도보다 안정적 이행'
  - 한국타이어 사내하청 노조 "원청 교섭 책임 인정해야"
- skipped_reason: ``
- failure_reason: ``

### yonhap_international — 연합뉴스 세계

- feed_url: `https://www.yna.co.kr/rss/international.xml`
- section_name: `international`
- fetch_limit: 120
- collection_enabled: True
- status: `rss_verified`
- fetch_status: `fetched`
- parse_status: `parsed`
- item_count: 120
- items_written: 118
- duplicate_skipped: 2
- duplicate_examples:
  - "서구 선진국 실질임금 감소 시작…인플레 압박 여파" — https://www.yna.co.kr/view/AKR20260526122100009
  - "엔화, 리라화 제치고 최약체 통화"…외환시장 화제 모은 주장 — https://www.yna.co.kr/view/AKR20260526124000073
- failure_count: 0
- oldest_published_at: `Tue, 26 May 2026 09:19:27 +0900`
- newest_published_at: `Tue, 26 May 2026 23:19:58 +0900`
- sample_titles:
  - 이란 대통령, '전시 차단' 인터넷 87일만에 복구 지시(종합)
  - '키이우 떠나라' 러 위협에…EU, 러 대사대리 불러 항의
  - 쿼드, 호르무즈사태 계기 인태 해양안보 공동감시 추진…中견제(종합)
- skipped_reason: ``
- failure_reason: ``

### yonhap_market — 연합뉴스 마켓+

- feed_url: `https://www.yna.co.kr/rss/market.xml`
- section_name: `market`
- fetch_limit: 120
- collection_enabled: False
- status: `rss_verified`
- fetch_status: `not_fetched`
- parse_status: `not_parsed`
- item_count: 0
- items_written: 0
- duplicate_skipped: 0
- duplicate_examples:
- failure_count: 0
- oldest_published_at: ``
- newest_published_at: ``
- sample_titles:
- skipped_reason: `collection_enabled_false`
- failure_reason: ``

### yonhap_health — 연합뉴스 건강

- feed_url: `https://www.yna.co.kr/rss/health.xml`
- section_name: `health`
- fetch_limit: 120
- collection_enabled: False
- status: `rss_verified`
- fetch_status: `not_fetched`
- parse_status: `not_parsed`
- item_count: 0
- items_written: 0
- duplicate_skipped: 0
- duplicate_examples:
- failure_count: 0
- oldest_published_at: ``
- newest_published_at: ``
- sample_titles:
- skipped_reason: `collection_enabled_false`
- failure_reason: ``

### infomax_manual — 연합인포맥스

- feed_url: `https://news.einfomax.co.kr/rss/allArticle.xml`
- section_name: ``
- fetch_limit: 
- collection_enabled: True
- status: `rss_verified`
- fetch_status: `fetched`
- parse_status: `parsed`
- item_count: 50
- items_written: 20
- duplicate_skipped: 0
- duplicate_examples:
- failure_count: 0
- oldest_published_at: `2026-05-26 15:33:10`
- newest_published_at: `2026-05-26 23:23:47`
- sample_titles:
  - 달러-원, 뉴욕장서 1,505원대 거래
  - 미 달러화 약세…美·이란 합의 기대감 속 마찰 빚기도
  - 이란 "미국, 여러 차례 이란 상선 위협…명백한 휴전 위반"
- skipped_reason: ``
- failure_reason: ``

### hankyung_manual — 한국경제

- feed_url: `https://www.hankyung.com/feed/all-news`
- section_name: ``
- fetch_limit: 
- collection_enabled: True
- status: `rss_verified`
- fetch_status: `fetched`
- parse_status: `parsed`
- item_count: 50
- items_written: 20
- duplicate_skipped: 0
- duplicate_examples:
- failure_count: 0
- oldest_published_at: `Tue, 26 May 2026 18:29:40 +0900`
- newest_published_at: `Tue, 26 May 2026 22:48:19 +0900`
- sample_titles:
  - 美와 협상중인 이란, 240억弗 동결자산 해제 요구
  - 예능 '진짜 사나이'도 발칵…"탁 치면 억" 자막 재조명
  - UBS "메모리칩 장기계약 수혜"…마이크론 목표가 2배 넘게 올려
- skipped_reason: ``
- failure_reason: ``

### mk_manual — 매일경제

- feed_url: `https://www.mk.co.kr/rss/30000001/`
- section_name: ``
- fetch_limit: 
- collection_enabled: False
- status: `rss_verified`
- fetch_status: `not_fetched`
- parse_status: `not_parsed`
- item_count: 0
- items_written: 0
- duplicate_skipped: 0
- duplicate_examples:
- failure_count: 0
- oldest_published_at: ``
- newest_published_at: ``
- sample_titles:
- skipped_reason: `collection_enabled_false`
- failure_reason: ``

### chosunbiz_manual — 조선비즈

- feed_url: ``
- section_name: ``
- fetch_limit: 
- collection_enabled: False
- status: `manual`
- fetch_status: `not_fetched`
- parse_status: `not_parsed`
- item_count: 0
- items_written: 0
- duplicate_skipped: 0
- duplicate_examples:
- failure_count: 0
- oldest_published_at: ``
- newest_published_at: ``
- sample_titles:
- skipped_reason: `skipped_status:manual`
- failure_reason: ``

### sedaily_manual — 서울경제

- feed_url: ``
- section_name: ``
- fetch_limit: 
- collection_enabled: False
- status: `manual`
- fetch_status: `not_fetched`
- parse_status: `not_parsed`
- item_count: 0
- items_written: 0
- duplicate_skipped: 0
- duplicate_examples:
- failure_count: 0
- oldest_published_at: ``
- newest_published_at: ``
- sample_titles:
- skipped_reason: `skipped_status:manual`
- failure_reason: ``

### joongang_manual — 중앙일보

- feed_url: ``
- section_name: ``
- fetch_limit: 
- collection_enabled: False
- status: `manual`
- fetch_status: `not_fetched`
- parse_status: `not_parsed`
- item_count: 0
- items_written: 0
- duplicate_skipped: 0
- duplicate_examples:
- failure_count: 0
- oldest_published_at: ``
- newest_published_at: ``
- sample_titles:
- skipped_reason: `skipped_status:manual`
- failure_reason: ``

### news1_manual — 뉴스1

- feed_url: ``
- section_name: ``
- fetch_limit: 
- collection_enabled: False
- status: `manual`
- fetch_status: `not_fetched`
- parse_status: `not_parsed`
- item_count: 0
- items_written: 0
- duplicate_skipped: 0
- duplicate_examples:
- failure_count: 0
- oldest_published_at: ``
- newest_published_at: ``
- sample_titles:
- skipped_reason: `skipped_status:manual`
- failure_reason: ``

### newsis_manual — 뉴시스

- feed_url: ``
- section_name: ``
- fetch_limit: 
- collection_enabled: False
- status: `manual`
- fetch_status: `not_fetched`
- parse_status: `not_parsed`
- item_count: 0
- items_written: 0
- duplicate_skipped: 0
- duplicate_examples:
- failure_count: 0
- oldest_published_at: ``
- newest_published_at: ``
- sample_titles:
- skipped_reason: `skipped_status:manual`
- failure_reason: ``

### bok — 한국은행

- feed_url: `https://www.bok.or.kr/portal/bbs/P0002353/news.rss?menuNo=200433`
- section_name: `BOK 이슈노트`
- fetch_limit: 
- collection_enabled: True
- status: `official_release`
- fetch_status: `fetched`
- parse_status: `parsed`
- item_count: 100
- items_written: 20
- duplicate_skipped: 0
- duplicate_examples:
- failure_count: 0
- oldest_published_at: `Mon, 19 Jun 2023 14:00:00 +0900`
- newest_published_at: `Thu, 14 May 2026 12:00:00 +0900`
- sample_titles:
  - [제2026-11호] 국내외 자산 토큰화 현황 및 향후 정책 과제
  - [제2026-10호｣ 우리나라 주식 자산효과에 대한 평가
  - [제2026-9호] 우리나라 대외부문의 구조적 변화가 환율에 미치는 영향
- skipped_reason: ``
- failure_reason: ``

### kosis — KOSIS/통계청

- feed_url: ``
- section_name: ``
- fetch_limit: 
- collection_enabled: False
- status: `official_release`
- fetch_status: `not_fetched`
- parse_status: `not_parsed`
- item_count: 0
- items_written: 0
- duplicate_skipped: 0
- duplicate_examples:
- failure_count: 0
- oldest_published_at: ``
- newest_published_at: ``
- sample_titles:
- skipped_reason: `collection_enabled_false`
- failure_reason: ``

### korea_policy_briefing — 정책브리핑

- feed_url: `https://www.korea.kr/rss/pressrelease.xml`
- section_name: `보도자료`
- fetch_limit: 
- collection_enabled: True
- status: `official_release`
- fetch_status: `fetched`
- parse_status: `parsed`
- item_count: 50
- items_written: 20
- duplicate_skipped: 0
- duplicate_examples:
- failure_count: 0
- oldest_published_at: `Tue, 26 May 2026 04:00:00 GMT`
- newest_published_at: `Tue, 26 May 2026 10:13:52 GMT`
- sample_titles:
  - [외교부]외교부, 한-아프리카 외교장관회의 관련 시민사회 정책 제안 접수
  - [국토교통부][장관동정] 김윤덕 장관, "신속한 사고 대응과 철도운행 정상화에 모든 역량 집중할 것"
  - [법무부]정성호 법무장관, 몽골 법·내무장관 면담…'연내 단체비자 도입' 가속화
- skipped_reason: ``
- failure_reason: ``

### kma — 기상청

- feed_url: ``
- section_name: ``
- fetch_limit: 
- collection_enabled: False
- status: `official_release`
- fetch_status: `not_fetched`
- parse_status: `not_parsed`
- item_count: 0
- items_written: 0
- duplicate_skipped: 0
- duplicate_examples:
- failure_count: 0
- oldest_published_at: ``
- newest_published_at: ``
- sample_titles:
- skipped_reason: `collection_enabled_false`
- failure_reason: ``

### world_bank — World Bank

- feed_url: ``
- section_name: ``
- fetch_limit: 
- collection_enabled: False
- status: `official_release`
- fetch_status: `not_fetched`
- parse_status: `not_parsed`
- item_count: 0
- items_written: 0
- duplicate_skipped: 0
- duplicate_examples:
- failure_count: 0
- oldest_published_at: ``
- newest_published_at: ``
- sample_titles:
- skipped_reason: `collection_enabled_false`
- failure_reason: ``

### imf — IMF

- feed_url: ``
- section_name: ``
- fetch_limit: 
- collection_enabled: False
- status: `official_release`
- fetch_status: `not_fetched`
- parse_status: `not_parsed`
- item_count: 0
- items_written: 0
- duplicate_skipped: 0
- duplicate_examples:
- failure_count: 0
- oldest_published_at: ``
- newest_published_at: ``
- sample_titles:
- skipped_reason: `collection_enabled_false`
- failure_reason: ``

### oecd — OECD

- feed_url: ``
- section_name: ``
- fetch_limit: 
- collection_enabled: False
- status: `official_release`
- fetch_status: `not_fetched`
- parse_status: `not_parsed`
- item_count: 0
- items_written: 0
- duplicate_skipped: 0
- duplicate_examples:
- failure_count: 0
- oldest_published_at: ``
- newest_published_at: ``
- sample_titles:
- skipped_reason: `collection_enabled_false`
- failure_reason: ``

### ilo — ILOSTAT

- feed_url: ``
- section_name: ``
- fetch_limit: 
- collection_enabled: False
- status: `official_release`
- fetch_status: `not_fetched`
- parse_status: `not_parsed`
- item_count: 0
- items_written: 0
- duplicate_skipped: 0
- duplicate_examples:
- failure_count: 0
- oldest_published_at: ``
- newest_published_at: ``
- sample_titles:
- skipped_reason: `collection_enabled_false`
- failure_reason: ``

### the_conversation — The Conversation

- feed_url: `https://theconversation.com/global/articles.atom`
- section_name: ``
- fetch_limit: 
- collection_enabled: True
- status: `rss_verified`
- fetch_status: `fetched`
- parse_status: `parsed`
- item_count: 50
- items_written: 20
- duplicate_skipped: 0
- duplicate_examples:
- failure_count: 0
- oldest_published_at: `2026-05-11T18:48:23Z`
- newest_published_at: `2026-05-26T01:00:43Z`
- sample_titles:
  - Entanglement injuries cause prolonged suffering for whales and dolphins – early intervention is crucial
  - Pope Leo warns of AI’s risks to humanity in his first encyclical
  - Why are people obsessed with (and stealing) Pokemon cards again?
- skipped_reason: ``
- failure_reason: ``

### atlas_obscura — Atlas Obscura

- feed_url: `https://www.atlasobscura.com/feeds/latest`
- section_name: ``
- fetch_limit: 
- collection_enabled: False
- status: `rss_verified`
- fetch_status: `not_fetched`
- parse_status: `not_parsed`
- item_count: 0
- items_written: 0
- duplicate_skipped: 0
- duplicate_examples:
- failure_count: 0
- oldest_published_at: ``
- newest_published_at: ``
- sample_titles:
- skipped_reason: `collection_enabled_false`
- failure_reason: ``

### yougov — YouGov

- feed_url: ``
- section_name: ``
- fetch_limit: 
- collection_enabled: False
- status: `manual`
- fetch_status: `not_fetched`
- parse_status: `not_parsed`
- item_count: 0
- items_written: 0
- duplicate_skipped: 0
- duplicate_examples:
- failure_count: 0
- oldest_published_at: ``
- newest_published_at: ``
- sample_titles:
- skipped_reason: `skipped_status:manual`
- failure_reason: ``

### pew — Pew Research

- feed_url: ``
- section_name: ``
- fetch_limit: 
- collection_enabled: False
- status: `manual`
- fetch_status: `not_fetched`
- parse_status: `not_parsed`
- item_count: 0
- items_written: 0
- duplicate_skipped: 0
- duplicate_examples:
- failure_count: 0
- oldest_published_at: ``
- newest_published_at: ``
- sample_titles:
- skipped_reason: `skipped_status:manual`
- failure_reason: ``

### gallup — Gallup

- feed_url: ``
- section_name: ``
- fetch_limit: 
- collection_enabled: False
- status: `manual`
- fetch_status: `not_fetched`
- parse_status: `not_parsed`
- item_count: 0
- items_written: 0
- duplicate_skipped: 0
- duplicate_examples:
- failure_count: 0
- oldest_published_at: ``
- newest_published_at: ``
- sample_titles:
- skipped_reason: `skipped_status:manual`
- failure_reason: ``

### slack_manual — Slack Manual Drop

- feed_url: ``
- section_name: ``
- fetch_limit: 
- collection_enabled: False
- status: `slack`
- fetch_status: `not_fetched`
- parse_status: `not_parsed`
- item_count: 0
- items_written: 0
- duplicate_skipped: 0
- duplicate_examples:
- failure_count: 0
- oldest_published_at: ``
- newest_published_at: ``
- sample_titles:
- skipped_reason: `collection_enabled_false`
- failure_reason: ``

## Failures

- none
