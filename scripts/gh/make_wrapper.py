#!/usr/bin/env python3
"""The must-accept control: a correct removal the gate has never seen.

The counterfeit study shows the gate rejects every fake it can observe. On its
own that is consistent with a degenerate gate that rejects everything not
byte-identical, and the only evidence against that reading is five references
the gate was tuned on. This builds the opposite control, in bulk, with
correctness guaranteed by construction rather than by an author's intent.

The construction: re-point the repository's imports at a thin module of its
own that forwards every call to the library. The declaration moves out of the
manifest, the call sites change, a new module appears, and the behaviour is
*provably identical* because the same code executes. A removal-shaped
submission that is correct by construction, authored by nobody, and
structurally unlike the hand-written references the gate was tuned on.

The gate MUST accept it. Any rejection is a false rejection on an input that
could not have been tuned for, which is exactly the quantity the evaluation
is missing.

Stated plainly, because the write-up has to: this is a *degenerate* removal.
The library is still installed and still does the work, so it does not test
whether a replacement is correct -- it tests whether the gate's notion of
behavioural equivalence is sound. It is a control, not a task, and it stands
alongside human-written references rather than replacing them.

usage:
  make_wrapper.py --observable observability.json --traces DIR --repo-data R
                  --dataset D... --out-predictions predictions/wrapper
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
from make_pseudo import imported_names, importing_files, rewire  # noqa: E402


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--observable", required=True)
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
    obs = json.load(open(a.observable))["pairs"]
    if a.limit:
        obs = obs[: a.limit]

    made, skipped = [], collections.Counter()
    for key in obs:
        iid, dep = key.split("__trace__")
        row = rows.get(iid)
        repo = pathlib.Path(a.repo_data) / "python" / iid
        trace = pathlib.Path(a.traces) / f"{key}.jsonl"
        if row is None or not repo.is_dir() or not trace.exists():
            skipped["no row, repo, or trace"] += 1
            continue
        recs = [json.loads(l) for l in trace.read_text().splitlines() if l.strip()]
        fns = sorted({(r.get("q") or "").split(".")[-1] for r in recs
                      if (r.get("q") or "").split(".")[-1].isidentifier()})
        names = import_names(dep)
        files = importing_files(repo, names)
        if not files or not fns:
            skipped["no importing file, or no recorded function"] += 1
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

        wanted: set[str] = set()
        for rel in files:
            wanted |= imported_names((repo / rel).read_text(errors="ignore"), names)
        wanted |= set(fns)
        pkg = files[0].split("/")[0] if "/" in files[0] else ""
        modfile = (pkg + "/" if pkg else "") + f"_forward_{norm(dep)}.py"
        dotted = (pkg + "." if pkg else "") + f"_forward_{norm(dep)}"
        # the forwarding module: same behaviour, by construction
        root = names[0]
        body = [f'"""Forwarding shim for {dep}: every call reaches the library."""',
                f"import {root} as _lib", ""]
        for sym in sorted(wanted):
            body += [f"{sym} = getattr(_lib, {sym!r}, None)"]
        src = "\n".join(body) + "\n"
        try:
            ast.parse(src)
        except SyntaxError:
            skipped["shim does not parse"] += 1
            continue

        changes = {bf: ((repo / bf).read_text(errors="ignore"), after),
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
        mid = f"{iid}__wrapper__{norm(dep)}"
        d = pathlib.Path(a.out_predictions) / "python" / mid
        d.mkdir(parents=True, exist_ok=True)
        (d / "patch.diff").write_text(multi_file_diff(changes))
        made.append(dict(id=mid, instance_id=iid, dependency=dep,
                         functions=fns, files_rewired=n))

    print(f"built {len(made)} must-accept controls")
    for k, v in skipped.most_common():
        print(f"  skipped {v:4d}  {k}")
    pathlib.Path(a.out_predictions).mkdir(parents=True, exist_ok=True)
    (pathlib.Path(a.out_predictions) / "index.json").write_text(json.dumps(made, indent=1))


if __name__ == "__main__":
    main()
