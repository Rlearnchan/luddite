# Appendix. Notion Sketch DB Insights

작성일: 2026-05-16
상태: v0.1 draft

## 1. 목적

Notion `Sketch 보기` DB는 형찬 작성분 및 채택/방송 연결 흐름을 볼 수 있는 자료다. Google Sheet가 리서치팀 전체 운영 데이터라면, Sketch DB는 실제 storyline/아이디어 단위의 작업 흔적에 가깝다.

## 2. 확인된 DB 구조

주요 속성:

```text
제목: title
파일: relation
제작: date
방송: url
상태: multi_select, 예: 추천/미사용
채택여부: select
```

## 3. 활용 목적

| 용도 | 설명 |
|---|---|
| positive example | `방송` URL이 있는 항목은 실제 채택 사례 가능성이 높음 |
| storyline reference | 개별 페이지 본문에서 스토리 초안 구조를 볼 수 있음 |
| file relation | 연결된 파일을 통해 PPT/자료와 연결 가능 |
| BDC 분리 | 광고성/브랜디드 콘텐츠는 일반 방송과 문법이 달라 별도 처리 |

## 4. 추가로 읽어야 할 항목

```text
- 최근 50~100개 Sketch 항목
- 상태 = 추천
- 상태 = 미사용
- 방송 URL이 있는 항목
- 파일 relation이 있는 항목
- BDC로 보이는 항목
```

## 5. 분석할 질문

```text
1. 추천과 미사용의 차이는 무엇인가?
2. 방송 URL이 붙은 항목은 어떤 구조를 갖는가?
3. 파일 relation이 있는 항목은 PPT와 어떻게 연결되는가?
4. Sketch 단계의 문장과 최종 PPT 문장은 얼마나 달라지는가?
5. BDC 항목은 일반 방송과 어떤 차이가 있는가?
```

## 6. 권장 저장 형식

```json
{
  "notion_page_id": "...",
  "title": "젠스파크(BDC)",
  "created_time": "...",
  "date_produced": "2026-03-30",
  "status": ["추천"],
  "broadcast_url": null,
  "file_relations": ["..."],
  "plain_text": "...",
  "tags_inferred": ["bdc", "ai", "ppt_generation"],
  "used_by": ["anny", "jibi"]
}
```

## 7. Codex 작업 항목

```text
[ ] Notion DB fetch script 작성
[ ] Sketch item JSONL dump
[ ] relation URL resolver 작성
[ ] broadcast_url 있는 항목을 positive label로 분리
[ ] BDC 후보 자동 태깅
```
