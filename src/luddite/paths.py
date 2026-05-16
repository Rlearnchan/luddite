"""Shared filesystem paths for repo-local tooling."""

from pathlib import Path

PACKAGE_ROOT = Path(__file__).resolve().parent
SRC_ROOT = PACKAGE_ROOT.parent
REPO_ROOT = SRC_ROOT.parent

DATA_DIR = REPO_ROOT / "data"
DOCS_DIR = REPO_ROOT / "docs"
SPECS_DIR = REPO_ROOT / "specs"
PROMPTS_DIR = REPO_ROOT / "prompts"
EVAL_DIR = REPO_ROOT / "eval"

STORYLINE_RAW_DIR = DATA_DIR / "storylines" / "raw"
LATEST_PPT_RAW_DIR = DATA_DIR / "ppt" / "latest" / "raw"
LEGACY_PPT_RAW_DIR = DATA_DIR / "ppt" / "legacy" / "raw"
SHEETS_DIR = DATA_DIR / "sheets"
NOTION_DIR = DATA_DIR / "notion"
MANIFESTS_DIR = DATA_DIR / "manifests"

STORYLINE_PARSED_JSONL = DATA_DIR / "storylines" / "parsed_storylines.jsonl"
PPT_PARSED_JSONL = DATA_DIR / "ppt" / "parsed_latest_ppts.jsonl"
SHEETS_RAW_DIR = SHEETS_DIR / "raw"
SHEETS_PARSED_DIR = SHEETS_DIR / "parsed"
SHEETS_PARSED_JSONL = SHEETS_DIR / "parsed_sheets.jsonl"
CORPUS_MANIFEST_JSONL = MANIFESTS_DIR / "corpus_manifest.jsonl"

OUTPUTS_DIR = REPO_ROOT / "outputs"
REPORTS_DIR = OUTPUTS_DIR / "reports"
PARSER_SMOKE_REPORT = REPORTS_DIR / "parser_smoke_report.md"
