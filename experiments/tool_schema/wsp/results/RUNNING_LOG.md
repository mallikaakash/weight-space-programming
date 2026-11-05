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

- trial `L29 down_proj top-1% magnitude x0.85`: 0.4 strict (base 0.40), parse 0.675, tool 0.55
- trial `L20 o_proj top-2% x1.2`: 0.4 strict (base 0.40), parse 0.8, tool 0.6
- trial `L12 o_proj top-2% x1.2`: 0.4 strict (base 0.40), parse 0.775, tool 0.575
- 2 base passes (8-ex, 40-ex): base train strict_ok 0.40 (parse .725, tool .575). Failures: wrong-tool routing, unit-name drift (kg vs kilograms), no stop after JSON, free text.
- 4 edited trials (sparse top-magnitude scaling in L29 down_proj x1.15/x0.85, L20/L12 o_proj x1.2): all strict_ok 0.40, no gain.
- Kept L20 o_proj edit, exported. Total metered passes: 6 of 12 (the budget counter is per-process, so I counted manually).
- TEST (n=20): strict_ok 0.20, parse 0.80, tool 0.25 — identical to baseline. No skill added.

## Run finished 2026-11-05T08:26:00Z

- exit_code: `0`
- edited summary present: `edited_test_latest.summary.json`
- status: **finished** (exit 0)


---

## Run2 plan

- Goal: hypothesis-driven edits targeting wrong-tool routing / arg drift / format leakage.
- Avoid run1 blind top-magnitude scaling.
- Session persistence is fixed (`working_state.pt` + `budget.json`).


## Run started 2026-11-05T08:32:02Z

- session_id: `wsp-run2-20261105T083202Z`
- budget: `15`
- claude_log: `/workspace/experiments/tool_schema/wsp/results/claude_editor_wsp-run2-20261105T083202Z.log`
- status: **running**


### Run2 interrupted

Stopped mid-run to harden protocol (test quarantine + exp8-aligned forward tool + budget-50 long run). Run2 had used 3/15 passes; one edit collapsed train strict_ok to 0.0.


## Leakage audit (pre long-run) — 2026-11-05

**Editor:** Claude Code uses the WSP harness (`WSPHarness` / `forward_pass` / `save_edit`). Cursor orchestrates seal → launch → unseal → `eval_edited`.

| Check | Result |
|-------|--------|
| train ∩ test ids | empty (40 / 20) |
| Harness practice source | `wsp/practice/train.jsonl` only |
| Forward rejects non-train ids | yes |
| Agent FS risk (pre-seal) | yes — full `dataset.jsonl` was readable |
| Long-run quarantine | `seal_for_run.py` moves test to `/tmp/wsp_seal`, stubs live dataset to train-only, hides baseline result dumps |
| `eval_edited` during lock | refused (`WSP_LOCK_TEST=1`) and refuses until budget exhausted |
| Forward modes | `generate` / `inspect` (+ `which=both`) per exp8 |

**Verdict:** harness API had no test leakage; agent-level leakage is sealed for the budget-50 run. Protocol matches exp8/p50c (use all passes; editor never sees holdout scores during the run).

