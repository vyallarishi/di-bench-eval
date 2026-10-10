#!/usr/bin/env python3
"""How much of a recorded trace can the behavioural comparison actually see?

The comparison in G4a/G4b is defined over value *summaries*, not objects, and a
summary can be less than the value: a string past the display cap, a container
past the item cap, an object known only by its repr. Where the summary is less
than the value, two different values can summarise the same way, and a
divergence there is invisible to the gate.

This script classifies every recorded return value by what the comparison can
see of it, so the gate's coverage is a reported number rather than an
assumption:

  exact        a primitive, or a container whose every element is exact
  array        an array-like whose full content is inlined
  hashed       more than the cap, but a hash of the whole decides equality
  structural   an object compared by its public attributes and length
  opaque       an object compared by type and address-stripped repr only
  truncated    more than the cap and no hash (recorded by the earlier recorder)
  exception    the call raised; compared by exception type

usage:  trace_fidelity.py [--traces DIR]
"""
from __future__ import annotations

import argparse
import collections
import json
import pathlib

MAXREPR, MAXITEMS = 300, 20
PRIMITIVE = {"NoneType", "bool", "int", "float", "str", "bytes", "bytearray"}


def classify(s) -> str:
    if not isinstance(s, dict):
        return "exact"
    t = s.get("t")
    if "h" in s:
        return "hashed"
    if t in ("str", "bytes", "bytearray"):
        return "truncated" if s.get("n", 0) > len(s.get("v") or "") else "exact"
    if t in PRIMITIVE:
        return "exact"
    if "items" in s:
        if s.get("n", 0) > MAXITEMS:
            return "truncated"
        kinds = {classify(i[1] if t == "dict" else i) for i in s["items"]}
        if kinds <= {"exact"}:
            return "exact"
        return "truncated" if "truncated" in kinds else min(kinds, key=RANK.get)
    if "list" in s:
        return "array"
    if "attrs" in s or "len" in s:
        return "structural"
    return "opaque"


RANK = {"exact": 0, "array": 1, "hashed": 2, "structural": 3, "opaque": 4, "truncated": 5}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--traces", default="oracle-blindness/data/traces")
    ap.add_argument("--json", default=None)
    a = ap.parse_args()
    tally = collections.Counter()
    capped = []
    for f in sorted(pathlib.Path(a.traces).glob("*.jsonl")):
        for line in f.read_text(errors="ignore").splitlines():
            try:
                r = json.loads(line)
            except json.JSONDecodeError:
                continue
            if r.get("unpinbench_capped"):      # cap header, not a call
                capped.append(dict(trace=f.name, **{k: v for k, v in r.items()
                                                    if k != "unpinbench_capped"}))
                continue
            tally["exception" if "raised" in r else classify(r.get("ret"))] += 1
    n = sum(tally.values())
    print(f"{n} recorded return values")
    for k, v in tally.most_common():
        print(f"  {v:6d}  {v / n:5.1%}  {k}")
    decided = sum(v for k, v in tally.items() if k in ("exact", "array", "hashed", "structural", "exception"))
    print(f"\ncomparison decides on the whole value: {decided}/{n} = {decided / n:.1%}")
    print(f"repr-only or truncated (a divergence there can be missed): "
          f"{n - decided}/{n} = {(n - decided) / n:.1%}")
    if capped:
        dropped = sum(c["records_dropped"] for c in capped)
        print(f"\nthis directory is the published copy: {len(capped)} trace(s) capped per call "
              f"site, {dropped} records dropped, so the shares above are over {n} of "
              f"{n + dropped} recorded values (see cap_traces.py)")
        for c in capped:
            print(f"  {c['trace']}: kept {c['records_kept']} of {c['records_recorded']} "
                  f"across {c['sites']} sites, {c['sites_capped']} capped at {c['per_site']}")
    if a.json:
        pathlib.Path(a.json).write_text(json.dumps(
            dict(values=n, classes=dict(tally), decided_on_whole_value=decided,
                 share_decided=round(decided / n, 4), capped=capped), indent=1))


if __name__ == "__main__":
    main()
