#!/usr/bin/env python3
"""Run the G4 fixture end to end and print what each gate sees.

Three candidates replace `slugger` with `app.textutil`; all three pass the two
tests. honest is a correct rewrite; pseudo is wrong only off the suite's input
set; hollow returns constants. Expected: G4a identical for all three (the
cheats are right on the inputs the tests use), G4b separating honest from the
other two. A fourth, inline, does the work at the call site with no module
the boundary recorder could name: G4a must still reach `identical`, decided at
the usage level. If G4a ever rejects honest or inline, the gate has a
false-rejection bug.

usage: run_fixture.py [python]
"""
import json
import os
import pathlib
import shutil
import subprocess
import sys

HERE = pathlib.Path(__file__).resolve().parent
T = HERE / "fixture"
sys.path.insert(0, str(HERE.parents[1] / "scripts" / "gh"))
import gate_behaviour  # noqa: E402
import record_usage  # noqa: E402
from gate_differential import compare_callables  # noqa: E402

PY = sys.argv[1] if len(sys.argv) > 1 else sys.executable


def run(work, out, targets, site_exclude=(), usage=None, pythonpath=()):
    if out.exists():
        out.unlink()
    record_usage.write_recorder(work, "slugger", targets, ["app", "tests"], out=str(out),
                                site_exclude=site_exclude, usage=usage)
    env = dict(os.environ, PYTHONPATH=":".join(str(p) for p in pythonpath))
    r = subprocess.run([PY, "-m", "pytest", "-q", "-p", "no:cacheprovider", "tests"],
                       cwd=work, env=env, capture_output=True, text=True)
    line = (r.stdout.strip().splitlines() or ["?"])[-1][:60]
    return line, gate_behaviour.load(out)


usage = record_usage.usage_functions(T / "repo", ["slugger"])
print("usage functions:", usage)
ref_line, ref = run(T / "repo", T / "ref.jsonl", ["slugger"], usage=usage,
                    pythonpath=[T / "site", T / "repo"])
sf = record_usage.site_functions(T / "repo", ref)
print(f"reference: pytest '{ref_line}', {len(ref)} records "
      f"({sum(1 for r in ref if r.get('level') != 'usage')} library, "
      f"{sum(1 for r in ref if r.get('level') == 'usage')} usage)")

import importlib.util  # noqa: E402
import random  # noqa: E402
sys.path.insert(0, str(T / "site"))
import slugger  # noqa: E402

for variant in ("honest", "pseudo", "hollow", "inline"):
    work = T / f"work_{variant}"
    if work.exists():
        shutil.rmtree(work)
    shutil.copytree(T / "repo", work, ignore=shutil.ignore_patterns(
        "sitecustomize.py", "conftest.py", "__pycache__", ".pytest_cache"))
    has_module = (T / f"replacement_{variant}.py").exists()
    if has_module:
        shutil.copy(T / f"replacement_{variant}.py", work / "app" / "textutil.py")
    (work / "app" / "core.py").write_text((T / f"core_{variant}.py").read_text())
    (work / "pyproject.toml").write_text('[project]\nname = "app"\ndependencies = []\n')
    line, cand = run(work, T / f"cand_{variant}.jsonl",
                     ["slugger", "app.textutil"] if has_module else ["slugger"],
                     site_exclude=["app/textutil.py"], usage=usage,
                     pythonpath=[T / "site", work])
    res = gate_behaviour.compare(ref, cand, sf)
    # G4b: the library and the replacement on inputs derived from the recorded ones
    g4b = {}
    if has_module:
        sp = importlib.util.spec_from_file_location("c", T / f"replacement_{variant}.py")
        m = importlib.util.module_from_spec(sp)
        sp.loader.exec_module(m)
        by_fn = {}
        for r in ref:
            if r.get("level") != "usage":
                by_fn.setdefault(r["q"].split(".")[-1], []).append(r)
        g4b = {fn: compare_callables(getattr(slugger, fn), getattr(m, fn), calls, n=200)
               for fn, calls in by_fn.items()}
    g4b_fail = sum(1 for v in g4b.values() if v["pass"] is False)
    print(f"[{variant:6s}] pytest '{line}' | {len(cand)} records | "
          f"G4a {res['verdict']} [{res['decided_at']}] matched {res['matched']} "
          f"(lib {res['matched_library']}, usage {res['matched_usage']}) "
          f"| G4b {('FAIL' if g4b_fail else 'pass') if g4b else 'n/a (no replacement module)'}: "
          + ", ".join(f"{fn} {v['evidence'].get('divergent', 0)}/{v['evidence'].get('tried', 0)}"
                      for fn, v in g4b.items()))
    if res["verdict"] == "divergent":
        print("    ", json.dumps(res["divergences"][:2], default=str)[:300])
