#!/usr/bin/env python3
"""Editable weight store with base snapshot and guarded save_edit."""
from __future__ import annotations

import copy
import json
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import torch
from transformers import AutoModelForCausalLM, AutoTokenizer

from .paths_wsp import MODEL_DIR, PROTECTED_PARAM_SUBSTRINGS


@dataclass
class EditRecord:
    name: str
    param: str
    timestamp: str
    numel: int
    note: str = ""


@dataclass
class WeightStore:
    model_dir: Path
    device: torch.device
    dtype: torch.dtype
    tokenizer: Any
    model: Any
    base_state: dict[str, torch.Tensor]
    working_state: dict[str, torch.Tensor]
    edits: list[EditRecord] = field(default_factory=list)

    @classmethod
    def load(cls, model_dir: Path | None = None) -> "WeightStore":
        model_dir = Path(model_dir or MODEL_DIR)
        if not model_dir.exists():
            raise FileNotFoundError(f"Model not found: {model_dir}. Run download_model.py first.")
        device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
        dtype = torch.bfloat16 if device.type == "cuda" else torch.float32
        tokenizer = AutoTokenizer.from_pretrained(model_dir)
        model = AutoModelForCausalLM.from_pretrained(model_dir, torch_dtype=dtype)
        model.to(device)
        model.eval()
        for p in model.parameters():
            p.requires_grad_(False)
        base_state = {k: v.detach().cpu().clone() for k, v in model.state_dict().items()}
        working_state = copy.deepcopy(base_state)
        return cls(
            model_dir=model_dir,
            device=device,
            dtype=dtype,
            tokenizer=tokenizer,
            model=model,
            base_state=base_state,
            working_state=working_state,
        )

    def list_params(self, substr: str | None = None) -> list[dict[str, Any]]:
        out = []
        for name, tensor in self.working_state.items():
            if substr and substr not in name:
                continue
            out.append(
                {
                    "name": name,
                    "shape": list(tensor.shape),
                    "dtype": str(tensor.dtype),
                    "numel": int(tensor.numel()),
                    "protected": self.is_protected(name),
                }
            )
        return out

    def is_protected(self, param: str) -> bool:
        return any(s in param for s in PROTECTED_PARAM_SUBSTRINGS)

    def get_tensor(self, param: str, *, source: str = "working") -> torch.Tensor:
        state = self._state(source)
        if param not in state:
            raise KeyError(f"Unknown param: {param}")
        return state[param].clone()

    def _state(self, source: str) -> dict[str, torch.Tensor]:
        if source == "working":
            return self.working_state
        if source == "base":
            return self.base_state
        raise ValueError("source must be 'working' or 'base'")

    def _reject_scalar_rescale(self, param: str, new: torch.Tensor) -> None:
        old = self.base_state[param].float()
        new_f = new.detach().cpu().float()
        if old.shape != new_f.shape:
            raise ValueError(f"Shape mismatch for {param}: {tuple(old.shape)} vs {tuple(new_f.shape)}")
        # Reject pure global scale of the whole tensor: new ≈ k * old
        old_flat = old.reshape(-1)
        new_flat = new_f.reshape(-1)
        denom = torch.dot(old_flat, old_flat).item()
        if denom <= 0:
            return
        k = torch.dot(new_flat, old_flat).item() / denom
        recon = k * old_flat
        rel = torch.norm(new_flat - recon).item() / (torch.norm(new_flat).item() + 1e-8)
        if rel < 1e-5 and abs(k - 1.0) > 1e-5:
            raise ValueError(
                f"Refused save_edit on {param}: looks like whole-tensor rescale (k≈{k:.4f})."
            )

    def save_edit(self, name: str, param: str, tensor: torch.Tensor, note: str = "") -> EditRecord:
        if self.is_protected(param):
            raise ValueError(f"Refused save_edit: protected parameter '{param}'")
        if param not in self.working_state:
            raise KeyError(f"Unknown param: {param}")
        if not isinstance(tensor, torch.Tensor):
            raise TypeError("tensor must be a torch.Tensor")
        if tensor.requires_grad:
            raise ValueError("Refused save_edit: tensor requires_grad (no training path)")
        t = tensor.detach().cpu().to(self.working_state[param].dtype)
        if tuple(t.shape) != tuple(self.working_state[param].shape):
            raise ValueError(
                f"Shape mismatch for {param}: expected {tuple(self.working_state[param].shape)}, got {tuple(t.shape)}"
            )
        self._reject_scalar_rescale(param, t)
        self.working_state[param] = t.contiguous()
        # Keep live model in sync for forward passes
        with torch.no_grad():
            self.model.load_state_dict(self.working_state, strict=True)
            self.model.to(self.device)
        rec = EditRecord(
            name=name,
            param=param,
            timestamp=datetime.now(timezone.utc).isoformat(),
            numel=int(t.numel()),
            note=note,
        )
        self.edits.append(rec)
        return rec

    def revert_param(self, param: str) -> None:
        if param not in self.base_state:
            raise KeyError(param)
        self.working_state[param] = self.base_state[param].clone()
        with torch.no_grad():
            self.model.load_state_dict(self.working_state, strict=True)
            self.model.to(self.device)
        self.edits.append(
            EditRecord(
                name=f"revert:{param}",
                param=param,
                timestamp=datetime.now(timezone.utc).isoformat(),
                numel=int(self.working_state[param].numel()),
                note="reverted to base",
            )
        )

    def revert_all(self) -> None:
        self.working_state = copy.deepcopy(self.base_state)
        with torch.no_grad():
            self.model.load_state_dict(self.working_state, strict=True)
            self.model.to(self.device)
        self.edits.append(
            EditRecord(
                name="revert_all",
                param="*",
                timestamp=datetime.now(timezone.utc).isoformat(),
                numel=0,
                note="full revert to base",
            )
        )

    def diff_stats(self, param: str | None = None) -> list[dict[str, Any]]:
        names = [param] if param else list(self.working_state.keys())
        stats = []
        for name in names:
            if name not in self.working_state:
                continue
            a = self.base_state[name].float().reshape(-1)
            b = self.working_state[name].float().reshape(-1)
            delta = b - a
            changed = bool(torch.any(delta != 0).item())
            if not changed and param is None:
                continue
            stats.append(
                {
                    "param": name,
                    "changed": changed,
                    "l2": float(torch.norm(delta).item()),
                    "max_abs": float(delta.abs().max().item()) if delta.numel() else 0.0,
                    "frac_nonzero_delta": float((delta != 0).float().mean().item()),
                }
            )
        return stats

    def export_state(self, out_dir: Path) -> Path:
        out_dir.mkdir(parents=True, exist_ok=True)
        path = out_dir / "edited_state.pt"
        torch.save(self.working_state, path)
        meta = {
            "model_dir": str(self.model_dir),
            "edits": [e.__dict__ for e in self.edits],
            "changed_params": [d["param"] for d in self.diff_stats()],
        }
        (out_dir / "edits.json").write_text(json.dumps(meta, indent=2), encoding="utf-8")
        return path
