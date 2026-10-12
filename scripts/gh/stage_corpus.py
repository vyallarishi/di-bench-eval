#!/usr/bin/env python3
"""Stage 617-corpus variants against the masked checkout, with the block.

The corpus patches are written against the *gold* manifest, as its README
says; the harness applies a prediction to the *masked* one. Applying them
as-is does not merely fail: git apply falls through to unix patch, the
manifest hunk lands with the wrong context, and both declarations disappear
instead of one. The run then reports a build error that says nothing about
the variant. The first C18 attempt failed exactly this way.

So each variant is rebuilt: the manifest is recomputed from the masked text
as gold-minus-the-target, the variant's own added and modified files are
carried over, and the scoped block is injected as it is for the references.

usage:
  stage_corpus.py --corpus DIR --family mutant --set mutantci [--dry-run]
"""
from __future__ import annotations

import argparse
import json
import os
import pathlib
import subprocess
import sys
import tempfile

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
import manifests as M  # noqa: E402
from g4b_variants import added_files  # noqa: E402
from make_blocked import (apply_patch, import_names, multi_file_diff,  # noqa: E402
                          own_packages, write_blocker)


def modified_files(patch: str) -> set[str]:
    """Paths the patch changes but does not create."""
    out, new = set(), set()
    cur = None
    for line in patch.splitlines():
        if line.startswith("diff --git"):
            cur = line.split(" b/")[-1]
        elif line.startswith("new file mode") and cur:
            new.add(cur)
    for line in patch.splitlines():
        if line.startswith("diff --git"):
            p = line.split(" b/")[-1]
            if p not in new:
                out.add(p)
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--corpus", required=True)
    ap.add_argument("--family", required=True)
    ap.add_argument("--set", required=True)
    ap.add_argument("--repo-data", default=".cache/repo-data")
    ap.add_argument("--pool", default="pilot/instances.jsonl")
    ap.add_argument("--dry-run", action="store_true")
    a = ap.parse_args()

    rows = {}
    for ds in ("regular", "large"):
        f = pathlib.Path(".cache") / f"dataset-dibench-{ds}.jsonl"
        if f.exists():
            for line in open(f):
                if line.strip():
                    r = json.loads(line)
                    rows.setdefault(r["instance_id"], r)
    pool = {(r["instance_id"], r["dependency"].replace("-", "_").lower()): r
            for r in map(json.loads, open(a.pool))}
    repo_data = pathlib.Path(a.repo_data)
    FIELDS = ["instance_id", "metadata", "language", "act_command", "ci_file",
              "patch", "build_files", "env_specs"]

    staged, skipped = [], []
    for d in sorted(pathlib.Path(a.corpus).iterdir()):
        if f"__{a.family}__" not in d.name or not (d / "patch.diff").exists():
            continue
        base = d.name.split(f"__{a.family}__")[0]
        dep = d.name.split("__")[-1]
        if (base, dep) not in pool:
            skipped.append(f"{d.name}: not a current pool pair")
            continue
        row = rows.get(base)
        repo = repo_data / "python" / base
        if row is None or not repo.is_dir():
            skipped.append(f"{d.name}: no dataset row or checkout")
            continue
        bf = row["build_files"][0]
        try:
            masked = (repo / bf).read_text()
            gold = apply_patch(repo, bf, row["patch"])
            after = M.remove(bf, gold, dep)
            if after is None:
                skipped.append(f"{d.name}: cannot edit the manifest")
                continue
        except Exception as e:
            skipped.append(f"{d.name}: {type(e).__name__}")
            continue

        text = (d / "patch.diff").read_text(errors="replace")
        files = {bf: (masked, after)}
        for rel, content in added_files(text).items():
            if rel != bf:
                files[rel] = (None, content)
        # a modified file is replayed by applying the variant's patch to a
        # scratch copy of the gold tree, then taking the result
        mods = [p for p in modified_files(text) if p != bf and (repo / p).exists()]
        if mods:
            with tempfile.TemporaryDirectory() as td:
                t = pathlib.Path(td)
                subprocess.run(["cp", "-R", str(repo) + "/.", str(t)], capture_output=True)
                (t / bf).write_text(gold)
                subprocess.run(["git", "apply", "--reject", "--whitespace=nowarn", "-"],
                               cwd=t, input=text, capture_output=True, text=True)
                for p in mods:
                    if (t / p).exists():
                        files[p] = ((repo / p).read_text(errors="ignore"),
                                    (t / p).read_text(errors="ignore"))
        mid = f"{base}__{a.family}__{dep}"
        with tempfile.TemporaryDirectory() as td:
            t = pathlib.Path(td)
            for b in write_blocker(t, dep, import_names(dep), own_packages(repo), "scoped"):
                old = repo / b
                files[b] = (old.read_text(errors="ignore") if old.exists() else None,
                            (t / b).read_text())
            patch = multi_file_diff(files)
        chk = subprocess.run(["git", "apply", "--check", "-"], cwd=repo,
                             input=patch, capture_output=True, text=True)
        if chk.returncode != 0:
            skipped.append(f"{mid}: rebuilt patch does not apply: {chk.stderr.strip()[:70]}")
            continue
        if not a.dry_run:
            o = pathlib.Path("predictions") / a.set / "python" / mid
            o.mkdir(parents=True, exist_ok=True)
            (o / "patch.diff").write_text(patch)
            link = repo_data / "python" / mid
            if not link.exists():
                os.symlink(base, link)
        staged.append({**{k: row[k] for k in FIELDS}, "instance_id": mid})

    if not a.dry_run and staged:
        with open(pathlib.Path("pilot") / f"{a.set}.jsonl", "w") as f:
            for r in staged:
                f.write(json.dumps(r) + "\n")
    print(f"{a.family}: staged {len(staged)}, skipped {len(skipped)}")
    for s in skipped[:8]:
        print("  skip:", s)


if __name__ == "__main__":
    main()
