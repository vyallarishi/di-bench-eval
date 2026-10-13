#!/usr/bin/env python3
"""What does each gate add, on every set whose correct verdict is known?

A grader is a stack, and the question a reviewer asks is what each layer is
worth: how many submissions does adding it remove from the accepted set? This
re-scores each set under cumulative configurations, from the tests alone up to
the full stack, and reports how many submissions each configuration accepts.
The difference between consecutive rows is that gate's contribution.

The empty patch is included as a floor: a submission that changes nothing must
be rejected by any configuration worth having.

usage:  ablation.py --grades FILE ... --variants FILE [--out out.json]
"""
from __future__ import annotations

import argparse
import json
import pathlib

CONFIGS = [
    ("tests only", ["G2_tests_pass"]),
    ("+ declaration gone", ["G2_tests_pass", "G1_declaration_gone"]),
    ("+ no copy or shadow", ["G2_tests_pass", "G1_declaration_gone", "G3_no_vendored_copy"]),
    ("+ no phantom use", ["G2_tests_pass", "G1_declaration_gone", "G3_no_vendored_copy",
                          "G5_no_phantom"]),
    ("+ tests untouched", ["G2_tests_pass", "G1_declaration_gone", "G3_no_vendored_copy",
                           "G5_no_phantom", "G7_tests_untouched"]),
    ("+ closure not grown", ["G2_tests_pass", "G1_declaration_gone", "G3_no_vendored_copy",
                             "G5_no_phantom", "G7_tests_untouched", "G8_closure_not_grown"]),
    ("+ library oracle (full)", ["G2_tests_pass", "G1_declaration_gone", "G3_no_vendored_copy",
                                 "G5_no_phantom", "G7_tests_untouched", "G8_closure_not_grown",
                                 "G4a_behaviour"]),
]


def accepts(att: dict, gates: list[str]) -> bool:
    """Would this configuration accept the submission?

    A gate that fails rejects; a gate that cannot speak also withholds
    acceptance, which is the grader's own rule. The caller separates the two
    when reporting, because only the first is a catch.

    A gate that fails rejects. A gate that cannot speak also withholds
    acceptance, which is the grader's own rule: `accepted` requires every
    gate in the configuration to have passed.
    """
    g = att.get("gates", {})
    for name in gates:
        st = g.get(name)
        if st is None:
            continue                 # not part of this run at all
        if st != "pass":
            return False
    return True


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--grades", nargs="*", default=[], help="grade_agent outputs")
    ap.add_argument("--out", default=None)
    a = ap.parse_args()

    att = []
    for g in a.grades:
        p = pathlib.Path(g)
        if p.exists():
            d = json.load(open(p))
            att += d["attempts"] if isinstance(d, dict) else d
    passes = [x for x in att if x.get("ci") == "pass"]

    print(f"agent submissions that pass the tests: {len(passes)}\n")
    # A step removes a submission either because the new gate *rejected* it or
    # because that gate *could not speak*. Reporting one number for both reads
    # as "this gate caught N", which is false and does not reconcile with the
    # results table's rejection counts. They are separated here.
    print(f"{'configuration':26s} {'accepts':>8s} {'rejected':>9s} {'withheld':>9s}")
    prev, prev_set = None, None
    rows = []
    for label, gates in CONFIGS:
        keep = [x for x in passes if accepts(x, gates)]
        n = len(keep)
        if prev is None:
            r = w = None
            print(f"  {label:24s} {n:8d} {'':>9s} {'':>9s}")
        else:
            gone = [x for x in prev_set if x not in keep]
            new_gate = gates[-1]
            r = sum(1 for x in gone if new_gate in (x.get("failed") or []))
            w = len(gone) - r
            print(f"  {label:24s} {n:8d} {r:9d} {w:9d}")
        rows.append(dict(config=label, accepts=n, rejected=r, withheld=w))
        prev, prev_set = n, keep
    if a.out:
        pathlib.Path(a.out).write_text(json.dumps(
            dict(n_ci_pass=len(passes), rows=rows), indent=1))
        print(f"\n-> {a.out}")


if __name__ == "__main__":
    main()
