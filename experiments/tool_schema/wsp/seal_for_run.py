#!/usr/bin/env python3
"""Quarantine holdout test material for a long WSP editor run.

Moves sealed test (+ any live dataset test exposure) outside the workspace so
Claude Code with --add-dir /workspace cannot read test examples mid-run.
"""
from __future__ import annotations

import argparse
import json
import shutil
import sys
from pathlib import Path

_WSP = Path(__file__).resolve().parent
if str(_WSP) not in sys.path:
    sys.path.insert(0, str(_WSP))

from paths_wsp import (  # noqa: E402
    EVAL_PATH,
    EXPERIMENT_ROOT,
    PRACTICE_TRAIN_PATH,
    REPO_ROOT,
    SEALED_DIR,
    SEALED_FULL_PATH,
    SEALED_TEST_PATH,
)

DEFAULT_SEAL = Path("/tmp/wsp_seal")


def _load_jsonl(path: Path) -> list[dict]:
    rows = []
    if not path.exists():
        return rows
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if line:
            rows.append(json.loads(line))
    return rows


def _write_jsonl(path: Path, rows: list[dict]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(json.dumps(r) for r in rows) + ("\n" if rows else ""), encoding="utf-8")


def seal(seal_dir: Path) -> dict:
    seal_dir.mkdir(parents=True, exist_ok=True)
    manifest: dict = {"seal_dir": str(seal_dir), "moved": [], "stubbed": []}

    # Ensure practice train exists
    if not PRACTICE_TRAIN_PATH.exists():
        raise SystemExit(f"missing {PRACTICE_TRAIN_PATH}")
    train = _load_jsonl(PRACTICE_TRAIN_PATH)

    # Move sealed eval artifacts out of the repo (tool-schema + BFCL-native).
    for src in (
        SEALED_TEST_PATH,
        SEALED_FULL_PATH,
        SEALED_DIR / "splits.json",
        SEALED_DIR / "bfcl_splits.json",
        SEALED_DIR / "bfcl_test.jsonl",
    ):
        if src.exists():
            dst = seal_dir / src.name
            if dst.exists():
                if dst.is_dir():
                    shutil.rmtree(dst)
                else:
                    dst.unlink()
            shutil.move(str(src), str(dst))
            manifest["moved"].append({"from": str(src), "to": str(dst)})

    # If sealed dir empty, remove it; else leave leftovers
    if SEALED_DIR.exists() and not any(SEALED_DIR.iterdir()):
        SEALED_DIR.rmdir()

    # Stub live dataset.jsonl to train-only (so accidental opens see no test)
    if EVAL_PATH.exists():
        backup = seal_dir / "dataset.jsonl.pre_seal"
        if not backup.exists():
            shutil.copy2(EVAL_PATH, backup)
            manifest["moved"].append({"from": str(EVAL_PATH), "to": str(backup), "copy": True})
        _write_jsonl(EVAL_PATH, train)
        manifest["stubbed"].append(str(EVAL_PATH))

    # Hide result artifacts that embed test completions / spotchecks
    hide_candidates = [
        EXPERIMENT_ROOT / "results",
        REPO_ROOT / "artifacts" / "baselines",
    ]
    for path in hide_candidates:
        if path.exists():
            dst = seal_dir / "hidden" / path.name
            dst.parent.mkdir(parents=True, exist_ok=True)
            if dst.exists():
                continue
            shutil.move(str(path), str(dst))
            manifest["moved"].append({"from": str(path), "to": str(dst)})

    # Keep wsp/results RUNNING_LOG writable — do not move wsp/results
    (seal_dir / "manifest.json").write_text(json.dumps(manifest, indent=2), encoding="utf-8")
    return manifest


def unseal(seal_dir: Path) -> dict:
    manifest_path = seal_dir / "manifest.json"
    if not manifest_path.exists():
        raise SystemExit(f"no manifest at {manifest_path}")
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    restored = []
    # Restore in reverse order
    for item in reversed(manifest.get("moved") or []):
        src = Path(item["to"])
        dst = Path(item["from"])
        if item.get("copy"):
            # restore original dataset from backup copy
            if src.exists():
                dst.parent.mkdir(parents=True, exist_ok=True)
                shutil.copy2(src, dst)
                restored.append(str(dst))
            continue
        if src.exists():
            dst.parent.mkdir(parents=True, exist_ok=True)
            if dst.exists():
                if dst.is_dir():
                    shutil.rmtree(dst)
                else:
                    dst.unlink()
            shutil.move(str(src), str(dst))
            restored.append(str(dst))

    # Always prefer restoring the pre-seal full dataset if the backup remains.
    pre = seal_dir / "dataset.jsonl.pre_seal"
    if pre.exists():
        EVAL_PATH.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(pre, EVAL_PATH)
        if str(EVAL_PATH) not in restored:
            restored.append(str(EVAL_PATH))

    # Ensure sealed test is back for eval
    if not SEALED_TEST_PATH.exists():
        alt = seal_dir / "test.jsonl"
        if alt.exists():
            SEALED_DIR.mkdir(parents=True, exist_ok=True)
            shutil.copy2(alt, SEALED_TEST_PATH)
            restored.append(str(SEALED_TEST_PATH))

    return {"restored": restored}


def main() -> int:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("action", choices=["seal", "unseal", "status"])
    p.add_argument("--seal-dir", type=Path, default=DEFAULT_SEAL)
    args = p.parse_args()
    if args.action == "seal":
        print(json.dumps(seal(args.seal_dir), indent=2))
    elif args.action == "unseal":
        print(json.dumps(unseal(args.seal_dir), indent=2))
    else:
        man = args.seal_dir / "manifest.json"
        print(
            json.dumps(
                {
                    "seal_dir": str(args.seal_dir),
                    "manifest_exists": man.exists(),
                    "practice_train_exists": PRACTICE_TRAIN_PATH.exists(),
                    "live_dataset_exists": EVAL_PATH.exists(),
                    "sealed_test_in_repo": SEALED_TEST_PATH.exists(),
                    "sealed_test_in_tmp": (args.seal_dir / "test.jsonl").exists(),
                },
                indent=2,
            )
        )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
