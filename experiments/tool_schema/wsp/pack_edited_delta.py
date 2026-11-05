#!/usr/bin/env python3
"""Pack or apply a compact WSP edited-weight delta.

The session export `edited_state.pt` is a full ~1.6GB state_dict (gitignored).
For hosting, prefer the ~200MB delta of only the changed tensors.

Examples:
  # Pack 32 changed tensors from a session export
  python3 experiments/tool_schema/wsp/pack_edited_delta.py pack \\
    --edited-state artifacts/wsp_sessions/wsp-bfcl-p100-20261105T143615Z/export/edited_state.pt \\
    --edits-json artifacts/wsp_sessions/wsp-bfcl-p100-20261105T143615Z/export/edits.json \\
    --out artifacts/wsp_sessions/wsp-bfcl-p100-20261105T143615Z/export/current4_delta.pt

  # Rebuild a full state_dict for bfcl_simple_eval --edited-state
  python3 experiments/tool_schema/wsp/pack_edited_delta.py apply \\
    --delta artifacts/.../current4_delta.pt \\
    --model-dir models/SmolLM2-360M-Instruct \\
    --out /tmp/edited_state.pt
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path

import torch
from transformers import AutoModelForCausalLM


def _changed_params(edits_json: Path | None, edited: dict) -> list[str]:
    if edits_json and edits_json.exists():
        meta = json.loads(edits_json.read_text())
        if meta.get("changed_params"):
            return list(meta["changed_params"])
        edits = meta.get("edits") or []
        last = -1
        for i, e in enumerate(edits):
            if e.get("param") == "*" or e.get("name") == "revert_all":
                last = i
        params = sorted(
            {
                e["param"]
                for e in edits[last + 1 :]
                if e.get("param") and e["param"] != "*"
            }
        )
        if params:
            return params
    # Fallback: caller must pass --params or we refuse guessing against base.
    raise SystemExit(
        "Need --edits-json with changed_params (or post-revert edits) to know which tensors changed"
    )


def cmd_pack(args: argparse.Namespace) -> None:
    edited = torch.load(args.edited_state, map_location="cpu", weights_only=True)
    params = args.params or _changed_params(args.edits_json, edited)
    missing = [p for p in params if p not in edited]
    if missing:
        raise SystemExit(f"edited state missing params: {missing[:5]}")
    payload = {
        "format": "wsp_delta_v1",
        "base_model_id": args.base_model_id,
        "session_id": args.session_id,
        "recipe": args.recipe,
        "params": params,
        "tensors": {p: edited[p].cpu() for p in params},
    }
    out = Path(args.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    torch.save(payload, out)
    nbytes = sum(t.numel() * t.element_size() for t in payload["tensors"].values())
    print(
        json.dumps(
            {
                "out": str(out),
                "n_tensors": len(params),
                "tensor_bytes": nbytes,
                "file_bytes": out.stat().st_size,
                "recipe": args.recipe,
                "session_id": args.session_id,
            },
            indent=2,
        )
    )


def cmd_apply(args: argparse.Namespace) -> None:
    delta = torch.load(args.delta, map_location="cpu", weights_only=False)
    if not isinstance(delta, dict) or "tensors" not in delta:
        raise SystemExit("delta file must be wsp_delta_v1 with a 'tensors' map")
    model = AutoModelForCausalLM.from_pretrained(args.model_dir, torch_dtype=torch.float32)
    state = model.state_dict()
    tensors = delta["tensors"]
    missing = [p for p in tensors if p not in state]
    if missing:
        raise SystemExit(f"base model missing params: {missing[:5]}")
    for p, t in tensors.items():
        if state[p].shape != t.shape:
            raise SystemExit(f"shape mismatch for {p}: base {tuple(state[p].shape)} vs delta {tuple(t.shape)}")
        state[p] = t.to(dtype=state[p].dtype)
    out = Path(args.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    torch.save(state, out)
    print(
        json.dumps(
            {
                "out": str(out),
                "n_overlaid": len(tensors),
                "file_bytes": out.stat().st_size,
                "base_model_id": delta.get("base_model_id"),
                "recipe": delta.get("recipe"),
                "session_id": delta.get("session_id"),
            },
            indent=2,
        )
    )


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest="cmd", required=True)

    p = sub.add_parser("pack", help="Pack changed tensors from a full edited_state.pt")
    p.add_argument("--edited-state", type=Path, required=True)
    p.add_argument("--edits-json", type=Path, default=None)
    p.add_argument("--params", nargs="*", default=None, help="Explicit param names (optional)")
    p.add_argument("--out", type=Path, required=True)
    p.add_argument("--base-model-id", default="HuggingFaceTB/SmolLM2-360M-Instruct")
    p.add_argument("--session-id", default="wsp-bfcl-p100-20261105T143615Z")
    p.add_argument("--recipe", default="current4")
    p.set_defaults(func=cmd_pack)

    a = sub.add_parser("apply", help="Overlay a delta onto a local base model → full state_dict")
    a.add_argument("--delta", type=Path, required=True)
    a.add_argument("--model-dir", type=Path, required=True)
    a.add_argument("--out", type=Path, required=True)
    a.set_defaults(func=cmd_apply)

    args = ap.parse_args()
    args.func(args)


if __name__ == "__main__":
    main()
