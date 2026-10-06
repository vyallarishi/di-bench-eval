#!/usr/bin/env python3
"""G4b: differential testing of the replacement against the removed library.

G4a compares behaviour on the inputs the test suite happened to exercise. That
is necessary but not sufficient: a replacement can be wrong only off that set,
and the `pseudo_genuine` cheat family is built to be exactly that -- filler
logic that satisfies the assertions it was shown and nothing more. 80 of 80 of
them survive every structural gate.

This closes it by generating *new* inputs and running both implementations on
them. The approach is Random testing with Ground Truth (RGT), after
Shamshiri et al. and Ye, Martinez & Monperrus (EMSE 2021), who assess repair
patches by generating tests from the human-written patch and reporting a 2.3%
false-positive rate for the method.

We are better placed than they are, and the difference is the point of the
paper. RGT needs a test generator because its ground truth is a static patch;
ours is a **running library**. We do not have to synthesise an oracle or guess
at intent -- we call the real thing. A divergence is therefore direct evidence,
not an inference from a generated assertion.

Inputs come from two sources, both seeded by the recorded trace:

  mutations of the recorded arguments, so the distribution is the project's own
  rather than arbitrary (the trace says `wcswidth("b")`, so neighbours of "b"
  are what the repository actually passes);
  type-directed generation from the recorded argument types, for breadth.

A divergence is reported with the input that produced it, so every claim is
reproducible by hand. Where the library and the replacement agree on every
generated input, the gate says `agrees` -- which is evidence of equivalence on
the sampled space, not proof of it, and is reported as such.

usage:
  gate_differential.py --trace ref.jsonl --reference-module M --candidate-module N
                       [--n 500] [--seed 0] [--json out.json]
or as a library: compare_callables(ref_fn, cand_fn, recorded_calls, n=500)
"""
from __future__ import annotations

import argparse
import json
import pathlib
import random
import string
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
from record_usage import values_equal  # noqa: E402

PRINTABLE = string.ascii_letters + string.digits + " -_,.!?'\"/\\&%#@()[]{}:;\t\n"


def _summary_to_value(s: dict):
    """Best-effort reconstruction of a recorded argument summary."""
    if not isinstance(s, dict):
        return s
    t = s.get("t")
    if t in ("str",):
        return s.get("v", "")
    if t == "bytes":
        return (s.get("v") or "").encode("utf-8", "replace")
    if t == "int":
        return s.get("v", 0)
    if t == "float":
        try:
            return float(s.get("v", "0.0"))
        except (TypeError, ValueError):
            return 0.0
    if t in ("bool", "NoneType"):
        return s.get("v")
    if t in ("list", "tuple", "set", "frozenset"):
        items = [_summary_to_value(i) for i in (s.get("items") or [])]
        return {"list": list, "tuple": tuple, "set": set, "frozenset": frozenset}[t](items)
    if t == "dict":
        return {k: _summary_to_value(v) for k, v in (s.get("items") or [])}
    return None            # opaque object: cannot be reconstructed


def mutate(value, rnd: random.Random):
    """A neighbour of a recorded value, of the same type."""
    if isinstance(value, str):
        if not value:
            return rnd.choice(PRINTABLE)
        s = list(value)
        for _ in range(rnd.randint(1, max(1, len(s) // 3))):
            op = rnd.choice(("ins", "del", "sub", "dup", "case"))
            i = rnd.randrange(len(s)) if s else 0
            if op == "ins" or not s:
                s.insert(rnd.randrange(len(s) + 1), rnd.choice(PRINTABLE))
            elif op == "del":
                s.pop(i)
            elif op == "sub":
                s[i] = rnd.choice(PRINTABLE)
            elif op == "dup":
                s.insert(i, s[i])
            else:
                s[i] = s[i].swapcase()
        return "".join(s)
    if isinstance(value, bool):
        return not value if rnd.random() < 0.5 else value
    if isinstance(value, int):
        return rnd.choice([value + rnd.randint(-5, 5), -value, 0, 1, -1,
                           2 ** rnd.randint(0, 40)])
    if isinstance(value, float):
        return rnd.choice([value * rnd.uniform(-2, 2), 0.0, -0.0,
                           float("inf"), float("nan"), value + 1e-9])
    if isinstance(value, bytes):
        m = mutate(value.decode("utf-8", "replace"), rnd)
        return m.encode("utf-8", "replace")
    if isinstance(value, (list, tuple)):
        items = list(value)
        if items and rnd.random() < 0.5:
            i = rnd.randrange(len(items))
            items[i] = mutate(items[i], rnd)
        elif items:
            items.pop(rnd.randrange(len(items)))
        return type(value)(items)
    if isinstance(value, dict):
        d = dict(value)
        if d and rnd.random() < 0.5:
            k = rnd.choice(list(d))
            d[k] = mutate(d[k], rnd)
        return d
    return value


EDGE_CASES = {
    str: ["", " ", "\n", "\t", "a" * 500, "é", "🙂", "a\x00b", "  leading",
          "trailing  ", "Hello, World!", "<&>\"'", "../../etc/passwd"],
    int: [0, 1, -1, 2 ** 31, -(2 ** 31), 2 ** 63],
    float: [0.0, -0.0, 1e-300, 1e300, float("inf"), float("-inf"), float("nan")],
    bytes: [b"", b"\x00", b"\xff\xfe", b"a" * 500],
}


def inputs_for(recorded: list[dict], rnd: random.Random, n: int) -> list[tuple]:
    """Argument tuples to try, seeded by what the repository actually passed."""
    seeds = []
    for rec in recorded:
        args = [_summary_to_value(a) for a in (rec.get("args") or [])]
        if any(a is None and (s or {}).get("t") not in ("NoneType",)
               for a, s in zip(args, rec.get("args") or [])):
            continue              # an argument we cannot reconstruct
        seeds.append(tuple(args))
    if not seeds:
        return []
    out = list(dict.fromkeys(seeds))          # the recorded calls themselves
    # edge cases, substituted position by position
    for base in seeds[:4]:
        for i, v in enumerate(base):
            for ec in EDGE_CASES.get(type(v), []):
                t = list(base)
                t[i] = ec
                out.append(tuple(t))
    while len(out) < n:
        base = rnd.choice(seeds)
        out.append(tuple(mutate(v, rnd) for v in base))
    return out[:n]


def _call(fn, args):
    try:
        return ("ret", fn(*args))
    except BaseException as e:            # noqa: BLE001 - a raise is an outcome
        return ("raised", type(e).__name__)


def _comparable(outcome):
    kind, val = outcome
    if kind == "raised":
        return ("raised", val)
    try:
        if isinstance(val, (str, bytes, int, float, bool, type(None))):
            return ("ret", val)
        return ("ret", repr(val)[:300])
    except Exception:
        return ("ret", "<unreprable>")


def compare_callables(ref_fn, cand_fn, recorded: list[dict],
                      n: int = 500, seed: int = 0) -> dict:
    """Run both on inputs derived from `recorded`; report divergences."""
    rnd = random.Random(seed)
    cases = inputs_for(recorded, rnd, n)
    if not cases:
        return dict(**{"pass": None},
                    reason="no recorded argument could be reconstructed, so no input "
                           "could be derived; the gate cannot speak",
                    evidence=dict(tried=0))
    divergences = []
    agreed = 0
    for args in cases:
        a, b = _comparable(_call(ref_fn, args)), _comparable(_call(cand_fn, args))
        if a[0] == b[0] and (a[0] == "raised" and a[1] == b[1]
                             or a[0] == "ret" and _eq(a[1], b[1])):
            agreed += 1
        else:
            divergences.append(dict(args=[repr(x)[:80] for x in args],
                                    library=repr(a[1])[:120],
                                    candidate=repr(b[1])[:120]))
    ok = not divergences
    if ok:
        reason = (f"agrees with the library on all {len(cases)} generated inputs "
                  "(evidence of equivalence on the sampled space, not proof)")
    else:
        d = divergences[0]
        reason = (f"{len(divergences)} of {len(cases)} generated inputs diverge, "
                  f"first at args={d['args']}: library {d['library']} vs "
                  f"candidate {d['candidate']}")
    return dict(**{"pass": ok}, reason=reason,
                evidence=dict(tried=len(cases), agreed=agreed,
                              divergent=len(divergences),
                              divergences=divergences[:10]))


def _eq(a, b) -> bool:
    if isinstance(a, float) and isinstance(b, float):
        if a != a and b != b:
            return True
        if a == b:
            return True
        return abs(a - b) <= 1e-9 * max(abs(a), abs(b), 1.0)
    return a == b


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--trace", required=True, help="reference trace jsonl")
    ap.add_argument("--call", required=True, help="qualified name to compare")
    ap.add_argument("--reference-module", required=True)
    ap.add_argument("--candidate-module", required=True)
    ap.add_argument("--n", type=int, default=500)
    ap.add_argument("--seed", type=int, default=0)
    ap.add_argument("--json", default=None)
    a = ap.parse_args()

    import importlib
    recorded = [json.loads(l) for l in open(a.trace) if l.strip()
                and json.loads(l).get("q") == a.call]
    fname = a.call.split(".")[-1]
    ref = getattr(importlib.import_module(a.reference_module), fname)
    cand = getattr(importlib.import_module(a.candidate_module), fname)
    res = compare_callables(ref, cand, recorded, a.n, a.seed)
    print(("PASS " if res["pass"] else "FAIL ") + res["reason"])
    for d in res["evidence"].get("divergences", [])[:5]:
        print(f"  args={d['args']}  library={d['library']}  candidate={d['candidate']}")
    if a.json:
        pathlib.Path(a.json).write_text(json.dumps(res, indent=1, default=str))
    sys.exit(0 if res["pass"] else 1)


if __name__ == "__main__":
    main()
