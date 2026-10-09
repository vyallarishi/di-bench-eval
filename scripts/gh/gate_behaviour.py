#!/usr/bin/env python3
"""G4a: did the replacement preserve what the library actually did?

The behavioural gate. Phase 0 (`record_usage.py`) ran the repository's tests
with the library present and recorded every call the repository's own code made
into it: qualified name, call site, argument summaries, return value, exception.
That recording is the *reference trace*. After a candidate change removes the
library, the same instrumentation records what the replacement does at the same
call sites, giving the *candidate trace*. This module compares them.

Why this is sound here and nowhere else. Every other repository-change
benchmark has to decide correctness against a specification it does not have:
SWE-bench compares to a human patch that may itself be wrong, migration
benchmarks compare across libraries whose semantics differ by design. In a
removal task the artifact whose behaviour must be preserved was *present and
running*, so its outputs are recordable. The removed library is the oracle.

What a divergence means, stated carefully. A difference in the recorded value
at a call site is evidence the replacement does not do what the library did on
an input the tests actually exercise. It is not proof of incorrectness: the
repository may not care about the part of the value that changed. And a pass is
only as strong as what the summary captures: a value past the cap is compared
by a hash of the whole, an object by its public attributes and length, and
only a bare object with neither is compared by repr alone; `trace_fidelity.py`
reports how much of a trace falls in each class (see `record_usage.values_equal`
for the rules). So this gate reports *divergences with evidence*, and the grade
distinguishes

  identical    every reference call has a matching candidate call, same value
  divergent    a call site returns a different value, or raises differently
  missing      a call site the reference exercised is never reached
  unverified   no reference call was recorded, so the gate cannot speak

`missing` is the stub-catcher. A hollow replacement that satisfies the
assertions typically never performs the work at all, so the sites the library
served simply vanish from the trace.

usage:
  gate_behaviour.py reference.jsonl candidate.jsonl [--json out.json]
or as a library: compare(reference_records, candidate_records) -> dict
"""
from __future__ import annotations

import argparse
import collections
import json
import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
from record_usage import values_equal  # noqa: E402


def _pair_key(rec: dict) -> tuple:
    """Identity of a call for reference-to-candidate pairing.

    Deliberately NOT the qualified name. A removal renames the callee by
    construction -- `slugger.slugify` becomes `app.textutil.slugify` or a local
    helper -- so keying on it rejects every honest replacement along with every
    cheat. What must be stable across the two runs is *where the repository
    asked for the work and with what arguments*: the call site and the
    arguments. The function's own name is the one thing the task changes.

    The last dotted component is kept as a weak hint, because a replacement
    that renames the function but preserves behaviour is still a valid removal
    and we do not want to depend on the name matching; it is recorded in the
    evidence rather than used for pairing.
    """
    import json as _j
    return (rec.get("site"),
            _j.dumps(rec.get("args"), sort_keys=True, default=str),
            _j.dumps(rec.get("kwargs"), sort_keys=True, default=str))


def load(path) -> list[dict]:
    out = []
    p = pathlib.Path(path)
    if not p.exists():
        return out
    for line in p.read_text(errors="ignore").splitlines():
        line = line.strip()
        if not line:
            continue
        try:
            out.append(json.loads(line))
        except json.JSONDecodeError:
            continue
    return out


def _outcome(rec: dict):
    """What the call produced: ('raised', type) or ('ret', summary)."""
    if "raised" in rec:
        return ("raised", rec["raised"])
    return ("ret", rec.get("ret"))


def _same_outcome(a: dict, b: dict) -> bool:
    ka, va = _outcome(a)
    kb, vb = _outcome(b)
    if ka != kb:
        return False
    if ka == "raised":
        return va == vb
    return values_equal(va, vb)


def compare(reference: list[dict], candidate: list[dict]) -> dict:
    """Compare two usage traces call-for-call.

    Calls are paired by (call site, arguments) -- see `_pair_key` -- so a
    replacement is judged on the inputs the library was actually given, without
    requiring it to keep the library's function names.
    Repeated identical calls are matched as multisets, in recorded order, which
    keeps the comparison stable when a suite runs tests in a different order.
    """
    ref_by: dict[tuple, list[dict]] = collections.defaultdict(list)
    for r in reference:
        ref_by[_pair_key(r)].append(r)
    cand_by: dict[tuple, list[dict]] = collections.defaultdict(list)
    for c in candidate:
        cand_by[_pair_key(c)].append(c)

    divergences, missing = [], []
    matched = 0
    for key, refs in ref_by.items():
        cands = cand_by.get(key, [])
        for i, r in enumerate(refs):
            if i >= len(cands):
                missing.append(dict(call=r.get("q"), site=r.get("site"),
                                    args=r.get("args"), kwargs=r.get("kwargs"),
                                    reference=_outcome(r)[1],
                                    why="call site never reached by the candidate"))
                continue
            c = cands[i]
            if _same_outcome(r, c):
                matched += 1
            else:
                divergences.append(dict(call=r.get("q"), candidate_call=c.get("q"),
                                        site=r.get("site"),
                                        args=r.get("args"), kwargs=r.get("kwargs"),
                                        reference=_outcome(r)[1],
                                        candidate=_outcome(c)[1]))
    # calls the candidate makes that the reference never did: not a failure on
    # its own (a replacement may call its own helpers), recorded for context
    extra = sum(max(0, len(v) - len(ref_by.get(k, []))) for k, v in cand_by.items())

    if not reference:
        verdict = "unverified"
    elif divergences:
        verdict = "divergent"
    elif missing:
        verdict = "missing"
    else:
        verdict = "identical"

    sites = {r.get("site") for r in reference}
    return dict(
        verdict=verdict,
        passed=verdict == "identical",
        reference_calls=len(reference),
        candidate_calls=len(candidate),
        reference_sites=len(sites),
        matched=matched,
        divergent=len(divergences),
        missing=len(missing),
        extra_candidate_calls=extra,
        divergences=divergences[:20],
        missing_calls=missing[:20],
    )


def explain(result: dict) -> str:
    v = result["verdict"]
    if v == "unverified":
        return ("G4a unverified: the reference run recorded no calls into the library, "
                "so behaviour cannot be checked. Grade on the other gates and flag it.")
    if v == "identical":
        return (f"G4a pass: {result['matched']} of {result['reference_calls']} recorded calls "
                f"across {result['reference_sites']} call sites reproduce the library's "
                "values exactly.")
    if v == "missing":
        return (f"G4a fail: {result['missing']} call sites the library served are never "
                "reached by the replacement. The work is not being done.")
    return (f"G4a fail: {result['divergent']} call sites return a different value than the "
            f"library did on the same arguments ({result['matched']} reproduce correctly).")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("reference")
    ap.add_argument("candidate")
    ap.add_argument("--json", default=None)
    a = ap.parse_args()
    res = compare(load(a.reference), load(a.candidate))
    print(explain(res))
    for d in res["divergences"][:5]:
        print(f"  {d['site']}  {d['call']}")
        print(f"    library  -> {json.dumps(d['reference'], default=str)[:150]}")
        print(f"    candidate-> {json.dumps(d['candidate'], default=str)[:150]}")
    for m in res["missing_calls"][:5]:
        print(f"  {m['site']}  {m['call']}  never called")
    if a.json:
        pathlib.Path(a.json).write_text(json.dumps(res, indent=1, default=str))
    sys.exit(0 if res["passed"] else 1)


if __name__ == "__main__":
    main()
