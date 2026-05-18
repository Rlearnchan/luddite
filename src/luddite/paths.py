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
CONFIG_DIR = REPO_ROOT / "config"
EXAMPLES_DIR = REPO_ROOT / "examples"

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

SOURCE_REGISTRY_YAML = CONFIG_DIR / "sources.yaml"
GOOGLE_SHEETS_EXAMPLE_CONFIG_YAML = CONFIG_DIR / "google_sheets.example.yaml"
GOOGLE_SHEETS_LOCAL_CONFIG_YAML = CONFIG_DIR / "google_sheets.local.yaml"
ARTICLE_INBOX_DIR = DATA_DIR / "inbox" / "articles"
CANDIDATES_DIR = DATA_DIR / "candidates"
RAW_ARTICLES_JSONL = CANDIDATES_DIR / "raw_articles.jsonl"
JIBI_CANDIDATES_JSONL = CANDIDATES_DIR / "jibi_candidates.jsonl"
JIBI_SCORED_CANDIDATES_JSONL = CANDIDATES_DIR / "jibi_scored_candidates.jsonl"
JIBI_CANDIDATE_CLUSTERS_JSONL = CANDIDATES_DIR / "jibi_candidate_clusters.jsonl"
ANNY_STORY_SEED_HANDOFF_JSONL = CANDIDATES_DIR / "anny_story_seed_handoff.jsonl"
ANNY_INPUT_BUNDLES_JSONL = CANDIDATES_DIR / "anny_input_bundles.jsonl"
ANNY_EVIDENCE_PACK_AI_KNOWLEDGE_JSON = (
    CANDIDATES_DIR / "anny_evidence_pack_ai_knowledge_institution.json"
)

OUTPUTS_DIR = REPO_ROOT / "outputs"
REPORTS_DIR = OUTPUTS_DIR / "reports"
DAILY_DIGEST_DIR = OUTPUTS_DIR / "daily_digest"
MODEL_DRY_RUNS_DIR = OUTPUTS_DIR / "model_dry_runs"
ANNY_STORYLINE_DRY_RUN_DIR = MODEL_DRY_RUNS_DIR / "anny_storyline"
PARSER_SMOKE_REPORT = REPORTS_DIR / "parser_smoke_report.md"
PARSER_SMOKE_NOTES = REPORTS_DIR / "parser_smoke_notes.md"
