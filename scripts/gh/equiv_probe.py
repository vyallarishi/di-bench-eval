#!/usr/bin/env python3
"""Does a mutant of a replacement differ from the original on any input we can find?

Run as: equiv_probe.py ORIGINAL.py MUTANT.py CALLS.json
Prints EQUIVALENT if no generated input separates them, SEPARATED otherwise.

Agreement is not proof of equivalence; this is deliberately conservative, and
a mutant reported equivalent is excluded from the denominator of the mutation
score rather than counted as something the gate failed to catch.
"""
from __future__ import annotations

import importlib.util
import json
import pathlib
import random
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
from gate_differential import inputs_for  # noqa: E402
from record_usage import summarize, values_equal  # noqa: E402


def load(name: str, path: str):
    sp = importlib.util.spec_from_file_location(name, path)
    m = importlib.util.module_from_spec(sp)
    sp.loader.exec_module(m)
    return m


def main() -> None:
    a_path, b_path, calls_path = sys.argv[1], sys.argv[2], sys.argv[3]
    A, B = load("mut_a", a_path), load("mut_b", b_path)
    calls = json.load(open(calls_path))
    by: dict[str, list] = {}
    for c in calls:
        by.setdefault((c.get("q") or "").split(".")[-1], []).append(c)
    rnd = random.Random(0)
    for fn, recs in by.items():
        fa, fb = getattr(A, fn, None), getattr(B, fn, None)
        if fa is None or fb is None or not callable(fa):
            continue
        for args in inputs_for(recs, rnd, 200):
            try:
                ra = ("ret", summarize(fa(*args)))
            except BaseException as e:            # noqa: BLE001 - a raise is an outcome
                ra = ("raised", type(e).__name__)
            try:
                rb = ("ret", summarize(fb(*args)))
            except BaseException as e:            # noqa: BLE001
                rb = ("raised", type(e).__name__)
            same = ra[0] == rb[0] and (values_equal(ra[1], rb[1]) if ra[0] == "ret"
                                       else ra[1] == rb[1])
            if not same:
                print("SEPARATED")
                return
    print("EQUIVALENT")


if __name__ == "__main__":
    main()
