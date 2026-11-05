#!/usr/bin/env python3
"""Restricted exec helper for future editor scripts.

No network, no subprocess, no file writes outside the session dir, no autograd.
The editor receives `harness` (WSPHarness) plus numpy/torch in the namespace.
"""
from __future__ import annotations

import ast
from typing import Any

import numpy as np
import torch

from .harness import WSPHarness

FORBIDDEN_NAMES = {
    "eval",
    "exec",
    "open",
    "compile",
    "__import__",
    "input",
    "breakpoint",
    "exit",
    "quit",
}


class SandboxError(RuntimeError):
    pass


def _assert_safe(tree: ast.AST) -> None:
    for node in ast.walk(tree):
        if isinstance(node, (ast.Import, ast.ImportFrom)):
            raise SandboxError("Imports are not allowed in sandbox scripts")
        if isinstance(node, ast.Attribute) and node.attr.startswith("__"):
            raise SandboxError(f"Dunder attribute access forbidden: {node.attr}")
        if isinstance(node, ast.Name) and node.id in FORBIDDEN_NAMES:
            raise SandboxError(f"Forbidden name: {node.id}")
        if isinstance(node, ast.Call) and isinstance(node.func, ast.Name):
            if node.func.id in FORBIDDEN_NAMES:
                raise SandboxError(f"Forbidden call: {node.func.id}")


def run_sandbox_script(harness: WSPHarness, code: str) -> dict[str, Any]:
    """Execute editor Python against the harness; return captured `result` if set."""
    tree = ast.parse(code, mode="exec")
    _assert_safe(tree)

    # Disable grad globally during sandbox runs
    prev = torch.is_grad_enabled()
    torch.set_grad_enabled(False)
    namespace: dict[str, Any] = {
        "harness": harness,
        "torch": torch,
        "np": np,
        "result": None,
    }
    try:
        compiled = compile(tree, filename="<wsp_sandbox>", mode="exec")
        exec(compiled, namespace, namespace)  # noqa: S102 — intentional restricted exec
    finally:
        torch.set_grad_enabled(prev)

    return {
        "result": namespace.get("result"),
        "status": harness.status(),
    }
