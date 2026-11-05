#!/usr/bin/env bash
# Launch Claude Code as the WSP weight editor for an exp8/p50c-style long run.
# Seals test material outside the workspace, locks eval, requires full budget use.
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../../.." && pwd)"
cd "$ROOT"

export PATH="${HOME}/.local/bin:${PATH}"

BUDGET="${WSP_BUDGET:-50}"
SESSION_ID="${WSP_SESSION_ID:-wsp-p50-$(date -u +%Y%m%dT%H%M%SZ)}"
RESULTS_DIR="$ROOT/experiments/tool_schema/wsp/results"
EDITOR_DIR="$ROOT/experiments/tool_schema/wsp/editor"
LOG="$RESULTS_DIR/RUNNING_LOG.md"
CLAUDE_LOG="$RESULTS_DIR/claude_editor_${SESSION_ID}.log"
SEAL_DIR="${WSP_SEAL_DIR:-/tmp/wsp_seal}"

mkdir -p "$RESULTS_DIR" "$ROOT/artifacts/wsp_sessions"

# Auth
# shellcheck source=/dev/null
source "$ROOT/scripts/orchestrator/ensure-claude-auth.sh"
# shellcheck source=/dev/null
source "$ROOT/scripts/orchestrator/ensure-claude.sh"

if [[ ! -d "$ROOT/models/SmolLM2-360M-Instruct" ]]; then
  echo "Model missing; downloading…"
  python3 "$ROOT/experiments/tool_schema/download_model.py"
fi

# Ensure sealed practice exists
if [[ ! -f "$ROOT/experiments/tool_schema/wsp/practice/train.jsonl" ]]; then
  echo "practice/train.jsonl missing" >&2
  exit 1
fi

echo "=== Sealing holdout test material → $SEAL_DIR ==="
python3 "$ROOT/experiments/tool_schema/wsp/seal_for_run.py" seal --seal-dir "$SEAL_DIR"
export WSP_LOCK_TEST=1
export WSP_SEAL_DIR="$SEAL_DIR"

echo "=== Leakage audit ==="
python3 "$ROOT/experiments/tool_schema/wsp/cli.py" audit
AUDIT_OK=$?
if [[ "$AUDIT_OK" -ne 0 ]]; then
  echo "Audit failed; unsealing and aborting" >&2
  python3 "$ROOT/experiments/tool_schema/wsp/seal_for_run.py" unseal --seal-dir "$SEAL_DIR" || true
  unset WSP_LOCK_TEST
  exit 1
fi

SYSTEM="$(cat "$EDITOR_DIR/SYSTEM.md")"
USER_TMPL="$(cat "$EDITOR_DIR/USER.md")"
USER_PROMPT="${USER_TMPL//\{\{BUDGET\}\}/$BUDGET}"
USER_PROMPT="${USER_PROMPT//\{\{SESSION_ID\}\}/$SESSION_ID}"

{
  echo ""
  echo "## Long run (exp8/p50) started $(date -u +%Y-%m-%dT%H:%M:%SZ)"
  echo ""
  echo "- session_id: \`$SESSION_ID\`"
  echo "- budget: \`$BUDGET\`"
  echo "- protocol: exp8-aligned (generate|inspect, which=both, use-all-budget)"
  echo "- seal_dir: \`$SEAL_DIR\`"
  echo "- WSP_LOCK_TEST: \`1\`"
  echo "- claude_log: \`$CLAUDE_LOG\`"
  echo "- status: **running**"
  echo ""
} >> "$LOG"

# Pointer for resume
printf '{"session_id":"%s","session_dir":"%s/artifacts/wsp_sessions/%s"}\n' \
  "$SESSION_ID" "$ROOT" "$SESSION_ID" \
  > "$ROOT/artifacts/wsp_sessions/latest.json"

echo "=== WSP long editor start session=$SESSION_ID budget=$BUDGET ===" | tee "$CLAUDE_LOG"

set +e
claude -p "$USER_PROMPT" \
  --append-system-prompt "$SYSTEM" \
  --permission-mode bypassPermissions \
  --permission-prompts none \
  --add-dir "$ROOT" \
  2>&1 | tee -a "$CLAUDE_LOG"
exit_code="${PIPESTATUS[0]}"
set -e

SESSION_DIR="$ROOT/artifacts/wsp_sessions/$SESSION_ID"
{
  echo ""
  echo "## Long run finished $(date -u +%Y-%m-%dT%H:%M:%SZ)"
  echo ""
  echo "- exit_code: \`$exit_code\`"
  if [[ -f "$SESSION_DIR/budget.json" ]]; then
    echo "- budget.json:"
    echo '```'
    python3 -c "import json,sys;print(json.dumps(json.load(open(sys.argv[1])),indent=2)[:2000])" \
      "$SESSION_DIR/budget.json" 2>/dev/null || true
    echo '```'
  fi
} >> "$LOG"

echo "=== Unsealing holdout ===" | tee -a "$CLAUDE_LOG"
unset WSP_LOCK_TEST || true
python3 "$ROOT/experiments/tool_schema/wsp/seal_for_run.py" unseal --seal-dir "$SEAL_DIR" \
  | tee -a "$CLAUDE_LOG" || true

if [[ -f "$SESSION_DIR/export/edited_state.pt" ]] || [[ -f "$SESSION_DIR/edited_state.pt" ]]; then
  echo "=== Post-run sealed test eval ===" | tee -a "$CLAUDE_LOG"
  python3 "$ROOT/experiments/tool_schema/wsp/eval_edited.py" \
    --session-dir "$SESSION_DIR" \
    --tag "wsp-p50-${SESSION_ID}" \
    --force \
    | tee -a "$CLAUDE_LOG" || true
else
  echo "No export found; skipping eval_edited" | tee -a "$CLAUDE_LOG"
fi

{
  if [[ -f "$RESULTS_DIR/edited_test_latest.summary.json" ]]; then
    echo "- edited summary: \`edited_test_latest.summary.json\`"
  else
    echo "- edited summary: _not written_"
  fi
  echo "- status: **finished** (exit $exit_code)"
  echo ""
} >> "$LOG"

echo "=== WSP long editor finished exit=$exit_code ===" | tee -a "$CLAUDE_LOG"
exit "$exit_code"
