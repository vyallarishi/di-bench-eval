#!/usr/bin/env python3
"""Is each generated counterfeit actually wrong on the inputs the tests used?

A counterfeit returns a plausible value of the recorded return type: 0 for an
int, '' for a str, {} for a dict. That value can *collide* with what the
library really returned -- a function that returns 0, or the empty string, on
the arguments the suite happens to pass. A collision makes the counterfeit
correct on those inputs, so a gate that fails to reject it is right, and
counting it as a gate miss would turn a generator artifact into a reported
defect.

This compares each counterfeit's fixed return against the values the recording
shows the library producing, before any gate runs. A counterfeit whose value
matches every recorded return is not a counterfeit on that function and is
excluded from the denominator.

usage:  verify_counterfeit.py --predictions DIR --traces DIR [--out out.json]
"""
from __future__ import annotations

import argparse
import ast
import collections
import json
import pathlib
import re
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
from make_blocked import norm  # noqa: E402

LIT = {"0": 0, "0.0": 0.0, "False": False, "None": None, "''": "", "b''": b"",
       "[]": [], "()": (), "{}": {}, "set()": set(), "frozenset()": frozenset(),
       "bytearray()": bytearray()}


def fake_returns(patch: str) -> dict[str, str]:
    """function -> the literal the counterfeit returns, read from the patch."""
    src, keep = [], False
    for line in patch.splitlines():
        if line.startswith("+++ ") and "_compat_" in line:
            keep = True
            continue
        if line.startswith("diff --git"):
            keep = False
        elif keep and line.startswith("+") and not line.startswith("+++"):
            src.append(line[1:])
    out = {}
    try:
        tree = ast.parse("\n".join(src))
    except SyntaxError:
        return out
    for node in tree.body:
        if isinstance(node, ast.FunctionDef):
            for st in node.body:
                if isinstance(st, ast.Return) and st.value is not None:
                    try:
                        out[node.name] = ast.unparse(st.value)
                    except Exception:
                        pass
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--predictions", required=True)
    ap.add_argument("--traces", default="oracle-blindness/data/traces")
    ap.add_argument("--out", default=None)
    a = ap.parse_args()

    idx = json.load(open(pathlib.Path(a.predictions) / "index.json"))
    rows, tally = [], collections.Counter()
    for it in idx:
        p = pathlib.Path(a.predictions) / "python" / it["id"] / "patch.diff"
        tr = pathlib.Path(a.traces) / f"{it['instance_id']}__trace__{norm(it['dependency'])}.jsonl"
        if not p.exists() or not tr.exists():
            continue
        fakes = fake_returns(p.read_text(errors="replace"))
        by = collections.defaultdict(list)
        for line in tr.read_text().splitlines():
            if not line.strip():
                continue
            r = json.loads(line)
            fn = (r.get("q") or "").split(".")[-1]
            if "ret" in r:
                by[fn].append(r["ret"])
        for fn, lit in fakes.items():
            rets = by.get(fn) or []
            if not rets:
                tally["no recorded return"] += 1
                cls = "no recorded return"
            else:
                types = {(r or {}).get("t") for r in rets if isinstance(r, dict)}
                if types <= {"NoneType"}:
                    cls = "void: library returns None, nothing to counterfeit"
                else:
                    # does the fake literal equal EVERY recorded value?
                    same = 0
                    for r in rets:
                        if not isinstance(r, dict):
                            continue
                        v = r.get("v", None)
                        if lit in LIT and v == LIT[lit]:
                            same += 1
                        elif lit == "{}" and r.get("t") == "dict" and not r.get("items"):
                            same += 1
                        elif lit == "[]" and r.get("t") == "list" and not r.get("items"):
                            same += 1
                    cls = ("collision: the fake value matches every recorded return"
                           if same == len(rets) else "genuinely wrong")
                tally[cls] += 1
            rows.append(dict(id=it["id"], fn=fn, literal=lit, cls=cls,
                             recorded=len(rets)))
    print(f"{len(rows)} (counterfeit, function) pairs checked against the recording")
    for k, v in tally.most_common():
        print(f"  {v:4d}  {k}")
    good = tally["genuinely wrong"]
    print(f"\nEvaluable as counterfeits: {good} "
          f"({good/max(sum(tally.values()),1):.0%} of generated functions)")
    if a.out:
        pathlib.Path(a.out).write_text(json.dumps(rows, indent=1))


if __name__ == "__main__":
    main()
