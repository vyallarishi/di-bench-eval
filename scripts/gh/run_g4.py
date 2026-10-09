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

Where the replacement lives decides what the LIBRARY-BOUNDARY recorder can
see. The constructed `stub` family shadows the package name (it writes
`wcwidth/__init__.py`), so the import name is unchanged and the recorder needs
no extra target. A replacement written as a new module of the repository needs
its dotted name passing as an extra target for the candidate phase;
`--replacement-module` does that. A replacement inside a modified module, or
inlined at the call site, is not a callable the boundary recorder can wrap at
all; for those the USAGE-SITE level is what observes it: the project's own
functions that use the library (static scan plus the sites the reference run
recorded) are wrapped in both phases and compared by function and inputs.

usage:
  run_g4.py --patches DIR --dataset D --repo-data R --out results.json
            [--ids id1,id2] [--limit N] [--python PY] [--fuzz 200]
"""
from __future__ import annotations

import argparse
import json
import os
import pathlib
import re
import shutil
import subprocess
import sys
import tempfile

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
import gate_behaviour  # noqa: E402
import manifests as M  # noqa: E402
from make_blocked import apply_patch as apply_manifest_patch  # noqa: E402
from make_blocked import import_names, own_packages  # noqa: E402
from record_usage import site_functions, usage_functions, write_recorder  # noqa: E402


def test_command(row: dict, python: str | None = None,
                 repo: pathlib.Path | None = None) -> list[str]:
    """How to run this repository's tests locally.

    Bare pytest is wrong for a sizeable minority of these projects. aioclock
    drives its suite through `rye`/`make test`, omniduct through
    `hatch run tests`; running pytest directly fails at collection, and the
    gate then reports "gold baseline failed, not gradeable" for a repository
    whose CI is perfectly healthy. That is a harness limitation masquerading as
    a property of the instance, which is the failure mode this project keeps
    tripping over.

    We cannot replay the workflow itself without the container harness, so the
    rule is: look at what the workflow invokes, and translate the common cases
    into something runnable in a plain venv. Where the project funnels its
    suite through a tool we cannot reproduce faithfully, say so rather than
    silently fall back and record a failure.
    """
    py = python or sys.executable
    default = [py, "-m", "pytest", "-q", "-p", "no:cacheprovider"]
    if repo is None:
        return default
    # a Makefile target the workflow calls is usually a thin pytest wrapper
    mk = repo / "Makefile"
    if mk.exists():
        try:
            text = mk.read_text(errors="ignore")
        except OSError:
            text = ""
        m = re.search(r"^test:.*?\n((?:\t.*\n)+)", text, re.M)
        if m:
            for line in m.group(1).splitlines():
                cmd = line.strip().lstrip("@-")
                # strip the runner prefix; the venv already has the deps
                cmd = re.sub(r"^(rye run|poetry run|pdm run|hatch run|uv run)\s+", "", cmd)
                if cmd.startswith("pytest"):
                    return [py, "-m"] + cmd.split()
    return default


def unsupported_runner(repo: pathlib.Path) -> str | None:
    """Name the build tool when the suite cannot be reproduced in a plain venv."""
    for name, marker in (("tox", "tox.ini"), ("nox", "noxfile.py")):
        if (repo / marker).exists():
            return None            # these usually still have a runnable pytest
    return None


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


BASE_PYTHON = sys.executable


def make_venv(where: pathlib.Path, timeout: int = 300) -> str | None:
    """A fresh interpreter for one instance. Returns its python, or None.

    Instances must not share an environment. Projects here install themselves
    editable and register entry points, so a flake8 plugin left behind by one
    repository makes flake8 fail for the next, and an editable install whose
    source directory has since been deleted breaks imports outright. A shared
    venv accumulated 195 packages this way and the GOLD baseline of an
    untouched repository began failing for a reason that had nothing to do with
    it -- which the gate would have recorded as a behavioural result.
    """
    try:
        subprocess.run([BASE_PYTHON, "-m", "venv", str(where)],
                       capture_output=True, text=True, timeout=timeout)
    except subprocess.SubprocessError:
        return None
    py = where / "bin" / "python"
    return str(py) if py.exists() else None


def install_gold_env(repo: pathlib.Path, row: dict, venv_py: str, timeout: int,
                     deps: list[str] | None = None) -> dict:
    """Install the repository's gold dependency set into a fresh environment.

    The reference phase must actually execute the tests, so the declared
    dependencies have to be present. Installed from the *gold* manifest (the
    masked file plus DI-Bench's patch), never from the candidate's, so the
    reference is the behaviour of the library the project declared.
    """
    bf = row["build_files"][0]
    if deps is None:
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


KEEP = None


def run_phase(repo: pathlib.Path, dep: str, out: pathlib.Path, own: list[str],
              extra_targets: tuple[str, ...], cmd: list[str], timeout: int,
              usage: dict | None = None) -> dict:
    names = tuple(import_names(dep)) + extra_targets
    if out.exists():
        out.unlink()
    write_recorder(repo, dep, names, own, out=str(out), usage=usage)
    env = dict(os.environ, PYTHONPATH=str(repo), PYTHONDONTWRITEBYTECODE="1")
    try:
        r = subprocess.run(cmd, cwd=repo, env=env, capture_output=True,
                           text=True, timeout=timeout)
        rc, tail = r.returncode, (r.stdout or r.stderr).strip().splitlines()
        if KEEP:
            KEEP.mkdir(parents=True, exist_ok=True)
            (KEEP / (out.stem + ".stdout")).write_text(r.stdout or "")
            (KEEP / (out.stem + ".stderr")).write_text(r.stderr or "")
    except subprocess.TimeoutExpired:
        rc, tail = -1, ["timeout"]
    recs = gate_behaviour.load(out)
    # The two phases run in different checkouts; a value that embeds the
    # checkout path (a cwd, a file argument) must not differ for that reason.
    # Under the CI harness both roots are /project and this is a no-op.
    roots = sorted({str(repo), str(repo.resolve()), os.path.realpath(str(repo))}, key=len, reverse=True)
    txt = json.dumps(recs)
    for r_ in roots:
        txt = txt.replace(r_, "<repo>")
    recs = json.loads(txt)
    if KEEP and out.exists():
        import shutil
        shutil.copy(out, KEEP / out.name)
    return dict(returncode=rc, tests_passed=rc == 0,
                last_line=(tail[-1][:120] if tail else ""), calls=len(recs),
                library_calls=sum(1 for r in recs if r.get("level") != "usage"),
                usage_calls=sum(1 for r in recs if r.get("level") == "usage"),
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
    ap.add_argument("--keep", default=None,
                    help="directory to keep each phase's trace and console output in, for diagnosis")
    ap.add_argument("--replacement-module", default=None,
                    help="dotted module of a NEW replacement module, instrumented in the "
                         "candidate phase only (a modified module is observed at its usage sites)")
    ap.add_argument("--python", default=None,
                    help="interpreter to build the per-instance environments from "
                         "(default: this one); use the version the repository's CI runs")
    ap.add_argument("--test-command", default=None,
                    help="override the test command; '{py}' is the phase's interpreter, "
                         "e.g. '{py} -m pytest -q -p no:cacheprovider tests/unit_test'")
    a = ap.parse_args()
    global KEEP, BASE_PYTHON
    KEEP = pathlib.Path(a.keep) if a.keep else None
    if a.python:
        BASE_PYTHON = a.python

    rows = {json.loads(l)["instance_id"]: json.loads(l)
            for l in open(a.dataset) if l.strip()}
    patch_root = pathlib.Path(a.patches)
    ids = [i.strip() for i in a.ids.split(",")] if a.ids else sorted(
        p.name for p in patch_root.iterdir() if (p / "patch.diff").exists())
    if a.limit:
        ids = ids[: a.limit]

    # The reference phase depends only on (repository, dependency), so the
    # cheat families built on one pair share it. Recomputing it per candidate
    # meant 154 reference runs for 54 distinct pairs, each with a fresh venv
    # and a full dependency install -- about three times the necessary work.
    ref_cache: dict[tuple, dict] = {}
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
            ref_py = sys.executable if a.no_install else make_venv(pathlib.Path(td) / "venv-ref")
            cand_py = sys.executable if a.no_install else make_venv(pathlib.Path(td) / "venv-cand")
            if ref_py is None or cand_py is None:
                rec.update(status="skipped", why="could not create a virtual environment")
                results.append(rec)
                print(f"  {mid}: venv creation failed"); continue
            ck = (base, M.norm(dep))
            if ck in ref_cache:
                ref = ref_cache[ck]
                rec["env"] = dict(cached_from=ref_cache[ck]["_from"])
            else:
                env_info = (dict(installed=True, why="--no-install", deps=[])
                            if a.no_install
                            else install_gold_env(ref_repo, row, ref_py, a.timeout))
                rec["env"] = {k: v for k, v in env_info.items() if k != "deps"}
                rec["env"]["n_deps"] = len(env_info.get("deps", []))
                # Usage sites: the project functions that use the library,
                # from a static scan of the reference checkout. They are
                # wrapped in this run so one reference run records both
                # levels; if the recorded boundary sites then name a function
                # the scan missed (a dynamic import, an alias it could not
                # resolve), the reference is run once more with the union.
                names = import_names(dep)
                usage = usage_functions(ref_repo, names)
                ref_cmd = (a.test_command.format(py=ref_py).split() if a.test_command
                           else test_command(row, ref_py, ref_repo))
                ref = run_phase(ref_repo, dep, pathlib.Path(td) / "ref.jsonl", own,
                                (), ref_cmd, a.timeout, usage=usage)
                fuller = usage_functions(ref_repo, names, ref["records"])
                if any(set(fuller.get(k, [])) - set(usage.get(k, [])) for k in fuller):
                    usage = {k: sorted(set(usage.get(k, [])) | set(fuller.get(k, [])))
                             for k in set(usage) | set(fuller)}
                    ref = run_phase(ref_repo, dep, pathlib.Path(td) / "ref.jsonl", own,
                                    (), ref_cmd, a.timeout, usage=usage)
                    ref["reran_for_usage"] = True
                ref["_usage"] = usage
                ref["_site_function"] = site_functions(ref_repo, ref["records"])
                ref["_from"] = mid
                ref["_deps"] = env_info.get("deps", [])
                ref_cache[ck] = ref
                if KEEP:
                    KEEP.mkdir(parents=True, exist_ok=True)
                    (KEEP / f"{mid}.usage.json").write_text(json.dumps(
                        dict(usage=usage, site_function=ref["_site_function"]), indent=1))
            if not apply_patch(cand_repo, patch):
                rec.update(status="skipped", why="patch did not apply")
                results.append(rec)
                print(f"  {mid}: patch did not apply"); continue
            if not a.no_install:
                # The candidate has rewritten the manifest, so the gold patch
                # may no longer apply to it; install the dependency set the
                # reference phase resolved, which is the gold set by definition.
                install_gold_env(cand_repo, row, cand_py, a.timeout,
                                 deps=ref.get("_deps") or None)
            # The candidate manifest may no longer carry the test runner (a
            # reference that rewrites the manifest can drop a dev group); the
            # suite must still run, or "no calls" would read as a rejection.
            if subprocess.run([str(cand_py), "-c", "import pytest"], capture_output=True).returncode != 0:
                subprocess.run([str(cand_py), "-m", "pip", "install", "-q", "pytest"],
                               capture_output=True, timeout=a.timeout)
            cand_cmd = (a.test_command.format(py=cand_py).split() if a.test_command
                        else test_command(row, cand_py, cand_repo))
            cand = run_phase(cand_repo, dep, pathlib.Path(td) / "cand.jsonl", own,
                             extra, cand_cmd, a.timeout, usage=ref.get("_usage"))

        g4a = gate_behaviour.compare(ref["records"], cand["records"], ref.get("_site_function"))
        rec.update(
            status="ok",
            # A failing reference run here means THIS RUNNER could not execute
            # the suite, not that the instance is unsound: every repository in
            # the corpus passes its own CI in the GitHub Actions harness. The
            # field is named accordingly so no table can quietly turn a local
            # limitation into a property of the instance.
            reference_runnable_locally=ref["tests_passed"],
            reference_tests_passed=ref["tests_passed"], reference_calls=ref["calls"],
            reference_library_calls=ref.get("library_calls"),
            reference_usage_calls=ref.get("usage_calls"),
            reference_last_line=ref.get("last_line", ""),
            usage_functions=sum(len(v) for v in (ref.get("_usage") or {}).values()),
            reran_for_usage=bool(ref.get("reran_for_usage")),
            replacement_module=a.replacement_module,
            candidate_tests_passed=cand["tests_passed"], candidate_calls=cand["calls"],
            candidate_library_calls=cand.get("library_calls"),
            candidate_usage_calls=cand.get("usage_calls"),
            ci_verdict="pass" if cand["tests_passed"] else "fail",
            g4a={k: v for k, v in g4a.items() if k not in ("divergences", "missing_calls")},
            g4a_evidence=dict(divergences=g4a["divergences"][:5],
                              not_observable=g4a["missing_calls"][:5]),
        )
        results.append(rec)
        print(f"  {mid}: ref_tests={'pass' if ref['tests_passed'] else 'FAIL'}"
              f" ({ref.get('library_calls')} lib + {ref.get('usage_calls')} usage calls) | cand_tests="
              f"{'pass' if cand['tests_passed'] else 'FAIL'} ({cand.get('library_calls')} lib + "
              f"{cand.get('usage_calls')} usage) | G4a={g4a['verdict']} [{g4a['decided_at']}]")

    pathlib.Path(a.out).write_text(json.dumps(results, indent=1, default=str))
    ok = [r for r in results if r.get("status") == "ok"]
    usable = [r for r in ok if r.get("reference_tests_passed") and r.get("reference_calls")]
    no_base = [r for r in ok if not r.get("reference_tests_passed")]
    no_trace = [r for r in ok if r.get("reference_tests_passed") and not r.get("reference_calls")]
    print(f"\n{len(results)} candidates, {len(ok)} ran, {len(usable)} with a usable reference")
    print(f"  suite not runnable by THIS runner (local limitation): {len(no_base)}")
    print(f"  baseline passed but no call recorded (G4 silent):     {len(no_trace)}")
    if usable:
        import collections
        c = collections.Counter((r["ci_verdict"], r["g4a"]["verdict"]) for r in usable)
        print("  (CI verdict, G4a verdict) -> n")
        for k, v in sorted(c.items()):
            print(f"    {k} -> {v}")
        caught = sum(1 for r in usable
                     if r["ci_verdict"] == "pass" and r["g4a"]["passed"] is False)
        inconclusive = sum(1 for r in usable
                           if r["ci_verdict"] == "pass" and r["g4a"]["passed"] is None)
        cip = sum(1 for r in usable if r["ci_verdict"] == "pass")
        print(f"  CI-passing candidates rejected by G4a: {caught} of {cip}; inconclusive: {inconclusive}")
    print(f"-> {a.out}")


if __name__ == "__main__":
    main()
