#!/usr/bin/env python3
"""Tabulate base vs edited BFCL cross-format results from bfcl_category_eval.py outputs.

Reads ``<base-tag>_<category>_latest.summary.json`` / ``<edited-tag>_<category>_latest.summary.json``
plus the matching (newest) ``*.generations.jsonl`` for paired per-item flips, and prints a
markdown table (paste into CROSSFMT_BASE_VS_EDITED.md).
"""
from __future__ import annotations

import argparse
import json
from math import comb
from pathlib import Path

EXPERIMENT_ROOT = Path(__file__).resolve().parent
CATS = ("simple_python", "simple_java", "simple_javascript", "multiple", "parallel", "parallel_multiple")


def load(out_dir: Path, tag: str, cat: str):
    s = json.loads((out_dir / f"{tag}_{cat}_latest.summary.json").read_text())
    gens = sorted(out_dir.glob(f"{tag}_{cat}_2*.generations.jsonl"))
    rows = {}
    if gens:
        for line in gens[-1].read_text().splitlines():
            if line.strip():
                r = json.loads(line)
                rows[r["id"]] = r
    return s, rows


def mcnemar_exact(b: int, c: int) -> float:
    """Two-sided exact binomial test on discordant pairs."""
    n = b + c
    if n == 0:
        return 1.0
    k = min(b, c)
    p = sum(comb(n, i) for i in range(k + 1)) / 2**n
    return min(1.0, 2 * p)


def pct(x: float) -> str:
    return f"{x:.3f}"


def rel_pct(base_acc: float, edited_acc: float, base_n: int | None = None, edited_n: int | None = None) -> str:
    """Relative change vs base accuracy. Prefer exact counts when available."""
    if base_n is not None and edited_n is not None:
        if base_n == 0:
            return "n/a (base 0)"
        return f"{(edited_n - base_n) / base_n * 100:+.1f}%"
    if base_acc == 0:
        return "n/a (base 0)"
    return f"{(edited_acc - base_acc) / base_acc * 100:+.1f}%"


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--out-dir", type=Path, default=EXPERIMENT_ROOT / "results" / "bfcl")
    ap.add_argument("--base-tag", default="crossfmt-base")
    ap.add_argument("--edited-tag", default="crossfmt-edited")
    args = ap.parse_args()

    main_rows, extra_rows, err_rows = [], [], []
    tot = {"n": 0, "b": 0, "e": 0}
    off = {"n": 0, "b": 0, "e": 0, "g": 0, "l": 0}
    for cat in CATS:
        try:
            sb, rb = load(args.out_dir, args.base_tag, cat)
            se, re_ = load(args.out_dir, args.edited_tag, cat)
        except FileNotFoundError:
            main_rows.append(f"| `{cat}` | – | (missing) | (missing) | – | – | – | – |")
            continue
        assert sb["n"] == se["n"], cat
        n, b, e = sb["n"], sb["n_correct"], se["n_correct"]
        gain = sum(1 for i in rb if not rb[i]["valid"] and re_.get(i, {}).get("valid"))
        loss = sum(1 for i in rb if rb[i]["valid"] and not re_.get(i, {}).get("valid"))
        p = mcnemar_exact(gain, loss)
        d = (e - b) / n
        main_rows.append(
            f"| `{cat}` | {n} | {b}/{n} = {pct(b / n)} | {e}/{n} = {pct(e / n)} | "
            f"{d:+.3f} | {rel_pct(b / n, e / n, b, e)} | +{gain} / −{loss} | {p:.3g} |"
        )
        extra_rows.append(
            f"| `{cat}` | {pct(sb['ast_accuracy_raw'])} | {pct(se['ast_accuracy_raw'])} | "
            f"{se['ast_accuracy_raw'] - sb['ast_accuracy_raw']:+.3f} |"
        )
        for name, es in (("base", sb["error_types"]), ("edited", se["error_types"])):
            top = ", ".join(f"`{k}` {v}" for k, v in list(es.items())[:4])
            err_rows.append(f"| `{cat}` | {name} | {top} |")
        tot["n"] += n
        tot["b"] += b
        tot["e"] += e
        if cat != "simple_python":
            off["n"] += n
            off["b"] += b
            off["e"] += e
            off["g"] += gain
            off["l"] += loss
        if cat == "simple_python" and "splits" in sb:
            for split in ("practice_0_299", "holdout_300_399"):
                xb, xe = sb["splits"][split], se["splits"][split]
                lo, hi = (0, 299) if split.startswith("practice") else (300, 399)
                ids = [i for i in rb if lo <= int(i.rsplit("_", 1)[1]) <= hi]
                g = sum(1 for i in ids if not rb[i]["valid"] and re_[i]["valid"])
                l_ = sum(1 for i in ids if rb[i]["valid"] and not re_[i]["valid"])
                main_rows.append(
                    f"| ↳ `simple_python` {split.replace('_', ' ', 1)} | {xb['n']} | "
                    f"{xb['n_correct']}/{xb['n']} = {pct(xb['ast_accuracy'])} | "
                    f"{xe['n_correct']}/{xe['n']} = {pct(xe['ast_accuracy'])} | "
                    f"{xe['ast_accuracy'] - xb['ast_accuracy']:+.3f} | "
                    f"{rel_pct(xb['ast_accuracy'], xe['ast_accuracy'], xb['n_correct'], xe['n_correct'])} | "
                    f"+{g} / −{l_} | {mcnemar_exact(g, l_):.3g} |"
                )

    print(
        "| category | n | base AST acc | edited AST acc | delta (abs) | relative % | "
        "paired flips (+gain / −loss) | McNemar exact p |"
    )
    print("|---|---:|---:|---:|---:|---:|---:|---:|")
    print("\n".join(main_rows))
    if off["n"]:
        print(
            f"| **pooled, excluding simple_python** (all items) | {off['n']} | {off['b']}/{off['n']} = {pct(off['b'] / off['n'])} | "
            f"{off['e']}/{off['n']} = {pct(off['e'] / off['n'])} | {(off['e'] - off['b']) / off['n']:+.3f} | "
            f"{rel_pct(off['b'] / off['n'], off['e'] / off['n'], off['b'], off['e'])} | "
            f"+{off['g']} / −{off['l']} | {mcnemar_exact(off['g'], off['l']):.3g} |"
        )
    if tot["n"]:
        print(
            f"| pooled, all six (all items; includes edit-tuning practice items) | {tot['n']} | "
            f"{tot['b']}/{tot['n']} = {pct(tot['b'] / tot['n'])} | "
            f"{tot['e']}/{tot['n']} = {pct(tot['e'] / tot['n'])} | {(tot['e'] - tot['b']) / tot['n']:+.3f} | "
            f"{rel_pct(tot['b'] / tot['n'], tot['e'] / tot['n'], tot['b'], tot['e'])} | | |"
        )
    print("\nRaw official decode (no `[...]` extraction):\n")
    print("| category | base raw | edited raw | delta |")
    print("|---|---:|---:|---:|")
    print("\n".join(extra_rows))
    print("\nTop failure types (official `error_type`):\n")
    print("| category | model | top error types |")
    print("|---|---|---|")
    print("\n".join(err_rows))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
