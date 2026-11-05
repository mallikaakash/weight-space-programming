#!/usr/bin/env python3
"""Metered forward-pass tool (exp8-aligned: generate | inspect; which=base|edited|both).

One successful pass costs one budget unit. Failed requests do not count (exp8).
"""
from __future__ import annotations

import importlib.util
import sys
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import torch
import torch.nn.functional as F

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


@torch.inference_mode()
def inspect_one(
    store: WeightStore,
    ex: dict[str, Any],
    *,
    layers: list[int] | None = None,
) -> dict[str, Any]:
    """Teacher-forced read of (prompt + expected assistant JSON).

    Returns mean token NLL on the assistant span plus optional residual-stream
    norms at requested layers (taken at the last prompt token).
    """
    tokenizer = store.tokenizer
    model = store.model
    messages = build_messages(ex)
    prompt = tokenizer.apply_chat_template(messages, tokenize=False, add_generation_prompt=True)
    # Expected tool call as the assistant continuation (teacher-forced target).
    expected = ex.get("expected")
    if isinstance(expected, dict):
        import json as _json

        target_text = _json.dumps(expected, separators=(",", ":"))
    else:
        target_text = str(expected)
    full = prompt + target_text
    prompt_ids = tokenizer(prompt, return_tensors="pt")["input_ids"]
    full_ids = tokenizer(full, return_tensors="pt")["input_ids"]
    input_ids = full_ids.to(store.device)
    prompt_len = int(prompt_ids.shape[-1])

    out = model(input_ids=input_ids, output_hidden_states=bool(layers), return_dict=True)
    logits = out.logits  # [1, T, V]
    # Next-token prediction: score tokens prompt_len .. end-1 predicting targets
    if input_ids.shape[-1] <= prompt_len:
        mean_nll = float("nan")
        n_target = 0
    else:
        # logits[t] predicts token t+1; targets are tokens at positions prompt_len..
        pred_logits = logits[0, prompt_len - 1 : -1, :]
        targets = input_ids[0, prompt_len:]
        nll = F.cross_entropy(pred_logits.float(), targets, reduction="mean")
        mean_nll = float(nll.item())
        n_target = int(targets.numel())

    layer_stats: dict[str, Any] = {}
    if layers and out.hidden_states is not None:
        # hidden_states[0]=embeddings, [i]=after layer i-1 ... last after final layer
        hs = out.hidden_states
        # Use last prompt token position
        pos = prompt_len - 1
        for li in layers:
            # Map layer index 0..n_layers to hidden_states index (1 + li for post-layer)
            idx = min(max(li + 1, 0), len(hs) - 1)
            h = hs[idx][0, pos, :].float()
            layer_stats[str(li)] = {
                "l2": float(torch.norm(h).item()),
                "mean": float(h.mean().item()),
                "abs_max": float(h.abs().max().item()),
            }

    return {
        "id": ex["id"],
        "mean_nll": mean_nll,
        "n_target_tokens": n_target,
        "layer_stats": layer_stats,
    }


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

    def _select_examples(
        self,
        example_ids: list[str] | None,
        max_examples: int,
    ) -> list[dict[str, Any]]:
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
        # Leakage: never allow non-train
        bad = [ex["id"] for ex in examples if ex.get("split") not in (None, "train")]
        if bad:
            raise RuntimeError(f"Refused forward: non-train ids in batch: {bad[:5]}")
        return examples

    def _with_weights(self, which: str):
        """Context-like helper: load base or keep working. Returns restore flag."""
        if which == "base":
            with torch.no_grad():
                self.store.model.load_state_dict(self.store.base_state, strict=True)
                self.store.model.to(self.store.device)
            return True
        return False

    def _restore_working(self) -> None:
        with torch.no_grad():
            self.store.model.load_state_dict(self.store.working_state, strict=True)
            self.store.model.to(self.store.device)

    def _generate_batch(
        self,
        examples: list[dict[str, Any]],
        *,
        max_new_tokens: int,
        temperature: float,
    ) -> list[dict[str, Any]]:
        rows = []
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
        return rows

    def forward_pass(
        self,
        example_ids: list[str] | None = None,
        *,
        max_examples: int = 32,
        max_new_tokens: int = 128,
        temperature: float = 0.0,
        which: str = "edited",
        mode: str = "generate",
        layers: list[int] | None = None,
    ) -> dict[str, Any]:
        """Spend one budget unit on a successful generate or inspect pass.

        which: 'base' | 'edited' | 'both'  (exp8: original / edited / both)
        mode:  'generate' | 'inspect'      (exp8: generate / teacher_forced)
        """
        # Normalize aliases from exp8 wording
        which_map = {"original": "base", "base": "base", "edited": "edited", "both": "both"}
        mode_map = {
            "generate": "generate",
            "inspect": "inspect",
            "teacher_forced": "inspect",
            "teacher-forced": "inspect",
        }
        if which not in which_map:
            raise ValueError("which must be 'base'|'edited'|'both' (or 'original')")
        if mode not in mode_map:
            raise ValueError("mode must be 'generate' or 'inspect' (teacher_forced)")
        which = which_map[which]
        mode = mode_map[mode]

        if self.budget.remaining <= 0:
            raise RuntimeError(f"Forward budget exhausted ({self.budget.used}/{self.budget.total})")

        examples = self._select_examples(example_ids, max_examples)

        # Run first; only consume on success (exp8: failed request does not count).
        try:
            if mode == "generate":
                result = self._run_generate(
                    examples,
                    which=which,
                    max_new_tokens=max_new_tokens,
                    temperature=temperature,
                )
            else:
                result = self._run_inspect(examples, which=which, layers=layers or [])
        except Exception:
            # Do not consume budget on failure.
            raise

        self.budget.consume(1)
        entry = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "mode": mode,
            "which": which,
            "n": len(examples),
            "ids": [ex["id"] for ex in examples],
            "summary": result.get("summary"),
            "budget_after": self.budget.used,
        }
        self.budget.log.append(entry)
        result["budget"] = self.status()
        return result

    def _run_generate(
        self,
        examples: list[dict[str, Any]],
        *,
        which: str,
        max_new_tokens: int,
        temperature: float,
    ) -> dict[str, Any]:
        if which == "both":
            # Cap: with both, compare on same problems (exp8: half capacity each).
            # Our practice set is tiny (40); still allow full batch for both.
            restored = self._with_weights("base")
            try:
                base_rows = self._generate_batch(
                    examples, max_new_tokens=max_new_tokens, temperature=temperature
                )
            finally:
                if restored:
                    self._restore_working()
            edited_rows = self._generate_batch(
                examples, max_new_tokens=max_new_tokens, temperature=temperature
            )
            base_sum = summarize(base_rows)
            edited_sum = summarize(edited_rows)
            paired = []
            for b, e in zip(base_rows, edited_rows):
                paired.append(
                    {
                        "id": b["id"],
                        "base_strict_ok": bool((b.get("scores") or {}).get("strict_ok")),
                        "edited_strict_ok": bool((e.get("scores") or {}).get("strict_ok")),
                        "delta_strict": int(bool((e.get("scores") or {}).get("strict_ok")))
                        - int(bool((b.get("scores") or {}).get("strict_ok"))),
                        "base_completion": (b.get("completion") or "")[:200],
                        "edited_completion": (e.get("completion") or "")[:200],
                    }
                )
            n = len(paired) or 1
            mean_delta = sum(p["delta_strict"] for p in paired) / n
            improved = sum(1 for p in paired if p["delta_strict"] > 0)
            worsened = sum(1 for p in paired if p["delta_strict"] < 0)
            summary = {
                "mode": "generate",
                "which": "both",
                "base": base_sum,
                "edited": edited_sum,
                "paired_mean_delta_strict": mean_delta,
                "n_improved": improved,
                "n_worsened": worsened,
                "n": len(paired),
            }
            return {
                "summary": summary,
                "examples": edited_rows,
                "paired": paired,
                "base_examples": base_rows,
            }

        restored = self._with_weights(which)
        try:
            rows = self._generate_batch(
                examples, max_new_tokens=max_new_tokens, temperature=temperature
            )
        finally:
            if restored:
                self._restore_working()
        summary = summarize(rows)
        summary = {**summary, "mode": "generate", "which": which}
        return {"summary": summary, "examples": rows}

    def _run_inspect(
        self,
        examples: list[dict[str, Any]],
        *,
        which: str,
        layers: list[int],
    ) -> dict[str, Any]:
        def _batch() -> list[dict[str, Any]]:
            return [inspect_one(self.store, ex, layers=layers) for ex in examples]

        if which == "both":
            restored = self._with_weights("base")
            try:
                base_rows = _batch()
            finally:
                if restored:
                    self._restore_working()
            edited_rows = _batch()
            paired = []
            for b, e in zip(base_rows, edited_rows):
                paired.append(
                    {
                        "id": b["id"],
                        "base_mean_nll": b["mean_nll"],
                        "edited_mean_nll": e["mean_nll"],
                        "delta_nll": (e["mean_nll"] - b["mean_nll"])
                        if (e["mean_nll"] == e["mean_nll"] and b["mean_nll"] == b["mean_nll"])
                        else None,
                    }
                )
            valid = [p["delta_nll"] for p in paired if p["delta_nll"] is not None]
            summary = {
                "mode": "inspect",
                "which": "both",
                "n": len(paired),
                "mean_delta_nll": (sum(valid) / len(valid)) if valid else None,
                "layers": layers,
            }
            return {"summary": summary, "examples": edited_rows, "paired": paired, "base_examples": base_rows}

        restored = self._with_weights(which)
        try:
            rows = _batch()
        finally:
            if restored:
                self._restore_working()
        valid = [r["mean_nll"] for r in rows if r["mean_nll"] == r["mean_nll"]]
        summary = {
            "mode": "inspect",
            "which": which,
            "n": len(rows),
            "mean_nll": (sum(valid) / len(valid)) if valid else None,
            "layers": layers,
        }
        return {"summary": summary, "examples": rows}
