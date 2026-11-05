#!/usr/bin/env bash
# Hand off X-thread rewrite (Aakash lingo) to Claude Code Opus high effort.
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../../.." && pwd)"
cd "$ROOT"

export PATH="${HOME}/.local/bin:${PATH}"
export CLAUDE_CODE_PRINT_BG_WAIT_CEILING_MS="${CLAUDE_CODE_PRINT_BG_WAIT_CEILING_MS:-0}"

SESSION_ID="${WSP_TWEET_SESSION_ID:-wsp-tweet-thread-$(date -u +%Y%m%dT%H%M%SZ)}"
RESULTS_DIR="$ROOT/experiments/tool_schema/wsp/results"
EDITOR_DIR="$ROOT/experiments/tool_schema/wsp/editor"
CLAUDE_LOG="$RESULTS_DIR/claude_tweet_${SESSION_ID}.log"
CLAUDE_MODEL="${WSP_CLAUDE_MODEL:-claude-opus-5-5}"
CLAUDE_EFFORT="${WSP_CLAUDE_EFFORT:-high}"

mkdir -p "$RESULTS_DIR"

# shellcheck source=/dev/null
source "$ROOT/scripts/orchestrator/ensure-claude-auth.sh"
# shellcheck source=/dev/null
source "$ROOT/scripts/orchestrator/ensure-claude.sh"

SYSTEM="$(cat "$EDITOR_DIR/SYSTEM_TWEET_THREAD.md")"
USER_TMPL="$(cat "$EDITOR_DIR/USER_TWEET_THREAD.md")"
USER_PROMPT="${USER_TMPL//\{\{SESSION_ID\}\}/$SESSION_ID}"

{
  echo ""
  echo "## Tweet-thread handoff started $(date -u +%Y-%m-%dT%H:%M:%SZ)"
  echo "- session_id: \`$SESSION_ID\`"
  echo "- editor: \`$CLAUDE_MODEL\` effort=\`$CLAUDE_EFFORT\`"
  echo "- deliverable: \`experiments/tool_schema/wsp/results/TWEET_THREAD_AAKASH.md\`"
  echo ""
} >> "$RESULTS_DIR/CROSSFMT_RUNNING_LOG.md"

echo "=== WSP tweet-thread Claude start session=$SESSION_ID ===" | tee "$CLAUDE_LOG"

set +e
claude -p "$USER_PROMPT" \
  --append-system-prompt "$SYSTEM" \
  --model "$CLAUDE_MODEL" \
  --effort "$CLAUDE_EFFORT" \
  --permission-mode bypassPermissions \
  --permission-prompts none \
  --add-dir "$ROOT" \
  --add-dir /opt/cursor/artifacts/wsp_tweet_charts \
  2>&1 | tee -a "$CLAUDE_LOG"
exit_code="${PIPESTATUS[0]}"
set -e

{
  echo ""
  echo "## Tweet-thread handoff finished $(date -u +%Y-%m-%dT%H:%M:%SZ)"
  echo "- exit_code: \`$exit_code\`"
  echo ""
} >> "$RESULTS_DIR/CROSSFMT_RUNNING_LOG.md"

exit "$exit_code"
