#!/usr/bin/env python3
"""The behavioural gate over the replication cheat corpus, per kind, with CI verdicts.

Joins the run_g4.py results over predictions/cheats (G4a, local run with the
usage-site recorder) with the harness's CI verdict for each variant
(results/cheats/<id>.json) and, where a reference trace exists, the G4b
outcome over the replacement module (g4b_variants.py style: library and
replacement on inputs derived from the recorded ones). Reports, per kind and
only for CI-passing variants, the G4a verdict and the G4b verdict, and the
coverage (how many variants each gate could speak about).

usage:
  summarize_cheats_g4.py --g4 cheats_g4_*.json --ci-dir results/cheats --out results/g4_cheats.json
"""
from __future__ import annotations

import argparse
import collections
import json
import pathlib

KINDS = ("hide", "stub", "vendor")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--g4", nargs="+", required=True)
    ap.add_argument("--ci-dir", default="oracle-blindness/results/cheats")
    ap.add_argument("--g4b", default=None, help="g4b_variants.py output over the same patches")
    ap.add_argument("--out", required=True)
    a = ap.parse_args()
    rows = {}
    for f in a.g4:
        for r in json.load(open(f)):
            rows[r["id"]] = r
    ci = {}
    for f in pathlib.Path(a.ci_dir).glob("*.json"):
        d = json.loads(f.read_text())
        ci[d["instance_id"]] = d.get("exec")
    g4b = collections.defaultdict(list)
    if a.g4b:
        for r in json.load(open(a.g4b)):
            g4b[r["id"]].append(r)

    out = []
    for mid, exec_ in sorted(ci.items()):
        kind = mid.split("__")[1]
        r = rows.get(mid)
        rec = dict(id=mid, kind=kind, ci=exec_)
        if r is None:
            rec["g4a"] = "not run"
        elif r.get("status") != "ok":
            rec["g4a"] = "not run: " + r.get("why", r.get("status", ""))
        elif not r.get("reference_tests_passed"):
            rec["g4a"] = "reference suite not runnable locally"
            rec["g4a_verdict"] = (r.get("g4a") or {}).get("verdict")
        elif not r.get("reference_calls"):
            rec["g4a"] = "no reference call recorded"
        else:
            g = r["g4a"]
            rec["g4a"] = g["verdict"]
            rec["g4a_decided_at"] = g.get("decided_at")
            rec["g4a_reason"] = g.get("reason", "")[:160]
            rec["reference_calls"] = r.get("reference_calls")
            rec["candidate_calls"] = r.get("candidate_calls")
        b = g4b.get(mid)
        if b:
            outcomes = collections.Counter(x["outcome"] for x in b)
            rec["g4b"] = ("CAUGHT" if outcomes["CAUGHT"] else "agrees" if outcomes["agrees"]
                          else next(iter(outcomes)))
            rec["g4b_functions"] = dict(outcomes)
        out.append(rec)

    print("| kind | variants | CI pass | G4a on CI-passing: identical / divergent / inconclusive / not evaluable | G4b on CI-passing: caught / agrees / cannot speak |")
    print("|---|---|---|---|---|")
    summary = {}
    for kind in KINDS:
        rs = [o for o in out if o["kind"] == kind]
        cp = [o for o in rs if o["ci"] == "pass"]
        va = collections.Counter(o["g4a"] if o["g4a"] in ("identical", "divergent", "unverified") else "not evaluable" for o in cp)
        vb = collections.Counter(o.get("g4b", "cannot speak") for o in cp)
        summary[kind] = dict(variants=len(rs), ci_pass=len(cp),
                             g4a={k: va[k] for k in ("identical", "divergent", "unverified", "not evaluable")},
                             g4b=dict(vb),
                             not_evaluable_why=dict(collections.Counter(o["g4a"] for o in cp if o["g4a"] not in ("identical", "divergent", "unverified"))))
        print(f"| {kind} | {len(rs)} | {len(cp)} | {va['identical']} / {va['divergent']} / {va['unverified']} / {va['not evaluable']} | "
              f"{vb.get('CAUGHT', 0)} / {vb.get('agrees', 0)} / {len(cp) - vb.get('CAUGHT', 0) - vb.get('agrees', 0)} |")
    pathlib.Path(a.out).write_text(json.dumps(dict(summary=summary, variants=out), indent=1))
    print(f"-> {a.out}")


if __name__ == "__main__":
    main()
