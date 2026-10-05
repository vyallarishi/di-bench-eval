#!/usr/bin/env python3
"""Static import footprint of a dependency inside a repository.

Mirrors oracle-blindness/code/analysis/analyze_python.py (which only covers the
regular subset and runs as a script) so that large-subset pairs get the same
features: which files import the package, whether any of them is a test or is
reachable from a test through the internal module graph, and how many
attribute-level uses the imported names have.
"""
from __future__ import annotations

import ast
import os
import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
from make_blocked import import_names as _block_names  # noqa: E402

# pipreqs ships a large import-name -> package-name table; use it when installed
# so that e.g. django_appconf -> appconf and xstatic_font_awesome -> xstatic.
PIPREQS_MAP: dict[str, set[str]] = {}
try:
    import pipreqs
    for line in open(pathlib.Path(pipreqs.__file__).with_name("mapping"),
                     encoding="utf-8", errors="ignore"):
        if ":" in line:
            imp, pkg = line.strip().split(":", 1)
            PIPREQS_MAP.setdefault(pkg.lower().replace("-", "_").replace(".", "_"), set()).add(imp)
except ImportError:
    pass


def import_names(dep: str) -> set[str]:
    d = dep.lower().replace("-", "_").replace(".", "_")
    return set(_block_names(dep)) | PIPREQS_MAP.get(d, set())

STDLIB = set(sys.stdlib_module_names) | {"__future__", "_typeshed"}
SKIP_DIRS = {".git", ".axon", "node_modules", "venv", ".venv", "build", "dist",
             "site-packages", "__pycache__", ".tox", ".eggs", "docs", "doc",
             "examples", "example", "benchmarks", "bench"}
TEST_DIR_NAMES = {"tests", "test", "testing", "unittests", "unit_tests", "integration_tests"}


def is_test_path(rel: pathlib.Path) -> bool:
    parts = rel.parts
    if any(p in TEST_DIR_NAMES for p in parts[:-1]):
        return True
    name = parts[-1]
    return (name.startswith("test_") or name.endswith("_test.py")
            or name in ("conftest.py", "tests.py"))


def _py_files(repo: pathlib.Path):
    for dp, dns, fns in os.walk(repo):
        dns[:] = [d for d in dns if d not in SKIP_DIRS and not d.startswith(".")]
        for f in fns:
            if f.endswith(".py"):
                yield pathlib.Path(dp) / f


def module_graph(repo: pathlib.Path):
    """Per-file third-party roots and internal import edges."""
    files = list(_py_files(repo))
    mod_of: dict[str, pathlib.Path] = {}
    for f in files:
        for r in (repo / "src", repo):
            try:
                rr = f.relative_to(r)
            except ValueError:
                continue
            parts = list(rr.with_suffix("").parts)
            if parts[-1] == "__init__":
                parts = parts[:-1]
            if parts:
                mod_of.setdefault(".".join(parts), f)
            break
    file_mod = {}
    for mod, f in mod_of.items():
        file_mod.setdefault(f, mod)
    internal_top = {m.split(".")[0] for m in mod_of}

    info = {}
    for f in files:
        try:
            tree = ast.parse(f.read_bytes())
        except Exception:
            continue
        thirds, internals, aliases = {}, set(), {}
        mymod = file_mod.get(f, "")
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                for a in node.names:
                    top = a.name.split(".")[0]
                    if top in STDLIB:
                        continue
                    if top in internal_top:
                        internals.add(a.name)
                    else:
                        thirds.setdefault(top, []).append(ast.unparse(node))
                        aliases[(a.asname or a.name).split(".")[0]] = top
            elif isinstance(node, ast.ImportFrom):
                if node.level:
                    base = mymod.split(".")
                    if f.name != "__init__.py":
                        base = base[:-1]
                    if node.level > 1:
                        base = base[: len(base) - (node.level - 1)]
                    target = ".".join(base + ([node.module] if node.module else []))
                    internals.add(target)
                    for a in node.names:
                        internals.add(f"{target}.{a.name}" if target else a.name)
                elif node.module:
                    top = node.module.split(".")[0]
                    if top in STDLIB:
                        continue
                    if top in internal_top:
                        internals.add(node.module)
                        for a in node.names:
                            internals.add(f"{node.module}.{a.name}")
                    else:
                        thirds.setdefault(top, []).append(ast.unparse(node))
                        for a in node.names:
                            aliases[a.asname or a.name] = top
        # attribute-level uses of whatever the file bound from third-party imports
        uses = {}
        for node in ast.walk(tree):
            if isinstance(node, ast.Attribute) and isinstance(node.value, ast.Name):
                top = aliases.get(node.value.id)
                if top:
                    uses[top] = uses.get(top, 0) + 1
            elif isinstance(node, ast.Call) and isinstance(node.func, ast.Name):
                top = aliases.get(node.func.id)
                if top:
                    uses[top] = uses.get(top, 0) + 1
        info[f] = dict(thirds=thirds, internals=internals, uses=uses,
                       test=is_test_path(f.relative_to(repo)))

    def resolve(name):
        parts = name.split(".")
        for i in range(len(parts), 0, -1):
            m = ".".join(parts[:i])
            if m in mod_of:
                return mod_of[m]
        return None

    edges = {f: {resolve(n) for n in d["internals"]} - {None} for f, d in info.items()}
    return info, edges


def reachable_from_tests(info, edges):
    seen = {f for f, d in info.items() if d["test"]}
    stack = list(seen)
    while stack:
        f = stack.pop()
        for g in edges.get(f, ()):
            if g not in seen:
                seen.add(g)
                stack.append(g)
    return seen


class RepoIndex:
    """Build the module graph once per repository, then query per dependency."""

    def __init__(self, repo: pathlib.Path):
        self.repo = repo
        self.info, self.edges = module_graph(repo)
        self.reach = reachable_from_tests(self.info, self.edges)

    def footprint(self, dep: str) -> dict:
        names = set(import_names(dep))
        src, tests, uses = {}, [], 0
        for f, d in self.info.items():
            hit = [n for n in names if n in d["thirds"]]
            if not hit:
                continue
            rel = str(f.relative_to(self.repo))
            stmts = sorted({s for n in hit for s in d["thirds"][n]})
            n_uses = sum(d["uses"].get(n, 0) for n in hit)
            uses += n_uses
            if d["test"]:
                tests.append(rel)
            src[rel] = dict(imports=stmts, attribute_uses=n_uses, is_test=d["test"])
        reachable = any(f in self.reach for f, d in self.info.items()
                        if any(n in d["thirds"] for n in names))
        n_src = sum(1 for v in src.values() if not v["is_test"])
        return dict(footprint_files=n_src, test_reachable=reachable,
                    source_files=src, test_files=sorted(tests), attribute_uses=uses)
