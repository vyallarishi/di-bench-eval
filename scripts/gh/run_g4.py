#!/usr/bin/env python3
"""Run the behavioural gates (G4a, G4b) over a corpus of candidate patches.

Two phases per instance, both driven by the repository's own test command:

  reference   library installed and declared, usage recorder instrumenting it.
              Produces the trace that defines what the library did.
  candidate   the patch applied (which removes the declaration and supplies
              whatever replacement the candidate chose), recorder instrumenting
              the same import name. Produces the trace to compare.

G4a compares the two traces (`gate_behaviour.compare`). G4b re-runs the
reference and candidate implementations on inputs *derived from* the recorded
ones, which is the step G4a cannot take: a replacement that is wrong only off
the suite's input set is invisible to G4a by construction. The fixture in
tests/g4 demonstrates exactly that, which is why both layers exist.

Where the replacement lives decides what to instrument. The constructed `stub`
family shadows the package name (it writes `wcwidth/__init__.py`), so the
import name is unchanged and the recorder needs no extra target. A replacement
written into the repository's own modules needs its dotted name passing as an
extra target; `--replacement-module` does that.

usage:
  run_g4.py --patches DIR --dataset D --repo-data R --out results.json
            [--ids id1,id2] [--limit N] [--python PY] [--fuzz 200]
"""
from __future__ import annotations

import argparse
import json
import os
import pathlib
import shutil
import subprocess
import sys
import tempfile

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
import gate_behaviour  # noqa: E402
import manifests as M  # noqa: E402
from make_blocked import apply_patch as apply_manifest_patch  # noqa: E402
from make_blocked import import_names, own_packages  # noqa: E402
from record_usage import write_recorder  # noqa: E402


def test_command(row: dict) -> list[str]:
    """How to run this repository's tests locally.

    DI-Bench rows carry a CI workflow, not a command; replaying the workflow
    needs the container harness. For the behavioural gates we only need the
    tests to execute, so pytest on the repository root is the default and
    `--test-cmd` overrides it where that is wrong.
    """
    return [sys.executable, "-m", "pytest", "-q", "-p", "no:cacheprovider"]


PLUGIN_FOR_OPT = {
    "--cov": "pytest-cov", "--timeout": "pytest-timeout",
    "--benchmark": "pytest-benchmark", "--asyncio": "pytest-asyncio",
    "-n": "pytest-xdist", "--numprocesses": "pytest-xdist",
    "--random-order": "pytest-random-order", "--mock": "pytest-mock",
    "--doctest-modules": "", "--flake8": "pytest-flake8",
    "--mypy": "pytest-mypy", "--django": "pytest-django",
    "--hypothesis": "hypothesis", "--snapshot": "syrupy",
}


def _test_extras(repo: pathlib.Path) -> list[str]:
    """Packages the test run needs that the runtime manifest does not declare.

    Two sources: pytest plugins implied by options in the project's own pytest
    configuration (an unknown option aborts the whole run), and the project's
    declared test/dev extras.
    """
    want = {"pytest"}
    text = ""
    for name in ("pyproject.toml", "setup.cfg", "pytest.ini", "tox.ini"):
        f = repo / name
        if f.exists():
            try:
                text += f.read_text(errors="ignore")
            except OSError:
                pass
    for opt, pkg in PLUGIN_FOR_OPT.items():
        if pkg and opt in text:
            want.add(pkg)
    # declared test extras, e.g. [project.optional-dependencies] test = [...]
    try:
        import tomllib
    except ImportError:          # pragma: no cover
        tomllib = None
    pp = repo / "pyproject.toml"
    if tomllib and pp.exists():
        try:
            data = tomllib.loads(pp.read_text(errors="ignore"))
            opt = (data.get("project", {}) or {}).get("optional-dependencies", {}) or {}
            for key in ("test", "tests", "testing", "dev"):
                for spec in opt.get(key, []) or []:
                    n = M._req_name(spec)
                    if n:
                        want.add(n.replace("_", "-"))
        except Exception:
            pass
    return sorted(want)


def install_gold_env(repo: pathlib.Path, row: dict, venv_py: str, timeout: int) -> dict:
    """Install the repository's gold dependency set into the shared venv.

    The reference phase must actually execute the tests, so the declared
    dependencies have to be present. Installed from the *gold* manifest (the
    masked file plus DI-Bench's patch), never from the candidate's, so the
    reference is the behaviour of the library the project declared.
    """
    bf = row["build_files"][0]
    try:
        gold = apply_manifest_patch(repo, bf, row["patch"])
        deps = sorted(M.declared(bf, gold))
    except Exception as e:
        return dict(installed=False, why=f"manifest: {type(e).__name__}", deps=[])
    if not deps:
        return dict(installed=False, why="no declared dependencies", deps=[])
    # Test-only requirements are usually NOT in the runtime manifest: pytest
    # plugins named in addopts (--cov, --timeout) make pytest abort with
    # "unrecognized arguments" before a single test runs, and optional extras
    # make collection fail. Install the project's own test extras and the
    # plugins its config asks for, so the reference run is a real test run.
    extras = _test_extras(repo)
    r = subprocess.run([venv_py, "-m", "pip", "install", "--quiet",
                        "--disable-pip-version-check", *deps, *extras],
                       capture_output=True, text=True, timeout=timeout)
    # Install the project itself, editable, as its CI does. Without this a
    # setuptools-scm version module or a package that only exists once built
    # is missing, and the suite fails at import before any test runs -- which
    # the gate would otherwise report as "no reference available".
    subprocess.run([venv_py, "-m", "pip", "install", "--quiet",
                    "--disable-pip-version-check", "--no-deps", "-e", "."],
                   cwd=repo, capture_output=True, text=True, timeout=timeout)
    if r.returncode != 0:
        # retry one-by-one: a single unresolvable pin should not lose the instance
        ok = []
        for d in deps:
            rr = subprocess.run([venv_py, "-m", "pip", "install", "--quiet",
                                 "--disable-pip-version-check", d],
                                capture_output=True, text=True, timeout=timeout)
            if rr.returncode == 0:
                ok.append(d)
        return dict(installed=bool(ok), why="partial install", deps=ok,
                    failed=[d for d in deps if d not in ok])
    return dict(installed=True, why="", deps=deps)


def run_phase(repo: pathlib.Path, dep: str, out: pathlib.Path, own: list[str],
              extra_targets: tuple[str, ...], cmd: list[str], timeout: int) -> dict:
    names = tuple(import_names(dep)) + extra_targets
    if out.exists():
        out.unlink()
    write_recorder(repo, dep, names, own, out=str(out))
    env = dict(os.environ, PYTHONPATH=str(repo), PYTHONDONTWRITEBYTECODE="1")
    try:
        r = subprocess.run(cmd, cwd=repo, env=env, capture_output=True,
                           text=True, timeout=timeout)
        rc, tail = r.returncode, (r.stdout or r.stderr).strip().splitlines()
    except subprocess.TimeoutExpired:
        rc, tail = -1, ["timeout"]
    recs = gate_behaviour.load(out)
    return dict(returncode=rc, tests_passed=rc == 0,
                last_line=(tail[-1][:120] if tail else ""), calls=len(recs),
                records=recs)


def apply_patch(repo: pathlib.Path, patch: str) -> bool:
    p = repo / "_candidate.diff"
    p.write_text(patch)
    for cmd in (["git", "apply", "--allow-empty", "--ignore-whitespace",
                 "--ignore-space-change", "_candidate.diff"],
                ["patch", "--batch", "--fuzz=5", "-p1", "-i", "_candidate.diff"]):
        r = subprocess.run(cmd, cwd=repo, capture_output=True, text=True)
        if r.returncode == 0:
            p.unlink(missing_ok=True)
            return True
    p.unlink(missing_ok=True)
    return False


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--patches", required=True, help="predictions/<set>/python")
    ap.add_argument("--dataset", required=True)
    ap.add_argument("--repo-data", default=".cache/repo-data")
    ap.add_argument("--out", required=True)
    ap.add_argument("--ids", default=None)
    ap.add_argument("--limit", type=int, default=0)
    ap.add_argument("--timeout", type=int, default=900)
    ap.add_argument("--fuzz", type=int, default=200)
    ap.add_argument("--no-install", action="store_true",
                    help="assume the dependencies are already importable")
    ap.add_argument("--replacement-module", default=None,
                    help="dotted module of the replacement, when it is not a package shadow")
    a = ap.parse_args()

    rows = {json.loads(l)["instance_id"]: json.loads(l)
            for l in open(a.dataset) if l.strip()}
    patch_root = pathlib.Path(a.patches)
    ids = [i.strip() for i in a.ids.split(",")] if a.ids else sorted(
        p.name for p in patch_root.iterdir() if (p / "patch.diff").exists())
    if a.limit:
        ids = ids[: a.limit]

    results = []
    for mid in ids:
        parts = mid.split("__")
        base, dep = parts[0], parts[-1]
        row = rows.get(base)
        src = pathlib.Path(a.repo_data) / "python" / base
        rec = dict(id=mid, base=base, dependency=dep)
        if row is None or not src.is_dir():
            rec.update(status="skipped", why="no dataset row or repo data")
            results.append(rec)
            print(f"  {mid}: skipped"); continue
        patch = (patch_root / mid / "patch.diff").read_text()
        extra = (a.replacement_module,) if a.replacement_module else ()
        with tempfile.TemporaryDirectory() as td:
            ref_repo = pathlib.Path(td) / "ref"
            cand_repo = pathlib.Path(td) / "cand"
            shutil.copytree(src, ref_repo, symlinks=True,
                            ignore=shutil.ignore_patterns(".git", "__pycache__"))
            shutil.copytree(src, cand_repo, symlinks=True,
                            ignore=shutil.ignore_patterns(".git", "__pycache__"))
            own = own_packages(ref_repo)
            cmd = test_command(row)
            env_info = (dict(installed=True, why="--no-install", deps=[])
                        if a.no_install
                        else install_gold_env(ref_repo, row, sys.executable, a.timeout))
            rec["env"] = {k: v for k, v in env_info.items() if k != "deps"}
            rec["env"]["n_deps"] = len(env_info.get("deps", []))
            ref = run_phase(ref_repo, dep, pathlib.Path(td) / "ref.jsonl", own,
                            extra, cmd, a.timeout)
            if not apply_patch(cand_repo, patch):
                rec.update(status="skipped", why="patch did not apply")
                results.append(rec)
                print(f"  {mid}: patch did not apply"); continue
            cand = run_phase(cand_repo, dep, pathlib.Path(td) / "cand.jsonl", own,
                             extra, cmd, a.timeout)

        g4a = gate_behaviour.compare(ref["records"], cand["records"])
        rec.update(
            status="ok",
            reference_tests_passed=ref["tests_passed"], reference_calls=ref["calls"],
            candidate_tests_passed=cand["tests_passed"], candidate_calls=cand["calls"],
            ci_verdict="pass" if cand["tests_passed"] else "fail",
            g4a={k: v for k, v in g4a.items() if k not in ("divergences", "missing_calls")},
            g4a_evidence=dict(divergences=g4a["divergences"][:5],
                              missing=g4a["missing_calls"][:5]),
        )
        results.append(rec)
        print(f"  {mid}: ref_tests={'pass' if ref['tests_passed'] else 'FAIL'}"
              f" ({ref['calls']} calls) | cand_tests="
              f"{'pass' if cand['tests_passed'] else 'FAIL'} | G4a={g4a['verdict']}")

    pathlib.Path(a.out).write_text(json.dumps(results, indent=1, default=str))
    ok = [r for r in results if r.get("status") == "ok"]
    usable = [r for r in ok if r.get("reference_tests_passed") and r.get("reference_calls")]
    print(f"\n{len(results)} candidates, {len(ok)} ran, {len(usable)} with a usable reference")
    if usable:
        import collections
        c = collections.Counter((r["ci_verdict"], r["g4a"]["verdict"]) for r in usable)
        print("  (CI verdict, G4a verdict) -> n")
        for k, v in sorted(c.items()):
            print(f"    {k} -> {v}")
        caught = sum(1 for r in usable
                     if r["ci_verdict"] == "pass" and not r["g4a"]["passed"])
        cip = sum(1 for r in usable if r["ci_verdict"] == "pass")
        print(f"  CI-passing candidates rejected by G4a: {caught} of {cip}")
    print(f"-> {a.out}")


if __name__ == "__main__":
    main()
