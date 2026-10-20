#!/usr/bin/env python3
"""Read the probe runs built by probes.py and classify every pair.

The categories were fixed before any result existed (20 Oct 2026), so a result
cannot choose its own bucket. A run whose instrument left no evidence is
"unknown", never folded into a substantive category.

Probe 2, per pool pair, from the three block arms:
  needs-uninstall  rtc passes: with the package still installed and its import
               blocked, nothing fails. The arms keep the gold manifest, while
               v1 deleted the declaration, which usually uninstalls the package,
               so v1 likely detected a non-import use (static files, a plugin,
               a CLI); genuine drift since screening cannot be told apart here.
               (Renamed from "drift" after reading the 16 logs on 20 Oct: 11
               are indirect-tier pairs with no importing file.)
  guard        rtc fails, rtf passes: the detection came from the v1 guard defect
  test-only    rtf fails, rta passes: detected only because test files import it
  runtime      rta fails with the block message: runtime code needs the library
  runtime-other rta fails without the block message (a test fails some other way)
  unknown      a result is missing, or a passing arm never announced the block
Before any of these, the repository's baseline: `gold-fails-today` when the
plain gold run fails now, `injection` when gold passes but the null injection
(rtn) fails. Neither can be read through an injected arm.

Probe 1, per pair:
  rdxw (recorder + probe):
    capture-gap   the probe sees calls from repository source into the library
                  and the recorder recorded none
    invisible-use library-referencing source functions ran, but no call into the
                  library was seen (ufuncs, constants, classes, exceptions)
    test-only     calls into the library come only from test files
    not-reached   the probe ran and no library-referencing source code executed
    agree         the recorder traced calls (expected for the 30 controls)
    unknown       no probe output in the log
  rdxp / rdxg: whether the suite is green with the probe alone and with nothing.

usage:
  probe_report.py RESULTS_DIR [RESULTS_DIR ...] [--manifest pilot/probes_manifest.json] [--out report.json]
"""
from __future__ import annotations

import argparse
import collections
import json
import pathlib

BLOCK_MSG = "(blocked: dependency"
BLOCK_ANNOUNCE = "UnpinBench blocker active"
REC_ANNOUNCE = "UnpinBench recorder active"
TRACE = "UNPINTRACE "
PROBE = "UNPINPROBE "


def load_runs(roots):
    runs = {}
    for root in roots:
        for f in pathlib.Path(root).rglob("eval-result.json"):
            mid = f.parent.name
            try:
                res = json.load(open(f))
            except Exception:
                continue
            log = ""
            for p in sorted((f.parent / "eval-workspace").glob("*.log")):
                log += p.read_text(errors="ignore")
            runs[mid] = {"exec": res.get("exec"), "log": log}
    return runs


def probe_summary(log: str) -> dict | None:
    recs = []
    for line in log.splitlines():
        i = line.find(PROBE)
        if i >= 0:
            try:
                recs.append(json.loads(line[i + len(PROBE):]))
            except Exception:
                pass
    if not recs:
        return None
    s = {"procs": len(recs), "calls_src": 0, "calls_test": 0, "ccalls_src": 0, "ccalls_test": 0,
         "dfn": set(), "dmod": set(), "examples": collections.Counter()}
    for r in recs:
        for k, n in r.get("calls", {}).items():
            s["calls_src" if k.startswith("s:") else "calls_test"] += n
            if k.startswith("s:"):
                s["examples"][k] += n
        for k, n in r.get("ccalls", {}).items():
            s["ccalls_src" if k.startswith("s:") else "ccalls_test"] += n
            if k.startswith("s:"):
                s["examples"][k] += n
        s["dfn"].update(r.get("dfn", {}))
        s["dmod"].update(r.get("dmod", {}))
    s["dfn"], s["dmod"] = len(s["dfn"]), len(s["dmod"])
    s["examples"] = dict(s["examples"].most_common(5))
    return s


def classify_rdxw(run) -> tuple[str, dict]:
    log = run["log"]
    traces = sum(1 for line in log.splitlines() if TRACE in line)
    ps = probe_summary(log)
    info = {"exec": run["exec"], "recorder_active": REC_ANNOUNCE in log, "trace_lines": traces, "probe": ps}
    if traces:
        return "agree", info
    if ps is None:
        return "unknown", info
    if ps["calls_src"] or ps["ccalls_src"]:
        return "capture-gap", info
    if ps["dfn"] or ps["dmod"]:
        return "invisible-use", info
    if ps["calls_test"] or ps["ccalls_test"]:
        return "test-only", info
    return "not-reached", info


def baseline(gold, null) -> str | None:
    """Why a repository cannot be read through any injected arm, if it cannot."""
    if gold is None or null is None:
        return "unknown"
    if gold["exec"] != "pass":
        return "gold-fails-today"
    if null["exec"] != "pass":
        return "injection"
    return None


def classify_rt(arms: dict, base: str | None) -> str:
    if base:
        return base
    if any(a is None for a in arms.values()):
        return "unknown"
    c, f, a = arms["rtc"], arms["rtf"], arms["rta"]
    for arm in (c, f, a):
        if arm["exec"] == "pass" and BLOCK_ANNOUNCE not in arm["log"]:
            return "unknown"
    if c["exec"] == "pass":
        return "needs-uninstall"
    if f["exec"] == "pass":
        return "guard"
    if a["exec"] == "pass":
        return "test-only"
    return "runtime" if BLOCK_MSG in a["log"] else "runtime-other"


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("roots", nargs="+")
    ap.add_argument("--manifest", default="pilot/probes_manifest.json")
    ap.add_argument("--pool", default="pilot/instances.jsonl")
    ap.add_argument("--out", default=None)
    a = ap.parse_args()

    man = json.load(open(a.manifest))["pairs"]
    runs = load_runs(a.roots)
    pool = {(r["instance_id"], r["dependency"]): r for r in map(json.loads, open(a.pool)) if r}
    report = {"missing": sorted(m for m in man if m not in runs), "rt": {}, "rdxw": {}, "rdxp": {}, "rdxg": {}}

    by_pair = collections.defaultdict(dict)
    null_mid = {}
    for mid, m in man.items():
        by_pair[(m["instance_id"], m["dependency"])][m["kind"]] = mid
        if m["kind"] == "rtn":
            null_mid[m["instance_id"]] = mid
    # gold runs come from the existing `gold` set, whose instance id is the repository
    base = {iid: baseline(runs.get(iid), runs.get(nm)) for iid, nm in null_mid.items()}
    report["baseline"] = {iid: b or "ok" for iid, b in base.items()}

    for pair, kinds in sorted(by_pair.items()):
        key = "%s|%s" % pair
        if {"rta", "rtf", "rtc"} <= kinds.keys():
            arms = {k: runs.get(kinds[k]) for k in ("rta", "rtf", "rtc")}
            report["rt"][key] = {"category": classify_rt(arms, base.get(pair[0], "unknown")),
                                 "evidence": pool.get(pair, {}).get("evidence"),
                                 "tier": pool.get(pair, {}).get("tier"),
                                 "exec": {k: (v or {}).get("exec") for k, v in arms.items()}}
        if "rdxw" in kinds and kinds["rdxw"] in runs:
            cat, info = classify_rdxw(runs[kinds["rdxw"]])
            report["rdxw"][key] = {"category": cat, "baseline": base.get(pair[0]) or "ok",
                                   "trace_state": man[kinds["rdxw"]]["trace_state"], **info}
        if "rdxp" in kinds and kinds["rdxp"] in runs:
            r = runs[kinds["rdxp"]]
            report["rdxp"][key] = {"exec": r["exec"], "baseline": base.get(pair[0]) or "ok",
                                   "trace_state": man[kinds["rdxp"]]["trace_state"],
                                   "probe": probe_summary(r["log"])}
        if "rdxg" in kinds and kinds["rdxg"] in runs:
            report["rdxg"][pair[0]] = {"exec": runs[kinds["rdxg"]]["exec"]}

    print(f"probe runs found {len(man) - len(report['missing'])} of {len(man)}; "
          f"gold runs found {sum(1 for i in null_mid if i in runs)} of {len(null_mid)}")
    print("repository baseline (73):", dict(collections.Counter(report["baseline"].values())))
    print("\nprobe 2 (330 pairs):", dict(collections.Counter(v["category"] for v in report["rt"].values())))
    print("  by v1 evidence kind:")
    for (ev, cat), n in sorted(collections.Counter((v["evidence"], v["category"])
                                                    for v in report["rt"].values()).items()):
        print(f"    {ev} / {cat}: {n}")
    for state in ("loaded, no call", "traced"):
        cnt = collections.Counter((v["baseline"], v["category"]) for v in report["rdxw"].values()
                                  if v["trace_state"] == state)
        print(f"\nprobe 1, recorder + probe, v1 state '{state}':", dict(cnt))
    print("\nprobe 1, probe only:", dict(collections.Counter((v["baseline"], v["trace_state"], v["exec"])
                                                           for v in report["rdxp"].values())))
    print("probe 1, gold only (per repository):", dict(collections.Counter(v["exec"] for v in report["rdxg"].values())))
    if a.out:
        json.dump(report, open(a.out, "w"), indent=1, default=str)


if __name__ == "__main__":
    main()
