# WSP protocol (exp8-aligned)

This document maps our SmolLM2-360M tool-schema run to Takehi **Experiment 8**
(`RikiyaT/lm_understand-logs` → `exp8_math/`, especially `runs/p50c`).

## Roles

| Original (exp8) | This repo |
|-----------------|-----------|
| Astra via Codex CLI | **Claude Code** via `run_editor_long.sh` |
| Qwen3.5-0.8B math | SmolLM2-360M-Instruct JSON tool-schema |
| Persistent weight kernel + forward tool | `WSPHarness` (`weights` / `forward` / `sandbox`) |
| Practice GSM8K/MATH train (no test) | `wsp/practice/train.jsonl` (40 train rows) |
| Held-out benchmarks (never shown) | `eval/sealed/test.jsonl` (20 rows), quarantined during the run |
| Pass budgets 10 / 25 / **50** | Long run = **50** (`WSP_BUDGET=50`) |

Claude Code is the weight editor using this harness. Cursor is the outer
orchestrator (start / seal / post-eval), not the tensor editor.

## Leakage (answer to “is there leakage?”)

| Surface | Status |
|---------|--------|
| Harness `load_practice` / `forward_pass` | **No leakage** — train-only; non-train ids refused |
| `save_edit` guards | Protected embed / lm_head / final norm; whole-tensor rescale refused |
| Agent filesystem (Claude + `--add-dir`) | **Was a real risk** — could open `eval/dataset.jsonl` test rows |
| Long-run quarantine (`WSP_LOCK_TEST=1`) | Live dataset stubbed to train-only; sealed test moved under `/tmp/wsp_seal/`; `eval_edited` refused until budget exhausted |

Baseline score ≈20% in the prompt is **not** considered leakage (exp8 also told
the editor how evaluation works). Optimizing on actual test *examples* would be.

## Forward tool (exact exp8 semantics, scaled down)

One **successful** request = one pass. Failed requests do not count.

1. **`mode="generate"`** — model answers practice items; scored with `strict_ok` ladder.
2. **`mode="inspect"`** (alias `teacher_forced`) — teacher-forced NLL on expected JSON; optional layer residual norms.
3. **`which="base"|"edited"|"both"`** — `both` = paired comparison on the same ids (exp8 `model: both`).

Local caps: practice size 40 (not 512/1024). Prefer full-train batches when measuring.

## How a run ends (exp8)

1. Continue until **all** forward passes are used.
2. Final choice = tensors in the session export (`export()`).
3. Editor replies with what changed and why — **without** seeing test scores.
4. Human/orchestrator unseals and runs `eval_edited.py --force` after the lock clears.

## Editor rules (from exp8 message.txt)

- No gradient descent / autograd / optimizers / fitting weights to a loss.
- Do not run the model except through `forward_pass`.
- Diagnose on practice → localize causally → measure with power (`which="both"`) → keep only clear gains.
- Prefer mechanism-level edits (routing / format / value failures), not global knobs.
- Explain each step in plain English before the next edit/forward.

## Commands

```bash
# Seal audit (must be ok before launch)
python3 experiments/tool_schema/wsp/cli.py audit

# Long run like p50c
WSP_BUDGET=50 bash experiments/tool_schema/wsp/run_editor_long.sh

# After run + unseal (orchestrator):
WSP_LOCK_TEST=0 python3 experiments/tool_schema/wsp/eval_edited.py \
  --session-dir artifacts/wsp_sessions/<id> --tag wsp-p50 --force
```
