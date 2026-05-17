# Source Integration Plan v0.8

## 1. 현재 확인된 source

### Luddite repo

현재 Luddite는 parser smoke, corpus insight, golden fixtures, jibi/anny/piti eval runners까지 갖춘 상태다.

### Google Drive / PPT corpus

사용자 허용 범위:

```text
Google Drive는 보수적으로 접근.
슈카월드 PPT 자료만 참고.
```

활용:

```text
- 최신 PPT: format/story archetype/golden fixture
- 과거 PPT: archetype 확장
- 실패/미사용 PPT: negative/edge cases
```

### Google Sheet

현재 역할:

```text
- 주제 찾기: jibi label/eval source
- 방송 주제: final title mapping 후보
- 슈카월드 채널: video title/view metadata
- 리서치 인수인계: redacted policy/risk/source guide
```

초기 운영 UI로도 Google Sheet가 적합하다.

### Notion

사용자 허용:

```text
노션은 개인용이라 마음껏 사용 가능.
```

활용:

```text
- Sketch DB
- 채택/방송 링크
- BDC/아이디어 기록
```

### syuka-ops

GitHub에서 `Rlearnchan/syuka-ops` repository 접근 가능.

README 기준 syuka-ops는 다음을 목표로 한다.

```text
1. 슈카월드 영상 메타데이터, 썸네일, 한국어 자막 수집
2. Slack에서 위 정보를 조회해서 직원 업무 지원
```

SQLite 기반이며 주요 테이블로 `videos`, `transcripts`, `download_attempts`가 정리되어 있고, 자막/썸네일/영상 메타데이터를 저장한다. 또한 Slack 조회 봇은 `/syuka search`, `/syuka transcript`, `/syuka 광고찾기`, `/syuka 썸네일` 등 검색/조회 흐름을 지원한다.

## 2. syuka-ops와 Luddite 연결 구상

사용자가 제안한 핵심 아이디어:

```text
seed/storyline/PPT -> YouTube final title/view/transcript와 유사도 연결
```

가능한 연결:

```text
Luddite candidate/storyline/deck title
-> syuka-ops videos.title / transcripts / video_analysis
-> similarity score
-> final YouTube title / view_count / upload_date
-> topic performance proxy
```

이 연결은 `jibi`의 조회수 proxy와 positive/negative feedback에 매우 중요하다.

## 3. source 연결 우선순위

단기:

```text
1. Google Sheet output
2. Slack digest/query output
3. syuka-ops read-only metadata import
```

중기:

```text
4. syuka-ops similarity matching
5. Google Drive PPT corpus expansion
6. Notion Sketch DB mapping
```

후기:

```text
7. RSS/뉴스 24/7 collector
8. Google Sheets API direct fetch
9. Drive direct sync
```

## 4. 보안/노출 정책

사용자 기준 외부 노출 금지:

```text
- 내부 계정
- 광고주 정보
- 미공개 방송 주제
- 대표님/직원 관련 내부 농담
- 채용/급여 관련 내부 자료
```

구독 기사 원문:

```text
- 내부 저장은 가능
- 사람이 보는 output은 링크 + 짧은 excerpt 중심
- PPT notes도 링크 중심
```

## 5. BDC

BDC는 MVP에서는 핵심이 아니지만, 설계에서 완전히 제외하지 않는다.

권장:

```text
- mode 필드 추가: normal | bdc
- BDC 전용 prompt/risk/source rule은 별도 appendix로 유지
- 초기 jibi digest에서는 bdc_candidate로 flag만 가능
```
