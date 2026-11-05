# WSP harness (exp8-aligned)

Weight-space programming harness for **SmolLM2-360M-Instruct** on the tool-schema skill.

**Editor:** Claude Code (via `run_editor_long.sh`), matching Takehi Experiment 8 / `p50c` protocol.  
See [`PROTOCOL.md`](PROTOCOL.md) for the exact mapping and leakage audit.

## Layout

| Module | Role |
|--------|------|
| `weights.py` | Base + working `state_dict`, protected params, `save_edit` / revert / diff / export |
| `practice/` | Sealed **train-only** `train.jsonl` (editor-visible) |
| `practice.py` | Loads practice train only |
| `forward.py` | Budgeted `generate` / `inspect`; `which=base\|edited\|both` |
| `harness.py` | Session API + `artifacts/wsp_sessions/<id>/` |
| `sandbox.py` | Restricted `exec` for editor scripts |
| `leakage_guard.py` / `seal_for_run.py` | Train/test seal + quarantine |
| `eval_edited.py` | Post-run test score (budget gate) |
| `cli.py` | Ops CLI |
| `PROTOCOL.md` | exp8 mapping |

## Guards (exp8 / blog)

- No gradients / training
- Refuse edits to `embed_tokens`, `lm_head`, final `model.norm`
- Refuse whole-tensor scalar rescale
- Practice = **train** only; test quarantined during long runs
- Failed forward requests do not consume budget
- `eval_edited` refuses until budget exhausted (unless operator `--force`)

## Quick start

```bash
python3 experiments/tool_schema/wsp/test_harness.py
python3 experiments/tool_schema/wsp/cli.py audit

python3 experiments/tool_schema/wsp/cli.py --budget 10 --session-id demo init
python3 experiments/tool_schema/wsp/cli.py --session-id demo forward \
  --mode generate --which base --max-examples 8
```

## Long Claude Code run (p50c-style, budget 50)

```bash
WSP_BUDGET=50 bash experiments/tool_schema/wsp/run_editor_long.sh
```

This seals holdout test material under `/tmp/wsp_seal`, sets `WSP_LOCK_TEST=1`,
launches Claude Code, then unseals and runs `eval_edited.py --force`.

Prompts: `editor/SYSTEM.md`, `editor/USER.md`.  
Live log: `results/RUNNING_LOG.md`.

## Editor API

```python
import sys
sys.path.insert(0, "experiments/tool_schema")
from wsp.harness import WSPHarness
h = WSPHarness(forward_budget=50, session_id="wsp-p50-demo")
h.forward_pass(mode="generate", which="base", max_examples=40)   # 1 pass
h.forward_pass(mode="inspect", which="edited", max_examples=40, layers=[16, 24])
h.forward_pass(mode="generate", which="both", max_examples=40)   # paired
h.export()
```
