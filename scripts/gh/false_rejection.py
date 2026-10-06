#!/usr/bin/env python3
"""Measure how often the grader rejects a removal that is actually correct.

Detection without this is half a result: a grader that rejected everything
would score perfectly on every cheat corpus. The usual way to get the other
half is hand-written reference solutions, which are expensive and which we do
not have. RGT (Ye, Martinez & Monperrus, EMSE 2021) faced the same problem for
repair patches and solved it by taking a known-correct artifact as ground truth
and measuring how often the assessment wrongly condemns it; they report 2.3%
for their technique.

Our known-correct artifact is free and already measured. 172 pairs in the
screening are **over-declared**: the package appears nowhere in the repository,
not imported and not named in any configuration. For those, deleting the
declaration and changing no code *is* the correct removal, by construction --
there is nothing to rewrite, and CI passes with the package gone, which is how
they were identified in the first place.

So the test is: build exactly that patch (declaration deleted, nothing else
touched) and run the full gate stack. Every gate must accept it. Any rejection
is a false positive, attributable to a named gate, with the instance to
reproduce it.

This does not replace hand-written references, and the limit should be stated
plainly: these removals are *easy*, requiring no code change, so they exercise
the manifest-level and closure gates far more than the behavioural one. They
bound false rejection from below, not from above.

usage:
  false_rejection.py --removals correct_removals.json --dataset D
                     [--repo-data R] [--out report.json]
"""
from __future__ import annotations

import argparse
import collections
import json
import pathlib
import subprocess
import sys
import tempfile

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
import grader  # noqa: E402
import manifests as M  # noqa: E402
from make_blocked import apply_patch  # noqa: E402


def removal_patch(repo: pathlib.Path, bf: str, gold_patch: str, dep: str) -> str | None:
    """The correct removal: gold manifest minus one declaration, nothing else."""
    try:
        gold = apply_patch(repo, bf, gold_patch)
    except Exception:
        return None
    after = M.remove(bf, gold, dep)
    if after is None or M.declared(bf, after) != M.declared(bf, gold) - {M.norm(dep)}:
        return None
    masked = (repo / bf).read_text(errors="ignore")
    with tempfile.TemporaryDirectory() as td:
        t = pathlib.Path(td)
        subprocess.run(["git", "init", "-q"], cwd=t, check=True)
        (t / bf).parent.mkdir(parents=True, exist_ok=True)
        (t / bf).write_text(masked)
        subprocess.run(["git", "add", "-A"], cwd=t, check=True)
        subprocess.run(["git", "-c", "user.email=a@b", "-c", "user.name=a",
                        "commit", "-q", "-m", "base"], cwd=t, check=True)
        (t / bf).write_text(after)
        subprocess.run(["git", "add", "-A"], cwd=t, check=True)
        return subprocess.run(["git", "diff", "--cached"], cwd=t,
                              capture_output=True, text=True).stdout


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--removals", required=True)
    ap.add_argument("--dataset", nargs="+", required=True)
    ap.add_argument("--repo-data", default=".cache/repo-data")
    ap.add_argument("--out", default=None)
    ap.add_argument("--limit", type=int, default=0)
    a = ap.parse_args()

    rows = {}
    for d in a.dataset:
        for line in open(d):
            if line.strip():
                r = json.loads(line)
                rows.setdefault(r["instance_id"], r)

    removals = json.load(open(a.removals))
    if a.limit:
        removals = removals[: a.limit]

    results, tally = [], collections.Counter()
    by_gate = collections.Counter()
    for item in removals:
        iid, dep = item["instance_id"], item["dependency"]
        row = rows.get(iid)
        repo = pathlib.Path(a.repo_data) / "python" / iid
        if row is None or not repo.is_dir():
            tally["skipped: no dataset row or repo"] += 1
            continue
        bf = row["build_files"][0]
        patch = removal_patch(repo, bf, row["patch"], dep)
        if patch is None:
            tally["skipped: could not build the removal"] += 1
            continue
        # CI is known to pass for these: that is how they were identified.
        g = grader.grade(patch, repo, dep, gold_patch=row["patch"], tests_passed=True)
        rec = dict(instance_id=iid, dependency=dep, accepted=g["accepted"],
                   failed=g["failed"], unverified=g["unverified"],
                   reasons={k: v["reason"][:140] for k, v in g["gates"].items()
                            if v["status"] == "fail"})
        results.append(rec)
        if g["failed"]:
            tally["FALSE REJECTION"] += 1
            for gate in g["failed"]:
                by_gate[gate] += 1
            print(f"  REJECTED {iid[:32]:32s} {dep:22s} by {','.join(x.split('_')[0] for x in g['failed'])}")
        else:
            tally["accepted"] += 1

    graded = tally["accepted"] + tally["FALSE REJECTION"]
    print(f"\n{len(removals)} known-correct removals, {graded} graded")
    for k, v in tally.most_common():
        print(f"  {v:4d}  {k}")
    if graded:
        fr = tally["FALSE REJECTION"] / graded
        print(f"\nFALSE REJECTION RATE: {tally['FALSE REJECTION']}/{graded} = {fr:.1%}")
        if by_gate:
            print("  attributable to:")
            for g, n in by_gate.most_common():
                print(f"    {g}: {n}")
    print("\nScope: these removals need no code change, so they exercise the")
    print("manifest and closure gates far more than the behavioural one.")
    print("They bound false rejection from below, not from above.")
    if a.out:
        pathlib.Path(a.out).write_text(json.dumps(
            dict(rate=(tally["FALSE REJECTION"] / graded) if graded else None,
                 graded=graded, rejected=tally["FALSE REJECTION"],
                 by_gate=dict(by_gate), results=results), indent=1))


if __name__ == "__main__":
    main()
