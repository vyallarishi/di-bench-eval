#!/usr/bin/env python3
"""Tests for manifests.py.

Two layers:

1. Unit tests on hand-written manifests covering the formatting traps
   (comments, markers, extras, directives, nested brackets, single-line forms).
2. A property test over every real DI-Bench Python instance: for each declared
   dependency, remove it and assert the declared set shrinks by exactly that
   one package and nothing else moved. This is the check that matters, because
   a silently wrong edit would corrupt a benchmark instance.

usage: test_manifests.py [--full]      (--full also runs the property test)
"""
import json
import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
import manifests as M  # noqa: E402

FAILS = []


def check(name, cond, detail=""):
    if cond:
        print(f"  pass  {name}")
    else:
        print(f"  FAIL  {name}  {detail}")
        FAILS.append(name)


def eq(name, got, want):
    check(name, got == want, f"got={got!r} want={want!r}")


# --------------------------------------------------------------------------
print("requirements.txt")
REQ = """\
# comment line
requests==2.31.0
Flask >= 2.0  # trailing comment
-r other.txt
-e .
urllib3[secure]>=1.26 ; python_version < '3.10'

package-with-dashes
"""
eq("declared", M.declared("requirements.txt", REQ),
   {"requests", "flask", "urllib3", "package_with_dashes"})
out = M.remove("requirements.txt", REQ, "Flask")
eq("remove keeps others", M.declared("requirements.txt", out),
   {"requests", "urllib3", "package_with_dashes"})
check("remove keeps directives", "-r other.txt" in out and "-e ." in out)
check("remove keeps comments", "# comment line" in out)
check("remove absent -> None", M.remove("requirements.txt", REQ, "nope") is None)
eq("extras+marker name", M._req_name("urllib3[secure]>=1.26 ; python_version < '3.10'"),
   "urllib3")
eq("url form", M._req_name("pkg @ https://example.com/p.whl"), "pkg")

# --------------------------------------------------------------------------
print("\nsetup.py")
SETUP = '''\
from setuptools import setup
setup(
    name="demo",
    install_requires=[
        "spake2==0.8", "pynacl",
        "attrs >= 19.2.0",  # 19.2.0 replaces cmp
        "twisted[tls] >= 17.5.0",
    ],
    extras_require={"dev": ["pytest"]},
)
'''
eq("declared", M.declared("setup.py", SETUP),
   {"spake2", "pynacl", "attrs", "twisted"})
out = M.remove("setup.py", SETUP, "attrs")
eq("remove mid-list", M.declared("setup.py", out), {"spake2", "pynacl", "twisted"})
check("comment removed with entry", "replaces cmp" not in out)
check("extras_require untouched", '"dev": ["pytest"]' in out)
out2 = M.remove("setup.py", SETUP, "pynacl")
eq("remove same-line entry", M.declared("setup.py", out2),
   {"spake2", "attrs", "twisted"})
check("still parses as python", compile(out, "<t>", "exec") is not None)
check("absent -> None", M.remove("setup.py", SETUP, "nope") is None)

COMMENTY = '''\
install_requires = [
    #
    # The core 'install_requires' should only be things
    # which are needed for the main editor to function.  # don't parse 't'
    #
    "PyQt5==5.13.2"
    + ';"arm" not in platform_machine and "aarch" not in platform_machine',
    "jupyter-client>=4.1,<6.2",  # comment with 'quotes' after an entry
]
setup(install_requires=install_requires)
'''
eq("comments and concatenated markers ignored", M.declared("setup.py", COMMENTY),
   {"pyqt5", "jupyter_client"})
out = M.remove("setup.py", COMMENTY, "jupyter-client")
eq("remove after commented block", M.declared("setup.py", out), {"pyqt5"})
check("comment with quotes untouched", "'install_requires' should" in out)
check("marker continuation intact", '+ \';"arm" not in platform_machine' in out)

NOLIST = 'setup(install_requires=reqs)\n'
eq("non-literal list -> empty", M.declared("setup.py", NOLIST), set())
check("non-literal remove -> None", M.remove("setup.py", NOLIST, "x") is None)

# --------------------------------------------------------------------------
print("\nsetup.cfg")
CFG = """\
[metadata]
name = demo

[options]
install_requires =
    colorzero
    importlib_resources~=5.0;python_version<'3.10'
    requests

[options.extras_require]
dev =
    pytest
"""
eq("declared", M.declared("setup.cfg", CFG),
   {"colorzero", "importlib_resources", "requests"})
out = M.remove("setup.cfg", CFG, "importlib-resources")
eq("remove with marker", M.declared("setup.cfg", out), {"colorzero", "requests"})
check("extras_require untouched", "pytest" in out)
check("section header intact", "[options.extras_require]" in out)
check("absent -> None", M.remove("setup.cfg", CFG, "nope") is None)

# --------------------------------------------------------------------------
print("\npyproject.toml")
PEP = """\
[project]
name = "demo"
dependencies = [
    "requests>=2",
    "click",
]

[project.optional-dependencies]
dev = ["pytest"]
"""
eq("pep621 declared", M.declared("pyproject.toml", PEP), {"requests", "click"})
out = M.remove("pyproject.toml", PEP, "click")
eq("pep621 remove", M.declared("pyproject.toml", out), {"requests"})
check("optional untouched", "pytest" in out)

POE = """\
[tool.poetry.dependencies]
python = "^3.9"
requests = "^2.28"
click = { version = "^8.0", optional = true }
"""
eq("poetry declared", M.declared("pyproject.toml", POE), {"requests", "click"})
out = M.remove("pyproject.toml", POE, "requests")
eq("poetry remove", M.declared("pyproject.toml", out), {"click"})
check("poetry inline table survives", "optional = true" in out)
check("python pin kept", 'python = "^3.9"' in out)

# --------------------------------------------------------------------------
if "--full" in sys.argv:
    print("\nproperty test over every real DI-Bench Python instance")
    import subprocess
    import shutil
    import tempfile

    def apply_patch(repo, bf, patch):
        with tempfile.TemporaryDirectory() as td:
            td = pathlib.Path(td)
            (td / bf).parent.mkdir(parents=True, exist_ok=True)
            shutil.copy(repo / bf, td / bf)
            (td / "p.diff").write_text(patch)
            r = subprocess.run(
                ["git", "apply", "--allow-empty", "--ignore-whitespace",
                 "--ignore-space-change", "p.diff"],
                cwd=td, capture_output=True, text=True)
            if r.returncode != 0:
                shutil.copy(repo / bf, td / bf)
                subprocess.run(["patch", "--batch", "--fuzz=5", "-p1", "-i", "p.diff"],
                               cwd=td, capture_output=True, text=True)
            return (td / bf).read_text()

    stats = {"instances": 0, "deps": 0, "ok": 0, "unsafe": 0, "WRONG": 0}
    wrong = []
    by_kind = {}
    for ds in ["dataset-dibench-regular.jsonl", "dataset-dibench-large.jsonl"]:
        p = pathlib.Path(".cache") / ds
        if not p.exists():
            continue
        for line in open(p):
            r = json.loads(line)
            if r["language"].lower() != "python":
                continue
            if len(r["build_files"]) != 1:
                continue
            repo = pathlib.Path(".cache/repo-data/python") / r["instance_id"]
            bf = r["build_files"][0]
            if not (repo / bf).exists():
                continue
            k = M.kind(bf)
            if k == "unknown":
                continue
            try:
                gold = apply_patch(repo, bf, r["patch"])
                base = M.declared(bf, gold)
            except Exception:
                continue
            if not base:
                continue
            stats["instances"] += 1
            d = by_kind.setdefault(k, {"inst": 0, "deps": 0, "ok": 0, "unsafe": 0})
            d["inst"] += 1
            for dep in sorted(base):
                stats["deps"] += 1
                d["deps"] += 1
                new = M.remove(bf, gold, dep)
                if new is None:
                    stats["unsafe"] += 1
                    d["unsafe"] += 1
                    continue
                got = M.declared(bf, new)
                want = base - {dep}
                if got == want:
                    stats["ok"] += 1
                    d["ok"] += 1
                else:
                    stats["WRONG"] += 1
                    wrong.append((r["instance_id"], bf, dep,
                                  sorted(want - got), sorted(got - want)))
    print(f"  instances {stats['instances']}, dependencies {stats['deps']}")
    print(f"  clean removals {stats['ok']}, declined as unsafe {stats['unsafe']},"
          f" INCORRECT {stats['WRONG']}")
    for k, d in sorted(by_kind.items()):
        print(f"    {k:13s} inst={d['inst']:3d} deps={d['deps']:4d}"
              f" ok={d['ok']:4d} unsafe={d['unsafe']:3d}")
    for w in wrong[:10]:
        print("    WRONG:", w)
    check("no incorrect edits on real data", stats["WRONG"] == 0,
          f"{stats['WRONG']} wrong")

print()
if FAILS:
    print(f"FAILED: {len(FAILS)} -> {FAILS}")
    sys.exit(1)
print("all tests passed")
