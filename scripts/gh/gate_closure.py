#!/usr/bin/env python3
"""G8: the dependency closure must not grow.

Removing a dependency means the project needs less, not differently. Two ways a
candidate can satisfy G1 (declaration gone) and G2 (tests pass) while having
removed nothing:

  trade        drop `requests`, declare `httpx` instead. One name left the
               manifest, another arrived; the project depends on just as much.
  launder      drop `requests` and declare something that requires it
               transitively, so it is still installed and still importable.

So the rule is a subset rule, applied to the *resolved* set rather than the
declared one: resolve(after) must be a subset of resolve(before) minus the
removed package. A package the manifest already declared is fine -- using more
of what you already depend on is a legitimate removal strategy.

Resolution is the hard part and the honest limitation. Fully resolving a Python
dependency set requires the resolver, the target platform and the Python
version; doing that per candidate is expensive and still environment-specific.
This module therefore supports three modes, in decreasing strength, and always
reports which one produced the verdict so the paper can state it:

  observed   the caller supplies `before`/`after` package sets, measured from
             two real installs (what the CI harness can provide). Strongest.
  metadata   resolve each declared name's requirement closure from PyPI
             metadata (requires_dist), cached. No install, no platform.
  declared   compare declared names only. Catches the trade, not the launder.

Interface matches the other gates:
    check(patch_text, repo, dep, before=None, after=None) -> {...}

usage: gate_closure.py <patch.diff> --dep NAME [--repo DIR]
                       [--before a,b,c --after a,b] [--metadata]
"""
from __future__ import annotations

import argparse
import json
import pathlib
import re
import subprocess
import sys
import tempfile
import urllib.error
import urllib.request

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
import manifests as M  # noqa: E402
from make_blocked import apply_patch as apply_manifest_patch  # noqa: E402

CACHE: dict[str, set[str]] = {}
# Build-time and test-time packages are not part of what the project ships;
# a candidate adding pytest is not growing the runtime closure.
IGNORE = {"pip", "setuptools", "wheel", "pytest", "tox", "nox", "build",
          "setuptools_scm", "hatchling", "flit_core", "poetry_core", "pdm_backend"}


def norm(n: str) -> str:
    return n.lower().replace("-", "_").replace(".", "_")


def manifest_paths(patch: str) -> list[str]:
    out = []
    for line in patch.splitlines():
        if line.startswith("diff --git"):
            m = re.search(r" b/(.+)$", line)
            if m and M.kind(m.group(1)) != "unknown":
                out.append(m.group(1))
    return out


def declared_before_after(patch: str, repo: pathlib.Path, path: str,
                          gold_patch: str | None = None):
    """Declared sets either side of the candidate's change, for one manifest.

    Two different texts are needed, and conflating them is the trap here.

    *Baseline* is the GOLD manifest: the checked-out file is **masked** (its
    dependency list emptied, because inferring it is the original task), so
    using the file on disk makes every declaration look newly added. Applying
    `gold_patch` restores what the project really declared.

    *After* must be produced by applying the candidate patch to the **masked**
    file, because that is the text the candidate was written against. Applying
    it to the gold text fails on context (`-dependencies = []` does not appear
    there), git leaves the file untouched, and the result silently reads as
    "nothing was removed" -- which reported every constructed cheat as a
    closure violation.
    """
    src = repo / path
    if not src.exists():
        return set(), set()
    masked_text = src.read_text(errors="ignore")

    before_text = masked_text
    if gold_patch:
        try:
            before_text = apply_manifest_patch(repo, path, gold_patch)
        except Exception:
            pass

    # Which text the candidate patch was written against is not knowable from
    # the patch alone. DI-Bench's own predictions target the MASKED file;
    # constructed variants are built on the GOLD manifest. Applying to the
    # wrong one fails on context, git leaves the file untouched, and the result
    # reads as "nothing was removed" -- which rejected every family including
    # the honest deletion. Try both and take whichever applies.
    applied = False
    for base_text in (masked_text, before_text):
        with tempfile.TemporaryDirectory() as td:
            tdp = pathlib.Path(td)
            (tdp / path).parent.mkdir(parents=True, exist_ok=True)
            (tdp / path).write_text(base_text)
            (tdp / "p.diff").write_text(patch)
            for cmd in (["git", "apply", "--allow-empty", "--ignore-whitespace",
                         "--ignore-space-change", "--include", path, "p.diff"],
                        ["patch", "--batch", "--fuzz=5", "-p1", "-i", "p.diff", path]):
                if subprocess.run(cmd, cwd=tdp, capture_output=True,
                                  text=True).returncode == 0:
                    applied = True
                    break
            if applied:
                after_text = (tdp / path).read_text(errors="ignore")
                break
        if base_text is before_text:
            break
    if not applied:
        after_text = ""
    try:
        before = M.declared(path, before_text)
    except Exception:
        before = set()
    try:
        after = M.declared(path, after_text) if applied else None
    except Exception:
        after = None
    return before, after


def pypi_requires(name: str, timeout: int = 15) -> set[str]:
    """Direct runtime requirements of a package, from PyPI metadata."""
    k = norm(name)
    if k in CACHE:
        return CACHE[k]
    out: set[str] = set()
    try:
        with urllib.request.urlopen(
                f"https://pypi.org/pypi/{name}/json", timeout=timeout) as fh:
            data = json.load(fh)
        for spec in (data.get("info", {}).get("requires_dist") or []):
            # skip extras-conditional requirements: not installed by default
            if "extra ==" in spec:
                continue
            m = re.match(r"\s*([A-Za-z0-9][A-Za-z0-9._-]*)", spec)
            if m:
                out.add(norm(m.group(1)))
    except (urllib.error.URLError, OSError, ValueError, json.JSONDecodeError):
        pass
    CACHE[k] = out
    return out


def closure(names, depth: int = 3) -> set[str]:
    seen = {norm(n) for n in names}
    frontier = set(seen)
    for _ in range(depth):
        nxt: set[str] = set()
        for n in frontier:
            nxt |= pypi_requires(n)
        nxt -= seen
        if not nxt:
            break
        seen |= nxt
        frontier = nxt
    return seen


def check(patch_text: str, repo: pathlib.Path, dep: str,
          before=None, after=None, use_metadata: bool = False,
          gold_patch: str | None = None) -> dict:
    target = norm(dep)
    mode = "observed"
    if before is None or after is None:
        mode = "metadata" if use_metadata else "declared"
        paths = manifest_paths(patch_text)
        if not paths:
            return dict(**{"pass": False}, reason="no manifest edit in the patch",
                        evidence=dict(mode=mode))
        before, after, unapplied = set(), set(), []
        for p in paths:
            b, a = declared_before_after(patch_text, repo, p, gold_patch)
            before |= b
            if a is None:
                unapplied.append(p)
            else:
                after |= a
        if unapplied:
            return dict(**{"pass": False},
                        reason="candidate manifest edit could not be applied: "
                               + ", ".join(unapplied),
                        evidence=dict(mode=mode, unapplied=unapplied))
        if mode == "metadata":
            before, after = closure(before), closure(after)

    before = {norm(x) for x in before} - IGNORE
    after = {norm(x) for x in after} - IGNORE

    if gold_patch and target not in before:
        # The package is not in the baseline at all, usually because it is a
        # build-time requirement that IGNORE strips (wheel, setuptools, build).
        # There is genuinely nothing to remove, which is not the candidate's
        # fault: returning "fail" here charged the grader six false rejections
        # on removals that were correct by construction.
        return dict(**{"pass": None},
                    reason=f"{dep} is not in the comparable dependency set "
                           "(build-time requirement or absent from the gold manifest); "
                           "this gate cannot speak",
                    evidence=dict(mode=mode, n_before=len(before), n_after=len(after)))
    still_present = target in after
    allowed = before - {target}
    added = sorted(after - allowed)

    ok = not added and not still_present
    if still_present:
        reason = f"{dep} is still in the resulting set"
    elif added:
        reason = (f"closure grew by {len(added)} package(s) not previously present: "
                  + ", ".join(added[:6]))
    else:
        reason = (f"resulting set is a subset of the original minus {dep} "
                  f"({len(after)} <= {len(allowed)} packages)")

    return dict(**{"pass": ok}, reason=reason,
                evidence=dict(mode=mode, added=added, removed=sorted(allowed - after),
                              target_still_present=still_present,
                              n_before=len(before), n_after=len(after)))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("patch")
    ap.add_argument("--dep", required=True)
    ap.add_argument("--repo", default=".")
    ap.add_argument("--before", default=None)
    ap.add_argument("--after", default=None)
    ap.add_argument("--metadata", action="store_true",
                    help="resolve requirement closures from PyPI metadata")
    ap.add_argument("--json", default=None)
    a = ap.parse_args()
    b = set(a.before.split(",")) if a.before else None
    f = set(a.after.split(",")) if a.after else None
    res = check(pathlib.Path(a.patch).read_text(errors="ignore"),
                pathlib.Path(a.repo), a.dep, b, f, a.metadata)
    print(("PASS " if res["pass"] else "FAIL ") + res["reason"])
    print(f"  mode: {res['evidence']['mode']}")
    if a.json:
        pathlib.Path(a.json).write_text(json.dumps(res, indent=1, default=str))
    sys.exit(0 if res["pass"] else 1)


if __name__ == "__main__":
    main()
