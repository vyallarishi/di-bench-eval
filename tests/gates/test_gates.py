#!/usr/bin/env python3
"""Tests for G7 (test oracle untouched) and G8 (closure not grown).

Each gate is checked in both directions. A gate that rejects everything has
perfect detection and is useless, so every case below pairs an attack the gate
must catch with a legitimate edit it must let through.

usage: test_gates.py
"""
import json
import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[2] / "scripts" / "gh"))
import gate_closure  # noqa: E402
import gate_tests  # noqa: E402

FAILS = []


def expect(name, got_pass, want_pass, detail=""):
    if got_pass == want_pass:
        print(f"  pass  {name}")
    else:
        print(f"  FAIL  {name}: expected {'pass' if want_pass else 'reject'}, "
              f"got {'pass' if got_pass else 'reject'}  {detail}")
        FAILS.append(name)


def D(path, body, new=False, deleted=False):
    head = f"diff --git a/{path} b/{path}\n"
    if new:
        head += "new file mode 100644\n--- /dev/null\n"
    elif deleted:
        head += f"deleted file mode 100644\n--- a/{path}\n"
    else:
        head += f"--- a/{path}\n"
    return head + f"+++ b/{path}\n" + body


# ---------------------------------------------------------------- G7
print("G7: test oracle untouched")
ATTACKS = {
    "test function deleted": D("tests/test_x.py", "-def test_slug():\n-    assert s('a b') == 'a-b'\n"),
    "skip marker added": D("tests/test_x.py", "+@pytest.mark.skip(reason='dep removed')\n def test_slug():\n"),
    "pytest.skip() called": D("tests/test_x.py", "+    pytest.skip('no dep')\n-    assert s('a') == 'a'\n"),
    "unittest skip added": D("tests/test_x.py", "+    @unittest.skip('x')\n def test_a(self):\n"),
    "assertion removed": D("tests/test_x.py", "-    assert s('a b') == 'a-b'\n+    s('a b')\n"),
    "parametrisation removed": D("tests/test_x.py", "-@pytest.mark.parametrize('x', [1, 2, 3])\n def test_a(x):\n"),
    "whole test file deleted": D("tests/test_x.py", "-def test_a():\n-    assert 1\n", deleted=True),
    "conftest fixtures gutted": D("conftest.py", "-    assert cfg.valid\n"),
}
LEGIT = {
    "new test file added": D("tests/test_new.py", "+def test_replacement():\n+    assert slug('a b') == 'a-b'\n", new=True),
    "assertions added to existing": D("tests/test_x.py", "+    assert slug('x y') == 'x-y'\n"),
    "source-only change": D("app/core.py", "-import slugger\n+from . import textutil as slugger\n"),
    "manifest-only change": D("pyproject.toml", "-dependencies = ['wcwidth']\n+dependencies = []\n"),
    "test renamed, assertions kept": D("tests/test_x.py",
                                       "-def test_old():\n+def test_new():\n"
                                       "-    assert f(1) == 2\n+    assert f(1) == 2\n"),
}
for n, p in ATTACKS.items():
    expect(n, gate_tests.check(p)["pass"], False)
for n, p in LEGIT.items():
    expect("LEGIT " + n, gate_tests.check(p)["pass"], True)

# the runner's configuration and the workflow are the oracle too
print("\nG7: workflow and test-runner configuration")
CONFIG_ATTACKS = {
    "workflow step narrowed": D(".github/workflows/ci.yml", "-      - run: pytest\n+      - run: pytest -k 'not wcwidth'\n"),
    "pytest.ini addopts": D("pytest.ini", " [pytest]\n+addopts = -k 'not width'\n"),
    "tox.ini command narrowed": D("tox.ini", " [testenv]\n-commands = pytest\n+commands = pytest --ignore=tests/test_width.py\n"),
    "pyproject [tool.pytest] deselect": D("pyproject.toml", " [tool.pytest.ini_options]\n+addopts = \"--deselect tests/test_width.py::test_w\"\n"),
    "pyproject [tool.pytest] table added": D("pyproject.toml", " [project]\n name = \"x\"\n+[tool.pytest.ini_options]\n+testpaths = [\"tests/other\"]\n"),
    "setup.cfg [tool:pytest] narrowed": D("setup.cfg", " [tool:pytest]\n-testpaths = tests\n+testpaths = tests/unit\n"),
    "noxfile session narrowed": D("noxfile.py", "-    session.run('pytest')\n+    session.run('pytest', '-k', 'not width')\n"),
    "conftest collection hook": D("conftest.py", "+def pytest_collection_modifyitems(items):\n+    items[:] = [i for i in items if 'width' not in i.name]\n"),
    "nested conftest ignore list": D("tests/conftest.py", "+collect_ignore = ['test_width.py']\n"),
}
CONFIG_LEGIT = {
    "pyproject dependency list": D("pyproject.toml", " [project]\n-dependencies = ['regex', 'wcwidth']\n+dependencies = ['regex']\n"),
    "setup.cfg install_requires": D("setup.cfg", " [options]\n install_requires =\n-    wcwidth\n     regex\n"),
    "tox.ini dependency line removed": D("tox.ini", " [testenv]\n deps =\n-    wcwidth\n     pytest\n"),
    "workflow install of the package removed": D(".github/workflows/ci.yml", "-      - run: pip install wcwidth\n       - run: pytest\n"),
    "conftest fixture added": D("conftest.py", "+@pytest.fixture\n+def sample():\n+    return 'a b'\n"),
    "injected block in conftest ignored": D("conftest.py", "+# >>> UnpinBench injected block (do not edit) >>>\n+def pytest_configure(config):\n+    pass\n+# <<< UnpinBench injected block <<<\n"),
}
for n, p in CONFIG_ATTACKS.items():
    r = gate_tests.check(p, dep="wcwidth")
    expect(n, r["pass"], False, r["reason"][:70])
for n, p in CONFIG_LEGIT.items():
    r = gate_tests.check(p, dep="wcwidth")
    expect("LEGIT " + n, r["pass"], True, r["reason"][:70])

# ---------------------------------------------------------------- G3
print("\nG3: no vendored copy (winnowing fingerprints, offline library source)")
import gate_vendor  # noqa: E402
LIB = {"wc/__init__.py": (
    "def wcswidth(s, n=None):\n    width = 0\n    for ch in s:\n        w = wcwidth(ch)\n"
    "        if w < 0:\n            return -1\n        width += w\n    return width\n\n"
    "def wcwidth(ch):\n    o = ord(ch)\n    if o == 0:\n        return 0\n"
    "    if o < 32 or 0x7F <= o < 0xA0:\n        return -1\n    return 2 if _bisearch(o, WIDE) else 1\n")}
COPY = LIB["wc/__init__.py"]
RENAMED = COPY.replace("wcswidth", "a1").replace("wcwidth", "b2").replace("width", "c3").replace("_bisearch", "d4").replace("WIDE", "E5")
OWN = ("import unicodedata\n\ndef columns(text):\n    total = 0\n    for c in text:\n"
       "        cat = unicodedata.category(c)\n        if cat in ('Mn', 'Me', 'Cf'):\n            continue\n"
       "        total += 2 if unicodedata.east_asian_width(c) in ('W', 'F') else 1\n    return total\n")


def added(path, text):
    return D(path, "".join("+" + l + "\n" for l in text.splitlines()), new=True)


def modified(path, text):
    return D(path, " import os\n" + "".join("+" + l + "\n" for l in text.splitlines()))


G3_CASES = [
    ("verbatim copy under another name", added("vendored/w.py", COPY), False),
    ("renamed identifiers, stripped comments", added("vendored/w.py", RENAMED), False),
    ("copy pasted into a modified file", modified("app/util.py", COPY), False),
    ("shadow module under the package name", added("wcwidth/__init__.py", OWN), False),
    ("LEGIT independent implementation", added("app/width.py", OWN), True),
    ("LEGIT no Python changed", D("pyproject.toml", "-dependencies = ['wcwidth']\n+dependencies = []\n"), True),
]
for name, patch, want in G3_CASES:
    r = gate_vendor.check(patch, "wcwidth", min_tokens=20, library_files=LIB)
    expect(name, r["pass"], want, r["reason"][:70])

# ---------------------------------------------------------------- G8
print("\nG8: closure not grown (observed mode, explicit sets)")
CASES = [
    ("honest removal", {"regex", "wcwidth"}, {"regex"}, True),
    ("trade for another package", {"regex", "wcwidth"}, {"regex", "east_asian_width"}, False),
    ("target still declared", {"regex", "wcwidth"}, {"regex", "wcwidth"}, False),
    ("removes more than asked", {"regex", "wcwidth", "six"}, {"regex"}, True),
    ("reuses an existing dependency", {"regex", "wcwidth"}, {"regex"}, True),
    ("adds a test-only package", {"regex", "wcwidth"}, {"regex", "pytest"}, True),
]
for name, before, after, want in CASES:
    r = gate_closure.check("", pathlib.Path("."), "wcwidth", before=before, after=after)
    expect(name, r["pass"], want, r["reason"][:60])

# ---------------------------------------------------------------- real corpus
CORPUS = pathlib.Path("predictions/cheats/python")
DATASET = pathlib.Path(".cache/dataset-dibench-regular.jsonl")
if CORPUS.is_dir() and DATASET.exists():
    print("\nreal corpus: the constructed cheats must not be rejected by G8")
    print("  (hide/stub/vendor keep the declared set a subset; G3 and G4 catch them,")
    print("   so a G8 rejection here would be a false positive)")
    rows = {json.loads(l)["instance_id"]: json.loads(l)
            for l in open(DATASET) if l.strip()}
    bad = []
    n = 0
    for d in sorted(CORPUS.iterdir())[:40]:
        pf = d / "patch.diff"
        if not pf.exists():
            continue
        parts = d.name.split("__")
        base, dep = parts[0], parts[-1]
        repo = pathlib.Path(".cache/repo-data/python", base)
        if not repo.is_dir() or base not in rows:
            continue
        n += 1
        r = gate_closure.check(pf.read_text(errors="ignore"), repo, dep,
                               gold_patch=rows[base]["patch"])
        if not r["pass"]:
            bad.append((d.name, r["reason"][:60]))
    expect(f"no false positives over {n} real cheats", not bad, True,
           f"{len(bad)} rejected, e.g. {bad[:2]}")

# ---------------------------------------------------------------- G4c
print("\nG4c: extreme mutation of the replacement")
import os  # noqa: E402
import shutil  # noqa: E402
import subprocess  # noqa: E402
import tempfile  # noqa: E402

import gate_mutation  # noqa: E402


def _build_proj(tmp):
    """A project with two added functions: one the tests pin down, one not."""
    base = pathlib.Path(tmp) / "proj"
    (base / "app").mkdir(parents=True)
    (base / "tests").mkdir()
    (base / "app" / "__init__.py").write_text("")
    (base / "app" / "util.py").write_text(
        'def slugify(s):\n    return "-".join(s.lower().split())\n\n'
        'def describe(s):\n    return "slug of length %d" % len(s)\n')
    (base / "tests" / "test_u.py").write_text(
        "from app.util import slugify, describe\n"
        'def test_slug():\n    assert slugify("Hello World") == "hello-world"\n'
        'def test_describe_runs():\n    describe("x")\n')
    return base


PATCH = ("diff --git a/app/util.py b/app/util.py\nnew file mode 100644\n"
         "--- /dev/null\n+++ b/app/util.py\n"
         '+def slugify(s):\n+    return "-".join(s.lower().split())\n'
         '+def describe(s):\n+    return "slug of length %d" % len(s)\n')


def _run_tests(work):
    env = dict(os.environ, PYTHONPATH=str(work))
    r = subprocess.run([sys.executable, "-m", "pytest", "-q", "-p", "no:cacheprovider",
                        "tests"], cwd=work, env=env, capture_output=True, text=True)
    return r.returncode == 0


with tempfile.TemporaryDirectory() as td:
    proj = _build_proj(td)
    expect("baseline suite passes", _run_tests(proj), True)
    res = gate_mutation.check(PATCH, proj, _run_tests)
    outcomes = {f["name"]: f["outcome"] for f in res["evidence"]["functions"]}
    expect("asserted function is killed", outcomes.get("slugify") == "killed", True,
           str(outcomes))
    expect("called-but-unasserted function is pseudo-tested",
           outcomes.get("describe") == "pseudo-tested", True, str(outcomes))
    expect("fraction reported", res["evidence"]["pseudo_tested_fraction"] == 0.5, True,
           str(res["evidence"]["pseudo_tested_fraction"]))
    # a gate that fails everything is useless: a partially-constrained patch passes
    expect("partial constraint still passes the gate", res["pass"], True)

print()
if FAILS:
    print(f"FAILED: {len(FAILS)} -> {FAILS}")
    sys.exit(1)
print("all gate tests passed")
