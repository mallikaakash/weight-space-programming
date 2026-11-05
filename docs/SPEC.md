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

- Full eval run with tag `base` on CPU or CUDA.
- Primary metric `strict_ok` reported (parseable JSON + correct tool + args).
- README documents setup and how to re-run.

**Verification hint:** `experiments/tool_schema/results/base_latest.summary.json` exists with `"tag": "base"`.

---

### REQ-005: Reject hallucinated argument keys

**Acceptance**

- `score.py` adds `no_hallucinated_keys`: true iff `arguments` contains no keys beyond the gold expected argument set.
- `strict_ok` requires `no_hallucinated_keys` in addition to existing checks.
- `summarize()` reports `no_hallucinated_keys` rate.
- `test_score.py` covers: (1) extra key fails `no_hallucinated_keys` / `strict_ok`; (2) exact args still pass.
- Re-run `python3 experiments/tool_schema/test_score.py` successfully.

**Verification hint:** Grep `no_hallucinated_keys` in `score.py` / `test_score.py`; tests pass.

---

### REQ-006: Frozen train/test holdout split

**Acceptance**

- Rebuild eval via `build_eval.py` so every example has `"split": "train"` or `"split": "test"`.
- Target ~40 train / ~20 test, **stratified by tier** (easy/medium/hard each contribute to both splits). Deterministic assignment (no RNG, or fixed seed documented in code).
- Also write `experiments/tool_schema/eval/splits.json` listing train/test ids.
- `benchmark.py` accepts `--split {all,train,test}` (default `all`) and filters examples; summary includes `"split"`.
- README documents the split and that **reported headline metrics use `--split test`**.

**Verification hint:** `dataset.jsonl` lines include `"split"`; `splits.json` exists; `benchmark.py --help` shows `--split`.

---

### REQ-007: Stability re-runs on the test split

**Acceptance**

- Add `experiments/tool_schema/stability.py` (or equivalent) that runs the benchmark **3 times** on `--split test` with greedy decoding (`temperature=0`), tags like `stability-r1`…`r3`.
- Writes `experiments/tool_schema/results/stability.json` with per-run `strict_ok` / `parse_ok` / `tool_ok` and `strict_ok_range` (max−min).
- If model weights are missing under `models/SmolLM2-360M-Instruct`, run `download_model.py` first.
- Prefer reusing one loaded model across runs if practical; otherwise three `benchmark.py` invocations are fine.
- Check in `results/stability.json` (summaries only; full generations may stay under gitignored `artifacts/`).

**Verification hint:** `results/stability.json` has 3 runs and `strict_ok_range`.

---

### REQ-008: Failure spot-check report

**Acceptance**

- Add `experiments/tool_schema/spotcheck.py` that reads a benchmark JSON artifact (default: latest test-split run under `artifacts/baselines/`) and writes `experiments/tool_schema/results/spotcheck.md`.
- Include **10–15 failures** (prefer diverse failure modes: parse fail, wrong tool, missing keys, bad values, hallucinated keys).
- For each: id, tier, user (short), expected tool, completion snippet, which score flags failed.
- Short “notes” section grouping dominant failure patterns.
- Check in `results/spotcheck.md`.

**Verification hint:** `results/spotcheck.md` exists with ≥10 failure entries.

---

### REQ-009: Refresh checked-in baseline on test split

**Acceptance**

- After scoring changes, run `benchmark.py --split test --tag base-test` (model already downloaded if possible).
- Update `experiments/tool_schema/results/base_latest.summary.json` from that test-split run (include `split: test`, `no_hallucinated_keys`, `n` ≈ 20).
- Update `experiments/tool_schema/README.md` for new flags, split, stability, spotcheck commands.

**Verification hint:** `base_latest.summary.json` has `"split": "test"` and `no_hallucinated_keys` field.

---

### REQ-010: WSP harness package (prep only — no editor agent run)

**Acceptance**

- Add `experiments/tool_schema/wsp/` with weight store, practice loader (train only), metered forward service, session harness, restricted sandbox, CLI, README.
- `WeightStore` supports `list_params`, `get_tensor`, `save_edit`, `revert_param` / `revert_all`, `diff_stats`, `export_state`.
- Guardrails: refuse protected params (`embed_tokens`, `lm_head`, final `model.norm`); refuse `requires_grad` tensors; refuse whole-tensor scalar rescale; `torch.set_grad_enabled(False)` during sandbox exec.
- Practice prompts load **train split only**; harness constructor rejects `practice_split != "train"`.
- `ForwardService.forward_pass` consumes one budget unit and returns scored practice batch (`edited` or temporary `base`).
- Sessions persist under `artifacts/wsp_sessions/<id>/` (`state.json`, events log).
- `python3 experiments/tool_schema/wsp/test_harness.py` passes.
- Live smoke (if model present): `cli.py smoke-edit` completes one edit + forward + revert.
- Do **not** run an Opus/Claude editor weight-programming loop in this change.

**Verification hint:** `wsp/README.md` exists; unit tests pass; optional smoke writes a session under `artifacts/wsp_sessions/`.

---

### REQ-011: Claude Code WSP editor run

**Acceptance**

- `experiments/tool_schema/wsp/editor/SYSTEM.md` and `USER.md` instruct Claude Code as the weight editor.
- `run_editor.sh` launches `claude -p` with budget/session substitution and appends to `results/RUNNING_LOG.md`.
- `eval_edited.py` scores an exported `edited_state.pt` on the **test** split and writes `results/edited_test_latest.summary.json`.
- Root `README.md` documents current baselines and how to start the editor.
- An editor run is started (or attempted) with a non-empty running log; if the model/auth is available, at least one forward_pass and one real edit attempt occur.
- Do not leak secrets into the log.

**Verification hint:** editor prompts + `run_editor.sh` exist; `RUNNING_LOG.md` has a started/finished section; optional `edited_test_latest.summary.json`.

---

## Rubric checklist (orchestrator)

- [ ] **REQ-001:** Spec-driven workflow exists — orchestrator scripts, hooks, and docs in place.
- [ ] **REQ-003:** SmolLM2-360M tool-schema eval harness — download, eval, score, benchmark scripts.
- [ ] **REQ-004:** Baseline benchmark recorded for SmolLM2-360M-Instruct — checked-in summary.
- [ ] **REQ-005:** Reject hallucinated argument keys — scorer + tests.
- [ ] **REQ-006:** Frozen train/test holdout split — dataset + `--split` filter.
- [ ] **REQ-007:** Stability re-runs on the test split — `results/stability.json`.
- [ ] **REQ-008:** Failure spot-check report — `results/spotcheck.md`.
- [ ] **REQ-009:** Refresh checked-in baseline on test split — summary + README.
- [ ] **REQ-010:** WSP harness package (prep only — no editor agent run).
- [ ] **REQ-011:** Claude Code WSP editor run — prompts, runner, log, test eval of export.

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
