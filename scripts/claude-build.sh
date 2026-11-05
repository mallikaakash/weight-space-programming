#!/usr/bin/env bash
# Run Claude Code headlessly to implement docs/SPEC.md (or SPEC_PATH).
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"

mkdir -p artifacts .orchestrator

# shellcheck source=orchestrator/ensure-claude-auth.sh
source "${ROOT}/scripts/orchestrator/ensure-claude-auth.sh"

SPEC="${SPEC_PATH:-docs/SPEC.md}"
if [[ ! -f "$SPEC" ]]; then
  echo "Missing spec file: $SPEC" >&2
  exit 1
fi

git rev-parse HEAD > .orchestrator/baseline.sha 2>/dev/null || echo "unknown" > .orchestrator/baseline.sha

# shellcheck source=orchestrator/ensure-claude.sh
source "${ROOT}/scripts/orchestrator/ensure-claude.sh"

LOG="${ROOT}/artifacts/claude-build.log"
SYSTEM="${ROOT}/scripts/orchestrator/prompts/claude-build-system.txt"
USER_TMPL="${ROOT}/scripts/orchestrator/prompts/claude-build-user.txt"

PROMPT_USER="$(SPEC_PATH="$SPEC" ROOT="$ROOT" python3 - <<'PY'
import os
from pathlib import Path
spec = os.environ["SPEC_PATH"]
root = Path(os.environ["ROOT"])
text = (root / "scripts/orchestrator/prompts/claude-build-user.txt").read_text()
print(text.replace("{{SPEC_PATH}}", spec))
PY
)"

echo "=== Claude build started $(date -u +"%Y-%m-%dT%H:%M:%SZ") spec=$SPEC ===" | tee "$LOG"

set +e
claude -p "$PROMPT_USER" \
  --append-system-prompt "$(cat "$SYSTEM")" \
  --permission-mode bypassPermissions \
  --permission-prompts none \
  --add-dir "$ROOT" \
  2>&1 | tee -a "$LOG"
exit_code="${PIPESTATUS[0]}"
set -e

echo "=== Claude build finished exit=$exit_code ===" | tee -a "$LOG"
exit "$exit_code"
