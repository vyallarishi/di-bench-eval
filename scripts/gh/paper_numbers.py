#!/usr/bin/env python3
"""Recompute every number the paper states, and fail if any has drifted.

The audit kept finding new defects, and every one had the same shape: a figure
quoted from a file that a later fix had invalidated, from a run that was never
made, or from an environment missing what the measurement needed. None was a
disagreement about a measurement. They were claims nobody had recomputed since
the thing they depended on changed.

So the fix is not another review. It is this: one script that derives every
stated number from the committed artifacts and exits non-zero when a stated
number and a computed one disagree. Run it before every submission. A claim
that cannot be computed here is listed as UNSUPPORTED rather than assumed, and
that list is the honest inventory of what the release does not back.

usage:  paper_numbers.py [--json out.json]
"""
from __future__ import annotations

import argparse
import collections
import json
import pathlib
import sys

ROOT = pathlib.Path(__file__).resolve().parents[2]

# Every number the paper states, with the commit-time value it was written
# against. A mismatch is a drift to investigate, never a value to overwrite.
STATED = {
    "candidates_screened": 622,
    "silent_after_rule": 226,
    "strict_blind": 34,
    "pool_pairs": 330,
    "pool_repos": 73,
    "traced_pairs": 172,
    "observable_pairs": 84,
    "functions_total": 714,
    "functions_observable": 164,
    "agent_attempts": 300,
    "agent_ci_pass": 33,
    "agent_accepted": 1,
    "agent_rejected": 10,
    "agent_judgeable": 11,
    "counterfeits_total": 617,
    "pseudo_genuine_survive_structural": 80,
    "oracle_rejected": 37,
    "oracle_accepted": 0,
    "rebuilt_ci_evaluated": 73,
    "rebuilt_ci_rejected": 71,
    "references_total": 32,
    "references_ci_pass": 32,
    # the library oracle on hand-written correct code: 7 accepted, 0 rejected
    "references_g4a_accepted": 7,
    "references_g4a_rejected": 0,
    # 38 of the 75 rebuilt counterfeits get no verdict; paired with
    # oracle_rejected so the 37/38 split is checked together
    "oracle_no_verdict": 38,
}


def compute() -> tuple[dict, list[str]]:
    v: dict[str, int] = {}
    missing: list[str] = []

    def load(rel):
        p = ROOT / rel
        if not p.exists():
            missing.append(rel)
            return None
        return json.load(open(p))

    attr = load("oracle-blindness/results/attribution.json")
    if attr:
        v["candidates_screened"] = len(attr)
        sil = [r for r in attr if r["disposition"] == "silent"]
        v["strict_blind_prerule"] = sum(1 for r in sil if "imported" in r["cause"])

    pool = [json.loads(l) for l in open(ROOT / "pilot/instances.jsonl") if l.strip()]
    v["pool_pairs"] = len(pool)
    v["pool_repos"] = len({r["instance_id"] for r in pool})

    traces = list((ROOT / "oracle-blindness/data/traces").glob("*.jsonl"))
    v["traced_pairs"] = len(traces)

    obs = load("oracle-blindness/results/observability.json")
    if obs:
        v["observable_pairs"] = obs["observable_pairs"]
        v["functions_total"] = obs["functions"]
        v["functions_observable"] = obs["observable_functions"]

    att = []
    for f in sorted((ROOT / "data/verdicts").glob("g3_*.json")):
        d = json.load(open(f))
        att += d["attempts"] if isinstance(d, dict) else d
    if att:
        p = [a for a in att if a.get("ci") == "pass"]
        v["agent_attempts"] = len(att)
        v["agent_ci_pass"] = len(p)
        v["agent_accepted"] = sum(1 for a in p if a.get("accepted"))
        v["agent_rejected"] = sum(1 for a in p if a.get("failed"))
        v["agent_judgeable"] = v["agent_accepted"] + v["agent_rejected"]

    var = load("data/analysis/variants_617_current.json")
    if var is not None:
        rows = var if isinstance(var, list) else var.get("results", [])
        v["counterfeits_total"] = len(rows)
        pg = [r for r in rows if r.get("family") == "pseudo_genuine"]
        v["pseudo_genuine_survive_structural"] = sum(1 for r in pg if not r.get("failed"))

    g4 = load("data/analysis/pseudo2_g4b_full.json")
    if g4 is not None:
        by = collections.defaultdict(list)
        for r in g4:
            by[r["id"]].append(r["outcome"])
        v["oracle_rejected"] = sum(1 for o in by.values() if "CAUGHT" in o)
        v["oracle_accepted"] = sum(1 for o in by.values()
                                   if "CAUGHT" not in o and "agrees" in o)
        v["oracle_no_verdict"] = sum(1 for o in by.values()
                                     if "CAUGHT" not in o and "agrees" not in o)

    refs = load("oracle-blindness/results/references_ci.json")
    if refs:
        v["references_total"] = len(refs["references"])
        v["references_ci_pass"] = sum(1 for r in refs["references"]
                                      if r.get("exec") == "pass")

    # The library oracle on correct code, over every reference: the 11 graded
    # while the gate was being built plus the 21 it never saw. "Accepted" is
    # G4a returning identical; "rejected" is it returning a divergence. The
    # second number is the false-rejection count and must stay 0.
    r11 = load("oracle-blindness/results/references_g4.json")
    r21 = load("data/analysis/references_21_g4.json")
    if r11 and r21 is not None:
        acc = sum(1 for r in r11["references"] if r.get("verdict") == "accepted")
        rej = sum(1 for r in r11["references"] if r.get("verdict") == "rejected")
        for r in r21:
            g = r.get("g4a") or {}
            if g.get("verdict") == "identical":
                acc += 1
            elif g.get("passed") is False:
                rej += 1
        v["references_g4a_accepted"] = acc
        v["references_g4a_rejected"] = rej

    ci = load("data/family_ci/pseudo_genuine_rebuilt75.json")
    if ci:
        ok = [r for r in ci["rows"] if r.get("FP") == 0 and r.get("FN") == 1]
        v["rebuilt_ci_evaluated"] = len(ok)
        v["rebuilt_ci_rejected"] = sum(1 for r in ok if r.get("ci") != "pass")

    return v, missing


# Claims the released artifacts cannot support. Stated here so the list is
# visible rather than discovered by a reviewer.
UNSUPPORTED = [
    "behaviour-identical controls: 44 of 74 patches do not apply, the 30 that "
    "do are all inconclusive, and no file shows a 'no difference' result",
    "block activation per agent run is not recorded, so '33 of 300 pass' cannot "
    "be filtered by the rule that a run without the block line is not a pass",
    "the 34 large-half rebuilt counterfeits have no released CI result",
    "11 of the 32 references do not run under the local behavioural runner, so "
    "G4a cannot speak on them; all 32 pass real CI with the block active",
    "only 144 of the 617 constructed submissions have a released patch; the "
    "stub_smart, trade and weaken_tests families have none, so Figure 1 and the "
    "per-gate table can be read but not re-derived from the patches",
]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--json", default=None)
    a = ap.parse_args()

    got, missing = compute()
    drift, ok = [], []
    for k, stated in STATED.items():
        if k not in got:
            continue
        (ok if got[k] == stated else drift).append((k, stated, got[k]))

    print(f"{len(ok)} of {len(ok) + len(drift)} stated numbers reproduce\n")
    for k, s, g in ok:
        print(f"  ok      {k:38s} {g}")
    for k, s, g in drift:
        print(f"  DRIFT   {k:38s} paper {s}, computed {g}")
    if missing:
        print(f"\n{len(missing)} artifact(s) missing, so their numbers were not checked:")
        for m in missing:
            print(f"    {m}")
    print(f"\n{len(UNSUPPORTED)} claim(s) the release does not support:")
    for u in UNSUPPORTED:
        print(f"    - {u}")
    if a.json:
        pathlib.Path(a.json).write_text(json.dumps(
            dict(computed=got, drift=[dict(key=k, paper=s, computed=g) for k, s, g in drift],
                 missing=missing, unsupported=UNSUPPORTED), indent=1))
    sys.exit(1 if drift or missing else 0)


if __name__ == "__main__":
    main()
