#!/usr/bin/env python3
"""Was the import block live in each silent run? Apply the counting rule of section 3.2.

A silent verdict (CI passes with the declaration removed and the import
blocked) is evidence of oracle blindness only if the block was actually
loaded in that run. The block announces itself twice: on stderr when it is
installed (`UnpinBench blocker active: <dep>`), which the harness captures for
some workflows, and through pytest's saved console descriptor when it is
loaded inside pytest (`UnpinBench blocker active (pytest saved fd N): <dep>`).

The rule: a silent verdict counts when the run's log shows either
announcement, or when the repository never imports the package (over-declared,
or used without importing), in which case nothing could have triggered the
block and its activation is immaterial. Otherwise the case is excluded with
the reason "inconclusive: block not observed". Pool evidence -- another pair
in the same repository was detected by the block raising in a repository
frame -- is reported alongside as a cross-check but does not count.

usage:
  activation.py --results RES_DIR [RES_DIR ...] --blind data/instances.blind.jsonl
                --attribution results/attribution.json --pool data/instances.jsonl
                --out results/activation.json
"""
from __future__ import annotations

import argparse
import collections
import json
import pathlib

INSTALL_LINE = "UnpinBench blocker active:"
HOOK_LINE = "blocker active (pytest saved fd"
NEVER_IMPORTED = {"over-declared", "used without importing"}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--results", nargs="+", required=True)
    ap.add_argument("--blind", default="oracle-blindness/data/instances.blind.jsonl")
    ap.add_argument("--attribution", default="oracle-blindness/results/attribution.json")
    ap.add_argument("--pool", default="oracle-blindness/data/instances.jsonl")
    ap.add_argument("--out", required=True)
    a = ap.parse_args()

    logs = {}
    for root in a.results:
        for f in pathlib.Path(root).rglob("eval-result.json"):
            iid = f.parent.name
            try:
                ci = json.loads(f.read_text()).get("exec")
            except Exception:
                ci = None
            text = "".join(p.read_text(errors="replace")
                           for p in (f.parent / "eval-workspace").glob("*.log"))
            parts = iid.split("__")
            logs[(parts[0], parts[-1])] = dict(ci=ci, install=INSTALL_LINE in text,
                                               hook=HOOK_LINE in text, run_id=iid)
    cause = {(r["instance_id"], r["dependency"]): r["cause"]
             for r in json.load(open(a.attribution)) if r["disposition"] == "silent"}
    pool = [json.loads(l) for l in open(a.pool) if l.strip()]
    repo_block_evidence = {p["instance_id"] for p in pool
                          if p.get("evidence") == "blocked_import_in_repo_frame"}
    blind = [json.loads(l) for l in open(a.blind) if l.strip()]

    rows, tally = [], collections.Counter()
    for b in blind:
        key = (b["instance_id"], b["dependency"])
        lg = logs.get(key)
        c = cause.get(key)
        row = dict(instance_id=b["instance_id"], dependency=b["dependency"], cause=c,
                   rerun_ci=lg["ci"] if lg else None,
                   install_line=bool(lg and lg["install"]), hook_line=bool(lg and lg["hook"]),
                   pool_evidence=b["instance_id"] in repo_block_evidence)
        row["activation_observed"] = row["install_line"] or row["hook_line"]
        if lg is None:
            row["status"] = "no rerun"
        elif lg["ci"] != "pass":
            row["status"] = "rerun failed"
        elif row["activation_observed"]:
            row["status"] = "counted: block observed"
        elif c in NEVER_IMPORTED:
            row["status"] = "counted: never imported"
        else:
            row["status"] = "excluded: inconclusive, block not observed"
        tally[row["status"]] += 1
        rows.append(row)

    counted = [r for r in rows if r["status"].startswith("counted")]
    excluded = [r for r in rows if r["status"].startswith("excluded")]
    summary = dict(
        blind=len(rows), with_rerun=sum(1 for r in rows if r["rerun_ci"] is not None),
        rerun_pass=sum(1 for r in rows if r["rerun_ci"] == "pass"),
        install_line=sum(1 for r in rows if r["install_line"]),
        hook_line=sum(1 for r in rows if r["hook_line"]),
        either_line=sum(1 for r in rows if r["activation_observed"]),
        pool_evidence=sum(1 for r in rows if r["pool_evidence"]),
        either_line_or_pool=sum(1 for r in rows if r["activation_observed"] or r["pool_evidence"]),
        status=dict(tally),
        counted_by_cause=dict(collections.Counter(r["cause"] for r in counted)),
        excluded_by_cause=dict(collections.Counter(r["cause"] for r in excluded)),
        excluded_by_repo=dict(collections.Counter(r["instance_id"] for r in excluded)),
        strict_before=sum(1 for r in rows if r["cause"] == "imported, unguarded, untested"),
        strict_after=sum(1 for r in counted if r["cause"] == "imported, unguarded, untested"),
    )
    pathlib.Path(a.out).write_text(json.dumps(dict(summary=summary, rows=rows), indent=1))
    for k, v in summary.items():
        print(f"  {k}: {v}")
    print(f"-> {a.out}")


if __name__ == "__main__":
    main()
