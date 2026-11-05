
## BFCL cross-format bench started 2026-11-06T04:44:45Z

- session_id: `wsp-bfcl-crossfmt-20261106T044445Z`
- editor: `claude-opus-5-5` effort=`high`
- edited_state: `/workspace/artifacts/wsp_sessions/wsp-bfcl-p100-20261105T143615Z/export/edited_state.pt`
- categories: simple_python, simple_java, simple_javascript, multiple, parallel, parallel_multiple
- status: **done** (see final entry)


### 2026-11-06 — design sketch (before implementation)

Read `bfcl_simple_eval.py` and bfcl-eval 2025.10.27.1 `eval_runner.ast_file_runner` → `_evaluate_single_ast_entry` → `handler.decode_ast` (OSS prompting handlers = `default_decode_ast_prompting`) → `is_function_calling_format_output` → `ast_checker`.

Official facts that shape the design:
- Language/return format per category: `simple_java` → JAVA (tree-sitter Java parser), `simple_javascript` → JAVASCRIPT (tree-sitter JS parser), everything else → PYTHON. All three parsers take the same `[func(name=value, ...)]` surface form.
- `ast_checker` dispatch is by category substring: `parallel*` → `parallel_function_checker_no_order`, `multiple` → `multiple_function_checker`, else `simple_function_checker`.
- Generation side: official prompting runs load function docs **with** language-specific hints (Java/JS params rewritten to `type: string` + "This is Java X type parameter in string representation"). Scoring side (`evaluate_task`) reloads docs **without** hints. We mirror that split.
- Sizes: simple_python 400, simple_java 100, simple_javascript 50, multiple 200, parallel 200, parallel_multiple 200 (1150 items / model).

Eval design (`experiments/tool_schema/bfcl_category_eval.py`):
1. One process per model loads weights once and runs any list of `--category` values (≥ "once per (model, category)").
2. Prompt style `card` (default) = the repo's simple_python protocol: short system prompt with format rules + compact per-function "card" in the user turn. `simple_python` prompt is kept **byte-identical** to `bfcl_simple_eval.py`, so items 300–399 reproduce the WSP holdout protocol. Adaptations: Java/JS system prompts with Java/JS literal rules (cards use official hinted descriptions); `multiple` lists N cards and asks for ONE call; `parallel`/`parallel_multiple` ask for ALL calls in one bracketed list. Optional `--prompt-style bfcl` uses the official `system_prompt_pre_processing_chat_model` (JSON function dump) as a secondary probe.
3. Greedy decoding; max_new_tokens 128 (simple/multiple), 256 (parallel*). Left-padded batching, length-sorted; sanity-check that batching reproduces the old holdout generations before trusting it.
4. Scoring: call bfcl-eval's own `_evaluate_single_ast_entry` with a shim handler whose `decode_ast` is `default_decode_ast_prompting`. Headline `ast_accuracy` = after the repo's `[...]` extraction (same as WSP protocol); also report `ast_accuracy_raw` = official decode on the untouched completion.
5. Outputs per (model, category): `*.summary.json` (+ error_type histogram, simple_python practice/holdout split) and `*.generations.jsonl` with per-item verdicts → paired flip counts in the table.

### 2026-11-06 — implementation + smoke

- Added `experiments/tool_schema/bfcl_category_eval.py` (multi-category CLI) and `run_bfcl_crossfmt.sh` (base → edited, all six categories, model loaded once per run).
- **Protocol check:** `simple_python` items 300–315 regenerated with the new CLI match the stored WSP holdout base completions **exactly** (16/16), at batch 1 and batch 8. Batch 1 was faster on this 4-core CPU (14.6 s vs 25.3 s / 16 items), so batch 1 is the default (= legacy protocol).
- Smoke (6 items/category, base) exposed prompt-template bugs of mine, fixed before any full run: `[1]`-style card numbering in `multiple` made the model answer `[function_name]`; `function_a/function_b` placeholders were copied literally in parallel_multiple; added "do not define the function" to Java/JS rules. No further prompt tuning (same prompt for base and edited).
- Official BFCL system prompt (`--prompt-style bfcl`, JSON function dump) smoke: base 1/36 overall — model writes prose / Python code / echoes JSON. Kept as optional secondary style; card style is the headline.
- Known floor: base writes JS function *definitions* instead of calls for `simple_javascript` even with the explicit rule.
- Full card-style run launched: base then edited, all six categories, no limit.

### 2026-11-06 — base simple_python done (full 400)

- base `simple_python` full: 156/400 = 0.390; practice 0–299 = 0.410 (123/300), holdout 300–399 = 0.330 (33/100) — **identical** to the documented WSP baseline numbers → protocol reproduction confirmed.
- base `simple_java`: 5/100. Failure mix: decoder_failed 40 (mostly `[Name]` + schema echo), wrong_func_name 40 — 28/100 copy the Java system-prompt demo (`ReportBuilder.export` / `TextIndex.search`), same demo-copy habit WSP edit #2 targeted for `math.factorial`. ~5.5 s/item (runs to the 128-token cap).
- base `simple_javascript`: 0/50 (writes JS function *definitions*, as in smoke).
- base `multiple`: 58/200 = 0.290.
- base `parallel`: 4/200 = 0.020 — 171/200 `wrong_count` (emits one call when several are needed).
- base `parallel_multiple`: 1/200 = 0.005.
- Base pass finished (~55 min wall); edited pass started automatically.
- edited `simple_python` full: 235/400 = 0.5875; practice 185/300 = 0.617, holdout 50/100 = 0.50 — **identical** to the documented WSP numbers; holdout completions match the stored edited holdout generations 100/100.
- Observation: edited simple_python generation took ~2.3× the base wall-clock (2.5 vs 1.07 s/item) despite near-identical completion lengths (mean 76 vs 69 chars) and clean `<|im_end|>` stops. Edited state has no subnormal weights, fp32, contiguous; no other CPU load. Cause not determined; does not affect accuracy. **Correction (end of run):** not systematic — totals are base 3181 s vs edited 3072 s across all six categories; edited was faster on JS and parallel_multiple. Treat per-category timings as noise.
- edited `simple_java` 8/100, `simple_javascript` 1/50, `multiple` 79/200, `parallel` 3/200, `parallel_multiple` 3/200.

### 2026-11-06 — results + writeup

| category | n | base | edited | delta | flips +/− |
|---|---:|---:|---:|---:|---:|
| simple_python (all) | 400 | 0.390 | 0.588 | +0.198 | +88/−9 |
| ↳ holdout 300–399 | 100 | 0.330 | 0.500 | +0.170 | +19/−2 |
| simple_java | 100 | 0.050 | 0.080 | +0.030 | +5/−2 |
| simple_javascript | 50 | 0.000 | 0.020 | +0.020 | +1/−0 |
| multiple | 200 | 0.290 | 0.395 | +0.105 | +26/−5 (p≈2e-4) |
| parallel | 200 | 0.020 | 0.015 | −0.005 | +0/−1 |
| parallel_multiple | 200 | 0.005 | 0.015 | +0.010 | +2/−0 |

- Mechanism check: fused paren openings go to ~0 in every Python-format category (multiple 36→0); `multiple` missing_required 34→9 → explains most of the `multiple` gain. `math.factorial` demo copying drops, but Java-demo copying rises 28→35 (Java wrong_func_name 40→49): small negative side-effect, masked by near-zero Java accuracy.
- Parallel: `wrong_count` 171/200 for both on `parallel` — edits fix call syntax, not "emit several calls".
- Raw official decode (no `[...]` extraction) gives identical accuracies in every cell.
- `--prompt-style bfcl` not run at full scale (smoke base 1/36 → all-floor comparison); documented.
- Wrote `experiments/tool_schema/results/bfcl/CROSSFMT_BASE_VS_EDITED.md`, README "Cross-format probe" subsection. `edited_state.pt` untouched.
