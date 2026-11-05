#!/usr/bin/env bash
# Ensure Claude Code CLI is on PATH (cloud VM or fresh machine).
# Prefer user npm prefix when global /usr install is not writable (common on cloud images).
if command -v claude >/dev/null 2>&1; then
  return 0 2>/dev/null || exit 0
fi

echo "Claude Code CLI not found; attempting install…" >&2

# User-local install path (smoke: EACCES on /usr/lib/node_modules)
export NPM_CONFIG_PREFIX="${NPM_CONFIG_PREFIX:-$HOME/.local}"
export PATH="$HOME/.local/bin:${PATH}"
mkdir -p "$HOME/.local"

if command -v npm >/dev/null 2>&1; then
  npm config set prefix "$HOME/.local" >/dev/null 2>&1 || true
  npm install -g @anthropic-ai/claude-code || true
fi

# Re-check with user bin on PATH
export PATH="$HOME/.local/bin:${PATH}"

if ! command -v claude >/dev/null 2>&1; then
  echo "Install Claude Code: https://docs.anthropic.com/en/docs/claude-code" >&2
  echo "Hint: npm config set prefix \"\$HOME/.local\" && export PATH=\"\$HOME/.local/bin:\$PATH\"" >&2
  exit 127
fi
