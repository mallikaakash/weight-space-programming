#!/usr/bin/env python3
"""Leakage / seal checks for WSP editor runs (exp8: editor never saw benchmarks)."""
from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any

from .paths_wsp import (
    EVAL_PATH,
    PRACTICE_TRAIN_PATH,
    SEALED_FULL_PATH,
    SEALED_TEST_PATH,
    SESSIONS_DIR,
)


def load_jsonl(path: Path) -> list[dict[str, Any]]:
    rows = []
    if not path.exists():
        return rows
    with path.open(encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line:
                rows.append(json.loads(line))
    return rows


def audit_seal() -> dict[str, Any]:
    """Report whether practice/test separation is intact."""
    train = load_jsonl(PRACTICE_TRAIN_PATH)
    seal_dir = Path(os.environ.get("WSP_SEAL_DIR", "/tmp/wsp_seal"))
    test_path = SEALED_TEST_PATH if SEALED_TEST_PATH.exists() else (seal_dir / "test.jsonl")
    test = load_jsonl(test_path)
    train_ids = {r["id"] for r in train}
    test_ids = {r["id"] for r in test}
    overlap = sorted(train_ids & test_ids)

    live = load_jsonl(EVAL_PATH) if EVAL_PATH.exists() else []
    live_test_ids = sorted({r["id"] for r in live if r.get("split") == "test"})
    lock = os.environ.get("WSP_LOCK_TEST", "0") == "1"

    issues: list[str] = []
    if not train:
        issues.append("practice/train.jsonl empty or missing")
    if any(r.get("split") not in (None, "train") for r in train):
        issues.append("practice/train.jsonl contains non-train split labels")
    if overlap:
        issues.append(f"train∩test overlap: {overlap[:10]}")
    if lock and live_test_ids:
        issues.append(
            f"WSP_LOCK_TEST=1 but live dataset.jsonl still exposes test ids: {live_test_ids[:5]}"
        )
    if lock and SEALED_TEST_PATH.exists():
        issues.append(
            "WSP_LOCK_TEST=1 but sealed test still under the workspace "
            f"({SEALED_TEST_PATH}); quarantine should move it to WSP_SEAL_DIR"
        )
    if not test and not lock:
        issues.append("sealed test missing (expected eval/sealed/test.jsonl)")

    return {
        "ok": not issues,
        "issues": issues,
        "train_n": len(train),
        "test_n": len(test),
        "overlap": overlap,
        "live_dataset_exists": EVAL_PATH.exists(),
        "live_test_ids_exposed": live_test_ids,
        "WSP_LOCK_TEST": lock,
        "practice_path": str(PRACTICE_TRAIN_PATH),
        "sealed_test_path": str(test_path),
        "sealed_full_exists": SEALED_FULL_PATH.exists() or (seal_dir / "dataset_full.jsonl").exists(),
    }


def assert_forward_log_train_only(session_dir: Path) -> dict[str, Any]:
    """Ensure every forward log id is in the sealed practice set."""
    train_ids = {r["id"] for r in load_jsonl(PRACTICE_TRAIN_PATH)}
    test_ids = {r["id"] for r in load_jsonl(SEALED_TEST_PATH)}
    budget_path = session_dir / "budget.json"
    if not budget_path.exists():
        return {"ok": False, "error": "missing budget.json", "leaked_ids": []}
    budget = json.loads(budget_path.read_text(encoding="utf-8"))
    leaked: list[str] = []
    seen: list[str] = []
    for entry in budget.get("log") or []:
        for i in entry.get("ids") or []:
            seen.append(i)
            if i in test_ids or i not in train_ids:
                leaked.append(i)
    return {
        "ok": not leaked,
        "n_forward_ids": len(seen),
        "leaked_ids": sorted(set(leaked)),
        "forward_used": budget.get("used"),
        "forward_total": budget.get("total"),
    }


def budget_exhausted(session_dir: Path) -> bool:
    budget_path = session_dir / "budget.json"
    if not budget_path.exists():
        return False
    budget = json.loads(budget_path.read_text(encoding="utf-8"))
    return int(budget.get("used", 0)) >= int(budget.get("total", 0))


def main() -> int:
    report = audit_seal()
    print(json.dumps(report, indent=2))
    # Also scan latest session if present
    latest = Path(SESSIONS_DIR) / ".." / "wsp_sessions"
    _ = latest  # keep import used for docs
    return 0 if report["ok"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
