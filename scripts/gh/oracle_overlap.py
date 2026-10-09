#!/usr/bin/env python3
"""The three oracles on identical candidates: CI replay, static import check, collection-only.

Per screened candidate (every candidate but the excluded ones), three verdicts:
CI replay as measured; the import check derived from the attribution ("an
unguarded import exists", which is what a type checker's import resolution
would flag with the package absent); collection-only derived from the
screening log ("the failure happened at collection"). Silent cases excluded
by the activation rule leave the population.

usage:
  oracle_overlap.py --attribution results/attribution.json --collection results/collection_stage.json
                    [--exclude results/activation.json] --out results/oracle_overlap.json
"""
from __future__ import annotations

import argparse
import collections
import json
import pathlib

STRICT = "imported, unguarded, untested"


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--attribution", default="oracle-blindness/results/attribution.json")
    ap.add_argument("--collection", default="oracle-blindness/results/collection_stage.json")
    ap.add_argument("--exclude", default=None)
    ap.add_argument("--out", required=True)
    a = ap.parse_args()
    rows = json.load(open(a.attribution))
    coll = json.load(open(a.collection))
    exclude = set()
    if a.exclude:
        exclude = {(r["instance_id"], r["dependency"]) for r in json.load(open(a.exclude))["rows"]
                   if r["status"].startswith("excluded")}
    out, tally = [], collections.Counter()
    for r in rows:
        if r["disposition"] == "excluded":
            continue
        key = (r["instance_id"], r["dependency"])
        if key in exclude:
            tally["excluded by the activation rule"] += 1
            continue
        ci = r["disposition"] == "pair"
        # the import check sees an unguarded import of an absent package
        guarded = r["guard"] in ("recovers", "fallback_to") or r["cause"] == "optional by design"
        unguarded = bool(r["footprint_files"] or r["test_files"]) and not guarded
        mid = f"{r['instance_id']}__block__{r['dependency'].lower().replace('-', '_').replace('.', '_')}"
        collection = bool(coll.get(mid, False)) if ci else False
        out.append(dict(instance_id=r["instance_id"], dependency=r["dependency"], ci_detects=ci,
                        import_check_detects=unguarded, collection_only_detects=collection,
                        cause=r["cause"]))
        tally[(ci, unguarded, collection)] += 1
    print(f"{len(out)} screened candidates")
    print("CI / import check / collection-only -> n")
    for k, v in sorted(tally.items(), key=lambda kv: str(kv[0])):
        print(f"  {k}: {v}")
    print(f"silent: CI {sum(1 for o in out if not o['ci_detects'])}, "
          f"import check {sum(1 for o in out if not o['import_check_detects'])}, "
          f"collection-only {sum(1 for o in out if not o['collection_only_detects'])}")
    pathlib.Path(a.out).write_text(json.dumps(out, indent=0))
    print(f"-> {a.out}")


if __name__ == "__main__":
    main()
