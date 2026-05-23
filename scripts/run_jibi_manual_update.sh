#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT_DIR="${JIBI_REPO_ROOT:-$(cd "${SCRIPT_DIR}/.." && pwd)}"
cd "${ROOT_DIR}"

VENV_PYTHON="${VENV_PYTHON:-.venv/bin/python}"
PYTHONPATH="${PYTHONPATH:-src}"
export PYTHONPATH

JIBI_DATE="${JIBI_DATE:-$(date +%F)}"
JIBI_APPEND_MODE="${JIBI_APPEND_MODE:-dry_run}"
LUDDITE_GOOGLE_TARGET_SHEET="${LUDDITE_GOOGLE_TARGET_SHEET:-jibi 후보}"
export LUDDITE_GOOGLE_TARGET_SHEET

LOCK_DIR="${JIBI_LOCK_DIR:-/tmp/luddite-jibi-manual-update.lock}"
LOG_DIR="${JIBI_LOG_DIR:-${HOME}/Library/Logs/luddite}"
LOG_FILE="${LOG_DIR}/jibi_manual_${JIBI_DATE}.log"
ERR_FILE="${LOG_DIR}/jibi_manual_${JIBI_DATE}.err.log"
RSS_INBOX="${JIBI_RSS_INBOX:-data/inbox/articles/rss_${JIBI_DATE}.jsonl}"
PREVIEW_CSV="outputs/daily_digest/${JIBI_DATE}_sheet_append_preview.csv"
DAILY_DIGEST="outputs/daily_digest/${JIBI_DATE}.md"
QUALITY_REPORT="outputs/reports/jibi_quality_${JIBI_DATE}.md"
CONTENT_ENRICHMENT_REPORT="outputs/reports/jibi_content_enrichment_${JIBI_DATE}.md"
CONTENT_ENRICHMENT_JSON="outputs/reports/jibi_content_enrichment_${JIBI_DATE}.json"
SHEET_APPEND_REPORT="outputs/reports/jibi_sheet_append_${JIBI_DATE}.md"
MANUAL_SUMMARY_MD="outputs/reports/jibi_manual_update_${JIBI_DATE}.md"
MANUAL_SUMMARY_JSON="outputs/reports/jibi_manual_update_${JIBI_DATE}.json"
CONTENT_ENRICHMENT_STATUS="not_run"
APPEND_STATUS="not_run"
SUMMARY_WRITTEN=0
LOCK_HELD=0

mkdir -p "${LOG_DIR}"
if [[ "${JIBI_DISABLE_LOG_TEE:-0}" != "1" ]]; then
  exec > >(tee -a "${LOG_FILE}") 2> >(tee -a "${ERR_FILE}" >&2)
fi

write_summary() {
  local command_status="$1"
  "${VENV_PYTHON}" -m luddite jibi-manual-run-summary \
    --date "${JIBI_DATE}" \
    --append-mode "${JIBI_APPEND_MODE}" \
    --target-sheet "${LUDDITE_GOOGLE_TARGET_SHEET}" \
    --rss-inbox "${RSS_INBOX}" \
    --preview-csv "${PREVIEW_CSV}" \
    --daily-digest "${DAILY_DIGEST}" \
    --quality-report "${QUALITY_REPORT}" \
    --content-enrichment-report "${CONTENT_ENRICHMENT_REPORT}" \
    --content-enrichment-json "${CONTENT_ENRICHMENT_JSON}" \
    --sheet-append-report "${SHEET_APPEND_REPORT}" \
    --summary-md "${MANUAL_SUMMARY_MD}" \
    --summary-json "${MANUAL_SUMMARY_JSON}" \
    --content-enrichment-status "${CONTENT_ENRICHMENT_STATUS}" \
    --append-status "${APPEND_STATUS}" \
    --command-status "${command_status}" \
    --log-file "${LOG_FILE}" \
    --err-log-file "${ERR_FILE}"
  SUMMARY_WRITTEN=1
}

cleanup() {
  local status=$?
  if [[ "${SUMMARY_WRITTEN}" != "1" ]]; then
    write_summary "failed_${status}" || true
  fi
  if [[ "${LOCK_HELD}" == "1" ]]; then
    rmdir "${LOCK_DIR}" 2>/dev/null || true
  fi
  exit "${status}"
}
trap cleanup EXIT

if ! mkdir "${LOCK_DIR}" 2>/dev/null; then
  echo "Another Jibi manual update is already running: ${LOCK_DIR}" >&2
  exit 42
fi
LOCK_HELD=1

if [[ ! -x "${VENV_PYTHON}" ]]; then
  echo "Python runtime is not executable: ${VENV_PYTHON}" >&2
  exit 1
fi

echo "== Jibi manual update =="
echo "date=${JIBI_DATE}"
echo "append_mode=${JIBI_APPEND_MODE}"
echo "target_sheet=${LUDDITE_GOOGLE_TARGET_SHEET}"
echo "rss_inbox=${RSS_INBOX}"
echo "preview_csv=${PREVIEW_CSV}"
echo "log=${LOG_FILE}"
echo "err_log=${ERR_FILE}"

"${VENV_PYTHON}" -m luddite jibi-ops-guard \
  --append-mode "${JIBI_APPEND_MODE}" \
  --target-sheet "${LUDDITE_GOOGLE_TARGET_SHEET}"

"${VENV_PYTHON}" -m luddite fetch-rss-articles \
  --date "${JIBI_DATE}" \
  --output "${RSS_INBOX}"
"${VENV_PYTHON}" -m luddite import-articles --input-file "${RSS_INBOX}"
"${VENV_PYTHON}" -m luddite normalize-candidates
"${VENV_PYTHON}" -m luddite score-candidates
"${VENV_PYTHON}" -m luddite cluster-jibi-candidates
"${VENV_PYTHON}" -m luddite render-daily-digest

if [[ ! -f "${PREVIEW_CSV}" ]]; then
  echo "Missing date-specific sheet preview CSV: ${PREVIEW_CSV}" >&2
  exit 1
fi
echo "Using date-specific preview CSV: ${PREVIEW_CSV}"

if ! "${VENV_PYTHON}" -m luddite render-jibi-content-enrichment-review \
  --date "${JIBI_DATE}"; then
  echo "WARN: content enrichment review failed; continuing because it is diagnostic only." >&2
  CONTENT_ENRICHMENT_STATUS="failed"
else
  CONTENT_ENRICHMENT_STATUS="succeeded"
fi

case "${JIBI_APPEND_MODE}" in
  dry_run)
    "${VENV_PYTHON}" -m luddite append-jibi-sheet \
      --preview-csv "${PREVIEW_CSV}" \
      --dry-run \
      --sheet-name "${LUDDITE_GOOGLE_TARGET_SHEET}"
    APPEND_STATUS="dry_run_completed"
    ;;
  staging_append)
    "${VENV_PYTHON}" -m luddite append-jibi-sheet \
      --preview-csv "${PREVIEW_CSV}" \
      --no-dry-run \
      --sheet-name "${LUDDITE_GOOGLE_TARGET_SHEET}"
    APPEND_STATUS="staging_append_completed"
    ;;
  *)
    echo "Invalid JIBI_APPEND_MODE after guard: ${JIBI_APPEND_MODE}" >&2
    exit 1
    ;;
esac

write_summary "success"

echo "== Jibi manual update complete =="
echo "Daily digest: ${DAILY_DIGEST}"
echo "Preview CSV: ${PREVIEW_CSV}"
echo "Sheet append report: ${SHEET_APPEND_REPORT}"
echo "Content enrichment report: ${CONTENT_ENRICHMENT_REPORT}"
echo "Manual update summary: ${MANUAL_SUMMARY_MD}"
