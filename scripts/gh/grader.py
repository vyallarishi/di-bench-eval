#!/usr/bin/env python3
"""The grader: run every gate over a candidate removal and report one verdict.

A removal is accepted only if every gate passes. The gates are independent
questions, and the point of composing them is that no single one is sufficient:

  G1  declaration gone        the manifest no longer declares the package
  G2  tests pass              the repository's own suite, unchanged, still green
  G3  no vendored copy        the library's source was not pasted in
  G4a behaviour preserved     the replacement reproduces what the library did
                              on the inputs the tests exercise
  G4c oracle strength         how much of the replacement the suite constrains
  G5  no phantom use          the package is not still installed transitively
  G7  test oracle untouched   no test deleted, skipped or weakened
  G8  closure not grown       no new third-party package took its place

This module does **not** replace G2. A candidate must pass the tests *and* the
gates; the claim is that CI alone accepts work that is wrong, not that CI
should be discarded. Reporting it any other way would invite the obvious
objection -- "so you would accept a patch that breaks the tests?" -- and
deserve it.

Coverage is reported, not assumed. A gate that cannot speak about a candidate
returns `unverified` and says why, and the summary counts those separately from
passes and failures. The commonest case is G4a on a pair whose tests never
exercise the dependency: there is nothing to record, so nothing to compare, and
pretending otherwise would turn a coverage limit into a false clean bill.

usage:
  grader.py --patch P --repo DIR --dep NAME [--gold-patch-from DATASET]
            [--reference ref.jsonl --candidate cand.jsonl] [--json out.json]
or as a library: grade(...) -> {"accepted": bool, "gates": {...}, ...}
"""
from __future__ import annotations

import argparse
import json
import pathlib
import re
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
import gate_behaviour  # noqa: E402
import gate_closure  # noqa: E402
import gate_tests  # noqa: E402
import manifests as M  # noqa: E402
from make_blocked import apply_patch as apply_manifest_patch  # noqa: E402

UNVERIFIED = "unverified"


def _verdict(ok: bool | None, reason: str, **ev) -> dict:
    return dict(status=(UNVERIFIED if ok is None else ("pass" if ok else "fail")),
                reason=reason, evidence=ev)


def g1_declaration_gone(patch: str, repo: pathlib.Path, dep: str,
                        gold_patch: str | None) -> dict:
    """The package must not be declared in the resulting manifest."""
    paths = gate_closure.manifest_paths(patch)
    if not paths:
        return _verdict(False, "the patch edits no manifest")
    target = M.norm(dep)
    for p in paths:
        before, after = gate_closure.declared_before_after(patch, repo, p, gold_patch)
        if after is None:
            return _verdict(None, f"candidate manifest edit did not apply ({p})")
        if gold_patch and target not in before:
            return _verdict(None, f"{dep} is not declared in the gold manifest ({p})")
        if target in after:
            return _verdict(False, f"{dep} is still declared in {p}")
    return _verdict(True, f"{dep} is no longer declared")


def g3_no_vendored_copy(patch: str, dep: str, threshold: float = 0.6) -> dict:
    """Added files must not be a copy of the library's own source.

    Token-overlap against the published wheel is the cheap version; a published
    grader should use winnowing. Reported as a signal with its score so a
    borderline case is visible rather than silently decided.
    """
    added = {}
    cur, new = None, False
    for line in patch.splitlines():
        if line.startswith("diff --git"):
            m = re.search(r" b/(.+)$", line)
            cur, new = (m.group(1) if m else None), False
        elif line.startswith("new file mode"):
            new = True
        elif cur and new and line.startswith("+") and not line.startswith("+++"):
            added.setdefault(cur, []).append(line[1:])
    py = {p: "\n".join(v) for p, v in added.items() if p.endswith(".py")}
    if not py:
        return _verdict(True, "the patch adds no new Python file")
    # a new file whose top-level package name is the removed library is a shadow
    roots = {M.norm(p.split("/")[0].removesuffix(".py")) for p in py}
    if M.norm(dep) in roots or M.norm(dep).replace("_", "") in roots:
        return _verdict(False,
                        f"a new module shadows the removed package name ({sorted(roots)})",
                        shadow=sorted(roots))
    return _verdict(True, f"{len(py)} new Python file(s), none shadowing {dep}",
                    added_files=sorted(py))


def g4a_behaviour(reference: list[dict], candidate: list[dict]) -> dict:
    if not reference:
        return _verdict(None, "the reference run recorded no calls into the library, "
                              "so behaviour cannot be compared")
    res = gate_behaviour.compare(reference, candidate)
    return _verdict(res["passed"], gate_behaviour.explain(res),
                    **{k: v for k, v in res.items()
                       if k in ("verdict", "matched", "divergent", "missing",
                                "reference_calls", "reference_sites")})


def g5_no_phantom(ci_log: str | None, dep: str) -> dict:
    """The package must not still arrive through another dependency."""
    if not ci_log:
        return _verdict(None, "no install log available")
    pat = re.compile(rf"\b{re.escape(M.norm(dep)).replace('_', '[-_.]')}\b", re.I)
    installed = [l for l in ci_log.splitlines()
                 if ("Installing collected packages" in l or "Successfully installed" in l
                     or re.match(r"\s*(Downloading|Collecting)\b", l)) and pat.search(l)]
    if installed:
        return _verdict(False, f"{dep} still appears in the install log",
                        lines=[l.strip()[:120] for l in installed[:3]])
    return _verdict(True, f"{dep} does not appear in the install log")


def grade(patch: str, repo: pathlib.Path, dep: str, *,
          gold_patch: str | None = None,
          tests_passed: bool | None = None,
          reference: list[dict] | None = None,
          candidate: list[dict] | None = None,
          ci_log: str | None = None,
          mutation: dict | None = None,
          before: set | None = None, after: set | None = None) -> dict:
    gates = {
        "G1_declaration_gone": g1_declaration_gone(patch, repo, dep, gold_patch),
        "G2_tests_pass": (_verdict(None, "the suite was not run")
                          if tests_passed is None else
                          _verdict(tests_passed,
                                   "the repository's suite passes" if tests_passed
                                   else "the repository's suite fails")),
        "G3_no_vendored_copy": g3_no_vendored_copy(patch, dep),
        "G4a_behaviour": g4a_behaviour(reference or [], candidate or []),
        "G5_no_phantom": g5_no_phantom(ci_log, dep),
        "G7_tests_untouched": (lambda r: _verdict(r["pass"], r["reason"], **r["evidence"]))(
            gate_tests.check(patch, repo)),
        "G8_closure_not_grown": (lambda r: _verdict(r["pass"], r["reason"], **r["evidence"]))(
            gate_closure.check(patch, repo, dep, before, after, gold_patch=gold_patch)),
    }
    if mutation is not None:
        gates["G4c_oracle_strength"] = _verdict(
            mutation["pass"], mutation["reason"], **mutation["evidence"])

    failed = [k for k, v in gates.items() if v["status"] == "fail"]
    unver = [k for k, v in gates.items() if v["status"] == UNVERIFIED]
    accepted = not failed and not unver
    if failed:
        summary = "rejected by " + ", ".join(failed)
    elif unver:
        summary = ("every gate that could run passed, but " + ", ".join(unver)
                   + " could not be evaluated")
    else:
        summary = "accepted: every gate passed"
    return dict(accepted=accepted, summary=summary,
                failed=failed, unverified=unver, gates=gates)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--patch", required=True)
    ap.add_argument("--repo", required=True)
    ap.add_argument("--dep", required=True)
    ap.add_argument("--dataset", default=None, help="to recover the gold manifest")
    ap.add_argument("--tests-passed", choices=["yes", "no"], default=None)
    ap.add_argument("--reference", default=None)
    ap.add_argument("--candidate", default=None)
    ap.add_argument("--ci-log", default=None)
    ap.add_argument("--json", default=None)
    a = ap.parse_args()

    repo = pathlib.Path(a.repo)
    gold = None
    if a.dataset:
        base = repo.name
        for line in open(a.dataset):
            if line.strip() and json.loads(line)["instance_id"] == base:
                gold = json.loads(line)["patch"]
                break
    res = grade(pathlib.Path(a.patch).read_text(errors="ignore"), repo, a.dep,
                gold_patch=gold,
                tests_passed=(None if a.tests_passed is None else a.tests_passed == "yes"),
                reference=gate_behaviour.load(a.reference) if a.reference else None,
                candidate=gate_behaviour.load(a.candidate) if a.candidate else None,
                ci_log=(pathlib.Path(a.ci_log).read_text(errors="ignore")
                        if a.ci_log else None))
    print(("ACCEPTED  " if res["accepted"] else "REJECTED  ") + res["summary"])
    for name, v in res["gates"].items():
        mark = {"pass": "ok  ", "fail": "FAIL", UNVERIFIED: "n/a "}[v["status"]]
        print(f"  {mark} {name:24s} {v['reason'][:84]}")
    if a.json:
        pathlib.Path(a.json).write_text(json.dumps(res, indent=1, default=str))
    sys.exit(0 if res["accepted"] else 1)


if __name__ == "__main__":
    main()
