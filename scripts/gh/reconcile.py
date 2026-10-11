#!/usr/bin/env python3
"""Check that every reported table sums, and that its unit is stated.

Three tables in one afternoon carried a unit ambiguity -- counterfeit against
function against (counterfeit, function) pair -- and in each case the rows did
not add to the stated total. The failure mode is not arithmetic: it is pooling
two populations in adjacent rows of one table. A previous draft died of
exactly this, so the check is mechanical rather than a habit.

Each table declares its unit and its identity; the script recomputes both from
the result files and fails loudly on a mismatch.

usage:  reconcile.py [--predictions DIR] [--g4b FILE]
"""
from __future__ import annotations

import argparse
import collections
import json
import pathlib
import sys


def table(name: str, unit: str, parts: dict[str, int], total: int) -> bool:
    s = sum(parts.values())
    ok = s == total
    print(f"\n{name}   [unit: {unit}]")
    for k, v in parts.items():
        print(f"  {v:5d}  {k}")
    print(f"  {'-' * 5}")
    print(f"  {s:5d}  sum        {'== ' + str(total) + ' OK' if ok else '!= ' + str(total) + '  LEDGER BREAK'}")
    return ok


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--predictions", default="predictions/pseudo2")
    ap.add_argument("--g4b", default=None)
    a = ap.parse_args()

    idx = json.load(open(pathlib.Path(a.predictions) / "index.json"))
    built = {x["id"] for x in idx}
    functions = sum(len(x["functions"]) for x in idx)
    ok = True

    if a.g4b and pathlib.Path(a.g4b).exists():
        d = json.load(open(a.g4b))
        # unit: (counterfeit, function) pair
        by_out = collections.Counter(r["outcome"] for r in d)
        ok &= table("G4b outcomes", "(counterfeit, function) pair",
                    dict(by_out), len(d))
        # unit: counterfeit
        byid = collections.defaultdict(set)
        for r in d:
            byid[r["id"]].add(r["outcome"])
        caught = {i for i, o in byid.items() if "CAUGHT" in o}
        agree = {i for i, o in byid.items() if "CAUGHT" not in o and "agrees" in o}
        none = {i for i, o in byid.items() if not (o & {"CAUGHT", "agrees"})}
        absent = built - set(byid)
        ok &= table("G4b verdict by counterfeit", "counterfeit",
                    {"rejected": len(caught), "accepted": len(agree),
                     "no verdict": len(none), "never evaluated": len(absent)},
                    len(built))
        # the conditional rate, stated with its denominator
        adj = len(caught) + len(agree)
        if adj:
            print(f"\n  conditional on a verdict: {len(caught)}/{adj} rejected "
                  f"= {len(caught)/adj:.0%}  [this figure is NOT quotable alone]")
            print(f"  unconditional:            {len(caught)}/{len(built)} "
                  f"= {len(caught)/len(built):.0%} of counterfeits built")

    # functions evaluated must not exceed functions generated
    if a.g4b and pathlib.Path(a.g4b).exists():
        d = json.load(open(a.g4b))
        seen = {(r["id"], r["fn"]) for r in d}
        print(f"\nfunction ledger   [unit: (counterfeit, function) pair]")
        print(f"  {functions:5d}  generated")
        print(f"  {len(seen):5d}  evaluated")
        print(f"  {functions - len(seen):5d}  not evaluated (no recorded call for that function)")
        if len(seen) > functions:
            print("  LEDGER BREAK: more evaluated than generated")
            ok = False

    print("\nALL TABLES RECONCILE" if ok else "\nLEDGER BREAK -- do not report these numbers")
    sys.exit(0 if ok else 1)


if __name__ == "__main__":
    main()
