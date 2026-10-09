#!/usr/bin/env python3
"""Build the prediction set for the hand-written reference removals.

Each reference is a patch against the masked checkout: the manifest hunk
restores the gold declarations minus the removed package, and the code hunks
replace what the package did. Running it through the harness as-is would show
only that CI is green with the package *undeclared* -- which, when another
declaration still pulls the package in transitively, proves nothing. So the
scoped import blocker is injected alongside, exactly as in the screening: CI
green then means the suite passes with the package unimportable from the
repository's own frames, and the blocker's activation line in the log says the
check was live.

The resulting verdicts feed the false-rejection measurement on removals that
required rewriting code, the half the 172 over-declared removals cannot give.

usage:
  make_references.py --references DIR --dataset D --repo-data R
                     --out-results O --out-dataset J [--count-only]
"""
from __future__ import annotations

import argparse
import json
import os
import pathlib
import sys
import tempfile

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
from make_blocked import import_names, multi_file_diff, norm, own_packages, write_blocker  # noqa: E402


def match_line_endings(patch: str, repo: pathlib.Path) -> str:
    """Give each file section the line endings of the file it patches.

    A reference written on a checkout that normalised CRLF to LF will not
    apply to the harness's checkout, which keeps the repository's own endings;
    `git apply` compares context bytes exactly.
    """
    out, crlf = [], False
    for line in patch.split("\n"):
        if line.startswith("diff --git"):
            target = line.split(" b/", 1)[-1]
            f = repo / target
            crlf = f.is_file() and b"\r\n" in f.read_bytes()
        elif crlf and line[:1] in (" ", "-", "+") and not line.startswith(("+++", "---")):
            line = line.rstrip("\r") + "\r"
        out.append(line)
    return "\n".join(out)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--references", required=True)
    ap.add_argument("--dataset", required=True)
    ap.add_argument("--repo-data", required=True)
    ap.add_argument("--out-results", required=True)
    ap.add_argument("--out-dataset", required=True)
    ap.add_argument("--count-only", action="store_true")
    a = ap.parse_args()

    rows = {json.loads(l)["instance_id"]: json.loads(l) for l in open(a.dataset) if l.strip()}
    repo_data = pathlib.Path(a.repo_data)
    out_results = pathlib.Path(a.out_results)
    fields = ["instance_id", "metadata", "language", "act_command", "ci_file",
              "patch", "build_files", "env_specs"]
    out_rows, skipped = [], []
    for d in sorted(pathlib.Path(a.references).iterdir()):
        if not (d / "patch.diff").exists():
            continue
        iid, dep = d.name.rsplit("__", 1)
        row = rows.get(iid)
        repo = repo_data / "python" / iid
        if row is None or not repo.is_dir():
            skipped.append(f"{iid}: not in this dataset")
            continue
        mid = f"{iid}__ref__{norm(dep)}"
        if not a.count_only:
            ref = match_line_endings((d / "patch.diff").read_text(), repo)
            with tempfile.TemporaryDirectory() as td:
                td = pathlib.Path(td)
                files = {}
                for bfile in write_blocker(td, dep, import_names(dep), own_packages(repo), "scoped"):
                    old = (repo / bfile).read_text() if (repo / bfile).exists() else None
                    files[bfile] = (old, (td / bfile).read_text())
                blocker = multi_file_diff(files)
            o = out_results / "python" / mid
            o.mkdir(parents=True, exist_ok=True)
            (o / "patch.diff").write_text(ref.rstrip("\n") + "\n" + blocker)
            link = repo_data / "python" / mid
            if not link.exists():
                os.symlink(iid, link)
        out_rows.append({**{k: row[k] for k in fields}, "instance_id": mid})

    if a.count_only:
        print(len(out_rows))
        return
    pathlib.Path(a.out_dataset).parent.mkdir(parents=True, exist_ok=True)
    with open(a.out_dataset, "w") as f:
        for r in out_rows:
            f.write(json.dumps(r) + "\n")
    print(f"reference instances: {len(out_rows)}, skipped: {len(skipped)}", file=sys.stderr)
    for s in skipped:
        print("  skip:", s, file=sys.stderr)


if __name__ == "__main__":
    main()
