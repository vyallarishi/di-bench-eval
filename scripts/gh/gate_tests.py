#!/usr/bin/env python3
"""G7: the test oracle must be untouched.

G2 accepts a removal when the tests pass. That is only meaningful if the tests
are the same tests. An agent that deletes the one test exercising the removed
library, marks it `skip`, or drops the assertion that checked the library's
output has not removed a dependency -- it has removed the evidence.

This cannot be caught structurally from the import graph: skipping a test
changes no import, adds no package, and leaves the call graph intact. It has to
be read off the test diff, which is what this gate does.

What counts as weakening:

  a test function or whole test file deleted
  a skip / xfail / skipif marker added, or pytest.skip() called
  assertions removed (more removed than added in the same file)
  a parametrisation narrowed (fewer cases than before)
  a test body replaced by pass / return / ...

What does NOT count:

  adding new tests (an agent may legitimately test its replacement)
  renaming or moving a test, as long as the assertions survive
  touching a test helper that is not itself an oracle
  editing a file the project does not treat as a test

Interface matches the other gates:
    check(patch_text, repo) -> {"pass": bool, "reason": str, "evidence": {...}}

usage: gate_tests.py <patch.diff> [--repo DIR] [--json out.json]
"""
from __future__ import annotations

import argparse
import json
import pathlib
import re
import sys

TEST_PATH = re.compile(
    r"(^|/)(tests?|testing|unittests?|integration_tests)/|"
    r"(^|/)test_[^/]*\.py$|_test\.py$|(^|/)conftest\.py$|(^|/)tests\.py$")

SKIP_ADDED = re.compile(
    r"@(?:pytest\.mark\.)?(?:skip|skipif|xfail)\b|"
    r"\bpytest\.skip\s*\(|\bunittest\.skip\b|\bself\.skipTest\s*\(|"
    r"\braise\s+SkipTest\b")
ASSERT_RE = re.compile(r"\bassert\b|\bself\.assert[A-Za-z]*\s*\(|\bpytest\.raises\b|"
                       r"\bself\.fail\s*\(|\bnp\.testing\.assert")
TEST_DEF = re.compile(r"^\s*(?:async\s+)?def\s+(test_[A-Za-z0-9_]*|[A-Za-z0-9_]*_test)\s*\(")
PARAMETRIZE = re.compile(r"@(?:pytest\.mark\.)?parametrize")
TRIVIAL_BODY = re.compile(r"^\s*(pass|\.\.\.|return(\s+None)?)\s*$")


def is_test_file(path: str) -> bool:
    return bool(TEST_PATH.search(path))


def parse_patch(patch: str) -> dict[str, dict]:
    """path -> {added: [lines], removed: [lines], new_file, deleted_file}"""
    files: dict[str, dict] = {}
    cur = None
    for line in patch.splitlines():
        if line.startswith("diff --git"):
            m = re.search(r" b/(.+)$", line)
            cur = m.group(1) if m else None
            if cur:
                files[cur] = dict(added=[], removed=[], new_file=False, deleted_file=False)
        elif cur is None:
            continue
        elif line.startswith("new file mode"):
            files[cur]["new_file"] = True
        elif line.startswith("deleted file mode"):
            files[cur]["deleted_file"] = True
        elif line.startswith("+") and not line.startswith("+++"):
            files[cur]["added"].append(line[1:])
        elif line.startswith("-") and not line.startswith("---"):
            files[cur]["removed"].append(line[1:])
    return files


def _count(lines, rx) -> int:
    return sum(1 for l in lines if rx.search(l))


def check(patch_text: str, repo: pathlib.Path | None = None) -> dict:
    files = parse_patch(patch_text)
    findings: list[dict] = []
    touched, added_only = [], []

    for path, d in files.items():
        if not is_test_file(path):
            continue
        if d["new_file"]:
            added_only.append(path)       # a brand-new test file is allowed
            continue
        touched.append(path)

        if d["deleted_file"]:
            findings.append(dict(file=path, signal="test file deleted",
                                 detail=f"{len(d['removed'])} lines removed"))
            continue

        removed_defs = _count(d["removed"], TEST_DEF)
        added_defs = _count(d["added"], TEST_DEF)
        if removed_defs > added_defs:
            findings.append(dict(file=path, signal="test function removed",
                                 detail=f"{removed_defs} removed, {added_defs} added"))

        skips = [l.strip() for l in d["added"] if SKIP_ADDED.search(l)]
        if skips:
            findings.append(dict(file=path, signal="skip/xfail added",
                                 detail=skips[:3]))

        ra, aa = _count(d["removed"], ASSERT_RE), _count(d["added"], ASSERT_RE)
        if ra > aa:
            findings.append(dict(file=path, signal="assertions removed",
                                 detail=f"{ra} removed, {aa} added"))

        rp, ap = _count(d["removed"], PARAMETRIZE), _count(d["added"], PARAMETRIZE)
        if rp > ap:
            findings.append(dict(file=path, signal="parametrisation removed",
                                 detail=f"{rp} removed, {ap} added"))

        # a test body replaced by a trivial statement
        if any(TRIVIAL_BODY.match(l) for l in d["added"]) and ra > 0 and aa == 0:
            findings.append(dict(file=path, signal="test body emptied",
                                 detail="trivial statement added where assertions were removed"))

    ok = not findings
    if ok:
        reason = ("no test file modified" if not touched else
                  f"{len(touched)} test file(s) modified, no weakening signal")
        if added_only:
            reason += f"; {len(added_only)} new test file(s) added"
    else:
        sigs = sorted({f["signal"] for f in findings})
        reason = f"test oracle weakened: {', '.join(sigs)}"

    return dict(**{"pass": ok}, reason=reason,
                evidence=dict(findings=findings,
                              test_files_modified=sorted(touched),
                              test_files_added=sorted(added_only)))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("patch")
    ap.add_argument("--repo", default=None)
    ap.add_argument("--json", default=None)
    a = ap.parse_args()
    res = check(pathlib.Path(a.patch).read_text(errors="ignore"),
                pathlib.Path(a.repo) if a.repo else None)
    print(("PASS " if res["pass"] else "FAIL ") + res["reason"])
    for f in res["evidence"]["findings"]:
        print(f"  {f['file']}: {f['signal']} ({f['detail']})")
    if a.json:
        pathlib.Path(a.json).write_text(json.dumps(res, indent=1, default=str))
    sys.exit(0 if res["pass"] else 1)


if __name__ == "__main__":
    main()
