#!/usr/bin/env python3
"""Did the model finish, or did it run out of steps?

A pass rate is only about the model if the model was allowed to finish. An
agent that exhausts its step budget submits whatever the workspace happens to
hold, which is incomplete work rather than a considered answer, and its lower
pass rate then partly measures our budget. This reports, per model, the share
of attempts that ended by declaring the task complete against the share that
hit the ceiling -- so the two can be told apart in the results table instead
of being pooled into one number.

usage:  agent_effort.py pilot/agent_out_* [--max-steps 40]
"""
from __future__ import annotations

import argparse
import json
import pathlib
import statistics


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("dirs", nargs="+")
    ap.add_argument("--max-steps", type=int, default=40)
    a = ap.parse_args()
    print(f"{'model':38s} {'n':>4s} {'finished':>9s} {'at ceiling':>11s} {'median calls':>13s}")
    for d in a.dirs:
        p = pathlib.Path(d) / "python"
        if not p.is_dir():
            continue
        calls, fin, cap = [], 0, 0
        for t in p.rglob("trajs.json"):
            try:
                j = json.loads(t.read_text())
            except Exception:
                continue
            n = sum(1 for e in j if e.get("role") == "assistant")
            calls.append(n)
            if any(e.get("role") == "assistant"
                   and any(c.get("name") == "finish" for c in (e.get("tool_calls") or []))
                   for e in j):
                fin += 1
            elif n >= a.max_steps:
                cap += 1
        if not calls:
            continue
        n = len(calls)
        print(f"{pathlib.Path(d).name[:38]:38s} {n:4d} {fin:5d} {fin/n:4.0%} "
              f"{cap:6d} {cap/n:4.0%} {statistics.median(calls):13.0f}")
    print("\nA model at the ceiling submitted unfinished work: its pass rate is a")
    print("lower bound, and the two columns must be read together.")


if __name__ == "__main__":
    main()
