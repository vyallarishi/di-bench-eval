#!/usr/bin/env python3
"""Does the oracle give the same verdict twice on the same patch?

The benchmark's central number is a count of CI verdicts, and every verdict
came from one run of a replayed workflow on a shared runner. A verdict that
flips between runs -- a test that depends on timing, network, or ordering --
would be counted as a finding about the dependency when it is a finding about
the suite. SWE-bench's audit found such flakiness in a measurable share of its
instances; it must be measured here, not assumed away.

The measurement is the simplest possible: run the identical prediction set
twice and count the instances whose verdict differs. "Identical" is checked,
not assumed -- the two prediction sets are compared byte for byte and only
pairs whose patches match are counted, so a difference in the injected file
between two generations of the screener cannot masquerade as a flip.

usage:
  flakiness.py --first RESULTS_A --second RESULTS_B
               [--patches-first PRED_A --patches-second PRED_B] [--out report.json]

RESULTS_* are directories of eval-result.json files (nested, as the harness
produces them). PRED_* are prediction-set directories of <id>/patch.diff.
"""
from __future__ import annotations

import argparse
import collections
import hashlib
import json
import pathlib


def verdicts(d: pathlib.Path) -> dict[str, bool]:
    """instance id -> CI passed, from every eval-result.json under d."""
    out = {}
    for f in d.rglob("eval-result.json"):
        try:
            r = json.loads(f.read_text())
        except Exception:
            continue
        iid = r.get("instance_id") or f.parent.name
        ok = r.get("exec") if "exec" in r else r.get("passed", r.get("success"))
        if isinstance(ok, dict):
            ok = ok.get("passed", ok.get("success"))
        if isinstance(ok, str):            # the harness writes "pass" / "fail"
            ok = ok.lower() in ("pass", "passed", "success", "true")
        if ok is not None:
            out[iid] = bool(ok)
    return out


def base_id(iid: str) -> str:
    """repeat sets name an instance <repo>__repeat__<dep>; the screening set
    <repo>__all__<dep> (or similar). The identity is (repo, dep)."""
    parts = iid.split("__")
    return f"{parts[0]}__{parts[-1]}" if len(parts) >= 3 else iid


def patch_hashes(d: pathlib.Path | None) -> dict[str, str]:
    if d is None:
        return {}
    out = {}
    for p in d.rglob("patch.diff"):
        out[base_id(p.parent.name)] = hashlib.sha1(p.read_bytes()).hexdigest()
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--first", required=True)
    ap.add_argument("--second", required=True)
    ap.add_argument("--patches-first", default=None)
    ap.add_argument("--patches-second", default=None)
    ap.add_argument("--out", default=None)
    a = ap.parse_args()

    va = {base_id(k): v for k, v in verdicts(pathlib.Path(a.first)).items()}
    vb = {base_id(k): v for k, v in verdicts(pathlib.Path(a.second)).items()}
    ha = patch_hashes(pathlib.Path(a.patches_first) if a.patches_first else None)
    hb = patch_hashes(pathlib.Path(a.patches_second) if a.patches_second else None)

    common = sorted(set(va) & set(vb))
    identical = [k for k in common if not (ha and hb) or ha.get(k) == hb.get(k)]
    differing_patch = [k for k in common if ha and hb and ha.get(k) != hb.get(k)]
    flips = [k for k in identical if va[k] != vb[k]]
    tally = collections.Counter((va[k], vb[k]) for k in identical)

    print(f"instances in both runs: {len(common)}")
    if ha and hb:
        print(f"  with byte-identical patches: {len(identical)}  "
              f"(excluded, patch differs: {len(differing_patch)})")
    print(f"  pass/pass {tally[(True, True)]}   fail/fail {tally[(False, False)]}   "
          f"pass->fail {tally[(True, False)]}   fail->pass {tally[(False, True)]}")
    print(f"\nFLIPS: {len(flips)}/{len(identical)} = "
          f"{(len(flips) / len(identical)) if identical else 0:.1%}")
    for k in flips:
        print(f"  {k}: {'pass' if va[k] else 'fail'} -> {'pass' if vb[k] else 'fail'}")
    if a.out:
        pathlib.Path(a.out).write_text(json.dumps(dict(
            compared=len(identical), flips=flips, excluded_patch_differs=differing_patch,
            tally={f"{x}->{y}": n for (x, y), n in tally.items()}), indent=1))


if __name__ == "__main__":
    main()
