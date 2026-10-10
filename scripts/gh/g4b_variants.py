#!/usr/bin/env python3
"""Run G4b over the pseudo_genuine cheat family, the one no structural gate sees.

A pseudo_genuine variant deletes the dependency and adds an internal module
with filler logic shaped like a real rewrite: new file, plausible names, the
call sites repointed. CI passes, every manifest and closure gate passes, and
80 of 80 of them survive the structural stack. The only thing wrong with them
is what the filler *returns*, so the only gate that can speak is the one that
runs the filler and the library on the same inputs and compares.

For each variant: the replacement module is read out of the patch (the added
file), the functions it defines that the reference trace shows the repository
calling are paired with the library's functions of the same name, and
`gate_differential.compare_callables` runs both on inputs derived from the
recorded ones. The library is imported in a subprocess (`g4b_one.py`) so a
hostile import cannot take the driver down.

Outcomes are reported separately, never pooled: CAUGHT (divergence found),
agrees, cannot speak (no reconstructible input), function not on both (the
filler does not expose the name the library does), library not importable
here. Only CAUGHT and agrees are verdicts.

usage:
  g4b_variants.py --patches DIR --traces oracle-blindness/data/traces
                  [--family pseudo_genuine] [--python PY] [--out out.json]
"""
from __future__ import annotations

import argparse
import collections
import json
import pathlib
import subprocess
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
from make_blocked import import_names  # noqa: E402

HERE = pathlib.Path(__file__).resolve().parent


def added_files(patch: str) -> dict[str, str]:
    """path -> contents, for every file the patch creates."""
    out, cur, lines = {}, None, None
    for line in patch.splitlines():
        if line.startswith("diff --git"):
            if cur and cur != "?" and lines is not None:
                out[cur] = "\n".join(lines) + "\n"
            cur, lines = None, None      # a binary file has a header and no text body
        elif line.startswith("new file mode"):
            cur = "?"
        elif line.startswith("+++ ") and cur == "?":
            cur = line[4:].split("\t")[0]
            cur = cur[2:] if cur.startswith("b/") else cur
            lines = []
        elif cur and cur != "?" and lines is not None:
            if line.startswith("+"):
                lines.append(line[1:])
            elif line.startswith("@@") or line.startswith("\\"):
                continue
    if cur and cur != "?" and lines is not None:
        out[cur] = "\n".join(lines) + "\n"
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--patches", required=True)
    ap.add_argument("--traces", default="oracle-blindness/data/traces")
    ap.add_argument("--family", default="pseudo_genuine")
    ap.add_argument("--python", default=sys.executable)
    ap.add_argument("--n", type=int, default=300)
    ap.add_argument("--out", default=None)
    a = ap.parse_args()

    rows = []
    for d in sorted(pathlib.Path(a.patches).iterdir()):
        parts = d.name.split("__")
        if len(parts) != 3 or parts[1] != a.family or not (d / "patch.diff").exists():
            continue
        iid, _, dep = parts
        trace = pathlib.Path(a.traces) / f"{iid}__trace__{dep}.jsonl"
        if not trace.exists():
            rows.append(dict(id=d.name, fn=None, outcome="no reference trace"))
            continue
        recs = [json.loads(l) for l in trace.read_text().splitlines() if l.strip()]
        files = {p: s for p, s in added_files((d / "patch.diff").read_text(errors="replace")).items()
                 if p.endswith(".py")}
        if not files:
            rows.append(dict(id=d.name, fn=None, outcome="no added module"))
            continue
        by_fn = collections.defaultdict(list)
        for r in recs:
            if r.get("level") == "usage":
                continue
            by_fn[(r.get("q") or "").split(".")[-1]].append(r)
        names = import_names(dep)
        for fn, calls in sorted(by_fn.items()):
            # the added file that defines the function; the whole set of added
            # files travels with it so a package's relative imports resolve
            defining = [pth for pth, src in files.items()
                        if f"def {fn}(" in src or f"class {fn}" in src or f"class {fn}(" in src]
            if not fn or not defining:
                continue
            spec = dict(import_names=names, files=files, defining=defining[0], fn=fn,
                        calls=calls[:200], n=a.n)
            # the spec travels through a file: a vendored package is far too
            # large for an argument vector
            import tempfile
            with tempfile.NamedTemporaryFile("w", suffix=".json", delete=False) as fh:
                json.dump(spec, fh)
                spec_path = fh.name
            p = subprocess.run([a.python, str(HERE / "g4b_one.py"), spec_path],
                               capture_output=True, text=True, timeout=600)
            pathlib.Path(spec_path).unlink(missing_ok=True)
            try:
                res = json.loads(p.stdout.strip().splitlines()[-1])
            except Exception:
                res = dict(outcome="error", reason=(p.stderr or p.stdout)[-160:])
            rows.append(dict(id=d.name, fn=fn, **res))
            print(f"  {res['outcome']:22s} {d.name[:48]:48s} {fn}")

    tally = collections.Counter(r["outcome"] for r in rows)
    print(f"\n{len(rows)} (variant, function) pairs")
    for k, v in tally.most_common():
        print(f"  {v:4d}  {k}")
    verdicts = tally["CAUGHT"] + tally["agrees"]
    if verdicts:
        print(f"\nG4b verdicts: {tally['CAUGHT']}/{verdicts} caught")
    if a.out:
        pathlib.Path(a.out).write_text(json.dumps(rows, indent=1))


if __name__ == "__main__":
    main()
