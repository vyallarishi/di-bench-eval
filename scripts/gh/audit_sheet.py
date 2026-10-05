#!/usr/bin/env python3
"""Stratified hand-audit sheet for the removal benchmark.

Samples pairs from the pool, over-weighting the weaker evidence classes, and
prints for each: the removed package, how CI detected the removal, the exact
log lines around the error, and the files the static footprint says import the
package. The auditor marks each row GENUINE / DOUBTFUL / WRONG and notes why.

usage: audit_sheet.py instances.jsonl --results DIR [DIR ...] [--n 40] [--seed 1] > sheet.md
"""
import argparse
import collections
import json
import pathlib
import random
import re
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
from build_pool import BLOCK_MSG, FAILED_STEP, MISSING, load_results, read_log  # noqa: E402

# how many of the sample go to each evidence class (rest proportional)
QUOTA = {"test_failure_without_import_error": 10, "linter_step_failed": 4}


def excerpt(lines, marker, n=8):
    for i, l in enumerate(lines):
        if marker.search(l):
            lo = max(0, i - n)
            return lines[lo:i + 1]
    return lines[-n:]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("pool")
    ap.add_argument("--results", nargs="+", required=True)
    ap.add_argument("--n", type=int, default=40)
    ap.add_argument("--seed", type=int, default=1)
    a = ap.parse_args()
    rows = [json.loads(l) for l in open(a.pool)]
    res = {}
    for d in a.results:
        res.update(load_results(pathlib.Path(d)))
    rnd = random.Random(a.seed)
    by = collections.defaultdict(list)
    for r in rows:
        by[r["evidence"]].append(r)
    sample = []
    for ev, q in QUOTA.items():
        pool = by.pop(ev, [])
        rnd.shuffle(pool)
        sample += pool[:q]
    rest = [r for v in by.values() for r in v]
    rnd.shuffle(rest)
    sample += rest[: max(0, a.n - len(sample))]
    sample.sort(key=lambda r: (r["evidence"], r["instance_id"]))

    print(f"# Hand audit: {len(sample)} of {len(rows)} pairs (seed {a.seed})\n")
    print("For each pair decide: **GENUINE** (the repository really uses the package on the tested "
          "path and a removal is possible), **DOUBTFUL**, or **WRONG** (unwinnable or an artifact). "
          "Note the reason in one line.\n")
    print("| # | repository | package | subset | tier | evidence | verdict |\n|---|---|---|---|---|---|---|")
    for i, r in enumerate(sample, 1):
        print(f"| {i} | {r['instance_id']} | {r['dependency']} | {r['subset']} | {r['tier']} | {r['evidence']} |  |")
    print()
    for i, r in enumerate(sample, 1):
        print(f"## {i}. {r['instance_id']} / {r['dependency']}  ({r['evidence']}, tier {r['tier']})\n")
        srcs = r.get("source_files") or {}
        if srcs:
            print("Static footprint:")
            for f, d in list(srcs.items())[:8]:
                print(f"- `{f}`{' (test)' if d['is_test'] else ''}: `{'; '.join(d['imports'][:2])}`")
            if len(srcs) > 8:
                print(f"- ... {len(srcs) - 8} more files")
        else:
            print("Static footprint: none (package is never imported directly)")
        rr = res.get(r["mutant_id"])
        if rr and rr["log"]:
            lines = read_log(rr["log"])
            marker = BLOCK_MSG if "blocked" in r["evidence"] else MISSING
            if r["evidence"] in ("test_failure_without_import_error", "linter_step_failed"):
                marker = re.compile(r"^E\s{2,}\S|error:|Error:|E0401|I900")
            steps = [FAILED_STEP.search(l).group(1) for l in lines if FAILED_STEP.search(l)]
            print(f"\nFailing CI step: `{steps[0] if steps else '?'}`\n\nLog around the error:\n")
            print("```")
            for l in excerpt(lines, marker):
                print(l[:160])
            print("```")
        print("\nVerdict: ______  Reason: ______________________________\n")


if __name__ == "__main__":
    main()
