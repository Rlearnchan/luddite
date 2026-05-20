# PPTX Contact Sheet Backend Runbook

## Purpose

`luddite render-pptx-contact-sheet` creates a review-only surface for rendered
PPTX drafts. Its goal is to let a human inspect slide thumbnails quickly before
any broadcast workflow is considered.

This tool does not modify PPTX content, rewrite slide meaning, insert images,
generate charts, call an LLM/API, or change production/broadcast readiness.

## Conversion Path

The thumbnail backend has three local prerequisites:

```text
PPTX -> PDF: LibreOffice / soffice
PDF -> PNG: pdftoppm from poppler
PNG -> contact sheet PNG/PDF: Pillow
```

The CLI still produces Markdown QA reports when a backend is missing. Missing
tools are reported as graceful warnings.

## Backend Check

Run:

```bash
PYTHONPATH=src .venv/bin/python -m luddite render-pptx-contact-sheet --check-backend-only
```

or:

```bash
make check-pptx-contact-sheet-backend
```

Expected fields:

```text
LibreOffice: found / missing
pdftoppm: found / missing
Pillow: found / missing
thumbnail_backend_ready: true / false
```

`thumbnail_backend_ready=true` means all three prerequisites are available.

## macOS Setup Examples

LibreOffice can be installed from the official LibreOffice download page or via
Homebrew Cask:

```bash
brew install --cask libreoffice
```

Depending on the install path, `soffice` may not be on `PATH`. Check:

```bash
which soffice
which libreoffice
```

If needed, add LibreOffice's program directory to `PATH`, for example:

```bash
export PATH="/Applications/LibreOffice.app/Contents/MacOS:$PATH"
```

Install Poppler for `pdftoppm`:

```bash
brew install poppler
```

Pillow is a Python dependency used for composing the contact sheet. If it is not
available in the project virtual environment:

```bash
.venv/bin/pip install Pillow
```

These are examples, not a required repo-wide setup policy.

## Windows Notes

Install LibreOffice from the official installer and make sure the `program`
directory containing `soffice.exe` is on `PATH`.

For Poppler, either install a Windows Poppler build and add its `bin` directory
to `PATH`, or run the contact sheet command inside a Docker image that includes
LibreOffice and `poppler-utils`.

## Docker Recommendation

For repeatable rendering, prefer a Docker image with:

```text
libreoffice
poppler-utils
python Pillow
project dependencies
```

The default repo command should still be:

```bash
make render-pptx-contact-sheet
```

## Outputs

Markdown reports:

```text
outputs/qa/pptx_contact_sheet/{deck_id}_contact_sheet.md
outputs/qa/pptx_contact_sheet/pptx_contact_sheet_summary.md
docs/reviews/pptx_contact_sheet_summary.md
```

When the backend is ready, per-deck output directories also contain:

```text
outputs/qa/pptx_contact_sheet/{deck_id}/thumbnails/slide-*.png
outputs/qa/pptx_contact_sheet/{deck_id}/{deck_id}_contact_sheet.png
outputs/qa/pptx_contact_sheet/{deck_id}/{deck_id}_contact_sheet.pdf
```

The PNG/PDF artifacts may be large and do not need to be committed by default.
The GitHub-visible summary in `docs/reviews/` is enough for status review.

## Failure Behavior

If LibreOffice, `pdftoppm`, or Pillow is unavailable:

- the command exits successfully,
- Markdown reports are still generated,
- `thumbnail_backend_ready=false` appears in the summary,
- deck rows include warnings such as `thumbnail_missing`,
- PPTX content is not modified.

## Review Boundary

The contact sheet is a human review surface only. It does not perform OCR,
automatic beauty judgment, AI layout scoring, image insertion, or chart
generation. Broadcast readiness remains false until human review and a separate
handoff workflow exist.
