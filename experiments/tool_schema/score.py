#!/usr/bin/env python3
"""Score model outputs against tool-schema expectations."""
from __future__ import annotations

import json
import re
from typing import Any


JSON_OBJECT_RE = re.compile(r"\{.*\}", re.DOTALL)


def extract_json_object(text: str) -> dict[str, Any] | None:
    if not text:
        return None
    text = text.strip()
    # Strip common markdown fences
    fence = re.search(r"```(?:json)?\s*(.*?)```", text, re.DOTALL | re.IGNORECASE)
    if fence:
        text = fence.group(1).strip()
    try:
        obj = json.loads(text)
        return obj if isinstance(obj, dict) else None
    except json.JSONDecodeError:
        pass
    m = JSON_OBJECT_RE.search(text)
    if not m:
        return None
    try:
        obj = json.loads(m.group(0))
        return obj if isinstance(obj, dict) else None
    except json.JSONDecodeError:
        return None


def _norm_str(v: Any) -> str:
    return str(v).strip()


def _numbers_equal(a: Any, b: Any) -> bool:
    try:
        return abs(float(a) - float(b)) < 1e-6
    except (TypeError, ValueError):
        return False


def arguments_match(expected: dict[str, Any], got: Any, tool_params: dict[str, Any] | None = None) -> dict[str, bool]:
    flags = {
        "args_is_object": isinstance(got, dict),
        "required_keys": False,
        "types_ok": False,
        "values_ok": False,
    }
    if not isinstance(got, dict):
        return flags

    req_keys = set(expected.keys())
    flags["required_keys"] = req_keys.issubset(got.keys())

    types_ok = True
    values_ok = True
    for key, exp_val in expected.items():
        if key not in got:
            types_ok = False
            values_ok = False
            continue
        got_val = got[key]
        if isinstance(exp_val, bool):
            types_ok = types_ok and isinstance(got_val, bool)
            values_ok = values_ok and got_val == exp_val
        elif isinstance(exp_val, int) and not isinstance(exp_val, bool):
            # accept int-like numbers
            try:
                types_ok = types_ok and float(got_val).is_integer()
                values_ok = values_ok and int(float(got_val)) == exp_val
            except (TypeError, ValueError):
                types_ok = False
                values_ok = False
        elif isinstance(exp_val, float):
            types_ok = types_ok and _numbers_equal(got_val, got_val)  # numeric parseable
            try:
                float(got_val)
            except (TypeError, ValueError):
                types_ok = False
            values_ok = values_ok and _numbers_equal(got_val, exp_val)
        else:
            types_ok = types_ok and isinstance(got_val, (str, int, float))
            values_ok = values_ok and _norm_str(got_val) == _norm_str(exp_val)

        if tool_params and key in tool_params:
            enum = tool_params[key].get("enum")
            if enum is not None and _norm_str(got_val) not in enum:
                types_ok = False
                values_ok = False

    flags["types_ok"] = types_ok
    flags["values_ok"] = values_ok
    return flags


def score_example(
    expected: dict[str, Any],
    completion: str,
    tools_by_name: dict[str, Any] | None = None,
) -> dict[str, Any]:
    parsed = extract_json_object(completion)
    result = {
        "parse_ok": parsed is not None,
        "tool_ok": False,
        "args_is_object": False,
        "required_keys": False,
        "types_ok": False,
        "values_ok": False,
        "strict_ok": False,
        "parsed": parsed,
    }
    if parsed is None:
        return result

    tool = parsed.get("tool")
    result["tool_ok"] = tool == expected.get("tool")
    params = None
    if tools_by_name and isinstance(tool, str) and tool in tools_by_name:
        params = tools_by_name[tool].get("parameters")

    arg_flags = arguments_match(expected.get("arguments", {}), parsed.get("arguments"), params)
    result.update(arg_flags)
    result["strict_ok"] = bool(
        result["parse_ok"]
        and result["tool_ok"]
        and result["args_is_object"]
        and result["required_keys"]
        and result["types_ok"]
        and result["values_ok"]
    )
    return result


def summarize(rows: list[dict[str, Any]]) -> dict[str, Any]:
    n = len(rows)
    def rate(key: str) -> float:
        return (sum(1 for r in rows if r["scores"][key]) / n) if n else 0.0

    by_tier: dict[str, list[dict[str, Any]]] = {}
    for r in rows:
        by_tier.setdefault(r.get("tier", "unknown"), []).append(r)

    tier_stats = {}
    for tier, items in by_tier.items():
        m = len(items)
        tier_stats[tier] = {
            "n": m,
            "strict_ok": sum(1 for x in items if x["scores"]["strict_ok"]) / m if m else 0.0,
            "parse_ok": sum(1 for x in items if x["scores"]["parse_ok"]) / m if m else 0.0,
            "tool_ok": sum(1 for x in items if x["scores"]["tool_ok"]) / m if m else 0.0,
        }

    return {
        "n": n,
        "parse_ok": rate("parse_ok"),
        "tool_ok": rate("tool_ok"),
        "required_keys": rate("required_keys"),
        "types_ok": rate("types_ok"),
        "values_ok": rate("values_ok"),
        "strict_ok": rate("strict_ok"),
        "by_tier": tier_stats,
    }
