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

### REQ-003: SmolLM2-360M tool-schema eval harness

**Acceptance**

- `experiments/tool_schema/` contains tools schema, eval builder, scorer, downloader, and benchmark runner.
- Eval set has ≥50 examples across easy/medium/hard tiers targeting JSON tool calls.
- Model weights download to gitignored `models/` (not committed).
- `python3 experiments/tool_schema/test_score.py` passes.
- Baseline summary checked in at `experiments/tool_schema/results/base_latest.summary.json`.

**Verification hint:** Paths above exist; summary includes `strict_ok` and per-tier stats.

---

### REQ-004: Baseline benchmark recorded for SmolLM2-360M-Instruct

**Acceptance**

- Full eval (`n=60`) run with tag `base` on CPU or CUDA.
- Primary metric `strict_ok` reported (parseable JSON + correct tool + args).
- README documents setup and how to re-run.

**Verification hint:** `experiments/tool_schema/results/base_latest.summary.json` has `"n": 60` and `"tag": "base"`.

---

## Rubric checklist (orchestrator)

- [ ] **REQ-001:** Spec-driven workflow exists — orchestrator scripts, hooks, and docs in place.
- [ ] **REQ-003:** SmolLM2-360M tool-schema eval harness — download, eval, score, benchmark scripts.
- [ ] **REQ-004:** Baseline benchmark recorded for SmolLM2-360M-Instruct — checked-in summary.

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
