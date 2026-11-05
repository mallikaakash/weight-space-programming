# weight-space-programming

Edit small LMs in **weight space** (no gradient descent) toward a specialized skill. Current target: **SmolLM2-360M-Instruct** → JSON **tool-schema** calling, using a Claude Code editor + local harness.

Inspired by [Sparks of Weight-Space Programming](https://rikiyat.github.io/blog/weight-space-programming/) (Takehi et al.) — same harness *shape*, different skill/angle (specialization + retention, not their math-loop curriculum).

---

## Current baselines (SmolLM2-360M-Instruct)

Headline metric: **`strict_ok`** on the **test** holdout (valid JSON tool call: correct tool, required keys, types, values, no extra keys).

| Split | n | parse_ok | tool_ok | no_hallucinated_keys | **strict_ok** |
|-------|---|----------|---------|----------------------|---------------|
| **test (headline)** | 20 | 80% | 25% | 40% | **20%** |
| easy (within test) | 6 | 83% | 17% | — | 17% |
| medium | 7 | 71% | 14% | — | 14% |
| hard | 7 | 86% | 43% | — | 29% |

- Stability (3× greedy on test): **`strict_ok_range = 0.0`** (all runs 20%).
- Train / test: **40 / 20**, stratified by tier (`experiments/tool_schema/eval/splits.json`).
- Sources: `experiments/tool_schema/results/base_latest.summary.json`, `stability.json`, `spotcheck.md`.

Earlier all-60 figure (~33% strict) is **not** comparable after holdout + hallucinated-key scoring.

---

## Repo layout

| Path | Role |
|------|------|
| `experiments/tool_schema/` | Tool-schema eval, scorer, baseline bench |
| `experiments/tool_schema/wsp/` | WSP harness + Claude editor prompts/runner |
| `models/` | Local weights (**gitignored**) |
| `artifacts/` | Session logs, full bench dumps (**gitignored**) |
| `docs/SPEC.md` | Spec for Claude Code / orchestrator builds |
| `docs/ORCHESTRATION.md` | Claude Code ↔ Cursor orchestrator |

---

## Setup

```bash
pip install -r experiments/tool_schema/requirements.txt
python3 experiments/tool_schema/build_eval.py
python3 experiments/tool_schema/download_model.py   # ~700MB → models/
```

### Re-run baseline

```bash
python3 experiments/tool_schema/benchmark.py --split test --tag base-test
python3 experiments/tool_schema/stability.py
python3 experiments/tool_schema/spotcheck.py
```

### WSP harness smoke

```bash
python3 experiments/tool_schema/wsp/test_harness.py
python3 experiments/tool_schema/wsp/cli.py --budget 5 --session-id demo smoke-edit --forward-n 3
```

### Start weight-space editor (Claude Code)

```bash
bash experiments/tool_schema/wsp/run_editor.sh
# logs: experiments/tool_schema/wsp/results/RUNNING_LOG.md
#      artifacts/wsp_sessions/<id>/
```

Requires `CLAUDE_CODE_OAUTH_TOKEN` (or local `claude` auth). See `experiments/tool_schema/wsp/editor/`.

---

## Scoring (tool schema)

`strict_ok` = `parse_ok` ∧ `tool_ok` ∧ args object ∧ required keys ∧ types ∧ values ∧ **`no_hallucinated_keys`**.

Details: [experiments/tool_schema/README.md](experiments/tool_schema/README.md).

---

## Orchestrator (optional)

Spec-driven Claude implementer + Cursor monitor: [docs/ORCHESTRATION.md](docs/ORCHESTRATION.md).
