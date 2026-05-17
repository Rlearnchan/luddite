# Luddite

Luddite is a staged corpus and agent project for turning source material into
ShukaWorld-style seed selection, storyline generation, and editable PPT drafts.

This repository currently contains project scaffolding only. Raw PPT and RTF
corpus files are kept local and ignored by git by default.

## Current Direction

The first usable product target is not automatic PPT production. It is a
research topic selection assistant.

Short-term priorities:

1. `jibi` Daily Digest MVP
2. Google Sheet append
3. Luddite Slack bot
4. `anny` DB-based storyline
5. `syuka-ops` similarity/performance bridge
6. `piti` renderer/PPTX draft

The first demo should be a weekday morning digest of 10 candidate topics. `jibi`
can collect every day even when human research time is constrained by PPT
production. Google Sheet integration targets a dedicated `jibi 후보` staging
sheet, with later human promotion into `주제 찾기`. Slack integration starts as a
dedicated Luddite bot rather than being merged into `syuka-ops`; the syuka-ops
bridge remains a future read-only/search proxy for past videos.

v0.9.3 also documents the source/RSS strategy, keeps BDC as a future
`mode: normal | bdc` design option, and points `anny` toward an
Article -> Candidate -> Cluster -> Story Seed -> Storyline flow.

See `docs/status/current_product_direction.md` for the v0.8/v0.8.1 design
checkpoint summary.

## Setup

```bash
make setup
make test
make doctor
```

`make test` and `make doctor` do not require the private raw corpus. They should
pass on a fresh clone after setup.

## Local Raw Corpus

Raw corpus files are intentionally ignored by git. Place local exports here when
you want to run parser smoke checks:

```text
data/
  storylines/
    raw/
      *.rtf
  ppt/
    latest/
      raw/
        국민도 주주가 되는가_배형찬.pptx
        대혼돈의 영국_김동찬 김성원.pptx
        미중 정상회담_김동찬.pptx
        슈승님의 은혜_김동찬.pptx
        여름에 회사에서 반바지 입어도 되나요_김동찬.pptx
        요즘 뜨는 레이저 치료_김동찬.pptx
        전당포 주식회사_배형찬.pptx
        코카콜라를 이기는 방법_김성원.pptx
  ppt/
    legacy/
      raw/
        *.pptx
  sheets/
    raw/
      *.xlsx 또는 *.csv
```

For the MVP, Google Sheets are handled as local XLSX/CSV exports under
`data/sheets/raw/`. Google Sheets API auth and direct fetching are a v0.2 task.

## Commands

```bash
make setup
make test
make doctor
make doctor-corpus
make parse-storylines
make parse-pptx
make fetch-sheets
make manifest
make corpus-smoke
make validate-golden
make eval-jibi-seeds
make eval-anny-reconstruction
make eval-piti-deck-plan
make import-articles
make normalize-candidates
make score-candidates
make render-daily-digest
make jibi-digest
```

`make doctor-corpus`, `make test-corpus`, and `make corpus-smoke` require local
raw corpus files. `make corpus-smoke` writes:

```text
data/storylines/parsed_storylines.jsonl
data/ppt/parsed_latest_ppts.jsonl
data/sheets/parsed_sheets.jsonl
data/manifests/corpus_manifest.jsonl
outputs/reports/parser_smoke_report.md
```

## jibi Daily Digest MVP

Milestone 0.9 starts with local/manual article input only. It does not call an
LLM, fetch RSS continuously, append to Google Sheets, or post to Slack.

Sample input:

```text
examples/articles/sample_articles.jsonl
```

Local generated outputs:

```text
data/candidates/raw_articles.jsonl
data/candidates/jibi_candidates.jsonl
data/candidates/jibi_scored_candidates.jsonl
outputs/daily_digest/YYYY-MM-DD.md
outputs/daily_digest/YYYY-MM-DD_sheet_append_preview.csv
```

Run the sample pipeline:

```bash
make jibi-digest
```

For real local input, place CSV/JSONL files under `data/inbox/articles/` and run:

```bash
luddite jibi-digest --input-dir data/inbox/articles
```
