# Jibi Operating Experiment Status — 2026-05-25

이 문서는 2026-05-25 기준 Jibi 운영 실험의 현재 위치를 정리한다.

## 현재 목표

Jibi의 현재 목표는 완전 자동 편집자가 되는 것이 아니다.

현재 목표는 매일 후보 10개를 실제 리서치팀에게 보여주고, 짧은 평가를 받아
선별 기준을 보정하는 것이다.

## 현재 가능한 것

- RSS와 공식자료를 날짜 단위로 수집한다.
- URL 단위 article history를 남겨 같은 날/다음 날 수집 변화량을 볼 수 있다.
- 후보를 정규화하고, 점수화하고, 유사 후보를 묶는다.
- `Jibi` 구글 시트에 리뷰보드 형태로 후보를 교체한다.
- 리뷰 컬럼이 이미 채워져 있으면 기본적으로 덮어쓰지 않는다.
- syuka-ops snapshot DB를 읽기 전용으로 조회한다.
- 과거 영상 유사도는 슈카월드 채널만 대상으로 본다.
- 과거 영상 제목, 일자, 조회수, 좋아요 수를 참고 정보로 붙인다.
- Codex editorial override로 `제목`과 `설명`을 사람이 읽기 좋은 문장으로 다듬는다.

## 현재 리뷰보드 형태

보이는 컬럼은 다음 10개다.

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

점수 표기는 `B · 68점` 형식이다.

## 표준 수동 실행 흐름

```bash
make jibi-review-board-refresh-with-syuka JIBI_DATE=YYYY-MM-DD
```

이 명령은 리뷰보드를 만들고, syuka bridge query를 만들고, 로컬 syuka snapshot을
조회한 뒤 다시 렌더한다. 이 단계는 구글 시트에 쓰지 않는다.

Codex 또는 사용자는 아래 파일에 제목/설명 override를 작성한다.

```text
outputs/editorial_overrides/jibi_review_board_YYYY-MM-DD.json
```

최종 확인 뒤 시트를 교체한다.

```bash
make jibi-review-board-replace-with-syuka JIBI_DATE=YYYY-MM-DD
```

리뷰가 끝나면 피드백 요약을 돌린다.

```bash
make jibi-review-feedback JIBI_DATE=YYYY-MM-DD
```

## 2026-05-25 리허설 결과

2026-05-25 리허설에서는 다음을 확인했다.

- RSS 수집: 446건
- 보드 후보: 10개
- syuka snapshot 상태: usable
- syuka 검색 대상: 슈카월드 2,269개 영상
- 시트 교체: 성공
- append errors: 0
- review comment overwrite guard: 정상

중간에 발견한 이슈와 처리:

- `underwater` 안의 `rwa`가 RWA 자산 토큰화로 오인되는 버그를 수정했다.
- syuka snapshot에서 머니코믹스 영상이 함께 검색되는 문제를 수정했다.
- 과거 영상 검색 대상을 `channel_key=syukaworld` 또는 `channel_name=슈카월드`로 제한했다.
- 점수 표기를 `B · 68점`으로 줄였다.

## 운영 원칙

- 하루 한 번 보드를 올리는 것을 기본으로 한다.
- 리뷰가 시작된 뒤에는 같은 날 보드를 다시 교체하지 않는다.
- 꼭 교체해야 할 때만 기존 리뷰를 snapshot한 뒤 명시적으로 overwrite한다.
- syuka 유사도는 참고 신호일 뿐, 자동 reject나 자동 promote 신호가 아니다.
- Codex editorial override는 당분간 유지한다. 실험 목적은 순수 자동 copy가 아니라
  Jibi가 고른 후보가 현실적인 리뷰 문맥에서 쓸 만한지 확인하는 것이다.

## 아직 남은 일

- 며칠치 리서치팀 리뷰를 모아 seed/evidence/reject 패턴을 분석한다.
- Codex가 수동으로 다듬은 제목/설명을 향후 자동 copy heuristic 개선 데이터로 쓴다.
- syuka 유사도 매칭의 broad keyword false positive를 계속 줄인다.
- 좋은 near-miss가 Top 10 밖으로 밀리는 경우를 따로 추적한다.
- article history는 아직 JSONL 기반이다. 검색/조인/보존 요구가 커지면 SQLite 전환을 검토한다.
