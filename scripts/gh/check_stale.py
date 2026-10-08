#!/usr/bin/env python3
"""Refuse to report results produced by a superseded version of an injected file.

The pool was built by a screening run dispatched before a fix to the blocker,
and nothing noticed: 622 patches carried a recursion bug, 28 pairs were admitted
on a harness crash, and the defect was found a day later by someone reading CI
logs. The fix itself was cheap. Not knowing the results were stale was the
expensive part.

An injected file is generated code embedded in every prediction patch, so a
patch is a frozen copy of whatever the generator produced that day. This script
compares what a prediction set contains against what the generator produces now
and names the difference, so a stale set is caught before its numbers are
quoted rather than after.

The check is deliberately crude -- the presence or absence of marker strings
that identify a known version -- because a semantic diff of generated code would
have its own bugs. Each marker names the defect it detects, so a set that lacks
one can be re-dispatched with a reason.

usage:
  check_stale.py predictions/all predictions/all_large
  check_stale.py --all          # every prediction set with injected files
"""
from __future__ import annotations

import argparse
import pathlib
import sys

# marker -> (what it indicates, whether current code should contain it)
MARKERS = {
    "_unpinbench_blocker_": (
        "blocker installs behind a flag on sys; without it the conftest and "
        "sitecustomize finders recurse when a third-party package imports the "
        "blocked dependency (admitted 28 pairs on a harness crash)", True),
    "isinstance(f, _BlockedFinder)": (
        "blocker uses the superseded isinstance guard, which cannot see the "
        "other injected copy", False),
    "_REAL_ROOT": (
        "origin test compares resolved paths; without it a symlinked checkout "
        "classifies every repository frame as foreign and the blocker is inert", True),
    "UnpinBench blocker active": (
        "blocker announces activation, so a passing run without the line can be "
        "distinguished from one where it never loaded", True),
    "_unpinbench_recorder_": (
        "recorder installs behind a flag on sys; same recursion defect as the "
        "blocker", True),
    "_TRACE_FD = os.dup(1)": (
        "recorder keeps its own fd, so traces survive pytest's --capture=fd "
        "(without it a whole harness run yields zero traces)", True),
}

# which markers each kind of set is expected to carry
EXPECTED = {
    "blocker": ["_unpinbench_blocker_", "_REAL_ROOT", "UnpinBench blocker active"],
    "recorder": ["_unpinbench_recorder_", "_TRACE_FD = os.dup(1)"],
}


def kind_of(set_dir: pathlib.Path) -> str | None:
    """Does this set inject the blocker, the recorder, or neither?"""
    for p in sorted(set_dir.rglob("patch.diff"))[:5]:
        t = p.read_text(errors="ignore")
        if "_BlockedFinder" in t:
            return "blocker"
        if "UnpinBench: record calls" in t or "_MARKER" in t:
            return "recorder"
    return None


def check(set_dir: pathlib.Path) -> dict:
    patches = sorted(set_dir.rglob("patch.diff"))
    if not patches:
        return dict(status="empty", n=0)
    kind = kind_of(set_dir)
    if kind is None:
        return dict(status="no injected file", n=len(patches))
    problems, ok = [], []
    for marker in EXPECTED[kind]:
        desc, want = MARKERS[marker]
        n = sum(1 for p in patches if marker in p.read_text(errors="ignore"))
        if want and n < len(patches):
            problems.append(f"{len(patches) - n} of {len(patches)} lack `{marker}`: {desc}")
        else:
            ok.append(marker)
    # markers that must NOT be present
    for marker, (desc, want) in MARKERS.items():
        if want:
            continue
        n = sum(1 for p in patches if marker in p.read_text(errors="ignore"))
        if n:
            problems.append(f"{n} of {len(patches)} still contain `{marker}`: {desc}")
    return dict(status="STALE" if problems else "current", n=len(patches),
                kind=kind, problems=problems, ok=ok)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("sets", nargs="*", default=[])
    ap.add_argument("--all", action="store_true")
    a = ap.parse_args()
    dirs = [pathlib.Path(s) for s in a.sets]
    if a.all or not dirs:
        dirs = sorted(p for p in pathlib.Path("predictions").iterdir() if p.is_dir())

    stale = 0
    for d in dirs:
        r = check(d)
        if r["status"] in ("empty", "no injected file"):
            continue
        mark = "STALE  " if r["status"] == "STALE" else "current"
        print(f"{mark}  {d.name:16s} {r['n']:4d} patches ({r['kind']})")
        for p in r["problems"]:
            print(f"           {p}")
        stale += r["status"] == "STALE"
    if stale:
        print(f"\n{stale} set(s) are stale. Results from them must not be reported "
              "until the set is regenerated and re-dispatched.")
    sys.exit(1 if stale else 0)


if __name__ == "__main__":
    main()
