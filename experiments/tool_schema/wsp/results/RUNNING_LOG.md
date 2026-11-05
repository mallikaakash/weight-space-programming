# WSP running log

Track weight-space programming editor runs here. Append-only during a run.

## Baseline (pre-edit)

- Model: `HuggingFaceTB/SmolLM2-360M-Instruct`
- Test `strict_ok`: **20%** (n=20); parse 80%; tool 25%; no_hallucinated_keys 40%
- Stability: 3× greedy, `strict_ok_range = 0.0`
- Train practice size: 40

## Runs

_Awaiting first editor launch…_

## Run started 2026-11-05T08:15:27Z

- session_id: `wsp-run1-20261105T081527Z`
- budget: `12`
- claude_log: `/workspace/experiments/tool_schema/wsp/results/claude_editor_wsp-run1-20261105T081527Z.log`
- status: **running**

- trial `L29 down_proj top-1% magnitude x1.15`: 0.4 strict (base 0.40), parse 0.75, tool 0.575

### Monitor note (2026-11-05 UTC)

- Editor is live and already ran multiple train forwards + localized `L29 down_proj` magnitude edits.
- **Bug found:** each new Python process re-inited the harness and reset budget/edits. Fixed mid-run: sessions now persist `working_state.pt` + `budget.json` and **resume** on the same `session_id`.
- Reconstructed `budget.json` from `events.jsonl` so remaining budget is honest going forward.

