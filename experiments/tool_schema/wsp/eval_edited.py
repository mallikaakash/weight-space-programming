#!/usr/bin/env python3
"""Score an exported WSP session on the sealed tool-schema test split.

exp8: evaluation happens after the run, never shown to the editor during the run.
This script refuses unless the session forward budget is exhausted (or --force).
"""
from __future__ import annotations

import argparse
import json
import os
import sys
from datetime import datetime, timezone
from pathlib import Path

import torch
from transformers import AutoModelForCausalLM, AutoTokenizer

EXPERIMENT_ROOT = Path(__file__).resolve().parents[1]
REPO_ROOT = EXPERIMENT_ROOT.parents[1]
sys.path.insert(0, str(EXPERIMENT_ROOT))

from benchmark import run_benchmark  # noqa: E402
from paths import MODEL_DIR, MODEL_ID  # noqa: E402
from wsp.leakage_guard import assert_forward_log_train_only, budget_exhausted  # noqa: E402
from wsp.paths_wsp import SEALED_TEST_PATH  # noqa: E402
from wsp.practice import load_jsonl  # noqa: E402


def main() -> int:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--session-dir", type=Path, required=True)
    p.add_argument("--model-dir", type=Path, default=MODEL_DIR)
    p.add_argument("--split", default="test")
    p.add_argument("--tag", default="wsp-edited")
    p.add_argument("--max-new-tokens", type=int, default=128)
    p.add_argument(
        "--force",
        action="store_true",
        help="Bypass budget-exhausted gate (operator only; not for the editor).",
    )
    args = p.parse_args()

    if args.split != "test":
        print("eval_edited.py is for the sealed test split only", file=sys.stderr)
        return 2

    # Editor must not unseal during a locked run.
    if os.environ.get("WSP_LOCK_TEST", "0") == "1" and not args.force:
        print(
            "Refused: WSP_LOCK_TEST=1. Test eval is sealed until the long run finishes.",
            file=sys.stderr,
        )
        return 3

    if not args.force and not budget_exhausted(args.session_dir):
        print(
            "Refused: forward budget not exhausted. "
            "Continue editing until all passes are used (exp8), then re-run; "
            "or pass --force as the human operator after the run.",
            file=sys.stderr,
        )
        return 4

    leak = assert_forward_log_train_only(args.session_dir)
    if not leak["ok"]:
        print(
            f"Refused: forward log leakage detected: {leak}",
            file=sys.stderr,
        )
        return 5

    edited_path = args.session_dir / "export" / "edited_state.pt"
    if not edited_path.exists():
        alt = args.session_dir / "edited_state.pt"
        if alt.exists():
            edited_path = alt
    if not edited_path.exists():
        print(f"Missing edited state at {edited_path}", file=sys.stderr)
        return 1

    # Prefer sealed test; fall back to quarantine path outside the repo.
    test_path = SEALED_TEST_PATH
    alt_q = Path(os.environ.get("WSP_SEAL_DIR", "/tmp/wsp_seal")) / "test.jsonl"
    if not test_path.exists() and alt_q.exists():
        test_path = alt_q
    if not test_path.exists():
        print(f"Missing sealed test at {SEALED_TEST_PATH} and {alt_q}", file=sys.stderr)
        return 1

    examples = load_jsonl(test_path)
    if not examples:
        print("Sealed test is empty", file=sys.stderr)
        return 1
    for ex in examples:
        ex.setdefault("split", "test")

    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    dtype = torch.bfloat16 if device.type == "cuda" else torch.float32
    print(f"Loading base {args.model_dir} + {edited_path} on {device}", flush=True)
    tokenizer = AutoTokenizer.from_pretrained(args.model_dir)
    model = AutoModelForCausalLM.from_pretrained(args.model_dir, torch_dtype=dtype)
    state = torch.load(edited_path, map_location="cpu", weights_only=True)
    model.load_state_dict(state, strict=True)
    model.to(device)
    model.eval()

    summary = run_benchmark(
        model,
        tokenizer,
        device,
        examples,
        tag=args.tag,
        split="test",
        model_dir=args.model_dir,
        max_new_tokens=args.max_new_tokens,
        temperature=0.0,
    )
    summary["session_dir"] = str(args.session_dir)
    summary["edited_state"] = str(edited_path)
    summary["model_id"] = MODEL_ID
    summary["baseline_test_strict_ok"] = 0.2
    summary["sealed_test_path"] = str(test_path)
    summary["leakage_check"] = leak
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
