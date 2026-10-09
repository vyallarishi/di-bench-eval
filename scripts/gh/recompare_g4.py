#!/usr/bin/env python3
"""Re-apply the current G4a comparison to traces a run_g4.py run kept.

`run_g4.py --keep DIR` leaves each instance's reference and candidate traces
and its usage map on disk, so a change to the comparison rules (not to the
recorder) can be re-evaluated without re-running any suite. The result file
is rewritten with the new g4a fields and a note of what was recomputed.

usage: recompare_g4.py --results run.json [run2.json ...] --keep DIR [DIR ...] --out merged.json
"""
from __future__ import annotations

import argparse
import json
import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
import gate_behaviour  # noqa: E402


def find_keep(dirs, mid):
    """The directory holding this instance's kept traces.

    A candidate that recorded nothing left no cand.jsonl (the recorder writes
    on the first call), so the reference trace plus the usage map identify
    the directory and the candidate trace is read as empty when absent.
    """
    for d in dirs:
        for cand in (pathlib.Path(d) / mid, pathlib.Path(d)):
            if (cand / f"{mid}.usage.json").exists() or (cand / "ref.jsonl").exists() and cand.name == mid:
                return cand
    return None


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--results", nargs="+", required=True)
    ap.add_argument("--keep", nargs="+", required=True)
    ap.add_argument("--out", required=True)
    a = ap.parse_args()
    rows = []
    seen = set()
    for f in a.results:
        for r in json.load(open(f)):
            if r["id"] in seen:
                continue
            seen.add(r["id"])
            rows.append(r)
    done = 0
    for r in rows:
        if r.get("status") != "ok":
            continue
        k = find_keep(a.keep, r["id"])
        if k is None:
            r["recomputed"] = False
            continue
        ref = gate_behaviour.load(k / "ref.jsonl")
        cand = gate_behaviour.load(k / "cand.jsonl")
        sf = {}
        u = k / f"{r['id']}.usage.json"
        if u.exists():
            sf = json.loads(u.read_text()).get("site_function", {})
        g = gate_behaviour.compare(ref, cand, sf)
        r["g4a"] = {x: v for x, v in g.items() if x not in ("divergences", "missing_calls", "discarded")}
        r["g4a_evidence"] = dict(divergences=g["divergences"][:5], not_observable=g["missing_calls"][:5],
                                 discarded=g["discarded"][:3])
        r["recomputed"] = True
        done += 1
        print(f"  {r['id'][:60]:60s} {g['verdict']:10s} [{g['decided_at']}] {g['reason'][:80]}")
    pathlib.Path(a.out).write_text(json.dumps(rows, indent=1, default=str))
    print(f"{done} recomputed -> {a.out}")


if __name__ == "__main__":
    main()
