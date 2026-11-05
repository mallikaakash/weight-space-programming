#!/usr/bin/env python3
"""Run the test-split benchmark 3x (greedy) with one loaded model; write results/stability.json."""
from __future__ import annotations

import json
import subprocess
import sys

from paths import EXPERIMENT_ROOT, MODEL_DIR

RUNS = 3
OUT = EXPERIMENT_ROOT / "results" / "stability.json"


def main() -> int:
    if not MODEL_DIR.exists():
        subprocess.check_call([sys.executable, str(EXPERIMENT_ROOT / "download_model.py")])

    from benchmark import load_examples, load_model, run_benchmark

    model, tokenizer, device = load_model(MODEL_DIR)
    examples = load_examples("test")
    runs = []
    for r in range(1, RUNS + 1):
        s = run_benchmark(
            model, tokenizer, device, examples,
            tag=f"stability-r{r}", split="test", model_dir=MODEL_DIR, temperature=0.0,
        )
        runs.append({k: s[k] for k in ("tag", "n", "strict_ok", "parse_ok", "tool_ok", "no_hallucinated_keys", "timestamp")})
    strict = [r["strict_ok"] for r in runs]
    out = {
        "split": "test",
        "temperature": 0.0,
        "runs": runs,
        "strict_ok_range": max(strict) - min(strict),
    }
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(out, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(out, indent=2))
    return 0


if __name__ == "__main__":
    sys.exit(main())
