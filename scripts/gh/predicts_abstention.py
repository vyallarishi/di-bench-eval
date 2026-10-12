#!/usr/bin/env python3
"""Does the observability census predict where the behavioural gate abstains?

Section 5.3 classifies every recorded function as observable, void (returns
None, so there is no value to compare) or opaque (an argument is a live object
the recording cannot rebuild, so no new input can be derived). That is a
static property of the recording, computed before any submission exists.

If it predicts the gate's abstentions, "principled, predictable abstention"
stops being a design claim and becomes a measured one: the gate declines
exactly where the census said it would have to. If it does not, the
abstentions have some other cause and the census does not explain them.

The test is a confusion matrix over graded pairs: predicted gradeable (the
pair has at least one observable function) against actual verdict.

usage:  predicts_abstention.py [--grades FILE ...]
"""
from __future__ import annotations

import argparse
import collections
import json
import pathlib
import sys


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--grades", nargs="*", default=[])
    ap.add_argument("--observability", default="oracle-blindness/results/observability.json")
    a = ap.parse_args()

    obs = json.load(open(a.observability))
    observable = {p.replace("__trace__", "|") for p in obs["pairs"]}
    traced = {p.name[:-6].replace("__trace__", "|")
              for p in pathlib.Path("oracle-blindness/data/traces").glob("*.jsonl")}

    rows = []
    for g in a.grades:
        f = pathlib.Path(g)
        if not f.exists():
            continue
        d = json.load(open(f))
        for att in (d["attempts"] if isinstance(d, dict) else d):
            if att.get("ci") != "pass":
                continue
            key = f"{att['base']}|{att['dependency']}"
            pred = ("observable" if key in observable else
                    "traced, no observable function" if key in traced else
                    "no recording")
            actual = ("accepted" if att.get("accepted") else
                      "rejected" if att.get("failed") else "inconclusive")
            g4 = att.get("gates", {}).get("G4a_behaviour", "?")
            rows.append((pred, actual, g4, key))

    if not rows:
        sys.exit("no graded attempts found; pass --grades")

    print(f"{len(rows)} CI-passing submissions\n")
    m = collections.Counter((p, a_) for p, a_, _, _ in rows)
    preds = ["observable", "traced, no observable function", "no recording"]
    acts = ["accepted", "rejected", "inconclusive"]
    print(f"{'predicted':32s}" + "".join(f"{x:>14s}" for x in acts))
    for p in preds:
        n = sum(m[(p, x)] for x in acts)
        if not n:
            continue
        print(f"  {p:30s}" + "".join(f"{m[(p, x)]:14d}" for x in acts))

    # the claim: G4a speaks iff the census says the pair is observable
    spoke = [(p, g) for p, _, g, _ in rows if g in ("pass", "fail")]
    silent = [(p, g) for p, _, g, _ in rows if g not in ("pass", "fail")]
    tp = sum(1 for p, _ in spoke if p == "observable")
    fp = len(spoke) - tp
    fn = sum(1 for p, _ in silent if p == "observable")
    tn = len(silent) - fn
    print(f"\nG4a returned a verdict on {len(spoke)} and abstained on {len(silent)}")
    print(f"  predicted observable and the gate spoke:     {tp}")
    print(f"  predicted observable and the gate abstained: {fn}")
    print(f"  predicted NOT observable and the gate spoke: {fp}")
    print(f"  predicted NOT observable and it abstained:   {tn}")
    if tp + fp:
        print(f"\nprecision of 'observable predicts a verdict': {tp}/{tp + fp} = {tp / (tp + fp):.0%}")
    if tp + fn:
        print(f"recall: {tp}/{tp + fn} = {tp / (tp + fn):.0%}")
    if tn + fn:
        print(f"abstention explained by the census: {tn}/{tn + fn} = {tn / (tn + fn):.0%}")


if __name__ == "__main__":
    main()
