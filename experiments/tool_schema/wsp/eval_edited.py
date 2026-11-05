#!/usr/bin/env python3
"""Score an exported WSP session on the tool-schema test split."""
from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

import torch
from transformers import AutoModelForCausalLM, AutoTokenizer

EXPERIMENT_ROOT = Path(__file__).resolve().parents[1]
REPO_ROOT = EXPERIMENT_ROOT.parents[1]
sys.path.insert(0, str(EXPERIMENT_ROOT))

from benchmark import load_examples, run_benchmark  # noqa: E402
from paths import MODEL_DIR, MODEL_ID  # noqa: E402


def main() -> int:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--session-dir", type=Path, required=True)
    p.add_argument("--model-dir", type=Path, default=MODEL_DIR)
    p.add_argument("--split", default="test")
    p.add_argument("--tag", default="wsp-edited")
    p.add_argument("--max-new-tokens", type=int, default=128)
    args = p.parse_args()

    edited_path = args.session_dir / "export" / "edited_state.pt"
    if not edited_path.exists():
        alt = args.session_dir / "edited_state.pt"
        if alt.exists():
            edited_path = alt
    if not edited_path.exists():
        print(f"Missing edited state at {edited_path}", file=sys.stderr)
        return 1

    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    dtype = torch.bfloat16 if device.type == "cuda" else torch.float32
    print(f"Loading base {args.model_dir} + {edited_path} on {device}", flush=True)
    tokenizer = AutoTokenizer.from_pretrained(args.model_dir)
    model = AutoModelForCausalLM.from_pretrained(args.model_dir, torch_dtype=dtype)
    state = torch.load(edited_path, map_location="cpu", weights_only=True)
    model.load_state_dict(state, strict=True)
    model.to(device)
    model.eval()

    examples = load_examples(args.split)
    summary = run_benchmark(
        model,
        tokenizer,
        device,
        examples,
        tag=args.tag,
        split=args.split,
        model_dir=args.model_dir,
        max_new_tokens=args.max_new_tokens,
        temperature=0.0,
    )
    summary["session_dir"] = str(args.session_dir)
    summary["edited_state"] = str(edited_path)
    summary["model_id"] = MODEL_ID
    summary["baseline_test_strict_ok"] = 0.2
    summary["timestamp"] = datetime.now(timezone.utc).isoformat()

    out_dir = Path(__file__).resolve().parent / "results"
    out_dir.mkdir(parents=True, exist_ok=True)
    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    (out_dir / f"edited_{args.tag}_{stamp}.summary.json").write_text(
        json.dumps(summary, indent=2), encoding="utf-8"
    )
    (out_dir / "edited_test_latest.summary.json").write_text(
        json.dumps(summary, indent=2), encoding="utf-8"
    )
    print(json.dumps(summary, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
