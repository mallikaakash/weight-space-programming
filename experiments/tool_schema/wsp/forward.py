#!/usr/bin/env python3
"""Metered forward-pass tool (generate + score on practice examples)."""
from __future__ import annotations

import importlib.util
import sys
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import torch

from .practice import tools_by_name
from .weights import WeightStore

EXPERIMENT_ROOT = Path(__file__).resolve().parents[1]


def _load_score_module():
    path = EXPERIMENT_ROOT / "score.py"
    spec = importlib.util.spec_from_file_location("tool_schema_score", path)
    if spec is None or spec.loader is None:
        raise ImportError(f"Cannot load {path}")
    mod = importlib.util.module_from_spec(spec)
    sys.modules["tool_schema_score"] = mod
    spec.loader.exec_module(mod)
    return mod


_score = _load_score_module()
score_example = _score.score_example
summarize = _score.summarize


def build_messages(ex: dict) -> list[dict[str, str]]:
    return [
        {"role": "system", "content": ex["system"]},
        {"role": "user", "content": ex["user"]},
    ]


@torch.inference_mode()
def generate_one(
    store: WeightStore,
    messages: list[dict[str, str]],
    max_new_tokens: int = 128,
    temperature: float = 0.0,
) -> str:
    tokenizer = store.tokenizer
    model = store.model
    prompt = tokenizer.apply_chat_template(messages, tokenize=False, add_generation_prompt=True)
    inputs = tokenizer(prompt, return_tensors="pt")
    inputs = {k: v.to(store.device) for k, v in inputs.items()}
    gen_kwargs: dict[str, Any] = {
        "max_new_tokens": max_new_tokens,
        "pad_token_id": tokenizer.eos_token_id,
    }
    if temperature and temperature > 0:
        gen_kwargs.update(do_sample=True, temperature=temperature, top_p=0.9)
    else:
        gen_kwargs.update(do_sample=False)
    out = model.generate(**inputs, **gen_kwargs)
    new_tokens = out[0, inputs["input_ids"].shape[-1] :]
    return tokenizer.decode(new_tokens, skip_special_tokens=True).strip()


@dataclass
class ForwardBudget:
    total: int
    used: int = 0
    log: list[dict[str, Any]] = field(default_factory=list)

    @property
    def remaining(self) -> int:
        return max(0, self.total - self.used)

    def consume(self, n: int = 1) -> None:
        if self.used + n > self.total:
            raise RuntimeError(f"Forward budget exhausted ({self.used}/{self.total})")
        self.used += n


@dataclass
class ForwardService:
    store: WeightStore
    practice: list[dict[str, Any]]
    budget: ForwardBudget
    by_id: dict[str, dict[str, Any]] = field(init=False)
    tools: dict[str, Any] = field(init=False)

    def __post_init__(self) -> None:
        self.by_id = {ex["id"]: ex for ex in self.practice}
        self.tools = tools_by_name()

    def status(self) -> dict[str, Any]:
        return {
            "forward_total": self.budget.total,
            "forward_used": self.budget.used,
            "forward_remaining": self.budget.remaining,
            "practice_n": len(self.practice),
        }

    def forward_pass(
        self,
        example_ids: list[str] | None = None,
        *,
        max_examples: int = 32,
        max_new_tokens: int = 128,
        temperature: float = 0.0,
        which: str = "edited",
    ) -> dict[str, Any]:
        """Spend one budget unit to generate+score a practice batch.

        which: 'edited' uses current working weights (already loaded on model).
               'base' temporarily loads base weights for the batch then restores.
        """
        if which not in {"edited", "base"}:
            raise ValueError("which must be 'edited' or 'base'")
        self.budget.consume(1)

        if example_ids:
            examples = [self.by_id[i] for i in example_ids if i in self.by_id]
            missing = [i for i in example_ids if i not in self.by_id]
            if missing:
                raise KeyError(f"Unknown practice ids (train only): {missing[:5]}")
        else:
            examples = self.practice[:max_examples]
        examples = examples[:max_examples]
        if not examples:
            raise ValueError("No practice examples selected")

        restored = False
        if which == "base":
            with torch.no_grad():
                self.store.model.load_state_dict(self.store.base_state, strict=True)
                self.store.model.to(self.store.device)
            restored = True

        rows = []
        try:
            for ex in examples:
                completion = generate_one(
                    self.store,
                    build_messages(ex),
                    max_new_tokens=max_new_tokens,
                    temperature=temperature,
                )
                scores = score_example(ex["expected"], completion, self.tools)
                rows.append(
                    {
                        "id": ex["id"],
                        "tier": ex.get("tier"),
                        "split": ex.get("split"),
                        "user": ex["user"],
                        "expected": ex["expected"],
                        "completion": completion,
                        "scores": {k: v for k, v in scores.items() if k != "parsed"},
                        "parsed": scores.get("parsed"),
                    }
                )
        finally:
            if restored:
                with torch.no_grad():
                    self.store.model.load_state_dict(self.store.working_state, strict=True)
                    self.store.model.to(self.store.device)

        summary = summarize(rows)
        entry = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "which": which,
            "n": len(rows),
            "ids": [r["id"] for r in rows],
            "summary": summary,
            "budget_after": self.budget.used,
        }
        self.budget.log.append(
            {k: entry[k] for k in ("timestamp", "which", "n", "ids", "summary", "budget_after")}
        )
        return {"summary": summary, "examples": rows, "budget": self.status()}
