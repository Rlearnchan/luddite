# Jibi Evidence-First Report Pipeline

This pipeline keeps Jibi selection unchanged while adding body/evidence/LLM
diagnostics for review.

## Commands

Fetch article bodies into a local gitignored cache:

```bash
make jibi-article-body-fetch JIBI_DATE=2026-06-01 \
  JIBI_ARTICLE_BODY_MAX_ITEMS=0 \
  JIBI_ARTICLE_BODY_FETCH_FLAGS="--llm-summary-fallback --llm-max-items 20"
```

Build the deterministic evidence pack:

```bash
make jibi-evidence-pack JIBI_DATE=2026-06-01
```

Run the report-only LLM judge:

```bash
make jibi-llm-editorial-judge JIBI_DATE=2026-06-01 \
  JIBI_LLM_JUDGE=1 \
  JIBI_LLM_JUDGE_MODEL=gpt-5-mini \
  JIBI_LLM_JUDGE_MAX_ITEMS=10
```

## Outputs

- `data/jibi/article_cache/article_bodies.jsonl`
- `outputs/reports/jibi_article_body_fetch_YYYY-MM-DD.md`
- `outputs/reports/jibi_article_body_fetch_YYYY-MM-DD.json`
- `outputs/reports/jibi_evidence_pack_YYYY-MM-DD.md`
- `outputs/reports/jibi_evidence_pack_YYYY-MM-DD.json`
- `outputs/reports/jibi_llm_editorial_judge_YYYY-MM-DD.md`
- `outputs/reports/jibi_llm_editorial_judge_YYYY-MM-DD.json`

The cache may contain full article body text and stays local/gitignored. Reports
do not print full body text.

## Guardrails

- No Google Sheet replace.
- No Google Drive original edits.
- No syuka-ops DB writes.
- No LLM-driven automatic selection.
- LLM judge is off by default and report-only when enabled.

