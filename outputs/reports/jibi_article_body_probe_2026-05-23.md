# Jibi Article Body Access Probe — 2026-05-23

Scope: report-only probe against stored 2026-05-23 RSS links. Atlas Obscura intentionally excluded because representative access returned Cloudflare 403. Full article bodies are not reproduced here; this report records access/extraction metrics and scoring deltas only.

## Summary

- samples checked: 9
- good: 6
- paywalled_or_teaser: 2
- usable: 1
- tested sources: BBC News, NPR, 연합인포맥스, 한국경제
- key finding: article body/metadata enrichment is feasible for BBC, NPR, and 연합인포맥스; 한국경제 is mixed because some pages expose only premium/paywall teaser text while regular news pages expose usable body text.

## Sample Results

| sample | source | http | bytes | extraction | status | rss_summary_chars | body_chars | paragraphs | score_delta | top_gate_after | remaining_gate_reasons |
| --- | --- | ---: | ---: | --- | --- | ---: | ---: | ---: | ---: | --- | --- |
| bbc_top_heat_papers | BBC News | 200 | 229136 | bbc_next_data_text | good | 95 | 4538 | 25 | 20.8 | True | none |
| bbc_single_market_goods | BBC News | 200 | 230437 | bbc_next_data_text | good | 113 | 2744 | 18 | -6.0 | False | generic_why_for_unspecific_seed_type |
| npr_google_ai_search | NPR | 200 | 94244 | npr_storytext_p | good | 123 | 5058 | 22 | 3.0 | False | generic_why_for_unspecific_seed_type |
| npr_shipyard_blast | NPR | 200 | 72388 | npr_storytext_p | good | 172 | 2757 | 17 | 0.0 | False | generic_why_for_unspecific_seed_type |
| infomax_calendar | 연합인포맥스 | 200 | 132075 | infomax_article_view_content | good | 299 | 2715 | 83 | -29.0 | False | single_company_without_broader_bridge |
| infomax_starbucks | 연합인포맥스 | 200 | 129711 | infomax_article_view_content | good | 299 | 1278 | 20 | -32.0 | False | generic_why_for_unspecific_seed_type |
| hankyung_kiw_space | 한국경제 | 200 | 68066 | hankyung_articletxt | paywalled_or_teaser | 0 | 217 | 1 | n/a | n/a | paywalled_or_teaser |
| hankyung_senior_reit | 한국경제 | 200 | 72452 | hankyung_articletxt | paywalled_or_teaser | 0 | 290 | 3 | n/a | n/a | paywalled_or_teaser |
| hankyung_bus_lane | 한국경제 | 200 | 93014 | hankyung_articletxt | usable | 0 | 879 | 9 | 41.8 | False | generic_why_for_unspecific_seed_type |

## Scoring Delta Notes

- bbc_top_heat_papers: 50.0 / gather_more_evidence / C -> 70.8 / gather_more_evidence / B; flags none -> none; gate none -> none.
- bbc_single_market_goods: 61.0 / gather_more_evidence / B -> 55.0 / editorial_review / B; flags none -> none; gate generic_why_for_unspecific_seed_type -> generic_why_for_unspecific_seed_type.
- npr_google_ai_search: 61.0 / gather_more_evidence / B -> 64.0 / gather_more_evidence / B; flags none -> none; gate generic_why_for_unspecific_seed_type -> generic_why_for_unspecific_seed_type.
- npr_shipyard_blast: 34.4 / reject / D -> 34.4 / reject / D; flags none -> none; gate generic_why_for_unspecific_seed_type -> generic_why_for_unspecific_seed_type.
- infomax_calendar: 64.0 / gather_more_evidence / B -> 35 / editorial_review / C; flags none -> single_stock_or_asset_frame,single_company_frame; gate generic_why_for_unspecific_seed_type -> single_company_without_broader_bridge.
- infomax_starbucks: 37.4 / keep_for_later / C -> 5.4 / editorial_review / D; flags none -> single_stock_or_asset_frame; gate generic_why_for_unspecific_seed_type -> generic_why_for_unspecific_seed_type.
- hankyung_kiw_space: simulation skipped (paywalled_or_teaser).
- hankyung_senior_reit: simulation skipped (paywalled_or_teaser).
- hankyung_bus_lane: 0 / keep_for_later / D -> 41.8 / keep_for_later / C; flags empty_summary,empty_summary_domestic_business -> none; gate generic_why_for_unspecific_seed_type -> generic_why_for_unspecific_seed_type.

## Implications For PR8

- Add a report-only article enrichment stage before changing gate thresholds.
- Enrich only Top + Near Miss queue first, not all RSS items, to control network cost and extraction noise.
- Store extraction metadata: content_enrichment_status, content_enrichment_method, body_chars, paragraph_count, meta_description_chars, paywall_or_blocked reason.
- Do not store or print full copyrighted bodies in reports; store a bounded internal excerpt or derived signals if needed.
- Recompute candidate diagnostics with enriched summary as a what-if simulation, but keep the production Top gate unchanged until several daily runs confirm the effect.
- Source-specific handling is necessary: BBC uses Next.js JSON payloads, NPR has storytext paragraphs, 연합인포맥스 has article-view-content-div, 한국경제 has article-body/articletxt but premium pages need paywall detection, Atlas should be marked blocked/manual-only for now.

## GPT Pro Handoff

Review report `outputs/reports/jibi_article_body_probe_2026-05-23.md`: stored RSS links generally allow article-level HTML access for BBC, NPR, 연합인포맥스, and parts of 한국경제; Atlas is blocked by Cloudflare and can remain excluded/manual-only. Body enrichment materially improves some diagnostics: the BBC Top candidate strengthens from 50.0 to 70.8, NPR Google AI search gains additional evidence but still fails the generic why gate, and 한국경제 regular news loses empty_summary when body text is available. However enrichment can also reveal that some high raw-score items are schedule/list/premium/teaser pages, so the next PR should be report-only enrichment plus source-specific extraction and paywall/block detection, not threshold relaxation. Proposed PR8: content enrichment probe for Top + Near Miss only, with content_enrichment_status/method/body_chars/paragraph_count/paywall flags, and a what-if rescoring section comparing RSS-only vs enriched diagnostics.
