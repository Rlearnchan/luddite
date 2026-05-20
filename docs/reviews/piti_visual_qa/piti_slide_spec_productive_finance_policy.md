# Piti Visual QA: piti_slide_spec_productive_finance_policy

- Generated at: 2026-05-20T01:40:17.017476+00:00
- Input: data/candidates/piti_slide_specs/productive_finance_policy_slide_spec.json
- Slides: 24
- Flagged slides: 12
- QA flags: 16
- QA flags are review warnings only.
- LLM/API calls: none
- Image insertion/chart generation/Google Slides integration: none

## Top Review Queue

| priority | deck | slide | headline | severity | flags | review_hint |
|---:|---|---:|---|---|---|---|
| 1 | piti_slide_spec_productive_finance_policy | 11 | 이건 “은행이 더 착해져야 한다”는 얘기가 아니다 | REVIEW | diagram_nodes_too_generic, overflow_notes_too_large, manual_insert_required_without_editor_instruction | Replace abstract labels with concrete actor -> mechanism -> result labels. |
| 2 | piti_slide_spec_productive_finance_policy | 5 | 금융은 원래 안전해야 하는가, 위험을 져야 하는가 | REVIEW | diagram_nodes_too_generic, manual_insert_required_without_editor_instruction | Replace abstract labels with concrete actor -> mechanism -> result labels. |
| 3 | piti_slide_spec_productive_finance_policy | 22 | 투자 이야기로 들리지 않게 조심해야 한다 | REVIEW | diagram_nodes_too_generic, manual_insert_required_without_editor_instruction | Replace abstract labels with concrete actor -> mechanism -> result labels. |
| 4 | piti_slide_spec_productive_finance_policy | 3 | 은행 입장에서는 담보가 제일 편하다 | REVIEW | diagram_nodes_too_generic | Replace abstract labels with concrete actor -> mechanism -> result labels. |
| 5 | piti_slide_spec_productive_finance_policy | 4 | 그런데 AI 산업은 담보보다 시간이 먼저 필요하다 | REVIEW | diagram_nodes_too_generic | Replace abstract labels with concrete actor -> mechanism -> result labels. |
| 6 | piti_slide_spec_productive_finance_policy | 9 | 부동산 담보는 보이지만, 기술의 미래는 잘 안 보인다 | REVIEW | diagram_nodes_too_generic | Replace abstract labels with concrete actor -> mechanism -> result labels. |
| 7 | piti_slide_spec_productive_finance_policy | 10 | 그래서 정책금융은 시장이 못 보는 시간을 보겠다는 말일 수 있다 | REVIEW | diagram_nodes_too_generic | Replace abstract labels with concrete actor -> mechanism -> result labels. |
| 8 | piti_slide_spec_productive_finance_policy | 16 | 성장산업을 돕는 것과 특정 기업을 밀어주는 것은 다르다 | REVIEW | diagram_nodes_too_generic | Replace abstract labels with concrete actor -> mechanism -> result labels. |
| 9 | piti_slide_spec_productive_finance_policy | 17 | 반대쪽 질문도 있다: 그럼 아무도 위험을 안 지면 어떻게 하나 | REVIEW | diagram_nodes_too_generic | Replace abstract labels with concrete actor -> mechanism -> result labels. |
| 10 | piti_slide_spec_productive_finance_policy | 18 | 결국 질문은 성장의 과실보다 위험의 배분이다 | REVIEW | diagram_nodes_too_generic | Replace abstract labels with concrete actor -> mechanism -> result labels. |
| 11 | piti_slide_spec_productive_finance_policy | 20 | 금융권에 “성장에 베팅하라”고 말하는 순간 생기는 문제 | REVIEW | diagram_nodes_too_generic | Replace abstract labels with concrete actor -> mechanism -> result labels. |
| 12 | piti_slide_spec_productive_finance_policy | 24 | 금융은 위험을 피하는 기술인가, 좋은 위험을 고르는 기술인가 | REVIEW | diagram_nodes_too_generic | Replace abstract labels with concrete actor -> mechanism -> result labels. |

## Review Queue

- slide 3 [REVIEW]: 은행 입장에서는 담보가 제일 편하다 -- diagram_nodes_too_generic
- slide 4 [REVIEW]: 그런데 AI 산업은 담보보다 시간이 먼저 필요하다 -- diagram_nodes_too_generic
- slide 5 [REVIEW]: 금융은 원래 안전해야 하는가, 위험을 져야 하는가 -- diagram_nodes_too_generic, manual_insert_required_without_editor_instruction
- slide 9 [REVIEW]: 부동산 담보는 보이지만, 기술의 미래는 잘 안 보인다 -- diagram_nodes_too_generic
- slide 10 [REVIEW]: 그래서 정책금융은 시장이 못 보는 시간을 보겠다는 말일 수 있다 -- diagram_nodes_too_generic
- slide 11 [REVIEW]: 이건 “은행이 더 착해져야 한다”는 얘기가 아니다 -- diagram_nodes_too_generic, overflow_notes_too_large, manual_insert_required_without_editor_instruction
- slide 16 [REVIEW]: 성장산업을 돕는 것과 특정 기업을 밀어주는 것은 다르다 -- diagram_nodes_too_generic
- slide 17 [REVIEW]: 반대쪽 질문도 있다: 그럼 아무도 위험을 안 지면 어떻게 하나 -- diagram_nodes_too_generic
- slide 18 [REVIEW]: 결국 질문은 성장의 과실보다 위험의 배분이다 -- diagram_nodes_too_generic
- slide 20 [REVIEW]: 금융권에 “성장에 베팅하라”고 말하는 순간 생기는 문제 -- diagram_nodes_too_generic
- slide 22 [REVIEW]: 투자 이야기로 들리지 않게 조심해야 한다 -- diagram_nodes_too_generic, manual_insert_required_without_editor_instruction
- slide 24 [REVIEW]: 금융은 위험을 피하는 기술인가, 좋은 위험을 고르는 기술인가 -- diagram_nodes_too_generic

## Flag Details

| deck | slide | flag | severity | reason | review_hint |
|---|---:|---|---|---|---|
| piti_slide_spec_productive_finance_policy | 3 | diagram_nodes_too_generic | REVIEW | diagram nodes are too abstract to guide an editable broadcast visual. | Replace abstract labels with concrete actor -> mechanism -> result labels. |
| piti_slide_spec_productive_finance_policy | 4 | diagram_nodes_too_generic | REVIEW | diagram nodes are too abstract to guide an editable broadcast visual. | Replace abstract labels with concrete actor -> mechanism -> result labels. |
| piti_slide_spec_productive_finance_policy | 5 | diagram_nodes_too_generic | REVIEW | diagram nodes are too abstract to guide an editable broadcast visual. | Replace abstract labels with concrete actor -> mechanism -> result labels. |
| piti_slide_spec_productive_finance_policy | 5 | manual_insert_required_without_editor_instruction | REVIEW | proof_object requires manual insertion, but no editor instruction is available. | Add a short editor_instruction describing what the editor should insert or verify. |
| piti_slide_spec_productive_finance_policy | 9 | diagram_nodes_too_generic | REVIEW | diagram nodes are too abstract to guide an editable broadcast visual. | Replace abstract labels with concrete actor -> mechanism -> result labels. |
| piti_slide_spec_productive_finance_policy | 10 | diagram_nodes_too_generic | REVIEW | diagram nodes are too abstract to guide an editable broadcast visual. | Replace abstract labels with concrete actor -> mechanism -> result labels. |
| piti_slide_spec_productive_finance_policy | 11 | diagram_nodes_too_generic | REVIEW | diagram nodes are too abstract to guide an editable broadcast visual. | Replace abstract labels with concrete actor -> mechanism -> result labels. |
| piti_slide_spec_productive_finance_policy | 11 | overflow_notes_too_large | INFO | overflow_notes has more than 3 items. | Check whether this is healthy screen compression or whether core logic disappeared from the slide. |
| piti_slide_spec_productive_finance_policy | 11 | manual_insert_required_without_editor_instruction | REVIEW | proof_object requires manual insertion, but no editor instruction is available. | Add a short editor_instruction describing what the editor should insert or verify. |
| piti_slide_spec_productive_finance_policy | 16 | diagram_nodes_too_generic | REVIEW | diagram nodes are too abstract to guide an editable broadcast visual. | Replace abstract labels with concrete actor -> mechanism -> result labels. |
| piti_slide_spec_productive_finance_policy | 17 | diagram_nodes_too_generic | REVIEW | diagram nodes are too abstract to guide an editable broadcast visual. | Replace abstract labels with concrete actor -> mechanism -> result labels. |
| piti_slide_spec_productive_finance_policy | 18 | diagram_nodes_too_generic | REVIEW | diagram nodes are too abstract to guide an editable broadcast visual. | Replace abstract labels with concrete actor -> mechanism -> result labels. |
| piti_slide_spec_productive_finance_policy | 20 | diagram_nodes_too_generic | REVIEW | diagram nodes are too abstract to guide an editable broadcast visual. | Replace abstract labels with concrete actor -> mechanism -> result labels. |
| piti_slide_spec_productive_finance_policy | 22 | diagram_nodes_too_generic | REVIEW | diagram nodes are too abstract to guide an editable broadcast visual. | Replace abstract labels with concrete actor -> mechanism -> result labels. |
| piti_slide_spec_productive_finance_policy | 22 | manual_insert_required_without_editor_instruction | REVIEW | proof_object requires manual insertion, but no editor instruction is available. | Add a short editor_instruction describing what the editor should insert or verify. |
| piti_slide_spec_productive_finance_policy | 24 | diagram_nodes_too_generic | REVIEW | diagram nodes are too abstract to guide an editable broadcast visual. | Replace abstract labels with concrete actor -> mechanism -> result labels. |

## Slide QA

| slide_no | screen_headline | layout_intent | proof_object.type | screen_body lines | overflow_notes count | needs_source | needs_fact_check | required_before_broadcast | manual_insert_required | visual_qa_flags | visual_qa_severity |
|---:|---|---|---|---:|---:|---|---|---|---|---|---|
| 1 | 생산적 금융과 정책자금 전환 | title | none | 2 | 0 | false | false | false | false | none | none |
| 2 | 금융위원장이 던진 질문 하나 | chart_table_reference | chart | 0 | 3 | false | true | true | true | none | none |
| 3 | 은행 입장에서는 담보가 제일 편하다 | diagram | diagram | 0 | 3 | false | true | true | true | diagram_nodes_too_generic | REVIEW |
| 4 | 그런데 AI 산업은 담보보다 시간이 먼저 필요하다 | diagram | diagram | 0 | 3 | false | true | true | true | diagram_nodes_too_generic | REVIEW |
| 5 | 금융은 원래 안전해야 하는가, 위험을 져야 하는가 | diagram | diagram | 0 | 3 | false | false | false | true | diagram_nodes_too_generic, manual_insert_required_without_editor_instruction | REVIEW |
| 6 | AI·반도체 투자와 장기 위험자본 | section_title | none | 0 | 0 | false | false | false | false | none | none |
| 7 | AI가 소프트웨어만의 문제가 아니게 된 순간 | source_card_or_article_quote | source_card | 0 | 3 | false | true | true | false | none | none |
| 8 | 장기 투자에는 기다릴 수 있는 돈이 필요하다 | chart_table_reference | chart | 0 | 3 | false | true | true | true | none | none |
| 9 | 부동산 담보는 보이지만, 기술의 미래는 잘 안 보인다 | diagram | diagram | 0 | 3 | false | true | true | true | diagram_nodes_too_generic | REVIEW |
| 10 | 그래서 정책금융은 시장이 못 보는 시간을 보겠다는 말일 수 있다 | diagram | diagram | 0 | 3 | false | true | true | true | diagram_nodes_too_generic | REVIEW |
| 11 | 이건 “은행이 더 착해져야 한다”는 얘기가 아니다 | diagram | diagram | 0 | 4 | false | false | false | true | diagram_nodes_too_generic, overflow_notes_too_large, manual_insert_required_without_editor_instruction | REVIEW |
| 12 | 국민성장펀드와 정책금융 논쟁 | section_title | none | 2 | 0 | false | false | false | false | none | none |
| 13 | 국민성장펀드라는 이름이 붙으면 이야기는 더 어려워진다 | chart_table_reference | chart | 0 | 3 | false | true | true | true | none | none |
| 14 | 위험을 나눈다는 말은 손실 가능성도 나눈다는 뜻이다 | chart_table_reference | chart | 0 | 3 | false | true | true | true | none | none |
| 15 | 정책금융의 어려움은 “누가 먼저 잃을 것인가”다 | source_card_or_article_quote | article_quote | 2 | 3 | false | true | true | true | none | none |
| 16 | 성장산업을 돕는 것과 특정 기업을 밀어주는 것은 다르다 | diagram | diagram | 0 | 3 | false | true | true | true | diagram_nodes_too_generic | REVIEW |
| 17 | 반대쪽 질문도 있다: 그럼 아무도 위험을 안 지면 어떻게 하나 | diagram | diagram | 0 | 3 | false | true | true | true | diagram_nodes_too_generic | REVIEW |
| 18 | 결국 질문은 성장의 과실보다 위험의 배분이다 | diagram | diagram | 0 | 3 | false | true | true | true | diagram_nodes_too_generic | REVIEW |
| 19 | 금융권은 어디까지 위험을 나눌 수 있는가 | section_title | none | 2 | 0 | false | false | false | false | none | none |
| 20 | 금융권에 “성장에 베팅하라”고 말하는 순간 생기는 문제 | diagram | diagram | 0 | 3 | false | true | true | true | diagram_nodes_too_generic | REVIEW |
| 21 | 이 부분은 아직 숫자가 필요하다 | appendix_checklist | none | 2 | 2 | false | true | true | false | none | none |
| 22 | 투자 이야기로 들리지 않게 조심해야 한다 | diagram | diagram | 0 | 3 | false | false | false | true | diagram_nodes_too_generic, manual_insert_required_without_editor_instruction | REVIEW |
| 23 | 방송 전 꼭 채워야 할 자료 | appendix_checklist | none | 2 | 2 | true | true | true | false | none | none |
| 24 | 금융은 위험을 피하는 기술인가, 좋은 위험을 고르는 기술인가 | diagram | diagram | 0 | 3 | false | true | true | true | diagram_nodes_too_generic | REVIEW |
