#!/usr/bin/env python3
"""How much of a repository's library use can ANY return-value oracle see?

Found by accident, twice. Building counterfeits revealed that 254 of 498
generated fakes were not fakes, because the library function returns None and
there is no wrong return value to produce. Grading them revealed that the
dominant reason the gate cannot speak is an argument that is a live object the
recording cannot rebuild. Both are properties of real library usage, not of
our instrument: a return-value oracle is blind to a call that returns nothing,
and a generated-input oracle is blind to a call whose arguments cannot be
reconstructed.

That is the same kind of fact as the census of the test oracle, and it is
measured the same way: over every recorded call in the benchmark, classify
what an oracle could observe.

  returns a value          a wrong return is possible, so the call is checkable
  returns None             side-effect only: outside a return-value oracle
  arguments reconstructible  new inputs can be generated for it
  arguments opaque         a live object; only the recorded call can be replayed

usage:  observability.py [--traces DIR] [--pool pilot/instances.jsonl]
"""
from __future__ import annotations

import argparse
import collections
import json
import pathlib

PRIM = {"str", "bytes", "bytearray", "int", "float", "bool", "NoneType",
        "list", "tuple", "dict", "set", "frozenset"}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--traces", default="oracle-blindness/data/traces")
    ap.add_argument("--pool", default="pilot/instances.jsonl")
    ap.add_argument("--out", default=None)
    a = ap.parse_args()

    calls = collections.Counter()
    fns: dict[tuple, set] = collections.defaultdict(set)
    fn_void: dict[tuple, bool] = {}
    fn_opaque: dict[tuple, bool] = {}
    pair_any = collections.Counter()

    for f in sorted(pathlib.Path(a.traces).glob("*.jsonl")):
        pair = f.name[:-6]
        for line in f.read_text(errors="ignore").splitlines():
            if not line.strip():
                continue
            try:
                r = json.loads(line)
            except json.JSONDecodeError:
                continue
            fn = (r.get("q") or "").split(".")[-1]
            key = (pair, fn)
            fns[pair].add(fn)
            ret = r.get("ret")
            void = isinstance(ret, dict) and ret.get("t") == "NoneType"
            args = r.get("args") or []
            opaque = any(isinstance(x, dict) and x.get("t") not in PRIM for x in args)
            calls["returns None (side-effect only)" if void else "returns a value"] += 1
            calls["argument is a live object" if opaque else "arguments reconstructible"] += 1
            fn_void[key] = fn_void.get(key, True) and void
            fn_opaque[key] = fn_opaque.get(key, False) or opaque

    n_fn = len(fn_void)
    void_fns = sum(1 for v in fn_void.values() if v)
    opaque_fns = sum(1 for k, v in fn_opaque.items() if v and not fn_void[k])
    observable = n_fn - void_fns - opaque_fns
    for (pair, fn), v in fn_void.items():
        if not v and not fn_opaque[(pair, fn)]:
            pair_any[pair] += 1

    traced = len(list(pathlib.Path(a.traces).glob("*.jsonl")))
    pool = sum(1 for _ in open(a.pool))
    print(f"over {sum(calls[k] for k in ('returns a value', 'returns None (side-effect only)'))} "
          f"recorded calls in {traced} traced pairs\n")
    print("per call:")
    for k in ("returns a value", "returns None (side-effect only)",
              "arguments reconstructible", "argument is a live object"):
        print(f"  {calls[k]:7d}  {k}")
    print(f"\nper (pair, function), n={n_fn}:")
    print(f"  {observable:7d}  {observable/n_fn:5.0%}  observable: returns a value AND arguments reconstructible")
    print(f"  {void_fns:7d}  {void_fns/n_fn:5.0%}  returns None on every recorded call")
    print(f"  {opaque_fns:7d}  {opaque_fns/n_fn:5.0%}  returns a value but takes a live object")
    print(f"\nper pair:")
    print(f"  {len(pair_any):7d}  of {traced} traced pairs have at least one observable function")
    print(f"  {len(pair_any):7d}  of {pool} pool pairs  = the OBSERVABLE subset")
    if a.out:
        pathlib.Path(a.out).write_text(json.dumps(dict(
            calls=dict(calls), functions=n_fn, observable_functions=observable,
            void_functions=void_fns, opaque_functions=opaque_fns,
            observable_pairs=len(pair_any), traced_pairs=traced, pool=pool,
            pairs=sorted(pair_any)), indent=1))


if __name__ == "__main__":
    main()
