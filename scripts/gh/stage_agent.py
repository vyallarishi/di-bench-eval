#!/usr/bin/env python3
"""Stage an agent run's patches as a harness prediction set.

The agent runner writes `pilot/agent_out_<model>/python/<id>/patch.diff` and a
`dataset.jsonl` of the rows it touched. The harness expects a prediction set at
`predictions/<set>/python/<id>/patch.diff` with `pilot/<set>.jsonl` listing the
rows, and a repo-data symlink per instance so `act` can find the checkout.
This moves one into the other, and refuses to stage anything it cannot grade.

Checks before staging, because a silently dropped instance becomes a model
failure in the results table:

  the patch is non-empty and applies to the masked checkout
  the dependency named in the instance id is in the pool
  the base repository has dataset row and repo data

usage:
  stage_agent.py --run pilot/agent_out_openai-gpt-5-1 --set agent_gpt51
                 [--repo-data .cache/repo-data] [--dry-run]
"""
from __future__ import annotations

import argparse
import json
import os
import pathlib
import subprocess
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--run", required=True)
    ap.add_argument("--set", required=True)
    ap.add_argument("--repo-data", default=".cache/repo-data")
    ap.add_argument("--pool", default="pilot/instances.jsonl")
    ap.add_argument("--dry-run", action="store_true")
    ap.add_argument("--split-subsets", action="store_true",
                    help="write <set> and <set>_large separately; the harness "
                         "downloads one release subset's checkouts per run, so a "
                         "set spanning both cannot be dispatched as one")
    a = ap.parse_args()

    run = pathlib.Path(a.run)
    repo_data = pathlib.Path(a.repo_data)
    pool_rows = {(r["instance_id"], r["dependency"].replace("-", "_").lower()): r
                 for r in map(json.loads, open(a.pool))}
    pool = set(pool_rows)
    # Rows are rebuilt from the release datasets rather than read from the
    # run's own dataset.jsonl, which the runner writes only when it finishes:
    # staging must work on a run that was interrupted, since that is exactly
    # when the patches already produced matter most.
    base_rows = {}
    for ds in ("regular", "large"):
        f = pathlib.Path(".cache") / f"dataset-dibench-{ds}.jsonl"
        if f.exists():
            for line in open(f):
                if line.strip():
                    r = json.loads(line)
                    base_rows.setdefault(r["instance_id"], r)
    FIELDS = ["instance_id", "metadata", "language", "act_command", "ci_file",
              "patch", "build_files", "env_specs"]

    staged, skipped = [], []
    for d in sorted((run / "python").iterdir()):
        patch_file = d / "patch.diff"
        if not patch_file.exists():
            continue
        mid = d.name
        base = mid.split("__")[0]
        dep = mid.split("__")[-1]
        patch = patch_file.read_text(errors="replace")
        br = base_rows.get(base)
        if br is None:
            skipped.append(f"{mid}: {base} is in neither release dataset")
            continue
        row = {**{k: br[k] for k in FIELDS}, "instance_id": mid}
        if not patch.strip():
            # An empty patch means the agent changed nothing. That is a
            # legitimate outcome (and a failure), but there is nothing for the
            # harness to apply, so record it rather than stage it.
            skipped.append(f"{mid}: empty patch (agent changed nothing)")
            continue
        if (base, dep) not in pool:
            skipped.append(f"{mid}: ({base}, {dep}) is not a pool pair")
            continue
        if not (repo_data / "python" / base).is_dir():
            skipped.append(f"{mid}: no repo data for {base}")
            continue
        chk = subprocess.run(["git", "apply", "--check", str(patch_file.resolve())],
                             cwd=repo_data / "python" / base,
                             capture_output=True, text=True)
        if chk.returncode != 0:
            skipped.append(f"{mid}: does not apply: {chk.stderr.strip()[:90]}")
            continue
        subset = pool_rows[(base, dep)].get("subset", "regular")
        set_name = a.set + ("_large" if (a.split_subsets and subset == "large") else "")
        if not a.dry_run:
            t = pathlib.Path("predictions") / set_name / "python" / mid
            t.mkdir(parents=True, exist_ok=True)
            (t / "patch.diff").write_text(patch)
            link = repo_data / "python" / mid
            if not link.exists():
                os.symlink(base, link)
        staged.append((set_name, row))

    by_set: dict[str, list] = {}
    for set_name, row in staged:
        by_set.setdefault(set_name, []).append(row)
    if not a.dry_run:
        for set_name, rows_out in by_set.items():
            with open(pathlib.Path("pilot") / f"{set_name}.jsonl", "w") as f:
                for r in rows_out:
                    f.write(json.dumps(r) + "\n")

    print(f"staged {len(staged)}, skipped {len(skipped)}")
    for set_name, rows_out in sorted(by_set.items()):
        print(f"  {set_name}: {len(rows_out)}")
    for sk in skipped:
        print("  skip:", sk)
    if not a.dry_run:
        for set_name in sorted(by_set):
            print(f"wrote pilot/{set_name}.jsonl and predictions/{set_name}/")
        print("register each set in prepare.py --set and the workflow's choices, then dispatch")


if __name__ == "__main__":
    main()
