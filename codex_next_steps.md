# Codex Next Steps after Milestone 1.22

## 상태

현재 Luddite는 `jibi -> anny -> piti` scaffold와
`piti_slide_spec -> styled PPTX draft` 렌더링이 동작하는 상태다.

중요한 방향은 다음과 같다.

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

## 다음 구현 목표: Milestone 1.24 Piti Visual QA

목표는 PPT를 더 예쁘게 만드는 것이 아니다. 사람이 눈으로 검수해야 할
슬라이드를 자동으로 드러내는 Markdown QA 리포트를 만든다.

추가할 CLI:

```text
luddite render-piti-visual-qa
```

추가할 Make target:

```text
make render-piti-visual-qa
```

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

각 슬라이드별 리포트에는 다음 항목을 포함한다.

- `slide_no`
- `screen_headline`
- `layout_intent`
- `proof_object.type`
- `screen_body` 줄 수
- `overflow_notes` 개수
- `needs_source`
- `needs_fact_check`
- `required_before_broadcast`
- `manual_insert_required`
- `visual_qa_flags`

Soft QA flags:

- `proof_object_missing_for_claim_slide`
- `too_many_source_cards_in_sequence`
- `diagram_nodes_too_generic`
- `chart_without_data_hint`
- `source_card_display_title_too_generic`
- `screen_body_empty_but_no_proof_object`
- `overflow_notes_too_large`
- `manual_insert_required_without_editor_instruction`

이 flag들은 실패 조건이 아니라 review warning이다. 특히
`overflow_notes`는 설명문을 화면 밖으로 잘 뺐다는 신호일 수 있으므로
바로 실패 처리하지 않는다.

## 이후 순서

1. Piti visual QA
2. Anny direct Piti slide spec experiment
3. Jibi slideability scoring

## 아직 하지 말 것

- production Anny agent
- production Piti agent
- scheduler
- Slack bot
- 이미지 자동 삽입
- 차트 자동 생성
- Google Slides 연동
- 방송 투입 가능 상태 선언
- 신규 LLM/API 호출 추가

## 완료 기준

- `make lint` 통과
- `make test` 통과
- `make build-piti-slide-specs` 통과
- `make validate-piti-slide-spec` 통과
- `make render-piti-slide-spec-pptx` 통과
- `make render-piti-visual-qa` 통과
- 기존 slide spec 렌더링 동작을 깨지 않는다.
- QA 리포트가 두 샘플 deck 모두에 대해 생성된다.
- 리포트만 보고도 사람이 어떤 슬라이드를 눈으로 검수해야 하는지
  파악할 수 있다.
