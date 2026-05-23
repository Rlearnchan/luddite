# Jibi Content Enrichment Review — 2026-05-23

## Summary

- selected_candidates: 11
- top_selected: 1
- near_miss_selected: 10
- enrichment_ok: 11
- enrichment_blocked: 0
- enrichment_paywalled_or_teaser: 0
- enrichment_empty: 0
- enrichment_error: 0

## Source Status Summary

| source | selected | ok | blocked | paywalled_or_teaser | empty | error | dominant_method |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | --- |
| BBC News | 4 | 4 | 0 | 0 | 0 | 0 | bbc_next_data_text |
| NPR | 3 | 3 | 0 | 0 | 0 | 0 | npr_storytext_p |
| 연합인포맥스 | 4 | 4 | 0 | 0 | 0 | 0 | infomax_article_view_content |

## Candidate Enrichment Table

| role | title | source | status | method | body_chars | paragraphs | meta_description_chars | reason |
| --- | --- | --- | --- | --- | ---: | ---: | ---: | --- |
| top | The Papers: 'Heat leaves Africa and Med in shade' and 'Can't cope without Catherine' | BBC News | ok | bbc_next_data_text | 4538 | 25 | 95 |  |
| near_miss | [발전사 이모저모] 동서, 석탄 대체 전원 가동…남부 'K-가스터빈' 시운전 | 연합인포맥스 | ok | infomax_article_view_content | 1359 | 10 | 299 |  |
| near_miss | [다음주 재정경제부 등 경제부처 일정] | 연합인포맥스 | ok | infomax_article_view_content | 2715 | 83 | 299 |  |
| near_miss | UK officials suggested single market for goods with Europe | BBC News | ok | bbc_next_data_text | 2744 | 18 | 113 |  |
| near_miss | Ask AI or just Google it? Google makes a big change to a little search box | NPR | ok | npr_storytext_p | 5061 | 22 | 123 |  |
| near_miss | '한국 진출 27주년'…스타벅스코리아 주인 바뀔 수도 있나 | 연합인포맥스 | ok | infomax_article_view_content | 1278 | 20 | 299 |  |
| near_miss | 국채선물, 종전 합의 기대 속 상승…10년물 12틱↑ | 연합인포맥스 | ok | infomax_article_view_content | 908 | 9 | 298 |  |
| near_miss | 'Eat, sleep, rave, repeat': Fatboy Slim lights up Radio 1's Big Weekend | BBC News | ok | bbc_next_data_text | 5439 | 45 | 111 |  |
| near_miss | How Panorama exposed rape allegations on Married at First Sight UK | BBC News | ok | bbc_next_data_text | 9256 | 64 | 96 |  |
| near_miss | 'It Takes Two' rapper Rob Base, who helped bring hip-hop mainstream, dies at 59 | NPR | ok | npr_storytext_p | 1544 | 8 | 192 |  |
| near_miss | 1 person died, 36 injured after blast at New York City shipyard, officials say | NPR | ok | npr_storytext_p | 2736 | 16 | 172 |  |

## RSS-only vs Enriched What-if Scoring

| role | title | source | status | score_delta | action_delta | grade_delta | resolved | remaining_gate_reasons |
| --- | --- | --- | --- | ---: | --- | --- | --- | --- |
| top | The Papers: 'Heat leaves Africa and Med in shade' and 'Can't cope without Catherine' | BBC News | ok | -9.2 | gather_more_evidence -> editorial_review | C -> C | disqualifying_details_found | market_rate_without_macro_bridge |
| near_miss | [발전사 이모저모] 동서, 석탄 대체 전원 가동…남부 'K-가스터빈' 시운전 | 연합인포맥스 | ok | 4.4 | gather_more_evidence -> gather_more_evidence | B -> B | none | generic_why_for_unspecific_seed_type |
| near_miss | [다음주 재정경제부 등 경제부처 일정] | 연합인포맥스 | ok | -29.0 | gather_more_evidence -> editorial_review | B -> C | disqualifying_details_found | single_company_without_broader_bridge |
| near_miss | UK officials suggested single market for goods with Europe | BBC News | ok | -6.0 | gather_more_evidence -> editorial_review | B -> B | none | generic_why_for_unspecific_seed_type |
| near_miss | Ask AI or just Google it? Google makes a big change to a little search box | NPR | ok | 3.0 | gather_more_evidence -> gather_more_evidence | B -> B | none | generic_why_for_unspecific_seed_type |
| near_miss | '한국 진출 27주년'…스타벅스코리아 주인 바뀔 수도 있나 | 연합인포맥스 | ok | -32.0 | keep_for_later -> editorial_review | C -> D | disqualifying_details_found | generic_why_for_unspecific_seed_type |
| near_miss | 국채선물, 종전 합의 기대 속 상승…10년물 12틱↑ | 연합인포맥스 | ok | 0.0 | editorial_review -> editorial_review | C -> C | none | market_rate_without_macro_bridge |
| near_miss | 'Eat, sleep, rave, repeat': Fatboy Slim lights up Radio 1's Big Weekend | BBC News | ok | -6.0 | reject -> reject | D -> D | none | generic_why_for_unspecific_seed_type |
| near_miss | How Panorama exposed rape allegations on Married at First Sight UK | BBC News | ok | 0.0 | reject -> reject | D -> D | none | generic_why_for_unspecific_seed_type |
| near_miss | 'It Takes Two' rapper Rob Base, who helped bring hip-hop mainstream, dies at 59 | NPR | ok | 26.6 | reject -> gather_more_evidence | D -> B | none | generic_why_for_unspecific_seed_type |
| near_miss | 1 person died, 36 injured after blast at New York City shipyard, officials say | NPR | ok | 26.6 | reject -> gather_more_evidence | D -> B | none | generic_why_for_unspecific_seed_type |

## Copyright / Storage Note

No full article bodies are printed or committed. Enrichment is used only for derived diagnostics.
