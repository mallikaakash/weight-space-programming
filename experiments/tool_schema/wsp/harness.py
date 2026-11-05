#!/usr/bin/env python3
"""WSP harness: weight store + train practice + metered forward passes."""
from __future__ import annotations

import json
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import torch

from .forward import ForwardBudget, ForwardService
from .paths_wsp import MODEL_DIR, SESSIONS_DIR
from .practice import load_practice
from .weights import WeightStore


class WSPHarness:
    """Preparation API for weight-space programming (no editor agent loop yet)."""

    def __init__(
        self,
        *,
        model_dir: Path | None = None,
        forward_budget: int = 25,
        session_id: str | None = None,
        practice_split: str = "train",
    ) -> None:
        if practice_split != "train":
            raise ValueError("WSP practice must use the train split (test is holdout).")
        self.session_id = session_id or datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ") + "-" + uuid.uuid4().hex[:8]
        self.session_dir = SESSIONS_DIR / self.session_id
        self.session_dir.mkdir(parents=True, exist_ok=True)

        self.store = WeightStore.load(model_dir or MODEL_DIR)
        self.practice = load_practice("train")
        self.forward = ForwardService(
            store=self.store,
            practice=self.practice,
            budget=ForwardBudget(total=forward_budget),
        )
        self._persist_state(event="init")

    # --- inspector API (for future editor) ---

    def status(self) -> dict[str, Any]:
        return {
            "session_id": self.session_id,
            "session_dir": str(self.session_dir),
            "model_dir": str(self.store.model_dir),
            "device": str(self.store.device),
            "n_params": len(self.store.working_state),
            "n_edits": len(self.store.edits),
            "changed_params": [d["param"] for d in self.store.diff_stats()],
            "forward": self.forward.status(),
            "practice_split": "train",
            "practice_n": len(self.practice),
            "practice_ids_head": [ex["id"] for ex in self.practice[:5]],
        }

    def list_params(self, substr: str | None = None) -> list[dict[str, Any]]:
        return self.store.list_params(substr)

    def get_tensor(self, param: str, source: str = "working") -> torch.Tensor:
        return self.store.get_tensor(param, source=source)

    def save_edit(self, name: str, param: str, tensor: torch.Tensor, note: str = "") -> dict[str, Any]:
        rec = self.store.save_edit(name, param, tensor, note=note)
        self._persist_state(event=f"save_edit:{name}")
        return rec.__dict__

    def revert_param(self, param: str) -> None:
        self.store.revert_param(param)
        self._persist_state(event=f"revert:{param}")

    def revert_all(self) -> None:
        self.store.revert_all()
        self._persist_state(event="revert_all")

    def diff_stats(self, param: str | None = None) -> list[dict[str, Any]]:
        return self.store.diff_stats(param)

    def forward_pass(self, **kwargs: Any) -> dict[str, Any]:
        result = self.forward.forward_pass(**kwargs)
        self._persist_state(event="forward_pass")
        # keep last forward summary on disk for inspection
        (self.session_dir / "last_forward.json").write_text(
            json.dumps({"summary": result["summary"], "budget": result["budget"]}, indent=2),
            encoding="utf-8",
        )
        return result

    def export(self) -> dict[str, Any]:
        path = self.store.export_state(self.session_dir / "export")
        self._persist_state(event="export")
        return {"edited_state": str(path), "session_dir": str(self.session_dir)}

    def _persist_state(self, event: str) -> None:
        payload = {
            "event": event,
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "status": self.status(),
            "edits": [e.__dict__ for e in self.store.edits],
            "forward_log": self.forward.budget.log,
        }
        (self.session_dir / "state.json").write_text(json.dumps(payload, indent=2), encoding="utf-8")
        log_path = self.session_dir / "events.jsonl"
        with log_path.open("a", encoding="utf-8") as f:
            f.write(json.dumps({"event": event, "timestamp": payload["timestamp"]}) + "\n")
