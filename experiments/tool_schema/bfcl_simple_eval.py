#!/usr/bin/env python3
"""Official BFCL Simple (Python) AST eval for a local SmolLM checkpoint.

Uses the BFCL v4 ``simple_python`` prompts + possible answers shipped with
``bfcl-eval``, and the official ``ast_checker``. This is a **subset** leaderboard
category (AST Simple/Python), not the full BFCL suite — honest about that.

The editor must never see these examples during a WSP run; treat this script as
post-run / orchestrator-only (same role as ``eval_edited.py``).
"""
from __future__ import annotations

import argparse
import json
import re
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import torch
from tqdm import tqdm
from transformers import AutoModelForCausalLM, AutoTokenizer

EXPERIMENT_ROOT = Path(__file__).resolve().parent
REPO_ROOT = EXPERIMENT_ROOT.parents[1]
sys.path.insert(0, str(EXPERIMENT_ROOT))

from paths import MODEL_DIR  # noqa: E402

SYSTEM_PROMPT = """You call Python functions. Reply with ONLY a single call in this exact form:

[function_name(param1=value1, param2=value2)]

Examples:
[calculate_triangle_area(base=10, height=5)]
[math.factorial(number=5)]

Rules:
- Square brackets around the call.
- Use the exact function name (including dots if present, e.g. math.factorial).
- Always use named arguments (number=5), never positional (5).
- Python literals only (strings in double quotes, ints/floats bare).
- Do NOT repeat the function schema/JSON. Do NOT write prose.
"""


def load_jsonl(path: Path) -> list[dict[str, Any]]:
    rows = []
    with path.open(encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line:
                rows.append(json.loads(line))
    return rows


def bfcl_data_paths() -> tuple[Path, Path]:
    import bfcl_eval

    root = Path(bfcl_eval.__file__).resolve().parent / "data"
    return root / "BFCL_v4_simple_python.json", root / "possible_answer" / "BFCL_v4_simple_python.json"


def build_user_content(ex: dict[str, Any]) -> str:
    # BFCL question is nested chat turns; for simple_python it's one user message.
    question = ex["question"]
    user_text = question[0][0]["content"]
    func = ex["function"][0]
    # Compact function card — reduce schema-echo temptation for tiny models.
    props = (func.get("parameters") or {}).get("properties") or {}
    required = (func.get("parameters") or {}).get("required") or []
    prop_lines = []
    for name, spec in props.items():
        req = "required" if name in required else "optional"
        prop_lines.append(f"  - {name} ({spec.get('type', '?')}, {req}): {spec.get('description', '')}")
    return (
        f"Function name: {func['name']}\n"
        f"Description: {func.get('description', '')}\n"
        f"Parameters:\n" + "\n".join(prop_lines) + "\n\n"
        f"User request: {user_text}\n\n"
        "Respond with only: [function_name(...)]"
    )


def extract_call_bracket(text: str) -> str:
    """Best-effort extract `[...]` or convert our JSON tool schema to BFCL form."""
    text = (text or "").strip()
    # Prefer first [...] block
    m = re.search(r"\[.*\]", text, flags=re.DOTALL)
    if m:
        return m.group(0).strip()

    # Fallback: {"tool": "...", "arguments": {...}} → [tool(k=v, ...)]
    try:
        # find first JSON object
        start = text.find("{")
        end = text.rfind("}")
        if start >= 0 and end > start:
            obj = json.loads(text[start : end + 1])
            if isinstance(obj, dict) and "tool" in obj and isinstance(obj.get("arguments"), dict):
                parts = []
                for k, v in obj["arguments"].items():
                    parts.append(f"{k}={json.dumps(v)}")
                return f"[{obj['tool']}({', '.join(parts)})]"
    except Exception:
        pass
    return text


@torch.inference_mode()
def generate_one(model, tokenizer, messages: list[dict[str, str]], max_new_tokens: int) -> str:
    prompt = tokenizer.apply_chat_template(messages, tokenize=False, add_generation_prompt=True)
    inputs = tokenizer(prompt, return_tensors="pt")
    inputs = {k: v.to(model.device) for k, v in inputs.items()}
    out = model.generate(
        **inputs,
        max_new_tokens=max_new_tokens,
        do_sample=False,
        pad_token_id=tokenizer.eos_token_id,
    )
    new_tokens = out[0, inputs["input_ids"].shape[-1] :]
    return tokenizer.decode(new_tokens, skip_special_tokens=True).strip()


def score_with_official_ast(
    prompts: list[dict],
    answers: list[dict],
    generations: list[dict[str, str]],
    *,
    model_name: str,
) -> dict[str, Any]:
    from bfcl_eval.constants.enums import Language, ReturnFormat
    from bfcl_eval.eval_checker.ast_eval.ast_checker import ast_checker
    from bfcl_eval.model_handler.utils import default_decode_ast_prompting
    from bfcl_eval.utils import is_function_calling_format_output

    by_id_p = {ex["id"]: ex for ex in prompts}
    by_id_a = {ex["id"]: ex for ex in answers}
    rows = []
    n_ok = 0
    for g in generations:
        eid = g["id"]
        prompt_entry = by_id_p[eid]
        answer_entry = by_id_a[eid]
        raw = g["completion"]
        extracted = extract_call_bracket(raw)
        try:
            decoded = default_decode_ast_prompting(extracted, ReturnFormat.PYTHON, False)
            if not is_function_calling_format_output(decoded):
                raise ValueError("wrong function-calling format")
            check = ast_checker(
                prompt_entry["function"],
                decoded,
                answer_entry["ground_truth"],
                Language.PYTHON,
                "simple_python",
                model_name,
            )
            valid = bool(check.get("valid"))
            err = check.get("error") or []
        except Exception as e:
            valid = False
            decoded = None
            err = [str(e)]
        if valid:
            n_ok += 1
        rows.append(
            {
                "id": eid,
                "valid": valid,
                "error": err,
                "completion": raw[:500],
                "extracted": extracted[:500],
                "decoded": decoded,
            }
        )
    n = len(rows) or 1
    return {
        "n": len(rows),
        "ast_accuracy": n_ok / n,
        "n_correct": n_ok,
        "category": "simple_python",
        "scorer": "bfcl_eval.ast_checker",
        "rows_head_failures": [r for r in rows if not r["valid"]][:15],
    }


def main() -> int:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--model-dir", type=Path, default=MODEL_DIR)
    p.add_argument(
        "--edited-state",
        type=Path,
        default=None,
        help="Optional edited state_dict (.pt) to load over the base model",
    )
    p.add_argument("--limit", type=int, default=0, help="0 = all 400 simple_python items")
    p.add_argument("--offset", type=int, default=0)
    p.add_argument("--max-new-tokens", type=int, default=128)
    p.add_argument("--tag", default="bfcl-simple-python")
    p.add_argument("--out-dir", type=Path, default=EXPERIMENT_ROOT / "results" / "bfcl")
    args = p.parse_args()

    q_path, a_path = bfcl_data_paths()
    prompts = load_jsonl(q_path)
    answers = load_jsonl(a_path)
    assert len(prompts) == len(answers) == 400
    # Keep id alignment
    prompts = prompts[args.offset :]
    answers = answers[args.offset :]
    if args.limit and args.limit > 0:
        prompts = prompts[: args.limit]
        answers = answers[: args.limit]

    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    dtype = torch.bfloat16 if device.type == "cuda" else torch.float32
    print(f"Loading {args.model_dir} on {device} (+edited={bool(args.edited_state)})", flush=True)
    tokenizer = AutoTokenizer.from_pretrained(args.model_dir)
    model = AutoModelForCausalLM.from_pretrained(args.model_dir, torch_dtype=dtype)
    if args.edited_state:
        state = torch.load(args.edited_state, map_location="cpu", weights_only=True)
        model.load_state_dict(state, strict=True)
    model.to(device)
    model.eval()

    generations = []
    for ex in tqdm(prompts, desc=f"bfcl[{args.tag}]"):
        messages = [
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": build_user_content(ex)},
        ]
        completion = generate_one(model, tokenizer, messages, args.max_new_tokens)
        generations.append({"id": ex["id"], "completion": completion})

    # bfcl-eval looks up model_name in MODEL_CONFIG_MAPPING and also does
    # model_name.replace("_", "/"). Use a real prompting-style id from the map.
    summary = score_with_official_ast(
        prompts,
        answers,
        generations,
        model_name="meta-llama/Llama-3.1-8B-Instruct",
    )
    summary.update(
        {
            "tag": args.tag,
            "model_dir": str(args.model_dir),
            "edited_state": str(args.edited_state) if args.edited_state else None,
            "offset": args.offset,
            "limit": args.limit or len(prompts),
            "device": str(device),
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "note": (
                "Official BFCL v4 simple_python AST category via bfcl-eval checker. "
                "Not full BFCL (no multiple/parallel/live/multi-turn)."
            ),
        }
    )

    args.out_dir.mkdir(parents=True, exist_ok=True)
    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    (args.out_dir / f"{args.tag}_{stamp}.summary.json").write_text(
        json.dumps(summary, indent=2, default=str), encoding="utf-8"
    )
    (args.out_dir / f"{args.tag}_latest.summary.json").write_text(
        json.dumps(summary, indent=2, default=str), encoding="utf-8"
    )
    (args.out_dir / f"{args.tag}_{stamp}.generations.jsonl").write_text(
        "\n".join(json.dumps(g) for g in generations) + "\n", encoding="utf-8"
    )
    print(json.dumps({k: summary[k] for k in summary if k != "rows_head_failures"}, indent=2))
    print("failures_head:", json.dumps(summary["rows_head_failures"][:3], indent=2, default=str)[:800])
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
