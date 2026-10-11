#!/usr/bin/env python3
"""Run mutation analysis of a reference removal against the tests and the gate.

For one reference whose replacement the recorder can observe:

  1. build the environment once (gold dependencies, editable install), record
     the reference trace from the unmutated reference -- this is the oracle
  2. for each mutant of the replacement module: run the project's own suite,
     then record the mutant's trace at the same sites and compare
  3. report the cross-tab, and the conditional that matters: of the mutants the
     suite does not kill, how many does the gate catch

The reference itself is run first as a control. If the unmutated reference is
not accepted in this environment, the pair is reported as not runnable rather
than producing numbers nobody should trust.

usage:
  mutation_g4.py --reference DIR --instance ID --dataset D --module M
                 [--kind new|modified] [--python PY] [--test-args ...]
                 [--limit N] [--out out.json] [--keep DIR]
"""
from __future__ import annotations

import argparse
import ast
import collections
import json
import pathlib
import shutil
import subprocess
import sys
import tempfile

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
import gate_behaviour  # noqa: E402
from g4b_variants import added_files  # noqa: E402
from make_blocked import apply_patch, import_names, own_packages  # noqa: E402
from mutate_reference import mutants  # noqa: E402
from record_usage import site_functions, usage_functions, write_recorder  # noqa: E402
from run_g4 import install_gold_env, make_venv  # noqa: E402


def reference_files(ref_dir: pathlib.Path) -> dict:
    """path -> new contents, for every file the reference patch writes."""
    return added_files((ref_dir / "patch.diff").read_text(errors="replace"))


def apply_reference(repo: pathlib.Path, work: pathlib.Path, ref_dir: pathlib.Path,
                    row: dict) -> None:
    """A checkout with the reference applied: masked tree, gold manifest, new files."""
    shutil.copytree(repo, work, dirs_exist_ok=True,
                    ignore=shutil.ignore_patterns(".git", "__pycache__", ".pytest_cache"))
    bf = row["build_files"][0]
    (work / bf).write_text(apply_patch(repo, bf, row["patch"]))
    p = subprocess.run(["git", "apply", "--reject", "--whitespace=nowarn",
                        str((ref_dir / "patch.diff").resolve())],
                       cwd=work, capture_output=True, text=True)
    if p.returncode != 0:
        # the manifest hunk conflicts with the gold text we just wrote; apply
        # only the code hunks, which is what the mutation study needs
        for rel, text in reference_files(ref_dir).items():
            if rel != bf:
                (work / rel).parent.mkdir(parents=True, exist_ok=True)
                (work / rel).write_text(text)


def run_suite(work: pathlib.Path, py: str, test_args: list[str], timeout: int) -> tuple:
    cmd = [py, "-m", "pytest", "-q", "-p", "no:cacheprovider"] + list(test_args)
    try:
        p = subprocess.run(cmd, cwd=work, capture_output=True, text=True, timeout=timeout)
    except subprocess.TimeoutExpired:
        return None, "timeout"
    tail = (p.stdout or p.stderr).strip().splitlines()
    return p.returncode == 0, (tail[-1][:90] if tail else "")


def record(work: pathlib.Path, dep: str, targets, own, out: pathlib.Path,
           py: str, test_args: list[str], timeout: int, site_exclude=(),
           usage=None) -> tuple:
    for name in ("sitecustomize.py", "conftest.py"):
        f = work / name
        if f.exists() and "UnpinBench" in f.read_text(errors="ignore"):
            f.unlink()
    if out.exists():
        out.unlink()
    write_recorder(work, dep, targets, own, out=str(out),
                   site_exclude=site_exclude, usage=usage)
    ok, line = run_suite(work, py, test_args, timeout)
    calls = gate_behaviour.load(out) if out.exists() else []
    return ok, line, calls


HERE = pathlib.Path(__file__).resolve().parent


def _canary(src: str) -> str | None:
    """The replacement with every public function raising on entry.

    The point is to establish that the suite can fail at all. An earlier
    version replaced the first `return` textually, which in a function whose
    first return sits on a rarely-taken early-exit path changes nothing the
    tests reach -- so the suite passed, and the canary wrongly condemned a
    perfectly good subject. Raising on entry leaves no doubt: if the suite
    still passes, it is not exercising the replacement.
    """
    try:
        tree = ast.parse(src)
    except SyntaxError:
        return None
    raise_stmt = ast.parse("raise RuntimeError('unpinbench canary')").body[0]
    n = 0
    for node in tree.body:
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)) \
                and not node.name.startswith("_"):
            node.body = [raise_stmt]
            n += 1
        elif isinstance(node, ast.ClassDef):
            for sub in node.body:
                if isinstance(sub, (ast.FunctionDef, ast.AsyncFunctionDef)) \
                        and not sub.name.startswith("_"):
                    sub.body = [raise_stmt]
                    n += 1
    if not n:
        return None
    ast.fix_missing_locations(tree)
    try:
        return ast.unparse(tree)
    except Exception:
        return None


def is_equivalent(original: str, mutant: str, ref_calls: list, py: str,
                  base: pathlib.Path) -> bool:
    """True when no generated input separates the mutant from the original."""
    d = pathlib.Path(tempfile.mkdtemp(dir=base))
    try:
        (d / "a.py").write_text(original)
        (d / "b.py").write_text(mutant)
        (d / "calls.json").write_text(json.dumps(ref_calls[:200], default=str))
        r = subprocess.run([py, str(HERE / "equiv_probe.py"), str(d / "a.py"),
                            str(d / "b.py"), str(d / "calls.json")],
                           capture_output=True, text=True, timeout=240)
        return "EQUIVALENT" in (r.stdout or "")
    except Exception:
        return False
    finally:
        shutil.rmtree(d, ignore_errors=True)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--reference", required=True)
    ap.add_argument("--instance", required=True)
    ap.add_argument("--dependency", required=True)
    ap.add_argument("--dataset", nargs="+", required=True)
    ap.add_argument("--repo-data", default=".cache/repo-data")
    ap.add_argument("--module", required=True, help="replacement module path in the repo")
    ap.add_argument("--kind", choices=["new", "modified"], default="new")
    ap.add_argument("--module-name", default=None, help="dotted name, for a new module")
    ap.add_argument("--python", default=None)
    ap.add_argument("--test-args", nargs="*", default=[])
    ap.add_argument("--extra-deps", nargs="*", default=[],
                    help="test-only packages the suite needs (pytest-mock, …)")
    ap.add_argument("--limit", type=int, default=0)
    ap.add_argument("--timeout", type=int, default=900)
    ap.add_argument("--out", default=None)
    a = ap.parse_args()

    rows = {}
    for d in a.dataset:
        for line in open(d):
            if line.strip():
                r = json.loads(line)
                rows.setdefault(r["instance_id"], r)
    row = rows[a.instance]
    repo = pathlib.Path(a.repo_data) / "python" / a.instance
    ref_dir = pathlib.Path(a.reference)

    base = pathlib.Path(tempfile.mkdtemp(prefix="mut-"))
    work = base / "repo"
    apply_reference(repo, work, ref_dir, row)
    mod = work / a.module
    if not mod.exists():
        sys.exit(f"replacement module not found after applying the reference: {a.module}")
    original = mod.read_text()

    py = a.python or sys.executable
    venv_py = make_venv(base / "venv")
    if venv_py:
        # Pass the dependency list explicitly. install_gold_env derives it by
        # applying DI-Bench's patch to the masked manifest, but our work tree
        # already carries the gold manifest (apply_reference wrote it), so that
        # patch no longer applies and the list comes back empty -- the suite
        # then fails for want of its dependencies, not for anything about the
        # reference. The removed package is installed too: the control run must
        # record what the library did.
        import manifests as _M
        deps = sorted(_M.declared(row["build_files"][0],
                                  (work / row["build_files"][0]).read_text()))
        info = install_gold_env(work, row, venv_py, a.timeout, deps=deps)
        # The runner itself must be present. install_gold_env adds the
        # project's own test extras, but a project whose pytest lives in a dev
        # extra it does not detect leaves the venv without pytest, and the
        # control then fails for want of a test runner rather than for any
        # reason about the reference.
        # The runner and the plugins the suite's fixtures need. A project whose
        # tests take a `mocker` fixture errors on two tests without
        # pytest-mock, and the control then reads FAIL for want of a plugin
        # rather than for anything about the reference. --extra-deps lets a
        # reference name what its NOTES record.
        subprocess.run([venv_py, "-m", "pip", "install", "--quiet",
                        "--disable-pip-version-check", "pytest", *a.extra_deps],
                       capture_output=True, text=True, timeout=a.timeout)
        print(f"env: {len(info.get('deps') or [])} declared dependencies installed"
              + (f" ({info.get('why')})" if info.get("why") else ""))
        py = venv_py

    # targets: the library boundary plus the replacement, so the same sites are
    # observed in both phases (see record_usage.write_recorder)
    targets = list(import_names(a.dependency))
    if a.kind == "new" and a.module_name:
        targets.append(a.module_name)
    own = own_packages(work)
    site_exclude = [a.module] if a.kind == "modified" else []

    # --- the oracle: the unmutated reference.
    #
    # Two passes. The first records at the library boundary and is also how the
    # usage sites are discovered; the second instruments those sites, which is
    # the only level at which a replacement inlined into an existing module is
    # observable at all. Without the second pass a `modified` reference records
    # nothing after the library is gone, and the study silently has no oracle.
    # Usage sites come from a static scan for the project's own functions that
    # use the library (run_g4 does the same), then are widened by whatever the
    # first run actually records. A replacement inlined into an existing module
    # is observable at this level and at no other, so getting this wrong leaves
    # the study with no oracle and nothing to say.
    names = list(import_names(a.dependency))
    usage = usage_functions(work, names)
    ok, line, ref_calls = record(work, a.dependency, targets, own,
                                 base / "ref.jsonl", py, a.test_args, a.timeout,
                                 site_exclude, usage=usage)
    fuller = usage_functions(work, names, ref_calls)
    if any(set(fuller.get(k, [])) - set(usage.get(k, [])) for k in fuller):
        usage = {k: sorted(set(usage.get(k, [])) | set(fuller.get(k, [])))
                 for k in set(usage) | set(fuller)}
        ok, line, ref_calls = record(work, a.dependency, targets, own,
                                     base / "ref.jsonl", py, a.test_args,
                                     a.timeout, site_exclude, usage=usage)
    lib = sum(1 for r in ref_calls if r.get("level") != "usage")
    use = len(ref_calls) - lib
    print(f"control (unmutated reference): tests={'pass' if ok else 'FAIL'} "
          f"({line}); oracle = {lib} library + {use} usage calls "
          f"over {len(usage)} instrumented functions")
    if not ok or not ref_calls:
        print("the control does not run here, so no mutant result would be trustworthy")
        if a.out:
            pathlib.Path(a.out).write_text(json.dumps(dict(
                instance=a.instance, dependency=a.dependency,
                status="control not runnable", control_tests=ok,
                control_calls=len(ref_calls), usage_sites=len(usage)), indent=1))
        sys.exit(0)

    # Sanity: the suite must be able to fail. A vacuous assertion makes every
    # mutant "survive the tests" and the mutation score meaningless.
    # IAMActionHunter's only test asserts `content == expected_a or expected_b`,
    # which parses as `(content == expected_a) or expected_b` and is therefore
    # always truthy -- the test cannot fail, and the study must say so instead
    # of reporting a 0% kill rate as if it were about the gate.
    canary = _canary(original)
    if canary and canary != original:
        mod.write_text(canary)
        ok_c, line_c, _ = record(work, a.dependency, targets, own,
                                 base / "canary.jsonl", py, a.test_args,
                                 min(a.timeout, 300), site_exclude, usage=usage)
        mod.write_text(original)
        if ok_c:
            print("CONTROL IS VACUOUS: the suite still passes with every "
                  f"public function of the replacement raising ({line_c}). "
                  "The tests cannot detect a broken replacement here, so no "
                  "mutation score from this pair would be about the gate.")
            if a.out:
                pathlib.Path(a.out).write_text(json.dumps(dict(
                    instance=a.instance, dependency=a.dependency,
                    status="suite cannot fail (vacuous assertion)",
                    canary_line=line_c), indent=1))
            shutil.rmtree(base, ignore_errors=True)
            sys.exit(0)
        print(f"canary: the suite does detect a wholly broken replacement ({line_c})")

    ms = mutants(original, a.limit)
    print(f"{len(ms)} mutants to evaluate\n")
    results, tally = [], collections.Counter()
    for i, (kind, text, lineno) in enumerate(ms):
        mod.write_text(text)
        ok_m, line_m, cand = record(work, a.dependency, targets, own,
                                    base / "cand.jsonl", py, a.test_args,
                                    a.timeout, site_exclude, usage=usage)
        cmp_ = gate_behaviour.compare(ref_calls, cand)
        caught = cmp_["verdict"] in ("divergent", "missing")
        tests_killed = ok_m is False
        # An *equivalent* mutant changes the text and not the behaviour -- here,
        # perturbing a codepoint in a Unicode constant that this project's
        # inputs never contain. Nothing can catch it because there is nothing
        # to catch, and mutation analysis has excluded such mutants since
        # DeMillo et al. (1978). Decided by differential execution over the
        # recorded arguments and neighbours of them, not by inspection.
        equivalent = False
        if not tests_killed and not caught:
            equivalent = is_equivalent(original, text, ref_calls, py, base)
        cell = ("tests kill" if tests_killed else "tests pass") + " / " + \
               ("gate catches" if caught else
                "equivalent mutant (nothing to catch)" if equivalent else
                "gate silent" if cmp_["verdict"] == "identical" else
                f"gate {cmp_['verdict']}")
        tally[cell] += 1
        results.append(dict(mutant=f"m{i:04d}", kind=kind, line=lineno,
                            tests_pass=ok_m, tests_line=line_m,
                            gate=cmp_["verdict"], caught=caught, equivalent=equivalent,
                            divergent=cmp_["divergent"], missing=cmp_["missing"],
                            matched=cmp_["matched"], cand_calls=len(cand)))
        flag = "" if tests_killed else ("  <= TESTS MISS" + (
            ", GATE CATCHES" if caught else
            ", equivalent" if equivalent else ", GATE SILENT"))
        print(f"  m{i:04d} {kind:18s} L{lineno:<4d} tests={'pass' if ok_m else 'kill'} "
              f"gate={cmp_['verdict']:10s}{flag}")
    mod.write_text(original)

    survived = [r for r in results if r["tests_pass"]]
    equiv = [r for r in survived if r.get("equivalent")]
    live = [r for r in survived if not r.get("equivalent")]
    caught = [r for r in live if r["caught"]]
    print(f"\n{len(results)} mutants: {len(results) - len(survived)} killed by the suite, "
          f"{len(survived)} survive it, {len(equiv)} of those equivalent "
          f"(no generated input separates them from the original)")
    if live:
        print(f"OF THE {len(live)} NON-EQUIVALENT SURVIVORS, THE GATE CATCHES "
              f"{len(caught)}/{len(live)} = {len(caught) / len(live):.0%}")
    print("\ncross-tab:")
    for k, n in tally.most_common():
        print(f"  {n:4d}  {k}")
    if a.out:
        pathlib.Path(a.out).write_text(json.dumps(dict(
            instance=a.instance, dependency=a.dependency, module=a.module,
            status="ok", control_calls=len(ref_calls),
            usage_sites=len(usage), mutants=len(results),
            killed_by_tests=len(results) - len(survived), survived=len(survived),
            equivalent=len(equiv), live=len(live), caught_by_gate=len(caught),
            rate=(len(caught) / len(live)) if live else None,
            cross_tab={k: v for k, v in tally.items()}, results=results), indent=1))
        print(f"-> {a.out}")
    shutil.rmtree(base, ignore_errors=True)


if __name__ == "__main__":
    main()
