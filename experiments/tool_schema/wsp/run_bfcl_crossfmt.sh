#!/usr/bin/env bash
# Hand off BFCL cross-format base-vs-edited benchmark to Claude Code (Opus, high thinking).
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../../.." && pwd)"
cd "$ROOT"

export PATH="${HOME}/.local/bin:${PATH}"
export CLAUDE_CODE_PRINT_BG_WAIT_CEILING_MS="${CLAUDE_CODE_PRINT_BG_WAIT_CEILING_MS:-0}"
# Eval-only; do not lock test (we are deliberately scoring many categories)
unset WSP_LOCK_TEST || true

SESSION_ID="${WSP_CROSSFMT_SESSION_ID:-wsp-bfcl-crossfmt-$(date -u +%Y%m%dT%H%M%SZ)}"
RESULTS_DIR="$ROOT/experiments/tool_schema/wsp/results"
EDITOR_DIR="$ROOT/experiments/tool_schema/wsp/editor"
CLAUDE_LOG="$RESULTS_DIR/claude_crossfmt_${SESSION_ID}.log"
CLAUDE_MODEL="${WSP_CLAUDE_MODEL:-claude-opus-5-5}"
CLAUDE_EFFORT="${WSP_CLAUDE_EFFORT:-high}"

mkdir -p "$RESULTS_DIR" "$ROOT/artifacts/wsp_sessions"

# shellcheck source=/dev/null
source "$ROOT/scripts/orchestrator/ensure-claude-auth.sh"
# shellcheck source=/dev/null
source "$ROOT/scripts/orchestrator/ensure-claude.sh"

if [[ ! -d "$ROOT/models/SmolLM2-360M-Instruct" ]]; then
  echo "Model missing; downloading…"
  python3 "$ROOT/experiments/tool_schema/download_model.py"
fi

EDITED="$ROOT/artifacts/wsp_sessions/wsp-bfcl-p100-20261105T143615Z/export/edited_state.pt"
DELTA="$ROOT/artifacts/wsp_sessions/wsp-bfcl-p100-20261105T143615Z/export/current4_delta.pt"
if [[ ! -f "$EDITED" ]]; then
  if [[ -f "$DELTA" ]]; then
    echo "Rebuilding edited_state.pt from delta…"
    python3 "$ROOT/experiments/tool_schema/wsp/pack_edited_delta.py" apply \
      --delta "$DELTA" \
      --model-dir "$ROOT/models/SmolLM2-360M-Instruct" \
      --out "$EDITED"
  else
    echo "Missing edited_state.pt and current4_delta.pt" >&2
    exit 1
  fi
fi

SYSTEM="$(cat "$EDITOR_DIR/SYSTEM_BFCL_CROSSFMT.md")"
USER_TMPL="$(cat "$EDITOR_DIR/USER_BFCL_CROSSFMT.md")"
USER_PROMPT="${USER_TMPL//\{\{SESSION_ID\}\}/$SESSION_ID}"

{
  echo ""
  echo "## BFCL cross-format bench started $(date -u +%Y-%m-%dT%H:%M:%SZ)"
  echo ""
  echo "- session_id: \`$SESSION_ID\`"
  echo "- editor: \`$CLAUDE_MODEL\` effort=\`$CLAUDE_EFFORT\`"
  echo "- edited_state: \`$EDITED\`"
  echo "- categories: simple_python, simple_java, simple_javascript, multiple, parallel, parallel_multiple"
  echo "- status: **running**"
  echo ""
} >> "$RESULTS_DIR/CROSSFMT_RUNNING_LOG.md"

echo "=== WSP BFCL crossfmt Claude start session=$SESSION_ID ===" | tee "$CLAUDE_LOG"

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

{
  echo ""
  echo "## BFCL cross-format bench finished $(date -u +%Y-%m-%dT%H:%M:%SZ)"
  echo "- exit_code: \`$exit_code\`"
  echo ""
} >> "$RESULTS_DIR/CROSSFMT_RUNNING_LOG.md"

echo "=== crossfmt finished exit=$exit_code ===" | tee -a "$CLAUDE_LOG"
exit "$exit_code"
