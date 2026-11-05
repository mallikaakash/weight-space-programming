# WSP run2 — SmolLM2-360M tool-schema (hypothesis-driven)

Work in `/workspace`.

## Environment

- Weights: `models/SmolLM2-360M-Instruct`
- Harness: `experiments/tool_schema/wsp/`
- Train practice: 40 examples (auto-loaded)
- Forward budget: **{{BUDGET}}**
- Session id: **{{SESSION_ID}}**  ← always reuse this exact id

## Drive the harness (resume-safe)

```python
import sys
sys.path.insert(0, "experiments/tool_schema")
from wsp.harness import WSPHarness

h = WSPHarness(forward_budget={{BUDGET}}, session_id="{{SESSION_ID}}")
print(h.status())  # should show resumed budget/edits if re-entering

out = h.forward_pass(max_examples=16, which="base")
print(out["summary"], out["budget"])
# inspect out["examples"] failures → log taxonomy

# hypothesis edit...
t = h.get_tensor(param)
h.save_edit("run2_hypA", param, t_new, note="...")
out2 = h.forward_pass(max_examples=16, which="edited")

h.export()
```

Final test eval:

```bash
python3 experiments/tool_schema/wsp/eval_edited.py \
  --session-dir artifacts/wsp_sessions/{{SESSION_ID}} \
  --tag wsp-run2
```

Ensure `experiments/tool_schema/wsp/results/edited_test_latest.summary.json` is updated.

## Deliverables

1. Failure taxonomy in `experiments/tool_schema/wsp/results/RUNNING_LOG.md`
2. ≥2 distinct hypotheses attempted with measured train forwards
3. Export + test summary vs 20% baseline
4. Explicit note: what moved (`tool_ok` / `values_ok` / `strict_ok`) and what did not

Start now with session `{{SESSION_ID}}`.
