# Build spec — weight-space-programming

Single source of truth for **Claude Code** implementation runs. Update this file before launching the orchestrator.

Orchestrator flow: Cursor agent runs `scripts/claude-build.sh` (Claude Code subprocess) → reads git diff → fills `artifacts/RUBRIC.md` using the checklist below.

---

## Requirements

### REQ-001: Spec-driven workflow exists

**Acceptance**

- `docs/SPEC.md` (this file) defines requirements with IDs.
- `scripts/claude-build.sh` invokes Claude Code against this spec.
- `scripts/orchestrator/run.mjs` launches the Cursor orchestrator on cloud.

**Verification hint:** Files exist and `docs/ORCHESTRATION.md` describes secrets.

---

### REQ-002: Project placeholder

**Acceptance**

- Add your first real feature requirements below this section (copy the REQ-00N template).
- Remove or replace this placeholder once you have concrete work items.

**Verification hint:** N/A until you define scope.

---

## Rubric checklist (orchestrator)

Copy each requirement you care about for automated pass/fail review:

- [ ] **REQ-001:** Spec-driven workflow exists — orchestrator scripts, hooks, and docs in place.
- [ ] **REQ-002:** Project placeholder — replace with real requirements before production builds.

---

## REQ template (for new items)

```markdown
### REQ-00N: Short title

**Acceptance**

- Bullet criteria Claude must satisfy.

**Verification hint:** Paths, commands, or tests the orchestrator can cite.
```

Add matching lines under **Rubric checklist**:

`- [ ] **REQ-00N:** Short title — one-line summary.`
