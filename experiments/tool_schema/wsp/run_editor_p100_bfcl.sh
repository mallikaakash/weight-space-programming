#!/usr/bin/env bash
# Larger WSP run (budget 100) + post-run official BFCL simple_python AST eval.
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../../.." && pwd)"
cd "$ROOT"

export PATH="${HOME}/.local/bin:${PATH}"
export WSP_BUDGET="${WSP_BUDGET:-100}"
export WSP_SESSION_ID="${WSP_SESSION_ID:-wsp-p100-$(date -u +%Y%m%dT%H%M%SZ)}"
BFCL_LIMIT="${BFCL_LIMIT:-100}"  # official subset size for CPU (full=400)
SEAL_DIR="${WSP_SEAL_DIR:-/tmp/wsp_seal}"
RESULTS="$ROOT/experiments/tool_schema/wsp/results"
LOG="$RESULTS/RUNNING_LOG.md"

mkdir -p "$RESULTS"

{
  echo ""
  echo "## Larger run plan (p100 + BFCL) $(date -u +%Y-%m-%dT%H:%M:%SZ)"
  echo ""
  echo "- session: \`$WSP_SESSION_ID\`"
  echo "- budget: \`$WSP_BUDGET\`"
  echo "- practice: sealed tool-schema train (40) — same as p50"
  echo "- official holdout probe: BFCL v4 \`simple_python\` AST, limit=\`$BFCL_LIMIT\` (orchestrator-only)"
  echo "- honesty: not full BFCL leaderboard; transfer probe from our JSON schema practice"
  echo ""
} >> "$LOG"

# Baseline BFCL on base model (before edits)
echo "=== BFCL base baseline (limit=$BFCL_LIMIT) ==="
python3 "$ROOT/experiments/tool_schema/bfcl_simple_eval.py" \
  --limit "$BFCL_LIMIT" \
  --tag "bfcl-base-pre-p100"

# Editor long run (seal + Claude + unseal + our test eval)
bash "$ROOT/experiments/tool_schema/wsp/run_editor_long.sh"
exit_code=$?

SESSION_DIR="$ROOT/artifacts/wsp_sessions/$WSP_SESSION_ID"
EDITED="$SESSION_DIR/export/edited_state.pt"
if [[ ! -f "$EDITED" ]]; then
  EDITED="$SESSION_DIR/edited_state.pt"
fi

if [[ -f "$EDITED" ]]; then
  echo "=== BFCL edited eval (limit=$BFCL_LIMIT) ==="
  python3 "$ROOT/experiments/tool_schema/bfcl_simple_eval.py" \
    --limit "$BFCL_LIMIT" \
    --edited-state "$EDITED" \
    --tag "bfcl-edited-p100"
else
  echo "No edited state; skip BFCL edited eval" >&2
fi

{
  echo ""
  echo "## p100+BFCL wrapper finished $(date -u +%Y-%m-%dT%H:%M:%SZ)"
  echo "- editor_exit: \`$exit_code\`"
  echo "- BFCL summaries under \`experiments/tool_schema/results/bfcl/\`"
  echo ""
} >> "$LOG"

exit "$exit_code"
