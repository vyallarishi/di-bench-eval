#!/usr/bin/env python3
"""Does a pure line shift make the behavioural gate report a divergence?

A call is identified by its repository-relative file and line, so a rewrite
that inserts an import moves every site below it. If the gate keyed only on
that, a correct rewrite would read as `unreached`, which counts as failure --
the "place is file:line" objection.

This tests it directly rather than by argument. Take a recorded reference
trace, shift every recorded line by a constant (as inserting N lines at the
top of a file would), and compare the shifted trace against the original. The
values are untouched, so any divergence is the line shift alone.

usage:  lineshift_probe.py [--traces DIR] [--shift 5] [--limit 40]
"""
from __future__ import annotations

import argparse
import collections
import json
import pathlib
import re
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
import gate_behaviour  # noqa: E402
import record_usage  # noqa: E402


def shift_sites(records: list[dict], n: int) -> list[dict]:
    """Every recorded site moved down by n lines, values untouched."""
    out = []
    for r in records:
        r = dict(r)
        if r.get("level") == "usage":
            out.append(r)        # keyed by function, not by line
            continue
        s = r.get("site")
        if isinstance(s, str) and ":" in s:
            path, _, line = s.rpartition(":")
            if line.isdigit():
                r["site"] = f"{path}:{int(line) + n}"
        out.append(r)
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--traces", default="oracle-blindness/data/traces")
    ap.add_argument("--shift", type=int, default=5)
    ap.add_argument("--limit", type=int, default=0)
    ap.add_argument("--repo-data", default=".cache/repo-data")
    ap.add_argument("--both-levels", action="store_true",
                    help="complete the reference with usage records, as a real run has")
    a = ap.parse_args()

    files = sorted(pathlib.Path(a.traces).glob("*.jsonl"))
    if a.limit:
        files = files[: a.limit]
    tally = collections.Counter()
    worst = []
    for f in files:
        ref = gate_behaviour.load(f)
        if not ref:
            continue
        repo = pathlib.Path(a.repo_data) / "python" / f.name.split("__trace__")[0]
        sf0 = record_usage.site_functions(repo, ref) if repo.is_dir() else {}
        # The committed traces are boundary-only. A real grading run records
        # both levels (run_g4 passes usage=), and the usage level is what can
        # absorb a shift, so the reference is completed with the usage records
        # its enclosing functions would have produced.
        if a.both_levels:
            use = []
            for r in ref:
                fn = sf0.get(gate_behaviour._norm_site(r.get("site")))
                if fn:
                    use.append({"q": fn, "site": fn, "level": "usage",
                                "args": r.get("args"), "kwargs": r.get("kwargs"),
                                "ret": r.get("ret"), "raised": r.get("raised")})
            ref = ref + use
        cand = shift_sites(ref, a.shift)
        # site_function is what credits a boundary call whose site moved to
        # the enclosing project function; omitting it tests only half the
        # gate and makes every shift look like a failure.
        res = gate_behaviour.compare(ref, cand, site_function=sf0)
        v = res["verdict"]
        tally[v] += 1
        if v != "identical":
            worst.append((f.name[:-6], v, res.get("divergent"), res.get("missing") or res.get("unreached")))
    n = sum(tally.values())
    print(f"{n} traces, every recorded line shifted by {a.shift}, values untouched\n")
    for k, v in tally.most_common():
        print(f"  {v:4d}  {k}")
    if worst:
        print(f"\n{len(worst)} traces report something other than identical:")
        for name, v, d, m in worst[:12]:
            print(f"    {name[:52]:52s} {v:10s} divergent={d} unreached={m}")
        print("\n-> the gate is sensitive to a pure line shift at this level.")
    else:
        print("\n-> a pure line shift produces no divergence: the comparison is")
        print("   not defeated by a rewrite that moves its call sites.")


if __name__ == "__main__":
    main()
