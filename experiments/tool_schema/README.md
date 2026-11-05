# Tool-schema specialization probe (SmolLM2-360M)

Phase 0: download **SmolLM2-360M-Instruct**, run a tiny tool-call / JSON-schema eval, record the baseline before any weight editing.

Weights live under gitignored `models/` (cloud VM disk / HF cache). Do **not** commit them.

## Setup

```bash
pip install -r experiments/tool_schema/requirements.txt
python3 experiments/tool_schema/build_eval.py
python3 experiments/tool_schema/download_model.py
```

## Baseline benchmark

```bash
python3 experiments/tool_schema/benchmark.py --tag base
# smoke:
python3 experiments/tool_schema/benchmark.py --tag smoke --limit 5
```

Results: `artifacts/baselines/tool_schema_*`.

## Scoring

Primary metric: **`strict_ok`** — parseable JSON object with correct `tool`, required argument keys, types, and values.

Also reported: `parse_ok`, `tool_ok`, per-tier rates (`easy` / `medium` / `hard`).
