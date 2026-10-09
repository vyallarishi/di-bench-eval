#!/usr/bin/env python3
"""Turn gate results over a candidate corpus into the paper's tables.

Reports, per cheat family and overall:

  CI alone          how many candidates the test suite accepts
  each gate         how many of those CI-accepted candidates it rejects
  the composition   how many survive every gate
  coverage          how many candidates each gate could not speak about

The last column is the one most easily fudged and the one a reviewer will look
for. A gate that abstains on half the corpus and catches everything else has
not caught half the corpus, and the table must not let that read as success.

Detection is only half a claim. The complement -- how often the gates reject an
honest removal -- needs reference solutions, and is reported from
`--references DIR` when any exist. With none, the script says so rather than
printing a detection rate as if it stood alone.

usage:
  report_gates.py --g4 g4_results.json --patches DIR --dataset D --repo-data R
                  [--references DIR] [--out report.md]
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

GATES = ["G1_declaration_gone", "G3_no_vendored_copy", "G4a_behaviour",
         "G5_no_phantom", "G7_tests_untouched", "G8_closure_not_grown"]


def family(mid: str) -> str:
    parts = mid.split("__")
    return parts[1] if len(parts) >= 3 else "unknown"


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--g4", required=True, help="run_g4.py output")
    ap.add_argument("--patches", required=True)
    ap.add_argument("--dataset", required=True)
    ap.add_argument("--repo-data", default=".cache/repo-data")
    ap.add_argument("--references", default=None)
    ap.add_argument("--out", default=None)
    a = ap.parse_args()

    rows = {json.loads(l)["instance_id"]: json.loads(l)
            for l in open(a.dataset) if l.strip()}
    g4 = {r["id"]: r for r in json.load(open(a.g4))}

    records = []
    for mid, r in sorted(g4.items()):
        if r.get("status") != "ok":
            records.append(dict(id=mid, family=family(mid), state=r.get("status"),
                                why=r.get("why", "")))
            continue
        parts = mid.split("__")
        base, dep = parts[0], parts[-1]
        patch = (pathlib.Path(a.patches) / mid / "patch.diff").read_text(errors="ignore")
        repo = pathlib.Path(a.repo_data) / "python" / base
        ev = r.get("g4a_evidence") or {}
        g = grader.grade(patch, repo, dep,
                         gold_patch=rows.get(base, {}).get("patch"),
                         tests_passed=r.get("candidate_tests_passed"))
        # substitute the measured G4a verdict, which run_g4 computed from traces
        g4a = r.get("g4a") or {}
        if r.get("reference_calls"):
            passed = g4a.get("passed")
            g["gates"]["G4a_behaviour"] = dict(
                status="pass" if passed else ("unverified" if passed is None else "fail"),
                reason=f"G4a verdict {g4a.get('verdict')}: {g4a.get('reason', '')}", evidence=g4a)
            g["failed"] = [k for k, v in g["gates"].items() if v["status"] == "fail"]
            g["unverified"] = [k for k, v in g["gates"].items() if v["status"] == "unverified"]
            g["accepted"] = not g["failed"] and not g["unverified"]
        records.append(dict(
            id=mid, family=family(mid), state="graded",
            ci_pass=bool(r.get("candidate_tests_passed")),
            gold_ok=bool(r.get("reference_tests_passed")),
            ref_calls=r.get("reference_calls") or 0,
            gates={k: v["status"] for k, v in g["gates"].items()},
            accepted=g["accepted"], failed=g["failed"], unverified=g["unverified"]))

    graded = [r for r in records if r["state"] == "graded"]
    gradeable = [r for r in graded if r["gold_ok"]]
    ci_pass = [r for r in gradeable if r["ci_pass"]]

    out = []
    w = out.append
    w("## The grader over a constructed-cheat corpus\n")
    w(f"- candidates: **{len(records)}**")
    w(f"- gold baseline passes, so the instance is gradeable: **{len(gradeable)}**")
    w(f"- of those, accepted by the test suite alone (G2): **{len(ci_pass)}**")
    w(f"- of those CI-accepted, rejected by at least one other gate: "
      f"**{sum(1 for r in ci_pass if r['failed'] and r['failed'] != ['G2_tests_pass'])}**\n")

    w("### Per gate, over the CI-accepted candidates\n")
    w("| Gate | rejects | passes | cannot speak |")
    w("|---|---|---|---|")
    for gname in GATES:
        rej = sum(1 for r in ci_pass if r["gates"].get(gname) == "fail")
        pas = sum(1 for r in ci_pass if r["gates"].get(gname) == "pass")
        unv = sum(1 for r in ci_pass if r["gates"].get(gname) == "unverified")
        w(f"| {gname} | {rej} | {pas} | {unv} |")
    w("")

    w("### Per cheat family\n")
    w("| Family | gradeable | CI accepts | grader accepts | caught by |")
    w("|---|---|---|---|---|")
    for fam in sorted({r["family"] for r in gradeable}):
        fr = [r for r in gradeable if r["family"] == fam]
        fci = [r for r in fr if r["ci_pass"]]
        acc = [r for r in fci if r["accepted"]]
        by = collections.Counter(g for r in fci for g in r["failed"]
                                 if g != "G2_tests_pass")
        top = ", ".join(f"{k.split('_')[0]} ({v})" for k, v in by.most_common(3))
        w(f"| {fam} | {len(fr)} | {len(fci)} | {len(acc)} | {top or '-'} |")
    w("")

    w("### Coverage of the behavioural gate\n")
    nb = [r for r in graded if not r["gold_ok"]]
    nt = [r for r in gradeable if not r["ref_calls"]]
    yt = [r for r in gradeable if r["ref_calls"]]
    w(f"- gold baseline fails, instance not gradeable: **{len(nb)}**")
    w(f"- baseline passes but the suite never calls the library, so G4 is silent: "
      f"**{len(nt)}**")
    w(f"- a reference trace exists, so G4 can speak: **{len(yt)}**")
    if yt:
        tot = sum(r["ref_calls"] for r in yt)
        w(f"- recorded calls across those: **{tot}** "
          f"(median {sorted(r['ref_calls'] for r in yt)[len(yt)//2]})")
    w("")

    w("### False rejection (the other half of the claim)\n")
    refs = pathlib.Path(a.references) if a.references else None
    have = sorted(p.name for p in refs.iterdir() if p.is_dir()) if refs and refs.is_dir() else []
    if not have:
        w("**Not measured.** Detection without false rejection is half a result: a gate "
          "that rejects everything would score perfectly in the tables above. This needs "
          "reference removals -- genuine solutions that the grader must accept -- and "
          "none are available yet, so no detection figure here should be read as a "
          "statement about the grader's accuracy.")
    else:
        w(f"{len(have)} reference removal(s) available: {', '.join(have[:10])}")
    w("")

    skipped = [r for r in records if r["state"] != "graded"]
    if skipped:
        w("### Candidates not graded\n")
        for why, n in collections.Counter(r["why"] for r in skipped).most_common():
            w(f"- {n}: {why}")
        w("")

    text = "\n".join(out)
    print(text)
    if a.out:
        pathlib.Path(a.out).write_text(text)
        print(f"-> {a.out}", file=sys.stderr)


if __name__ == "__main__":
    main()
