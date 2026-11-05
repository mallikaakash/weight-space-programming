# Claude Code build + Cursor orchestrator

Claude Code implements features from `docs/SPEC.md`. A **Cursor agent** does not edit app code; it launches Claude, monitors the subprocess, then produces a verification rubric.

## Architecture

```text
run.mjs (your machine / CI)
  └─► Cursor cloud agent (orchestrator prompt)
        ├─► bash scripts/claude-build.sh  →  claude -p … (CLAUDE_CODE_OAUTH_TOKEN)
        ├─► node scripts/orchestrator/verify-rubric.mjs  →  artifacts/RUBRIC.md
        └─► reads diff + spec → assessment in artifacts/RUBRIC.md
```

Project hook `.cursor/hooks/orchestrator-guard.sh` blocks Cursor **Write/Edit** tools while `artifacts/.orchestrator-active` exists, so the orchestrator cannot patch source files during a run.

## Secrets (never commit)

| Secret | Used by | Where to store |
|--------|---------|----------------|
| `CLAUDE_CODE_OAUTH_TOKEN` | Claude Code CLI (Pro / Max subscription via `setup-token`) | **[Cursor Dashboard → Cloud Agents → secrets](https://cursor.com/dashboard?tab=cloud-agents)** for cloud runs; repo `.env` locally (gitignored) |
| `CURSOR_API_KEY` | `scripts/orchestrator/run.mjs` | Laptop / CI only — [Dashboard → Integrations](https://cursor.com/dashboard/integrations) |
| `ANTHROPIC_API_KEY` (optional) | Claude Code via Console API billing | Only if you are **not** using subscription token; separate from Pro |

### Subscription token (recommended)

1. On a machine with a browser: `claude setup-token`
2. Approve in the browser; copy the **full** token (often starts with `sk-ant-oat01-…`)
3. Set **`CLAUDE_CODE_OAUTH_TOKEN`** — it is **not** saved anywhere by that command

Local:

```bash
cp .env.example .env
# CLAUDE_CODE_OAUTH_TOKEN=…   (no quotes needed unless value has spaces)
```

Cloud: add the same variable name in **Cloud Agent environment secrets**. Cloud VMs do **not** read your laptop `.env`.

Docs: [Claude Code authentication](https://code.claude.com/docs/en/authentication) (`setup-token` → `CLAUDE_CODE_OAUTH_TOKEN`).

### Optional: Console API key

If you prefer pay-as-you-go API instead of subscription token, set `ANTHROPIC_API_KEY` instead (or as fallback). That bills your **API** account, not Pro.

### Local-only: interactive login

If you already ran `claude auth login` on the same machine, `claude-build.sh` may work without env vars. Cloud orchestrator still needs **`CLAUDE_CODE_OAUTH_TOKEN` in Cloud Agent secrets**.

Never commit tokens, paste them into chat, or check them into the repo.

## One-time setup

```bash
cd scripts/orchestrator
npm install
cp ../../.env.example ../../.env   # if not already
```

Set in `.env`:

- `CURSOR_API_KEY`
- `GITHUB_REPO_URL` (this repo on GitHub — required for `npm start`)
- `CLAUDE_CODE_OAUTH_TOKEN` (from `claude setup-token`)
- `GITHUB_REF` (branch, default `main`)
- Optional: `AUTO_CREATE_PR=1`, `CURSOR_MODEL=composer-2.5`

For **cloud** runs, also set **`CLAUDE_CODE_OAUTH_TOKEN`** in Cursor Cloud Agent settings.

## Launch cloud orchestrator

From repo root:

```bash
set -a && source .env && set +a   # or direnv
cd scripts/orchestrator && npm start
```

SDK-started cloud agents may be hidden by default — filter **Source → SDK** in Cursor, then open the run on mobile or desktop.

## Local orchestrator (same repo checkout)

```bash
cd scripts/orchestrator && npm run start:local
```

Requires `CLAUDE_CODE_OAUTH_TOKEN` (or local `claude auth login`) for `claude-build.sh`.

## Updating what gets built

1. Edit `docs/SPEC.md` (requirements + rubric checklist).
2. Commit and push.
3. Re-run `npm start` (cloud) or `npm run start:local`.

## Outputs

| Path | Description |
|------|-------------|
| `artifacts/claude-build.log` | Full Claude Code stdout/stderr |
| `artifacts/RUBRIC.md` | Checklist + changed files + orchestrator assessment |
| `.orchestrator/baseline.sha` | Git HEAD before Claude run (for diff) |

`artifacts/*.log` and session markers are gitignored; commit `artifacts/.gitkeep` only.
