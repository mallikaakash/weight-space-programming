#!/usr/bin/env python3
"""Build sealed BFCL simple_python train/test split for WSP.

Uses official BFCL v4 simple_python (400 items) from bfcl-eval:
  - train/practice: ids 0..299  (300)  → editor-visible
  - test/holdout:   ids 300..399 (100) → sealed until budget exhausted

This replaces the homemade tool-schema practice for BFCL-native runs.
"""
from __future__ import annotations

import json
from pathlib import Path

from paths_wsp import PRACTICE_DIR, SEALED_DIR

# Import prompt builders from the eval module (same format the scorer expects).
import sys

EXPERIMENT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(EXPERIMENT_ROOT))
from bfcl_simple_eval import SYSTEM_PROMPT, bfcl_data_paths, build_user_content, load_jsonl  # noqa: E402

TRAIN_N = 300
TEST_N = 100


def main() -> int:
    q_path, a_path = bfcl_data_paths()
    prompts = load_jsonl(q_path)
    answers = load_jsonl(a_path)
    assert len(prompts) == len(answers) == 400
    by_ans = {a["id"]: a for a in answers}

    train_rows = []
    test_rows = []
    for i, ex in enumerate(prompts):
        ans = by_ans[ex["id"]]
        row = {
            "id": ex["id"],
            "split": "train" if i < TRAIN_N else "test",
            "task": "bfcl_simple_python",
            "system": SYSTEM_PROMPT,
            "user": build_user_content(ex),
            "question": ex["question"],
            "function": ex["function"],
            "ground_truth": ans["ground_truth"],
            # For teacher-forced inspect: a representative gold call string.
            "expected_call": _gold_call_string(ans["ground_truth"]),
        }
        if i < TRAIN_N:
            train_rows.append(row)
        else:
            test_rows.append(row)

    assert len(train_rows) == TRAIN_N and len(test_rows) == TEST_N
    # No id overlap
    assert not ({r["id"] for r in train_rows} & {r["id"] for r in test_rows})

    PRACTICE_DIR.mkdir(parents=True, exist_ok=True)
    SEALED_DIR.mkdir(parents=True, exist_ok=True)
    # Harness + seal_for_run expect these canonical paths.
    train_path = PRACTICE_DIR / "train.jsonl"
    test_path = SEALED_DIR / "test.jsonl"
    # Keep an explicit BFCL copy for operators / resume clarity.
    train_copy = PRACTICE_DIR / "bfcl_train.jsonl"
    test_copy = SEALED_DIR / "bfcl_test.jsonl"

    def write(path: Path, rows: list[dict]) -> None:
        path.write_text("\n".join(json.dumps(r) for r in rows) + "\n", encoding="utf-8")

    write(train_path, train_rows)
    write(test_path, test_rows)
    write(train_copy, train_rows)
    write(test_copy, test_rows)

    splits = {
        "task": "bfcl_simple_python",
        "train_ids": [r["id"] for r in train_rows],
        "test_ids": [r["id"] for r in test_rows],
        "train_n": TRAIN_N,
        "test_n": TEST_N,
        "train_id_range": "simple_python_0 .. simple_python_299 (file order 0:300)",
        "test_id_range": "simple_python_300 .. simple_python_399 (file order 300:400)",
        "source": "bfcl-eval BFCL_v4_simple_python.json",
        "metric": "official bfcl_eval.ast_checker (simple_python)",
    }
    (PRACTICE_DIR / "bfcl_splits.json").write_text(json.dumps(splits, indent=2), encoding="utf-8")
    (SEALED_DIR / "bfcl_splits.json").write_text(json.dumps(splits, indent=2), encoding="utf-8")
    # Full sealed dump for restore / audit (train+test).
    write(SEALED_DIR / "dataset_full.jsonl", train_rows + test_rows)
    print(
        json.dumps(
            {
                "wrote_train": str(train_path),
                "wrote_test": str(test_path),
                "train_n": TRAIN_N,
                "test_n": TEST_N,
                "task": "bfcl_simple_python",
            },
            indent=2,
        )
    )
    return 0


def _gold_call_string(ground_truth: list) -> str:
    """Pick first acceptable value per arg to form [name(k=v, ...)]."""
    if not ground_truth:
        return "[]"
    call = ground_truth[0]
    name, args = next(iter(call.items()))
    parts = []
    for k, vals in (args or {}).items():
        if isinstance(vals, list) and vals:
            v = vals[0]
        else:
            v = vals
        if v == "":
            continue
        parts.append(f"{k}={json.dumps(v)}")
    return f"[{name}({', '.join(parts)})]"


if __name__ == "__main__":
    raise SystemExit(main())
