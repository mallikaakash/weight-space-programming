#!/usr/bin/env python3
"""Practice prompts for WSP = tool-schema train split only (never test)."""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from .paths_wsp import EVAL_PATH, TOOLS_PATH


def load_jsonl(path: Path) -> list[dict[str, Any]]:
    rows = []
    with path.open(encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line:
                rows.append(json.loads(line))
    return rows


def load_practice(split: str = "train", eval_path: Path | None = None) -> list[dict[str, Any]]:
    if split not in {"train", "test", "all"}:
        raise ValueError("split must be train, test, or all")
    rows = load_jsonl(Path(eval_path or EVAL_PATH))
    if split != "all":
        rows = [r for r in rows if r.get("split") == split]
    return rows


def load_tools() -> dict[str, Any]:
    return json.loads(Path(TOOLS_PATH).read_text(encoding="utf-8"))


def tools_by_name() -> dict[str, Any]:
    tools = load_tools()
    return {t["name"]: t for t in tools["tools"]}
