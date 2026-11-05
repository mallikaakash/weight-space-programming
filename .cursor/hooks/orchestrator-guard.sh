#!/usr/bin/env bash
# Deny Cursor agent file edits during orchestrator runs (Claude Code implements).
set -euo pipefail

input=$(cat)

if [[ ! -f artifacts/.orchestrator-active ]]; then
  printf '%s\n' '{"permission":"allow"}'
  exit 0
fi

tool=""
if command -v python3 >/dev/null 2>&1; then
  tool=$(printf '%s' "$input" | python3 -c "
import json, sys
try:
    d = json.load(sys.stdin)
except json.JSONDecodeError:
    print('')
    sys.exit(0)
for key in ('tool_name', 'tool', 'toolName', 'name'):
    v = d.get(key)
    if isinstance(v, str) and v:
        print(v)
        break
" 2>/dev/null || true)
fi

case "$tool" in
  Write|Edit|NotebookEdit|ApplyPatch|*Write*|*Edit*)
    printf '%s\n' '{"permission":"deny","agent_message":"Orchestrator mode: implementation is done by Claude Code via scripts/claude-build.sh. Use Shell only; write reports under artifacts/ via redirection."}'
    exit 0
    ;;
esac

printf '%s\n' '{"permission":"allow"}'
exit 0
