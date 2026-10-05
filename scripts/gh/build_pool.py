#!/usr/bin/env python3
"""Assemble the verified removal benchmark from execution results.

A pair (repository, dependency) enters the pool only if CI *fails* when the
dependency is removed, on a repository whose gold manifest *passes* in the same
harness. Three result sets feed it:

  regular / deletion   plain-deletion mutants   <iid>__del__<dep>    (DI-Bench regular)
  regular / blocked    import-blocked mutants   <iid>__block__<dep>  (the 91 log-phantoms re-screened)
  large   / blocked    import-blocked mutants   <iid>__block__<dep>  (DI-Bench large)

Blocked failures must be attributable: the CI log has to contain the blocker's
own ImportError message. Deletion failures are taken as DI-Bench reports them.

Each row carries the static footprint of the removed package (which files import
it, whether a test reaches them, attribute-level uses) and a tier derived from
the non-test footprint:

  indirect  0 files      package reached only indirectly (plugin, entry point, CLI)
  strong    1-2 files    the original pilot's "strong" tier
  medium    3-4 files    the original pilot's "medium" tier
  hard      5+ files

usage: build_pool.py --out pilot/instances.jsonl
         --gold-regular DIR --mutation DIR --blocked-regular DIR
         --gold-large DIR --blocked-large DIR [--repo-data .cache/repo-data]
"""
from __future__ import annotations

import argparse
import collections
import json
import pathlib
import re
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
from footprint import RepoIndex  # noqa: E402
from manifests import norm  # noqa: E402

BLOCK_MSG = re.compile(r"blocked: dependency")


def load_results(d: pathlib.Path) -> dict[str, dict]:
    """instance_id -> {exec, log_path}. Accepts flat <id>.json or nested eval-result.json."""
    out = {}
    for f in list(d.rglob("eval-result.json")) + list(d.glob("*.json")):
        try:
            r = json.loads(f.read_text())
        except Exception:
            continue
        iid = r.get("instance_id")
        if not iid or "exec" not in r:
            continue
        log = f.parent / "eval-workspace" / "exec-output.log"
        out[iid] = dict(exec=r["exec"], log=log if log.exists() else None)
    return out


def gold_pass(d: pathlib.Path) -> set[str]:
    return {i for i, r in load_results(d).items() if r["exec"] == "pass"}


def split_id(mid: str):
    for sep in ("__block__", "__del__"):
        if sep in mid:
            base, dep = mid.split(sep, 1)
            return base, dep, "blocked" if sep == "__block__" else "deletion"
    return None


def attributable(r: dict, kind: str) -> str | None:
    """Evidence string if the failure is attributable to the removed package."""
    if r["exec"] != "fail":
        return None
    if kind == "deletion":
        return "deletion_ci_fail"
    if r["log"] and BLOCK_MSG.search(r["log"].read_text(errors="ignore")):
        return "blocked_import_error"
    return None


def tier_of(n_src: int) -> str:
    if n_src == 0:
        return "indirect"
    if n_src <= 2:
        return "strong"
    if n_src <= 4:
        return "medium"
    return "hard"


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", required=True)
    ap.add_argument("--gold-regular", required=True)
    ap.add_argument("--mutation", required=True)
    ap.add_argument("--blocked-regular", required=True)
    ap.add_argument("--gold-large", required=True)
    ap.add_argument("--blocked-large", required=True)
    ap.add_argument("--repo-data", default=".cache/repo-data")
    ap.add_argument("--phantom-pred", default="oracle-blindness/data/phantom_pred.json")
    ap.add_argument("--datasets", nargs="*",
                    default=[".cache/dataset-dibench-regular.jsonl", ".cache/dataset-dibench-large.jsonl"])
    a = ap.parse_args()

    build_file = {}
    for ds in a.datasets:
        p = pathlib.Path(ds)
        if p.exists():
            for line in open(p):
                if line.strip():
                    r = json.loads(line)
                    build_file[r["instance_id"]] = r["build_files"][0]

    phantom_pred = {}
    pp = pathlib.Path(a.phantom_pred)
    if pp.exists():
        raw = json.load(open(pp))
        # {"iid": {"dep": bool}} (phantom_predict.py) or [{"instance_id","dependency","predicted"}]
        if isinstance(raw, dict):
            for iid, deps in raw.items():
                for dep, v in deps.items():
                    phantom_pred[(iid, norm(dep))] = bool(v)
        else:
            for e in raw:
                phantom_pred[(e["instance_id"], norm(e["dependency"]))] = bool(
                    e.get("predicted", e.get("phantom_predicted")))

    sources = [
        ("regular", "deletion", gold_pass(pathlib.Path(a.gold_regular)), load_results(pathlib.Path(a.mutation))),
        ("regular", "blocked", gold_pass(pathlib.Path(a.gold_regular)), load_results(pathlib.Path(a.blocked_regular))),
        ("large", "blocked", gold_pass(pathlib.Path(a.gold_large)), load_results(pathlib.Path(a.blocked_large))),
    ]
    gold_counts = {s: len(g) for s, _k, g, _r in sources}

    rows, seen = [], set()
    stats = collections.Counter()
    for subset, kind, gold, results in sources:
        for mid, r in results.items():
            s = split_id(mid)
            if not s or s[2] != kind:
                continue
            base, dep, _ = s
            if base not in gold:
                stats[f"{subset}/{kind}: gold-failing repo"] += 1
                continue
            stats[f"{subset}/{kind}: conditioned"] += 1
            ev = attributable(r, kind)
            if ev is None:
                stats[f"{subset}/{kind}: " + ("blind spot (CI passes)" if r["exec"] == "pass"
                                              else "fail not attributable")] += 1
                continue
            key = (base, norm(dep))
            if key in seen:  # a deletion-verified pair also re-screened under blocking
                stats[f"{subset}/{kind}: duplicate of deletion-verified pair"] += 1
                continue
            seen.add(key)
            rows.append(dict(instance_id=base, dependency=dep, subset=subset,
                             build_file=build_file.get(base), mutant_id=mid,
                             verified_by=kind, evidence=ev, deletion_ci="fail",
                             phantom_predicted=phantom_pred.get(key)))
            stats[f"{subset}/{kind}: VERIFIED"] += 1

    # static footprint, one module graph per repository
    repo_data = pathlib.Path(a.repo_data) / "python"
    idx_cache: dict[str, RepoIndex] = {}
    for row in rows:
        repo = repo_data / row["instance_id"]
        if not repo.is_dir():
            row.update(footprint_files=None, test_reachable=None, source_files={},
                       test_files=[], attribute_uses=None, tier="unknown")
            continue
        idx = idx_cache.get(row["instance_id"])
        if idx is None:
            idx = idx_cache[row["instance_id"]] = RepoIndex(repo)
        fp = idx.footprint(row["dependency"])
        row.update(fp)
        row["tier"] = tier_of(fp["footprint_files"])

    rows.sort(key=lambda r: (r["subset"], r["instance_id"], r["dependency"]))
    out = pathlib.Path(a.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    with open(out, "w") as f:
        for row in rows:
            f.write(json.dumps(row) + "\n")

    print(f"gold-passing repositories: {gold_counts}")
    for k, v in sorted(stats.items()):
        print(f"  {v:4d}  {k}")
    print(f"\nVERIFIED POOL: {len(rows)} pairs over "
          f"{len({r['instance_id'] for r in rows})} repositories -> {out}")
    tab = collections.Counter((r["subset"], r["tier"]) for r in rows)
    for subset in ("regular", "large"):
        line = "  ".join(f"{t}={tab[(subset, t)]}" for t in ("indirect", "strong", "medium", "hard", "unknown"))
        print(f"  {subset:8s} {line}")
    by = collections.Counter((r["subset"], r["verified_by"]) for r in rows)
    print("  by verification:", dict(by))


if __name__ == "__main__":
    main()
