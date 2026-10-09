#!/usr/bin/env python3
"""The grader: run every gate over a candidate removal and report one verdict.

A removal is accepted only if every gate passes. The gates are independent
questions, and the point of composing them is that no single one is sufficient:

  G1  declaration gone        the manifest no longer declares the package
  G2  tests pass              the repository's own suite, unchanged, still green
  G3  no vendored copy        the library's source was not pasted in
  G4a behaviour preserved     the replacement reproduces what the library did
                              on the inputs the tests exercise, observed at the
                              library boundary where a replacement callable is
                              named and at the project's own usage sites always
  G4c oracle strength         how much of the replacement the suite constrains
  G5  no phantom use          the package is not used while undeclared
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
import gate_vendor  # noqa: E402
import manifests as M  # noqa: E402
from make_blocked import apply_patch as apply_manifest_patch  # noqa: E402

UNVERIFIED = "unverified"


def _verdict(ok: bool | None, reason: str, **ev) -> dict:
    return dict(status=(UNVERIFIED if ok is None else ("pass" if ok else "fail")),
                reason=reason, evidence=ev)


def _after_text(patch: str, repo: pathlib.Path, path: str,
                gold_patch: str | None) -> str:
    """The manifest as the candidate leaves it, or '' if the patch will not apply."""
    import subprocess
    import tempfile
    src = repo / path
    if not src.exists():
        return ""
    masked = src.read_text(errors="ignore")
    gold = masked
    if gold_patch:
        try:
            gold = apply_manifest_patch(repo, path, gold_patch)
        except Exception:
            pass
    for base in (masked, gold):
        with tempfile.TemporaryDirectory() as td:
            t = pathlib.Path(td)
            (t / path).parent.mkdir(parents=True, exist_ok=True)
            (t / path).write_text(base)
            (t / "p.diff").write_text(patch)
            for cmd in (["git", "apply", "--allow-empty", "--ignore-whitespace",
                         "--ignore-space-change", "--include", path, "p.diff"],
                        ["patch", "--batch", "--fuzz=5", "-p1", "-i", "p.diff", path]):
                if subprocess.run(cmd, cwd=t, capture_output=True,
                                  text=True).returncode == 0:
                    return (t / path).read_text(errors="ignore")
    return ""


def _declared_anywhere(path: str, text: str, dep: str) -> list[str]:
    """Sections of a manifest that still name `dep`, beyond the main list.

    `manifests.declared` reads the runtime dependency list only, which is the
    right scope for most questions and the wrong one for this gate: moving a
    package into `[project.optional-dependencies]`, a Poetry group, or a
    requirements file referenced by `-r` removes it from that list while
    leaving it installable. The constructed `hide` family does exactly this,
    and G1 passed all 77 of them before this check existed.
    """
    import re as _re
    target = M.norm(dep)
    hits = []
    # any TOML table whose name suggests dependencies, other than the main one
    for m in _re.finditer(r"^\[([^\]]+)\]\s*$", text, _re.M):
        name = m.group(1)
        if "depend" not in name and "group" not in name and "extras" not in name:
            continue
        body = text[m.end():]
        nxt = _re.search(r"^\[", body, _re.M)
        body = body[: nxt.start()] if nxt else body
        for tok in _re.findall(r"[A-Za-z0-9][A-Za-z0-9._-]*", body):
            if M.norm(tok) == target:
                hits.append(f"[{name}]")
                break
    # setup.py extras_require / tests_require
    for key in ("extras_require", "tests_require", "setup_requires"):
        m = _re.search(key + r"\s*=\s*[\[{]", text)
        if not m:
            continue
        seg = text[m.end(): m.end() + 2000]
        for tok in _re.findall(r"[A-Za-z0-9][A-Za-z0-9._-]*", seg):
            if M.norm(tok) == target:
                hits.append(key)
                break
    return sorted(set(hits))


def g1_declaration_gone(patch: str, repo: pathlib.Path, dep: str,
                        gold_patch: str | None) -> dict:
    """The package must not be declared anywhere the build system reads."""
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
        # the main list is clean; check the places a declaration can hide
        after_text = _after_text(patch, repo, p, gold_patch)
        elsewhere = _declared_anywhere(p, after_text, dep) if after_text else []
        if elsewhere:
            return _verdict(False,
                            f"{dep} was moved rather than removed: still named in "
                            + ", ".join(elsewhere) + f" of {p}",
                            sections=elsewhere)
    return _verdict(True, f"{dep} is no longer declared")


def g3_no_vendored_copy(patch: str, dep: str, threshold: float = 0.6) -> dict:
    """The name-only check that preceded `gate_vendor` (kept for comparison).

    It sees a new module under the package's import name and nothing else;
    the grader now calls `gate_vendor.check`, which also fingerprints every
    added or modified Python file against the library's distributed source.
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


def g4a_behaviour(reference: list[dict], candidate: list[dict],
                  nothing_to_verify: bool = False,
                  site_function: dict | None = None) -> dict:
    if not reference and nothing_to_verify:
        # the repository never imported the package, so there is no behaviour
        # to preserve: nothing to verify is a pass, not an inconclusive
        return _verdict(True, "the repository never imported the package, so there is "
                              "no behaviour to preserve")
    if not reference:
        return _verdict(None, "the reference run recorded no calls into the library, "
                              "so behaviour cannot be compared")
    res = gate_behaviour.compare(reference, candidate, site_function)
    # passed is True / False / None: None means the candidate could not be
    # observed for some reference call, which is inconclusive, never a rejection
    return _verdict(res["passed"], gate_behaviour.explain(res),
                    **{k: v for k, v in res.items()
                       if k in ("verdict", "decided_at", "matched", "matched_library",
                                "matched_usage", "covered_by_usage", "divergent",
                                "not_observable", "reference_calls", "reference_sites",
                                "reference_usage_calls", "candidate_library_calls",
                                "candidate_usage_calls")})


BLOCKER_ACTIVE = "UnpinBench blocker active"


def g5_no_phantom(ci_log: str | None, dep: str, tests_passed: bool | None = None,
                  blocker_active: bool | None = None) -> dict:
    """The repository must not go on using the package without declaring it.

    Phantom use needs two things: the package still present, and the
    repository importing it. Presence alone is not a fault -- a correct removal
    cannot uninstall a package that another declaration pulls in transitively
    (typing_extensions, werkzeug, sniffio arrive that way in real references).
    So when the run carried the scoped import blocker, the import side is what
    decides: a green suite under the blocker means no repository frame imported
    the package, and the package being installed is irrelevant. Without a
    blocker in the run, presence in the install log is all the evidence there
    is, and the gate fails on it as before.
    """
    # The block announces itself on stderr, which the harness captures for
    # only some workflows; the patch itself is the authoritative evidence that
    # the run carried it. The caller may say so; otherwise fall back to the log.
    active = blocker_active if blocker_active is not None else bool(ci_log and BLOCKER_ACTIVE in ci_log)
    if active and tests_passed:
        return _verdict(True, f"the suite passed with {dep} unimportable from repository "
                              "frames, so any installed copy is unused")
    if not ci_log:
        return _verdict(None, "no install log available")
    pat = re.compile(rf"\b{re.escape(M.norm(dep)).replace('_', '[-_.]')}\b", re.I)
    installed = [l for l in ci_log.splitlines()
                 if ("Installing collected packages" in l or "Successfully installed" in l
                     or re.match(r"\s*(Downloading|Collecting)\b", l)) and pat.search(l)]
    if not installed:
        return _verdict(True, f"{dep} does not appear in the install log")
    if active:
        if tests_passed:
            return _verdict(True, f"{dep} is still installed (transitively) but the suite "
                                  "passed with it unimportable from repository frames",
                            lines=[l.strip()[:120] for l in installed[:3]])
        return _verdict(None, f"{dep} is still installed and the suite failed under the "
                              "blocker; G2 carries that failure",
                        lines=[l.strip()[:120] for l in installed[:3]])
    return _verdict(False, f"{dep} still appears in the install log and the run had no "
                           "import blocker, so phantom use cannot be excluded",
                    lines=[l.strip()[:120] for l in installed[:3]])


def grade(patch: str, repo: pathlib.Path, dep: str, *,
          gold_patch: str | None = None,
          tests_passed: bool | None = None,
          reference: list[dict] | None = None,
          candidate: list[dict] | None = None,
          ci_log: str | None = None,
          mutation: dict | None = None,
          before: set | None = None, after: set | None = None,
          blocker_active: bool | None = None,
          nothing_to_verify: bool = False,
          site_function: dict | None = None) -> dict:
    if blocker_active is None and "UnpinBench injected block" in patch:
        blocker_active = True
    gates = {
        "G1_declaration_gone": g1_declaration_gone(patch, repo, dep, gold_patch),
        "G2_tests_pass": (_verdict(None, "the suite was not run")
                          if tests_passed is None else
                          _verdict(tests_passed,
                                   "the repository's suite passes" if tests_passed
                                   else "the repository's suite fails")),
        "G3_no_vendored_copy": (lambda r: _verdict(r["pass"], r["reason"], **r["evidence"]))(
            gate_vendor.check(patch, dep)),
        "G4a_behaviour": g4a_behaviour(reference or [], candidate or [], nothing_to_verify,
                                       site_function),
        "G5_no_phantom": g5_no_phantom(ci_log, dep, tests_passed, blocker_active),
        "G7_tests_untouched": (lambda r: _verdict(r["pass"], r["reason"], **r["evidence"]))(
            gate_tests.check(patch, repo, dep)),
        # r["pass"] may be None, meaning the gate cannot speak; _verdict maps
        # that to "unverified" rather than a rejection
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
