# Luddite

Luddite is a staged corpus and agent project for turning source material into
ShukaWorld-style seed selection, storyline generation, and editable PPT drafts.

This repository currently contains project scaffolding only. Raw PPT and RTF
corpus files are kept local and ignored by git by default.

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
