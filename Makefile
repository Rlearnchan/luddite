PYTHON ?= python3
VENV ?= .venv
VENV_PYTHON := $(VENV)/bin/python
PYTHONPATH ?= src

.PHONY: setup test test-corpus lint doctor doctor-corpus parse-storylines parse-pptx fetch-sheets manifest corpus-smoke validate-golden

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
