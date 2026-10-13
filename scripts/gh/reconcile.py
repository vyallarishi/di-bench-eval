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


def check_grades(grade_files, ablation_file):
    """The invariants that relate the results table to the ablation.

    Added after an ablation counted "could not speak" as a rejection and so
    removed more submissions at a step than the results table reported
    rejected, with nothing in either table showing it.
    """
    import collections
    GATES = ["G1_declaration_gone", "G2_tests_pass", "G3_no_vendored_copy",
             "G4a_behaviour", "G5_no_phantom", "G7_tests_untouched",
             "G8_closure_not_grown"]
    att = []
    for g in grade_files:
        p = pathlib.Path(g)
        if not p.exists():
            print(f"  missing verdict file: {g}")
            return False
        d = json.load(open(p))
        att += d["attempts"] if isinstance(d, dict) else d
    passes = [x for x in att if x.get("ci") == "pass"]
    acc = [x for x in passes if x.get("accepted")]
    rej = [x for x in passes if x.get("failed")]
    inc = [x for x in passes if not x.get("accepted") and not x.get("failed")]
    ok = True
    print(f"\n{len(att)} submissions, {len(passes)} pass the tests")
    print(f"  accepted {len(acc)}   rejected {len(rej)}   inconclusive {len(inc)}")
    if len(acc) + len(rej) + len(inc) != len(passes):
        print("  LEDGER BREAK: the three verdicts do not partition the CI passes")
        ok = False
    print(f"  {'gate':24s} {'rejects':>8s} {'abstains':>9s}")
    for g in GATES:
        fails = sum(1 for x in passes if g in (x.get("failed") or []))
        unv = sum(1 for x in passes if g in (x.get("unverified") or []))
        status_fail = sum(1 for x in passes if x.get("gates", {}).get(g) == "fail")
        if fails != status_fail:
            print(f"  LEDGER BREAK: {g} has {fails} in failed lists, {status_fail} with status fail")
            ok = False
        print(f"  {g:24s} {fails:8d} {unv:9d}")
    if ablation_file and pathlib.Path(ablation_file).exists():
        ab = json.load(open(ablation_file))
        if ab.get("n_ci_pass") != len(passes):
            print(f"  LEDGER BREAK: ablation computed on {ab.get('n_ci_pass')} passes, these files have {len(passes)}")
            ok = False
        if ab["rows"][-1]["accepts"] != len(acc):
            print(f"  LEDGER BREAK: ablation accepts {ab['rows'][-1]['accepts']}, verdicts accept {len(acc)}")
            ok = False
    return ok


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--predictions", default="predictions/pseudo2")
    ap.add_argument("--g4b", default=None)
    ap.add_argument("--grades", nargs="*", default=[])
    ap.add_argument("--ablation", default=None)
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

    if a.grades:
        ok = check_grades(a.grades, a.ablation) and ok
    elif not a.g4b:
        print("\nnothing was checked: pass --g4b and/or --grades")
        ok = False
    print("\nALL TABLES RECONCILE" if ok else "\nLEDGER BREAK -- do not report these numbers")
    sys.exit(0 if ok else 1)


if __name__ == "__main__":
    main()
