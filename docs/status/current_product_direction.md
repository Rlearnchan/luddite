# Current Product Direction after Milestone 1.0 Sheet Append Start

Status date: 2026-05-18

## Current checkpoint

Luddite is at the v0.7 eval harness checkpoint plus v0.8/v0.8.1 design
alignment, v0.9.3 jibi Daily Digest quality calibration, v0.9.4 final
digest polish, and Milestone 1.0 Google Sheet `jibi 후보` append implementation.

Completed:

- parser smoke stable
- corpus insight docs
- golden reconstruction fixtures
- `validate-golden`
- `eval-jibi-seeds`
- `eval-anny-reconstruction`
- `eval-piti-deck-plan`
- Manual LLM Dry Run
- jibi / anny / piti dry runs evaluable through the eval harness
- jibi source/RSS strategy documented
- syuka-ops bridge designed as a read-only/search proxy
- Google Sheet append direction moved to the `jibi 후보` staging sheet
- anny direction expanded to Article -> Candidate -> Cluster -> Story Seed -> Storyline
- BDC mode kept open as design, outside the MVP implementation scope
- v0.9.4 digest summary wording clarified so `send_to_anny=0` is not confused
  with zero useful Top Candidates
- visible `why_interesting` reduced generic scoring clauses; generic signals can
  live in `score_reason`
- Milestone 1.0 dry-run-capable Google Sheet appender added for `jibi 후보`
- duplicate rows are skipped by `duplicate_key` or `source_url_canonical`

Not started:

- real LLM API calls
- jibi/anny/piti production agent implementation
- RSS collector
- Google Sheets API direct fetch
- Slack bot implementation
- full PPT generator
- image auto collection
- syuka-ops DB bridge

## Product priority

Short-term implementation priority:

1. jibi Daily Digest MVP
2. Google Sheet append
3. Luddite Slack bot
4. anny DB-based storyline
5. syuka-ops similarity/performance bridge
6. piti renderer/PPTX draft

## Key design changes

- The first real user-facing goal is not automatic PPT creation. It is research
  topic selection support.
- The first demo is a daily morning digest of 10 candidate topics.
- `jibi` collects every day.
- Humans may collect less on Wednesday/Thursday/Friday because PPT production is
  heavier then, but the bot has no such limitation.
- `jibi` may append rows to a dedicated Google Sheet staging tab.
- Bot rows must stay separate from human-operated rows.
- Slack should start as a separate Luddite bot, not as a direct extension of
  `syuka-ops`.
- `syuka-ops` is the past-video metadata/transcript/view database; Luddite is
  the future-candidate discovery database.
- BDC is not an MVP target, but candidate/storyline schemas should leave room
  for `mode: normal | bdc`.

## Google Sheet append principles

- Target sheet: `jibi 후보`
- Keep existing `주제 찾기` as the human-operated sheet.
- Never overwrite human rows.
- `jibi` append is append-only for MVP.
- Duplicate rows are skipped, not updated, when `duplicate_key` or
  `source_url_canonical` already exists.
- Humans mark `review_result` as blank, keep, promote, needs_more_evidence,
  editorial_review, or reject.
- Later, only `review_result=promote` rows may be promoted/copied to
  `주제 찾기`.
- Do not put subscription article full text in the visible sheet.
- Store link, short summary, `why_interesting`, `risk_flags`, and
  `recommended_action` instead.

Required staging metadata:

```text
digest_date
collected_at
last_seen_at
duplicate_key
source_url_canonical
```

Implemented command:

```text
luddite append-jibi-sheet --dry-run
make append-jibi-sheet
```

The command writes an append report under `outputs/reports/`. It does not
promote rows into `주제 찾기`.

Authentication and first-run rules:

- Service account is the default Google Sheets auth mode for automation.
- Add the service account email as an editor on the shared spreadsheet before
  the first real append.
- Keep the service account JSON local and out of git. Use
  `GOOGLE_APPLICATION_CREDENTIALS`, `LUDDITE_GOOGLE_SERVICE_ACCOUNT_JSON`, or
  the gitignored `config/google_sheets.local.yaml`.
- Keep committed config placeholder-only in `config/google_sheets.example.yaml`.
  Real spreadsheet ids and local credential paths should not be committed.
- OAuth is fallback only when a service account cannot be added to the sheet.
- First real execution should be dry-run, then 1-2 test rows, then full preview,
  then duplicate rerun verification.

## Source registry status

- `rss_candidate` entries are still unverified endpoint candidates.
- Before implementing the RSS collector, each candidate source needs endpoint
  discovery, fetch test, and parse test.
- Milestone 1.1 adds `make probe-rss-sources` for one-shot RSS/Atom endpoint
  probing only. It is not a 24/7 collector.
- Milestone 1.1.1 improves feed discovery with HTML autodiscovery, expanded
  known path candidates, and suggested source patch output.
- `status=rss_verified` means technical fetch+parse verification only.
  `collection_enabled=false` keeps operational collection off until terms and
  usage scope are reviewed.
- Milestone 1.1.2 adds
  `docs/integrations/rss_terms_enablement_review.md` and
  `config/rss_collection_allowlist.yaml`; all verified feeds stay disabled
  until an operator enables them after review.
- Milestone 1.2 adds a one-shot `make fetch-rss-articles` path that writes
  `data/inbox/articles/rss_YYYY-MM-DD.jsonl` for enabled RSS sources. It is not
  a scheduler and does not store full article text.
- Milestone 1.2.1 keeps that one-shot shape and adds run-level dedupe,
  source contribution reporting, feed-summary cleanup, and a small domestic
  smoke allowlist: BBC, NPR, Atlas Obscura, 연합인포맥스, 한국경제. 한국은행 and
  정책브리핑 remain disabled evidence sources; 연합뉴스 remains retry-later/manual.
- Milestone 1.2.2 adds an RSS candidate quality gate before Top Candidate
  selection: sports-only, single-event accident/crime, pure place listings,
  live politics, empty-summary items, and single-stock/asset frames are
  downranked or excluded unless a broader structure is visible. Top Candidates
  are selected only after quality gating and source balancing.
- Milestone 1.2.3 adds editorial scoring polish: domestic finance/policy and
  RSS items now get narrower categories such as `productive_finance_policy`,
  `industrial_policy_rnd`, `single_company_financing`, `market_rate_stress`,
  `ai_knowledge_institution`, `infrastructure_project_failure`, and
  `climate_policy_conflict`. Generic rationale no longer keeps weak `other`
  candidates in Top Candidates.
- Milestone 1.3 adds a rule-based Evidence Cluster / Story Seed MVP. Scored
  candidates are grouped into `data/candidates/jibi_candidate_clusters.jsonl`,
  with readiness, missing evidence, suggested official sources, and future
  hooks for syuka-ops and LLM enrichment. It does not generate full anny
  storylines.
- Milestone 1.3.1 adds story seed handoff polish. Full clusters stay in the
  audit JSONL/report, while `data/candidates/anny_story_seed_handoff.jsonl` and
  `outputs/daily_digest/YYYY-MM-DD_story_seed_handoff.md` expose only
  handoff-worthy story seeds with quality flags and handoff priority. Weak
  generic `other` clusters are hidden from the human-facing handoff.
- Milestone 1.4 builds anny input bundles from story seed handoff records and
  scored candidates. Bundles include candidate articles, core questions,
  suggested story structure, missing evidence, official-source suggestions, and
  do-not-claim guardrails. It still does not generate full anny storylines or
  call an LLM.
- Milestone 1.4.1 cleans bundle evidence tasks, enriches candidate article
  context, adds dry-run readiness fields, and defines
  `eval/golden_cases/anny_dry_run_cases.json` for manual anny storyline dry
  runs. It still does not generate a storyline.
- Milestone 1.5 prepares the first manual anny storyline dry run for
  `AI 즉답 시대의 지식기관 역할`. It extracts a single GPT Pro input bundle under
  `outputs/model_dry_runs/anny_storyline/` and adds a validator for the future
  manual storyline JSON. Production anny generation and LLM API calls remain out
  of scope.
- The 1.5 GPT Pro dry run is a story-structure sample built from the input
  bundle, not a completed research packet or broadcast-ready script. Passing the
  dry-run eval means the structure is usable; evidence enrichment is still
  required before production anny generation.
- Milestone 1.5.1 creates an evidence enrichment plan for the same AI
  knowledge-institution topic. It maps `needs_source` / `needs_fact_check`
  slides to evidence tasks, writes an evidence pack scaffold, and defines
  Milestone 1.5.2 as an enriched manual dry run. It still does not fetch the web
  or call an LLM.
- Probe output is written to `outputs/reports/rss_probe_YYYY-MM-DD.md` and
  `data/manifests/rss_probe_results.jsonl`.
- A source should only move from `rss_candidate` to `rss_verified` after fetch
  and parse tests pass, and the registry update is still manual.
- `subscription_manual` sources must not be auto-fetched; use links and short
  summaries only.

## Slack bot principles

- Luddite starts as a separate Slack bot.
- `syuka-ops` remains the system for past video, transcript, thumbnail, and
  metadata search.
- Luddite is for future candidate discovery, topic selection, and storyline
  requests.
- Long-term, Luddite may query syuka-ops DB/API for past video similarity and
  view-performance proxy.

MVP commands:

```text
/luddite today
/luddite search <keyword>
/luddite candidate <candidate_id>
/luddite help
```

Later buttons:

```text
Keep
Needs more evidence
Editorial review
Reject
Request storyline
```

## Next milestones

Milestone 0.8: Manual LLM Dry Run

- jibi 6 cases
- anny `pawnshop_f88` 1 case
- piti `pawnshop_f88` 1 case
- no API calls
- save GPT Pro manual outputs as JSON/JSONL and run existing eval runners

Milestone 0.9: jibi Daily Digest MVP

- daily collection
- weekday morning digest
- 10 human-facing candidates
- Markdown report
- Google Sheet append preparation
- later Slack bot integration

Milestone 1.0: Google Sheet `jibi 후보` append implementation

Milestone 1.1: RSS endpoint discovery / fetch test

Milestone 1.2: RSS item ingestion MVP

Milestone 1.2.1: RSS ingest dedupe/report polish + small domestic source enable

Milestone 1.2.2: RSS Candidate Quality Gate + Source-specific Filtering

Milestone 1.2.3: RSS Candidate Editorial Scoring Polish

Milestone 1.3: Evidence Cluster / Story Seed MVP

Milestone 1.3.1: Story Seed Handoff Polish

Milestone 1.4: anny Story Seed Input Builder

Milestone 1.4.1: Bundle Hygiene + Anny Dry Run Prep

Milestone 1.5: Manual Anny Storyline Dry Run

Milestone 1.5.1: Evidence Enrichment Plan for Anny

Milestone 1.5.2a: Evidence Fill for AI Knowledge Institution

- Fill the AI knowledge-institution evidence pack with a small curated source set
  before another manual dry run.
- Keep full article text out of repo artifacts; store only title, URL, source,
  short summary, role, reliability, and manual-check state.
- Treat question/bridge slides as `rhetorical_bridge` with low source priority
  instead of forcing every line into a supporting-article task.
- Mark slide evidence needs as covered/partial/missing and expose
  `ready_for_enriched_dry_run` before 1.5.2b.

Milestone 1.5.3: Anny Evidence/Fact-Check Review + Source Hygiene

- Do not write a new storyline. Review the current enriched manual dry run.
- Add slide-level sidecar metadata for `fact_check_priority`,
  `fact_check_reason`, `required_before_broadcast`, and `source_roles`.
- Treat `ready_for_prompt_design=true` as acceptable while keeping
  `ready_for_production_agent=false` and `ready_for_broadcast=false`.
- Carry prompt rules forward: distinguish sourced slides from fact-checked
  slides, include counterpoints, keep Korea bridge as supporting context, and
  avoid over-sourcing rhetorical bridge slides.

Milestone 1.6: Anny Prompt / Eval Contract Design

- Generalize 1.5.x manual/enriched dry-run learnings into a prompt/eval contract.
- Extend hygiene metadata with `fact_check_kind`, `required_before_storyline`,
  `required_before_broadcast`, and slide-specific `source_refs`.
- Validator can require the hygiene contract without implementing a production
  anny agent or making an LLM API call.
- Keep the second dry-run fixture, `생산적 금융과 정책자금 전환`, as a
  prompt/eval case only. It needs stronger policy/investment guardrails before
  any production generation.

Milestone 1.6.1: Prompt Contract Finalization + Second Dry-run Prep

- Finalize the output contract in `docs/product/anny_mvp_storyline_spec.md`.
- Prepare the second dry-run input bundle for `생산적 금융과 정책자금 전환`.
- Add policy/finance guardrails to prompt/eval: no policy-effect certainty, no
  investment advice, no price/return/stock forecasts, no corporate/product promo.
- Keep `ready_for_prompt_design=true`, `ready_for_production_agent=false`, and
  `ready_for_broadcast=false`.

Milestone 1.6.4: Anny Contract Final Polish + Finance Evidence Fill Prep

- Keep production anny out of scope. This is still prompt/eval contract and
  evidence-prep work only.
- Finalize `docs/product/anny_output_contract.md` and
  `docs/product/anny_prompt_contract_lessons.md`.
- Compare the AI knowledge-institution and productive-finance manual dry runs in
  `outputs/reports/anny_dry_run_comparison.md`.
- Prepare `data/candidates/anny_evidence_pack_productive_finance_policy.json`
  with URL-pending evidence categories for the next manual evidence fill.
- Finance evidence fill must cover official material, policy mechanism,
  independent long-term investment context, counterpoint, market/finance view,
  and visual candidates without storing full article text.
- Maintain `ready_for_prompt_design=true`, `ready_for_production_agent=false`,
  and `ready_for_broadcast=false`.

Milestone 1.7: Anny DB-based MVP Design / Run Contract Scaffold

- Add `specs/anny_run_input_schema.json` and
  `specs/anny_run_manifest_schema.json`.
- Add `luddite anny-run-storyline` / `make anny-run-storyline` as a local
  validation runner for manually prepared storyline JSON.
- The runner writes run input files, manifests, and reports for the two existing
  manual dry runs. It uses the existing dry-run validator and hygiene contract.
- This is not a production anny agent and does not call an LLM API.
- Current readiness:
  `ready_for_prompt_design=true`, `ready_for_manual_storyline=true`,
  `ready_for_api_experiment=false`, `ready_for_production_agent=false`,
  `ready_for_broadcast=false`.

Milestone 1.7.1: Run Registry Polish + Reproducibility

- Add run manifest checksums for input bundle, evidence pack, output storyline,
  hygiene sidecar, and prompt file.
- Copy output contract, prompt, validator, and schema versions into every run
  manifest/report.
- Generate `data/manifests/anny_runs/index.jsonl` as a local registry of anny
  manual runs.
- Reports include file existence, checksum summaries, readiness state, and the
  warning that a passing run does not imply production readiness.
- Keep `ready_for_api_experiment=false` and `ready_for_production_agent=false`.

Milestone 1.8: Anny API Experiment Prep / Failure Handling Scaffold

- Prepare API experiment handling without calling an LLM API.
- Run modes include `api_experiment`; `openai_api` is reserved as a future
  `model_source`.
- Future API experiment outputs should preserve `raw_model_output.txt` under
  `outputs/model_dry_runs/anny_api_experiments/<run_id>/`.
- Failure taxonomy and repair policy are documented in
  `docs/product/anny_failure_modes.md`.
- Anny output is evidence-bound: source URLs must come from input bundle or
  evidence pack URLs, and unsupported claims keep `needs_source` or
  `needs_fact_check`.
- First future API experiment candidate is `AI 즉답 시대의 지식기관 역할`.
- Current readiness:
  `ready_for_api_experiment_prep=true`, `ready_for_api_experiment=false`,
  `ready_for_production_agent=false`, `ready_for_broadcast=false`.

Milestone 1.8.1: API Experiment Preflight / Fixture Simulation

- Add fixture-only validation for future API outputs. This still does not call
  an LLM API.
- Fixtures cover valid raw JSON, invalid JSON, source hallucination, and missing
  counterpoint.
- `luddite validate-anny-api-experiment` preserves `raw_model_output.txt`,
  writes `parsed_storyline.json` when parsing succeeds, and creates manifest and
  Markdown validation reports.
- Evidence-bound URL checks compare storyline `source_urls` and
  `source_refs.url` against the input bundle and evidence pack URL set.
- Repair policy remains strict: `repair_attempted=false` and failed raw outputs
  are reported, not rewritten.
- Current readiness after fixture preflight:
  `ready_for_api_experiment_prep=true`,
  `ready_for_api_experiment=true candidate pending human approval`,
  `ready_for_production_agent=false`, `ready_for_broadcast=false`.

Milestone 1.9: First Anny API Experiment

- Add `luddite run-anny-api-experiment` / `make run-anny-api-experiment` for one
  controlled API call on `AI 즉답 시대의 지식기관 역할`.
- API configuration is env-only: `OPENAI_API_KEY` and
  `LUDDITE_ANNY_API_MODEL` are required; `LUDDITE_ANNY_API_TEMPERATURE` defaults
  to `0.2` and may not exceed `0.2`.
- The command stores input bundle, evidence pack, prompt, raw model output,
  parsed storyline when available, response metadata, validation report, and
  manifest under the run directory.
- Validation reuses the 1.8.1 evidence-bound checks and failure taxonomy.
- The API output is compared with the AI knowledge-institution enriched manual
  dry run in
  `outputs/reports/anny_api_experiment_ai_knowledge_institution_comparison.md`.
- This is not a production anny agent and does not batch topics.
- Keep `ready_for_production_agent=false` and `ready_for_broadcast=false`.

Milestone 1.16.1: API Experiment Summary / Production Gate Decision

- Summarize AI knowledge-institution API experiments v1-v9 in
  `outputs/reports/anny_api_experiment_ai_knowledge_institution_summary.md`.
- v9 is the most stable AI case run so far: schema-valid, key beat recall 1.00,
  source hallucination 0, do-not-claim violations 0, unsupported claim 0, and
  counterpoint included.
- Remaining failure is `needs_fact_check_removed_too_aggressively`, concentrated
  in education/AI/institution-role slides that still need conservative
  `needs_fact_check=true`.
- Section count policy is clarified: 3-4 sections are the production default;
  5 sections are an API-experiment warning unless explicitly justified.
- Current readiness:
  `ready_for_api_experiment=true`, `ready_for_production_agent=false`,
  `ready_for_broadcast=false`.
- Next recommended milestone is Productive Finance First API Experiment, not a
  production anny agent. The goal is to check the same contract against a
  higher-risk policy/finance topic.

Milestone 1.17: Productive Finance First API Experiment

- Run one controlled API experiment for `생산적 금융과 정책자금 전환`.
- This remains a single API experiment, not a production anny agent and not a
  batch runner.
- Output artifacts are stored under
  `outputs/model_dry_runs/anny_api_experiments/anny_api_experiment_productive_finance_policy_v1/`.
- Comparison report:
  `outputs/reports/anny_api_experiment_productive_finance_policy_v1_comparison.md`.
- First result: schema-valid, source hallucination 0, do-not-claim violations 0,
  counterpoint included, and policy/finance guardrail errors 0.
- Remaining failures are `unsupported_claim` and `key_beat_drift`.
- Interpretation: policy/investment safety guardrails held, but finance-specific
  source hygiene and stable key-beat anchor alignment need another prompt or
  validator patch before any production step.
- Keep `ready_for_api_experiment=true`, `ready_for_production_agent=false`, and
  `ready_for_broadcast=false`.

Milestone 1.17.1: Productive Finance Claim Hygiene / Key Beat Patch

- Add finance-specific source/claim markers for policy effect, fund structure,
  loss-sharing, bank soundness, BIS/risk-weighted asset, market-finance view,
  and policy-finance failure/counterpoint claims.
- Productive finance key beats now use stable ids and anchor phrases:
  `kb_finance_short_term_limit`, `kb_long_term_risk_capital`,
  `kb_growth_fund_policy_finance`, `kb_finance_risk_sharing`, and
  `kb_counterpoint_policy_risk`.
- Revalidate the existing productive finance API v1 output without a new API
  call and write
  `outputs/reports/anny_api_experiment_productive_finance_policy_v1_claim_hygiene_review.md`.
- The stricter validator now records unsupported claims and
  policy-finance fact-check conservatism gaps more explicitly. This is expected
  and does not imply a regression in production readiness.
- Keep `ready_for_production_agent=false` and `ready_for_broadcast=false`.

Milestone 1.17.2: Human-readable Anny Storyline Samples

- Add `luddite render-anny-storyline-sample` and
  `make render-anny-storyline-samples`.
- Render four existing manual/API storyline JSON artifacts into Markdown under
  `outputs/samples/anny_storylines/`.
- The sample README explains that these are manual/API dry-run samples, not
  production Anny output or broadcast-ready scripts.
- Markdown samples expose sections, slides, sources, source refs,
  `needs_source`, `needs_fact_check`, fact-check metadata, key-beat metadata,
  and production-checklist markers for human review.

Milestone 1.17.4: Human-readable Sample Renderer Polish

- Add `compact`, `audit`, and `both` render modes to
  `luddite render-anny-storyline-sample`.
- `make render-anny-storyline-samples` now creates compact research-team samples
  under `outputs/samples/anny_storylines/compact/` while keeping root-level audit
  samples for development and validator review.
- Compact samples use global slide numbers and show headline, body, first
  sources, `needs_source`, `needs_fact_check`, before-broadcast/fact-check
  metadata, and a shortened note.
- Detailed `source_refs`, key-beat metadata, and hygiene fields remain in audit
  mode.
- The sample README now recommends
  `compact/ai_knowledge_institution_manual_enriched.md` as the first human
  reading sample and warns that productive finance API v1 is failure analysis,
  not a product example.

Milestone 1.17.5: Human Review Feedback Template

- Add a review template for research-team feedback:
  `docs/reviews/anny_storyline_sample_review_template.md`.
- Add a sample review guide:
  `docs/reviews/anny_storyline_sample_review_guide.md`.
- The guide points reviewers to the compact manual enriched samples first,
  explains manual enriched vs API experiment outputs, and reiterates that the
  samples are not production output or broadcast-ready scripts.
- The sample README links to the guide and template.
- No API calls, production Anny agent, batch runner, PPT generator, or external
  research automation are part of this milestone.

Milestone 1.17.6: Human Review Pilot

- Add a human review pilot pack:
  `docs/reviews/anny_storyline_human_review_pilot_pack.md`.
- Add a per-reviewer result template:
  `docs/reviews/results/anny_storyline_sample_review_YYYY-MM-DD.md`.
- Add a consolidated summary template:
  `docs/reviews/anny_storyline_sample_review_summary_template.md`.
- The pilot asks reviewers to read the compact AI knowledge institution and
  productive finance manual samples first, then record whether the artifact
  feels useful as a newsletter draft, storyline draft, research memo, or source
  checklist.
- Keep productive finance API v1 as failure analysis only.
- Keep `ready_for_production_agent=false` and `ready_for_broadcast=false`.

Milestone 1.18: Piti Storyline-to-Deck Plan MVP

- Convert existing manual/enriched Anny storyline samples into deterministic
  Piti deck-plan JSON, without generating PPTX or calling an LLM.
- Add `luddite build-piti-deck-plan` / `make build-piti-deck-plans`.
- Add `luddite render-piti-storyboard` / `make render-piti-storyboards`.
- Output deck plans:
  `data/candidates/piti_deck_plans/ai_knowledge_institution_deck_plan.json`
  and
  `data/candidates/piti_deck_plans/productive_finance_policy_deck_plan.json`.
- Output storyboards:
  `outputs/samples/piti_storyboards/ai_knowledge_institution_storyboard.md`
  and
  `outputs/samples/piti_storyboards/productive_finance_policy_storyboard.md`.
- The deck plan keeps source URLs and image URLs separate, preserves
  `needs_source` / `needs_fact_check`, carries speaker notes forward, and marks
  production-checklist slides as appendix/internal material.
- The storyboard README states that these are storyboard/deck-plan samples, not
  PPTX, Google Slides, production Piti agent output, or broadcast-ready decks.
- Keep `ready_for_ppt_generation=false`,
  `ready_for_production_piti_agent=false`, `ready_for_production_agent=false`,
  and `ready_for_broadcast=false`.

Milestone 1.19: Piti PPTX Renderer Scaffold

- Add `luddite render-piti-pptx` and `make render-piti-pptx`.
- Render existing Piti deck plans into editable 16:9 PowerPoint skeletons:
  `outputs/pptx/ai_knowledge_institution_draft.pptx` and
  `outputs/pptx/productive_finance_policy_draft.pptx`.
- Add renderer documentation:
  `docs/product/piti_pptx_renderer_scaffold.md`.
- The renderer uses simple scaffold layouts, editable text boxes, visual
  placeholder boxes, and speaker notes preservation. It does not implement
  final Syukaworld visual fidelity.
- Speaker notes preserve source URLs, image URLs, visual plans, edit notes,
  `needs_source`, `needs_fact_check`, `required_before_broadcast`, and copyright
  risk markers.
- Production checklist slides are rendered as internal/appendix checklist
  material rather than normal broadcast claims.
- Render report:
  `outputs/reports/piti_pptx_render_report_2026-05-19.md`.
- Current readiness:
  `ready_for_ppt_generation=true` for scaffold review only,
  `ready_for_production_piti_agent=false`, `ready_for_broadcast=false`.
- Still out of scope: image auto collection/insertion, chart generation,
  Google Slides integration, LLM calls, production Piti agent, and production
  Anny agent.

Milestone 1.19.1: Syukaworld PPTX Style Extraction

- Add `luddite extract-pptx-style` and `make extract-pptx-style`.
- Analyze the first Syukaworld PPTX sample:
  `data/ppt/latest/raw/전당포 주식회사_배형찬.pptx`.
- Output shape-level style samples:
  `data/style_profiles/syukaworld_ppt_shape_samples.jsonl`.
- Output aggregate style profile:
  `data/style_profiles/syukaworld_ppt_style_profile.json`.
- Output human-readable report:
  `outputs/reports/piti_style_profile_report.md`.
- Extract slide size, shape x/y/w/h, text run font size/color/style where
  explicit, paragraph alignment/bullet/indent/line spacing, image/chart
  container positions, notes URL counts, and source/image URL counts.
- Mark likely theme/master inherited text style fields separately, because the
  PPTX sample often stores font family and some visual defaults through
  inherited theme/master styling rather than explicit run properties.
- Current sample profile: 16:9 slide size, 173 shape records, 130 text shape
  records, common explicit font sizes led by 28pt / 20pt / 54pt, and common
  explicit red text color `#FF0000`.
- Keep `ready_for_ppt_generation=true` for scaffold review only.
  `ready_for_renderer_style_application=false` until the next milestone.
- Still out of scope: applying the extracted style to the Piti renderer,
  production Piti agent, image auto collection/insertion, chart generation,
  Google Slides integration, and LLM calls.

Milestone 1.19.2: Theme/Master Font Extraction

- Extend `luddite extract-pptx-style` to parse PPTX theme/master/layout XML:
  `ppt/theme/theme*.xml`, `ppt/slideMasters/slideMaster*.xml`, and
  `ppt/slideLayouts/slideLayout*.xml`.
- Resolve theme font references such as `+mj-ea` and `+mn-ea` into actual
  candidate font families where possible.
- Add `theme_fonts`, `master_text_styles`, `placeholder_styles`, and
  `font_resolution` to `data/style_profiles/syukaworld_ppt_style_profile.json`.
- The first Syukaworld sample resolves the inherited Korean theme font to
  `맑은 고딕`; keep `Malgun Gothic` as the practical fallback name for
  Windows/PowerPoint-style rendering code.
- Update `outputs/reports/piti_style_profile_report.md` with theme/master font
  candidates, sparse explicit-font explanation, and renderer fallback notes.
- Keep `ready_for_renderer_style_application=false`; the extracted font profile
  is a reference for the next milestone, not yet applied to PPTX output.
- Still out of scope: Piti renderer style application, PPTX regeneration,
  image auto insertion, chart generation, Google Slides integration, and
  production Piti agent implementation.

Milestone 1.19.3: Apply Syukaworld Style Profile to Piti Renderer

- Extend `luddite render-piti-pptx` / `make render-piti-pptx` with optional
  `--style-profile`, defaulting to
  `data/style_profiles/syukaworld_ppt_style_profile.json`.
- Preserve existing scaffold PPTX outputs and add styled draft outputs:
  `outputs/pptx/ai_knowledge_institution_styled_draft.pptx` and
  `outputs/pptx/productive_finance_policy_styled_draft.pptx`.
- Apply extracted slide size, theme font candidate `맑은 고딕`, `Malgun Gothic`
  fallback metadata, common red text color, and median layout boxes for
  supported layout types.
- Keep visual placeholders as placeholders only, with quieter gray styling and
  visual plans preserved in speaker notes.
- Preserve speaker notes/source/fact-check flags and add parse-back counts to
  `outputs/reports/piti_pptx_render_report_2026-05-19.md`.
- Current readiness:
  `ready_for_ppt_generation=true` for scaffold/styled draft review only,
  `ready_for_production_piti_agent=false`, `ready_for_broadcast=false`.
- Still out of scope: production Piti agent, image auto collection/insertion,
  chart generation, Google Slides integration, LLM/API calls, and final
  Syukaworld visual fidelity claims.

Milestone 1.19.4: Piti Styled Renderer Layout Tuning

- Keep the extracted Syukaworld style profile but make styled drafts more
  readable with adaptive body font sizing: 28pt for short text, 24pt for
  medium text, and 20pt for long or visual-heavy slides.
- Separate text and visual placeholder regions on styled slides so placeholders
  do not collide with body text; overlap is now a failure for styled drafts and
  a warning for legacy scaffold outputs.
- Shorten on-slide visual placeholder labels to compact cues such as
  `[이미지 후보]`, `[차트 후보]`, `[도식 후보]`, and preserve detailed visual-plan
  descriptions in speaker notes.
- Keep section titles large but avoid forcing red on section-title slides; use
  theme/default black unless a stronger section-title color is explicitly
  extracted later.
- Add render-report metrics for adaptive font usage, downgraded font sizes,
  body line estimates, visually dense slides, visual+long-body slides, and
  text/visual overlap warnings.
- Regenerate styled draft PPTX outputs:
  `outputs/pptx/ai_knowledge_institution_styled_draft.pptx` and
  `outputs/pptx/productive_finance_policy_styled_draft.pptx`.
- Current readiness:
  `ready_for_ppt_generation=true` for scaffold/styled draft review only,
  `ready_for_production_piti_agent=false`, `ready_for_broadcast=false`.
- Still out of scope: production Piti agent, image auto collection/insertion,
  chart generation, Google Slides integration, LLM/API calls, and final
  Syukaworld visual fidelity claims.

Milestone 1.19.5: Piti Screen Formatting Rules v0.1

- Treat explicit screen-formatting rules as higher priority than style-profile
  frequency counts. Red `#FF0000` and 28pt are not generic body defaults.
- Document the v0.1 rules in `docs/product/piti_formatting_checklist.md`.
- Apply headline red 28pt while keeping normal Korean body text black by
  default.
- Add bilingual quote handling: English source lines render black 28pt and
  Korean translation/interpretation lines render red 28pt.
- Add chart/table placeholder grammar: black 28pt bold-underlined title,
  18pt bold data/body labels, and 20pt underlined parenthesized source label.
- Hide manual visual placeholders from styled screens by default; keep the
  visual plan and overflow body lines in speaker notes.
- Prefer left-side image/screenshot areas for image-heavy slides while keeping
  text on the right.
- Track report metrics for headline red count, body black count, bilingual
  quote count, chart/table style count, image-left count, hidden manual
  placeholders, screen-body overflow, split recommendations, and 20pt usage.
- Current readiness:
  `ready_for_ppt_generation=true` for scaffold/styled draft review only,
  `ready_for_production_piti_agent=false`, `ready_for_broadcast=false`.
- Still out of scope: production Piti agent, image auto collection/insertion,
  chart generation, Google Slides integration, LLM/API calls, and final
  Syukaworld visual fidelity claims.

Milestone 1.19.6: Piti Reference Layout Grammar Patch

- Tighten styled drafts against the pawn PPT reference grammar rather than
  only applying extracted colors and font sizes.
- Hide styled on-screen debug footers (`draft skeleton`, `needs_fact_check`,
  slide numbers); keep flags and source/fact-check state in speaker notes and
  reports.
- Restore title and section-title slides closer to reference rhythm: large
  centered black title/section treatment with body text moved to notes.
- Force normal content-slide headlines into the reference top-left band
  (`x≈1.59cm`, `y≈0.99cm`) instead of allowing centered/right-shifted headline
  layouts.
- Keep chart/table slides as a two-level screen: red top-left story headline
  plus black underlined chart/table title and large proof-object area.
- Continue to hide manual visual placeholders while making chart/diagram/image
  candidate placeholders compact and secondary.
- Current readiness:
  `ready_for_ppt_generation=true` for scaffold/styled draft review only,
  `ready_for_production_piti_agent=false`, `ready_for_broadcast=false`.
- Still out of scope: production Piti agent, image auto collection/insertion,
  chart generation, Google Slides integration, LLM/API calls, and final
  Syukaworld visual fidelity claims.

Milestone 1.19.7: Piti Proof Object Layout Scaffold

- Shift styled PPTX drafts from text-summary cards toward reference-style
  proof-object slides.
- Add an internal `proof_object` model derived from each slide's `visual_plan`,
  layout type, and slide type. Supported proof object types include image,
  chart, table, article quote, screenshot, diagram, logo, map, person photo,
  and generated-image candidate.
- Reserve screen areas for proof objects without collecting or inserting real
  images. Image/screenshot/diagram/article-quote proof objects use a left-half
  proof area with right-side interpretation text, while chart/table proof
  objects use a large center chart/table skeleton.
- Keep on-screen proof labels compact (`[이미지]`, `[차트]`, `[표]`,
  `[기사 캡처]`, `[도식]`) and preserve the full visual plan, proof-object
  metadata, sources, and fact-check flags in speaker notes.
- Add render-report metrics for proof object counts, type distribution,
  reserved proof areas, text-only slides, dense text-only slides,
  chart/table skeletons, article-quote skeletons, image-left layouts, and
  proof/text overlap.
- Styled drafts remain scaffold outputs only:
  `ready_for_ppt_generation=true` for review,
  `ready_for_production_piti_agent=false`, `ready_for_broadcast=false`.
- Still out of scope: image auto collection/insertion, actual chart generation,
  Google Slides integration, production Piti agent, LLM/API calls, and final
  Syukaworld visual fidelity claims.

Future milestone: anny DB-based Storyline MVP

Future milestone: syuka-ops similarity/performance bridge

Future milestone: piti renderer MVP
