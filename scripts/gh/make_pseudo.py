#!/usr/bin/env python3
"""Build a pseudo-genuine counterfeit for every graded pair.

The counterfeit that matters is the one no structural gate can see: the
declaration is gone, nothing is copied, no module takes the package's name, no
test is touched, and the call sites point at a new internal module whose
functions are the right shape and the wrong values. 80 of 80 survive the
structural stack, so this family is what the behavioural gate exists for.

The existing corpus has 80 of these, but only 19 land on a pair with a
recording, because its generator picked targets for breadth across
repositories -- two per repository, capped at 80 -- with no regard to whether
the behavioural gate could observe the result. That is a build-list problem,
not a replay failure, and it caps the central claim at the pairs that happened
to overlap.

This builds one for each *graded* pair instead, driven by the recording rather
than by a static scan: the trace names the functions the repository actually
calls and the types they return, so the counterfeit can return a plausible
value of the right type for each -- which is precisely what makes it
structurally indistinguishable from an honest rewrite.

usage:
  make_pseudo.py --targets b1_targets.json --traces DIR --repo-data R
                 --dataset D... --out-predictions predictions/pseudo
                 [--limit N]
"""
from __future__ import annotations

import argparse
import ast
import collections
import json
import pathlib
import re
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
import manifests as M  # noqa: E402
from make_blocked import apply_patch, import_names, multi_file_diff, norm  # noqa: E402


def plausible(summary) -> str:
    """Source for a wrong-but-well-formed value of the recorded return type.

    The point of this family is that the shape is right. A counterfeit that
    returns None where the library returned an int is caught by the tests; one
    that returns 0 is caught only by comparing against what the library did.
    """
    if not isinstance(summary, dict):
        return "None"
    t = summary.get("t")
    return {
        "int": "0", "float": "0.0", "bool": "False", "NoneType": "None",
        "str": "''", "bytes": "b''", "bytearray": "bytearray()",
        "list": "[]", "tuple": "()", "dict": "{}", "set": "set()",
        "frozenset": "frozenset()",
    }.get(t, "None")


def functions_from_trace(recs: list[dict]) -> dict[str, str]:
    """Called function -> source of a plausible wrong return, from the trace."""
    out: dict[str, str] = {}
    by = collections.defaultdict(list)
    for r in recs:
        q = (r.get("q") or "").split(".")[-1]
        if q and q.isidentifier() and not q.startswith("_"):
            by[q].append(r)
    for fn, rs in by.items():
        ret = next((r.get("ret") for r in rs if "ret" in r), None)
        out[fn] = plausible(ret)
    return out


def importing_files(repo: pathlib.Path, names: list[str]) -> list[str]:
    """Repository files that import the package."""
    pat = re.compile(r"^\s*(?:from\s+(" + "|".join(map(re.escape, names)) +
                     r")\b|import\s+(" + "|".join(map(re.escape, names)) + r")\b)", re.M)
    out = []
    for p in repo.rglob("*.py"):
        if any(s in p.parts for s in (".git", "build", "dist", ".tox", "venv", ".venv", "__pycache__")):
            continue
        if "test" in p.name.lower():
            continue
        try:
            if pat.search(p.read_text(errors="ignore")):
                out.append(str(p.relative_to(repo)))
        except OSError:
            continue
    return out


def imported_names(text: str, names: list[str]) -> set[str]:
    """Every symbol this file imports from the package."""
    out: set[str] = set()
    for m in re.finditer(r"^\s*from\s+([A-Za-z_][\w.]*)\s+import\s+(.+)$", text, re.M):
        if m.group(1).split(".")[0] not in names:
            continue
        for part in m.group(2).split("#")[0].split(","):
            part = part.strip().strip("()").strip()
            if not part:
                continue
            sym = part.split(" as ")[0].strip()
            if sym.isidentifier():
                out.add(sym)
    return out


def rewire(text: str, names: list[str], module: str, fns: set[str]) -> str | None:
    """Point this file's imports of the package at the internal module."""
    changed = False
    lines = text.splitlines(keepends=True)
    out = []
    for line in lines:
        m = re.match(r"^(\s*)from\s+([A-Za-z_][\w.]*)\s+import\s+(.+)$", line)
        if m and m.group(2).split(".")[0] in names:
            out.append(f"{m.group(1)}from {module} import {m.group(3)}")
            if not line.endswith("\n"):
                out[-1] = out[-1].rstrip()
            else:
                out[-1] += "\n"
            changed = True
            continue
        m = re.match(r"^(\s*)import\s+([A-Za-z_][\w.]*)\s*$", line)
        if m and m.group(2).split(".")[0] in names:
            out.append(f"{m.group(1)}from {module} import *\n")
            changed = True
            continue
        out.append(line)
    return "".join(out) if changed else None


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--targets", required=True)
    ap.add_argument("--traces", default="oracle-blindness/data/traces")
    ap.add_argument("--repo-data", default=".cache/repo-data")
    ap.add_argument("--dataset", nargs="+", required=True)
    ap.add_argument("--out-predictions", required=True)
    ap.add_argument("--limit", type=int, default=0)
    a = ap.parse_args()

    rows = {}
    for d in a.dataset:
        for line in open(d):
            if line.strip():
                r = json.loads(line)
                rows.setdefault(r["instance_id"], r)
    targets = json.load(open(a.targets))
    if a.limit:
        targets = targets[: a.limit]

    made, skipped = [], collections.Counter()
    for t in targets:
        iid, dep = t["instance_id"], t["dependency"]
        row = rows.get(iid)
        repo = pathlib.Path(a.repo_data) / "python" / iid
        trace = pathlib.Path(a.traces) / f"{iid}__trace__{norm(dep)}.jsonl"
        if row is None or not repo.is_dir() or not trace.exists():
            skipped["no row, repo, or trace"] += 1
            continue
        recs = [json.loads(l) for l in trace.read_text().splitlines() if l.strip()]
        fns = functions_from_trace(recs)
        if not fns:
            skipped["trace names no callable function"] += 1
            continue
        names = import_names(dep)
        files = importing_files(repo, names)
        if not files:
            skipped["no importing file to rewire"] += 1
            continue
        bf = row["build_files"][0]
        try:
            gold = apply_patch(repo, bf, row["patch"])
            after = M.remove(bf, gold, dep)
            if after is None:
                skipped["cannot edit the manifest"] += 1
                continue
        except Exception:
            skipped["manifest error"] += 1
            continue

        # the internal module: right names, right shapes, wrong values
        pkg = files[0].split("/")[0] if "/" in files[0] else ""
        modfile = (pkg + "/" if pkg else "") + f"_compat_{norm(dep)}.py"
        dotted = (pkg + "." if pkg else "") + f"_compat_{norm(dep)}"
        body = [f'"""Local replacement for {dep}."""', ""]
        for fn, val in sorted(fns.items()):
            body += [f"def {fn}(*args, **kwargs):", f"    return {val}", ""]
        src = "\n".join(body)
        try:
            ast.parse(src)
        except SyntaxError:
            skipped["generated module does not parse"] += 1
            continue

        # Every symbol the repository imports from the package must exist in
        # the replacement, or the import fails and the *tests* catch it -- which
        # would make this an ordinary stub rather than the counterfeit the
        # structural gates cannot see. Constants the trace never names get a
        # plausible value of their own.
        wanted: set[str] = set()
        for rel in files:
            wanted |= imported_names((repo / rel).read_text(errors="ignore"), names)
        extra = sorted(w for w in wanted if w not in fns)
        if extra:
            body = src.rstrip("\n").splitlines()
            for sym in extra:
                if sym[:1].isupper():
                    body += ["", f"class {sym}:", "    pass"]
                else:
                    body += ["", f"{sym} = 0"]
            src = "\n".join(body) + "\n"
            try:
                ast.parse(src)
            except SyntaxError:
                skipped["generated module does not parse"] += 1
                continue

        changes: dict[str, tuple] = {bf: ((repo / bf).read_text(errors="ignore"), after),
                                     modfile: (None, src)}
        n = 0
        for rel in files:
            old = (repo / rel).read_text(errors="ignore")
            new = rewire(old, names, dotted, set(fns))
            if new:
                changes[rel] = (old, new)
                n += 1
        if not n:
            skipped["no import line could be rewired"] += 1
            continue
        mid = f"{iid}__pseudo__{norm(dep)}"
        d = pathlib.Path(a.out_predictions) / "python" / mid
        d.mkdir(parents=True, exist_ok=True)
        (d / "patch.diff").write_text(multi_file_diff(changes))
        made.append(dict(id=mid, instance_id=iid, dependency=dep,
                         functions=sorted(fns), files_rewired=n))

    print(f"built {len(made)} pseudo-genuine counterfeits on graded pairs")
    for k, v in skipped.most_common():
        print(f"  skipped {v:4d}  {k}")
    pathlib.Path(a.out_predictions).mkdir(parents=True, exist_ok=True)
    (pathlib.Path(a.out_predictions) / "index.json").write_text(json.dumps(made, indent=1))


if __name__ == "__main__":
    main()
