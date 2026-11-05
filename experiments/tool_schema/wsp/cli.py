#!/usr/bin/env python3
"""CLI for WSP harness preparation (no editor agent yet).

Usage from repo root:
  python3 -m experiments.tool_schema.wsp.cli init
  python3 experiments/tool_schema/wsp/cli.py smoke-edit --session-id <id>
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

EXPERIMENT_ROOT = Path(__file__).resolve().parents[1]
REPO_ROOT = EXPERIMENT_ROOT.parents[1]
if str(EXPERIMENT_ROOT) not in sys.path:
    sys.path.insert(0, str(EXPERIMENT_ROOT))

from wsp.harness import WSPHarness  # noqa: E402
from wsp.sandbox import run_sandbox_script  # noqa: E402


def _print(obj: object) -> None:
    print(json.dumps(obj, indent=2, default=str))


def cmd_init(args: argparse.Namespace) -> int:
    h = WSPHarness(forward_budget=args.budget, session_id=args.session_id)
    _print(h.status())
    pointer = Path(args.pointer)
    pointer.parent.mkdir(parents=True, exist_ok=True)
    pointer.write_text(
        json.dumps({"session_id": h.session_id, "session_dir": str(h.session_dir)}, indent=2),
        encoding="utf-8",
    )
    print(f"pointer={pointer}", flush=True)
    return 0


def _harness(args: argparse.Namespace) -> WSPHarness:
    if not args.session_id:
        pointer = Path(args.pointer)
        if pointer.exists():
            args.session_id = json.loads(pointer.read_text(encoding="utf-8"))["session_id"]
    return WSPHarness(forward_budget=args.budget, session_id=args.session_id)


def cmd_status(args: argparse.Namespace) -> int:
    _print(_harness(args).status())
    return 0


def cmd_list_params(args: argparse.Namespace) -> int:
    h = _harness(args)
    params = h.list_params(args.substr)
    _print({"n": len(params), "params": params[: args.limit]})
    return 0


def cmd_smoke_edit(args: argparse.Namespace) -> int:
    h = _harness(args)
    candidates = [
        p["name"]
        for p in h.list_params()
        if (not p["protected"]) and p["name"].endswith("weight") and "mlp" in p["name"]
    ]
    if not candidates:
        raise SystemExit("No editable mlp weight tensors found")
    param = candidates[0]
    t = h.get_tensor(param)
    rec = h.save_edit("smoke_eps", param, t + float(args.epsilon), note="smoke epsilon nudge")
    diff = h.diff_stats(param)
    fwd = h.forward_pass(max_examples=args.forward_n, which="edited")
    h.revert_param(param)
    _print(
        {
            "param": param,
            "edit": rec,
            "diff": diff,
            "forward_summary": fwd["summary"],
            "budget": fwd["budget"],
            "status_after_revert": {
                "n_edits": h.status()["n_edits"],
                "changed_params": h.status()["changed_params"],
                "forward": h.status()["forward"],
            },
        }
    )
    return 0


def cmd_forward(args: argparse.Namespace) -> int:
    h = _harness(args)
    ids = args.ids.split(",") if args.ids else None
    out = h.forward_pass(example_ids=ids, max_examples=args.max_examples, which=args.which)
    _print({"summary": out["summary"], "budget": out["budget"]})
    return 0


def cmd_sandbox(args: argparse.Namespace) -> int:
    h = _harness(args)
    code = Path(args.script).read_text(encoding="utf-8")
    _print(run_sandbox_script(h, code))
    return 0


def cmd_export(args: argparse.Namespace) -> int:
    _print(_harness(args).export())
    return 0


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--budget", type=int, default=25)
    p.add_argument("--session-id", default=None)
    p.add_argument(
        "--pointer",
        default=str(REPO_ROOT / "artifacts" / "wsp_sessions" / "latest.json"),
    )
    sub = p.add_subparsers(dest="cmd", required=True)

    sub.add_parser("init").set_defaults(func=cmd_init)

    sub.add_parser("status").set_defaults(func=cmd_status)

    s = sub.add_parser("list-params")
    s.add_argument("--substr", default=None)
    s.add_argument("--limit", type=int, default=30)
    s.set_defaults(func=cmd_list_params)

    s = sub.add_parser("smoke-edit")
    s.add_argument("--epsilon", type=float, default=1e-4)
    s.add_argument("--forward-n", type=int, default=3)
    s.set_defaults(func=cmd_smoke_edit)

    s = sub.add_parser("forward")
    s.add_argument("--ids", default=None)
    s.add_argument("--max-examples", type=int, default=8)
    s.add_argument("--which", choices=["edited", "base"], default="edited")
    s.set_defaults(func=cmd_forward)

    s = sub.add_parser("sandbox")
    s.add_argument("script")
    s.set_defaults(func=cmd_sandbox)

    sub.add_parser("export").set_defaults(func=cmd_export)
    return p


def main() -> int:
    args = build_parser().parse_args()
    return args.func(args)


if __name__ == "__main__":
    raise SystemExit(main())
