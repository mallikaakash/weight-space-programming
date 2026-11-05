#!/usr/bin/env bash
# Resume an interrupted BFCL-native WSP editor session (same session_id / seal).
# Does NOT rebuild split, baseline, or reseal. Requires an existing sealed run.
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../../.." && pwd)"
cd "$ROOT"

export PATH="${HOME}/.local/bin:${PATH}"

SESSION_ID="${WSP_SESSION_ID:?set WSP_SESSION_ID to the interrupted session}"
BUDGET="${WSP_BUDGET:-100}"
RESULTS_DIR="$ROOT/experiments/tool_schema/wsp/results"
EDITOR_DIR="$ROOT/experiments/tool_schema/wsp/editor"
LOG="$RESULTS_DIR/RUNNING_LOG.md"
CLAUDE_LOG="$RESULTS_DIR/claude_editor_${SESSION_ID}.resume.log"
SEAL_DIR="${WSP_BFCL_SEAL_DIR:-${WSP_SEAL_DIR:-/tmp/wsp_seal}}"
CLAUDE_MODEL="${WSP_CLAUDE_MODEL:-claude-opus-5-5}"
CLAUDE_EFFORT="${WSP_CLAUDE_EFFORT:-high}"

# Avoid Claude Code aborting long metered forwards waiting on background shells.
export CLAUDE_CODE_PRINT_BG_WAIT_CEILING_MS="${CLAUDE_CODE_PRINT_BG_WAIT_CEILING_MS:-0}"

mkdir -p "$RESULTS_DIR" "$ROOT/artifacts/wsp_sessions"

# shellcheck source=/dev/null
source "$ROOT/scripts/orchestrator/ensure-claude-auth.sh"
# shellcheck source=/dev/null
source "$ROOT/scripts/orchestrator/ensure-claude.sh"

if [[ ! -f "$ROOT/artifacts/wsp_sessions/$SESSION_ID/budget.json" ]]; then
  echo "missing session budget: $SESSION_ID" >&2
  exit 1
fi
if [[ ! -f "$SEAL_DIR/test.jsonl" ]]; then
  echo "holdout not sealed at $SEAL_DIR/test.jsonl — refuse resume to avoid leakage" >&2
  exit 1
fi

export WSP_LOCK_TEST=1
export WSP_SEAL_DIR="$SEAL_DIR"
export WSP_SESSION_ID="$SESSION_ID"
export WSP_BUDGET="$BUDGET"

echo "=== Leakage audit (resume) ==="
python3 "$ROOT/experiments/tool_schema/wsp/cli.py" audit

# Restore best known edit (current4) into working_state before Claude continues.
if [[ -f "$ROOT/wsp_work/e_cur4.py" ]]; then
  echo "=== Restore current4 into session working_state ==="
  python3 - <<'PY'
import sys
sys.path.insert(0, "/workspace/experiments/tool_schema")
sys.path.insert(0, "/workspace/wsp_work")
import torch
from wsp.harness import WSPHarness
import os
sid = os.environ["WSP_SESSION_ID"]
budget = int(os.environ.get("WSP_BUDGET", "100"))
h = WSPHarness(forward_budget=budget, session_id=sid)
# apply_current4 reverts then reapplies the kept stack
ns = {"h": h, "torch": torch}
exec(open("/workspace/wsp_work/e_cur4.py").read(), ns)
print("changed:", h.status()["changed_params"][:12], "n=", len(h.status()["changed_params"]))
print("budget", h.status()["forward"])
# Checkpoint export so post-run holdout eval has a candidate even if resume dies again.
out = h.export()
print("exported", out)
PY
fi

SYSTEM="$(cat "$EDITOR_DIR/SYSTEM_BFCL.md")"
USER_TMPL="$(cat "$EDITOR_DIR/USER_BFCL.md")"
USER_PROMPT="${USER_TMPL//\{\{BUDGET\}\}/$BUDGET}"
USER_PROMPT="${USER_PROMPT//\{\{SESSION_ID\}\}/$SESSION_ID}"
USER_PROMPT="$USER_PROMPT

## RESUME
This session was interrupted by Claude Code's background-wait ceiling. Resume the SAME session_id. Budget already partially used — continue until forward_used == ${BUDGET}. Re-apply current4 (family proj down_proj-only L16-31 + bool shear + math proj) if working_state drifted from ablations, then keep searching / confirm / export. Do not open sealed holdout. Prefer fewer huge background waits; poll short or run forwards in the foreground."

{
  echo ""
  echo "## BFCL-native RESUME $(date -u +%Y-%m-%dT%H:%M:%SZ)"
  echo "- session_id: \`$SESSION_ID\`"
  echo "- seal_dir: \`$SEAL_DIR\`"
  echo "- model: \`$CLAUDE_MODEL\` effort=\`$CLAUDE_EFFORT\`"
  echo "- CLAUDE_CODE_PRINT_BG_WAIT_CEILING_MS: \`$CLAUDE_CODE_PRINT_BG_WAIT_CEILING_MS\`"
  echo "- status: **resuming**"
  echo ""
} >> "$LOG"

echo "=== WSP BFCL resume start session=$SESSION_ID ===" | tee "$CLAUDE_LOG"

set +e
claude -p "$USER_PROMPT" \
  --append-system-prompt "$SYSTEM" \
  --model "$CLAUDE_MODEL" \
  --effort "$CLAUDE_EFFORT" \
  --permission-mode bypassPermissions \
  --permission-prompts none \
  --add-dir "$ROOT" \
  2>&1 | tee -a "$CLAUDE_LOG"
exit_code="${PIPESTATUS[0]}"
set -e

SESSION_DIR="$ROOT/artifacts/wsp_sessions/$SESSION_ID"
{
  echo ""
  echo "## BFCL-native resume finished $(date -u +%Y-%m-%dT%H:%M:%SZ)"
  echo "- exit_code: \`$exit_code\`"
  if [[ -f "$SESSION_DIR/budget.json" ]]; then
    python3 -c 'import json,sys; b=json.load(open(sys.argv[1])); print(f"- budget: **{b.get(\"used\")}/{b.get(\"total\")}** used"); print(f"- forward_log_entries: `{len(b.get(\"log\") or [])}`")' \
      "$SESSION_DIR/budget.json" >> "$LOG" || true
  fi
} >> "$LOG"

echo "=== Unsealing BFCL holdout ===" | tee -a "$CLAUDE_LOG"
unset WSP_LOCK_TEST || true
python3 "$ROOT/experiments/tool_schema/wsp/seal_for_run.py" unseal --seal-dir "$SEAL_DIR" \
  | tee -a "$CLAUDE_LOG" || true

EDITED=""
if [[ -f "$SESSION_DIR/export/edited_state.pt" ]]; then
  EDITED="$SESSION_DIR/export/edited_state.pt"
elif [[ -f "$SESSION_DIR/edited_state.pt" ]]; then
  EDITED="$SESSION_DIR/edited_state.pt"
fi

if [[ -n "$EDITED" ]]; then
  echo "=== BFCL holdout EDITED eval (offset=300, limit=100) ===" | tee -a "$CLAUDE_LOG"
  python3 "$ROOT/experiments/tool_schema/bfcl_simple_eval.py" \
    --offset 300 \
    --limit 100 \
    --edited-state "$EDITED" \
    --tag "bfcl-holdout-edited-${SESSION_ID}" \
    | tee -a "$CLAUDE_LOG" || true
else
  echo "No export found; skipping holdout edited eval" | tee -a "$CLAUDE_LOG"
fi

{
  echo "- edited_state: \`${EDITED:-missing}\`"
  echo "- status: **finished** (exit $exit_code)"
  echo ""
} >> "$LOG"

echo "=== WSP BFCL resume finished exit=$exit_code ===" | tee -a "$CLAUDE_LOG"
exit "$exit_code"
