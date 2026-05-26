PYTHON ?= python3
VENV ?= .venv
VENV_PYTHON := $(VENV)/bin/python
PYTHONPATH ?= src
COMPARE_SLIDEABILITY_VISUAL_QA_ARGS ?= --include-direct --direct-run-id live_m132_20260520_all
JIBI_DATE ?= $(shell date +%F)
JIBI_RSS_INBOX ?= data/inbox/articles/rss_$(JIBI_DATE).jsonl
JIBI_SYUKA_DATA_DIR ?= /Users/bae/Documents/code/syuka-ops/data
JIBI_EDITORIAL_OVERRIDES ?= outputs/editorial_overrides/jibi_review_board_$(JIBI_DATE).json
JIBI_SHEET_NAME ?= Jibi
JIBI_SEARCH_PROVIDER ?= naver
JIBI_SEARCH_CATEGORIES ?= news
JIBI_SEARCH_PRIORITIES ?= high
JIBI_SEARCH_MAX_QUERIES ?= 10
JIBI_SEARCH_RESULTS_PER_QUERY ?= 5

.PHONY: setup test test-corpus lint doctor doctor-corpus parse-storylines parse-pptx fetch-sheets manifest corpus-smoke validate-golden eval-jibi-seeds eval-anny-reconstruction validate-anny-dry-run validate-anny-enriched-dry-run validate-anny-api-experiment run-anny-api-experiment run-anny-slide-spec-experiment run-anny-api-experiment-finance-v1 review-anny-api-finance-v1-claim-hygiene revalidate-anny-api-finance-v1 eval-piti-deck-plan build-piti-deck-plans build-piti-slide-specs validate-piti-slide-spec render-piti-storyboards render-piti-pptx render-piti-slide-spec-pptx render-piti-visual-qa render-pptx-contact-sheet summarize-pptx-contact-sheet-review check-pptx-contact-sheet-backend compare-slideability-visual-qa extract-pptx-style import-articles fetch-rss-articles normalize-candidates score-candidates cluster-jibi-candidates build-anny-input-bundles prepare-anny-input-bundles prepare-anny-dry-run prepare-anny-finance-dry-run plan-anny-evidence review-anny-fact-check compare-anny-dry-runs compare-anny-enriched-dry-runs anny-run-storyline render-anny-storyline-samples render-daily-digest jibi-digest jibi-mvp-rss-dry-run jibi-manual-update jibi-review-board-dry-run jibi-review-board-replace jibi-review-board-refresh-with-syuka jibi-review-board-replace-with-syuka jibi-review-board-alternate-dry-run jibi-syuka-snapshot-probe jibi-source-experiment-guardian jibi-review-feedback jibi-second-search-plan jibi-second-search-local jibi-second-search-web jibi-review-feedback-loop jibi-review-history-feedback jibi-content-enrichment-review append-jibi-sheet append-jibi-bundle-review-sheet probe-rss-sources

setup:
	$(PYTHON) -m venv $(VENV)
	$(VENV_PYTHON) -m pip install --upgrade pip
	$(VENV_PYTHON) -m pip install -r requirements-dev.txt
	$(VENV_PYTHON) -m pip install -e .

test:
	PYTHONPATH=$(PYTHONPATH) $(VENV_PYTHON) -m pytest

test-corpus:
	PYTHONPATH=$(PYTHONPATH) $(VENV_PYTHON) -m pytest -m corpus

lint:
	$(VENV_PYTHON) -m ruff check .

doctor:
	PYTHONPATH=$(PYTHONPATH) $(VENV_PYTHON) -m luddite doctor

doctor-corpus:
	PYTHONPATH=$(PYTHONPATH) $(VENV_PYTHON) -m luddite doctor-corpus

parse-storylines:
	PYTHONPATH=$(PYTHONPATH) $(VENV_PYTHON) -m luddite.parsers.parse_storylines

parse-pptx:
	PYTHONPATH=$(PYTHONPATH) $(VENV_PYTHON) -m luddite.parsers.parse_pptx

fetch-sheets:
	PYTHONPATH=$(PYTHONPATH) $(VENV_PYTHON) -m luddite.parsers.fetch_sheets

manifest:
	PYTHONPATH=$(PYTHONPATH) $(VENV_PYTHON) -m luddite.parsers.build_corpus_manifest

corpus-smoke:
	PYTHONPATH=$(PYTHONPATH) $(VENV_PYTHON) -m luddite.parsers.corpus_smoke

validate-golden:
	PYTHONPATH=$(PYTHONPATH) $(VENV_PYTHON) -m luddite validate-golden

eval-jibi-seeds:
	PYTHONPATH=$(PYTHONPATH) $(VENV_PYTHON) -m luddite eval-jibi-seeds

eval-anny-reconstruction:
	PYTHONPATH=$(PYTHONPATH) $(VENV_PYTHON) -m luddite eval-anny-reconstruction

validate-anny-dry-run:
	PYTHONPATH=$(PYTHONPATH) $(VENV_PYTHON) -m luddite validate-anny-dry-run

validate-anny-enriched-dry-run:
	PYTHONPATH=$(PYTHONPATH) $(VENV_PYTHON) -m luddite validate-anny-dry-run \
		--storyline outputs/model_dry_runs/anny_storyline/ai_knowledge_institution_gpt_pro_storyline_enriched.json \
		--baseline-storyline outputs/model_dry_runs/anny_storyline/ai_knowledge_institution_gpt_pro_storyline.json \
		--hygiene-jsonl outputs/model_dry_runs/anny_storyline/ai_knowledge_institution_source_hygiene.jsonl \
		--report outputs/eval/anny_storyline_dry_run/latest_enriched.md \
		--output-jsonl outputs/eval/anny_storyline_dry_run/latest_enriched.jsonl \
		--require-enriched \
		--require-hygiene-contract

validate-anny-api-experiment:
	PYTHONPATH=$(PYTHONPATH) $(VENV_PYTHON) -m luddite validate-anny-api-experiment \
		--raw-output tests/fixtures/anny_api_experiment/valid_ai_knowledge_storyline_raw.txt
	PYTHONPATH=$(PYTHONPATH) $(VENV_PYTHON) -m luddite validate-anny-api-experiment \
		--raw-output tests/fixtures/anny_api_experiment/invalid_json_raw.txt
	PYTHONPATH=$(PYTHONPATH) $(VENV_PYTHON) -m luddite validate-anny-api-experiment \
		--raw-output tests/fixtures/anny_api_experiment/source_hallucination_raw.txt
	PYTHONPATH=$(PYTHONPATH) $(VENV_PYTHON) -m luddite validate-anny-api-experiment \
		--raw-output tests/fixtures/anny_api_experiment/missing_counterpoint_raw.txt

run-anny-api-experiment:
	PYTHONPATH=$(PYTHONPATH) $(VENV_PYTHON) -m luddite run-anny-api-experiment

run-anny-slide-spec-experiment:
	PYTHONPATH=$(PYTHONPATH) $(VENV_PYTHON) -m luddite run-anny-slide-spec-experiment

run-anny-api-experiment-v2:
	PYTHONPATH=$(PYTHONPATH) $(VENV_PYTHON) -m luddite run-anny-api-experiment \
		--run-id anny_api_experiment_ai_knowledge_institution_v2 \
		--timeout 300

run-anny-api-experiment-v3:
	PYTHONPATH=$(PYTHONPATH) $(VENV_PYTHON) -m luddite run-anny-api-experiment \
		--run-id anny_api_experiment_ai_knowledge_institution_v3 \
		--timeout 300

run-anny-api-experiment-v4:
	PYTHONPATH=$(PYTHONPATH) $(VENV_PYTHON) -m luddite run-anny-api-experiment \
		--run-id anny_api_experiment_ai_knowledge_institution_v4 \
		--timeout 300

run-anny-api-experiment-v5:
	PYTHONPATH=$(PYTHONPATH) $(VENV_PYTHON) -m luddite run-anny-api-experiment \
		--run-id anny_api_experiment_ai_knowledge_institution_v5 \
		--timeout 300

run-anny-api-experiment-v6:
	PYTHONPATH=$(PYTHONPATH) $(VENV_PYTHON) -m luddite run-anny-api-experiment \
		--run-id anny_api_experiment_ai_knowledge_institution_v6 \
		--timeout 300

run-anny-api-experiment-v7:
	PYTHONPATH=$(PYTHONPATH) $(VENV_PYTHON) -m luddite run-anny-api-experiment \
		--run-id anny_api_experiment_ai_knowledge_institution_v7 \
		--timeout 300

run-anny-api-experiment-v8:
	PYTHONPATH=$(PYTHONPATH) $(VENV_PYTHON) -m luddite run-anny-api-experiment \
		--run-id anny_api_experiment_ai_knowledge_institution_v8 \
		--timeout 300

run-anny-api-experiment-v9:
	PYTHONPATH=$(PYTHONPATH) $(VENV_PYTHON) -m luddite run-anny-api-experiment \
		--run-id anny_api_experiment_ai_knowledge_institution_v9 \
		--timeout 300

run-anny-api-experiment-finance-v1:
	PYTHONPATH=$(PYTHONPATH) $(VENV_PYTHON) -m luddite run-anny-api-experiment \
		--run-id anny_api_experiment_productive_finance_policy_v1 \
		--case-id anny_api_experiment_productive_finance_policy_v1 \
		--input-bundle outputs/model_dry_runs/anny_storyline/productive_finance_policy_input_bundle.json \
		--evidence-pack data/candidates/anny_evidence_pack_productive_finance_policy.json \
		--manual-storyline outputs/model_dry_runs/anny_storyline/productive_finance_policy_gpt_pro_storyline_enriched.json \
		--manual-case-id anny_dry_run_productive_finance_policy_v1 \
		--comparison-report outputs/reports/anny_api_experiment_productive_finance_policy_v1_comparison.md \
		--report-title "Anny API Experiment Comparison — Productive Finance Policy" \
		--timeout 300

compare-anny-api-experiment-v1-v2:
	PYTHONPATH=$(PYTHONPATH) $(VENV_PYTHON) -m luddite run-anny-api-experiment compare-v1-v2

compare-anny-api-experiment-v1-v2-v3:
	PYTHONPATH=$(PYTHONPATH) $(VENV_PYTHON) -m luddite run-anny-api-experiment compare-v1-v2-v3

compare-anny-api-experiment-v1-v2-v3-v4:
	PYTHONPATH=$(PYTHONPATH) $(VENV_PYTHON) -m luddite run-anny-api-experiment compare-v1-v2-v3-v4

compare-anny-api-experiment-v1-v2-v3-v4-v5:
	PYTHONPATH=$(PYTHONPATH) $(VENV_PYTHON) -m luddite run-anny-api-experiment compare-v1-v2-v3-v4-v5

compare-anny-api-experiment-v1-v2-v3-v4-v5-v6:
	PYTHONPATH=$(PYTHONPATH) $(VENV_PYTHON) -m luddite run-anny-api-experiment compare-v1-v2-v3-v4-v5-v6

compare-anny-api-experiment-v1-v2-v3-v4-v5-v6-v7:
	PYTHONPATH=$(PYTHONPATH) $(VENV_PYTHON) -m luddite run-anny-api-experiment compare-v1-v2-v3-v4-v5-v6-v7

compare-anny-api-experiment-v1-v2-v3-v4-v5-v6-v7-v8:
	PYTHONPATH=$(PYTHONPATH) $(VENV_PYTHON) -m luddite run-anny-api-experiment compare-v1-v2-v3-v4-v5-v6-v7-v8

compare-anny-api-experiment-v1-v2-v3-v4-v5-v6-v7-v8-v9:
	PYTHONPATH=$(PYTHONPATH) $(VENV_PYTHON) -m luddite run-anny-api-experiment compare-v1-v2-v3-v4-v5-v6-v7-v8-v9

review-anny-api-v6-claim-hygiene:
	PYTHONPATH=$(PYTHONPATH) $(VENV_PYTHON) -m luddite run-anny-api-experiment review-v6-claim-hygiene

review-anny-api-finance-v1-claim-hygiene:
	PYTHONPATH=$(PYTHONPATH) $(VENV_PYTHON) -m luddite run-anny-api-experiment review-finance-v1-claim-hygiene

revalidate-anny-api-finance-v1:
	PYTHONPATH=$(PYTHONPATH) $(VENV_PYTHON) -m luddite run-anny-api-experiment revalidate-finance-v1

eval-piti-deck-plan:
	PYTHONPATH=$(PYTHONPATH) $(VENV_PYTHON) -m luddite eval-piti-deck-plan

build-piti-deck-plans:
	PYTHONPATH=$(PYTHONPATH) $(VENV_PYTHON) -m luddite build-piti-deck-plan

build-piti-slide-specs:
	PYTHONPATH=$(PYTHONPATH) $(VENV_PYTHON) -m luddite build-piti-slide-spec

validate-piti-slide-spec:
	PYTHONPATH=$(PYTHONPATH) $(VENV_PYTHON) -m luddite validate-piti-slide-spec

render-piti-storyboards:
	PYTHONPATH=$(PYTHONPATH) $(VENV_PYTHON) -m luddite render-piti-storyboard

render-piti-pptx:
	PYTHONPATH=$(PYTHONPATH) $(VENV_PYTHON) -m luddite render-piti-pptx

render-piti-slide-spec-pptx:
	PYTHONPATH=$(PYTHONPATH) $(VENV_PYTHON) -m luddite render-piti-slide-spec-pptx

render-piti-visual-qa:
	PYTHONPATH=$(PYTHONPATH) $(VENV_PYTHON) -m luddite render-piti-visual-qa

render-pptx-contact-sheet:
	PYTHONPATH=$(PYTHONPATH) $(VENV_PYTHON) -m luddite render-pptx-contact-sheet

summarize-pptx-contact-sheet-review:
	PYTHONPATH=$(PYTHONPATH) $(VENV_PYTHON) -m luddite summarize-pptx-contact-sheet-review

check-pptx-contact-sheet-backend:
	PYTHONPATH=$(PYTHONPATH) $(VENV_PYTHON) -m luddite render-pptx-contact-sheet --check-backend-only

compare-slideability-visual-qa:
	PYTHONPATH=$(PYTHONPATH) $(VENV_PYTHON) -m luddite compare-slideability-visual-qa $(COMPARE_SLIDEABILITY_VISUAL_QA_ARGS)

extract-pptx-style:
	PYTHONPATH=$(PYTHONPATH) $(VENV_PYTHON) -m luddite extract-pptx-style

import-articles:
	PYTHONPATH=$(PYTHONPATH) $(VENV_PYTHON) -m luddite import-articles

fetch-rss-articles:
	PYTHONPATH=$(PYTHONPATH) $(VENV_PYTHON) -m luddite fetch-rss-articles

normalize-candidates:
	PYTHONPATH=$(PYTHONPATH) $(VENV_PYTHON) -m luddite normalize-candidates

score-candidates:
	PYTHONPATH=$(PYTHONPATH) $(VENV_PYTHON) -m luddite score-candidates

cluster-jibi-candidates:
	PYTHONPATH=$(PYTHONPATH) $(VENV_PYTHON) -m luddite cluster-jibi-candidates

build-anny-input-bundles:
	PYTHONPATH=$(PYTHONPATH) $(VENV_PYTHON) -m luddite build-anny-input-bundles

prepare-anny-input-bundles: build-anny-input-bundles

prepare-anny-dry-run:
	PYTHONPATH=$(PYTHONPATH) $(VENV_PYTHON) -m luddite prepare-anny-dry-run

prepare-anny-finance-dry-run:
	PYTHONPATH=$(PYTHONPATH) $(VENV_PYTHON) -m luddite prepare-anny-dry-run \
		--case-id anny_dry_run_productive_finance_policy_v1 \
		--output-bundle outputs/model_dry_runs/anny_storyline/productive_finance_policy_input_bundle.json \
		--expected-storyline outputs/model_dry_runs/anny_storyline/productive_finance_policy_gpt_pro_storyline.json

plan-anny-evidence:
	PYTHONPATH=$(PYTHONPATH) $(VENV_PYTHON) -m luddite plan-anny-evidence

review-anny-fact-check:
	PYTHONPATH=$(PYTHONPATH) $(VENV_PYTHON) -m luddite review-anny-fact-check

compare-anny-dry-runs:
	PYTHONPATH=$(PYTHONPATH) $(VENV_PYTHON) -m luddite compare-anny-dry-runs

compare-anny-enriched-dry-runs:
	PYTHONPATH=$(PYTHONPATH) $(VENV_PYTHON) -m luddite compare-anny-enriched-dry-runs

anny-run-storyline:
	PYTHONPATH=$(PYTHONPATH) $(VENV_PYTHON) -m luddite anny-run-storyline

render-anny-storyline-samples:
	PYTHONPATH=$(PYTHONPATH) $(VENV_PYTHON) -m luddite render-anny-storyline-sample

render-daily-digest:
	PYTHONPATH=$(PYTHONPATH) $(VENV_PYTHON) -m luddite render-daily-digest

jibi-digest:
	PYTHONPATH=$(PYTHONPATH) $(VENV_PYTHON) -m luddite jibi-digest --input-dir examples/articles

jibi-mvp-rss-dry-run:
	PYTHONPATH=$(PYTHONPATH) $(VENV_PYTHON) -m luddite fetch-rss-articles \
		--date $(JIBI_DATE) \
		--output $(JIBI_RSS_INBOX)
	PYTHONPATH=$(PYTHONPATH) $(VENV_PYTHON) -m luddite import-articles --input-file $(JIBI_RSS_INBOX)
	PYTHONPATH=$(PYTHONPATH) $(VENV_PYTHON) -m luddite normalize-candidates
	PYTHONPATH=$(PYTHONPATH) $(VENV_PYTHON) -m luddite score-candidates
	PYTHONPATH=$(PYTHONPATH) $(VENV_PYTHON) -m luddite cluster-jibi-candidates
	PYTHONPATH=$(PYTHONPATH) $(VENV_PYTHON) -m luddite render-daily-digest
	PYTHONPATH=$(PYTHONPATH) $(VENV_PYTHON) -m luddite append-jibi-sheet --dry-run

jibi-manual-update:
	JIBI_DATE=$(JIBI_DATE) JIBI_RSS_INBOX=$(JIBI_RSS_INBOX) \
		VENV_PYTHON=$(VENV_PYTHON) PYTHONPATH=$(PYTHONPATH) \
		./scripts/run_jibi_manual_update.sh

jibi-review-board-dry-run:
	JIBI_SHEET_SCHEMA=bundle_review JIBI_DATE=$(JIBI_DATE) JIBI_RSS_INBOX=$(JIBI_RSS_INBOX) \
		VENV_PYTHON=$(VENV_PYTHON) PYTHONPATH=$(PYTHONPATH) \
		./scripts/run_jibi_manual_update.sh

jibi-review-board-replace:
	JIBI_SHEET_SCHEMA=bundle_review JIBI_APPEND_MODE=staging_replace \
		JIBI_DATE=$(JIBI_DATE) JIBI_RSS_INBOX=$(JIBI_RSS_INBOX) \
		VENV_PYTHON=$(VENV_PYTHON) PYTHONPATH=$(PYTHONPATH) \
		./scripts/run_jibi_manual_update.sh

jibi-review-board-refresh-with-syuka:
	JIBI_SHEET_SCHEMA=bundle_review JIBI_DATE=$(JIBI_DATE) JIBI_RSS_INBOX=$(JIBI_RSS_INBOX) \
		VENV_PYTHON=$(VENV_PYTHON) PYTHONPATH=$(PYTHONPATH) \
		./scripts/run_jibi_manual_update.sh
	PYTHONPATH=$(PYTHONPATH) $(VENV_PYTHON) -m luddite refresh-jibi-review-board-with-syuka \
		--date $(JIBI_DATE) \
		--syuka-data-dir $(JIBI_SYUKA_DATA_DIR) \
		--editorial-overrides $(JIBI_EDITORIAL_OVERRIDES) \
		--sheet-name $(JIBI_SHEET_NAME)

jibi-review-board-replace-with-syuka:
	JIBI_SHEET_SCHEMA=bundle_review JIBI_DATE=$(JIBI_DATE) JIBI_RSS_INBOX=$(JIBI_RSS_INBOX) \
		VENV_PYTHON=$(VENV_PYTHON) PYTHONPATH=$(PYTHONPATH) \
		./scripts/run_jibi_manual_update.sh
	PYTHONPATH=$(PYTHONPATH) $(VENV_PYTHON) -m luddite refresh-jibi-review-board-with-syuka \
		--date $(JIBI_DATE) \
		--syuka-data-dir $(JIBI_SYUKA_DATA_DIR) \
		--editorial-overrides $(JIBI_EDITORIAL_OVERRIDES) \
		--sheet-name $(JIBI_SHEET_NAME) \
		--replace-sheet

jibi-review-board-alternate-dry-run:
	PYTHONPATH=$(PYTHONPATH) $(VENV_PYTHON) -m luddite render-daily-digest \
		--date $(JIBI_DATE) \
		--alternate-review-board-only

jibi-syuka-snapshot-probe:
	PYTHONPATH=$(PYTHONPATH) $(VENV_PYTHON) -m luddite probe-syuka-snapshot \
		--date $(JIBI_DATE) \
		--syuka-data-dir $(JIBI_SYUKA_DATA_DIR)

jibi-source-experiment-guardian:
	PYTHONPATH=$(PYTHONPATH) $(VENV_PYTHON) -m luddite run-jibi-source-experiment \
		--date $(JIBI_DATE) \
		--experiment guardian_sections_v1

jibi-review-feedback:
	PYTHONPATH=$(PYTHONPATH) $(VENV_PYTHON) -m luddite summarize-jibi-review-board \
		--date $(JIBI_DATE)

jibi-second-search-plan:
	PYTHONPATH=$(PYTHONPATH) $(VENV_PYTHON) -m luddite.agents.jibi.second_search_planner \
		--date $(JIBI_DATE)

jibi-second-search-local:
	PYTHONPATH=$(PYTHONPATH) $(VENV_PYTHON) -m luddite.agents.jibi.second_search_runner \
		--date $(JIBI_DATE)

jibi-second-search-web:
	PYTHONPATH=$(PYTHONPATH) $(VENV_PYTHON) -m luddite.agents.jibi.second_search_web \
		--date $(JIBI_DATE) \
		--provider $(JIBI_SEARCH_PROVIDER) \
		--categories $(JIBI_SEARCH_CATEGORIES) \
		--priorities $(JIBI_SEARCH_PRIORITIES) \
		--max-queries $(JIBI_SEARCH_MAX_QUERIES) \
		--results-per-query $(JIBI_SEARCH_RESULTS_PER_QUERY)

jibi-review-feedback-loop: jibi-review-feedback jibi-second-search-plan jibi-second-search-local

jibi-review-history-feedback:
	PYTHONPATH=$(PYTHONPATH) $(VENV_PYTHON) -m luddite summarize-jibi-review-history \
		--date $(JIBI_DATE) \
		--current-csv outputs/daily_digest/$(JIBI_DATE)_bundle_review_sheet.csv

jibi-content-enrichment-review:
	PYTHONPATH=$(PYTHONPATH) $(VENV_PYTHON) -m luddite render-jibi-content-enrichment-review --date $(JIBI_DATE)

append-jibi-sheet:
	PYTHONPATH=$(PYTHONPATH) $(VENV_PYTHON) -m luddite append-jibi-sheet --dry-run

append-jibi-bundle-review-sheet:
	PYTHONPATH=$(PYTHONPATH) $(VENV_PYTHON) -m luddite append-jibi-sheet \
		--preview-csv outputs/daily_digest/$(JIBI_DATE)_bundle_review_sheet.csv \
		--schema bundle_review \
		--replace-existing \
		--dry-run

probe-rss-sources:
	PYTHONPATH=$(PYTHONPATH) $(VENV_PYTHON) -m luddite probe-rss-sources
