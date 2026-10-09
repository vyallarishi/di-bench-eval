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

  identical    every reference call has a matching candidate call, same value,
               or its enclosing project function is observed to agree
  divergent    a paired call returns a different value, or raises differently
  unverified   the gate cannot speak: no reference call was recorded, or the
               candidate could not be observed for some reference call (it
               recorded nothing at either level, a site is module-level with
               no function to observe, a function was renamed). The reason
               says which. A gate that cannot see does not reject.

Two levels are compared. At the LIBRARY BOUNDARY the recorder wraps the
library's callables and, for a candidate, a replacement module named as a
target; calls pair by site and order. At the USAGE SITE the recorder wraps
the project's own functions that use the library, in both phases; calls pair
by function and inputs. The second level is what observes a rewrite inside a
modified module or inlined at the site, which the first cannot (see
`record_usage.usage_functions`).

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
from record_usage import parse_site  # noqa: E402,F401


def _norm_site(site):
    """A call site relative to the repository root, whatever checkout it was recorded in.

    The reference and candidate runs live in different working copies; a site
    recorded as a path through a temporary directory, or through the '..'
    segments a symlinked checkout produces, must pair with the same file and
    line in the other copy. Only the repository-relative path identifies a site.
    """
    import re as _re
    if not isinstance(site, str):
        return site
    s = _re.sub(r"^(?:\.\./)+", "", site)
    s = _re.sub(r"^.*?/(?:ref|cand)/", "", s)
    return s


_TMP_PATTERNS = None


def _norm_value(v):
    """Strip temporary-directory paths from recorded strings before comparing.

    A test suite that creates a temporary directory passes its path into the
    library and gets it back in results; the path differs between any two
    runs, including two CI jobs, and is not behaviour. Checkout roots are
    handled by the runner; pytest's and the OS's temporary directories are
    handled here.
    """
    global _TMP_PATTERNS
    import re as _re
    if _TMP_PATTERNS is None:
        _TMP_PATTERNS = [_re.compile(r"pytest-of-[^/\\]+[/\\]pytest-\d+(?:[/\\][^/\\'\" ]*)?"),
                         _re.compile(r"(?:/private)?/var/folders/[^ '\"]*?/T/[^ '\"/]+"),
                         _re.compile(r"/tmp/(?:tmp|pytest-)[A-Za-z0-9_.-]+")]
    if isinstance(v, str):
        for pat in _TMP_PATTERNS:
            v = pat.sub("<tmp>", v)
        return v
    if isinstance(v, list):
        return [_norm_value(x) for x in v]
    if isinstance(v, dict):
        return {k: _norm_value(x) for k, x in v.items()}
    return v


def _pair_key(rec: dict) -> tuple:
    """Identity of a library-boundary call for pairing: the call site.

    Deliberately NOT the qualified name, and NOT the arguments either. A
    removal renames the callee by construction, and it also changes what is
    passed: a rewrite hands its own Color object where the library's was
    handed before, and a path argument differs between two checkouts. What
    is stable across the two runs is *where* the repository asked for the
    work. Calls at a site are paired in order: the i-th call the reference
    made at a site pairs with the i-th call the candidate made there. The
    arguments travel with the record as evidence and are reported with every
    divergence, but they do not decide pairing.
    """
    return (_norm_site(rec.get("site")),)


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


def _level(rec: dict) -> str:
    return "usage" if rec.get("level") == "usage" else "library"


def _usage_inputs(rec: dict):
    """The inputs that identify a usage-site call: its arguments without `self`."""
    args = rec.get("args") or []
    if rec.get("m") and args:
        args = args[1:]
    return args, rec.get("kwargs") or {}


def _same_inputs(a: dict, b: dict) -> bool:
    aa, ak = _usage_inputs(a)
    ba, bk = _usage_inputs(b)
    if len(aa) != len(ba) or set(ak) != set(bk):
        return False
    return (all(values_equal(x, y) for x, y in zip(aa, ba))
            and all(values_equal(ak[k], bk[k]) for k in ak))


def _divergence(r: dict, c: dict, level: str) -> dict:
    return dict(level=level, call=r.get("q"), candidate_call=c.get("q"),
                site=r.get("site"), args=r.get("args"), kwargs=r.get("kwargs"),
                reference=_outcome(r)[1], candidate=_outcome(c)[1])


def _pair_library(reference, candidate):
    """Pair by site and order. Returns (matched, divergences, unreached records)."""
    ref_by: dict[tuple, list[dict]] = collections.defaultdict(list)
    for r in reference:
        ref_by[_pair_key(r)].append(r)
    cand_by: dict[tuple, list[dict]] = collections.defaultdict(list)
    for c in candidate:
        cand_by[_pair_key(c)].append(c)
    matched, divergences, unreached = 0, [], []
    for key, refs in ref_by.items():
        cands = cand_by.get(key, [])
        for i, r in enumerate(refs):
            if i >= len(cands):
                unreached.append(r)
            elif _same_outcome(r, cands[i]):
                matched += 1
            else:
                divergences.append(_divergence(r, cands[i], "library"))
    extra = sum(max(0, len(v) - len(ref_by.get(k, []))) for k, v in cand_by.items())
    return matched, divergences, unreached, extra


def _nondeterministic(refs: list[dict]) -> bool:
    """Did the reference itself return different values for equal inputs?

    A function whose output is not a function of its inputs (a git hash, a
    timestamp, a temporary name) cannot be compared across two runs; a
    difference there is not evidence about the replacement. The reference
    run supplies the test: two of its own calls with equal inputs and
    different outcomes.
    """
    seen: list[tuple[dict, tuple]] = []
    for r in refs:
        out = _outcome(r)
        for other, o2 in seen:
            if _same_inputs(r, other):
                if not (out[0] == o2[0] and (out[1] == o2[1] if out[0] == "raised"
                                               else values_equal(out[1], o2[1]))):
                    return True
                break
        else:
            seen.append((r, out))
    return False


def _pair_usage(reference, candidate):
    """Pair by function, then align in order on equal inputs.

    The inputs of a project function come from the tests, so they are the
    same in both phases; a candidate that adds tests of its own inserts
    calls, and aligning on inputs rather than on position alone keeps those
    insertions from shifting every later pair. A reference call whose inputs
    never recur in the candidate is unreached, not divergent. A function the
    reference shows to be nondeterministic is paired and reported, but its
    divergences are not evidence.
    """
    ref_by: dict[str, list[dict]] = collections.defaultdict(list)
    for r in reference:
        ref_by[r.get("q")].append(r)
    cand_by: dict[str, list[dict]] = collections.defaultdict(list)
    for c in candidate:
        cand_by[c.get("q")].append(c)
    matched, divergences, unreached, discarded = 0, [], [], []
    per_fn: dict[str, dict] = {}
    for q, refs in ref_by.items():
        cands = cand_by.get(q, [])
        nondet = _nondeterministic(refs)
        j = 0
        m = d = u = 0
        for r in refs:
            k = j
            while k < len(cands) and not _same_inputs(r, cands[k]):
                k += 1
            if k >= len(cands):
                unreached.append(r)
                u += 1
                continue
            if _same_outcome(r, cands[k]):
                matched += 1
                m += 1
            elif nondet:
                discarded.append(_divergence(r, cands[k], "usage"))
                d += 1
            else:
                divergences.append(_divergence(r, cands[k], "usage"))
                d += 1
            j = k + 1
        per_fn[q] = dict(reference=len(refs), candidate=len(cands), matched=m,
                         divergent=0 if nondet else d, unreached=u,
                         nondeterministic=nondet, discarded=d if nondet else 0)
    extra = sum(max(0, len(v) - len(ref_by.get(k, []))) for k, v in cand_by.items())
    return matched, divergences, unreached, extra, per_fn, discarded


def compare(reference: list[dict], candidate: list[dict],
            site_function: dict | None = None) -> dict:
    """Compare two traces at both levels and return one verdict.

    Library-boundary records (calls into the library, or into a replacement
    module named as a target) pair by call site and order. Usage-site records
    (calls of the project's own functions that use the library) pair by
    function and inputs. `site_function` maps a recorded library site to the
    'rel::qualname' of its enclosing function, so that a site the candidate
    never reaches at the boundary can be credited to the usage level when
    that function is observed there.

    The verdict:

      divergent    a paired call, at either level, produced a different value
      identical    every reference call was matched, or its enclosing function
                   was observed at the usage level without divergence
      unverified   nothing to compare (no reference call), or the candidate
                   could not be observed for some reference call: it recorded
                   nothing at either level, a site has no enclosing function
                   the candidate reaches, or a function was renamed. The
                   reason names which. This is never reported as a failure.
    """
    reference = [_norm_value(r) for r in reference]
    candidate = [_norm_value(c) for c in candidate]
    site_function = {_norm_site(k): v for k, v in (site_function or {}).items()}
    ref_lib = [r for r in reference if _level(r) == "library"]
    ref_use = [r for r in reference if _level(r) == "usage"]
    cand_lib = [c for c in candidate if _level(c) == "library"]
    cand_use = [c for c in candidate if _level(c) == "usage"]

    lib_m, lib_d, lib_u, lib_x = _pair_library(ref_lib, cand_lib)
    use_m, use_d, use_u, use_x, per_fn, use_discarded = _pair_usage(ref_use, cand_use)
    lib_observable = bool(cand_lib)
    observed_fns = {q for q, v in per_fn.items() if v["candidate"] > 0 and v["divergent"] == 0}

    divergences = (lib_d if lib_observable else []) + use_d
    covered = 0                      # library calls credited to the usage level
    not_observable = []              # (what, why)
    lib_unpaired = lib_u if lib_observable else ref_lib
    for r in lib_unpaired:
        fn = site_function.get(_norm_site(r.get("site")))
        if fn and fn in observed_fns:
            covered += 1
        elif fn and fn in per_fn:
            not_observable.append(dict(level="library", site=r.get("site"), call=r.get("q"),
                                       why=f"site not reached; its function {fn} is not observed in the candidate"))
        elif fn:
            not_observable.append(dict(level="library", site=r.get("site"), call=r.get("q"),
                                       why=f"site not reached; its function {fn} recorded nothing in the reference"))
        else:
            not_observable.append(dict(level="library", site=r.get("site"), call=r.get("q"),
                                       why=("no replacement callable observable" if not lib_observable
                                            else "site not reached") + "; module-level or test-file site has no function to observe"))
    for r in use_u:
        q = r.get("q")
        v = per_fn.get(q, {})
        why = ("function not observed in the candidate (renamed, removed, or not wrappable)"
               if not v.get("candidate") else
               f"fewer calls with these inputs than the reference ({v.get('candidate')} of {v.get('reference')})")
        not_observable.append(dict(level="usage", site=q, call=q, why=why))

    n_ref = len(reference)
    if n_ref == 0:
        verdict, passed = "unverified", None
        reason = "the reference run recorded no calls into the library"
    elif divergences:
        verdict, passed = "divergent", False
        reason = (f"{len(divergences)} paired call(s) return a different value than the library "
                  f"({lib_m + use_m} agree)")
    elif not cand_lib and not cand_use:
        verdict, passed = "unverified", None
        reason = "replacement not observable: the candidate recorded no call at either level"
    elif not_observable:
        verdict, passed = "unverified", None
        whys = collections.Counter(x["why"].split(";")[0] for x in not_observable)
        reason = (f"identical on {lib_m + use_m + covered} of {n_ref} reference calls; "
                  f"{len(not_observable)} not observable: "
                  + "; ".join(f"{n} {w}" for w, n in whys.most_common(3)))
    else:
        verdict, passed = "identical", True
        reason = (f"{lib_m + use_m} paired calls reproduce the library's values"
                  + (f", {covered} boundary call(s) verified through the enclosing function" if covered else "")
                  + (f"; {len(use_discarded)} usage-level difference(s) in nondeterministic function(s) not counted"
                     if use_discarded else ""))

    decided = ("both" if (lib_observable and ref_use and cand_use) else
               "usage" if (ref_use and cand_use) else
               "library" if lib_observable else "none")
    return dict(
        verdict=verdict,
        passed=passed,
        reason=reason,
        decided_at=decided,
        reference_calls=n_ref,
        candidate_calls=len(candidate),
        reference_sites=len({r.get("site") for r in ref_lib}),
        reference_library_calls=len(ref_lib),
        reference_usage_calls=len(ref_use),
        candidate_library_calls=len(cand_lib),
        candidate_usage_calls=len(cand_use),
        matched=lib_m + use_m,
        matched_library=lib_m,
        matched_usage=use_m,
        covered_by_usage=covered,
        divergent=len(divergences),
        missing=len(not_observable),
        not_observable=len(not_observable),
        discarded_nondeterministic=len(use_discarded),
        extra_candidate_calls=lib_x + use_x,
        usage_functions={q: v for q, v in per_fn.items()},
        divergences=divergences[:20],
        discarded=use_discarded[:5],
        missing_calls=not_observable[:20],
    )


def explain(result: dict) -> str:
    v = result["verdict"]
    if v == "unverified":
        return "G4a unverified: " + result.get("reason", "") + ". Grade on the other gates and flag it."
    if v == "identical":
        return (f"G4a pass: {result['matched']} paired calls ({result['matched_library']} at the library "
                f"boundary, {result['matched_usage']} at usage sites) reproduce the library's values"
                + (f"; {result['covered_by_usage']} boundary call(s) verified through the enclosing function"
                   if result.get("covered_by_usage") else "") + ".")
    return (f"G4a fail: {result['divergent']} paired call(s) return a different value than the "
            f"library did on the same inputs ({result['matched']} agree).")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("reference")
    ap.add_argument("candidate")
    ap.add_argument("--json", default=None)
    ap.add_argument("--repo", default=None,
                    help="reference checkout, to map each recorded site to its enclosing function")
    a = ap.parse_args()
    ref = load(a.reference)
    from record_usage import site_functions
    sf = site_functions(pathlib.Path(a.repo), ref) if a.repo else None
    res = compare(ref, load(a.candidate), sf)
    print(explain(res))
    for d in res["divergences"][:5]:
        print(f"  {d['site']}  {d['call']}")
        print(f"    library  -> {json.dumps(d['reference'], default=str)[:150]}")
        print(f"    candidate-> {json.dumps(d['candidate'], default=str)[:150]}")
    for m in res["missing_calls"][:5]:
        print(f"  {m['site']}  {m['call']}  not observable: {m['why']}")
    if a.json:
        pathlib.Path(a.json).write_text(json.dumps(res, indent=1, default=str))
    sys.exit(0 if res["passed"] else (2 if res["passed"] is None else 1))


if __name__ == "__main__":
    main()
