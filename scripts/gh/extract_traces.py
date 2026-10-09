#!/usr/bin/env python3
"""Pull reference traces out of harness CI logs.

The trace prediction set (`make_traces.py`) makes the recorder write each call
as a `UNPINTRACE <json>` line on the CI console, because the console log is
the only channel the harness brings back from the container. This collects
those lines per instance into `<instance>__trace__<dep>.jsonl`, and reports
the three outcomes separately: recorder never loaded (no activation line),
loaded but recorded nothing (the suite never calls the library), and traced.

usage:  extract_traces.py RESULTS_DIR [RESULTS_DIR ...] --out data/traces
"""
from __future__ import annotations

import argparse
import collections
import json
import pathlib

MARKER = "UNPINTRACE "
ACTIVE = "UnpinBench recorder active"


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("results", nargs="+")
    ap.add_argument("--out", required=True)
    ap.add_argument("--states", default=None,
                    help="write the per-pair outcome ('<repo>|<dep>' -> state) here")
    ap.add_argument("--clean", action="store_true",
                    help="delete traces already in --out before extracting")
    a = ap.parse_args()
    out = pathlib.Path(a.out)
    out.mkdir(parents=True, exist_ok=True)
    if a.clean:
        for old in out.glob("*.jsonl"):
            old.unlink()

    tally = collections.Counter()
    calls = collections.Counter()
    states = {}
    for root in a.results:
        for res in pathlib.Path(root).rglob("eval-result.json"):
            iid = res.parent.name
            try:
                ci = json.loads(res.read_text()).get("exec")
            except Exception:
                ci = None
            lines, active = [], False
            for log in (res.parent / "eval-workspace").glob("*.log"):
                for line in log.read_text(errors="ignore").splitlines():
                    if ACTIVE in line:
                        active = True
                    i = line.find(MARKER)
                    if i >= 0:
                        try:
                            json.loads(line[i + len(MARKER):])
                        except json.JSONDecodeError:
                            tally["malformed line"] += 1
                            continue
                        lines.append(line[i + len(MARKER):])
            if lines:
                (out / f"{iid}.jsonl").write_text("\n".join(lines) + "\n")
                tally["traced"] += 1
                calls[iid] = len(lines)
                state = "traced"
            elif active:
                tally["recorder loaded, no call recorded"] += 1
                state = "loaded, no call"
            else:
                tally["recorder never loaded"] += 1
                state = "never loaded"
            if ci != "pass":
                tally["CI not green under the recorder"] += 1
                # a trace from a red run is kept, but the pair is reported as
                # not green: its suite did not run to completion under the recorder
                state = "not green"
            parts = iid.split("__")
            key = f"{parts[0]}|{parts[-1]}" if len(parts) >= 3 else iid
            states[key] = state
    if a.states:
        pathlib.Path(a.states).write_text(json.dumps(dict(sorted(states.items())), indent=0))

    n = tally["traced"] + tally["recorder loaded, no call recorded"] + tally["recorder never loaded"]
    print(f"{n} instances")
    for k in ("traced", "recorder loaded, no call recorded", "recorder never loaded",
              "CI not green under the recorder", "malformed line"):
        if tally[k]:
            print(f"  {tally[k]:4d}  {k}")
    print(f"  {sum(calls.values())} recorded calls; largest "
          f"{max(calls, key=calls.get) if calls else '-'} at {max(calls.values()) if calls else 0}")


if __name__ == "__main__":
    main()
