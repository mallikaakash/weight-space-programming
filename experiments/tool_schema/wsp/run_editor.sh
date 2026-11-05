#!/usr/bin/env bash
# Launch Claude Code as the WSP weight editor.
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../../.." && pwd)"
cd "$ROOT"

export PATH="${HOME}/.local/bin:${PATH}"

BUDGET="${WSP_BUDGET:-15}"
SESSION_ID="${WSP_SESSION_ID:-wsp-$(date -u +%Y%m%dT%H%M%SZ)}"
RESULTS_DIR="$ROOT/experiments/tool_schema/wsp/results"
EDITOR_DIR="$ROOT/experiments/tool_schema/wsp/editor"
LOG="$RESULTS_DIR/RUNNING_LOG.md"
CLAUDE_LOG="$RESULTS_DIR/claude_editor_${SESSION_ID}.log"

mkdir -p "$RESULTS_DIR" "$ROOT/artifacts/wsp_sessions"

# Auth (same as claude-build.sh)
# shellcheck source=/dev/null
source "$ROOT/scripts/orchestrator/ensure-claude-auth.sh"
# shellcheck source=/dev/null
source "$ROOT/scripts/orchestrator/ensure-claude.sh"

if [[ ! -d "$ROOT/models/SmolLM2-360M-Instruct" ]]; then
  echo "Model missing; downloading…"
  python3 "$ROOT/experiments/tool_schema/download_model.py"
fi

SYSTEM="$(cat "$EDITOR_DIR/SYSTEM.md")"
USER_TMPL="$(cat "$EDITOR_DIR/USER.md")"
USER_PROMPT="${USER_TMPL//\{\{BUDGET\}\}/$BUDGET}"
USER_PROMPT="${USER_PROMPT//\{\{SESSION_ID\}\}/$SESSION_ID}"

{
  echo ""
  echo "## Run started $(date -u +%Y-%m-%dT%H:%M:%SZ)"
  echo ""
  echo "- session_id: \`$SESSION_ID\`"
  echo "- budget: \`$BUDGET\`"
  echo "- claude_log: \`$CLAUDE_LOG\`"
  echo "- status: **running**"
  echo ""
} >> "$LOG"

echo "=== WSP editor start session=$SESSION_ID budget=$BUDGET ===" | tee "$CLAUDE_LOG"

set +e
claude -p "$USER_PROMPT" \
  --append-system-prompt "$SYSTEM" \
  --permission-mode bypassPermissions \
  --permission-prompts none \
  --add-dir "$ROOT" \
  2>&1 | tee -a "$CLAUDE_LOG"
exit_code="${PIPESTATUS[0]}"
set -e

{
  echo ""
  echo "## Run finished $(date -u +%Y-%m-%dT%H:%M:%SZ)"
  echo ""
  echo "- exit_code: \`$exit_code\`"
  if [[ -f "$RESULTS_DIR/edited_test_latest.summary.json" ]]; then
    echo "- edited summary present: \`edited_test_latest.summary.json\`"
  else
    echo "- edited summary: _not written yet_"
  fi
  echo "- status: **finished** (exit $exit_code)"
  echo ""
} >> "$LOG"

echo "=== WSP editor finished exit=$exit_code ===" | tee -a "$CLAUDE_LOG"
exit "$exit_code"
