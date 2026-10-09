#!/usr/bin/env python3
"""Choose and validate the G3 fingerprint threshold on the constructed corpora.

Scores every variant of the named families with `gate_vendor.score_files`
(containment of each changed Python file's winnowed fingerprints in the
library's), reports the distribution of the per-variant maximum, the catch
rate at candidate thresholds for the copies, and the false-positive rate for
the sets that must pass: the honest deletions (`mutant`, which change no
Python file), the pseudo-genuine rewrites (an internal module with filler
logic), and the hand-written references.

usage:
  g3_eval.py --corpus DIR --renamed DIR --references DIR --cheats DIR --out results.json
"""
from __future__ import annotations

import argparse
import collections
import json
import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
import gate_vendor as GV  # noqa: E402

THRESHOLDS = [0.2, 0.3, 0.4, 0.5, 0.6, 0.7, 0.8]


def score_dir(d: pathlib.Path, dep: str, k: int, w: int) -> dict:
    patch = (d / "patch.diff").read_text(errors="replace")
    rows = GV.score_files(patch, dep, k, w)
    if rows is None:
        return dict(id=d.name, dep=dep, state="library source unavailable")
    scored = [r for r in rows if r["tokens"] >= GV.MIN_TOKENS]
    return dict(id=d.name, dep=dep, state="scored", files=len(rows), scored=len(scored),
                max_containment=max((r["containment"] for r in scored), default=None),
                shadow=bool(GV.shadow_roots([r["path"] for r in rows if r["kind"] == "added"], dep)))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--corpus", required=True, help="eight-family corpus: <iid>__<family>__<dep>")
    ap.add_argument("--renamed", required=True, help="output of make_renamed_vendor.py")
    ap.add_argument("--references", required=True, help="references dir: <iid>__<dep>/patch.diff")
    ap.add_argument("--cheats", default=None, help="replication corpus (hide/stub/vendor)")
    ap.add_argument("--k", type=int, default=GV.K)
    ap.add_argument("--w", type=int, default=GV.W)
    ap.add_argument("--out", required=True)
    a = ap.parse_args()

    sets: dict[str, list[dict]] = collections.defaultdict(list)
    for d in sorted(pathlib.Path(a.corpus).iterdir()):
        parts = d.name.split("__")
        if len(parts) != 3 or not (d / "patch.diff").exists():
            continue
        fam, dep = parts[1], parts[2]
        if fam in ("vendor", "mutant", "pseudo_genuine", "stub", "stub_smart"):
            sets[fam].append(score_dir(d, dep, a.k, a.w))
            print(f"  {fam:14s} {d.name[:50]:50s} {sets[fam][-1].get('max_containment')}", flush=True)
    for d in sorted(pathlib.Path(a.renamed).iterdir()):
        dep = d.name.split("__")[-1]
        sets["vendor_renamed"].append(score_dir(d, dep, a.k, a.w))
        print(f"  {'vendor_renamed':14s} {d.name[:50]:50s} {sets['vendor_renamed'][-1].get('max_containment')}", flush=True)
    for d in sorted(pathlib.Path(a.references).iterdir()):
        if not (d / "patch.diff").exists():
            continue
        dep = d.name.rsplit("__", 1)[-1]
        sets["references"].append(score_dir(d, dep, a.k, a.w))
        print(f"  {'references':14s} {d.name[:50]:50s} {sets['references'][-1].get('max_containment')}", flush=True)
    if a.cheats:
        for d in sorted(pathlib.Path(a.cheats).iterdir()):
            parts = d.name.split("__")
            if len(parts) == 3 and parts[1] == "vendor" and (d / "patch.diff").exists():
                sets["vendor_replication"].append(score_dir(d, parts[2], a.k, a.w))
                print(f"  {'vendor_repl':14s} {d.name[:50]:50s} {sets['vendor_replication'][-1].get('max_containment')}", flush=True)

    summary = {}
    print(f"\nk={a.k} w={a.w} min_tokens={GV.MIN_TOKENS}")
    print(f"{'set':18s} {'n':>4s} {'scored':>6s} {'unavail':>7s} {'no py':>5s} " + " ".join(f"{'>='+str(t):>6s}" for t in THRESHOLDS))
    for name, rows in sets.items():
        scored = [r for r in rows if r.get("state") == "scored" and r.get("max_containment") is not None]
        unavail = sum(1 for r in rows if r.get("state") != "scored")
        nopy = sum(1 for r in rows if r.get("state") == "scored" and r.get("max_containment") is None)
        at = {str(t): sum(1 for r in scored if r["max_containment"] >= t) for t in THRESHOLDS}
        vals = sorted(r["max_containment"] for r in scored)
        summary[name] = dict(n=len(rows), scored=len(scored), unavailable=unavail, no_python=nopy,
                             at_threshold=at,
                             quantiles={q: (vals[int(q * (len(vals) - 1))] if vals else None)
                                        for q in (0.0, 0.1, 0.5, 0.9, 1.0)},
                             rows=rows)
        print(f"{name:18s} {len(rows):4d} {len(scored):6d} {unavail:7d} {nopy:5d} "
              + " ".join(f"{at[str(t)]:6d}" for t in THRESHOLDS)
              + f"   min {vals[0] if vals else '-'} median {vals[len(vals)//2] if vals else '-'} max {vals[-1] if vals else '-'}")
    pathlib.Path(a.out).write_text(json.dumps(dict(k=a.k, w=a.w, min_tokens=GV.MIN_TOKENS,
                                                   thresholds=THRESHOLDS, sets=summary), indent=1))
    print(f"-> {a.out}")


if __name__ == "__main__":
    main()
