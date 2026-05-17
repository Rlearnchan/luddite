# anny MVP: Storyline Spec

## 1. 목표

`anny`는 사람이 수동으로 지정한 단일 주제만 처리하는 도구가 아니다. `jibi`가 쌓은 뉴스 DB와 evidence cluster를 바탕으로, 좋은 seed를 찾아 연결하고 3~4단 storyline outline을 제안해야 한다.

## 2. 우선 산출물

사용자 선호:

```text
D. 사람이 읽기 좋은 Markdown
B. 3~4단 storyline outline
E. 구현상 필요한 JSON
```

따라서 MVP output은 다음을 동시에 생성한다.

```text
1. Markdown outline
2. anny_storyline JSON
```

## 3. 분량

사용자 기대:

```text
최소 standard, deep도 좋음.
```

기본값:

```text
standard: 45~65 slides
```

자료가 충분하고 대표님이 추가 리서치를 덜 해도 될 정도를 목표로 할 때:

```text
deep: 80~110 slides
```

단, 첫 draft에서는 representative outline으로 시작해도 된다.

## 4. 농담/멘트

사용자는 농담/멘트를 적극 허용한다.

원칙:

```text
- 마음껏 시도한다.
- 다만 출처 없는 사실처럼 보이는 농담은 금지.
- 내부 밈/드립은 사람 수정 가능성을 전제로 둔다.
```

## 5. fact-check 책임

MVP 기준:

```text
- 출처를 반드시 붙인다.
- 근거 부족하면 needs_fact_check / needs_source 표시.
```

숫자/환율/날짜 검산과 공식자료 재검증은 후순위 또는 사람 검토로 둔다.

## 6. 원문 인용

anny는 원문 전체를 많이 넣기보다 핵심 문장만 사용한다.

```text
anny: 핵심 문장 + 설명 중심
piti/PPT: 필요 시 원문 + 번역 확대
```

## 7. 한국 연결

한국 연결은 필수는 아니다.

원칙:

```text
- 주제에 따라 관심 환기 정도면 충분.
- 해외 구조 설명 자체가 강하면 한국 연결 없이도 가능.
- 한국 메인 이슈라면 해외 사례를 먼저 배경으로 쓰는 방식도 가능.
```

## 8. DB 연결형 storyline

`anny`는 다음 입력을 받는 구조가 좋다.

```json
{
  "seed_candidate": {...},
  "related_candidates": [...],
  "evidence_cluster": {...},
  "past_video_matches": [...],
  "reference_archetype": "...",
  "length_mode": "standard"
}
```

즉, 특정 기사 하나가 아니라 `뉴스 DB 속 연결된 evidence bundle`이 입력이다.

## 9. storyline Markdown format

```md
# 제목 후보

한 줄 요약:

## 1부. 엥? 하는 seed
- slide headline 후보
- 근거 링크

## 2부. 왜 중요한가
- 숫자/통계
- 구조 문제

## 3부. 배경 설명 / 세계관
- 시청자 이해를 위한 설명

## 4부. 회수 / 리스크 / 질문
- 농담 또는 찝찝한 결론
- needs_fact_check
```
