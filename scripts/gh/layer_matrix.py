#!/usr/bin/env python3
"""Which layer catches which counterfeit, and which catches it alone?

The paper's argument is that no single oracle suffices. That is a claim about
*overlap*: if every counterfeit the tests miss is also missed by the gates,
the layers are redundant and one would do. The evidence is a matrix of every
counterfeit against every layer, with each layer's count of unique catches.

Three layers, in the order a maintainer would apply them:

  structural   G1, G3, G7, G8 -- what the submission changed
  tests        the project's own suite, run under the import block
  library      the removed library as the oracle: G4a on recorded inputs,
               G4b on generated neighbours of them

A counterfeit caught by exactly one layer is that layer's unique contribution.
A counterfeit caught by none is what the whole stack misses, and is reported
rather than hidden.

usage:
  layer_matrix.py --structural FILE --ci DIR [DIR ...] --behavioural FILE
                  [--family pseudo] [--out out.json]
"""
from __future__ import annotations

import argparse
import collections
import json
import pathlib


def key(name: str) -> str:
    """repo|dep, however the variant is named."""
    parts = name.split("__")
    return f"{parts[0]}|{parts[-1]}"


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--structural", help="variants_*.json from run_variants")
    ap.add_argument("--ci", nargs="*", default=[], help="harness result dirs")
    ap.add_argument("--behavioural", nargs="*", default=[], help="g4b_variants output")
    ap.add_argument("--family", default=None)
    ap.add_argument("--out", default=None)
    a = ap.parse_args()

    struct: dict[str, bool] = {}
    if a.structural and pathlib.Path(a.structural).exists():
        d = json.load(open(a.structural))
        for r in (d if isinstance(d, list) else d.get("results", [])):
            if a.family and r.get("family") != a.family:
                continue
            struct[key(r["id"])] = bool(r.get("failed"))

    tests: dict[str, bool] = {}
    for root in a.ci:
        for f in pathlib.Path(root).rglob("eval-result.json"):
            j = json.loads(f.read_text())
            tests[key(j["instance_id"])] = j.get("exec") != "pass"   # True = caught

    lib: dict[str, bool] = {}
    for b in a.behavioural:
        p = pathlib.Path(b)
        if not p.exists():
            continue
        for r in json.load(open(p)):
            k = key(r["id"])
            if r.get("outcome") == "CAUGHT":
                lib[k] = True
            elif r.get("outcome") == "agrees":
                lib.setdefault(k, False)

    universe = sorted(set(struct) | set(tests) | set(lib))
    rows, tally = [], collections.Counter()
    for k in universe:
        s, t, l = struct.get(k), tests.get(k), lib.get(k)
        caught = [n for n, v in (("structural", s), ("tests", t), ("library", l)) if v]
        known = [n for n, v in (("structural", s), ("tests", t), ("library", l)) if v is not None]
        rows.append(dict(pair=k, structural=s, tests=t, library=l, caught=caught))
        tally["+".join(caught) if caught else
              ("none (all three spoke)" if len(known) == 3 else
               f"none ({len(known)} of 3 could speak)")] += 1

    print(f"{len(universe)} counterfeits; layers that could speak: "
          f"structural {len(struct)}, tests {len(tests)}, library {len(lib)}\n")
    print("caught by:")
    for k, v in tally.most_common():
        print(f"  {v:4d}  {k}")
    print("\nunique contribution (caught by that layer and no other):")
    for layer in ("structural", "tests", "library"):
        u = sum(1 for r in rows if r["caught"] == [layer])
        print(f"  {u:4d}  {layer}")
    both = sum(1 for r in rows if len(r["caught"]) >= 2)
    print(f"  {both:4d}  caught by more than one")
    if a.out:
        pathlib.Path(a.out).write_text(json.dumps(
            dict(tally=dict(tally), rows=rows), indent=1))
        print(f"-> {a.out}")


if __name__ == "__main__":
    main()
