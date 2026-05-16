PYTHON ?= /Users/bae/.cache/codex-runtimes/codex-primary-runtime/dependencies/python/bin/python3
VENV ?= .venv
VENV_PYTHON := $(VENV)/bin/python
PYTHONPATH ?= src

.PHONY: setup test lint doctor parse-storylines parse-pptx fetch-sheets manifest

setup:
	$(PYTHON) -m venv $(VENV)
	$(VENV_PYTHON) -m pip install --upgrade pip
	$(VENV_PYTHON) -m pip install -r requirements-dev.txt
	$(VENV_PYTHON) -m pip install -e .

test:
	PYTHONPATH=$(PYTHONPATH) $(VENV_PYTHON) -m pytest

lint:
	$(VENV_PYTHON) -m ruff check .

doctor:
	PYTHONPATH=$(PYTHONPATH) $(VENV_PYTHON) -m luddite doctor

parse-storylines:
	PYTHONPATH=$(PYTHONPATH) $(VENV_PYTHON) -m luddite.parsers.parse_storylines

parse-pptx:
	PYTHONPATH=$(PYTHONPATH) $(VENV_PYTHON) -m luddite.parsers.parse_pptx

fetch-sheets:
	PYTHONPATH=$(PYTHONPATH) $(VENV_PYTHON) -m luddite.parsers.fetch_sheets

manifest:
	PYTHONPATH=$(PYTHONPATH) $(VENV_PYTHON) -m luddite.parsers.build_corpus_manifest
