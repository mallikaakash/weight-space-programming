# WSP long run (exp8 / p50c-style) — SmolLM2-360M tool-schema

Work in `/workspace`. Read `experiments/tool_schema/wsp/PROTOCOL.md` if you need the mapping.

## Environment

- Weights: `models/SmolLM2-360M-Instruct` (read via harness)
- Harness: `experiments/tool_schema/wsp/`
- Practice (only): `experiments/tool_schema/wsp/practice/train.jsonl` — **40 train examples with answers**
- Forward budget: **{{BUDGET}}** — use **all** of them
- Session id: **{{SESSION_ID}}** ← always reuse this exact id
- Test split: **sealed**. Do not open eval datasets, sealed folders, or run `eval_edited.py`.

## Drive the harness (resume-safe)

```python
import sys
sys.path.insert(0, "experiments/tool_schema")
from wsp.harness import WSPHarness

h = WSPHarness(forward_budget={{BUDGET}}, session_id="{{SESSION_ID}}")
print(h.status())  # resumed budget/edits if re-entering

# Diagnostic generation (1 pass)
out = h.forward_pass(mode="generate", which="base", max_examples=40)
print(out["summary"], out["budget"])

# Optional inspect (1 pass)
ins = h.forward_pass(mode="inspect", which="base", max_examples=40, layers=[8, 16, 24])
print(ins["summary"])

# After an edit — paired comparison (1 pass)
t = h.get_tensor(param)
h.save_edit("hypA", param, t_new, note="...")
both = h.forward_pass(mode="generate", which="both", max_examples=40)
print(both["summary"])

# When budget remaining hits 0:
h.export()
```

## Deliverables (before you stop)

1. Failure taxonomy + every hypothesis in `experiments/tool_schema/wsp/results/RUNNING_LOG.md`
2. Full budget consumed (`forward_used == {{BUDGET}}`)
3. `export()` written under `artifacts/wsp_sessions/{{SESSION_ID}}/export/`
4. Final plain-English summary: what changed, evidence, why you expect it to help
5. **Do not** score the test split yourself

Start now with session `{{SESSION_ID}}`. Continue until every forward pass is used.
