# weight-space-programming

Edit small LMs in **weight space** (no gradient descent / no fine-tuning) toward a specialized skill.

**Current headline target:** [BFCL](https://gorilla.cs.berkeley.edu/blogs/15_bfcl_v4_web_search.html) v4 `simple_python` AST tool calling on **SmolLM2-360M-Instruct**, using a Claude Code editor + local metered harness (Takehi Experiment-8 style).

Inspired by [Sparks of Weight-Space Programming](https://rikiyat.github.io/blog/weight-space-programming/) (Takehi et al.).

---

## Headline result (BFCL-native, verified)

Session: `wsp-bfcl-p100-20261105T143615Z`  
Editor: Claude Opus 5.5, `--effort high`  
Budget: **100 / 100** metered practice forwards  
Split: practice **300** (`simple_python_0`…`299`) / sealed holdout **100** (`300`…`399`)  
Scorer: official `bfcl_eval.ast_checker` (AST accuracy)

### Numbers re-checked from artifacts

| Split | Base | Edited (`current4`) | Paired |
|-------|------|---------------------|--------|
| Practice (300) | **123 / 300 = 0.410** | **185 / 300 = 0.617** | **+69 / −7** |
| Practice DEV half (150) | 61 | 93 | — |
| Practice CONF half (150) | 62 | 92 | — |
| **Holdout (100, sealed during edit)** | **33 / 100 = 0.33** | **50 / 100 = 0.50** | **+19 / −2** |

Holdout merged-paren family tokens in completions (`('`, `("`, `(['`, `([`): **base 24 → edited 0**.

**Sources (in-repo):**
- Holdout summaries: `experiments/tool_schema/results/bfcl/bfcl-holdout-base-pre-wsp-bfcl-p100-20261105T143615Z_latest.summary.json`, `…/bfcl-holdout-edited-wsp-bfcl-p100-20261105T143615Z_latest.summary.json`
- Holdout generations: matching `*.generations.jsonl` next to those summaries
- Practice paired confirmation: session forward log + `RUNNING_LOG.md` pass 100 (byte-identical to pass 37)
- Full diary: `experiments/tool_schema/wsp/results/RUNNING_LOG.md`

### What `current4` is (the exported edit)

Three closed-form edits on late weights only (**32 tensors**). No changes to embeddings, `lm_head`, or final norm.

1. **Merged-paren family projection** — `mlp.down_proj`, layers **16–31**, strength β=1  
   Removes late-MLP writes that push fused tokens like `('`, `("`, `(['`, …  
   Stops positional “paren stuck to value” openings; forces normal `(` then `name=`.  
   Largest effect (~+44 practice items in leave-one-component checks recorded in the run log).

2. **System-example `math` projection** — `o_proj` + `down_proj`, layers **16–31**, β=0.5  
   Weakens copying of the prompt demo `[math.factorial(number=5)]` while keeping real `math.*` tools.  
   (~+16 in the same leave-one-component checks.)

3. **Bool shear** — `o_proj` + `down_proj`, layers **24–31**, α=1  
   When the residual looks “boolean”, tilt writes toward `True` (flags like `equal_variance`, `avoid_tolls`).  
   (~+8.)

Edits are built so a large set of common / code tokens keep unchanged logits (“protected”), and only the targeted directions move.

### How the recipe was found (investigation trace)

Not by training. An editor got **100** practice-only forward passes (holdout sealed with `WSP_LOCK_TEST=1`).

1. **Fail taxonomy** on base completions → fused paren openings, `math` prompt-copy, missing `True` flags.  
2. **Hypothesis → tiny weight edit → score** on practice (often DEV first, then all 300 / CONF).  
3. **Dose / layer / matrix localization** (e.g. family effect lives in late **MLP `down_proj`**, not attention-only).  
4. **Stack** into `current4`, then **reject** further ideas that were net-flat or harmful (space-in-name fixes, eq-boost / eq-dual, prior p50 `v_proj` damp, etc.).  
5. **Controls recorded in the run log:** random same-shape “null” edits (~0 to −5 items); specificity swaps; gold-call NLL for `current4` **0.2733 → 0.2463 (−9.9%)** on all 300 (pass 79).  
6. **Unseal holdout** only after budget exhaustion → **0.33 → 0.50**.

### Reproduce holdout scoring

```bash
# Base model (~700MB)
python3 experiments/tool_schema/download_model.py

# Base holdout (offset 300, limit 100)
python3 experiments/tool_schema/bfcl_simple_eval.py \
  --offset 300 --limit 100 \
  --tag bfcl-holdout-base-repro

# Edited holdout (needs edited weights — see Hosting below)
python3 experiments/tool_schema/bfcl_simple_eval.py \
  --offset 300 --limit 100 \
  --edited-state /path/to/edited_state.pt \
  --tag bfcl-holdout-edited-repro
```

Launchers used for the run: `experiments/tool_schema/wsp/run_editor_bfcl_native.sh`, `run_editor_bfcl_resume.sh`.

---

## Hosting the edited weights

`artifacts/` is **gitignored** (full checkpoints are large). The verified export from this run lives locally at:

```text
artifacts/wsp_sessions/wsp-bfcl-p100-20261105T143615Z/export/
  edited_state.pt   # full state_dict ≈ 1.6GB (what bfcl_simple_eval loads)
  edits.json        # edit ledger + changed_params (32 names)
```

### Recommended: publish a **delta** (~0.2GB), not the full 1.6GB

Only 32 tensors differ from base `HuggingFaceTB/SmolLM2-360M-Instruct`. Pack them, host the pack, then rebuild a full `edited_state.pt` on any machine that already has the base model:

```bash
# On the machine that has the session export
python3 experiments/tool_schema/wsp/pack_edited_delta.py pack \
  --edited-state artifacts/wsp_sessions/wsp-bfcl-p100-20261105T143615Z/export/edited_state.pt \
  --edits-json   artifacts/wsp_sessions/wsp-bfcl-p100-20261105T143615Z/export/edits.json \
  --out          artifacts/wsp_sessions/wsp-bfcl-p100-20261105T143615Z/export/current4_delta.pt \
  --session-id   wsp-bfcl-p100-20261105T143615Z \
  --recipe       current4

# Host `current4_delta.pt` (≈216MB) via one of:
#   1) Hugging Face Hub model/dataset repo (best for ML artifacts)
#   2) GitHub Release asset (good for a versioned attachment on this repo)
#   3) Any object store (S3/GCS/R2) + URL in the release notes

# Consumer machine: download base + delta, apply, eval
python3 experiments/tool_schema/download_model.py
python3 experiments/tool_schema/wsp/pack_edited_delta.py apply \
  --delta /path/to/current4_delta.pt \
  --model-dir models/SmolLM2-360M-Instruct \
  --out /tmp/edited_state.pt

python3 experiments/tool_schema/bfcl_simple_eval.py \
  --offset 300 --limit 100 \
  --edited-state /tmp/edited_state.pt \
  --tag bfcl-holdout-from-delta
```

### Hosting options (pick one)

| Option | What to upload | Pros | Cons |
|--------|----------------|------|------|
| **Hugging Face Hub** | `current4_delta.pt` (+ short model card with the table above) | Standard for weights; `hf upload` / `huggingface-cli upload` | Needs an HF token / repo |
| **GitHub Release** | Same delta as a Release asset on a tag (e.g. `bfcl-current4`) | Tied to this git history; easy link from README | 216MB asset; not ideal for frequent overwrites |
| **Full `edited_state.pt`** | 1.6GB state_dict | Drop-in for `--edited-state` | Large; prefer delta unless you must |

Example HF upload (after `huggingface-cli login`):

```bash
huggingface-cli upload <your-user>/smollm2-360m-bfcl-current4 \
  artifacts/wsp_sessions/wsp-bfcl-p100-20261105T143615Z/export/current4_delta.pt \
  current4_delta.pt
```

Example GitHub Release asset:

```bash
gh release create bfcl-current4 \
  artifacts/wsp_sessions/wsp-bfcl-p100-20261105T143615Z/export/current4_delta.pt \
  --title "BFCL current4 weight delta" \
  --notes "SmolLM2-360M-Instruct WSP current4 (32 tensors). Practice 0.410→0.617, holdout 0.33→0.50."
```

> Note: this environment’s `gh` is read-only for some write paths; create the Release from a machine/token with upload permission, or use the GitHub UI.

Until a public URL is published, treat the local `artifacts/.../export/` path as the source of truth for this agent VM.

---

## Earlier tool-schema baselines (pre-BFCL pivot)

Headline then was JSON tool-schema `strict_ok` on a 40/20 train/test split (not BFCL).

| Split | n | parse_ok | tool_ok | no_hallucinated_keys | **strict_ok** |
|-------|---|----------|---------|----------------------|---------------|
| **test (headline)** | 20 | 80% | 25% | 40% | **20%** |

First short WSP editor run on that skill did not move test `strict_ok` (still 20%). Details remain in `experiments/tool_schema/wsp/results/RUNNING_LOG.md` (pre-BFCL sections) and `experiments/tool_schema/results/`.

---

## Repo layout

| Path | Role |
|------|------|
| `experiments/tool_schema/` | Eval, scorers, BFCL + legacy tool-schema benches |
| `experiments/tool_schema/wsp/` | WSP harness, BFCL runners, editor prompts |
| `experiments/tool_schema/wsp/pack_edited_delta.py` | Pack/apply compact edited-weight deltas for hosting |
| `experiments/tool_schema/results/bfcl/` | Committed BFCL holdout summaries + generations |
| `models/` | Local base weights (**gitignored**) |
| `artifacts/` | Sessions, full `edited_state.pt` (**gitignored**) |
| `docs/SPEC.md` | Spec for Claude Code / orchestrator builds |
| `docs/ORCHESTRATION.md` | Claude Code ↔ Cursor orchestrator |

---

## Setup

```bash
pip install -r experiments/tool_schema/requirements.txt
python3 experiments/tool_schema/build_eval.py
python3 experiments/tool_schema/download_model.py   # ~700MB → models/
# BFCL practice/holdout split (300/100):
python3 experiments/tool_schema/wsp/build_bfcl_split.py
```

### WSP harness smoke

```bash
python3 experiments/tool_schema/wsp/test_harness.py
python3 experiments/tool_schema/wsp/cli.py --budget 5 --session-id demo smoke-edit --forward-n 3
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
