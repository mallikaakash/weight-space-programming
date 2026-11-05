#!/usr/bin/env python3
"""Write a markdown spot-check of benchmark failures (diverse failure modes)."""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from paths import ARTIFACTS_DIR, EXPERIMENT_ROOT

OUT = EXPERIMENT_ROOT / "results" / "spotcheck.md"
FLAGS = ["parse_ok", "tool_ok", "args_is_object", "required_keys", "no_hallucinated_keys", "types_ok", "values_ok"]


def mode(row: dict) -> str:
    s = row["scores"]
    if not s["parse_ok"]:
        return "parse fail"
    if not s["tool_ok"]:
        return "wrong tool"
    if not s["args_is_object"] or not s["required_keys"]:
        return "missing keys"
    if not s["no_hallucinated_keys"]:
        return "hallucinated keys"
    return "bad values"


def latest_test_artifact() -> Path | None:
    best = None
    for p in sorted(ARTIFACTS_DIR.glob("tool_schema_*.json")):
        if p.name.endswith(".summary.json"):
            continue
        try:
            if json.loads(p.read_text(encoding="utf-8"))["summary"].get("split") == "test":
                best = p
        except (KeyError, ValueError):
            continue
    return best


def pick(failures: list[dict], k: int) -> list[dict]:
    """Round-robin across failure modes so the sample is diverse."""
    groups: dict[str, list[dict]] = {}
    for r in failures:
        groups.setdefault(mode(r), []).append(r)
    chosen = []
    while len(chosen) < k and any(groups.values()):
        for g in list(groups.values()):
            if g and len(chosen) < k:
                chosen.append(g.pop(0))
    return chosen


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--input", type=Path, default=None)
    ap.add_argument("--max", type=int, default=15)
    args = ap.parse_args()
    src = args.input or latest_test_artifact()
    if not src or not src.exists():
        print("No test-split artifact found; run benchmark.py --split test first.", file=sys.stderr)
        return 1
    data = json.loads(src.read_text(encoding="utf-8"))
    rows = data["examples"]
    failures = [r for r in rows if not r["scores"]["strict_ok"]]
    chosen = pick(failures, args.max)

    counts: dict[str, int] = {}
    for r in failures:
        counts[mode(r)] = counts.get(mode(r), 0) + 1

    lines = [
        "# Failure spot-check",
        "",
        f"Source: `{src.name}` (tag `{data['summary'].get('tag')}`, split `{data['summary'].get('split')}`). "
        f"{len(failures)}/{len(rows)} strict failures; showing {len(chosen)}.",
        "",
    ]
    for r in chosen:
        failed = [f for f in FLAGS if not r["scores"].get(f)]
        user = r["user"] if len(r["user"]) <= 100 else r["user"][:97] + "..."
        comp = " ".join(r["completion"].split())
        comp = comp if len(comp) <= 200 else comp[:197] + "..."
        lines += [
            f"## {r['id']} ({r['tier']}) — {mode(r)}",
            f"- user: {user}",
            f"- expected tool: `{r['expected']['tool']}` args `{json.dumps(r['expected']['arguments'])}`",
            f"- completion: `{comp.replace('`', "'")}`",
            f"- failed flags: {', '.join(failed)}",
            "",
        ]
    lines += ["## Notes", ""]
    for m, c in sorted(counts.items(), key=lambda x: -x[1]):
        lines.append(f"- **{m}**: {c} of {len(failures)} failures")
    lines.append("")
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text("\n".join(lines), encoding="utf-8")
    print(f"Wrote {OUT} ({len(chosen)} entries)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
