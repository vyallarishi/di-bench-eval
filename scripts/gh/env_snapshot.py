#!/usr/bin/env python3
"""Recover the environment of the reported runs from their saved workflow logs.

Package versions resolve when a workflow runs, so the only record of what a
reported run installed is its own log. This reads every saved log and takes
what the installers printed: pip's "Successfully installed", poetry's
"Installing name (version)", uv's and pip freeze's "name==version", and the
interpreter version. Nothing is re-run and nothing is inferred: a package no
installer line names is absent, and a package seen with two versions is kept
with both.

Output, per repository: every workflow job with its interpreter and its
package versions, taken from the unmodified (gold) runs, and a pip constraints
file per job. The summary says how complete the record is.

usage:  env_snapshot.py [--logs run_logs] [--out data/environments]
"""
from __future__ import annotations

import argparse
import collections
import csv
import json
import pathlib
import re

ROOT = pathlib.Path(__file__).resolve().parents[2]
LINE = re.compile(r"^\[([^\]]+)\]\s+\|\s?(.*)$")
PIP = re.compile(r"Successfully installed (.+)$")
POETRY = re.compile(r"(?:Installing|Updating) ([A-Za-z0-9_.\-]+) \((?:[^ )]+ -> )?(\d[^ )]*)\)")
PINNED = re.compile(r"^\s*\+?\s*([A-Za-z0-9_.\-]+)==(\d[A-Za-z0-9_.!+\-]*)\s*$")
PYTHON = re.compile(r"(?:[Pp]ython[ \-/]|CPython \(|cpython-)(3\.\d+\.\d+)")


def norm(name: str) -> str:
    return re.sub(r"[-_.]+", "-", name).lower()


def read_log(path: pathlib.Path) -> dict:
    """{job: {"python": Counter, "packages": {name: set(versions)}}}"""
    jobs: dict = {}
    # split on newlines only: pip's progress bars put carriage returns inside a line
    job = None
    for raw in path.read_text(errors="ignore").split("\n"):
        raw = raw.replace("\r", " ")
        m = LINE.match(raw)
        if m:
            job, text = m.group(1).strip(), m.group(2)
        elif job:
            text = raw                    # a continuation of the same job's output
        else:
            continue
        j = jobs.setdefault(job, {"python": collections.Counter(), "packages": collections.defaultdict(set)})
        for v in PYTHON.findall(text):
            j["python"][v] += 1
        p = PIP.search(text)
        if p:
            for tok in p.group(1).split():
                name, _, ver = tok.rpartition("-")
                if name and ver[:1].isdigit():
                    j["packages"][norm(name)].add(ver)
            continue
        for name, ver in POETRY.findall(text):
            j["packages"][norm(name)].add(ver)
        q = PINNED.match(text)
        if q:
            j["packages"][norm(q.group(1))].add(q.group(2))
        elif "==" in text and "," in text:
            # tox prints the environment's pip freeze on one line, comma-separated
            for tok in text.split(": ", 1)[-1].split(","):
                q = PINNED.match(tok)
                if q:
                    j["packages"][norm(q.group(1))].add(q.group(2))
    return jobs


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--logs", default=str(ROOT / "run_logs"))
    ap.add_argument("--out", default=str(ROOT / "data/environments"))
    ap.add_argument("--artifacts", default=None, help="tsv of id, name, size, expired, date, run, branch")
    a = ap.parse_args()
    out = pathlib.Path(a.out)
    (out / "constraints").mkdir(parents=True, exist_ok=True)

    branch, date = {}, {}
    if a.artifacts:
        for r in csv.reader(open(a.artifacts), delimiter="\t"):
            branch[r[5]], date[r[5]] = r[6], r[4]

    pool = [json.loads(l) for l in open(ROOT / "pilot/instances.jsonl") if l.strip()]
    repos = sorted({r["instance_id"] for r in pool})

    # per repository: gold runs give the snapshot, every run gives the drift check
    gold = {r: {} for r in repos}
    seen = {r: collections.defaultdict(lambda: collections.defaultdict(set)) for r in repos}
    n_logs = collections.Counter()
    for log in sorted(pathlib.Path(a.logs).rglob("exec-output.log")):
        run, artifact, inst = log.parts[-6], log.parts[-5], log.parts[-3]
        if branch and branch.get(run) != "main":
            continue                      # the reported runs are the ones on main
        repo = inst.split("__")[0]
        if repo not in gold:
            continue
        jobs = read_log(log)
        n_logs[repo] += 1
        for job, j in jobs.items():
            for name, vers in j["packages"].items():
                seen[repo][job][name] |= vers
        if "__" not in inst and "-gold-" in artifact:
            for job, j in jobs.items():
                g = gold[repo].setdefault(job, {"python": collections.Counter(), "packages": collections.defaultdict(set),
                                                "runs": set()})
                g["python"] += j["python"]
                g["runs"].add(run)
                for name, vers in j["packages"].items():
                    g["packages"][name] |= vers

    summary = {"repositories": len(repos), "with_gold_log": 0, "jobs": 0, "packages": 0,
               "one_version_in_gold": 0, "one_version_in_all_runs": 0, "pairs": len(pool),
               "pairs_with_dependency_version": 0, "logs_read": sum(n_logs.values()),
               "run_dates": sorted({date[r] for r in date if branch.get(r) == "main"})[:1] +
                            sorted({date[r] for r in date if branch.get(r) == "main"})[-1:]}
    per_repo = {}
    for repo in repos:
        jobs = gold[repo]
        if any(g["packages"] for g in jobs.values()):
            summary["with_gold_log"] += 1
        doc = {}
        for job, g in sorted(jobs.items()):
            if not g["packages"]:
                continue
            py = g["python"].most_common(1)
            doc[job] = {"python": py[0][0] if py else None, "runs": sorted(g["runs"]),
                        "packages": {n: sorted(v) for n, v in sorted(g["packages"].items())}}
            summary["jobs"] += 1
            for n, v in g["packages"].items():
                summary["packages"] += 1
                summary["one_version_in_gold"] += len(v) == 1
                summary["one_version_in_all_runs"] += len(seen[repo][job].get(n, v)) == 1
            safe = re.sub(r"[^A-Za-z0-9_.-]+", "_", job)
            (out / "constraints" / f"{repo}__{safe}.txt").write_text(
                "".join(f"{n}=={v[-1]}\n" for n, v in doc[job]["packages"].items()))
        per_repo[repo] = doc
        (out / f"{repo}.json").write_text(json.dumps(doc, indent=1))

    missing = []
    for r in pool:
        dep = norm(r["dependency"])
        if any(dep in j["packages"] for j in per_repo[r["instance_id"]].values()):
            summary["pairs_with_dependency_version"] += 1
        else:
            missing.append(f"{r['instance_id']}|{r['dependency']}")
    summary["packages_per_repository_median"] = sorted(
        len({n for j in d.values() for n in j["packages"]}) for d in per_repo.values())[len(per_repo) // 2]
    summary["repositories_under_10_packages"] = sorted(
        r for r, d in per_repo.items() if len({n for j in d.values() for n in j["packages"]}) < 10)
    summary["pairs_without_dependency_version"] = missing
    (out / "summary.json").write_text(json.dumps(summary, indent=1))
    for k, v in summary.items():
        if not isinstance(v, list) or len(v) <= 12:
            print(f"{k}: {v}")
        else:
            print(f"{k}: {len(v)} entries, e.g. {v[:6]}")


if __name__ == "__main__":
    main()
