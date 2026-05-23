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

mkdir -p "${LOG_DIR}"
exec > >(tee -a "${LOG_FILE}") 2> >(tee -a "${ERR_FILE}" >&2)

cleanup() {
  rmdir "${LOCK_DIR}" 2>/dev/null || true
}
trap cleanup EXIT

if ! mkdir "${LOCK_DIR}" 2>/dev/null; then
  echo "Another Jibi manual update is already running: ${LOCK_DIR}" >&2
  exit 42
fi

if [[ ! -x "${VENV_PYTHON}" ]]; then
  echo "Python runtime is not executable: ${VENV_PYTHON}" >&2
  exit 1
fi

echo "== Jibi manual update =="
echo "date=${JIBI_DATE}"
echo "append_mode=${JIBI_APPEND_MODE}"
echo "target_sheet=${LUDDITE_GOOGLE_TARGET_SHEET}"
echo "rss_inbox=${RSS_INBOX}"
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

if ! "${VENV_PYTHON}" -m luddite render-jibi-content-enrichment-review \
  --date "${JIBI_DATE}"; then
  echo "WARN: content enrichment review failed; continuing because it is diagnostic only." >&2
fi

case "${JIBI_APPEND_MODE}" in
  dry_run)
    "${VENV_PYTHON}" -m luddite append-jibi-sheet \
      --dry-run \
      --sheet-name "${LUDDITE_GOOGLE_TARGET_SHEET}"
    ;;
  staging_append)
    "${VENV_PYTHON}" -m luddite append-jibi-sheet \
      --no-dry-run \
      --sheet-name "${LUDDITE_GOOGLE_TARGET_SHEET}"
    ;;
  *)
    echo "Invalid JIBI_APPEND_MODE after guard: ${JIBI_APPEND_MODE}" >&2
    exit 1
    ;;
esac

echo "== Jibi manual update complete =="
echo "Daily digest: outputs/daily_digest/${JIBI_DATE}.md"
echo "Sheet append report: outputs/reports/jibi_sheet_append_${JIBI_DATE}.md"
echo "Content enrichment report: outputs/reports/jibi_content_enrichment_${JIBI_DATE}.md"
