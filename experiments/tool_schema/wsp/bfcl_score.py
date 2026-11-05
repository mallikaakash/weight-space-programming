#!/usr/bin/env python3
"""Official BFCL AST scoring for a single practice/holdout example.

Used by the metered WSP forward tool so practice metric == holdout metric.
"""
from __future__ import annotations

import re
from typing import Any

BFCL_MODEL_NAME = "meta-llama/Llama-3.1-8B-Instruct"


def extract_call_bracket(text: str) -> str:
    text = (text or "").strip()
    m = re.search(r"\[.*\]", text, flags=re.DOTALL)
    if m:
        return m.group(0).strip()
    # Fallback: {"tool": "...", "arguments": {...}} → [tool(k=v, ...)]
    try:
        import json

        start = text.find("{")
        end = text.rfind("}")
        if start >= 0 and end > start:
            obj = json.loads(text[start : end + 1])
            if isinstance(obj, dict) and "tool" in obj and isinstance(obj.get("arguments"), dict):
                parts = [f"{k}={json.dumps(v)}" for k, v in obj["arguments"].items()]
                return f"[{obj['tool']}({', '.join(parts)})]"
    except Exception:
        pass
    return text


def score_bfcl_example(ex: dict[str, Any], completion: str) -> dict[str, Any]:
    """Return score flags compatible with ``score.summarize`` (strict_ok = AST valid)."""
    from bfcl_eval.constants.enums import Language, ReturnFormat
    from bfcl_eval.eval_checker.ast_eval.ast_checker import ast_checker
    from bfcl_eval.model_handler.utils import default_decode_ast_prompting
    from bfcl_eval.utils import is_function_calling_format_output

    extracted = extract_call_bracket(completion)
    decoded = None
    err: list[Any] = []
    valid = False
    try:
        decoded = default_decode_ast_prompting(extracted, ReturnFormat.PYTHON, False)
        if not is_function_calling_format_output(decoded):
            raise ValueError("wrong function-calling format")
        check = ast_checker(
            ex["function"],
            decoded,
            ex["ground_truth"],
            Language.PYTHON,
            "simple_python",
            BFCL_MODEL_NAME,
        )
        valid = bool(check.get("valid"))
        err = check.get("error") or []
    except Exception as e:
        valid = False
        err = [str(e)]

    # Alias AST validity onto the editor-facing primary metric (strict_ok).
    return {
        "parse_ok": decoded is not None,
        "tool_ok": valid,
        "args_is_object": True,
        "required_keys": valid,
        "no_hallucinated_keys": valid,
        "types_ok": valid,
        "values_ok": valid,
        "strict_ok": valid,
        "ast_ok": valid,
        "error": err,
        "extracted": extracted[:500],
        "parsed": decoded,
    }


def is_bfcl_example(ex: dict[str, Any]) -> bool:
    return ex.get("task") == "bfcl_simple_python" or (
        "ground_truth" in ex and "function" in ex and "expected_call" in ex
    )
