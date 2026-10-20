#!/usr/bin/env python3
"""Two diagnostic probes run before the rebuild commits to its foundations.

Both answer a question the rebuild plan (oracle-blindness/docs/REBUILD_PLAN.md,
Phase -1) cannot answer from existing files, and both run on the existing
harness so that nothing new about the environment confounds the answer.

Probe 1, `rdx`: why do 117 traced pairs record no call?
  results/trace_states.json has 143 pairs traced, 117 "loaded, no call", 64 not
  green and 6 never loaded. The recorder wraps the library's callables when it
  is imported, and only objects that inspect.isfunction / isbuiltin accept, so a
  numpy ufunc or a C-level callable is never wrapped. Whether that, or genuinely
  untested code, explains the 117 decides whether the gradable pool can grow.

  Each pair runs the v1 recorder unchanged AND an independent probe in the same
  process, so a difference between them is a difference of instrument, never of
  environment. The probe uses sys.setprofile: every Python-level call into the
  library, every builtin (C) call whose module is the library, and every
  execution of a repository function that statically references the library.
  The last signal does not depend on how the library is called at all, so a
  pair where library-referencing functions run but no call is seen is a
  capture gap, and a pair where none runs is genuinely untested.

  Arms (instance id <iid>__<kind>__<dep>):
    rdxw  recorder + probe   the 117, and 30 traced pairs as a control: the
                             probe must see calls wherever the recorder did,
                             or the probe itself is wrong
    rdxp  probe only         the 64 not green and 6 never loaded: is the
                             recorder what turns these suites red?
    rdxg  gold, nothing      one per repository of those 70: is the suite red
                             with no instrument at all (drift since screening)?

Probe 2, `rta` / `rtf` / `rtc`: what does the test-import rule cost, and how
much of the census came from a defect in the v1 block?
  104 of 330 pairs have a test file importing the library unguarded. Under the
  current rules (no test edits, the block covers test frames) those are not
  solvable. Rule (a) of the plan lets tests keep the library: the block then
  covers only the repository's non-test frames. Every pair runs three times with the
  gold manifest (the library stays installed, as a test-only dependency would
  keep it):
    rtc   v1 block, tests included      control: should fail on all 330, as the
                                        census found; any pass is drift.
    rtf   fixed block, tests included   rtc fails but rtf passes -> the v1
                                        detection came from the guard defect
                                        described above blocker_body, not from
                                        the repository using the library.
    rta   fixed block, tests exempt     CI still fails -> the runtime code needs
                                        the library and the tests see it: a task
                                        under rule (a). rtf fails but rta passes
                                        -> the detection rested on test files
                                        importing the library.

Control for both, `rtn`: the same injected files with an empty body, once per
repository (see NULL_BODY). Today's plain gold comes from the existing `gold`
set.

Nothing written here reports a number. `probe_report.py` reads the results.

usage:
  probes.py --dataset-regular D --dataset-large D --repo-data R --out-root DIR
"""
from __future__ import annotations

import argparse
import ast
import json
import os
import pathlib
import random
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
import footprint as FP  # noqa: E402
import manifests as M  # noqa: E402
from make_blocked import BLOCKER, apply_patch, multi_file_diff, own_packages  # noqa: E402
from make_blocked import import_names as block_names  # noqa: E402
from make_traces import recorder_body  # noqa: E402

ROOT = pathlib.Path(__file__).resolve().parents[2]
FIELDS = ["instance_id", "metadata", "language", "act_command", "ci_file",
          "patch", "build_files", "env_specs"]
MARK_BEGIN = "# >>> UnpinBench injected block (do not edit) >>>\n"
MARK_END = "# <<< UnpinBench injected block <<<\n"
N_TRACED_CONTROLS = 30
SEED = 20261020


# --- probe 2: the block with test frames exempt ----------------------------
# The only change to the v1 blocker: a frame in a test file is foreign, so a
# test may import the library and use it, while any non-test repository frame
# is still refused. The test rule is footprint.is_test_path, the same rule the
# 104-pair scan used.
_TEST_RULE = '''
_TEST_DIRS = {test_dirs!r}


def _is_test(real):
    rel = real[len(_REAL_ROOT) + 1:] if real.startswith(_REAL_ROOT + os.sep) else real
    parts = rel.split(os.sep)
    name = parts[-1]
    return (any(p in _TEST_DIRS for p in parts[:-1]) or name.startswith("test_")
            or name.endswith("_test.py") or name in ("conftest.py", "tests.py"))

'''

_V1_REL = '''    elif not os.path.isabs(fn):
        r = True                                            # relative paths are project files'''
_RT_REL = '''    elif not os.path.isabs(fn):
        r = not _is_test(os.path.realpath(fn))              # test frames are exempt'''
_V1_ABS = '''            r = None if (os.path.abspath(fn) in _SELF or real in _REAL_SELF) else True'''
_RT_ABS = '''            r = None if (os.path.abspath(fn) in _SELF or real in _REAL_SELF) else (not _is_test(real))'''


# --- the v1 guard defect, and the fix both rt arms use -----------------------
# When a foreign frame (a third-party package, or under rule (a) a test) loads
# the blocked library, v1 replaces each of its modules in sys.modules with a
# _Guard: an empty ModuleType forwarding attribute access. `from m import *`
# reads a module's __dict__ when it has no __all__, and a _Guard's __dict__ is
# empty, so star imports inside the library import nothing. numpy's own import
# then fails (NameError: 'scalar'), reproduced on 3.8 and 3.12 with a suite whose
# only use of numpy is through pandas. Under v1 such a suite fails, and the
# census reads the failure as the tests noticing the removal.
#
# The fix replaces no module. The finder still refuses a first import from a
# repository frame, and a builtins.__import__ wrapper refuses every later import
# statement from a repository frame, which is what the guard existed to catch
# (an import served from sys.modules never reaches a finder). Not covered:
# importlib.import_module of an already-loaded module from repository code.
_V1_GUARD_TAIL = '''        for finder in sys.meta_path:
            if finder is self or not hasattr(finder, "find_spec"):
                continue
            spec = finder.find_spec(fullname, path, target)
            if spec is not None:
                if spec.loader is not None and hasattr(spec.loader, "exec_module"):
                    spec.loader = _GuardLoader(spec.loader)
                return spec
        return None'''
_FIX_TAIL = '''        return None'''
_V1_PURGE = '''    sys.meta_path.insert(0, _BlockedFinder())
    for name in list(sys.modules):      # force every first import through the finder
        if _blocked(name):
            del sys.modules[name]'''
_FIX_HOOK = '''    sys.meta_path.insert(0, _BlockedFinder())
    import builtins
    _orig = builtins.__import__

    def _unpinbench_import(name, globals=None, locals=None, fromlist=(), level=0):
        if level == 0 and _blocked(name) and _repo_origin(2):
            raise ImportError("No module named %r %s" % (name, _MARK))
        return _orig(name, globals, locals, fromlist, level)

    builtins.__import__ = _unpinbench_import'''


def blocker_body(dep, names, own, exempt_tests: bool, fixed: bool = True) -> str:
    """v1 blocker (fixed=False, tests included) or the fixed one, optionally exempting tests."""
    body = BLOCKER.format(dep=dep, names=names, own=list(own))
    tags = []
    if fixed:
        for old, new in ((_V1_GUARD_TAIL, _FIX_TAIL), (_V1_PURGE, _FIX_HOOK)):
            assert body.count(old) == 1, "blocker guard code changed; update probes.py"
            body = body.replace(old, new)
        tags.append("import hook")
    if exempt_tests:
        for old, new in ((_V1_REL, _RT_REL), (_V1_ABS, _RT_ABS)):
            assert body.count(old) == 1, "blocker frame test changed; update probes.py"
            body = body.replace(old, new)
        anchor = "\ndef _is_repo_file(fn):"
        assert body.count(anchor) == 1
        body = body.replace(anchor, _TEST_RULE.format(test_dirs=sorted(FP.TEST_DIR_NAMES)) + anchor)
        tags.append("tests exempt")
    if tags:
        old = '"UnpinBench blocker active: %s (pid %d, root %s)\\n"'
        assert body.count(old) == 1, "blocker announcement changed; update probes.py"
        body = body.replace(old, '"UnpinBench blocker active: %%s (pid %%d, root %%s) [%s]\\n"' % ", ".join(tags))
    return body


# --- probe 1: static map of library-referencing repository functions -------
def dmap(repo: pathlib.Path, names: set[str]) -> dict:
    """relpath -> {"f": [first lines of functions referencing the library], "m": module-level use}.

    First line is the earliest decorator line or the def line, which is what
    co_firstlineno reports on Python 3.8+ for a decorated function.
    """
    out = {}
    for path in FP._py_files(repo):
        rel = path.relative_to(repo)
        if FP.is_test_path(rel) or rel.name in ("setup.py", "sitecustomize.py"):
            continue
        try:
            tree = ast.parse(path.read_text(errors="ignore"))
        except (SyntaxError, ValueError):
            continue
        aliases = set()
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                for a in node.names:
                    if a.name.split(".")[0] in names:
                        aliases.add(a.asname or a.name.split(".")[0])
            elif isinstance(node, ast.ImportFrom) and node.module and node.level == 0:
                if node.module.split(".")[0] in names:
                    for a in node.names:
                        aliases.add(a.asname or a.name)
        if not aliases:
            continue
        funcs, module_use = set(), False
        stack: list[int] = []

        def first_line(fn):
            return min([fn.lineno] + [d.lineno for d in fn.decorator_list])

        def visit(node):
            nonlocal module_use
            is_fn = isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef))
            if is_fn:
                stack.append(first_line(node))
            hit = False
            if isinstance(node, ast.Name) and node.id in aliases:
                hit = True
            elif isinstance(node, ast.Attribute):
                root = node
                while isinstance(root, ast.Attribute):
                    root = root.value
                hit = isinstance(root, ast.Name) and root.id in aliases
            if hit:
                if stack:
                    funcs.add(stack[-1])
                else:
                    module_use = True
            for child in ast.iter_child_nodes(node):
                visit(child)
            if is_fn:
                stack.pop()

        visit(tree)
        if funcs or module_use:
            out[str(rel)] = {"f": sorted(funcs), "m": module_use}
    return out


PROBE = r'''# fmt: off
# flake8: noqa
# ruff: noqa
# pylint: skip-file
# mypy: ignore-errors
# isort: skip_file
"""Injected by UnpinBench probe: which calls into {dep!r} does this repository make?

Diagnostic only. It never changes a result: every hook swallows its own
errors, and nothing is written to stdout or stderr except by the top-level
process at exit, so a test that captures a subprocess's output sees nothing.
"""
import atexit as _pz_atexit
import json as _pz_json
import os as _pz_os
import sys as _pz_sys
import threading as _pz_th

_PZ_FLAG = "_unpinbench_probe_" + {flag!r}


def _pz_main():
    if getattr(_pz_sys, _PZ_FLAG, False):
        return
    setattr(_pz_sys, _PZ_FLAG, True)
    names = frozenset({names!r})
    own = frozenset({own!r})
    dm = {dmap!r}
    here = _pz_os.path.dirname(_pz_os.path.abspath(__file__))
    root = _pz_os.path.realpath(here)
    pre = root + _pz_os.sep
    selfs = {{_pz_os.path.realpath(_pz_os.path.join(root, n)) for n in ("sitecustomize.py", "conftest.py")}}
    stdlib = _pz_os.path.dirname(_pz_os.__file__)
    marks = tuple("/%s-packages/%s%s" % (sp, n, tail)
                  for sp in ("site", "dist") for n in names for tail in ("/", ".py"))
    venv = ("/.venv/", "/venv/", "/.tox/", "/.nox/", "/.eggs/", "/node_modules/")
    testdirs = frozenset({test_dirs!r})
    dfuncs = {{rel: frozenset(v["f"]) for rel, v in dm.items()}}
    dmods = frozenset(rel for rel, v in dm.items() if v["m"])
    kind, relof = {{}}, {{}}
    st = {{"calls": {{}}, "ccalls": {{}}, "dfn": {{}}, "dmod": {{}}, "imp": {{}}, "on": False}}
    outdir = "/tmp/unpinbench_probe"
    top = _pz_os.environ.get("UNPINBENCH_PROBE_TOP")
    me = str(_pz_os.getpid())
    if not top:
        _pz_os.environ["UNPINBENCH_PROBE_TOP"] = me

    def classify(fn):
        k = kind.get(fn)
        if k is not None:
            return k
        if not fn or fn.startswith("<"):
            k = "x"
        elif any(m in fn for m in marks):
            k = "D"
        elif fn.startswith(stdlib + "/") or "/importlib/" in fn:
            k = "x"
        elif any(v in fn for v in venv) or "-packages/" in fn:
            k = "o"
        else:
            real = _pz_os.path.realpath(fn)
            if real in selfs:
                k = "x"
            elif real.startswith(pre):
                rel = real[len(pre):]
                parts = rel.split(_pz_os.sep)
                nm = parts[-1]
                test = (any(p in testdirs for p in parts[:-1]) or nm.startswith("test_")
                        or nm.endswith("_test.py") or nm in ("conftest.py", "tests.py"))
                k = "t" if test else "s"
                relof[fn] = rel
            else:
                k = "o"
        kind[fn] = k
        return k

    def caller(f):
        n = 0
        while f is not None and n < 64:
            k = classify(f.f_code.co_filename)
            if k != "x":
                return k
            f, n = f.f_back, n + 1
        return "o"

    def bump(d, key):
        d[key] = d.get(key, 0) + 1

    def prof(frame, event, arg):
        try:
            if event == "call":
                co = frame.f_code
                k = classify(co.co_filename)
                if k == "D":
                    c = caller(frame.f_back)
                    if co.co_name == "<module>":
                        bump(st["imp"], c)
                    elif c in ("s", "t"):
                        fn = co.co_filename
                        bump(st["calls"], c + ":" + fn[fn.rfind("-packages/") + 10:] + ":" + co.co_name)
                elif k == "s":
                    rel = relof.get(co.co_filename)
                    if co.co_name == "<module>":
                        if rel in dmods:
                            bump(st["dmod"], rel)
                    elif co.co_firstlineno in dfuncs.get(rel, ()):
                        bump(st["dfn"], "%s:%d" % (rel, co.co_firstlineno))
            elif event == "c_call":
                m = getattr(arg, "__module__", None)
                if not isinstance(m, str):
                    s = getattr(arg, "__self__", None)
                    m = getattr(s, "__name__", None) if type(s).__name__ == "module" else type(s).__module__
                if isinstance(m, str) and m.split(".")[0] in names:
                    c = caller(frame)
                    if c in ("s", "t"):
                        bump(st["ccalls"], c + ":" + m + "." + str(getattr(arg, "__name__", "?")))
        except Exception:
            pass

    def activate():
        if st["on"]:
            return
        st["on"] = True
        _pz_sys.setprofile(prof)
        _pz_th.setprofile(prof)

    class Trigger:
        """Turns the profiler on at the first import of the repository, its tests or the
        library, so pip, poetry and tox processes run at full speed."""

        def find_spec(self, fullname, path=None, target=None):
            if not st["on"]:
                r = fullname.split(".")[0]
                if r in own or r in names or r == "conftest" or r.startswith("test"):
                    activate()
            return None

    def cap(d, n):
        return dict(sorted(d.items(), key=lambda kv: -kv[1])[:n])

    def dump():
        try:
            if not st["on"]:
                return
            rec = {{"pid": me, "top": top or me, "argv0": _pz_os.path.basename(_pz_sys.argv[0] if _pz_sys.argv else ""),
                   "calls": cap(st["calls"], 60), "ccalls": cap(st["ccalls"], 60),
                   "dfn": cap(st["dfn"], 80), "dmod": st["dmod"], "imp": st["imp"],
                   "n_calls": sum(st["calls"].values()), "n_ccalls": sum(st["ccalls"].values()),
                   "n_dfn": len(st["dfn"])}}
            _pz_os.makedirs(outdir, exist_ok=True)
            with open(_pz_os.path.join(outdir, me + ".json"), "w") as fh:
                fh.write(_pz_json.dumps(rec))
        except Exception:
            pass

    def report():
        # Only a top-level process prints, and only at exit, when pytest has
        # released fd 2: children leave a file the top-level process collects.
        dump()
        if top:
            return
        try:
            fd = _pz_os.dup(2)
            for f in sorted(_pz_os.listdir(outdir)):
                try:
                    rec = _pz_json.load(open(_pz_os.path.join(outdir, f)))
                except Exception:
                    continue
                if rec.get("top") == me:
                    _pz_os.write(fd, ("UNPINPROBE " + _pz_json.dumps(rec) + chr(10)).encode("utf-8", "replace"))
        except Exception:
            pass

    if _pz_sys.argv and _pz_sys.argv[0]:
        try:
            if _pz_os.path.realpath(_pz_sys.argv[0]).startswith(pre):
                activate()
        except Exception:
            pass
    if any(n.split(".")[0] in names or n.split(".")[0] in own for n in list(_pz_sys.modules)):
        activate()
    _pz_sys.meta_path.insert(0, Trigger())
    _pz_atexit.register(report)


_pz_main()
'''


def probe_body(dep, names, own, dm) -> str:
    return PROBE.format(dep=dep, flag=M.norm(dep), names=sorted(names), own=sorted(own),
                        dmap=dm, test_dirs=sorted(FP.TEST_DIR_NAMES))


# --- the null injection: the control every injected arm needs --------------
# v1 delivers its instruments as sitecustomize.py and conftest.py at the
# repository root. A root conftest.py makes pytest put the root on sys.path, so
# a package with a compiled part can be imported from the source tree instead of
# the installed build: KaveIO_PhiK then fails with "No module named
# 'phik.lib'" under the probe alone while its gold run passes. rtn injects the
# same two files with an empty body, once per repository; a repository that
# fails it cannot be read through any injected arm.
NULL_BODY = "# UnpinBench null injection: no block, no recorder, no probe\n"


# --- assembling prediction sets --------------------------------------------
def injected(repo: pathlib.Path, body: str) -> dict:
    files = {}
    for name in ("sitecustomize.py", "conftest.py"):
        old = (repo / name).read_text() if (repo / name).exists() else None
        files[name] = (old, MARK_BEGIN + body.rstrip("\n") + "\n" + MARK_END + ("\n" + old if old else ""))
    return files


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--dataset-regular", required=True)
    ap.add_argument("--dataset-large", required=True)
    ap.add_argument("--repo-data", required=True)
    ap.add_argument("--out-root", default=str(ROOT))
    ap.add_argument("--only", choices=["rdx", "rt", "rtn"], default=None)
    a = ap.parse_args()

    rows = {}
    for sub, path in (("regular", a.dataset_regular), ("large", a.dataset_large)):
        for line in open(path):
            if line.strip():
                r = json.loads(line)
                rows[r["instance_id"]] = (sub, r)
    pool = [json.loads(l) for l in open(ROOT / "pilot/instances.jsonl") if l.strip()]
    states = json.load(open(ROOT / "oracle-blindness/results/trace_states.json"))
    repo_data = pathlib.Path(a.repo_data) / "python"
    out = pathlib.Path(a.out_root)

    def state(p):
        return states.get(f"{p['instance_id']}|{M.norm(p['dependency'])}")

    traced = sorted((p for p in pool if state(p) == "traced"),
                    key=lambda p: (p["instance_id"], M.norm(p["dependency"])))
    controls = {(p["instance_id"], p["dependency"])
                for p in random.Random(SEED).sample(traced, N_TRACED_CONTROLS)}
    assert all(state(p) is not None for p in pool), "pool pair missing from trace_states.json"

    sets: dict[str, list] = {}
    manifest = {"seed": SEED, "pairs": {}}
    gold_done, null_done = set(), set()

    def emit(set_base, iid, kind, dep, files):
        sub, r = rows[iid]
        set_name = set_base + ("_large" if sub == "large" else "")
        mid = f"{iid}__{kind}__{M.norm(dep)}"
        d = out / "predictions" / set_name / "python" / mid
        d.mkdir(parents=True, exist_ok=True)
        (d / "patch.diff").write_text(multi_file_diff(files) if files else "")
        sets.setdefault(set_name, []).append({**{k: r[k] for k in FIELDS}, "instance_id": mid})
        manifest["pairs"][mid] = {"set": set_name, "instance_id": iid, "dependency": dep,
                                  "kind": kind, "trace_state": state({"instance_id": iid, "dependency": dep})}

    for p in pool:
        iid, dep = p["instance_id"], p["dependency"]
        sub, r = rows[iid]
        repo = repo_data / iid
        bf = r["build_files"][0]
        masked = (repo / bf).read_text()
        gold = apply_patch(repo, bf, r["patch"])
        own = own_packages(repo)
        manifest_files = {bf: (masked, gold)}
        st = state(p)

        if a.only in (None, "rt"):
            bn = block_names(dep)
            for kind, exempt, fixed in (("rta", True, True), ("rtf", False, True), ("rtc", False, False)):
                emit(kind, iid, kind, dep,
                     {**manifest_files, **injected(repo, blocker_body(dep, bn, own, exempt, fixed))})

        if a.only in (None, "rtn") and iid not in null_done:
            null_done.add(iid)
            emit("rtn", iid, "rtn", dep, {**manifest_files, **injected(repo, NULL_BODY)})

        if a.only in (None, "rdx"):
            pn = set(FP.import_names(dep))
            dm = dmap(repo, pn)
            if st == "loaded, no call" or (iid, dep) in controls:
                rec = recorder_body(dep, block_names(dep), own, "/dev/stdout")
                emit("rdx", iid, "rdxw", dep,
                     {**manifest_files, **injected(repo, rec + "\n\n" + probe_body(dep, pn, own, dm))})
            elif st in ("not green", "never loaded"):
                emit("rdx", iid, "rdxp", dep,
                     {**manifest_files, **injected(repo, probe_body(dep, pn, own, dm))})
                if iid not in gold_done:
                    gold_done.add(iid)
                    emit("rdx", iid, "rdxg", dep, dict(manifest_files))

    for set_name, srows in sets.items():
        with open(out / "pilot" / f"{set_name}.jsonl", "w") as f:
            for r in srows:
                f.write(json.dumps(r) + "\n")
        print(f"{set_name}: {len(srows)}", file=sys.stderr)
    with open(out / "pilot" / "probes_manifest.json", "w") as f:
        json.dump(manifest, f, indent=1, sort_keys=True)


if __name__ == "__main__":
    main()
