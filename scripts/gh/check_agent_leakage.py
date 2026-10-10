#!/usr/bin/env python3
"""What can an agent read in its workspace that it should not?

Distinct from `check_leakage.py`, which asks whether a *second install source*
makes a pair unwinnable. This asks a narrower and more embarrassing question:
does the workspace we hand the agent contain anything belonging to the
evaluation rather than to the repository?

The agent's workspace is a copy of the masked checkout with the gold manifest
restored (`agent_runner.run_instance`), built by `snapshot()`, which walks the
tree and copies every file except `.git`. So anything our own tooling has ever
written into a checkout travels with it. Four classes are checked:

  our own injected files -- the import block and the usage recorder are
  written into the checkout as sitecustomize.py and conftest.py, and a stale
  copy left by an earlier run would hand the agent the grader's instrumentation
  recorded traces -- a reference trace names every call the repository makes
  into the package, which is the behavioural gate's oracle
  evaluation artifacts -- eval-result.json, patch.diff, results directories
  gold answers -- the unmasked manifest of another pair, a solution patch

Also reported, not as defects but so the paper can state them: files other
than the build file that name the package (the answer to DI-Bench's original
inference task, not to ours), and whether any lock file pins it.

usage:
  check_agent_leakage.py [--repo-data .cache/repo-data] [--pool pilot/instances.jsonl]
                         [--workspaces pilot/agent_out_*/python]
"""
from __future__ import annotations

import argparse
import collections
import json
import pathlib
import re
import sys

OURS = {
    "sitecustomize.py": "our injected block or recorder lives here",
    "conftest.py": "our injected block or recorder lives here too (a real repo may also have one)",
}
OUR_MARKERS = [
    ("UnpinBench", "our own injected code, by name"),
    ("_unpinbench_blocker_", "the import block's install flag"),
    ("_unpinbench_recorder_", "the usage recorder's install flag"),
    ("_BlockedFinder", "the import block's meta-path finder"),
    ("UNPINTRACE", "the trace marker the recorder emits"),
]
ARTIFACTS = ["eval-result.json", "patch.diff", "eval-workspace", "usage.jsonl",
             "ref.jsonl", "cand.jsonl", ".unpinbench"]


def scan_tree(root: pathlib.Path) -> dict:
    """Our own leavings in one checkout or workspace."""
    found = collections.defaultdict(list)
    for p in root.rglob("*"):
        if ".git" in p.parts or not p.is_file():
            continue
        rel = str(p.relative_to(root))
        if p.name in ARTIFACTS or any(a in rel for a in ARTIFACTS):
            # A filename alone is not evidence: NVFlare checks in its own
            # nvflight/patch.diff, and a repository may legitimately ship a
            # file called patch.diff or usage.jsonl. Only count it when it is
            # at the root (where we would have written it) or carries one of
            # our markers.
            try:
                head = p.read_text(errors="ignore")[:4000]
            except Exception:
                head = ""
            ours = any(m in head for m, _ in OUR_MARKERS)
            if ours or "/" not in rel:
                found["evaluation artifact"].append(rel + ("" if ours else " (at the root)"))
            continue
        if p.name in OURS or p.suffix in (".py", ".cfg", ".toml", ".ini", ".txt"):
            try:
                t = p.read_text(errors="ignore")
            except Exception:
                continue
            for marker, why in OUR_MARKERS:
                if marker in t:
                    found[f"our code: {why}"].append(rel)
                    break
    return dict(found)


def names_package(root: pathlib.Path, dep: str, build_file: str) -> list[str]:
    """Files other than the build file that mention the package."""
    pat = re.compile(re.escape(dep.replace("_", "[-_.]")).replace("\\[", "[").replace("\\]", "]"), re.I)
    hits = []
    for p in root.rglob("*"):
        if ".git" in p.parts or not p.is_file():
            continue
        rel = str(p.relative_to(root))
        if rel == build_file or p.suffix not in (".txt", ".toml", ".cfg", ".ini", ".lock", ".yml", ".yaml"):
            continue
        try:
            if pat.search(p.read_text(errors="ignore")):
                hits.append(rel)
        except Exception:
            pass
    return hits


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--repo-data", default=".cache/repo-data")
    ap.add_argument("--pool", default="pilot/instances.jsonl")
    ap.add_argument("--workspaces", nargs="*", default=[])
    ap.add_argument("--limit", type=int, default=0)
    a = ap.parse_args()

    pool = [json.loads(l) for l in open(a.pool) if l.strip()]
    repos = sorted({r["instance_id"] for r in pool})
    if a.limit:
        repos = repos[: a.limit]

    print(f"== checkouts handed to agents ({len(repos)} repositories)")
    bad = collections.Counter()
    for iid in repos:
        root = pathlib.Path(a.repo_data) / "python" / iid
        if not root.is_dir() or root.is_symlink():
            continue
        found = scan_tree(root)
        for kind, files in found.items():
            bad[kind] += len(files)
            print(f"  LEAK  {iid}: {kind}")
            for f in files[:3]:
                print(f"          {f}")
    if not bad:
        print("  clean: no injected file, trace, or evaluation artifact in any checkout")

    # the workspaces the agents actually saw, reconstructed from their patches
    for w in a.workspaces:
        d = pathlib.Path(w)
        if not d.is_dir():
            continue
        print(f"\n== patches produced under {w}")
        touched = collections.Counter()
        for pf in d.rglob("patch.diff"):
            for line in pf.read_text(errors="ignore").splitlines():
                if line.startswith("diff --git"):
                    f = line.split(" b/")[-1]
                    if f in OURS or f in ARTIFACTS:
                        touched[f] += 1
        if touched:
            print("  agents edited files that are ours, not the repository's:")
            for f, n in touched.most_common():
                print(f"    {n:3d}  {f}")
        else:
            print("  no agent patch touches an injected or evaluation file")

    print("\n== the package named outside the build file (reported, not a defect)")
    rows = pool[: a.limit] if a.limit else pool
    named = 0
    for r in rows:
        root = pathlib.Path(a.repo_data) / "python" / r["instance_id"]
        if not root.is_dir():
            continue
        hits = names_package(root, r["dependency"], r.get("build_file") or "")
        if hits:
            named += 1
    print(f"  {named} of {len(rows)} pairs name the package in some other file.")
    print("  This is the answer to DI-Bench's inference task, not to ours: the agent")
    print("  is TOLD which package to remove, so a file naming it reveals nothing.")
    print("  Disqualifying only when CI installs from that file -- see check_leakage.py.")
    sys.exit(1 if bad else 0)


if __name__ == "__main__":
    main()
