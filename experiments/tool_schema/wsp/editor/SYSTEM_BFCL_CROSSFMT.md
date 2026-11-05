You are implementing and running a **BFCL cross-format benchmark** for this repo.

## Goal
Compare **base** SmolLM2-360M-Instruct vs the exported **`current4` edited** weights on BFCL v4 categories **beyond** the original `simple_python` practice/holdout WSP run. Produce a clear results table (base vs edited AST accuracy per category).

## Scope (must)
Non-live AST-style categories with official `possible_answer` + `ast_checker` (via bfcl-eval):

- `simple_python` (include as reference; may reuse existing holdout numbers if identical protocol, but prefer a fresh full-category run or document clearly)
- `simple_java`
- `simple_javascript`
- `multiple`
- `parallel`
- `parallel_multiple`

**Out of scope for this pass** (different runners / APIs / huge cost): live_*, multi_turn_*, web_search, memory, agentic, format_sensitivity, irrelevance/relevance. Mention them as skipped with reason in the writeup.

## Assets
- Base model: `models/SmolLM2-360M-Instruct`
- Edited state: `artifacts/wsp_sessions/wsp-bfcl-p100-20261105T143615Z/export/edited_state.pt`
  - If missing, rebuild via `pack_edited_delta.py apply` from `current4_delta.pt` + base
- Package: `bfcl-eval==2025.10.27.1` (BFCL v4 data under site-packages)
- Existing single-category script: `experiments/tool_schema/bfcl_simple_eval.py` (simple_python only — generalize or replace)

## Implementation requirements
1. Build a reusable eval entrypoint (extend `bfcl_simple_eval.py` or add `bfcl_category_eval.py`) that:
   - Takes `--category`, `--edited-state` (optional), `--limit`, `--offset`, `--tag`, `--out-dir`
   - Loads the right `BFCL_v4_<category>.json` + `possible_answer/`
   - Prompts the local HF model (same style as simple_python where applicable; adapt system/user prompt for java/js/multiple/parallel as needed so the model can emit the expected call format)
   - Scores with official `bfcl_eval` AST path (`ast_checker` / decode helpers used by eval_runner)
   - Writes `*.summary.json` + `*.generations.jsonl` under `experiments/tool_schema/results/bfcl/`
2. Run **base** then **edited** on each in-scope category (full set unless CPU forces a documented limit; if limiting, use the same limit for base and edited and say so).
3. Prefer loading the model once per (model, category) and batching sensibly. CPU is OK; do not invent GPU.
4. Write a markdown results table to `experiments/tool_schema/results/bfcl/CROSSFMT_BASE_VS_EDITED.md` and add a short pointer section in the root `README.md`.
5. Commit on branch `cursor/bfcl-crossfmt-base-vs-edited-317b` with clear messages; push when the table is ready.

## Honesty rules
- Do not claim full BFCL leaderboard parity.
- Edits were tuned on `simple_python` only — expect little/no gain (or regressions) elsewhere; report numbers either way.
- No WSP editing in this task — **eval only**.
- Do not delete `edited_state.pt`.

## Working style
- High thinking. Implement, then run, then tabulate.
- Log progress to `experiments/tool_schema/wsp/results/CROSSFMT_RUNNING_LOG.md`.
- If a category’s official decode path differs, read bfcl-eval’s `eval_runner.py` / `ast_checker.py` and match it.
