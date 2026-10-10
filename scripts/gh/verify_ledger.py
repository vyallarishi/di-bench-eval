#!/usr/bin/env python3
"""Check every figure the ledger quotes against the result file it names.

The rule of this project is that no number reaches the paper except from a
result file produced by a script here. This asserts the other direction: that
the figures written into `docs/RESULTS_LEDGER.md` and `paper/numbers.tex` are
the ones those files actually contain. It is cheap, it runs offline, and it
catches the failure that costs the most -- a result file regenerated while a
hand-written figure stays behind.

usage: verify_ledger.py [--results DIR]   (exit 1 on any mismatch)
"""
from __future__ import annotations

import argparse
import json
import pathlib
import re
import sys

EXPECTED = {}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--results", default="oracle-blindness/results")
    ap.add_argument("--numbers", default="oracle-blindness/paper/numbers.tex")
    a = ap.parse_args()
    R = pathlib.Path(a.results)
    load = lambda n: json.loads((R / n).read_text())
    def macros(text: str) -> dict:
        """name -> value, counting braces: a value may contain {,} as a digit separator."""
        out = {}
        for m in re.finditer(r"\\newcommand\{\\([A-Za-z]+)\}\{", text):
            i, depth, start = m.end(), 1, m.end()
            while i < len(text) and depth:
                depth += (text[i] == "{") - (text[i] == "}")
                i += 1
            out[m.group(1)] = text[start:i - 1]
        return out

    nums = macros(pathlib.Path(a.numbers).read_text())
    clean = lambda v: v.replace("{,}", "").replace("\\%", "")

    act = load("activation.json")["summary"]
    rob = load("robustness.json")["confirmed"]
    ov = load("oracle_overlap.json")
    ts = load("trace_states.json")
    tf = load("trace_fidelity.json")
    rg = load("references_g4.json")["summary"]["by_class"]
    rc = load("references_ci.json")["summary"]
    g3 = load("g3_fingerprint.json")["result"]["sets"]
    gc = load("g4_cheats.json")["summary"]
    gp = load("g4b_pseudo_genuine.json")["summary"]
    ag = load("agent_grader.json")["summary"]
    excluded = act["status"]["excluded: inconclusive, block not observed"]

    checks = [
        ("nSilent", act["blind"] - excluded),
        ("nSilentAll", act["blind"]),
        ("nExclInconclusive", excluded),
        ("nStrict", act["strict_after"]),
        ("medianRate", round(rob["all"]["median"] * 100, 1)),
        ("nIncidence", rob["all"]["incidence"]),
        ("nReposThree", rob["all"]["repos"]),
        ("dropTenMedian", round(rob["drop_k"]["10"]["median"] * 100, 1)),
        ("nScreenedRule", len(ov)),
        ("nImportSilent", sum(1 for r in ov if not r["import_check_detects"])),
        ("nImportCatchesCIMisses", sum(1 for r in ov if not r["ci_detects"] and r["import_check_detects"])),
        ("nCIcatchesImportMisses", sum(1 for r in ov if r["ci_detects"] and not r["import_check_detects"])),
        ("nTracedPairs", sum(1 for v in ts.values() if v == "traced")),
        ("nRecLoadedNoCall", sum(1 for v in ts.values() if v == "loaded, no call")),
        ("nRecNotObserved", sum(1 for v in ts.values() if v == "never loaded")),
        ("nRecNotGreen", sum(1 for v in ts.values() if v == "not green")),
        ("nTraceCalls", tf["values"]),
        ("fidelityWhole", round(tf["share_decided"] * 100, 1)),
        ("nRefsAccepted", sum(v for k, v in rg.items() if "accepted" in k)),
        ("nRefsInconclusive", sum(v for k, v in rg.items() if "inconclusive" in k)),
        ("nRefsRejected", sum(v for k, v in rg.items() if "rejected" in k)),
        ("nRefsPass", rc["ci_pass"]),
        ("nVendorNamedCaught", g3["vendor"]["at_threshold"]["0.6"]),
        ("nVendorRenamedCaught", g3["vendor_renamed"]["at_threshold"]["0.6"]),
        ("nRefsGThreeFlagged", g3["references"]["at_threshold"]["0.6"]),
        ("nPseudoGThreeFlagged", g3["pseudo_genuine"]["at_threshold"]["0.6"]),
        ("nCheatCIPass", sum(v["ci_pass"] for v in gc.values())),
        ("nStubCIPass", gc["stub"]["ci_pass"]),
        ("nPseudoFunctions", gp["caught_functions"]),
        ("nPseudoEvaluable", gp["caught_variants"]),
        ("nPseudoTraced", gp["on_traced_pair"]),
        ("nAgentPass", ag["ci_pass"]),
        ("nAgentAccepted", ag["on_ci_passing"].get("accepted", 0)),
        ("nAgentInconclusive", ag["on_ci_passing"].get("inconclusive", 0)),
        ("nAgentRejected", ag["on_ci_passing"].get("tests or behaviour", 0)
                           + ag["on_ci_passing"].get("unstated constraint only", 0)),
        ("nAgentUnstated", ag["on_ci_passing"].get("unstated constraint only", 0)),
    ]
    bad = []
    for macro, measured in checks:
        declared = clean(nums.get(macro, "<undefined>"))
        same = declared == clean(str(measured))
        print(f"  {'ok  ' if same else 'FAIL'} \\{macro:24s} numbers.tex={declared:>10s}  measured={measured}")
        if not same:
            bad.append(macro)
    print(f"\n{len(checks)} figures checked, {len(bad)} mismatched" + (": " + ", ".join(bad) if bad else ""))
    sys.exit(1 if bad else 0)


if __name__ == "__main__":
    main()
