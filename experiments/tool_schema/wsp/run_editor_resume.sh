#!/usr/bin/env bash
# Resume an in-progress sealed WSP Claude session (same session_id).
set -euo pipefail
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../../.." && pwd)"
cd "$ROOT"
export PATH="${HOME}/.local/bin:${PATH}"

BUDGET="${WSP_BUDGET:-100}"
SESSION_ID="${WSP_SESSION_ID:?set WSP_SESSION_ID}"
RESULTS_DIR="$ROOT/experiments/tool_schema/wsp/results"
EDITOR_DIR="$ROOT/experiments/tool_schema/wsp/editor"
LOG="$RESULTS_DIR/RUNNING_LOG.md"
CLAUDE_LOG="$RESULTS_DIR/claude_editor_${SESSION_ID}.resume.log"
SEAL_DIR="${WSP_SEAL_DIR:-/tmp/wsp_seal}"

# Avoid Claude Code exiting while background shells still run.
export CLAUDE_CODE_PRINT_BG_WAIT_CEILING_MS=0

# shellcheck source=/dev/null
source "$ROOT/scripts/orchestrator/ensure-claude-auth.sh"
# shellcheck source=/dev/null
source "$ROOT/scripts/orchestrator/ensure-claude.sh"

python3 "$ROOT/experiments/tool_schema/wsp/seal_for_run.py" seal --seal-dir "$SEAL_DIR"
export WSP_LOCK_TEST=1
export WSP_SEAL_DIR="$SEAL_DIR"
python3 "$ROOT/experiments/tool_schema/wsp/cli.py" audit

SYSTEM="$(cat "$EDITOR_DIR/SYSTEM.md")"
USED=$(python3 -c "import json;print(json.load(open('artifacts/wsp_sessions/${SESSION_ID}/budget.json'))['used'])")
REMAIN=$((BUDGET - USED))

USER_PROMPT=$(cat <<EOF
# WSP RESUME — session ${SESSION_ID}

Continue the same session. Do **not** create a new session_id.

- Forward budget total: **${BUDGET}**
- Already used: **${USED}** → remaining **${REMAIN}**
- Working weights were restored to the best known edit: \`v_proj\` KV head 1 ×0.55 on layers 16–17 (practice strict_ok 0.475). Confirm with a short forward if needed, then keep searching for something better OR spend remaining budget on robustness / alternate families, then export.

## Hard ops rules for this resume
1. **No background / nohup / parallel harness processes.** Run one Python harness script at a time in the foreground.
2. Reuse \`WSPHarness(forward_budget=${BUDGET}, session_id="${SESSION_ID}")\` always.
3. Use **all remaining** forward passes, then \`export()\`. Do not call eval_edited / BFCL / test.
4. Keep \`experiments/tool_schema/wsp/results/RUNNING_LOG.md\` updated.

Start now.
EOF
)

{
  echo ""
  echo "## Resume started $(date -u +%Y-%m-%dT%H:%M:%SZ)"
  echo "- session_id: \`$SESSION_ID\`"
  echo "- used/remaining: \`$USED / $REMAIN\`"
  echo "- status: **running**"
  echo ""
} >> "$LOG"

set +e
claude -p "$USER_PROMPT" \
  --append-system-prompt "$SYSTEM" \
  --permission-mode bypassPermissions \
  --permission-prompts none \
  --add-dir "$ROOT" \
  2>&1 | tee -a "$CLAUDE_LOG"
exit_code="${PIPESTATUS[0]}"
set -e

echo "=== Unsealing ===" | tee -a "$CLAUDE_LOG"
unset WSP_LOCK_TEST || true
python3 "$ROOT/experiments/tool_schema/wsp/seal_for_run.py" unseal --seal-dir "$SEAL_DIR" || true

SESSION_DIR="$ROOT/artifacts/wsp_sessions/$SESSION_ID"
if [[ -f "$SESSION_DIR/export/edited_state.pt" ]] || [[ -f "$SESSION_DIR/edited_state.pt" ]]; then
  python3 "$ROOT/experiments/tool_schema/wsp/eval_edited.py" \
    --session-dir "$SESSION_DIR" \
    --tag "wsp-p100-resume" \
    --force | tee -a "$CLAUDE_LOG" || true
else
  # Force export if Claude forgot
  python3 - <<PY | tee -a "$CLAUDE_LOG" || true
import sys
sys.path.insert(0,'experiments/tool_schema')
from wsp.harness import WSPHarness
h=WSPHarness(forward_budget=${BUDGET}, session_id='${SESSION_ID}')
print(h.export())
PY
  python3 "$ROOT/experiments/tool_schema/wsp/eval_edited.py" \
    --session-dir "$SESSION_DIR" \
    --tag "wsp-p100-resume" \
    --force | tee -a "$CLAUDE_LOG" || true
fi

{
  echo ""
  echo "## Resume finished $(date -u +%Y-%m-%dT%H:%M:%SZ)"
  echo "- exit_code: \`$exit_code\`"
  echo ""
} >> "$LOG"
exit "$exit_code"
