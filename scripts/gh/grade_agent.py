#!/usr/bin/env python3
"""The agent pilot through the grader: every gate's verdict on every attempt.

Inputs: the attempts' patches (predictions/agent), their CI verdicts and logs
from the harness (results/agent_final, or the downloaded run directory for
the install logs), and the behavioural run (run_g4.py over the same patches).
For each attempt the grader runs with the CI verdict as G2, the install log
for G5, and the recorded traces for G4a. A rejection is classed by what it
rests on: a constraint the prompt never stated (G8: trade; G3: vendor or
shadow), or the tests and behaviour (G2, G4a, G1, G5, G7).

usage:
  grade_agent.py --patches predictions/agent/python --dataset .cache/dataset-dibench-regular.jsonl
                 --ci results/agent_final --logs RESULTS_DIR --g4 agent_g4_*.json --out results/agent_grader.json
"""
from __future__ import annotations

import argparse
import collections
import json
import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
import gate_behaviour  # noqa: E402
import grader  # noqa: E402

UNSTATED = {"G8_closure_not_grown": "trade (closure grew)", "G3_no_vendored_copy": "vendor or shadow module"}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--patches", default="predictions/agent/python")
    ap.add_argument("--dataset", default=".cache/dataset-dibench-regular.jsonl")
    ap.add_argument("--repo-data", default=".cache/repo-data")
    # No default: this pointed at the first pilot's results, so grading a
    # later run without passing --ci silently graded the earlier one and
    # reported its attempt count. The verdicts must be named explicitly.
    ap.add_argument("--ci", required=True,
                    help="directory of harness eval results for THIS run")
    ap.add_argument("--logs", nargs="*", default=[])
    ap.add_argument("--g4", nargs="*", default=[])
    ap.add_argument("--keep", nargs="*", default=[], help="run_g4 --keep dirs, for the traces")
    ap.add_argument("--out", required=True)
    a = ap.parse_args()
    rows = {json.loads(l)["instance_id"]: json.loads(l) for l in open(a.dataset) if l.strip()}
    ci = {}
    cd = pathlib.Path(a.ci)
    for f in list(cd.glob("*.json")) + list(cd.rglob("eval-result.json")):
        try:
            d = json.loads(f.read_text())
        except Exception:
            continue
        if "instance_id" in d:
            ci[d["instance_id"]] = d.get("exec")
    if not ci:
        sys.exit(f"no CI verdicts under {a.ci}: grading needs the harness run first")
    # The patches and the verdicts must describe the same run, or the report
    # is a mix of two. Anything in one and not the other is named, not dropped.
    have = {d.name for d in pathlib.Path(a.patches).iterdir() if d.is_dir()}
    only_ci, only_patch = sorted(set(ci) - have), sorted(have - set(ci))
    if only_ci or only_patch:
        print(f"WARNING: {len(only_ci)} verdicts without a patch here, "
              f"{len(only_patch)} patches without a verdict; grading the "
              f"{len(set(ci) & have)} in both")
        for m in (only_ci + only_patch)[:6]:
            print(f"  unmatched: {m}")
        ci = {k: v for k, v in ci.items() if k in have}
    logs = {}
    for root in a.logs:
        for f in pathlib.Path(root).rglob("eval-result.json"):
            logs[f.parent.name] = "".join(p.read_text(errors="replace")
                                         for p in (f.parent / "eval-workspace").glob("*.log"))
    g4 = {}
    for f in a.g4:
        for r in json.load(open(f)):
            g4[r["id"]] = r

    out = []
    for mid in sorted(ci):
        parts = mid.split("__")
        base, dep = parts[0], parts[-1]
        pf = pathlib.Path(a.patches) / mid / "patch.diff"
        if not pf.exists() or base not in rows:
            out.append(dict(id=mid, ci=ci[mid], status="no patch or dataset row"))
            continue
        patch = pf.read_text(errors="ignore")
        repo = pathlib.Path(a.repo_data) / "python" / base
        r = g4.get(mid) or {}
        ref = cand = None
        sf = None
        for k in a.keep:
            d = pathlib.Path(k) / mid
            if (d / f"{mid}.usage.json").exists():
                ref = gate_behaviour.load(d / "ref.jsonl")
                cand = gate_behaviour.load(d / "cand.jsonl")
                sf = json.loads((d / f"{mid}.usage.json").read_text()).get("site_function")
                break
        g = grader.grade(patch, repo, dep, gold_patch=rows[base]["patch"],
                         tests_passed=(ci[mid] == "pass"), reference=ref, candidate=cand,
                         ci_log=logs.get(mid), site_function=sf)
        if r.get("status") == "ok" and not r.get("reference_tests_passed"):
            g["gates"]["G4a_behaviour"] = dict(status="unverified", evidence={},
                                               reason="the reference suite is not runnable by the local runner")
        elif r.get("status") == "ok" and not r.get("reference_calls"):
            g["gates"]["G4a_behaviour"] = dict(status="unverified", evidence={},
                                               reason="the reference run recorded no call into the library")
        elif not r:
            g["gates"]["G4a_behaviour"] = dict(status="unverified", evidence={},
                                               reason="the behavioural run did not cover this attempt")
        failed = [k for k, v in g["gates"].items() if v["status"] == "fail"]
        unver = [k for k, v in g["gates"].items() if v["status"] == "unverified"]
        unstated = [UNSTATED[k] for k in failed if k in UNSTATED]
        tested = [k for k in failed if k not in UNSTATED]
        out.append(dict(id=mid, base=base, dependency=dep, agent=parts[1], ci=ci[mid],
                        accepted=(not failed and not unver), failed=failed, unverified=unver,
                        rejection_rests_on=("tests or behaviour" if tested else
                                            "unstated constraint only" if unstated else None),
                        unstated=unstated,
                        gates={k: v["status"] for k, v in g["gates"].items()},
                        reasons={k: v["reason"][:160] for k, v in g["gates"].items()}))
    passing = [o for o in out if o.get("ci") == "pass" and "gates" in o]
    print(f"{len(out)} attempts, {len(passing)} pass CI")
    print("| attempt | " + " | ".join(k.split('_')[0] for k in passing[0]["gates"]) + " | rests on |" if passing else "")
    for o in passing:
        print(f"| {o['id'][:60]} | " + " | ".join(o["gates"].values()) + f" | {o['rejection_rests_on'] or ('accepted' if o['accepted'] else 'inconclusive')} |")
    tally = collections.Counter(("accepted" if o["accepted"] else o["rejection_rests_on"] or "inconclusive") for o in passing)
    print(dict(tally))
    pathlib.Path(a.out).write_text(json.dumps(dict(summary=dict(attempts=len(out), ci_pass=len(passing), on_ci_passing=dict(tally)),
                                                   attempts=out), indent=1, default=str))
    print(f"-> {a.out}")


if __name__ == "__main__":
    main()
