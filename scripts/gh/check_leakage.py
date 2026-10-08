#!/usr/bin/env python3
"""Find pool pairs where another file also declares the removed package.

Two severities, and conflating them would either keep a broken task or discard
a sound one:

  second install source   CI installs from that other file, so deleting the
                          declaration removes nothing. The task is unwinnable
                          by doing the right thing and passable by doing
                          nothing. Disqualifying.
  name appears elsewhere  a docs requirements file, a dev lock, a tox env. CI
                          never installs from it. Harmless: the agent is told
                          which dependency to remove, so there is no hidden
                          answer, and the grader scores the rewrite rather than
                          the naming.

usage: check_leakage.py [--pool pilot/instances.jsonl] [--json out.json]
"""
from __future__ import annotations

import argparse
import collections
import json
import pathlib
import re

PATTERNS = ["requirements*.txt", "*.lock", "constraints*.txt", "Pipfile",
            "environment.yml", "tox.ini", ".pre-commit-config.yaml", "*.cfg"]


def declares(path: pathlib.Path, dep: str) -> bool:
    a, b = dep.lower().replace("_", "-"), dep.lower().replace("-", "_")
    try:
        text = path.read_text(errors="ignore").lower()
    except OSError:
        return False
    for line in text.splitlines():
        s = line.strip()
        if not s or s.startswith("#"):
            continue
        if re.match(r"^['\"]?(%s|%s)\b" % (re.escape(a), re.escape(b)), s):
            return True
    return False


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--pool", default="pilot/instances.jsonl")
    ap.add_argument("--repo-data", default=".cache/repo-data")
    ap.add_argument("--datasets", nargs="*",
                    default=[".cache/dataset-dibench-regular.jsonl",
                             ".cache/dataset-dibench-large.jsonl"])
    ap.add_argument("--json", default=None)
    a = ap.parse_args()

    rows = {}
    for d in a.datasets:
        p = pathlib.Path(d)
        if p.exists():
            for line in open(p):
                if line.strip():
                    r = json.loads(line)
                    rows.setdefault(r["instance_id"], r)

    hard, soft = [], []
    for line in open(a.pool):
        p = json.loads(line)
        repo = pathlib.Path(a.repo_data) / "python" / p["instance_id"]
        row = rows.get(p["instance_id"])
        if not repo.is_dir() or row is None:
            continue
        bf = pathlib.Path(p.get("build_file") or "").name
        ci = repo / (row.get("ci_file") or "")
        ci_text = ci.read_text(errors="ignore") if ci.exists() else ""
        for pat in PATTERNS:
            for f in list(repo.glob(pat)) + list(repo.glob("*/" + pat)):
                if not f.is_file() or f.name == bf or not declares(f, p["dependency"]):
                    continue
                rel = str(f.relative_to(repo))
                rec = dict(instance_id=p["instance_id"], dependency=p["dependency"], file=rel)
                (hard if (rel in ci_text or f.name in ci_text) else soft).append(rec)
                break
            else:
                continue
            break

    print(f"second install source (DISQUALIFYING): {len(hard)}")
    for h in hard:
        print(f"  {h['instance_id'][:30]:30s} {h['dependency']:18s} via {h['file']}")
    print(f"\nname appears elsewhere (harmless): {len(soft)}")
    for f, n in collections.Counter(s["file"] for s in soft).most_common(8):
        print(f"  {n:3d}  {f}")
    if a.json:
        pathlib.Path(a.json).write_text(json.dumps(dict(hard=hard, soft=soft), indent=1))


if __name__ == "__main__":
    main()
