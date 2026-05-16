# Luddite

Luddite is a staged corpus and agent project for turning source material into
ShukaWorld-style seed selection, storyline generation, and editable PPT drafts.

This repository currently contains project scaffolding only. Raw PPT and RTF
corpus files are kept local and ignored by git by default.

## Setup

```bash
make setup
make doctor
make test
```

## Parser Smoke Commands

```bash
make parse-storylines
make parse-pptx
make fetch-sheets
make manifest
```
