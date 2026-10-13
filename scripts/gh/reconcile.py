#!/usr/bin/env python3
"""Do the paper's tables agree with each other and with the verdict files?

Two tables built from the same submissions can disagree in ways that are
invisible in isolation: an ablation that counts "could not speak" as a
rejection removes more submissions at a step than the results table reports
rejected, and nothing in either table shows it. This recomputes every figure
that appears in more than one place from one per-submission verdict file and
fails loudly on a mismatch.

Three invariants, each the shape of a mistake already made here:

  partition      accepted + rejected + inconclusive = the CI passes, per set
  attribution    a gate's rejection count equals the submissions whose stored
                 `failed` list contains it, never its non-pass count
  abstention     a gate that cannot speak withholds acceptance but is not a
                 rejection, and the two are reported separately

usage:  reconcile.py --grades FILE ... [--ablation FILE]
"""
from __future__ import annotations

import argparse
import collections
import json
import pathlib
import sys

GATES = ["G1_declaration_gone", "G2_tests_pass", "G3_no_vendored_copy",
         "G4a_behaviour", "G5_no_phantom", "G7_tests_untouched",
         "G8_closure_not_grown"]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--grades", nargs="+", required=True)
    ap.add_argument("--ablation", default=None)
    a = ap.parse_args()

    att = []
    for g in a.grades:
        p = pathlib.Path(g)
        if not p.exists():
            sys.exit(f"missing verdict file: {g}")
        d = json.load(open(p))
        att += d["attempts"] if isinstance(d, dict) else d
    passes = [x for x in att if x.get("ci") == "pass"]

    acc = [x for x in passes if x.get("accepted")]
    rej = [x for x in passes if x.get("failed")]
    inc = [x for x in passes if not x.get("accepted") and not x.get("failed")]
    problems = []

    print(f"{len(att)} submissions, {len(passes)} pass the tests")
    print(f"  accepted {len(acc)}   rejected {len(rej)}   inconclusive {len(inc)}")
    if len(acc) + len(rej) + len(inc) != len(passes):
        problems.append("accepted + rejected + inconclusive does not equal the CI passes")

    print("\nper gate, over the CI passes:")
    print(f"  {'gate':24s} {'rejects':>8s} {'abstains':>9s} {'passes':>7s}")
    for g in GATES:
        fails = sum(1 for x in passes if g in (x.get("failed") or []))
        unv = sum(1 for x in passes if g in (x.get("unverified") or []))
        ok = sum(1 for x in passes if x.get("gates", {}).get(g) == "pass")
        status_fail = sum(1 for x in passes if x.get("gates", {}).get(g) == "fail")
        if fails != status_fail:
            problems.append(f"{g}: {fails} in the failed lists but {status_fail} with status fail")
        print(f"  {g:24s} {fails:8d} {unv:9d} {ok:7d}")

    # a gate's rejections must not exceed the submissions rejected at all
    tot_rej = len(rej)
    for g in GATES:
        fails = sum(1 for x in passes if g in (x.get("failed") or []))
        if fails > tot_rej:
            problems.append(f"{g} rejects {fails} but only {tot_rej} submissions are rejected")

    if a.ablation and pathlib.Path(a.ablation).exists():
        ab = json.load(open(a.ablation))
        print(f"\nablation file: {ab.get('n_ci_pass')} CI passes")
        if ab.get("n_ci_pass") != len(passes):
            problems.append(f"ablation was computed on {ab.get('n_ci_pass')} CI passes, "
                            f"these verdict files have {len(passes)}")
        last = ab["rows"][-1]["accepts"]
        if last != len(acc):
            problems.append(f"the full ablation configuration accepts {last}, "
                            f"the verdict files accept {len(acc)}")

    print()
    if problems:
        print(f"{len(problems)} INCONSISTENCY(IES):")
        for p in problems:
            print(f"  - {p}")
        sys.exit(1)
    print("consistent: every figure derives from the same verdict files")


if __name__ == "__main__":
    main()
