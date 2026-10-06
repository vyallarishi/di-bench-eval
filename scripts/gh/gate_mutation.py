#!/usr/bin/env python3
"""G4c: how much of the replacement does the oracle actually constrain?

G2 says the tests pass. G4a says the replacement reproduces the library's
recorded values. Neither answers the question a reviewer will ask: *would the
tests have noticed if the replacement were wrong?*

Extreme mutation answers it. For each function the candidate added or modified,
replace its body with a type-appropriate constant and re-run the tests. If they
still pass, nothing in the oracle constrains that function: it is
*pseudo-tested*, in the sense of Vera-Perez et al.'s Descartes, and whatever
G2 reported about it was luck rather than evidence.

This is Descartes applied to the patch rather than to the project, which is the
useful direction here: we do not care how well the project is tested in
general, only whether the specific code that replaced the library is pinned
down by anything.

The output is a fraction, not a pass/fail, and that is deliberate. A removal
whose replacement is entirely pseudo-tested has not been verified by the test
suite no matter what G2 says, so the grade should carry that confidence rather
than hide it. `check` therefore returns `pseudo_tested_fraction` alongside a
`pass` that is only False when *every* added function is pseudo-tested -- the
case where the suite constrains nothing at all.

usage:
  gate_mutation.py --patch P --repo DIR --test-cmd "pytest -q" [--json out.json]
or as a library: check(patch_text, repo, run_tests) -> {...}
"""
from __future__ import annotations

import argparse
import ast
import json
import pathlib
import re
import shutil
import subprocess
import sys
import tempfile

# Body a function is replaced with, by what its annotation or observed returns
# suggest. The constant must be type-plausible so the mutant fails for the
# right reason (behaviour) rather than the wrong one (TypeError on arrival).
CONSTANT_FOR = {
    "str": '""', "bytes": 'b""', "int": "0", "float": "0.0",
    "bool": "False", "list": "[]", "dict": "{}", "set": "set()",
    "tuple": "()", "None": "None",
}


def added_or_modified_files(patch: str) -> dict[str, list[str]]:
    """path -> added lines, for Python files the patch writes."""
    out: dict[str, list[str]] = {}
    cur = None
    for line in patch.splitlines():
        if line.startswith("diff --git"):
            m = re.search(r" b/(.+)$", line)
            cur = m.group(1) if m else None
            if cur and cur.endswith(".py"):
                out.setdefault(cur, [])
            else:
                cur = None
        elif cur and line.startswith("+") and not line.startswith("+++"):
            out[cur].append(line[1:])
    return out


def _is_test(path: str) -> bool:
    return bool(re.search(r"(^|/)(tests?|testing)/|(^|/)test_|_test\.py$|conftest\.py$", path))


def candidate_functions(repo: pathlib.Path, patch: str) -> list[dict]:
    """Functions the candidate introduced, located in the patched tree.

    A function counts when its name appears in the patch's added lines for a
    non-test Python file and it exists in the file now. Test files are excluded:
    mutating a test is G7's concern, not a measure of what the oracle pins down.
    """
    out = []
    for path, added in added_or_modified_files(patch).items():
        if _is_test(path):
            continue
        f = repo / path
        if not f.exists():
            continue
        names = set()
        for line in added:
            m = re.match(r"\s*(?:async\s+)?def\s+([A-Za-z_]\w*)\s*\(", line)
            if m:
                names.add(m.group(1))
        if not names:
            continue
        try:
            tree = ast.parse(f.read_text(errors="ignore"))
        except SyntaxError:
            continue
        for node in ast.walk(tree):
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)) and node.name in names:
                if not node.body:
                    continue
                # a function that is already trivial cannot be mutated further;
                # it is reported separately rather than counted as pseudo-tested
                body = [b for b in node.body
                        if not (isinstance(b, ast.Expr) and isinstance(b.value, ast.Constant))]
                trivial = (not body or (len(body) == 1 and isinstance(
                    body[0], (ast.Pass, ast.Ellipsis if hasattr(ast, "Ellipsis") else ast.Pass))))
                out.append(dict(path=path, name=node.name, lineno=node.lineno,
                                end_lineno=getattr(node, "end_lineno", node.lineno),
                                col=node.col_offset, returns=_ret_hint(node),
                                already_trivial=trivial))
    return out


def _ret_hint(node) -> str:
    """Best guess at a type-plausible constant for this function's return."""
    ann = getattr(node, "returns", None)
    if ann is not None:
        txt = ast.unparse(ann) if hasattr(ast, "unparse") else ""
        for k in CONSTANT_FOR:
            if k in txt:
                return k
    # otherwise look at what it actually returns
    kinds = set()
    for n in ast.walk(node):
        if isinstance(n, ast.Return) and n.value is not None:
            v = n.value
            if isinstance(v, ast.Constant):
                kinds.add(type(v.value).__name__)
            elif isinstance(v, (ast.List, ast.ListComp)):
                kinds.add("list")
            elif isinstance(v, (ast.Dict, ast.DictComp)):
                kinds.add("dict")
            elif isinstance(v, (ast.Set, ast.SetComp)):
                kinds.add("set")
            elif isinstance(v, ast.Tuple):
                kinds.add("tuple")
            elif isinstance(v, ast.JoinedStr):
                kinds.add("str")
    for k in ("str", "int", "float", "bool", "list", "dict", "set", "tuple"):
        if k in kinds:
            return k
    return "None"


def mutate_source(text: str, fn: dict) -> str | None:
    """Replace one function's body with a constant return, preserving signature."""
    lines = text.splitlines(keepends=True)
    start, end = fn["lineno"] - 1, fn["end_lineno"]
    if start >= len(lines):
        return None
    # find the signature's end: the line whose bracket depth returns to zero
    depth, sig_end = 0, None
    for i in range(start, min(end, len(lines))):
        for ch in lines[i]:
            if ch in "([{":
                depth += 1
            elif ch in ")]}":
                depth -= 1
        if lines[i].rstrip().endswith(":") and depth <= 0:
            sig_end = i
            break
    if sig_end is None:
        return None
    indent = " " * (fn["col"] + 4)
    const = CONSTANT_FOR.get(fn["returns"], "None")
    body = f"{indent}return {const}\n"
    return "".join(lines[: sig_end + 1]) + body + "".join(lines[end:])


def check(patch_text: str, repo: pathlib.Path, run_tests, limit: int = 25) -> dict:
    """run_tests(repo) -> bool; called once per mutant on a scratch copy."""
    fns = candidate_functions(repo, patch_text)
    mutable = [f for f in fns if not f["already_trivial"]][:limit]
    results = []
    for fn in mutable:
        src = (repo / fn["path"]).read_text(errors="ignore")
        mutated = mutate_source(src, fn)
        if mutated is None or mutated == src:
            results.append(dict(**fn, outcome="could not mutate"))
            continue
        with tempfile.TemporaryDirectory() as td:
            work = pathlib.Path(td) / "repo"
            shutil.copytree(repo, work, symlinks=True,
                            ignore=shutil.ignore_patterns(".git", "__pycache__"))
            (work / fn["path"]).write_text(mutated)
            survived = run_tests(work)
        results.append(dict(**fn, outcome="pseudo-tested" if survived else "killed"))

    killed = sum(1 for r in results if r["outcome"] == "killed")
    pseudo = sum(1 for r in results if r["outcome"] == "pseudo-tested")
    scored = killed + pseudo
    frac = (pseudo / scored) if scored else None
    trivial = [f for f in fns if f["already_trivial"]]

    if scored == 0:
        reason = ("no added function could be mutated, so the suite's hold on the "
                  "replacement is unmeasured")
        ok = True
    elif pseudo == scored:
        reason = (f"all {scored} added function(s) are pseudo-tested: the suite does not "
                  "constrain the replacement at all")
        ok = False
    else:
        reason = (f"{pseudo} of {scored} added function(s) pseudo-tested "
                  f"({frac:.0%}); {killed} are constrained by the suite")
        ok = True

    return dict(**{"pass": ok}, reason=reason,
                evidence=dict(pseudo_tested_fraction=frac, killed=killed,
                              pseudo_tested=pseudo, scored=scored,
                              already_trivial=len(trivial),
                              functions=results))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--patch", required=True)
    ap.add_argument("--repo", required=True)
    ap.add_argument("--test-cmd", default="pytest -q -p no:cacheprovider")
    ap.add_argument("--timeout", type=int, default=600)
    ap.add_argument("--json", default=None)
    a = ap.parse_args()

    def run_tests(work: pathlib.Path) -> bool:
        try:
            r = subprocess.run(a.test_cmd, shell=True, cwd=work, capture_output=True,
                               text=True, timeout=a.timeout)
            return r.returncode == 0
        except subprocess.TimeoutExpired:
            return False

    res = check(pathlib.Path(a.patch).read_text(errors="ignore"),
                pathlib.Path(a.repo), run_tests)
    print(("PASS " if res["pass"] else "FAIL ") + res["reason"])
    for f in res["evidence"]["functions"]:
        print(f"  {f['path']}:{f['lineno']} {f['name']} -> {f['outcome']}")
    if a.json:
        pathlib.Path(a.json).write_text(json.dumps(res, indent=1, default=str))
    sys.exit(0 if res["pass"] else 1)


if __name__ == "__main__":
    main()
