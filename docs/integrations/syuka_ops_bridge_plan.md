# syuka-ops Bridge Plan for Luddite

작성일: 2026-05-17  
상태: research/design draft

## 1. 목적

`syuka-ops`는 과거 슈카월드 영상 메타데이터, 썸네일, 자막, 요약/키워드를 수집하고 Slack에서 검색할 수 있는 운영 프로젝트다.
Luddite는 미래 주제 후보를 발굴하는 프로젝트다.

두 프로젝트를 연결하면 `jibi`의 조회수 가능성 proxy, 중복/쿨다운 판단, 과거 유사 영상 검색이 가능해진다.

```text
Luddite = future candidate discovery
syuka-ops = past video / transcript / performance memory
```

## 2. 확인된 syuka-ops 구조

### 2.1 package / runtime

`syuka-ops`는 SQLite 기반 Syukaworld collector와 Slack bot 프로젝트이며, 주요 의존성에 `requests`,
`slack-bolt`, `yt-dlp`, `openpyxl` 등이 포함된다.

주요 console scripts:

```text
syuka-collect
syuka-slack-bot
syuka-import-legacy-meta
syuka-audit
syuka-report
syuka-diagnostics
syuka-scheduler
```

### 2.2 database tables

`src/syuka_ops/db.py` 기준 주요 테이블:

```text
videos
transcripts
video_analysis
video_ad_analysis
download_attempts
```

`videos`에는 video_id, channel_key, title, upload_date, view_count, like_count, thumbnail_url,
source_url, info_json_path 등이 있다.

`transcripts`에는 video_id, dialogue, subtitle_path, subtitle_source, segment_count가 있다.

`video_analysis`에는 summary, keywords_json, analysis_source가 있다.

### 2.3 search functions

`syuka-ops`에는 `search_videos`, `search_videos_count`, `transcript_snippets`,
`browse_videos`, `get_video` 등 검색/조회 함수가 있다.

`search_videos`는 제목, video_id, summary, keywords_json, transcript를 함께 보며 relevance_score를 계산한다.
따라서 Luddite가 초기에 별도 vector search 없이도 keyword search bridge를 붙일 수 있다.

## 3. Luddite에서 사용할 Bridge Output

`jibi_candidate`에 아래 필드를 추가하거나 별도 `past_video_matches` object로 둔다.

```json
{
  "past_video_matches": [
    {
      "video_id": "...",
      "title": "...",
      "upload_date": "...",
      "view_count": 1234567,
      "like_count": 12345,
      "match_reason": ["title", "keyword", "summary", "transcript"],
      "relevance_score": 17,
      "source_url": "https://www.youtube.com/watch?v=..."
    }
  ],
  "past_performance_proxy": {
    "similar_video_count": 8,
    "top_view_count": 2500000,
    "median_view_count": 720000,
    "recent_cooldown_risk": "medium",
    "novelty_note": "최근 90일 내 유사 소재 1건"
  }
}
```

## 4. Use Cases

### 4.1 유사 과거 영상 검색

새 후보 title/keywords를 syuka-ops에 검색한다.

예:

```text
candidate: "드론 비용 역전"
queries:
- 드론
- 레이저 무기
- 방산
- 이란 전쟁
- 우크라이나 드론
```

결과로 유사 영상이 나오면:

```text
- 이미 최근 다뤘는가?
- 조회수는 어땠는가?
- 어떤 각도였는가?
- 이번 후보는 다른 각도가 있는가?
```

### 4.2 조회수 가능성 proxy

과거 유사 영상의 view_count/like_count를 참고하되, 직접 예측으로 쓰지 않는다.

```text
high proxy:
- 유사 주제 median views 높음
- 최근 cooldown 낮음
- 이번 seed가 과거와 다른 angle

medium proxy:
- 유사 주제 조회수는 보통
- angle이 다소 겹침

low proxy:
- 유사 주제 조회수 낮음
- 이미 최근 다룸
- 이번 seed가 새롭지 않음
```

### 4.3 중복 / 쿨다운 감지

`recent_cooldown_risk` 기준:

```text
high: 최근 30일 내 매우 유사한 주제 방송
medium: 최근 90일 내 유사 주제 방송
low: 최근 90일 내 없음
```

쿨다운은 reject가 아니라 `keep_for_later` 또는 angle 변경에 사용한다.

### 4.4 제목 변환 학습

장기적으로:

```text
seed article title
→ storyline title
→ PPT title
→ YouTube final title
→ view_count
```

를 연결한다.

이때 syuka-ops의 `videos.title`, `video_analysis.summary`, `keywords_json`, `transcripts.dialogue`가 최종 영상 쪽 anchor가 된다.

## 5. Bridge Architecture

### Phase 0: No integration

현재.

### Phase 1: Read-only SQLite bridge

Luddite가 syuka-ops DB를 read-only로 읽는다.

설정:

```yaml
syuka_ops:
  enabled: true
  mode: sqlite_readonly
  db_path: ../syuka-ops/data/db/syuka_ops.db
```

주의:

```text
- Luddite가 syuka-ops DB에 write하지 않음
- WAL mode DB read 가능성 확인
- missing DB면 bridge skipped
```

### Phase 2: Export bridge

syuka-ops가 summary JSON/CSV export를 만들고 Luddite가 읽는다.

장점:

```text
- 프로젝트 간 의존성 낮음
- Windows/Docker 운영과 충돌 적음
- Luddite 테스트 쉬움
```

추천 export:

```text
data/external/syuka_ops/videos_export.jsonl
data/external/syuka_ops/video_analysis_export.jsonl
```

### Phase 3: Search API / Slack integration

나중에 별도 API 또는 Slack command bridge.

아직 구현하지 않는다.

## 6. Query Design

초기 query는 LLM 없이 rule-based로 만든다.

입력 candidate에서 추출:

```text
title keywords
seed_type
named entities
country
industry
risk flags
```

예:

```python
queries = [
    title_main_nouns,
    country + industry,
    seed_type_alias,
]
```

검색 우선순위:

```text
1. title/keywords match
2. video_analysis summary/keywords match
3. transcript match
4. recent videos by category
```

## 7. Performance Proxy Formula Draft

```text
past_performance_proxy =
  0.35 * normalized_median_views_of_similar
+ 0.20 * top_views_signal
+ 0.15 * novelty_vs_recent
+ 0.15 * keyword_overlap_with_high_performers
+ 0.15 * category_strength
- cooldown_penalty
```

주의:

- 조회수는 직접 예측이 아니라 ranking 보조.
- 낮은 조회수 카테고리라도 seed가 강하면 버리지 않는다.
- 신규/이상한 hook은 과거 유사도 낮아도 high potential 가능.

## 8. Bridge Module Proposal

파일:

```text
src/luddite/integrations/syuka_ops_bridge.py
```

초기 함수:

```python
def load_syuka_ops_config() -> SyukaOpsConfig: ...
def search_similar_videos(candidate, limit=5) -> list[PastVideoMatch]: ...
def build_past_performance_proxy(matches) -> dict: ...
def attach_syuka_ops_context(candidate) -> candidate: ...
```

CLI:

```text
luddite syuka-ops-search --query "드론"
luddite enrich-candidates-with-syuka-ops
```

Makefile:

```text
make syuka-ops-search
make enrich-candidates
```

## 9. What Not to Do Yet

```text
- syuka-ops DB write
- syuka-ops Slack bot merge
- vector DB implementation
- OpenAI embedding calls
- production bridge API
```

## 10. Next Steps

0.9.3 이후:

1. syuka-ops DB path config만 추가
2. read-only search prototype
3. jibi candidate에 `past_video_matches` attach
4. digest에 “과거 유사 영상” 1~3개 표시
5. 성과 proxy는 report에는 보이되, score에는 약하게만 반영
