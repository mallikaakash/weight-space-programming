#!/usr/bin/env bash
# Validate Claude Code auth for headless builds (subscription token or API key).
set -euo pipefail

if [[ -n "${CLAUDE_CODE_OAUTH_TOKEN:-}" ]]; then
  return 0 2>/dev/null || exit 0
fi

if [[ -n "${ANTHROPIC_API_KEY:-}" ]]; then
  return 0 2>/dev/null || exit 0
fi

if command -v claude >/dev/null 2>&1; then
  if claude auth status --text 2>/dev/null | grep -qiE 'logged in|authenticated'; then
    return 0 2>/dev/null || exit 0
  fi
  if claude auth status --json 2>/dev/null | python3 -c "
import json, sys
try:
    d = json.load(sys.stdin)
except json.JSONDecodeError:
    sys.exit(1)
# tolerate schema changes — any truthy authenticated flag
for key in ('authenticated', 'isAuthenticated', 'loggedIn'):
    if d.get(key) is True:
        sys.exit(0)
auth = d.get('auth') or d.get('account')
if isinstance(auth, dict) and auth.get('authenticated') is True:
    sys.exit(0)
sys.exit(1)
" 2>/dev/null; then
    return 0 2>/dev/null || exit 0
  fi
fi

cat >&2 <<'EOF'
Claude Code is not authenticated for headless build.

Preferred (Pro / Max subscription):
  1. Run: claude setup-token   (on a machine with a browser)
  2. Copy the token into CLAUDE_CODE_OAUTH_TOKEN
     - Local: repo .env (gitignored)
     - Cloud: Cursor Dashboard → Cloud Agents → secrets

Optional fallback: ANTHROPIC_API_KEY from Anthropic Console (separate API billing).

See docs/ORCHESTRATION.md
EOF
return 1 2>/dev/null || exit 1
