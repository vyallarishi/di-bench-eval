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

The oracle is also the machinery that selects and runs the tests, and that
machinery is configuration, not test code: the workflow the harness replays,
pytest's own configuration (`pytest.ini`, `[tool:pytest]` in `setup.cfg`,
`[tool.pytest.*]` in `pyproject.toml`), tox and nox, and pytest's collection
hooks in a `conftest.py`. An `addopts = -k "not dep"`, a `--deselect`, a
narrowed `testpaths`, a workflow step that runs a subset, or a
`pytest_collection_modifyitems` that drops items weakens the oracle without
touching a test. Any edit inside those scopes is rejected, with one
exception: a removed line that names the removed package (a `deps =` entry in
`tox.ini`, a `pip install` of it in a workflow) is part of the removal.

Interface matches the other gates:
    check(patch_text, repo, dep=None) -> {"pass": bool, "reason": str, "evidence": {...}}

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

# --- the runner's configuration ------------------------------------------
WORKFLOW_PATH = re.compile(r"(^|/)\.github/workflows/[^/]+\.ya?ml$")
RUNNER_FILE = re.compile(r"(^|/)(pytest\.ini|\.pytest\.ini|tox\.ini|noxfile\.py)$")
# tables / sections that configure pytest, tox or nox inside a shared file
PYPROJECT_TABLE = re.compile(r"^\s*\[\s*tool\.(pytest|tox|nox)(\.|\s*\]|\])")
SETUPCFG_SECTION = re.compile(r"^\s*\[\s*(tool:pytest|pytest|tox:[^\]]*)\s*\]")
ANY_HEADER = re.compile(r"^\s*\[[^\]]+\]\s*$")
COLLECTION_HOOK = re.compile(
    r"^\s*(?:(?:async\s+)?def\s+pytest_(?:collection_modifyitems|ignore_collect|collect_file|"
    r"collect_directory|pycollect_makeitem|runtest_setup|runtest_call|deselected|"
    r"runtest_makereport|sessionstart)\b|collect_ignore(?:_glob)?\s*=)")
INJECT_BEGIN = "# >>> UnpinBench injected block"
INJECT_END = "# <<< UnpinBench injected block"


def _strip_injected(lines: list[str]) -> list[str]:
    """Drop the harness's own injected block from a file's added lines."""
    out, skipping = [], False
    for l in lines:
        if INJECT_BEGIN in l:
            skipping = True
            continue
        if INJECT_END in l:
            skipping = False
            continue
        if not skipping:
            out.append(l)
    return out


def _names_dep(line: str, dep: str | None) -> bool:
    if not dep:
        return False
    d = re.escape(dep.lower().replace("_", "[-_.]").replace("\\[", "[").replace("\\]", "]"))
    return re.search(r"(?<![a-z0-9])" + d + r"(?![a-z0-9])", line.lower()) is not None


def parse_hunks(patch: str) -> dict[str, list[dict]]:
    """path -> [{old_start, lines: [(kind, text)]}], kind in ' ', '+', '-'.

    A diff without hunk headers (as hand-made test diffs are) is one hunk
    whose position is unknown.
    """
    files: dict[str, list[dict]] = {}
    cur = None
    for line in patch.splitlines():
        if line.startswith("diff --git"):
            m = re.search(r" b/(.+)$", line)
            cur = m.group(1) if m else None
            if cur:
                files[cur] = []
        elif cur is None or line.startswith(("---", "+++", "index ", "new file", "deleted file",
                                             "similarity", "rename ", "old mode", "new mode")):
            continue
        elif line.startswith("@@"):
            m = re.match(r"@@ -(\d+)", line)
            files[cur].append(dict(old_start=int(m.group(1)) if m else None, lines=[]))
        elif line[:1] in (" ", "+", "-", "\\"):
            if not files[cur]:
                files[cur].append(dict(old_start=None, lines=[]))
            if line[:1] != "\\":
                files[cur][-1]["lines"].append((line[0], line[1:]))
    return files


def _section_of(original: list[str] | None, hunk: dict, header_rx) -> str | None:
    """The config section a hunk starts in, from the original file when there is one."""
    if not original:
        return None
    anchor = next((t for k, t in hunk["lines"] if k != "+"), None)
    idx = None
    if anchor is not None:
        hits = [i for i, l in enumerate(original) if l == anchor]
        if hits:
            want = (hunk["old_start"] or 1) - 1
            idx = min(hits, key=lambda i: abs(i - want))
    if idx is None and hunk["old_start"]:
        idx = min(hunk["old_start"] - 1, len(original) - 1)
    if idx is None:
        return None
    for i in range(idx, -1, -1):
        if ANY_HEADER.match(original[i]):
            return original[i].strip()
    return None


def config_edits(patch: str, repo: pathlib.Path | None, dep: str | None) -> list[dict]:
    """Edits to the runner's configuration, with the file and section named."""
    findings = []
    for path, hunks in parse_hunks(patch).items():
        base = path.rsplit("/", 1)[-1]
        scope = None
        header_rx = None
        if WORKFLOW_PATH.search(path):
            scope = "workflow file"
        elif RUNNER_FILE.search(path):
            scope = "test-runner configuration"
        elif base == "pyproject.toml":
            header_rx = PYPROJECT_TABLE
        elif base == "setup.cfg":
            header_rx = SETUPCFG_SECTION
        elif base == "conftest.py" or base.endswith("/conftest.py"):
            added = _strip_injected([t for h in hunks for k, t in h["lines"] if k == "+"])
            hooks = [l.strip() for l in added if COLLECTION_HOOK.match(l)]
            if hooks:
                findings.append(dict(file=path, signal="collection hook added", detail=hooks[:3]))
            continue
        else:
            continue
        original = None
        if header_rx is not None and repo is not None and (repo / path).exists():
            original = (repo / path).read_text(errors="ignore").splitlines()
        for h in hunks:
            section = _section_of(original, h, header_rx) if header_rx is not None else None
            in_scope = scope is not None or bool(section and header_rx.match(section))
            bad = []
            for kind, text in h["lines"]:
                if header_rx is not None and ANY_HEADER.match(text):
                    section = text.strip()
                    in_scope = bool(header_rx.match(section))
                    if kind == "+" and in_scope:
                        bad.append("+" + text.strip())
                    continue
                if kind == " " or not in_scope:
                    continue
                if kind == "-" and _names_dep(text, dep):
                    continue            # removing the package from the runner's deps is the removal
                if text.strip():
                    bad.append(kind + text.strip())
            if bad:
                where = scope or f"{section} in {base}"
                findings.append(dict(file=path, signal=f"{where} edited",
                                     detail=bad[:3]))
    return findings


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


def check(patch_text: str, repo: pathlib.Path | None = None, dep: str | None = None) -> dict:
    files = parse_patch(patch_text)
    findings: list[dict] = config_edits(patch_text, repo, dep)
    touched, added_only = [], []

    for path, d in files.items():
        if not is_test_file(path):
            continue
        # the harness's own injected block is not the submission's edit
        d["added"] = _strip_injected(d["added"])
        if d["new_file"]:
            added_only.append(path)       # a brand-new test file is allowed
            continue
        if not d["added"] and not d["removed"]:
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
        reason += "; no workflow or runner configuration edited"
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
    ap.add_argument("--dep", default=None)
    ap.add_argument("--json", default=None)
    a = ap.parse_args()
    res = check(pathlib.Path(a.patch).read_text(errors="ignore"),
                pathlib.Path(a.repo) if a.repo else None, a.dep)
    print(("PASS " if res["pass"] else "FAIL ") + res["reason"])
    for f in res["evidence"]["findings"]:
        print(f"  {f['file']}: {f['signal']} ({f['detail']})")
    if a.json:
        pathlib.Path(a.json).write_text(json.dumps(res, indent=1, default=str))
    sys.exit(0 if res["pass"] else 1)


if __name__ == "__main__":
    main()
