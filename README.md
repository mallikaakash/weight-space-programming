# weight-space-programming

Experiments on editing small LMs (starting with **SmolLM2-360M-Instruct**) toward specialized skills — beginning with **JSON tool-schema calling**.

Also includes a Claude Code + Cursor orchestrator workflow. See [docs/ORCHESTRATION.md](docs/ORCHESTRATION.md).

## Tool-schema baseline (Phase 0)

```bash
pip install -r experiments/tool_schema/requirements.txt
python3 experiments/tool_schema/build_eval.py
python3 experiments/tool_schema/download_model.py   # -> gitignored models/
python3 experiments/tool_schema/benchmark.py --tag base
```

Details: [experiments/tool_schema/README.md](experiments/tool_schema/README.md).

Latest baseline summary: [experiments/tool_schema/results/base_latest.summary.json](experiments/tool_schema/results/base_latest.summary.json).

## WSP harness (prep for next run)

```bash
python3 experiments/tool_schema/wsp/test_harness.py
python3 experiments/tool_schema/wsp/cli.py smoke-edit --budget 5 --forward-n 3
```

Details: [experiments/tool_schema/wsp/README.md](experiments/tool_schema/wsp/README.md).

## Orchestrator (optional)

1. Edit requirements in `docs/SPEC.md`.
2. Set secrets in `.env` (see `.env.example`) and in Cursor Cloud Agent secrets for cloud runs.
3. `cd scripts/orchestrator && npm install && npm run start:local` (local) or `npm start` (cloud).
