# weight-space-programming

We took a small open model (**SmolLM2-360M-Instruct**) that was mediocre at writing Python tool calls, and improved it by **editing a few of its weight matrices directly** — no fine-tuning, no gradients, no extra training data beyond looking at practice failures.

The idea is from [Sparks of Weight-Space Programming](https://rikiyat.github.io/blog/weight-space-programming/) (Takehi et al.): give an editor model a budgeted number of forward passes on practice examples, let it propose tiny weight changes, keep what helps, throw out what doesn’t.

This repo is the harness + the first real BFCL run of that loop.

---

## What we did (plain version)

1. Pick a benchmark people already trust for tool calling: **Berkeley Function-Calling Leaderboard (BFCL) v4**, category **`simple_python` only**.
2. Split its 400 official items into **300 practice** + **100 sealed holdout**.
3. Run Claude Opus 5.5 (high thinking) as the editor for **100 metered practice forwards**. It never saw the holdout while editing.
4. It found three recurring bugs in the small model’s outputs, wrote three small weight edits for them, stacked them into a recipe we call **`current4`**, and exported the weights.
5. Then we unsealed the holdout and scored with the official BFCL AST checker.

**Result:** practice **41% → 62%**. Sealed holdout **33% → 50%**.

### What the gains actually were

The dump, short version: gains were **primarily from fixing formatting bottlenecks** — learning a better **policy for how to write a call** (named args, don’t fuse `('…`, don’t parrot the prompt’s `math` demo, prefer `True` on flags).

That is **not**:
- new knowledge infused into the small model, or
- an emergent ability the base never had, or
- a clear cleanup of the **semantic leftover** (wrong values, wrong/mangled names, bad optional-arg choices) that was already failing before any edits.

So WSP here worked as **expression surgery** on errors the model was already close to getting right — not as a way to pour BFCL facts or broader tool skill into SmolLM2.

That is the whole story. Details below.

---

## Dataset and scope

### What BFCL piece we used

| | |
|---|---|
| Benchmark | **BFCL v4** |
| Category | **`simple_python` only** (AST Simple / Python) |
| Package | `bfcl-eval==2025.10.27.1` |
| Official files | `BFCL_v4_simple_python.json` + matching `possible_answer/` |
| Scorer | official `bfcl_eval.ast_checker` |
| **Not in scope** | multiple calls, parallel calls, live APIs, multi-turn, other BFCL categories |

Every item is the same task type: user asks for something → model must emit **one** Python-style call like:

```text
[calculate_triangle_area(base=10, height=5)]
```

with the right function name, named arguments, and values. Always **one function schema per item**.

### Our split (file order, not a new taxonomy)

| Split | IDs | n | Role |
|-------|-----|---|------|
| Practice | `simple_python_0` … `299` | **300** | Editor can see these |
| Holdout | `simple_python_300` … `399` | **100** | Sealed until budget is done |

Both halves are the **same** BFCL category. The holdout is just the last 100 items in the official list.

Inside that, content varies (math, music, sports, restaurants, weather, …). Rough shape:

| | Practice (300) | Holdout (100) |
|---|---|---|
| Unique gold function names | 277 | 94 |
| Dotted names (`math.factorial`, …) | 115 | 51 |
| Items with optional params | 203 | 70 |
| Name overlap between splits | 1 (`detailed_weather_forecast`) | |

So we did **not** train on “sports vs math” as separate tasks. We edited for format bugs that show up across the category, then checked generalization on held-out items from the same category.

---

## Results (verified from artifacts)

Session `wsp-bfcl-p100-20261105T143615Z` · budget **100/100** · editor Claude Opus 5.5 high thinking.

| Split | Base | After `current4` | Paired |
|-------|------|------------------|--------|
| Practice (300) | **123 / 300 = 0.410** | **185 / 300 = 0.617** | **+69 / −7** |
| Practice DEV half (150) | 61 | 93 | — |
| Practice CONF half (150) | 62 | 92 | — |
| **Holdout (100, sealed)** | **33 / 100 = 0.33** | **50 / 100 = 0.50** | **+19 / −2** |

On holdout, fused paren openings like `('` / `("` / `(['` went from **24 completions → 0**.

**Sources in this repo:**
- `experiments/tool_schema/results/bfcl/bfcl-holdout-*-latest.summary.json` (+ matching `*.generations.jsonl`)
- Diary: `experiments/tool_schema/wsp/results/RUNNING_LOG.md`
- Edit ledger (no tensors): `experiments/tool_schema/results/bfcl/wsp-bfcl-p100-20261105T143615Z/edits.json`

### Cross-format probe (other BFCL categories)

Does `current4` (tuned only on `simple_python` practice) carry over to other BFCL v4 **non-live AST** categories? We ran base vs edited on the full category sets, using the same prompt protocol and the official per-entry AST scorer. Eval only.

| category | n | base | edited | delta |
|---|---:|---:|---:|---:|
| `simple_python` holdout (300–399) | 100 | 0.330 | 0.500 | +0.170 |
| `simple_java` | 100 | 0.050 | 0.080 | +0.030 (n.s.) |
| `simple_javascript` | 50 | 0.000 | 0.020 | +0.020 (n.s.) |
| `multiple` | 200 | 0.290 | **0.395** | **+0.105** (+26/−5, p≈2e-4) |
| `parallel` | 200 | 0.020 | 0.015 | −0.005 (n.s.) |
| `parallel_multiple` | 200 | 0.005 | 0.015 | +0.010 (n.s.) |

The fused-parenthesis fix transfers (it drives the `multiple` gain). Java, JS and parallel calling stay near the floor for both models, and no category regresses significantly. One small side-effect: copying of the Java prompt's demo rises (28 → 35 completions). Live, multi-turn, irrelevance, web_search, memory and format_sensitivity were skipped. **Not** a leaderboard result.

Full table, paired flips, failure analysis and protocol: [`experiments/tool_schema/results/bfcl/CROSSFMT_BASE_VS_EDITED.md`](experiments/tool_schema/results/bfcl/CROSSFMT_BASE_VS_EDITED.md).

---

## What we changed in the model

No training run. We touched **32 late weight tensors** on SmolLM2-360M-Instruct (`o_proj` / `down_proj` in layers 16–31). Embeddings, `lm_head`, and final norm stayed untouched.

Three edits, one per bug:

1. **Stop mangled parentheses** (`down_proj`, layers 16–31)  
   Base often started args with fused tokens like `('Alice'…)` instead of `(` then `name=…`. We removed the late-MLP wiring that pushes those fused tokens. Biggest win.

2. **Stop copying the `math` demo from the prompt** (`o_proj` + `down_proj`, layers 16–31, milder strength)  
   The system prompt shows `[math.factorial(number=5)]`. The model kept pasting that pattern. We weakened that habit without killing real `math.*` tools.

3. **Prefer `True` for boolean flags** (`o_proj` + `down_proj`, layers 24–31)  
   Flags like `avoid_tolls` / `equal_variance` were often left unset. We tilted “this looks boolean” toward writing `True`.

Together that stack is **`current4`**. Lots of other ideas were tried in the 100 passes and rejected (space-in-name fixes, force more `=`, an older edit from a previous run, etc.) because they helped a few items and broke others.

**How we found which weights / how much:** look at failures → guess a mechanism → try a small edit → score on practice → keep, dial, or discard. Dose and layer were chosen by small grids around a default (e.g. math strength 1.0 was too strong; 0.5 stuck). Holdout stayed sealed the whole time.

---

## Reproduce the holdout numbers

```bash
python3 experiments/tool_schema/download_model.py

# Base holdout
python3 experiments/tool_schema/bfcl_simple_eval.py \
  --offset 300 --limit 100 \
  --tag bfcl-holdout-base-repro

# Edited holdout (needs edited weights — see Hosting)
python3 experiments/tool_schema/bfcl_simple_eval.py \
  --offset 300 --limit 100 \
  --edited-state /path/to/edited_state.pt \
  --tag bfcl-holdout-edited-repro
```

Runners: `experiments/tool_schema/wsp/run_editor_bfcl_native.sh`, `run_editor_bfcl_resume.sh`.

---

## Hosting the edited weights

Full checkpoints live under gitignored `artifacts/`:

```text
artifacts/wsp_sessions/wsp-bfcl-p100-20261105T143615Z/export/
  edited_state.pt   # full state_dict ≈ 1.6GB
  edits.json        # ledger (also committed — see below)
  current4_delta.pt # optional packed 32-tensor delta ≈ 216MB
```

**On GitHub already (metadata only):**  
`experiments/tool_schema/results/bfcl/wsp-bfcl-p100-20261105T143615Z/edits.json`

That file lists every edit event (`name`, which matrix, timestamp, size, note) and the final 32 `changed_params`. It does **not** contain weight values.

### Prefer hosting the ~216MB delta

Only 32 tensors differ from `HuggingFaceTB/SmolLM2-360M-Instruct`. Pack → upload → apply on top of the base model:

```bash
python3 experiments/tool_schema/wsp/pack_edited_delta.py pack \
  --edited-state artifacts/wsp_sessions/wsp-bfcl-p100-20261105T143615Z/export/edited_state.pt \
  --edits-json   experiments/tool_schema/results/bfcl/wsp-bfcl-p100-20261105T143615Z/edits.json \
  --out          artifacts/wsp_sessions/wsp-bfcl-p100-20261105T143615Z/export/current4_delta.pt \
  --session-id   wsp-bfcl-p100-20261105T143615Z \
  --recipe       current4

# Consumer
python3 experiments/tool_schema/download_model.py
python3 experiments/tool_schema/wsp/pack_edited_delta.py apply \
  --delta /path/to/current4_delta.pt \
  --model-dir models/SmolLM2-360M-Instruct \
  --out /tmp/edited_state.pt
```

| Option | Upload | Notes |
|--------|--------|-------|
| **Hugging Face Hub** | `current4_delta.pt` | Best default for weights |
| **GitHub Release asset** | same delta on a tag | Fine for a one-shot release |
| Full `edited_state.pt` | 1.6GB | Only if you need a drop-in state_dict |

```bash
huggingface-cli upload <you>/smollm2-360m-bfcl-current4 \
  artifacts/wsp_sessions/wsp-bfcl-p100-20261105T143615Z/export/current4_delta.pt \
  current4_delta.pt
```

Until someone publishes a public URL, the local `artifacts/.../export/` path on the run machine is the source of truth for the actual tensors.

---

## Earlier work (pre-BFCL)

Before pivoting to BFCL we used a homemade JSON tool-schema set (40 train / 20 test). Base test `strict_ok` was **20%**; a short first editor run did not move it. That history is still in `RUNNING_LOG.md` and `experiments/tool_schema/results/`. Headline now is BFCL.

---

## Repo layout

| Path | Role |
|------|------|
| `experiments/tool_schema/` | Eval, scorers, BFCL + legacy tool-schema benches |
| `experiments/tool_schema/wsp/` | WSP harness, BFCL runners, editor prompts |
| `experiments/tool_schema/wsp/pack_edited_delta.py` | Pack/apply compact edited-weight deltas for hosting |
| `experiments/tool_schema/results/bfcl/` | Holdout scores, generations, + `edits.json` |
| `models/` | Local base weights (**gitignored**) |
| `artifacts/` | Sessions + full `edited_state.pt` (**gitignored**) |
| `docs/SPEC.md` | Spec for Claude Code / orchestrator builds |
| `docs/ORCHESTRATION.md` | Claude Code ↔ Cursor orchestrator |

---

## Setup

```bash
pip install -r experiments/tool_schema/requirements.txt
python3 experiments/tool_schema/build_eval.py
python3 experiments/tool_schema/download_model.py   # ~700MB → models/
python3 experiments/tool_schema/wsp/build_bfcl_split.py   # 300/100 split
```

### WSP harness smoke

```bash
python3 experiments/tool_schema/wsp/test_harness.py
```

### Start BFCL-native weight-space editor (Claude Code)

```bash
bash experiments/tool_schema/wsp/run_editor_bfcl_native.sh
# resume after interrupt:
# bash experiments/tool_schema/wsp/run_editor_bfcl_resume.sh
# logs: experiments/tool_schema/wsp/results/RUNNING_LOG.md
#      artifacts/wsp_sessions/<id>/
```

Requires `CLAUDE_CODE_OAUTH_TOKEN` (or local `claude` auth). See `experiments/tool_schema/wsp/editor/`.

---

## Scoring

- **BFCL (headline):** official AST via `bfcl_eval.ast_checker` (`bfcl_simple_eval.py`, `wsp/bfcl_score.py`).
- **Legacy tool-schema:** `strict_ok` = parse ∧ tool ∧ args ∧ required keys ∧ types ∧ values ∧ no hallucinated keys — see [experiments/tool_schema/README.md](experiments/tool_schema/README.md).

---

## Orchestrator (optional)

Spec-driven Claude implementer + Cursor monitor: [docs/ORCHESTRATION.md](docs/ORCHESTRATION.md).
