# BFCL cross-format probe: base vs `current4`-edited SmolLM2-360M-Instruct

Session `wsp-bfcl-crossfmt-20261106T044445Z` · 2026-11-06 · **eval only** (no weight editing).

**Question:** the `current4` edit stack was tuned on BFCL `simple_python` practice items only (`wsp-bfcl-p100-20261105T143615Z`). Does it carry over to other BFCL v4 non-live AST categories (other languages, function choice, parallel calls), do nothing, or hurt?

**Short answer:** on these six categories it **did not hurt anywhere measurable**. It **helped clearly on `multiple`** (+10.5 pts, 26 gains vs 5 losses, p ≈ 2e-4). Java, JavaScript, `parallel` and `parallel_multiple` stay near the floor for both models, and the small changes there are not significant. Treat this as a probe of one tiny model under this repo's prompt protocol, **not** a BFCL leaderboard result.

## Main table (full categories, no limit)

| category | n | base AST acc | edited AST acc | delta (abs) | relative % | paired flips (+gain / −loss) | McNemar exact p |
|---|---:|---:|---:|---:|---:|---:|---:|
| `simple_python` | 400 | 156/400 = 0.390 | 235/400 = 0.588 | +0.198 | **+50.6%** | +88 / −9 | 2e-17 |
| ↳ `simple_python` practice 0–299 (**editor saw these**) | 300 | 123/300 = 0.410 | 185/300 = 0.617 | +0.207 | +50.4% | +69 / −7 | 6.4e-14 |
| ↳ `simple_python` holdout 300–399 (sealed during editing) | 100 | 33/100 = 0.330 | 50/100 = 0.500 | +0.170 | **+51.5%** | +19 / −2 | 2.2e-4 |
| `simple_java` | 100 | 5/100 = 0.050 | 8/100 = 0.080 | +0.030 | +60.0% | +5 / −2 | 0.45 |
| `simple_javascript` | 50 | 0/50 = 0.000 | 1/50 = 0.020 | +0.020 | n/a (base 0) | +1 / −0 | 1.0 |
| `multiple` | 200 | 58/200 = 0.290 | 79/200 = 0.395 | **+0.105** | **+36.2%** | +26 / −5 | **1.9e-4** |
| `parallel` | 200 | 4/200 = 0.020 | 3/200 = 0.015 | −0.005 | −25.0% | +0 / −1 | 1.0 |
| `parallel_multiple` | 200 | 1/200 = 0.005 | 3/200 = 0.015 | +0.010 | +200.0% | +2 / −0 | 0.5 |
| **pooled, excluding `simple_python`** | 750 | 68/750 = 0.091 | 94/750 = 0.125 | +0.035 | +38.2% | +34 / −8 | 6.9e-5 |
| pooled, all six (includes edit-tuning practice items) | 1150 | 224/1150 = 0.195 | 329/1150 = 0.286 | +0.091 | +46.9% | | |

- "AST acc" = official bfcl-eval per-entry AST verdict, scored after the repo's `[...]` extraction (the same protocol as the WSP holdout numbers). Scoring the untouched completion with the official decode gives **the same numbers in every cell** (`ast_accuracy_raw` in each summary).
- **delta (abs)** = edited − base accuracy (percentage points as a fraction). **relative %** = `(edited − base) / base`, i.e. gain or loss relative to the base model's score; `n/a` when base is exactly 0. Near-floor categories (Java, JS, parallel*) can show large relative swings from tiny absolute moves — trust the absolute delta and McNemar p there.
- Paired flips: items wrong for base and right for edited (+), and the reverse (−). The p-value is a two-sided exact binomial test on those flips (McNemar).
- Reading the `simple_python` row: the full-category figure mixes 300 items the editor tuned on with the 100 sealed holdout items. **Only the holdout row is a clean generalization number for `simple_python`.**
- **Reproduction check:** base and edited `simple_python` reproduce the documented WSP numbers exactly (practice 123 → 185, holdout 33 → 50). All 100 edited holdout completions are character-identical to the stored `bfcl-holdout-edited-*` generations, so the new CLI uses the same protocol.

## What transferred, and what didn't

Completion-level counts (base → edited), all items per category:

| category | fused paren openings `('` `("` `([` `((` | `math.factorial` demo copied | other system-prompt demo copied |
|---|---:|---:|---:|
| `simple_python` | 81 → 0 | 4 → 2 | 0 → 2 |
| `simple_java` | 2 → 2 | 0 → 0 | **28 → 35** |
| `simple_javascript` | 11 → 2 | 0 → 0 | 0 → 0 |
| `multiple` | 36 → 0 | 2 → 0 | 0 → 0 |
| `parallel` | 6 → 0 | 6 → 3 | 0 → 1 |
| `parallel_multiple` | 22 → 0 | 16 → 2 | 9 → 2 |

- **Edit #1 (fused parens, `down_proj` L16–31) generalizes across formats.** Fused openings disappear in every Python-format category. On `multiple`, `missing_required` errors fall 34 → 9: the base model often wrote positional args (`store_price('Assassins Creed…', 'PlayStation', …)`), and the edited model writes named ones. That is most of the `multiple` gain.
- **Edit #2 (anti-copying of the `math.factorial` demo) is specific to that demo.** It cuts `math.factorial` copying (e.g. parallel_multiple 16 → 2) but not copying of *other* demos. In Java, copying of the Java prompt's example (`ReportBuilder.export` / `TextIndex.search`) **rises** 28 → 35, and Java `wrong_func_name` goes 40 → 49. This is a real small negative side-effect, masked in the accuracy column because Java accuracy is near zero anyway.
- **Parallel calling is untouched.** `parallel_function_checker_no_order:wrong_count` is 171/200 for **both** models on `parallel`; on `parallel_multiple` it is 99 → 121 (fewer decode failures, but still one call where 2+ are needed). The edits fix call *syntax*, not the decision to emit several calls, and they were never targeted at it.
- **JavaScript is at floor for both.** The model writes JS function *definitions* (`function validateUserInput(...) {...}`) instead of a call, even with an explicit "do not define" rule: 35–36/50 are `decoder_wrong_output_format`.
- `multiple` losses (5) include a choice of a different function (e.g. `recipe_search` → `ingredient_replace`), a dropped `)` and a repeated list element. These are small amounts of noise, not a systematic regression.

## Protocol

- **Data / scorer:** `bfcl-eval==2025.10.27.1`, `BFCL_v4_<category>.json` + `possible_answer/BFCL_v4_<category>.json`. Per item, scoring runs bfcl-eval's own `eval_runner._evaluate_single_ast_entry` with an OSS-prompting decode (`default_decode_ast_prompting`). Language and return format match `ast_file_runner` (Java → tree-sitter Java parser, JS → tree-sitter JS parser, else Python). `ast_checker` dispatches to the simple, `multiple` or `parallel_no_order` checker by category, exactly as upstream. As in `evaluate_task`, the checker sees function docs **without** language hints.
- **Model:** `models/SmolLM2-360M-Instruct`, fp32, CPU (4 cores), greedy decoding, batch 1. Edited = base + `load_state_dict(strict=True)` of `artifacts/wsp_sessions/wsp-bfcl-p100-20261105T143615Z/export/edited_state.pt` (`current4`).
- **Prompt (`--prompt-style card`, the repo's protocol):** a short system prompt with format rules and two demos, plus a compact "function card" in the user turn. `simple_python` is byte-identical to `bfcl_simple_eval.py`. Adaptations:
  - Java/JS: Java/JS literal rules and Java/JS demos. Cards show the raw parameter type with the **official** generation-side description hints ("This is Java boolean type parameter in string representation", etc.).
  - `multiple`: lists every candidate function as `Function i of N` cards and asks for exactly one call.
  - `parallel` / `parallel_multiple`: asks for all calls inside one bracketed list.
  - The same prompt is used for base and edited. Prompts were fixed once, after a 6-item smoke run surfaced template bugs (bracket-style numbering, copyable `function_a` placeholders); there was no further tuning.
- `max_new_tokens`: 128 (simple, multiple), 256 (parallel*).
- **Official BFCL system prompt:** `--prompt-style bfcl` (JSON function dump, `system_prompt_pre_processing_chat_model`) is implemented but was **not** run at full scale. In a 6-item/category smoke run, base scored 1/36: the model writes prose, Python code or echoes the JSON schema, so the comparison would be all floor.
- Wall-clock: base 3181 s, edited 3072 s for all six categories. Per-category times vary both ways and were partly concurrent with diagnostics, so they aren't a latency comparison.

## Caveats

- This is **not** BFCL leaderboard parity. It uses a custom prompt protocol (not the official prompt), a non-official `[...]` extraction (which happens to change nothing here), and only six non-live AST categories.
- Java/JS absolute numbers are depressed by demo copying and code-writing. They tell you little about Java/JS *ability*, only that both models fail similarly.
- There are near-zero baselines on JS, `parallel` and `parallel_multiple`. "No change" there means "no room to measure", not "robust".
- All results are single greedy runs on one checkpoint pair.

## Skipped categories (out of scope for this pass)

| category family | why skipped |
|---|---|
| `live_*` (live_simple, live_multiple, live_parallel, …) | user-contributed live data with different prompts/distribution; separate pass |
| `multi_turn_*` | needs the stateful multi-turn executor and environments, not a single-shot AST check |
| `irrelevance` / `relevance` (incl. live) | scored by abstention / any-call checks, not `ast_checker`; needs a separate prompt contract |
| `web_search`, `memory_*` (agentic) | need tool backends / external APIs and multi-step runners |
| `format_sensitivity` | sweeps prompt formats; large cost and measures prompt robustness rather than the edit |
| `exec_*` / `rest` variants | not part of the v4 scored set (shipped only under `data/unused_datasets/`); executable checks need runtimes |

## Files

- CLI: `experiments/tool_schema/bfcl_category_eval.py` · runner: `experiments/tool_schema/run_bfcl_crossfmt.sh` · table: `experiments/tool_schema/bfcl_crossfmt_table.py`
- Per run: `crossfmt-{base,edited}_<category>_latest.summary.json` and timestamped `*.summary.json` / `*.generations.jsonl` (per-item verdict, official `error_type`, completion), all in this directory.
- Logs: `crossfmt_logs/` · diary: `experiments/tool_schema/wsp/results/CROSSFMT_RUNNING_LOG.md`

Reproduce:

```bash
experiments/tool_schema/run_bfcl_crossfmt.sh            # base then edited, all six (~55 min each on 4 CPU cores)
python3 experiments/tool_schema/bfcl_crossfmt_table.py  # prints the tables above
# single category / slice:
python3 experiments/tool_schema/bfcl_category_eval.py --category multiple --limit 20 --tag try \
  [--edited-state artifacts/wsp_sessions/wsp-bfcl-p100-20261105T143615Z/export/edited_state.pt]
```
