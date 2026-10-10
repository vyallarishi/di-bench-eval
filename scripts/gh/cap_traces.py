#!/usr/bin/env python3
"""Cap a recorded trace at N records per call site, for the committed copy.

The traces are published with the benchmark, and GitHub refuses a file over
100 MB. One trace exceeds it: speakeasy's `pefile` pair records 21,387 calls
whose argument summaries average 6.8 KB, 138 MB in all. Dropping the pair
would lose a traced instance; truncating the file blindly would lose whole
call sites, because the records of a site are contiguous in the log.

So the cap is applied PER SITE, keeping the first N records of each: every
call site and every library function the suite reached survives, and G4a --
which pairs the i-th call at a site with the i-th -- compares the kept prefix
and reports the rest as not observable rather than as a divergence. What is
lost is the tail of the four hottest sites, and the counts are written into
the file's own header record so the published trace states its own cap.

usage: cap_traces.py --traces DIR [--max-bytes 90000000] [--per-site 400]
"""
from __future__ import annotations

import argparse
import collections
import json
import pathlib


def cap_file(path: pathlib.Path, per_site: int) -> dict:
    recs = []
    for line in path.read_text(errors="ignore").splitlines():
        if not line.strip():
            continue
        try:
            recs.append(json.loads(line))
        except json.JSONDecodeError:
            continue
    seen: collections.Counter = collections.Counter()
    kept, dropped = [], 0
    for r in recs:
        key = (r.get("site"), r.get("level"))
        if seen[key] < per_site:
            seen[key] += 1
            kept.append(r)
        else:
            dropped += 1
    header = {"unpinbench_capped": True, "per_site": per_site,
              "records_recorded": len(recs), "records_kept": len(kept),
              "records_dropped": dropped,
              "sites": len({r.get("site") for r in recs}),
              "sites_capped": sum(1 for k, v in seen.items() if v >= per_site)}
    path.write_text("\n".join([json.dumps(header)] + [json.dumps(r) for r in kept]) + "\n")
    return header


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--traces", default="oracle-blindness/data/traces")
    ap.add_argument("--max-bytes", type=int, default=90_000_000)
    ap.add_argument("--per-site", type=int, default=400)
    a = ap.parse_args()
    for f in sorted(pathlib.Path(a.traces).glob("*.jsonl")):
        if f.stat().st_size <= a.max_bytes:
            continue
        before = f.stat().st_size
        h = cap_file(f, a.per_site)
        print(f"{f.name}: {before/1e6:.0f} MB -> {f.stat().st_size/1e6:.1f} MB; "
              f"kept {h['records_kept']} of {h['records_recorded']} records across "
              f"{h['sites']} sites ({h['sites_capped']} capped)")


if __name__ == "__main__":
    main()
