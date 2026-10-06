#!/usr/bin/env python3
"""Is a dependency optional by design -- does the code work without it?

A pair whose package the repository explicitly handles the absence of is not a
removal task: there is nothing to remove, because the fallback already exists.
Such pairs must leave the benchmark. But deciding this needs more care than
"the import sits inside a try/except ImportError", which is what a first pass
naturally checks and which is wrong in both directions:

  textnets imports `concepts` inside try/except and the handler `raise`s after
  warning. The absence is detected, not handled. It IS a removal task.

  csachs/pflake8 tries stdlib `tomllib` FIRST and falls back to `tomli`. The
  package is the fallback, so on Python 3.11+ it is never imported. It is NOT
  a removal task.

So the question is not whether a guard exists but whether the handler
*recovers*: does control continue with something usable, or does it re-raise,
exit, or fail later. This module answers:

  recovers      the handler binds a replacement, sets a sentinel, imports
                something else, or simply passes -- the code runs on
  reraises      the handler raises (bare or new), exits, or asserts
  fallback_to   the package IS the fallback: tried after another import failed
  unguarded     no ImportError guard covers the import at all

Only `recovers` and `fallback_to` make a pair non-removable.

usage: optional_deps.py <pool.jsonl> [--repo-data DIR] [--json out.json]
"""
from __future__ import annotations

import argparse
import ast
import json
import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
from make_blocked import import_names  # noqa: E402

SKIP = ('.git', '__pycache__', 'site-packages', '/build/', '/.tox/')


def _handles_import_error(handler: ast.ExceptHandler) -> bool:
    if handler.type is None:
        return True            # bare except catches ImportError too
    txt = ast.unparse(handler.type)
    return "ImportError" in txt or "ModuleNotFoundError" in txt


def _handler_recovers(handler: ast.ExceptHandler) -> bool:
    """Does control continue usefully after the handler runs?"""
    for node in ast.walk(handler):
        if isinstance(node, ast.Raise):
            return False
        if isinstance(node, ast.Call):
            f = node.func
            name = getattr(f, "id", None) or getattr(f, "attr", None)
            if name in ("exit", "_exit"):
                return False
    return True


def classify(repo: pathlib.Path, dep: str) -> dict:
    names = set(import_names(dep))
    sites = []
    for f in repo.rglob("*.py"):
        if any(p in str(f) for p in SKIP):
            continue
        try:
            tree = ast.parse(f.read_bytes())
        except Exception:
            continue
        # Map each import to the try that guards it, tracking the TRY BODY and
        # the HANDLER bodies separately: an import inside the handler is the
        # fallback, and conflating the two spans made csachs/pflake8 -- which
        # tries stdlib tomllib first and imports tomli in the handler -- look
        # unguarded.
        guards: list[tuple[ast.Try, int, int]] = []
        handler_spans: list[tuple[ast.Try, int, int]] = []
        for node in ast.walk(tree):
            if not (isinstance(node, ast.Try)
                    and any(_handles_import_error(h) for h in node.handlers)):
                continue
            body_lines = [x.lineno for b in node.body for x in ast.walk(b)
                          if hasattr(x, "lineno")]
            if body_lines:
                guards.append((node, min(body_lines), max(body_lines)))
            for h in node.handlers:
                if not _handles_import_error(h):
                    continue
                hl = [x.lineno for x in ast.walk(h) if hasattr(x, "lineno")]
                if hl:
                    handler_spans.append((node, min(hl), max(hl)))
        for node in ast.walk(tree):
            if not isinstance(node, (ast.Import, ast.ImportFrom)):
                continue
            mods = ([a.name.split(".")[0] for a in node.names]
                    if isinstance(node, ast.Import) else [(node.module or "").split(".")[0]])
            if not any(m in names for m in mods):
                continue
            rel = str(f.relative_to(repo))
            in_handler = any(lo <= node.lineno <= hi for _t, lo, hi in handler_spans)
            if in_handler:
                sites.append(dict(file=rel, line=node.lineno, kind="fallback_to"))
                continue
            g = next((t for t, lo, hi in guards if lo <= node.lineno <= hi), None)
            if g is None:
                sites.append(dict(file=rel, line=node.lineno, kind="unguarded"))
                continue
            handlers = [h for h in g.handlers if _handles_import_error(h)]
            recovers = any(_handler_recovers(h) for h in handlers)
            sites.append(dict(file=rel, line=node.lineno,
                              kind="recovers" if recovers else "reraises"))
    kinds = {s["kind"] for s in sites}
    if not sites:
        verdict = "never imported"
    elif kinds <= {"recovers", "fallback_to"}:
        verdict = "optional by design"
    elif "unguarded" in kinds or "reraises" in kinds:
        verdict = "required"
    else:
        verdict = "mixed"
    return dict(verdict=verdict, sites=sites)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("pool")
    ap.add_argument("--repo-data", default=".cache/repo-data")
    ap.add_argument("--json", default=None)
    a = ap.parse_args()
    rows = [json.loads(l) for l in open(a.pool) if l.strip()]
    out = []
    import collections
    tally = collections.Counter()
    for r in rows:
        repo = pathlib.Path(a.repo_data) / "python" / r["instance_id"]
        if not repo.is_dir():
            continue
        c = classify(repo, r["dependency"])
        tally[c["verdict"]] += 1
        if c["verdict"] == "optional by design":
            ks = {s["kind"] for s in c["sites"]}
            print(f"  OPTIONAL  {r['instance_id'][:32]:32s} {r['dependency']:22s} {sorted(ks)}")
            for s in c["sites"][:2]:
                print(f"            {s['file']}:{s['line']} ({s['kind']})")
        out.append(dict(instance_id=r["instance_id"], dependency=r["dependency"], **c))
    print()
    for k, v in tally.most_common():
        print(f"  {v:4d}  {k}")
    if a.json:
        pathlib.Path(a.json).write_text(json.dumps(out, indent=1))


if __name__ == "__main__":
    main()
