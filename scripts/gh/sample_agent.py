#!/usr/bin/env python3
"""Draw the agent-evaluation sample so the result cannot be dismissed as a subset artifact.

A proportional sample of this pool would be indefensible in one specific way:
one repository supplies 39 of the 330 pairs, so proportional sampling gives it
12 of 100 and invites the reviewer to say the agent result is a property of
that project. The same argument applies to `numpy`, which appears 14 times.

So the draw is stratified on the two dimensions the paper reports (tier and
release subset), proportionally, with two caps applied inside the strata:

  at most MAX_PER_REPO pairs from any one repository
  at most MAX_PER_DEP pairs for any one dependency

and, within a stratum, pairs are preferred in an order that maximises
coverage: a repository not yet drawn beats one already drawn, then a
dependency not yet drawn,         then the
footprint band the sample is most short of relative to the stratum (so the
draw reproduces the pool's distribution of how much code must change, not
merely its median). The seed is recorded and the whole
thing is deterministic.

Trace availability is deliberately NOT a preference. Preferring pairs the
behavioural gate can grade would make the sample easier to grade than the pool
it stands for, and the agent pass rate would be reported on a subset selected
for the property the grader needs. Coverage of the sample is reported instead,
so the reader sees how much of it the gate can speak about.

Reported alongside the sample: its marginals against the pool's, so a reader
can check the draw rather than trust it.

usage:
  sample_agent.py --pool pilot/instances.jsonl --n 100 --out pilot/agent_sample_100.jsonl
"""
from __future__ import annotations

import argparse
import collections
import json
import pathlib
import random
import statistics

TIERS = ["strong", "medium", "hard", "indirect"]
SUBSETS = ["regular", "large"]


# How much code the removal touches, in bands, because the exact file count has
# a long tail (0 to 88) and a median match on it hides the shape.
BANDS = [(0, 0), (1, 1), (2, 2), (3, 4), (5, 9), (10, 10 ** 6)]


def band(n: int) -> tuple:
    return next(b for b in BANDS if b[0] <= n <= b[1])


def norm(d: str) -> str:
    return d.replace("-", "_").replace(".", "_").lower()


def trace_key(r: dict) -> str:
    return f"{r['instance_id']}__trace__{norm(r['dependency'])}"


def allocate(pool: list[dict], n: int) -> dict[tuple, int]:
    """Largest-remainder allocation of n across (tier, subset) strata."""
    counts = collections.Counter((r["tier"], r["subset"]) for r in pool)
    total = sum(counts.values())
    exact = {k: n * v / total for k, v in counts.items()}
    base = {k: int(v) for k, v in exact.items()}
    left = n - sum(base.values())
    for k, _ in sorted(exact.items(), key=lambda kv: -(kv[1] - int(kv[1])))[:left]:
        base[k] += 1
    return base


def draw(pool: list[dict], n: int, max_per_repo: int, max_per_dep: int,
         traces: set[str], seed: int) -> list[dict]:
    rnd = random.Random(seed)
    quota = allocate(pool, n)
    by_stratum: dict[tuple, list[dict]] = collections.defaultdict(list)
    for r in pool:
        by_stratum[(r["tier"], r["subset"])].append(r)

    chosen: list[dict] = []
    repo_n: collections.Counter = collections.Counter()
    dep_n: collections.Counter = collections.Counter()

    # strata in a fixed order, smallest first: the tight strata (indirect) get
    # their pick of repositories before the large ones consume the budget
    order = sorted(quota, key=lambda k: (len(by_stratum[k]), k))
    for stratum in order:
        want = quota[stratum]
        cands = list(by_stratum[stratum])
        rnd.shuffle(cands)                       # break ties reproducibly
        # Target share of each footprint band within this stratum, from the pool.
        target = collections.Counter(band(c["footprint_files"]) for c in cands)
        for k in target:
            target[k] = target[k] / len(cands)
        got: collections.Counter = collections.Counter()
        taken = 0
        while taken < want and cands:
            def rank(c):
                # Footprint bands are matched to the stratum's distribution, NOT
                # minimised, and trace availability is not consulted: either
                # would bias the sample toward work that is easier to do or
                # easier to grade than the pool it represents.
                b = band(c["footprint_files"])
                deficit = target[b] * max(1, taken + 1) - got[b]
                return (repo_n[c["instance_id"]],                 # new repo first
                        dep_n[norm(c["dependency"])],             # then new dependency
                        -deficit,                                 # then the short band
                        c["instance_id"], norm(c["dependency"]))  # deterministic tie-break
            cands.sort(key=rank)
            pick = next((c for c in cands
                         if repo_n[c["instance_id"]] < max_per_repo
                         and dep_n[norm(c["dependency"])] < max_per_dep), None)
            if pick is None:
                break                            # caps bind; shortfall redistributed below
            cands.remove(pick)
            chosen.append(pick)
            repo_n[pick["instance_id"]] += 1
            dep_n[norm(pick["dependency"])] += 1
            got[band(pick["footprint_files"])] += 1
            taken += 1

    # any shortfall from a binding cap is filled from the pool at large, still
    # respecting the caps, so the sample size is exact and the reason is logged
    if len(chosen) < n:
        rest = [r for r in pool if r not in chosen]
        rnd.shuffle(rest)
        pool_med = statistics.median([r["footprint_files"] for r in pool])
        rest.sort(key=lambda c: (repo_n[c["instance_id"]], dep_n[norm(c["dependency"])],
                                 abs(c["footprint_files"] - pool_med)))
        for c in rest:
            if len(chosen) >= n:
                break
            if repo_n[c["instance_id"]] < max_per_repo and dep_n[norm(c["dependency"])] < max_per_dep:
                chosen.append(c)
                repo_n[c["instance_id"]] += 1
                dep_n[norm(c["dependency"])] += 1
    return chosen


def report(pool: list[dict], sample: list[dict], traces: set[str]) -> str:
    out = []
    n, N = len(sample), len(pool)
    out.append(f"sample {n} of {N} pairs\n")

    def marg(key, label, order=None):
        pc = collections.Counter(key(r) for r in pool)
        sc = collections.Counter(key(r) for r in sample)
        keys = order or sorted(pc, key=lambda k: -pc[k])
        out.append(f"{label:<14}{'pool':>14}{'sample':>14}")
        for k in keys:
            out.append(f"  {str(k):<12}{pc[k]:>6} {pc[k]/N:>6.1%}{sc[k]:>7} {sc[k]/n:>6.1%}")
        out.append("")

    marg(lambda r: r["tier"], "tier", TIERS)
    marg(lambda r: r["subset"], "subset", SUBSETS)
    marg(lambda r: r["test_reachable"], "test-reachable", [True, False])
    marg(lambda r: f"{r['footprint_files']}" if r["footprint_files"] < 3
         else ("3-4" if r["footprint_files"] < 5 else ("5-9" if r["footprint_files"] < 10 else "10+")),
         "footprint", ["0", "1", "2", "3-4", "5-9", "10+"])

    rp = collections.Counter(r["instance_id"] for r in sample)
    dp = collections.Counter(norm(r["dependency"]) for r in sample)
    pool_rp = collections.Counter(r["instance_id"] for r in pool)
    out.append(f"repositories   {len(pool_rp):>6} in pool   {len(rp):>6} in sample")
    out.append(f"  most pairs from one repo: pool {max(pool_rp.values())} "
               f"({max(pool_rp, key=pool_rp.get)}), sample {max(rp.values())} "
               f"({max(rp, key=rp.get)})")
    out.append(f"dependencies   {len({norm(r['dependency']) for r in pool}):>6} in pool   "
               f"{len(dp):>6} in sample")
    out.append(f"  most pairs for one dependency: sample {max(dp.values())} "
               f"({max(dp, key=dp.get)})")
    fp_p = [r["footprint_files"] for r in pool]
    fp_s = [r["footprint_files"] for r in sample]
    out.append(f"footprint files  pool median {statistics.median(fp_p):.1f} "
               f"mean {statistics.mean(fp_p):.1f} max {max(fp_p)}   "
               f"sample median {statistics.median(fp_s):.1f} "
               f"mean {statistics.mean(fp_s):.1f} max {max(fp_s)}")
    out.append(f"with a reference trace  pool {sum(1 for r in pool if trace_key(r) in traces)}"
               f" ({sum(1 for r in pool if trace_key(r) in traces)/N:.0%})   "
               f"sample {sum(1 for r in sample if trace_key(r) in traces)}"
               f" ({sum(1 for r in sample if trace_key(r) in traces)/n:.0%})")
    return "\n".join(out)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--pool", default="pilot/instances.jsonl")
    ap.add_argument("--n", type=int, default=100)
    ap.add_argument("--max-per-repo", type=int, default=4)
    ap.add_argument("--max-per-dep", type=int, default=4)
    ap.add_argument("--traces", default="oracle-blindness/data/traces")
    ap.add_argument("--seed", type=int, default=20261009)
    ap.add_argument("--out", default=None)
    a = ap.parse_args()

    pool = [json.loads(l) for l in open(a.pool) if l.strip()]
    traces = {p.name[:-6] for p in pathlib.Path(a.traces).glob("*.jsonl")}
    sample = draw(pool, a.n, a.max_per_repo, a.max_per_dep, traces, a.seed)
    print(report(pool, sample, traces))
    print(f"\nseed {a.seed}, caps: {a.max_per_repo} per repository, {a.max_per_dep} per dependency")
    if a.out:
        with open(a.out, "w") as f:
            for r in sorted(sample, key=lambda r: (r["instance_id"], r["dependency"])):
                f.write(json.dumps(r) + "\n")
        print(f"wrote {a.out}")


if __name__ == "__main__":
    main()
