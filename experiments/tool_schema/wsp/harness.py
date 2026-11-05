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
from .weights import EditRecord, WeightStore


class WSPHarness:
    """API for weight-space programming sessions (persists across process restarts)."""

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
        # Always sealed train-only practice (exp8: none from the test sets).
        self.practice = load_practice("train")
        practice_ids = {ex["id"] for ex in self.practice}
        if any(ex.get("split") not in (None, "train") for ex in self.practice):
            raise RuntimeError("Leakage: practice contains non-train rows")
        self._practice_ids = practice_ids

        budget_path = self.session_dir / "budget.json"
        working_path = self.session_dir / "working_state.pt"
        resumed = False

        used = 0
        log: list[dict[str, Any]] = []
        total = forward_budget
        if budget_path.exists():
            saved = json.loads(budget_path.read_text(encoding="utf-8"))
            total = int(saved.get("total", forward_budget))
            used = int(saved.get("used", 0))
            log = list(saved.get("log") or [])
            resumed = True

        if working_path.exists():
            state = torch.load(working_path, map_location="cpu", weights_only=True)
            self.store.working_state = state
            with torch.no_grad():
                self.store.model.load_state_dict(self.store.working_state, strict=True)
                self.store.model.to(self.store.device)
            resumed = True

        state_path = self.session_dir / "state.json"
        if state_path.exists():
            prev = json.loads(state_path.read_text(encoding="utf-8"))
            edits = []
            for e in prev.get("edits") or []:
                edits.append(EditRecord(**e))
            self.store.edits = edits
            resumed = True

        self.forward = ForwardService(
            store=self.store,
            practice=self.practice,
            budget=ForwardBudget(total=total, used=used, log=log),
        )
        self._persist_state(event="resume" if resumed else "init")

    def status(self) -> dict[str, Any]:
        task = (self.practice[0].get("task") if self.practice else None) or "tool_schema"
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
            "practice_source": "wsp/practice/train.jsonl",
            "practice_task": task,
            "test_sealed": True,
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
        (self.session_dir / "last_forward.json").write_text(
            json.dumps({"summary": result["summary"], "budget": result["budget"]}, indent=2),
            encoding="utf-8",
        )
        failures = []
        for row in result.get("examples") or []:
            scores = row.get("scores") or {}
            if scores.get("strict_ok"):
                continue
            failed = [k for k, v in scores.items() if v is False]
            failures.append(
                {
                    "id": row.get("id"),
                    "tier": row.get("tier"),
                    "user": row.get("user"),
                    "expected": row.get("expected"),
                    "completion": (row.get("completion") or "")[:400],
                    "failed_flags": failed,
                }
            )
        (self.session_dir / "last_forward_failures.json").write_text(
            json.dumps({"n_fail": len(failures), "failures": failures[:30]}, indent=2),
            encoding="utf-8",
        )
        return result

    def export(self) -> dict[str, Any]:
        path = self.store.export_state(self.session_dir / "export")
        self._persist_state(event="export")
        return {"edited_state": str(path), "session_dir": str(self.session_dir)}

    def _persist_state(self, event: str) -> None:
        # Persist tensors + budget so a new Python process can resume the same session.
        torch.save(self.store.working_state, self.session_dir / "working_state.pt")
        (self.session_dir / "budget.json").write_text(
            json.dumps(
                {
                    "total": self.forward.budget.total,
                    "used": self.forward.budget.used,
                    "log": self.forward.budget.log,
                },
                indent=2,
            ),
            encoding="utf-8",
        )
        payload = {
            "event": event,
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "status": self.status(),
            "edits": [e.__dict__ for e in self.store.edits],
            "forward_log": self.forward.budget.log,
        }
        (self.session_dir / "state.json").write_text(json.dumps(payload, indent=2), encoding="utf-8")
        with (self.session_dir / "events.jsonl").open("a", encoding="utf-8") as f:
            f.write(json.dumps({"event": event, "timestamp": payload["timestamp"]}) + "\n")
