# Tool-schema specialization probe (SmolLM2-360M)

Phase 0: download **SmolLM2-360M-Instruct**, run a tiny tool-call / JSON-schema eval, record the baseline before any weight editing.

Weights live under gitignored `models/` (cloud VM disk / HF cache). Do **not** commit them.

## Setup

```bash
pip install -r experiments/tool_schema/requirements.txt
python3 experiments/tool_schema/build_eval.py
python3 experiments/tool_schema/download_model.py
```

## Train/test split

`build_eval.py` assigns each example a frozen `"split"` (deterministic, no RNG: within each tier, 1-indexed `i % 3 == k`), giving 40 train / 20 test, stratified by tier (easy 14/6, medium 13/7, hard 13/7). Ids are listed in `eval/splits.json`. **Reported headline metrics use `--split test`.**

## Baseline benchmark

```bash
python3 experiments/tool_schema/benchmark.py --split test --tag base-test   # headline
python3 experiments/tool_schema/benchmark.py --split {all,train,test} --tag base
# smoke:
python3 experiments/tool_schema/benchmark.py --tag smoke --limit 5
```

Full outputs: `artifacts/baselines/tool_schema_*` (gitignored). Checked-in headline summary: `results/base_latest.summary.json` (split `test`).

## Stability and spot-check

```bash
python3 experiments/tool_schema/stability.py   # 3 greedy runs on test -> results/stability.json
python3 experiments/tool_schema/spotcheck.py   # 10-15 failures -> results/spotcheck.md
python3 experiments/tool_schema/test_score.py  # scorer unit tests
```

## Scoring

Primary metric: **`strict_ok`** — parseable JSON object with correct `tool`, required argument keys, no hallucinated keys (`no_hallucinated_keys`: `arguments` has no keys beyond the gold set), types, and values.

Also reported: `parse_ok`, `tool_ok`, `no_hallucinated_keys`, per-tier rates (`easy` / `medium` / `hard`).

## WSP harness (prep)

Weight store + guarded edits + train practice + metered forward passes:

See [wsp/README.md](wsp/README.md).

```bash
python3 experiments/tool_schema/wsp/test_harness.py
python3 experiments/tool_schema/wsp/cli.py smoke-edit --budget 5 --forward-n 3
```

Editor-agent WSP loop is **not** started here — next run.
