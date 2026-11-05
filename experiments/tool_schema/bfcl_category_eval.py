#!/usr/bin/env python3
"""Multi-category BFCL v4 (non-live AST) eval for a local SmolLM checkpoint.

Generalizes ``bfcl_simple_eval.py`` beyond ``simple_python`` to the other
single-turn AST categories that ship an official ``possible_answer`` file:

    simple_python, simple_java, simple_javascript, multiple, parallel, parallel_multiple

Scoring goes through bfcl-eval's own per-entry AST path
(``eval_runner._evaluate_single_ast_entry`` → ``default_decode_ast_prompting`` →
``is_function_calling_format_output`` → ``ast_checker``), with the same
language / return-format selection as ``eval_runner.ast_file_runner``.

This is a **subset** of BFCL (non-live AST only). It is not a leaderboard
reproduction: live_*, multi_turn_*, irrelevance/relevance, web_search, memory,
format_sensitivity are out of scope, and prompts use this repo's protocol
(``--prompt-style card``) unless ``--prompt-style bfcl`` is passed.

Eval only — this script never modifies weights.
"""
from __future__ import annotations

import argparse
import collections
import copy
import json
import os
import re
import sys
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import torch
from transformers import AutoModelForCausalLM, AutoTokenizer

EXPERIMENT_ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(EXPERIMENT_ROOT))

from paths import MODEL_DIR  # noqa: E402
import bfcl_simple_eval as legacy  # noqa: E402  (simple_python prompt + extractor, kept identical)

CATEGORIES = (
    "simple_python",
    "simple_java",
    "simple_javascript",
    "multiple",
    "parallel",
    "parallel_multiple",
)

# Same model id the legacy script uses: bfcl-eval's convert_func_name() looks it up
# in MODEL_CONFIG_MAPPING; this prompting-style entry keeps dotted names as-is.
CHECKER_MODEL_NAME = "meta-llama/Llama-3.1-8B-Instruct"

# --------------------------------------------------------------------------- prompts
# ``card`` style = the repo's simple_python protocol (short system prompt + compact
# function card in the user turn). simple_python is byte-identical to bfcl_simple_eval.

_PY_EXAMPLES_SINGLE = """Examples:
[calculate_triangle_area(base=10, height=5)]
[math.factorial(number=5)]"""

_PY_RULES = """Rules:
- Square brackets around the call{plural}.
- Use the exact function name (including dots if present, e.g. math.factorial).
- Always use named arguments (number=5), never positional (5).
- Python literals only (strings in double quotes, ints/floats bare).
- Do NOT repeat the function schema/JSON. Do NOT write prose.
"""

SYSTEM_PROMPTS: dict[str, str] = {
    "simple_python": legacy.SYSTEM_PROMPT,
    "simple_java": """You call Java methods. Reply with ONLY a single call in this exact form:

[ClassName.methodName(param1=value1, param2=value2)]

Examples:
[ReportBuilder.export(target=outputFile, overwrite=true)]
[TextIndex.search(query="annual report", maxHits=20)]

Rules:
- Square brackets around the call.
- Use the exact method name given, including the class prefix (e.g. ReportBuilder.export).
- Always use named arguments (maxHits=20), never positional (20).
- Values are Java expressions: strings in double quotes, numbers bare, booleans true/false, existing variables/objects by their plain name.
- Do NOT define or implement the method (no code body). Only CALL it.
- Do NOT repeat the function schema/JSON. Do NOT write prose.
""",
    "simple_javascript": """You call JavaScript functions. Reply with ONLY a single call in this exact form:

[functionName(param1=value1, param2=value2)]

Examples:
[renderChart(containerId="salesChart", animate=true)]
[scheduleRetry(task=uploadTask, delayMs=500)]

Rules:
- Square brackets around the call.
- Use the exact function name given.
- Always use named arguments (delayMs=500), never positional (500).
- Values are JavaScript expressions: strings in double quotes, numbers bare, booleans true/false, arrays [..], objects {..}, existing variables by their plain name.
- Do NOT define or implement the function (no `function` keyword, no code body). Only CALL it.
- Do NOT repeat the function schema/JSON. Do NOT write prose.
""",
    "multiple": """You call Python functions. Several functions are available; pick the ONE that fits the request.
Reply with ONLY a single call in this exact form:

[function_name(param1=value1, param2=value2)]

"""
    + _PY_EXAMPLES_SINGLE
    + "\n\n"
    + _PY_RULES.format(plural="")
    + "- Call exactly one function: the one that matches the request.\n",
    "parallel": """You call Python functions. The request may need the SAME function called several times (for example once per city, person, or value).
Reply with ONLY a list of calls in this exact form:

[function_name(param1=value1), function_name(param1=value2)]

Examples:
[calculate_triangle_area(base=10, height=5), calculate_triangle_area(base=6, height=3)]
[math.factorial(number=5), math.factorial(number=7)]

"""
    + _PY_RULES.format(plural="s (one pair of brackets around the whole list)")
    + "- Make one call per item the user asks about; separate calls with commas.\n",
    "parallel_multiple": """You call Python functions. The request may need SEVERAL calls, possibly to different functions, and the same function more than once.
Reply with ONLY a list of calls in this exact form:

[function_name(param1=value1), other_function_name(param2=value2)]

Examples:
[calculate_triangle_area(base=10, height=5), math.factorial(number=5)]
[math.factorial(number=5), math.factorial(number=7), calculate_triangle_area(base=6, height=3)]

"""
    + _PY_RULES.format(plural="s (one pair of brackets around the whole list)")
    + "- Make every call the request needs; separate calls with commas.\n",
}

RESPOND_LINE = {
    "simple_python": "Respond with only: [function_name(...)]",
    "simple_java": "Respond with only: [ClassName.methodName(...)]",
    "simple_javascript": "Respond with only: [functionName(...)]",
    "multiple": "Respond with only: [function_name(...)]",
    "parallel": "Respond with only: [function_name(...), function_name(...)]",
    "parallel_multiple": "Respond with only: [function_name(...), other_function_name(...)]",
}

MAX_NEW_TOKENS = {
    "simple_python": 128,
    "simple_java": 128,
    "simple_javascript": 128,
    "multiple": 128,
    "parallel": 256,
    "parallel_multiple": 256,
}


def language_for(category: str):
    """Mirror eval_runner.ast_file_runner's language / return-format choice."""
    from bfcl_eval.constants.enums import Language, ReturnFormat
    from bfcl_eval.utils import is_java, is_js

    if is_java(category):
        return Language.JAVA, ReturnFormat.JAVA
    if is_js(category):
        return Language.JAVASCRIPT, ReturnFormat.JAVASCRIPT
    return Language.PYTHON, ReturnFormat.PYTHON


def _card(func_raw: dict, func_shown: dict) -> list[str]:
    """Compact function card (legacy layout). Types come from the raw doc (e.g. Java
    ``boolean`` / ``any``), descriptions from ``func_shown`` (hinted for Java/JS)."""
    params_raw = func_raw.get("parameters") or {}
    props_raw = params_raw.get("properties") or {}
    props_shown = (func_shown.get("parameters") or {}).get("properties") or {}
    required = params_raw.get("required") or []
    prop_lines = []
    for name, spec in props_raw.items():
        req = "required" if name in required else "optional"
        desc = (props_shown.get(name) or spec).get("description", "")
        prop_lines.append(f"  - {name} ({spec.get('type', '?')}, {req}): {desc}")
    return [
        f"Function name: {func_raw['name']}",
        f"Description: {func_shown.get('description', '')}",
        "Parameters:\n" + "\n".join(prop_lines),
    ]


def build_card_messages(category: str, ex_raw: dict, ex_shown: dict) -> list[dict[str, str]]:
    user_text = ex_raw["question"][0][0]["content"]
    if category == "simple_python":
        # Byte-identical to the WSP holdout protocol.
        content = legacy.build_user_content(ex_raw)
    else:
        funcs = list(zip(ex_raw["function"], ex_shown["function"]))
        if len(funcs) == 1:
            body = "\n".join(_card(*funcs[0]))
        else:
            blocks = []
            for i, (fr, fs) in enumerate(funcs, 1):
                lines = _card(fr, fs)
                blocks.append(f"Function {i} of {len(funcs)}\n" + "\n".join(lines))
            body = "Available functions:\n\n" + "\n\n".join(blocks)
        content = f"{body}\n\nUser request: {user_text}\n\n{RESPOND_LINE[category]}"
    return [
        {"role": "system", "content": SYSTEM_PROMPTS[category]},
        {"role": "user", "content": content},
    ]


def build_bfcl_messages(category: str, ex_shown: dict) -> list[dict[str, str]]:
    """Official BFCL default prompting system prompt (JSON function dump)."""
    from bfcl_eval.model_handler.utils import system_prompt_pre_processing_chat_model

    turn = copy.deepcopy(ex_shown["question"][0])
    return system_prompt_pre_processing_chat_model(turn, ex_shown["function"], ex_shown["id"])


# --------------------------------------------------------------------------- data
def load_category(category: str, prompt_style: str):
    """Return (raw prompts for scoring, prompts shown to the model, ground truth)."""
    from bfcl_eval.utils import load_dataset_entry, load_ground_truth_entry

    raw = load_dataset_entry(category, include_prereq=False, include_language_specific_hint=False)
    answers = load_ground_truth_entry(category)
    if prompt_style == "bfcl" or category in ("simple_java", "simple_javascript"):
        # Official generation-side docs (language hints; Java/JS types → string repr).
        shown = load_dataset_entry(category, include_prereq=False, include_language_specific_hint=True)
    else:
        # Python card style: raw docs, identical to the WSP simple_python protocol.
        shown = copy.deepcopy(raw)
    assert len(raw) == len(answers) == len(shown), category
    for r, a, s in zip(raw, answers, shown):
        assert r["id"] == a["id"] == s["id"], (r["id"], a["id"], s["id"])
        assert len(r["question"]) == 1 and len(r["question"][0]) == 1, r["id"]
        assert r["question"][0][0]["role"] == "user", r["id"]
    return raw, shown, answers


# --------------------------------------------------------------------------- generation
@torch.inference_mode()
def generate_batch(model, tokenizer, batch_messages, max_new_tokens: int) -> list[str]:
    prompts = [
        tokenizer.apply_chat_template(m, tokenize=False, add_generation_prompt=True)
        for m in batch_messages
    ]
    enc = tokenizer(prompts, return_tensors="pt", padding=True)
    enc = {k: v.to(model.device) for k, v in enc.items()}
    out = model.generate(
        **enc,
        max_new_tokens=max_new_tokens,
        do_sample=False,
        pad_token_id=tokenizer.eos_token_id,
    )
    new = out[:, enc["input_ids"].shape[-1] :]
    return [tokenizer.decode(row, skip_special_tokens=True).strip() for row in new]


def run_generation(model, tokenizer, messages_by_id, max_new_tokens, batch_size, desc):
    ids = list(messages_by_id)
    if batch_size <= 1:
        order = ids
    else:  # length-sort to cut padding waste
        lens = {
            i: len(tokenizer.apply_chat_template(messages_by_id[i], tokenize=True, add_generation_prompt=True))
            for i in ids
        }
        order = sorted(ids, key=lambda i: lens[i])
    out: dict[str, str] = {}
    t0 = time.time()
    bs = max(1, batch_size)
    for s in range(0, len(order), bs):
        chunk = order[s : s + bs]
        comps = generate_batch(model, tokenizer, [messages_by_id[i] for i in chunk], max_new_tokens)
        out.update(zip(chunk, comps))
        done = min(s + bs, len(order))
        el = time.time() - t0
        print(f"[{desc}] {done}/{len(order)}  {el:.0f}s  ({el / done:.2f}s/item)", flush=True)
    return out, time.time() - t0


# --------------------------------------------------------------------------- scoring
class _PromptingDecodeShim:
    """Stands in for an OSS prompting handler: decode_ast == default_decode_ast_prompting."""

    def decode_ast(self, result, language, has_tool_call_tag):
        from bfcl_eval.model_handler.utils import default_decode_ast_prompting

        return default_decode_ast_prompting(result, language, has_tool_call_tag)


def official_entry_verdict(text: str, prompt_entry: dict, gt: list, category: str) -> dict:
    from bfcl_eval.eval_checker.eval_runner import _evaluate_single_ast_entry

    language, return_format = language_for(category)
    try:
        r = _evaluate_single_ast_entry(
            _PromptingDecodeShim(),
            prompt_entry["id"],
            text,
            gt,
            prompt_entry,
            CHECKER_MODEL_NAME,
            category,
            language=language,
            return_format=return_format,
            has_tool_call_tag=False,
        )
    except Exception as e:  # official runner would crash here; count as invalid
        return {"valid": False, "error": [f"checker exception: {e!r}"], "error_type": "checker_exception"}
    if r["valid"]:
        return {"valid": True, "error": [], "error_type": None}
    return {
        "valid": False,
        "error": r.get("error") or [],
        "error_type": r.get("error_type"),
        "decoded": r.get("model_result_decoded"),
    }


def score(category, raw_prompts, answers, completions) -> tuple[dict, list[dict]]:
    by_a = {a["id"]: a for a in answers}
    rows = []
    for p in raw_prompts:
        eid = p["id"]
        comp = completions[eid]
        extracted = legacy.extract_call_bracket(comp)
        v = official_entry_verdict(extracted, p, by_a[eid]["ground_truth"], category)
        v_raw = official_entry_verdict(comp, p, by_a[eid]["ground_truth"], category)
        rows.append(
            {
                "id": eid,
                "valid": v["valid"],
                "valid_raw": v_raw["valid"],
                "error_type": v["error_type"],
                "error": [str(x)[:300] for x in v["error"]][:3],
                "completion": comp,
                "extracted": extracted,
                "decoded": v.get("decoded"),
            }
        )
    n = len(rows)
    n_ok = sum(r["valid"] for r in rows)
    n_ok_raw = sum(r["valid_raw"] for r in rows)
    etypes = collections.Counter(r["error_type"] for r in rows if not r["valid"])
    summary: dict[str, Any] = {
        "category": category,
        "n": n,
        "n_correct": n_ok,
        "ast_accuracy": n_ok / n if n else 0.0,
        "n_correct_raw": n_ok_raw,
        "ast_accuracy_raw": n_ok_raw / n if n else 0.0,
        "error_types": dict(etypes.most_common()),
    }
    if category == "simple_python":
        idx = lambda r: int(r["id"].rsplit("_", 1)[1])  # noqa: E731
        for name, lo, hi in (("practice_0_299", 0, 299), ("holdout_300_399", 300, 399)):
            sub = [r for r in rows if lo <= idx(r) <= hi]
            if sub:
                k = sum(r["valid"] for r in sub)
                summary.setdefault("splits", {})[name] = {"n": len(sub), "n_correct": k, "ast_accuracy": k / len(sub)}
    return summary, rows


# --------------------------------------------------------------------------- main
def main() -> int:
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--category", nargs="+", required=True, choices=CATEGORIES,
                   help="One or more categories; the model is loaded once for all of them.")
    p.add_argument("--model-dir", type=Path, default=MODEL_DIR)
    p.add_argument("--edited-state", type=Path, default=None,
                   help="Optional edited state_dict (.pt) loaded over the base model (strict).")
    p.add_argument("--limit", type=int, default=0, help="0 = whole category")
    p.add_argument("--offset", type=int, default=0)
    p.add_argument("--max-new-tokens", type=int, default=0, help="0 = per-category default")
    p.add_argument("--batch-size", type=int, default=1, help="1 = exact legacy protocol (and fastest on CPU here)")
    p.add_argument("--threads", type=int, default=0, help="torch threads (0 = torch default)")
    p.add_argument("--prompt-style", choices=("card", "bfcl"), default="card")
    p.add_argument("--tag", required=True)
    p.add_argument("--out-dir", type=Path, default=EXPERIMENT_ROOT / "results" / "bfcl")
    p.add_argument("--force", action="store_true", help="Allow running while WSP_LOCK_TEST=1.")
    args = p.parse_args()

    if os.environ.get("WSP_LOCK_TEST", "0") == "1" and not args.force:
        print("Refused: WSP_LOCK_TEST=1 (BFCL is sealed during editor runs).", file=sys.stderr)
        return 3
    if args.threads:
        torch.set_num_threads(args.threads)

    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    dtype = torch.bfloat16 if device.type == "cuda" else torch.float32
    print(f"Loading {args.model_dir} on {device} (edited={args.edited_state})", flush=True)
    tokenizer = AutoTokenizer.from_pretrained(args.model_dir)
    tokenizer.padding_side = "left"
    if tokenizer.pad_token is None:
        tokenizer.pad_token = tokenizer.eos_token
    model = AutoModelForCausalLM.from_pretrained(args.model_dir, torch_dtype=dtype)
    if args.edited_state:
        state = torch.load(args.edited_state, map_location="cpu", weights_only=True)
        model.load_state_dict(state, strict=True)
        del state
    model.to(device)
    model.eval()

    args.out_dir.mkdir(parents=True, exist_ok=True)
    overview = []
    for category in args.category:
        raw, shown, answers = load_category(category, args.prompt_style)
        sl = slice(args.offset, args.offset + args.limit if args.limit > 0 else None)
        raw, shown, answers = raw[sl], shown[sl], answers[sl]
        if args.prompt_style == "card":
            msgs = {r["id"]: build_card_messages(category, r, s) for r, s in zip(raw, shown)}
        else:
            msgs = {s["id"]: build_bfcl_messages(category, s) for s in shown}
        mnt = args.max_new_tokens or MAX_NEW_TOKENS[category]
        tag = f"{args.tag}_{category}"
        completions, gen_s = run_generation(model, tokenizer, msgs, mnt, args.batch_size, tag)
        summary, rows = score(category, raw, answers, completions)
        summary.update(
            {
                "tag": tag,
                "model_dir": str(args.model_dir),
                "edited_state": str(args.edited_state) if args.edited_state else None,
                "offset": args.offset,
                "limit": args.limit or len(raw),
                "prompt_style": args.prompt_style,
                "max_new_tokens": mnt,
                "batch_size": args.batch_size,
                "decoding": "greedy",
                "device": str(device),
                "dtype": str(dtype),
                "generation_seconds": round(gen_s, 1),
                "scorer": "bfcl_eval.eval_checker.eval_runner._evaluate_single_ast_entry (ast_checker)",
                "checker_model_name": CHECKER_MODEL_NAME,
                "bfcl_eval_version": _bfcl_version(),
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "note": (
                    "BFCL v4 non-live AST category scored with bfcl-eval's official per-entry AST path. "
                    "ast_accuracy = after the repo's [..] extraction (WSP protocol); ast_accuracy_raw = "
                    "official decode on the untouched completion. Not a BFCL leaderboard reproduction."
                ),
                "rows_head_failures": [r for r in rows if not r["valid"]][:10],
            }
        )
        stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
        js = json.dumps(summary, indent=2, default=str)
        (args.out_dir / f"{tag}_{stamp}.summary.json").write_text(js, encoding="utf-8")
        (args.out_dir / f"{tag}_latest.summary.json").write_text(js, encoding="utf-8")
        with (args.out_dir / f"{tag}_{stamp}.generations.jsonl").open("w", encoding="utf-8") as f:
            for r in rows:
                f.write(json.dumps(r, default=str) + "\n")
        brief = {k: summary[k] for k in ("tag", "n", "n_correct", "ast_accuracy", "ast_accuracy_raw", "generation_seconds")}
        brief["splits"] = summary.get("splits")
        brief["error_types"] = summary["error_types"]
        overview.append(brief)
        print(json.dumps(brief, indent=2), flush=True)
    print("=== overview ===")
    for b in overview:
        print(f"{b['tag']:60s} {b['n_correct']:4d}/{b['n']:<4d} = {b['ast_accuracy']:.3f} (raw {b['ast_accuracy_raw']:.3f})")
    return 0


def _bfcl_version() -> str:
    try:
        import importlib.metadata as md

        return md.version("bfcl-eval")
    except Exception:
        return "?"


if __name__ == "__main__":
    raise SystemExit(main())
