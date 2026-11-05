#!/usr/bin/env python3
"""Practice prompts for WSP = sealed train-only file (never test).

exp8 mapping: practice problems with answers, none from the test sets.
The live practice surface is ``wsp/practice/train.jsonl``. The holdout test
rows live under ``eval/sealed/`` (and may be quarantined outside the workspace
during a long editor run).
"""
from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any

from .paths_wsp import PRACTICE_TRAIN_PATH, SEALED_TEST_PATH, TOOLS_PATH


def load_jsonl(path: Path) -> list[dict[str, Any]]:
    rows = []
    with path.open(encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line:
                rows.append(json.loads(line))
    return rows


def _assert_train_only(rows: list[dict[str, Any]], path: Path) -> None:
    bad = [r.get("id") for r in rows if r.get("split") not in (None, "train")]
    # Allow missing split on sealed practice file, but reject explicit non-train.
    explicit_bad = [r.get("id") for r in rows if r.get("split") and r.get("split") != "train"]
    if explicit_bad:
        raise RuntimeError(
            f"Leakage guard: practice file {path} contains non-train rows: {explicit_bad[:5]}"
        )
    for r in rows:
        if r.get("split") is None:
            r["split"] = "train"


def load_practice(split: str = "train", eval_path: Path | None = None) -> list[dict[str, Any]]:
    """Load practice examples.

    Only ``train`` is allowed for the editor harness. Pass ``split="test"`` only
    from post-run evaluation helpers that intentionally unseal.
    """
    if split == "train":
        path = Path(eval_path) if eval_path else PRACTICE_TRAIN_PATH
        if not path.exists():
            raise FileNotFoundError(
                f"Sealed practice missing: {path}. Run build_practice.py / seal step."
            )
        rows = load_jsonl(path)
        _assert_train_only(rows, path)
        return rows
    if split == "test":
        if os.environ.get("WSP_LOCK_TEST", "0") == "1":
            raise RuntimeError("WSP_LOCK_TEST=1: test split is sealed until the editor run ends.")
        path = Path(eval_path) if eval_path else SEALED_TEST_PATH
        if not path.exists():
            raise FileNotFoundError(f"Sealed test missing: {path}")
        return load_jsonl(path)
    raise ValueError("split must be 'train' or 'test' (no 'all' in sealed harness)")


def load_tools() -> dict[str, Any]:
    return json.loads(Path(TOOLS_PATH).read_text(encoding="utf-8"))


def tools_by_name() -> dict[str, Any]:
    tools = load_tools()
    return {t["name"]: t for t in tools["tools"]}
