#!/usr/bin/env python3
"""Baseline tool-schema benchmark for SmolLM2-360M-Instruct."""
from __future__ import annotations

import argparse
import json
import os
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

import torch
from tqdm import tqdm
from transformers import AutoModelForCausalLM, AutoTokenizer

from paths import ARTIFACTS_DIR, EVAL_PATH, HF_HOME, MODEL_DIR, MODEL_ID, TOOLS_PATH
from score import score_example, summarize


def load_jsonl(path: Path) -> list[dict]:
    rows = []
    with path.open(encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line:
                rows.append(json.loads(line))
    return rows


def build_messages(ex: dict) -> list[dict[str, str]]:
    return [
        {"role": "system", "content": ex["system"]},
        {"role": "user", "content": ex["user"]},
    ]


@torch.inference_mode()
def generate_one(model, tokenizer, messages: list[dict[str, str]], max_new_tokens: int, temperature: float) -> str:
    prompt = tokenizer.apply_chat_template(messages, tokenize=False, add_generation_prompt=True)
    inputs = tokenizer(prompt, return_tensors="pt")
    inputs = {k: v.to(model.device) for k, v in inputs.items()}
    gen_kwargs = {
        "max_new_tokens": max_new_tokens,
        "pad_token_id": tokenizer.eos_token_id,
    }
    if temperature and temperature > 0:
        gen_kwargs.update(do_sample=True, temperature=temperature, top_p=0.9)
    else:
        gen_kwargs.update(do_sample=False)
    out = model.generate(**inputs, **gen_kwargs)
    new_tokens = out[0, inputs["input_ids"].shape[-1] :]
    return tokenizer.decode(new_tokens, skip_special_tokens=True).strip()


def load_model(model_dir: Path):
    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    dtype = torch.bfloat16 if device.type == "cuda" else torch.float32
    print(f"Loading {model_dir} on {device} dtype={dtype}", flush=True)
    tokenizer = AutoTokenizer.from_pretrained(model_dir)
    model = AutoModelForCausalLM.from_pretrained(model_dir, torch_dtype=dtype)
    model.to(device)
    model.eval()
    return model, tokenizer, device


def load_examples(split: str = "all", limit: int = 0) -> list[dict]:
    examples = load_jsonl(EVAL_PATH)
    if split != "all":
        examples = [e for e in examples if e.get("split") == split]
    if limit and limit > 0:
        examples = examples[:limit]
    return examples


def run_benchmark(model, tokenizer, device, examples, *, tag, split, model_dir, max_new_tokens=128, temperature=0.0) -> dict:
    """Run the eval, write artifacts, return the summary."""
    tools = json.loads(TOOLS_PATH.read_text(encoding="utf-8"))
    tools_by_name = {t["name"]: t for t in tools["tools"]}
    rows = []
    t0 = time.time()
    for ex in tqdm(examples, desc=f"benchmark[{tag}]"):
        completion = generate_one(
            model, tokenizer, build_messages(ex), max_new_tokens=max_new_tokens, temperature=temperature
        )
        scores = score_example(ex["expected"], completion, tools_by_name)
        rows.append(
            {
                "id": ex["id"],
                "tier": ex["tier"],
                "split": ex.get("split"),
                "user": ex["user"],
                "expected": ex["expected"],
                "completion": completion,
                "scores": {k: v for k, v in scores.items() if k != "parsed"},
                "parsed": scores.get("parsed"),
            }
        )
    elapsed = time.time() - t0
    summary = summarize(rows)
    summary.update(
        {
            "model_id": MODEL_ID,
            "model_dir": str(model_dir),
            "tag": tag,
            "split": split,
            "device": str(device),
            "temperature": temperature,
            "max_new_tokens": max_new_tokens,
            "elapsed_sec": round(elapsed, 2),
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }
    )

    ARTIFACTS_DIR.mkdir(parents=True, exist_ok=True)
    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    out_json = ARTIFACTS_DIR / f"tool_schema_{tag}_{stamp}.json"
    out_summary = ARTIFACTS_DIR / f"tool_schema_{tag}_{stamp}.summary.json"
    latest = ARTIFACTS_DIR / f"tool_schema_{tag}_latest.summary.json"
    out_json.write_text(json.dumps({"summary": summary, "examples": rows}, indent=2), encoding="utf-8")
    out_summary.write_text(json.dumps(summary, indent=2), encoding="utf-8")
    latest.write_text(json.dumps(summary, indent=2), encoding="utf-8")
    print(f"Wrote {out_json}", flush=True)
    return summary


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--limit", type=int, default=0, help="Optional cap on examples (0 = all)")
    parser.add_argument("--max-new-tokens", type=int, default=128)
    parser.add_argument("--temperature", type=float, default=0.0)
    parser.add_argument("--model-dir", type=Path, default=MODEL_DIR)
    parser.add_argument("--tag", type=str, default="base")
    parser.add_argument("--split", choices=["all", "train", "test"], default="all", help="Which split to evaluate (headline metrics use test)")
    args = parser.parse_args()

    os.environ.setdefault("HF_HOME", str(HF_HOME))
    os.environ.setdefault("HUGGINGFACE_HUB_CACHE", str(HF_HOME / "hub"))

    if not args.model_dir.exists():
        print(f"Model not found at {args.model_dir}. Run download_model.py first.", file=sys.stderr)
        return 1
    if not EVAL_PATH.exists():
        print(f"Missing eval set {EVAL_PATH}. Run build_eval.py first.", file=sys.stderr)
        return 1

    examples = load_examples(args.split, args.limit)
    model, tokenizer, device = load_model(args.model_dir)
    summary = run_benchmark(
        model, tokenizer, device, examples,
        tag=args.tag, split=args.split, model_dir=args.model_dir,
        max_new_tokens=args.max_new_tokens, temperature=args.temperature,
    )
    print(json.dumps(summary, indent=2))
    return 0


if __name__ == "__main__":
    sys.exit(main())
