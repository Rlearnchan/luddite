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

## 8.1 anny input bundle

Milestone 1.4부터 immediate input은 `anny_input_bundle`이다.

```text
story_seed_handoff
-> anny_input_bundle
-> manual dry run
-> later storyline generation
```

Bundle에는 다음이 포함된다.

```text
core_question
candidate_articles
required_evidence
nice_to_have_evidence
fact_check_tasks
official_source_tasks
suggested_story_structure
opening_hook
audience_question
must_include
avoid
do_not_claim
needs_fact_check
```

원칙:

- `do_not_claim`은 생성기가 절대 넘으면 안 되는 guardrail이다.
- `candidate_articles`에는 원문 전문을 넣지 않는다.
- evidence가 부족하면 내용을 발명하지 않고 `needs_fact_check` /
  `needs_source`를 남긴다.
- 1.4.1에서는 dry-run case만 준비하고 full storyline generation은 하지 않는다.

## 8.2 anny output contract

Milestone 1.6부터 anny output은 단순 outline JSON이 아니라 prompt/eval contract를
따른다. Production agent 구현 전에도 이 contract를 기준으로 manual dry run을
검증한다.

Required top-level fields:

```text
storyline_id
title
sections
risk_flags
required_fact_checks
```

Required slide fields:

```text
slide_type
headline
body
source_urls
image_urls
notes
needs_fact_check
needs_source
```

Source hygiene sidecar 또는 slide metadata:

```text
fact_check_priority: high | medium | low
fact_check_kind:
  factual_claim
  institution_quote_context
  education_research_claim
  korea_bridge_claim
  policy_effect_claim
  investment_risk_claim
  production_checklist
  rhetorical_caution
  source_context
required_before_storyline: bool
required_before_broadcast: bool
source_refs:
  - url
    role
    use
    confidence
    manual_check_required
```

Rules:

- The output is evidence-bound. It must not create facts, numbers, claims, or
  URLs that are absent from the input bundle or evidence pack.
- `source_urls` must come from candidate article URLs or evidence-pack URLs.
- Body claims must match slide-specific `source_refs.use`; otherwise keep
  `needs_source` or `needs_fact_check`.
- `source_urls`와 `image_urls`는 분리한다. 같은 URL이 양쪽에 있으면 실패다.
- source가 붙은 slide를 fact-check 완료 slide로 취급하지 않는다.
- needs_fact_check / needs_source는 적극적으로 남긴다. 근거 부족을 숨기면 실패다.
- `required_before_storyline`은 dry-run storyline 생성 전 꼭 필요한 최소 근거다.
- `required_before_broadcast`는 방송 전 사람이 반드시 확인해야 할 근거다.
- counterpoint는 AI/교육/정책/금융처럼 논쟁적인 주제에서 필수다.
- risk slide 또는 counterpoint slide는 민감 주제에서 정상적인 구조 요소다.
- `korea_bridge`는 후반 보조 연결로만 사용하고 메인 논지를 한국 사례로
  과확장하지 않는다.
- rhetorical bridge, 질문형 전환, punchline은 출처를 과도하게 요구하지 않되,
  사실 주장처럼 쓰면 안 된다.
- key beat 평가는 단일 단어가 아니라 구문 중심 alias로 한다.
- `production_checklist` slide는 나중에 PPT 본문보다 내부 제작 체크리스트,
  appendix, notes로 넘기는 것을 기본으로 한다.
- `do_not_claim`과 `avoid`는 절대 넘지 않는다.

Policy/finance guardrails:

- 정책 효과를 단정하지 않는다.
- 금융상품, 정책상품, 특정 회사 홍보처럼 쓰지 않는다.
- 투자 조언, 매수/매도 의견, 가격·수익률·주가 전망을 단정하지 않는다.
- 공식자료가 없으면 `needs_source` 또는 `required_before_broadcast`로 남긴다.
- 정책/금융 주제는 risk discussion 또는 counterpoint를 포함한다.

Run contract scaffold:

- `specs/anny_run_input_schema.json` defines the local run input manifest:
  `run_id`, `bundle_id`, `story_seed_title`, input/evidence paths,
  `length_mode`, contract/prompt versions, mode, requester, and timestamp.
- `specs/anny_run_manifest_schema.json` defines the run result manifest:
  status, input/evidence/storyline/report paths, `model_source`, schema and
  hygiene pass/fail, timestamp, and notes.
- `luddite anny-run-storyline` validates manually prepared storyline JSON and
  writes run manifests/reports. It does not call an LLM and is not a production
  anny agent.
- Run manifests include sha256 checksums for the input bundle, evidence pack,
  output storyline, hygiene sidecar, and prompt file when those files exist.
  Missing optional files use `null` checksums.
- Run manifests also copy `output_contract_version`, `prompt_version`,
  `validator_version`, and `schema_version` so future eval changes can be
  tracked.
- `data/manifests/anny_runs/index.jsonl` is a local run registry index for
  comparing manual, fixture, and future API experiment runs.
- Every run report must include the warning:
  `This run does not imply production readiness.`

API experiment prep:

- Milestone 1.8 adds API experiment fields and documents failure handling only.
  It does not call an LLM API.
- Run input mode may be `manual`, `dry_run`, `api_experiment`, or `api_future`.
- Manifest `model_source` may be `manual_gpt_pro`, `openai_api`, or `fixture`.
- Future API experiment files use:
  `outputs/model_dry_runs/anny_api_experiments/<run_id>/`
- Each API experiment directory should preserve `raw_model_output.txt`,
  `parsed_storyline.json` when parsing succeeds, `validation_report.md`, and
  `manifest.json`.
- Invalid JSON or schema failure is recorded as failure. The initial repair
  policy does not rewrite model output, invent sources, or remove
  `needs_fact_check`.
- Failure modes are documented in `docs/product/anny_failure_modes.md` and
  include source hallucination, unsupported claims, counterpoint missing,
  source/image overlap, investment-advice violations, and required broadcast
  checks missing.

Readiness states:

- `ready_for_prompt_design`: prompt/eval contract is clear enough to design
  production prompts.
- `ready_for_manual_storyline`: a human/GPT Pro dry run can be prepared and
  validated with the local runner.
- `ready_for_api_experiment_prep`: API experiment storage, validation, and
  failure handling are specified, but no API call is enabled.
- `ready_for_api_experiment`: API-based generation may be tested in a controlled
  non-production setting.
- `ready_for_production_agent`: automated anny generation is safe enough to
  wire into the product.
- `ready_for_broadcast`: evidence and fact-check review are complete enough for
  broadcast use.

Current expected state:

- `ready_for_prompt_design: true`
- `ready_for_manual_storyline: true`
- `ready_for_api_experiment_prep: true`
- `ready_for_api_experiment: false`
- `ready_for_production_agent: false`
- `ready_for_broadcast: false`

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
