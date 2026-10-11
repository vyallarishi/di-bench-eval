#!/usr/bin/env python3
"""Run the generated-input check over every generated pseudo-genuine counterfeit.

G4a compares on the inputs the suite happened to exercise; G4b generates
neighbours of those inputs and runs both the library and the replacement on
them. For this family the replacement is a function of the right shape
returning a fixed wrong value, so a divergence is expected on the first input
that reaches it -- and the number worth reporting is how many of the
counterfeits the gate can *observe*, not just how many it rejects once seen.

Each (counterfeit, function) pair is evaluated in a subprocess, so a hostile
import cannot take the driver down, and the outcome is one of: CAUGHT,
agrees, or a stated reason the gate cannot speak.

usage:
  g4b_pseudo_batch.py --predictions predictions/pseudo --traces DIR
                      [--n 300] [--python PY] [--out out.json]
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
    ap.add_argument("--n", type=int, default=300)
    ap.add_argument("--python", default=sys.executable)
    ap.add_argument("--limit", type=int, default=0)
    ap.add_argument("--out", default=None)
    a = ap.parse_args()

    idx = json.load(open(pathlib.Path(a.predictions) / "index.json"))
    if a.limit:
        idx = idx[: a.limit]
    rows, tally = [], collections.Counter()
    for it in idx:
        d = pathlib.Path(a.predictions) / "python" / it["id"]
        patch = d / "patch.diff"
        if not patch.exists():
            continue
        trace = pathlib.Path(a.traces) / f"{it['instance_id']}__trace__{norm(it['dependency'])}.jsonl"
        if not trace.exists():
            tally["no trace"] += 1
            continue
        recs = [json.loads(l) for l in trace.read_text().splitlines() if l.strip()]
        by = collections.defaultdict(list)
        for r in recs:
            by[(r.get("q") or "").split(".")[-1]].append(r)
        # the generated module, read back out of the patch, with the path it
        # is written to: g4b_one loads it under an alias from a scratch tree,
        # so it needs both the contents and where they live
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
        module = "\n".join(src)
        if not module.strip() or not rel:
            tally["could not read the generated module"] += 1
            continue
        names = import_names(it["dependency"])
        for fn in it["functions"]:
            calls = by.get(fn) or []
            if not calls:
                continue
            spec = dict(import_names=names, files={rel: module}, defining=rel,
                         fn=fn, calls=calls[:200], n=a.n)
            try:
                # via a file: a spec carrying a trace is far longer than any
                # argv limit, and a driver that silently reports "error" for
                # every pair is worse than one that fails loudly
                tf = pathlib.Path(tempfile.mkstemp(suffix=".json")[1])
                tf.write_text(json.dumps(spec))
                p = subprocess.run([a.python, str(HERE / "g4b_one.py"), str(tf)],
                                   capture_output=True, text=True, timeout=300)
                tf.unlink(missing_ok=True)
                out = (p.stdout or "").strip().splitlines()
                if not out:
                    res = dict(outcome="error",
                               reason=(p.stderr or "no output").strip().splitlines()[-1][:120])
                else:
                    res = json.loads(out[-1])
            except Exception as e:
                res = dict(outcome="error", reason=f"{type(e).__name__}: {str(e)[:90]}")
            rows.append(dict(id=it["id"], fn=fn, **res))
            tally[res["outcome"]] += 1
    verdicts = tally["CAUGHT"] + tally["agrees"]
    print(f"{len(rows)} (counterfeit, function) pairs evaluated")
    for k, v in tally.most_common():
        print(f"  {v:4d}  {k}")
    if verdicts:
        print(f"\nG4b verdicts: {tally['CAUGHT']}/{verdicts} caught "
              f"({tally['CAUGHT']/verdicts:.0%})")
    caught_ids = {r["id"] for r in rows if r["outcome"] == "CAUGHT"}
    print(f"distinct counterfeits rejected: {len(caught_ids)} of {len(set(r['id'] for r in rows))} with any verdict")
    if a.out:
        pathlib.Path(a.out).write_text(json.dumps(rows, indent=1))


if __name__ == "__main__":
    main()
