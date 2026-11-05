#!/usr/bin/env python3
"""Unit tests for WSP harness guards (no full model generate required for most)."""
from __future__ import annotations

import json
import sys
from pathlib import Path
from unittest.mock import MagicMock

import torch

EXPERIMENT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(EXPERIMENT_ROOT))

from wsp.leakage_guard import audit_seal  # noqa: E402
from wsp.paths_wsp import PRACTICE_TRAIN_PATH, PROTECTED_PARAM_SUBSTRINGS  # noqa: E402
from wsp.practice import load_practice  # noqa: E402
from wsp.sandbox import SandboxError, run_sandbox_script  # noqa: E402
from wsp.weights import WeightStore  # noqa: E402


def _fake_store() -> WeightStore:
    """Construct a WeightStore-like object without loading SmolLM."""
    base = {
        "model.layers.0.mlp.down_proj.weight": torch.zeros(4, 4),
        "model.embed_tokens.weight": torch.zeros(8, 4),
        "model.norm.weight": torch.ones(4),
        "lm_head.weight": torch.zeros(8, 4),
    }
    working = {k: v.clone() for k, v in base.items()}
    store = WeightStore(
        model_dir=Path("/tmp"),
        device=torch.device("cpu"),
        dtype=torch.float32,
        tokenizer=None,
        model=MagicMock(),
        base_state=base,
        working_state=working,
    )

    def _load_state_dict(state, strict=True):  # noqa: ARG001
        return None

    store.model.load_state_dict = _load_state_dict
    store.model.to = lambda *a, **k: store.model
    return store


def test_protected_params():
    store = _fake_store()
    assert store.is_protected("model.embed_tokens.weight")
    assert store.is_protected("lm_head.weight")
    assert store.is_protected("model.norm.weight")
    assert not store.is_protected("model.layers.0.mlp.down_proj.weight")
    assert any("embed" in s or "lm_head" in s for s in PROTECTED_PARAM_SUBSTRINGS)


def test_save_edit_and_revert():
    store = _fake_store()
    param = "model.layers.0.mlp.down_proj.weight"
    t = store.get_tensor(param)
    store.save_edit("nudge", param, t + 0.1)
    assert store.diff_stats(param)[0]["changed"]
    store.revert_param(param)
    assert not store.diff_stats(param)[0]["changed"]


def test_refuse_protected_edit():
    store = _fake_store()
    try:
        store.save_edit("bad", "lm_head.weight", store.get_tensor("lm_head.weight") + 1)
        raise AssertionError("expected ValueError")
    except ValueError as e:
        assert "protected" in str(e).lower()


def test_refuse_whole_tensor_rescale():
    store = _fake_store()
    param = "model.layers.0.mlp.down_proj.weight"
    store.working_state[param] = torch.randn(4, 4)
    store.base_state[param] = store.working_state[param].clone()
    try:
        store.save_edit("scale", param, store.base_state[param] * 2.0)
        raise AssertionError("expected ValueError")
    except ValueError as e:
        assert "rescale" in str(e).lower()


def test_sandbox_forbids_import():
    class Dummy:
        def status(self):
            return {}

    try:
        run_sandbox_script(Dummy(), "import os\nresult=1")  # type: ignore[arg-type]
        raise AssertionError("expected SandboxError")
    except SandboxError:
        pass


def test_practice_train_only():
    assert PRACTICE_TRAIN_PATH.exists(), PRACTICE_TRAIN_PATH
    rows = load_practice("train")
    assert len(rows) == 40
    assert all(r.get("split") in (None, "train") for r in rows)
    report = audit_seal()
    assert report["ok"], report["issues"]
    assert report["overlap"] == []
    assert report["train_n"] == 40
    assert report["test_n"] == 20


def test_forward_budget_aliases():
    from wsp.forward import ForwardBudget, ForwardService

    store = _fake_store()
    practice = [
        {
            "id": "easy-01",
            "split": "train",
            "tier": "easy",
            "system": "sys",
            "user": "u",
            "expected": {"tool": "t", "arguments": {}},
        }
    ]
    # tools_by_name needs tools.json — skip full generate; just check which/mode validation
    svc = ForwardService(store=store, practice=practice, budget=ForwardBudget(total=2))
    try:
        svc.forward_pass(mode="nope")
        raise AssertionError("expected ValueError")
    except ValueError:
        pass
    try:
        svc.forward_pass(which="nope")
        raise AssertionError("expected ValueError")
    except ValueError:
        pass
    # Unknown practice id refused
    try:
        svc.forward_pass(example_ids=["test-leak-id"])
        raise AssertionError("expected KeyError")
    except KeyError as e:
        assert "train only" in str(e).lower() or "unknown" in str(e).lower()


def main() -> None:
    test_protected_params()
    test_save_edit_and_revert()
    test_refuse_protected_edit()
    test_refuse_whole_tensor_rescale()
    test_sandbox_forbids_import()
    test_practice_train_only()
    test_forward_budget_aliases()
    print("ok")


if __name__ == "__main__":
    main()
