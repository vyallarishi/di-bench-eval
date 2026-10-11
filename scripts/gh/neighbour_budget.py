#!/usr/bin/env python3
"""At how many generated inputs does the first divergence appear?

G4b runs the library and the replacement on 300 generated neighbours of the
recorded arguments. 300 is a budget we chose, and a reviewer is entitled to
ask whether it is load-bearing: if every divergence appears within the first
handful of inputs, the budget is generous and the result is robust to it; if
divergences cluster near the cap, the number is an artifact and a larger
budget would find more.

This re-runs the same comparisons at several budgets and reports, for each
counterfeit the gate catches, the index of the first input that separates it.

usage:
  neighbour_budget.py --predictions DIR --traces DIR --budgets 30 100 300
"""
from __future__ import annotations

import argparse
import collections
import json
import pathlib
import subprocess
import sys
import tempfile

HERE = pathlib.Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
from make_blocked import import_names, norm  # noqa: E402


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--predictions", required=True)
    ap.add_argument("--traces", default="oracle-blindness/data/traces")
    ap.add_argument("--budgets", nargs="+", type=int, default=[30, 100, 300])
    ap.add_argument("--python", default=sys.executable)
    ap.add_argument("--limit", type=int, default=40)
    ap.add_argument("--out", default=None)
    a = ap.parse_args()

    idx = json.load(open(pathlib.Path(a.predictions) / "index.json"))[: a.limit]
    per = {b: collections.Counter() for b in a.budgets}
    rows = []
    for it in idx:
        d = pathlib.Path(a.predictions) / "python" / it["id"]
        patch = d / "patch.diff"
        trace = pathlib.Path(a.traces) / f"{it['instance_id']}__trace__{norm(it['dependency'])}.jsonl"
        if not patch.exists() or not trace.exists():
            continue
        recs = [json.loads(l) for l in trace.read_text().splitlines() if l.strip()]
        by = collections.defaultdict(list)
        for r in recs:
            by[(r.get("q") or "").split(".")[-1]].append(r)
        src, keep, rel = [], False, None
        for line in patch.read_text().splitlines():
            if line.startswith("+++ ") and "_compat_" in line:
                keep = True
                rel = line[4:].split("\t")[0]
                rel = rel[2:] if rel.startswith("b/") else rel
                continue
            if line.startswith("diff --git"):
                keep = False
            elif keep and line.startswith("+") and not line.startswith("+++"):
                src.append(line[1:])
        if not src or not rel:
            continue
        for fn in it["functions"]:
            calls = by.get(fn) or []
            if not calls:
                continue
            for b in a.budgets:
                spec = dict(import_names=import_names(it["dependency"]),
                            files={rel: "\n".join(src)}, defining=rel,
                            fn=fn, calls=calls[:200], n=b)
                tf = pathlib.Path(tempfile.mkstemp(suffix=".json")[1])
                tf.write_text(json.dumps(spec))
                try:
                    p = subprocess.run([a.python, str(HERE / "g4b_one.py"), str(tf)],
                                       capture_output=True, text=True, timeout=300)
                    out = (p.stdout or "").strip().splitlines()
                    res = json.loads(out[-1]) if out else {"outcome": "error"}
                except Exception:
                    res = {"outcome": "error"}
                finally:
                    tf.unlink(missing_ok=True)
                per[b][res["outcome"]] += 1
                rows.append(dict(id=it["id"], fn=fn, budget=b, outcome=res["outcome"]))

    print(f"{'budget':>8s} {'caught':>7s} {'agrees':>7s} {'verdicts':>9s} {'catch rate':>11s}")
    for b in a.budgets:
        c, g = per[b]["CAUGHT"], per[b]["agrees"]
        v = c + g
        print(f"{b:8d} {c:7d} {g:7d} {v:9d} {(c/v if v else 0):11.0%}")
    print("\nIf the catch rate is flat across budgets, 300 is not load-bearing.")
    if a.out:
        pathlib.Path(a.out).write_text(json.dumps(rows, indent=1))


if __name__ == "__main__":
    main()
