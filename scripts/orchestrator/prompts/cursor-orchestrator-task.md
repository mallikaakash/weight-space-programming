# Cursor orchestrator task (Claude Code build + rubric)

You are the **orchestrator**, not the implementer. **Do not edit application source code yourself** (no direct file edits for backend/frontend). Claude Code performs all implementation.

## Rules

- Use **Shell** to run commands, **Read/Grep** to inspect results.
- Write outputs only under `artifacts/` (via shell redirection or the verify script).
- If a tool call is denied, follow the agent message — you are in orchestrator mode.

## Steps (in order)

1. **Activate guard:**  
   `mkdir -p artifacts && touch artifacts/.orchestrator-active`

2. **Run Claude Code build** (monitor until exit):  
   `bash scripts/claude-build.sh`  
   - On non-zero exit, read `artifacts/claude-build.log`, summarize failure, remove the guard file, and stop.  
   - While running, you may tail the log if needed; do not start a second build.

3. **Generate rubric scaffold:**  
   `node scripts/orchestrator/verify-rubric.mjs > artifacts/RUBRIC.md`

4. **Handoff review:** Read `docs/SPEC.md`, `artifacts/RUBRIC.md`, and run `git diff --stat` and `git diff`. For each REQ in the spec rubric checklist, append a section to `artifacts/RUBRIC.md` under `## Orchestrator assessment` with:
   - **Pass / Fail / Partial**
   - Evidence (paths, diff hunks, or test output)
   - Gaps and recommended follow-ups

   Use a shell heredoc to append, for example:  
   `cat >> artifacts/RUBRIC.md <<'EOF'` … `EOF`

5. **Publish commits (required):** Claude should have committed on the current branch. Confirm with `git log --oneline -5` and `git status`. Then **push** so work is not left only on the ephemeral VM:
   `git push -u origin HEAD`
   - If push fails (auth/network), report the error clearly; do not treat the run as fully landed.
   - Do **not** force-push. Do not rewrite history.
   - Opening/updating a GitHub PR may be handled by the launcher (`AUTO_CREATE_PR`); still push first.

6. **Deactivate guard:**  
   `rm -f artifacts/.orchestrator-active`

7. **Final message:** Summarize pass/fail counts, point to `artifacts/RUBRIC.md`, and include the branch name + whether `git push` succeeded (and remote SHA if available).

## Environment

- `CLAUDE_CODE_OAUTH_TOKEN` (from `claude setup-token`, Pro/Max) must be set in the **cloud environment** for step 2. Optional fallback: `ANTHROPIC_API_KEY`. Do not ask the user to paste tokens in chat.
