# Codex Next Steps after Corpus Insight v0.2

## 상태

parser smoke는 통과했고, GPT Pro가 parsed corpus 기반 appendix 문서 3개를 보강했다.

보강된 문서:

- `docs/appendix/latest_ppt_pattern_report.md`
- `docs/appendix/storyline_pattern_catalog.md`
- `docs/appendix/google_sheet_insights.md`

보조 테이블:

- `outputs/tables/ppt_deck_metrics.csv`
- `outputs/tables/storyline_catalog_metrics.csv`
- `outputs/tables/topic_finding_examples.csv`
- `outputs/tables/channel_titles_metrics.csv`

## 다음 구현 목표: Golden Reconstruction

아직 jibi/anny/piti LLM agent 본구현으로 가지 말 것. 다음은 deterministic fixture 작업이다.

### 1. anny_storyline fixture 만들기

아래 두 PPT를 기준으로 사람이 검토 가능한 `anny_storyline` JSON fixture를 만든다.

- `전당포 주식회사_배형찬.pptx`
- `코카콜라를 이기는 방법_김성원.pptx`

위치는:

```text
eval/golden_cases/anny_storylines/golden_pawnshop_f88_storyline.json
eval/golden_cases/anny_storylines/golden_coca_cola_ambani_storyline.json
```

조건:

- `specs/anny_storyline_schema.json` 통과
- section 3개 이상
- 각 slide는 headline/body/source_urls/image_urls/notes 포함
- source_urls와 image_urls overlap 없음
- needs_fact_check/needs_source를 표시할 수 있게 함

### 2. piti_deck_plan fixture 만들기

위 anny_storyline을 `piti_slide_schema` 또는 `deck_schema`에 맞춰 deck plan으로 변환한다.

```text
eval/golden_cases/deck_plans/golden_pawnshop_f88_deck_plan.json
eval/golden_cases/deck_plans/golden_coca_cola_ambani_deck_plan.json
```

### 3. prompt 보정

아래 prompt 문서를 corpus insight v0.2 기준으로 수정한다.

- `prompts/jibi/seed_scorer.md`
- `prompts/anny/storyline_writer.md`
- `prompts/piti/deck_planner.md`

특히 jibi prompt에는 `주제 찾기` positive/negative examples를 넣는다.

### 4. 아직 하지 말 것

- RSS 24/7 collector
- Google Sheets API direct fetch
- full PPT generator
- image auto collection
- production-grade agent orchestration

## 완료 기준

- golden_pawnshop_f88_storyline.json schema 통과
- golden_coca_cola_ambani_storyline.json schema 통과
- deck_plan fixture schema 통과
- prompt에 실제 corpus examples 반영
- `make test` 통과
