#!/usr/bin/env python3
"""Per-repository silent rates and the robustness checks of docs/ROBUSTNESS.md.

Inputs: the attribution of every screened candidate (`attribution.json`, one
row per candidate with its disposition) and, optionally, a list of silent
cases to exclude (from `activation.py`: silent verdicts whose block was not
observed). The rate of a repository is its silent candidates over all of its
candidates, pairs and exclusions included, as the ledger defines it; an
excluded silent case leaves both numerator and denominator, because the
screening produced no usable verdict for it.

Reports, over repositories with at least three candidates: median rate and
incidence; the same after dropping the k repositories with the most silent
cases; the rate distribution; and the correlation of the rate with the share
of a repository's files that are tests, the share reachable from tests, and
the candidate count.

usage:
  robustness.py --attribution results/attribution.json [--exclude results/activation.json]
                --repo-data .cache/repo-data --out results/robustness.json
"""
from __future__ import annotations

import argparse
import collections
import json
import math
import pathlib
import statistics
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
import footprint as FP  # noqa: E402

BUCKETS = [("0%", lambda r: r == 0), ("1-10%", lambda r: 0 < r <= 0.10),
           ("10-25%", lambda r: 0.10 < r <= 0.25), ("25-50%", lambda r: 0.25 < r <= 0.50),
           (">50%", lambda r: r > 0.50)]


def pearson(xs, ys):
    n = len(xs)
    if n < 2:
        return None
    mx, my = sum(xs) / n, sum(ys) / n
    sxx = sum((x - mx) ** 2 for x in xs)
    syy = sum((y - my) ** 2 for y in ys)
    if not sxx or not syy:
        return None
    return sum((x - mx) * (y - my) for x, y in zip(xs, ys)) / math.sqrt(sxx * syy)


def stats(rates: dict[str, float]) -> dict:
    vals = sorted(rates.values())
    return dict(repos=len(vals), median=round(statistics.median(vals), 4) if vals else None,
                incidence=sum(1 for v in vals if v > 0))


def compute(rows, exclude: set, repo_data: pathlib.Path | None, min_candidates=3) -> dict:
    by = collections.defaultdict(lambda: dict(n=0, silent=0))
    for r in rows:
        key = (r["instance_id"], r["dependency"])
        if r["disposition"] == "silent" and key in exclude:
            continue
        by[r["instance_id"]]["n"] += 1
        by[r["instance_id"]]["silent"] += r["disposition"] == "silent"
    rates = {repo: c["silent"] / c["n"] for repo, c in by.items() if c["n"] >= min_candidates}
    out = dict(rates=rates, counts={k: v for k, v in by.items() if v["n"] >= min_candidates},
               pooled=dict(silent=sum(c["silent"] for c in by.values()),
                           candidates=sum(c["n"] for c in by.values())),
               all=stats(rates))
    order = sorted(rates, key=lambda r: (-by[r]["silent"], r))
    out["drop_k"] = {k: stats({r: v for r, v in rates.items() if r not in set(order[:k])})
                     for k in (1, 3, 5, 10)}
    out["distribution"] = {name: sum(1 for v in rates.values() if f(v)) for name, f in BUCKETS}
    if repo_data is not None:
        xs = collections.defaultdict(list)
        for repo, rate in rates.items():
            idx = FP.RepoIndex(repo_data / "python" / repo)
            n_files = len(idx.info) or 1
            xs["test_file_share"].append(sum(1 for d in idx.info.values() if d["test"]) / n_files)
            xs["test_reachable_share"].append(len(idx.reach) / n_files)
            xs["candidate_count"].append(by[repo]["n"])
            xs["rate"].append(rate)
        out["correlation"] = {k: round(pearson(v, xs["rate"]), 3) for k, v in xs.items() if k != "rate"}
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--attribution", default="oracle-blindness/results/attribution.json")
    ap.add_argument("--exclude", default=None, help="activation.json; its excluded rows leave the census")
    ap.add_argument("--repo-data", default=".cache/repo-data")
    ap.add_argument("--no-correlation", action="store_true")
    ap.add_argument("--out", required=True)
    a = ap.parse_args()
    rows = json.load(open(a.attribution))
    exclude = set()
    if a.exclude:
        act = json.load(open(a.exclude))
        exclude = {(r["instance_id"], r["dependency"]) for r in act["rows"]
                   if r["status"].startswith("excluded")}
    rd = None if a.no_correlation else pathlib.Path(a.repo_data)
    res = dict(rates_all=compute(rows, set(), rd)["rates"])
    full = compute(rows, set(), rd)
    res.update(all_candidates=full)
    if exclude:
        conf = compute(rows, exclude, rd)
        res.update(rates_confirmed=conf["rates"], confirmed=conf, excluded=sorted(f"{a}|{b}" for a, b in exclude))
    for name in ("all_candidates", "confirmed"):
        if name not in res:
            continue
        c = res[name]
        print(f"{name}: pooled {c['pooled']['silent']}/{c['pooled']['candidates']}; "
              f"median {c['all']['median']}, incidence {c['all']['incidence']}/{c['all']['repos']}; "
              f"drop-k " + ", ".join(f"{k}: {v['median']} ({v['incidence']}/{v['repos']})" for k, v in c["drop_k"].items())
              + f"; distribution {c['distribution']}" + (f"; correlation {c['correlation']}" if "correlation" in c else ""))
    pathlib.Path(a.out).write_text(json.dumps(res, indent=1))
    print(f"-> {a.out}")


if __name__ == "__main__":
    main()
