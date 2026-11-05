#!/usr/bin/env python3
"""Unit tests for WSP harness guards (no full model generate required for most)."""
from __future__ import annotations

import sys
from pathlib import Path
from unittest.mock import MagicMock

import torch

EXPERIMENT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(EXPERIMENT_ROOT))

from wsp.paths_wsp import PROTECTED_PARAM_SUBSTRINGS  # noqa: E402
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


def main() -> None:
    test_protected_params()
    test_save_edit_and_revert()
    test_refuse_protected_edit()
    test_refuse_whole_tensor_rescale()
    test_sandbox_forbids_import()
    print("ok")


if __name__ == "__main__":
    main()
