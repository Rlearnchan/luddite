# Luddite

Luddite는 슈카월드 리서치 흐름을 돕기 위한 로컬 개발 프로젝트입니다.

지금의 핵심 제품은 자동 PPT 제작기가 아니라, 매일 들어오는 기사와 공식자료 중
방송 소재가 될 만한 후보를 골라 `Jibi` 구글 시트에 올리고, 리서치팀의 짧은
평가를 받아 선별 감각을 보정하는 도구입니다.

## 한눈에 보기

Luddite에는 세 역할이 있습니다.

- `Jibi`: 기사와 공식자료를 수집하고 후보를 선별합니다. 현재 가장 많이 구현된 부분입니다.
- `Anny`: 선별된 후보를 방송용 이야기 구조로 키우는 역할입니다. 아직 운영 실험 전 단계입니다.
- `Piti`: 이야기 구조를 PPT 초안으로 바꾸는 역할입니다. 아직 별도 실험 단계입니다.

현재 운영의 중심은 `Jibi`입니다.

```text
RSS/공식자료 수집
-> 후보 정규화/점수화/묶기
-> 슈카월드 과거 영상 유사도 확인
-> Codex가 제목/설명 문장을 사람이 읽기 좋게 다듬기
-> 구글 시트 Jibi 탭 교체
-> 리서치팀 3인이 한 줄 리뷰
-> 리뷰를 다시 분석해 다음 선별 기준 보정
```

## 현재 상태

2026-05-25 기준으로 가능한 일:

- 연합뉴스, 정책브리핑, 한국은행, Guardian, The Conversation 등에서 RSS 후보를 수집합니다.
- 같은 이야기로 보이는 후보를 묶고, 대표 후보와 서브 링크를 만듭니다.
- 후보를 `Jibi` 구글 시트에 리뷰보드 형태로 올립니다.
- 시트 컬럼은 사람이 보기 좋게 줄여져 있습니다.
- 기존 리뷰가 남아 있으면 실수로 덮어쓰지 않도록 막습니다.
- 로컬 `syuka-ops` snapshot DB를 읽어 슈카월드 과거 영상과의 겹침을 참고합니다.
- 과거 영상 검색은 `슈카월드` 채널만 대상으로 합니다. `머니코믹스` 등 다른 채널은 제외합니다.
- Codex가 과도기적으로 제목과 설명을 사람이 읽기 좋은 문장으로 다듬어 올립니다.

아직 하지 않는 일:

- 자동 스케줄러로 매일 아침 무조건 실행하지 않습니다.
- Slack에 자동으로 올리지 않습니다.
- LLM API를 호출해 후보를 고르지 않습니다.
- 전체 기사 본문을 장기 DB화하지 않습니다.
- `syuka-ops` DB를 수정하지 않습니다. 읽기 전용 snapshot만 봅니다.
- 리서치팀 리뷰가 시작된 같은 날 시트를 임의로 다시 덮어쓰지 않습니다.

## 리뷰 시트

현재 구글 시트 탭 이름은 `Jibi`입니다.

보이는 컬럼:

```text
일시
제목
점수
메인 링크
서브 링크
설명
리뷰-성원
리뷰-동찬
리뷰-형찬
ID
```

점수는 사람이 빠르게 읽도록 `B · 68점` 형식으로 표시합니다.
점수는 승인 지시가 아니라 Jibi의 내부 확신도에 가깝습니다.

리서치팀은 각자 리뷰 칸에 한 줄로 적으면 됩니다.

예:

```text
seed 가능, BOK 자료 두 개는 묶어서 보면 좋음
evidence에 가까움, 단독 주제로는 약함
reject, 투자 뉴스처럼 보임
needs, 숫자와 두 번째 출처 필요
```

## 처음 실행하기

로컬 개발 환경:

```bash
make setup
make test
make doctor
```

구글 시트에 실제로 쓰려면 로컬 환경 변수나
`config/google_sheets.local.yaml`이 필요합니다.

```bash
export LUDDITE_GOOGLE_SPREADSHEET_ID="..."
export LUDDITE_GOOGLE_TARGET_SHEET="Jibi"
export GOOGLE_APPLICATION_CREDENTIALS="/absolute/path/to/service-account.json"
```

서비스 계정 JSON은 절대 커밋하지 않습니다.

## 매일 수동 운영

현재 권장 방식은 수동 실행입니다. 맥북이 켜져 있고, 사용자가 결과를 볼 수 있을 때
한 번 돌리는 방식이 가장 안전합니다.

1. 후보를 뽑고 슈카월드 과거 영상까지 붙인 리뷰보드를 만듭니다.

```bash
make jibi-review-board-refresh-with-syuka JIBI_DATE=YYYY-MM-DD
```

2. Codex가 제목과 설명을 다듬습니다.

다듬은 문장은 아래 파일에 저장됩니다.

```text
outputs/editorial_overrides/jibi_review_board_YYYY-MM-DD.json
```

이 파일은 로컬 산출물입니다. 원래 자동 문구는 metadata sidecar에 남습니다.

3. 최종 보드를 `Jibi` 시트에 교체합니다.

```bash
make jibi-review-board-replace-with-syuka JIBI_DATE=YYYY-MM-DD
```

4. 리서치팀이 각자 리뷰 칸에 한 줄 평가를 씁니다.

5. 리뷰를 요약합니다.

```bash
make jibi-review-feedback JIBI_DATE=YYYY-MM-DD
```

주의:

- 리뷰가 이미 달린 보드는 기본적으로 덮어쓰지 않습니다.
- 정말 덮어써야 할 때만 `JIBI_ALLOW_REVIEW_OVERWRITE=1`을 사용합니다.
- 같은 날 리뷰가 시작된 뒤에는 시트를 다시 교체하지 않는 것이 원칙입니다.

## 주요 산출물

```text
data/inbox/articles/rss_YYYY-MM-DD.jsonl
data/candidates/raw_articles.jsonl
data/candidates/jibi_candidates.jsonl
data/candidates/jibi_scored_candidates.jsonl
data/candidates/jibi_candidate_clusters.jsonl

outputs/daily_digest/YYYY-MM-DD.md
outputs/daily_digest/YYYY-MM-DD_bundle_review_sheet.csv
outputs/daily_digest/YYYY-MM-DD_bundle_review_sheet_metadata.json

outputs/reports/rss_ingest_YYYY-MM-DD.md
outputs/reports/jibi_quality_YYYY-MM-DD.md
outputs/reports/jibi_syuka_snapshot_matches_YYYY-MM-DD.md
outputs/reports/jibi_syuka_refresh_YYYY-MM-DD.md
outputs/reports/jibi_operating_experiment_log.jsonl
```

`outputs/`와 대부분의 `data/candidates/` 산출물은 재생성 가능한 로컬 파일이라 git에
커밋하지 않습니다.

## 내부 문서

자주 보는 문서:

- `docs/runbooks/jibi_daily_ops.md`: Jibi 일일 운영 절차
- `docs/status/jibi_operating_experiment_2026-05-25.md`: 현재 운영 실험 상태
- `docs/product/jibi_mvp_daily_digest_spec.md`: Jibi MVP 기본 제품 스펙
- `docs/integrations/rss_source_strategy.md`: RSS/source 전략
- `docs/integrations/syuka_ops_bridge_plan.md`: syuka-ops 연결 구상

## 개발 원칙

- 운영 시트 보호가 먼저입니다.
- scoring threshold를 성급하게 풀지 않습니다.
- source allowlist는 자동으로 바꾸지 않습니다.
- `syuka-ops`는 읽기 전용 참고 자료로만 씁니다.
- 리서치팀이 읽는 제목/설명 품질이 중요합니다.
- 며칠간 실제 리뷰를 받아 Jibi의 선별 기준을 보정합니다.

## 현재 다음 목표

이번 주 수동 운영 실험의 목표는 단순합니다.

1. 하루 10개 후보를 실제로 올립니다.
2. 리서치팀 3인이 한 줄씩 평가합니다.
3. 어떤 후보가 seed, evidence, reject였는지 모읍니다.
4. Jibi가 놓친 좋은 후보와 잘못 올린 후보를 비교합니다.
5. 다음 PR에서 선별 기준과 설명 문구를 보정합니다.
