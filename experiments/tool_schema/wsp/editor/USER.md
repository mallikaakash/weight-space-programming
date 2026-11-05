# WSP run — SmolLM2-360M tool-schema specialization

Work in the repo root: `/workspace`.

## Environment

- Model weights: `models/SmolLM2-360M-Instruct` (already downloaded).
- Harness package: `experiments/tool_schema/wsp/`
- Train practice: 40 examples (harness loads automatically).
- Forward budget for this run: **{{BUDGET}}** (set by runner).
- Session id: **{{SESSION_ID}}**

## How to drive the harness

```python
import sys
from pathlib import Path
sys.path.insert(0, "experiments/tool_schema")
from wsp.harness import WSPHarness

h = WSPHarness(forward_budget={{BUDGET}}, session_id="{{SESSION_ID}}")
print(h.status())

# one metered practice batch (costs 1 budget)
out = h.forward_pass(max_examples=8, which="edited")  # or which="base"
print(out["summary"], out["budget"])

# edit example
param = "model.layers.15.mlp.down_proj.weight"  # choose after inspection
t = h.get_tensor(param)
# ... surgical modification ...
h.save_edit("desc", param, t_new, note="why")

h.export()
```

CLI alternatives:

```bash
python3 experiments/tool_schema/wsp/cli.py --budget {{BUDGET}} --session-id {{SESSION_ID}} status
python3 experiments/tool_schema/wsp/cli.py --budget {{BUDGET}} --session-id {{SESSION_ID}} forward --max-examples 8
```

After export, score **test** holdout with the edited weights:

```bash
python3 experiments/tool_schema/wsp/eval_edited.py \
  --session-dir artifacts/wsp_sessions/{{SESSION_ID}} \
  --tag wsp-edited
```

Copy the summary into `experiments/tool_schema/wsp/results/` as `edited_test_latest.summary.json`.

## Deliverables before you stop

1. Meaningful edit attempts under the budget (not just smoke epsilon).
2. Updated `experiments/tool_schema/wsp/results/RUNNING_LOG.md`.
3. Exported session under `artifacts/wsp_sessions/{{SESSION_ID}}/`.
4. Test-split summary for the edited model vs the known 20% baseline.
5. Short final note: what worked / what did not (expect possible failure to *add* skill — still a result).

Start now: create the harness session, inspect base failures with one forward pass, then edit.
