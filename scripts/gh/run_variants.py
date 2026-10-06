#!/usr/bin/env python3
"""Grade the eight constructed cheat families, and say which gate catches which.

The families come from Sushane's generator (`sushane/work/scripts/cheats2.py`,
emitted as patches with EMIT_PATCHES=1):

  mutant          the declaration is deleted and nothing else changes
  hide            the declaration is moved somewhere the parser does not read
  vendor          the library's own source is copied into the repository
  stub            a module shadowing the package name, returning constants
  stub_smart      the same, shaped to satisfy the assertions it has seen
  pseudo_genuine  filler logic in an internal module, no name reuse
  weaken_tests    the declaration is deleted and the tests that would notice
                  are skipped
  trade           the declaration is replaced by unrelated packages and the
                  imports rewired to them

They are not interchangeable, and the point of grading all eight is to show the
gates are *not* redundant: each family should be caught by a different gate, and
`pseudo_genuine` should survive everything structural. That family is the
acceptance test for the behavioural gate -- Sushane's own result is that no
structural signal separates it from a real rewrite.

Two things this driver must get right, both learned the hard way:

  the variants were built on the GOLD manifest, so a checkout must have gold
  restored before the patch will apply at all;
  a family that no gate catches is a finding, not a bug to be explained away.

usage:
  run_variants.py --patches DIR --dataset D --repo-data R --out results.json
                  [--pool pilot/instances.jsonl] [--families a,b] [--limit N]
"""
from __future__ import annotations

import argparse
import collections
import json
import pathlib
import shutil
import subprocess
import sys
import tempfile

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
import grader  # noqa: E402
from make_blocked import apply_patch as apply_gold  # noqa: E402
from manifests import norm  # noqa: E402

# which gate each family is designed to exercise; used only to report whether
# the expectation held, never to decide a verdict
EXPECTED = {
    "mutant": "G1/G2 (an honest deletion, so CI should notice if the tests do)",
    "hide": "G1 (the declaration is not really gone)",
    "vendor": "G3 (the library's source is present)",
    "stub": "G3/G4 (a shadowing module that does not do the work)",
    "stub_smart": "G4 (shaped to the assertions, so only behaviour separates it)",
    "pseudo_genuine": "G4 (structurally identical to a real rewrite)",
    "weaken_tests": "G7 (the oracle itself was edited)",
    "trade": "G8 (the closure did not shrink)",
}


def parse_id(name: str):
    """<iid>__<family>__<dep> -- the family is the middle field."""
    parts = name.split("__")
    if len(parts) < 3:
        return None
    return parts[0], parts[1], parts[-1]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--patches", required=True)
    ap.add_argument("--dataset", required=True)
    ap.add_argument("--repo-data", default=".cache/repo-data")
    ap.add_argument("--out", required=True)
    ap.add_argument("--pool", default="pilot/instances.jsonl")
    ap.add_argument("--families", default=None)
    ap.add_argument("--limit", type=int, default=0)
    a = ap.parse_args()

    rows = {json.loads(l)["instance_id"]: json.loads(l)
            for l in open(a.dataset) if l.strip()}
    pool = set()
    if pathlib.Path(a.pool).exists():
        pool = {(json.loads(l)["instance_id"], norm(json.loads(l)["dependency"]))
                for l in open(a.pool) if l.strip()}
    want = set(a.families.split(",")) if a.families else None

    dirs = sorted(p for p in pathlib.Path(a.patches).iterdir()
                  if (p / "patch.diff").exists())
    if a.limit:
        dirs = dirs[: a.limit]

    results = []
    for d in dirs:
        parsed = parse_id(d.name)
        if not parsed:
            continue
        iid, family, dep = parsed
        if want and family not in want:
            continue
        rec = dict(id=d.name, instance_id=iid, family=family, dependency=dep,
                   in_pool=(iid, norm(dep)) in pool)
        row = rows.get(iid)
        src = pathlib.Path(a.repo_data) / "python" / iid
        if row is None or not src.is_dir():
            rec.update(status="skipped", why="no dataset row or repo data")
            results.append(rec)
            continue

        patch = (d / "patch.diff").read_text(errors="replace")
        with tempfile.TemporaryDirectory() as td:
            work = pathlib.Path(td) / "w"
            shutil.copytree(src, work, symlinks=True,
                            ignore=shutil.ignore_patterns(".git", "__pycache__"))
            # restore gold: the variants were built from it, and the checked-out
            # manifest is masked
            bf = row["build_files"][0]
            try:
                (work / bf).write_text(apply_gold(src, bf, row["patch"]))
            except Exception:
                pass
            (work / "p.diff").write_text(patch)
            r = subprocess.run(["git", "apply", "--allow-empty", "--ignore-whitespace",
                                "-p1", "p.diff"], cwd=work, capture_output=True, text=True)
            if r.returncode != 0:
                r = subprocess.run(["patch", "--batch", "--fuzz=5", "-p1", "-i", "p.diff"],
                                   cwd=work, capture_output=True, text=True)
            if r.returncode != 0:
                rec.update(status="skipped", why="patch did not apply")
                results.append(rec)
                continue

            g = grader.grade(patch, src, dep, gold_patch=row["patch"])

        rec.update(status="graded", accepted=g["accepted"],
                   failed=g["failed"], unverified=g["unverified"],
                   gates={k: v["status"] for k, v in g["gates"].items()},
                   reasons={k: v["reason"][:120] for k, v in g["gates"].items()})
        results.append(rec)
        marks = ",".join(x.split("_")[0] for x in g["failed"]) or "-"
        print(f"  {d.name[:52]:52s} {family:14s} "
              f"{'ACCEPT' if g['accepted'] else 'reject'}  by {marks}")

    pathlib.Path(a.out).write_text(json.dumps(results, indent=1, default=str))

    graded = [r for r in results if r.get("status") == "graded"]
    print(f"\n{len(results)} variants, {len(graded)} graded, "
          f"{sum(1 for r in graded if r['in_pool'])} on pairs in the canonical pool\n")
    # "accepted" is not the complement of "rejected": a variant no gate rejects
    # may still be unaccepted because a gate could not run. Conflating the two
    # would report a grader that rejects everything as a perfect one.
    print("| family | graded | rejected | no gate objects | caught by |")
    print("|---|---|---|---|---|")
    for fam in sorted({r["family"] for r in graded}):
        fr = [r for r in graded if r["family"] == fam]
        rej = [r for r in fr if r["failed"]]
        clean = [r for r in fr if not r["failed"]]
        by = collections.Counter(g for r in fr for g in r["failed"])
        top = ", ".join(f"{k.split('_')[0]} ({v})" for k, v in by.most_common(3)) or "-"
        print(f"| {fam} | {len(fr)} | {len(rej)} | {len(clean)} | {top} |")
    unrun = collections.Counter(g for r in graded for g in r["unverified"])
    if unrun:
        print("\ngates that could not run (so no family above is cleared by them):")
        for g, n in unrun.most_common():
            print(f"  {g}: {n} of {len(graded)}")
    print("\nexpected catcher per family (for comparison, not a verdict):")
    for fam in sorted({r["family"] for r in graded}):
        print(f"  {fam:16s} {EXPECTED.get(fam, '?')}")
    surviving = [f for f in {r["family"] for r in graded}
                 if not any(r["failed"] for r in graded if r["family"] == f)]
    if surviving:
        print("\nFamilies NO gate rejects: " + ", ".join(sorted(surviving)))
        print("  Report this as a result. If pseudo_genuine is here, the structural")
        print("  gates are insufficient and the behavioural gate is what must close it.")
    print(f"-> {a.out}")


if __name__ == "__main__":
    main()
