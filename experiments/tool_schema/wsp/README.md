# WSP harness (preparation)

Weight-space programming harness for **SmolLM2-360M-Instruct** on the tool-schema skill.

This is the **prep layer only**: weight store, guarded `save_edit`, train-split practice, metered `forward_pass`, restricted sandbox. The editor-agent loop (Opus) starts in a later run.

## Layout

| Module | Role |
|--------|------|
| `weights.py` | Base + working `state_dict`, protected params, `save_edit` / revert / diff / export |
| `practice.py` | Loads **train** split only |
| `forward.py` | Budgeted generate+score on practice |
| `harness.py` | Session API + `artifacts/wsp_sessions/<id>/` |
| `sandbox.py` | Restricted `exec` for future editor scripts |
| `cli.py` | Smoke / ops CLI |

## Guards (blog-style)

- No gradients / training
- Refuse edits to `embed_tokens`, `lm_head`, final `model.norm`
- Refuse whole-tensor scalar rescale
- Practice = **train** only; test stays holdout

## Quick start

```bash
# unit tests (no model download required for guards)
python3 experiments/tool_schema/wsp/test_harness.py

# live smoke against local models/SmolLM2-360M-Instruct
# (global flags before the subcommand)
python3 experiments/tool_schema/wsp/cli.py --budget 10 --session-id demo init
python3 experiments/tool_schema/wsp/cli.py --session-id demo list-params --substr mlp --limit 10
python3 experiments/tool_schema/wsp/cli.py --budget 5 --session-id demo smoke-edit --forward-n 3
python3 experiments/tool_schema/wsp/cli.py --session-id demo status
```

Session state lands in `artifacts/wsp_sessions/` (gitignored via `artifacts/*`).

## Claude Code editor run

```bash
# default budget 15
bash experiments/tool_schema/wsp/run_editor.sh

WSP_BUDGET=10 WSP_SESSION_ID=wsp-manual bash experiments/tool_schema/wsp/run_editor.sh
```

Prompts: `editor/SYSTEM.md`, `editor/USER.md`.  
Live log: `results/RUNNING_LOG.md`.  
After export: `python3 experiments/tool_schema/wsp/eval_edited.py --session-dir artifacts/wsp_sessions/<id>`.

## Editor API

```python
import sys
sys.path.insert(0, "experiments/tool_schema")
from wsp.harness import WSPHarness
h = WSPHarness(forward_budget=25, session_id="demo")
h.list_params("mlp")
t = h.get_tensor("model.layers.0.mlp.down_proj.weight")
h.save_edit("try1", "model.layers.0.mlp.down_proj.weight", t.clone())
out = h.forward_pass(max_examples=8)   # spends 1 budget
h.export()
```
