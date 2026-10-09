#!/usr/bin/env python3
"""Rebuild run_g4.py result rows from the traces and console output it kept.

A run that hangs on one repository (a jax-based suite whose pytest never
finishes exiting on this machine) used to take every finished instance's
in-memory results with it. The kept directories survive: per instance, the
reference and candidate console output, their traces when any call was
recorded, and the usage map. This rebuilds the rows the runner would have
written, with the test outcome read from pytest's summary line, and the G4a
verdict recomputed with the current comparison.

usage: rebuild_g4_results.py --keep DIR --ids a,b,... --out results.json
"""
from __future__ import annotations

import argparse
import json
import pathlib
import re
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
import gate_behaviour  # noqa: E402

SUMMARY = re.compile(r"(\d+) (passed|failed|error|errors|skipped|xfailed|xpassed|warning|warnings|no tests ran)")


def suite_passed(stdout: str, stderr: str):
    """pytest's verdict from its summary line; None when no summary was printed."""
    lines = [l for l in (stdout or "").strip().splitlines() if l.strip()]
    tail = " ".join(lines[-3:]) if lines else ""
    if "no tests ran" in tail or "error" in tail.lower() and "passed" not in tail:
        return False
    if re.search(r"\b\d+ (failed|error)", tail):
        return False
    if re.search(r"\b\d+ passed", tail):
        return True
    if "Interrupted" in tail or "Traceback" in (stderr or "")[-2000:]:
        return False
    return None


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--keep", required=True)
    ap.add_argument("--ids", required=True)
    ap.add_argument("--out", required=True)
    a = ap.parse_args()
    rows = []
    for mid in [x for x in a.ids.split(",") if x]:
        d = pathlib.Path(a.keep) / mid
        parts = mid.split("__")
        rec = dict(id=mid, base=parts[0], dependency=parts[-1], rebuilt=True)
        # the reference phase runs once per (repository, dependency) and its
        # files sit in the directory of whichever variant ran it first
        rd = None
        for cand_dir in sorted(pathlib.Path(a.keep).glob(f"{parts[0]}__*__{parts[-1]}")):
            if (cand_dir / "ref.stdout").exists():
                rd = cand_dir
                break
        if rd is None:
            rec.update(status="skipped", why="no kept reference run")
            rows.append(rec)
            continue
        ref_out, ref_err = (rd / "ref.stdout").read_text(errors="ignore"), (rd / "ref.stderr").read_text(errors="ignore")
        ref = gate_behaviour.load(rd / "ref.jsonl")
        rp = suite_passed(ref_out, ref_err)
        if not (d / "cand.stdout").exists():
            rec.update(status="skipped", why="no kept candidate run",
                       reference_tests_passed=rp, reference_calls=len(ref))
            rows.append(rec)
            continue
        cand_out, cand_err = (d / "cand.stdout").read_text(errors="ignore"), (d / "cand.stderr").read_text(errors="ignore")
        cand = gate_behaviour.load(d / "cand.jsonl")
        cp = suite_passed(cand_out, cand_err)
        sf = {}
        for u in sorted(rd.glob("*.usage.json")):
            sf = json.loads(u.read_text()).get("site_function", {})
            break
        g = gate_behaviour.compare(ref, cand, sf)
        rec.update(status="ok", reference_runnable_locally=bool(rp), reference_tests_passed=bool(rp),
                   reference_calls=len(ref),
                   reference_library_calls=sum(1 for r in ref if r.get("level") != "usage"),
                   reference_usage_calls=sum(1 for r in ref if r.get("level") == "usage"),
                   candidate_tests_passed=bool(cp), candidate_calls=len(cand),
                   candidate_library_calls=sum(1 for r in cand if r.get("level") != "usage"),
                   candidate_usage_calls=sum(1 for r in cand if r.get("level") == "usage"),
                   ci_verdict="pass" if cp else "fail",
                   g4a={k: v for k, v in g.items() if k not in ("divergences", "missing_calls", "discarded")},
                   g4a_evidence=dict(divergences=g["divergences"][:5], not_observable=g["missing_calls"][:5]))
        rows.append(rec)
    pathlib.Path(a.out).write_text(json.dumps(rows, indent=1, default=str))
    ok = sum(1 for r in rows if r.get("status") == "ok")
    print(f"{len(rows)} rows, {ok} rebuilt -> {a.out}")


if __name__ == "__main__":
    main()
