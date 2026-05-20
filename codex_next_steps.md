# Codex Next Steps after Milestone 1.28

## 상태

현재 Luddite는 `jibi -> anny -> piti` scaffold와
`piti_slide_spec -> styled PPTX draft` 렌더링이 동작하는 상태다.

중요한 방향은 그대로 유지한다.

- Piti는 의미를 재작성하지 않는다.
- Piti는 proof object를 새로 추론하지 않는다.
- Piti는 명시적인 `piti_slide_spec`을 렌더링만 한다.
- 현재 결과물은 검수 가능한 PPTX draft이며 방송 투입본이 아니다.

현재 readiness:

```text
ready_for_piti_renderer_contract=true
ready_for_api_experiment=true
ready_for_production_anny_agent=false
ready_for_production_piti_agent=false
ready_for_broadcast=false
```

## Milestone 1.25 완료 상태

`luddite render-piti-visual-qa`는 warning-only Markdown QA 리포트를 만든다.

입력:

```text
data/candidates/piti_slide_specs/*.json
```

출력:

```text
outputs/qa/piti_visual_qa/{deck_id}.md
outputs/qa/piti_visual_qa/piti_visual_qa_summary.md
```

GitHub에서 GPT가 검색할 수 있도록 같은 리포트를 아래 위치에도 mirror한다.

```text
docs/reviews/piti_visual_qa/{deck_id}.md
docs/reviews/piti_visual_qa/piti_visual_qa_summary.md
```

Milestone 1.25에서 추가된 해석성:

- QA flag severity: `BLOCKER`, `REVIEW`, `INFO`
- flagged slide별 `flag`, `severity`, `reason`, `review_hint`
- `Top Review Queue`
- `Severity Counts`
- `Flag Explanations`
- `Next Recommended Fix Area`

현재 summary:

```text
Decks: 2
Slides: 50
Flagged slides: 33
QA flags: 45
Severity: BLOCKER 0, REVIEW 42, INFO 3
Main weakness: diagram proof objects are still too generic.
Recommended next fix: improve Anny/adapter diagram node generation, not Piti renderer.
```

중요한 해석:

- `overflow_notes_too_large`는 `INFO`다. 실패 조건이 아니다.
- `diagram_nodes_too_generic`는 `REVIEW`다. 다음 개선은 Piti renderer가 아니라
  Anny/adapter의 diagram node 생성 품질 쪽이다.
- 모든 QA flag는 계속 warning-only다.

## Milestone 1.26 완료 상태

`luddite run-anny-slide-spec-experiment`는 Anny가 `piti_slide_spec` 계약을
직접 출력하는 controlled experiment harness다.

Make target:

```text
make run-anny-slide-spec-experiment
```

기본 모드는 fixture/synthetic validation이다.

- live API를 호출하지 않는다.
- 기존 두 case만 대상으로 한다.
- 기존 input bundle, evidence pack, enriched manual storyline, schema, visual QA
  기준을 재사용한다.
- production Anny agent가 아니다.
- Piti renderer가 의미를 재작성하거나 proof object를 재추론하지 않는다.

대상 case:

```text
ai_knowledge_institution
productive_finance_policy
```

각 case별 출력:

```text
outputs/model_dry_runs/anny_slide_spec_experiments/{case_id}/raw_model_output.txt
outputs/model_dry_runs/anny_slide_spec_experiments/{case_id}/parsed_piti_slide_spec.json
outputs/model_dry_runs/anny_slide_spec_experiments/{case_id}/validation_report.md
outputs/model_dry_runs/anny_slide_spec_experiments/{case_id}/visual_qa_report.md
outputs/model_dry_runs/anny_slide_spec_experiments/{case_id}/comparison_against_adapter.md
```

GitHub-visible mirror:

```text
docs/reviews/anny_slide_spec_experiments/{case_id}_validation.md
docs/reviews/anny_slide_spec_experiments/{case_id}_comparison.md
```

live API는 명시적으로 `--live-api`를 붙일 때만 호출한다.

## Milestone 1.27 완료 상태

Anny direct slide spec experiment의 fixture mode에서 diagram proof object를
adapter output의 단순 복사본으로 두지 않고, 같은 story/source/fact-check
metadata를 유지하면서 concrete diagram node/edge fixture를 적용한다.

핵심 원칙:

- diagram node는 추상 명사가 아니라 화면 박스에 들어갈 짧은 방송 문장이다.
- 가능한 구조는 `actor/context -> mechanism/change -> result/tension`이다.
- Piti renderer는 여전히 의미를 재작성하지 않는다.
- Piti는 diagram node를 고치거나 proof object를 재추론하지 않는다.
- QA flags는 계속 warning-only다.

fixture comparison:

```text
ai_knowledge_institution:
  adapter diagram_nodes_too_generic: 18
  direct diagram_nodes_too_generic: 0
  diagram_nodes_too_generic_delta: -18
  safety_regression_detected: false
  diagram_quality_improved: true

productive_finance_policy:
  adapter diagram_nodes_too_generic: 12
  direct diagram_nodes_too_generic: 0
  diagram_nodes_too_generic_delta: -12
  safety_regression_detected: false
  diagram_quality_improved: true
```

comparison report에는 아래 delta가 명시된다.

- `diagram_nodes_too_generic_delta`
- `manual_insert_required_without_editor_instruction_delta`
- `source_card_display_title_too_generic_delta`
- `overflow_notes_too_large_delta`
- `visual_qa_review_delta`
- `visual_qa_info_delta`
- `safety_regression_detected`
- `diagram_quality_improved`

## Milestone 1.28 완료 상태

live API opt-in 실행 경로가 fixture 결과와 분리됐다.

기본 경로:

- `make run-anny-slide-spec-experiment`는 여전히 fixture/synthetic mode다.
- 기본 테스트/CI는 API key나 model availability를 요구하지 않는다.
- live API는 `--live-api`를 붙였을 때만 호출한다.

live output:

```text
outputs/model_dry_runs/anny_slide_spec_experiments_live/{run_id}/{case_id}/raw_model_output.txt
outputs/model_dry_runs/anny_slide_spec_experiments_live/{run_id}/{case_id}/parsed_piti_slide_spec.json
outputs/model_dry_runs/anny_slide_spec_experiments_live/{run_id}/{case_id}/validation_report.md
outputs/model_dry_runs/anny_slide_spec_experiments_live/{run_id}/{case_id}/visual_qa_report.md
outputs/model_dry_runs/anny_slide_spec_experiments_live/{run_id}/{case_id}/comparison_against_adapter.md
outputs/model_dry_runs/anny_slide_spec_experiments_live/{run_id}/summary.md
```

live review mirror는 기본 생성하지 않는다. 필요할 때만
`--mirror-live-review`를 붙인다.

live 실행 예시:

```text
PYTHONPATH=src .venv/bin/python -m luddite run-anny-slide-spec-experiment --case-id ai_knowledge_institution --live-api
PYTHONPATH=src .venv/bin/python -m luddite run-anny-slide-spec-experiment --case-id productive_finance_policy --live-api
PYTHONPATH=src .venv/bin/python -m luddite run-anny-slide-spec-experiment --case-id all --live-api
```

live summary 판정:

- `success`: schema/render 통과, safety regression 없음, adapter 대비
  `diagram_nodes_too_generic` 감소
- `partial_success`: schema/render 통과, safety regression 없음, 하지만
  `diagram_nodes_too_generic`가 감소하지 않음
- `failure`: parse/schema/render 실패 또는 source/fact-check safety regression

문서와 report 해석:

- fixture mode는 harness와 deterministic expected behavior를 검증한다.
- live mode는 실제 model behavior를 관찰한다.
- fixture improvement는 production readiness를 의미하지 않는다.
- live success도 broadcast readiness를 의미하지 않는다.
- production readiness flags remain false.

## 다음 구현/평가 목표

1. live API opt-in으로 두 case를 실행하고 `summary.md`를 확인한다.
2. live 결과가 stable success인지, partial_success인지, failure인지 평가한다.
3. live 결과가 안정적이면 fixture logic이 아니라 prompt/contract 자체의
   diagram 지침을 더 다듬는다.
4. Jibi slideability scoring으로 넘어간다.
5. 그 이후 production agent/scheduler/Slack/Slides 검토

## 아직 하지 말 것

- production Anny agent
- production Piti agent
- scheduler
- Slack bot
- 이미지 자동 삽입
- 차트 자동 생성
- Google Slides 연동
- 방송 투입 가능 상태 선언
- 기본 검증 경로에서 신규 LLM/API 호출 추가

## 검증 기준

- `make lint` 통과
- `make test` 통과
- `make build-piti-slide-specs` 통과
- `make validate-piti-slide-spec` 통과
- `make render-piti-slide-spec-pptx` 통과
- `make render-piti-visual-qa` 통과
- `make run-anny-slide-spec-experiment` 통과
- 기존 slide spec 렌더링 동작을 깨지 않는다.
- `docs/reviews/piti_visual_qa/*.md`가 계속 생성된다.
- `docs/reviews/anny_slide_spec_experiments/*.md`가 생성된다.
- QA flags는 warning-only다.
