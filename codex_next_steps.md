# Codex Next Steps after Milestone 1.34

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

## Milestone 1.29 완료 상태

live API opt-in으로 실제 Anny direct `piti_slide_spec` 생성을 실행했다.

실행 명령:

```text
PYTHONPATH=src .venv/bin/python -m luddite run-anny-slide-spec-experiment --case-id all --live-api --run-id live_m129_20260520_all --timeout 600
```

생성 위치:

```text
outputs/model_dry_runs/anny_slide_spec_experiments_live/live_m129_20260520_all/
docs/reviews/anny_slide_spec_experiments_live/live_m129_20260520_all_summary_review.md
```

실행 결과:

```text
run_id: live_m129_20260520_all
model: gpt-5-mini-2025-08-07
overall outcome: failure
case outcomes: ai_knowledge_institution=failure, productive_finance_policy=failure
```

case별 비교:

```text
ai_knowledge_institution:
  adapter diagram_nodes_too_generic: 18
  live diagram_nodes_too_generic: 0
  schema_valid: false
  render_passed: false
  safety_regression_detected: true
  diagram_quality_improved: false

productive_finance_policy:
  adapter diagram_nodes_too_generic: 12
  live diagram_nodes_too_generic: 0
  schema_valid: false
  render_passed: false
  safety_regression_detected: true
  diagram_quality_improved: false
```

해석:

- live model은 strengthened diagram contract를 어느 정도 따랐다.
- 두 case 모두 `diagram_nodes_too_generic`가 `0`으로 줄었다.
- 하지만 두 case 모두 schema/render validation에 실패했다.
- fact-check/required-before-broadcast metadata 보존도 너무 공격적으로
  줄어 safety regression으로 판정됐다.
- 따라서 live run은 성공이 아니라 유용한 failure diagnostic이다.
- production Anny/Piti/broadcast readiness는 계속 false다.

주요 실패 원인:

- AI case: `sections[].slides` 배열이 누락됐다.
- Finance case: `layout_intent=hook`처럼 schema enum 밖 값을 사용했다.
- 두 case 모두 adapter 대비 slide count를 너무 줄였다.
- 두 case 모두 `needs_fact_check` 또는 `required_before_broadcast`를 너무
  많이 제거했다.

## Milestone 1.30 완료 상태

Anny direct slide spec prompt/contract를 schema shape, slide coverage, safety
metadata preservation 중심으로 강화했다.

prompt에 추가된 핵심:

- 정확한 `piti_slide_spec_schema.json` object 출력
- `sections[].slides` non-empty array 요구
- top-level `slides[]`와 section slide object 대응 요구
- nullable array field를 `null`로 쓰지 말라는 지시
- schema-valid `layout_intent` enum 명시
- 24-26장 representative deck을 20장 미만으로 압축하지 말라는 지시
- `needs_fact_check`, `required_before_broadcast`, `source_refs`,
  `do_not_claim` 보수적 보존
- `diagram_nodes[]` 내부 `->` 금지
- final JSON 전 preflight checklist

validator/report에 추가된 진단:

- `missing_required_schema_paths`
- `invalid_enum_values`
- `missing_sections_slides_count`
- `section_slide_ref_mismatch_count`
- `slide_count_delta_vs_adapter`
- `section_count_delta_vs_adapter`
- `source_refs_delta_vs_adapter`
- `needs_fact_check_delta_vs_adapter`
- `required_before_broadcast_delta_vs_adapter`
- `do_not_claim_delta_vs_adapter`
- `diagram_nodes_with_arrow_count`
- failure reason: `sections_slides_missing`, `invalid_layout_intent`,
  `deck_too_compressed`, `safety_metadata_removed`,
  `diagram_node_contains_arrow`

live opt-in 재실행:

```text
PYTHONPATH=src .venv/bin/python -m luddite run-anny-slide-spec-experiment --case-id all --live-api --run-id live_m130_20260520_all --timeout 600
```

결과:

```text
run_id: live_m130_20260520_all
model: gpt-5-mini-2025-08-07
overall outcome: failure
```

m129 대비:

```text
ai_knowledge_institution:
  schema_valid: false -> true
  render_passed: false -> true
  slide_count: 11 -> 0
  safety_regression_detected: true -> true
  result: still failure

productive_finance_policy:
  schema_valid: false -> true
  render_passed: false -> false
  slide_count: 8 -> 24
  safety_regression_detected: true -> false
  diagram_nodes_too_generic: 0 -> 0
  diagram_nodes_with_arrow_count: 0
  result: improved but still failure
```

해석:

- Finance case는 coverage/safety/schema가 크게 좋아졌다.
- AI case는 schema-valid empty deck을 냈고, 새 contract diagnostics가 이를
  `sections_slides_missing`, `deck_too_compressed`, `safety_metadata_removed`로
  잡았다.
- live success는 아니다.
- production/broadcast readiness는 계속 false다.

## Milestone 1.31 완료 상태

Anny direct slide spec prompt/contract를 empty deck 방지와 renderer-specific
proof requirements 중심으로 한 번 더 강화했다.

prompt에 추가된 핵심:

- empty schema-valid deck은 failure라는 지시
- top-level `slides[]` non-empty 요구
- 모든 `sections[].slides[]` non-empty 요구
- 24-26장 baseline이면 최소 20장 유지 요구
- section마다 최소 1개 slide 포함 요구
- 모든 slide가 정확히 1개 section에 속해야 한다는 지시
- chart/table proof object의 `data_hint`와 짧은 body 요구
- 긴 chart/table 설명은 `overflow_notes` 또는 `speaker_notes_expanded`로 이동
- `article_quote`는 non-empty `quote_text`가 있어야 한다는 요구
- 실제 quote가 없으면 `source_card` 또는 `diagram`을 쓰라는 지시

validator/report에 추가된 진단:

- `top_level_slides_empty`
- `empty_sections_count`
- `sections_with_empty_slides`
- `minimum_slide_count_failed`
- `representative_deck_compressed_to_empty`
- `deck_has_no_renderable_slides`
- `chart_table_body_too_long_count`
- `chart_table_body_too_long_slides`
- `article_quote_missing_quote_text_count`
- `article_quote_missing_quote_text_slides`
- `source_card_generic_title_count`
- `proof_object_renderer_contract_failed`
- `renderer_failure_reasons`

live opt-in 재실행:

```text
PYTHONPATH=src .venv/bin/python -m luddite run-anny-slide-spec-experiment --case-id all --live-api --run-id live_m131_20260520_all --timeout 600
```

결과:

```text
run_id: live_m131_20260520_all
model: gpt-5-mini-2025-08-07
overall outcome: failure
```

m129/m130/m131 비교:

```text
ai_knowledge_institution:
  m129 schema_valid=false, render_passed=false, slide_count=11, safety_regression=true
  m130 schema_valid=true, render_passed=true, slide_count=0, safety_regression=true
  m131 schema_valid=true, render_passed=true, slide_count=0, safety_regression=true
  result: empty deck persists; diagnostics are now explicit.

productive_finance_policy:
  m129 schema_valid=false, render_passed=false, slide_count=8, safety_regression=true
  m130 schema_valid=true, render_passed=false, slide_count=24, safety_regression=false
  m131 schema_valid=true, render_passed=true, slide_count=24, safety_regression=false
  result: renderer failure cleared, coverage/safety preserved, but section slide arrays are empty.
```

해석:

- Finance case는 renderer-level proof object 문제가 개선됐다.
- Finance case는 24-slide coverage와 source/fact-check safety metadata를 유지했다.
- AI case는 여전히 schema-valid empty deck을 냈다.
- 두 case 모두 `sections[].slides` arrays가 비어 있거나 top-level `slides[]`와
  대응되지 않아 live success가 아니다.
- 두 case 모두 `diagram_nodes_too_generic=0`을 유지했다.
- production Anny/Piti/broadcast readiness는 계속 false다.

## Milestone 1.32 완료 상태

`specs/piti_slide_spec_schema.json`을 확인한 결과:

- `sections[].slides[]`는 slide number/id reference 배열이 아니다.
- `sections[].slides[]`는 `#/$defs/slide`를 따르는 full slide object 배열이다.
- 따라서 top-level `slides[]`와 section-level `sections[].slides[]`는 같은
  `slide_no`/`slide_id` set을 덮어야 한다.

prompt에 추가/강화된 핵심:

- `sections[].slides[]`는 full slide object이며 숫자/ID reference가 아니라는
  명시
- 1 section + 2 slides의 schema-accurate minimal valid shape 예시
- section-level slide object와 top-level slide object가 같은 slide_no/slide_id
  set을 덮어야 한다는 지시
- every slide의 `section_id`가 existing section과 match해야 한다는 지시
- `ai_knowledge_institution`은 4-section, 26-slide coverage를 유지하라는
  case coverage anchor

validator/report에 추가된 section mapping diagnostics:

- `top_level_slide_numbers`
- `section_mapped_slide_numbers`
- `missing_from_sections`
- `unknown_section_slide_refs`
- `duplicate_section_slide_refs`
- `slides_with_unknown_section_id`
- `slides_missing_section_id`
- `sections_without_matching_top_level_slides`
- `section_mapping_complete`

live opt-in 재실행:

```text
PYTHONPATH=src .venv/bin/python -m luddite run-anny-slide-spec-experiment --case-id all --live-api --run-id live_m132_20260520_all --timeout 600
```

결과:

```text
run_id: live_m132_20260520_all
model: gpt-5-mini-2025-08-07
overall outcome: success
case outcomes: ai_knowledge_institution=success, productive_finance_policy=success
```

m129/m130/m131/m132 비교:

```text
ai_knowledge_institution:
  m129 schema_valid=false, render_passed=false, slide_count=11, section_mapping_complete=false, safety_regression=true
  m130 schema_valid=true, render_passed=true, slide_count=0, section_mapping_complete=false, safety_regression=true
  m131 schema_valid=true, render_passed=true, slide_count=0, section_mapping_complete=false, safety_regression=true
  m132 schema_valid=true, render_passed=true, slide_count=26, section_mapping_complete=true, safety_regression=false

productive_finance_policy:
  m129 schema_valid=false, render_passed=false, slide_count=8, section_mapping_complete=false, safety_regression=true
  m130 schema_valid=true, render_passed=false, slide_count=24, section_mapping_complete=false, safety_regression=false
  m131 schema_valid=true, render_passed=true, slide_count=24, section_mapping_complete=false, safety_regression=false
  m132 schema_valid=true, render_passed=true, slide_count=24, section_mapping_complete=true, safety_regression=false
```

해석:

- AI empty deck 문제가 m132 live run에서는 사라졌다.
- Finance section mapping 문제가 m132 live run에서는 사라졌다.
- 두 case 모두 `section_mapping_complete=true`다.
- 두 case 모두 schema/render/safety/coverage를 통과했다.
- 두 case 모두 `diagram_nodes_too_generic=0`을 유지했다.
- 이것은 controlled live experiment success이지 production/broadcast readiness가
  아니다.

## Milestone 1.34 완료 상태

Milestone 1.33에서 Jibi slideability scoring v0가 추가됐고, Milestone 1.34에서
이 정보를 Anny input bundle로 넘긴다.

구현된 상태:

- `score-candidates`가 각 후보에 optional `slideability` object를 붙인다.
- `cluster-jibi-candidates`가 cluster-level `slideability`를 병합한다.
- story seed handoff에는 `slideability_score`, `first_slide_idea`,
  `likely_proof_object_types`, `visual_risks`가 추가된다.
- daily digest, Jibi quality report, cluster report, story seed handoff digest에
  slideability summary가 표시된다.
- `build-anny-input-bundles`가 story seed의 slideability를
  `visual_planning_hint`로 옮긴다.
- `visual_planning_hint`는 bundle top-level에 있고, `candidate_articles`,
  `required_evidence`, `fact_check_tasks`와 분리된다.
- 구현은 rule-based deterministic v0이며 LLM/API 호출이 없다.
- slideability는 review signal이다. `recommended_action`, 기존 scoring, handoff
  gate를 hard 변경하지 않는다.

현재 `slideability` shape:

```text
score: 0.0-1.0
visualizability: low|medium|high
chartability: none|weak|strong
diagramability: none|weak|strong
screenshotability: none|weak|strong
source_card_fit: none|weak|strong
first_slide_idea: short review hint
likely_proof_object_types: diagram/chart/source_card
risks: too_abstract, single_source, needs_official_data, policy_claim_risk, market_claim_risk, no_clear_visual
reason: compact deterministic explanation
```

현재 `visual_planning_hint` shape:

```text
slideability_score: 0.0-1.0
visualizability: low|medium|high
first_slide_idea: tentative opening visual idea
likely_proof_object_types: diagram/chart/source_card
visual_risks: single_source, needs_official_data, policy_claim_risk, market_claim_risk, ...
reason: deterministic slideability explanation
planning_note: slideability is planning context only, not evidence
```

대표 bundle 확인:

```text
생산적 금융과 정책자금 전환:
  visual planning: high / diagram+chart+source_card
  visual risks: single_source, needs_official_data, policy_claim_risk
  guardrails: needs_fact_check=true; official/numeric/source checks remain

AI 즉답 시대의 지식기관 역할:
  visual planning: high / diagram+source_card
  visual risks: single_source
  guardrails: needs_fact_check=true
```

GitHub-visible review note:

```text
docs/reviews/jibi_slideability_v0.md
docs/reviews/anny_input_bundle_slideability_v0.md
```

## 다음 구현/평가 목표

1. slideability/visual planning hint와 downstream Piti visual QA 결과를 연결해,
   Jibi 단계의 예측력이 실제 slide spec QA와 맞는지 본다.
2. `likely_proof_object_types`가 실제 proof object 선택과 맞는지 비교한다.
3. `visual_risks`가 source/fact-check caution 보존에 도움이 되는지 본다.
4. PPT contact sheet QA surface를 검토한다.
5. 필요하면 현재 prompt로 live confirmation pass를 한 번 더 돌린 뒤 case set을
   넓힌다.
6. visual QA와 Anny direct comparison report는 계속 warning-only review surface로
   유지한다.
7. 그 이후 production agent/scheduler/Slack/Slides 검토

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
- `make normalize-candidates` 통과
- `make score-candidates` 통과
- `make cluster-jibi-candidates` 통과
- `make build-anny-input-bundles` 통과
- `make prepare-anny-input-bundles` 통과
- 가능하면 `make render-daily-digest` 통과
- 기존 slide spec 렌더링 동작을 깨지 않는다.
- `docs/reviews/piti_visual_qa/*.md`가 계속 생성된다.
- `docs/reviews/anny_slide_spec_experiments/*.md`가 생성된다.
- QA flags는 warning-only다.
