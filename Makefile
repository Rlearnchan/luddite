PYTHON ?= python3
VENV ?= .venv
VENV_PYTHON := $(VENV)/bin/python
PYTHONPATH ?= src

.PHONY: setup test test-corpus lint doctor doctor-corpus parse-storylines parse-pptx fetch-sheets manifest corpus-smoke validate-golden eval-jibi-seeds eval-anny-reconstruction validate-anny-dry-run validate-anny-enriched-dry-run eval-piti-deck-plan import-articles fetch-rss-articles normalize-candidates score-candidates cluster-jibi-candidates build-anny-input-bundles prepare-anny-input-bundles prepare-anny-dry-run prepare-anny-finance-dry-run plan-anny-evidence review-anny-fact-check compare-anny-dry-runs compare-anny-enriched-dry-runs anny-run-storyline render-daily-digest jibi-digest append-jibi-sheet probe-rss-sources

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

eval-piti-deck-plan:
	PYTHONPATH=$(PYTHONPATH) $(VENV_PYTHON) -m luddite eval-piti-deck-plan

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

render-daily-digest:
	PYTHONPATH=$(PYTHONPATH) $(VENV_PYTHON) -m luddite render-daily-digest

jibi-digest:
	PYTHONPATH=$(PYTHONPATH) $(VENV_PYTHON) -m luddite jibi-digest --input-dir examples/articles

append-jibi-sheet:
	PYTHONPATH=$(PYTHONPATH) $(VENV_PYTHON) -m luddite append-jibi-sheet --dry-run

probe-rss-sources:
	PYTHONPATH=$(PYTHONPATH) $(VENV_PYTHON) -m luddite probe-rss-sources
