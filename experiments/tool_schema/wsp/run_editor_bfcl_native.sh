#!/usr/bin/env bash
# BFCL-native WSP: 100 forwards on BFCL train (300), holdout eval on remaining 100.
# Editor: Claude Opus 5.5 with high thinking effort.
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../../.." && pwd)"
cd "$ROOT"

export PATH="${HOME}/.local/bin:${PATH}"

BUDGET="${WSP_BUDGET:-100}"
SESSION_ID="${WSP_SESSION_ID:-wsp-bfcl-p100-$(date -u +%Y%m%dT%H%M%SZ)}"
RESULTS_DIR="$ROOT/experiments/tool_schema/wsp/results"
EDITOR_DIR="$ROOT/experiments/tool_schema/wsp/editor"
LOG="$RESULTS_DIR/RUNNING_LOG.md"
CLAUDE_LOG="$RESULTS_DIR/claude_editor_${SESSION_ID}.log"
# Always use a BFCL-specific seal dir (ignore inherited WSP_SEAL_DIR from older runs).
SEAL_DIR="${WSP_BFCL_SEAL_DIR:-/tmp/wsp_seal_bfcl}"
CLAUDE_MODEL="${WSP_CLAUDE_MODEL:-claude-opus-5-5}"
CLAUDE_EFFORT="${WSP_CLAUDE_EFFORT:-high}"
# Avoid Claude Code aborting long metered forwards waiting on background shells.
export CLAUDE_CODE_PRINT_BG_WAIT_CEILING_MS="${CLAUDE_CODE_PRINT_BG_WAIT_CEILING_MS:-0}"
# Ensure lock is on for this process tree before any child can race.
export WSP_LOCK_TEST=0  # flipped to 1 after seal below

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

echo "=== Build BFCL train/test split (300/100) ==="
python3 "$ROOT/experiments/tool_schema/wsp/build_bfcl_split.py"

# Baseline BEFORE seal (holdout ids 300:400). Write ONLY under
# experiments/tool_schema/results/bfcl/ — seal_for_run quarantines that tree so
# the editor cannot see holdout numbers mid-run. Do NOT tee into wsp/results.
echo "=== BFCL holdout BASELINE on base model (offset=300, limit=100) ==="
mkdir -p "$RESULTS_DIR"
BASELINE_LOG="$ROOT/experiments/tool_schema/results/bfcl/baseline_${SESSION_ID}.log"
mkdir -p "$(dirname "$BASELINE_LOG")"
python3 "$ROOT/experiments/tool_schema/bfcl_simple_eval.py" \
  --offset 300 \
  --limit 100 \
  --tag "bfcl-holdout-base-pre-${SESSION_ID}" \
  > "$BASELINE_LOG" 2>&1
echo "Baseline logged to $BASELINE_LOG (will be sealed)"

echo "=== Sealing BFCL holdout → $SEAL_DIR ==="
# Fresh seal dir for BFCL-native (do not mix with prior tool-schema seals)
rm -rf "$SEAL_DIR"
python3 "$ROOT/experiments/tool_schema/wsp/seal_for_run.py" seal --seal-dir "$SEAL_DIR"
export WSP_LOCK_TEST=1
export WSP_SEAL_DIR="$SEAL_DIR"
# Re-export into a file Claude/tool shells can source if needed
printf 'export WSP_LOCK_TEST=1\nexport WSP_SEAL_DIR=%q\n' "$SEAL_DIR" > "$RESULTS_DIR/wsp_lock.env"

echo "=== Leakage audit ==="
python3 "$ROOT/experiments/tool_schema/wsp/cli.py" audit
AUDIT_OK=$?
if [[ "$AUDIT_OK" -ne 0 ]]; then
  echo "Audit failed; unsealing and aborting" >&2
  python3 "$ROOT/experiments/tool_schema/wsp/seal_for_run.py" unseal --seal-dir "$SEAL_DIR" || true
  unset WSP_LOCK_TEST
  exit 1
fi

SYSTEM="$(cat "$EDITOR_DIR/SYSTEM_BFCL.md")"
USER_TMPL="$(cat "$EDITOR_DIR/USER_BFCL.md")"
USER_PROMPT="${USER_TMPL//\{\{BUDGET\}\}/$BUDGET}"
USER_PROMPT="${USER_PROMPT//\{\{SESSION_ID\}\}/$SESSION_ID}"

{
  echo ""
  echo "## BFCL-native WSP run started $(date -u +%Y-%m-%dT%H:%M:%SZ)"
  echo ""
  echo "- session_id: \`$SESSION_ID\`"
  echo "- budget: \`$BUDGET\`"
  echo "- practice: BFCL simple_python train **300**"
  echo "- holdout: BFCL simple_python test **100** (sealed)"
  echo "- metric: official AST (\`strict_ok\`)"
  echo "- editor model: \`$CLAUDE_MODEL\` effort=\`$CLAUDE_EFFORT\`"
  echo "- seal_dir: \`$SEAL_DIR\`"
  echo "- WSP_LOCK_TEST: \`1\`"
  echo "- claude_log: \`$CLAUDE_LOG\`"
  echo "- status: **running**"
  echo ""
} >> "$LOG"

printf '{"session_id":"%s","session_dir":"%s/artifacts/wsp_sessions/%s","task":"bfcl_simple_python"}\n' \
  "$SESSION_ID" "$ROOT" "$SESSION_ID" \
  > "$ROOT/artifacts/wsp_sessions/latest.json"

echo "=== WSP BFCL editor start session=$SESSION_ID budget=$BUDGET model=$CLAUDE_MODEL effort=$CLAUDE_EFFORT ===" \
  | tee "$CLAUDE_LOG"

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
  echo "## BFCL-native run finished $(date -u +%Y-%m-%dT%H:%M:%SZ)"
  echo ""
  echo "- exit_code: \`$exit_code\`"
  if [[ -f "$SESSION_DIR/budget.json" ]]; then
    python3 -c 'import json,sys; b=json.load(open(sys.argv[1])); print("- budget: **{}/{}** used".format(b.get("used"), b.get("total"))); print("- forward_log_entries: `{}`".format(len(b.get("log") or [])))' \
      "$SESSION_DIR/budget.json" || true
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

echo "=== WSP BFCL-native finished exit=$exit_code ===" | tee -a "$CLAUDE_LOG"
exit "$exit_code"
