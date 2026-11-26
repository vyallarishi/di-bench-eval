#!/usr/bin/env python3
"""Build the pinned-environment check: the gold manifest, re-run under the recorded versions.

env_snapshot.py recovers what each reported run installed from its log. This
turns that record into a check anyone can run: per repository, the unmodified
(gold) repository plus a constraints file holding the recorded versions, with
the workflow told to honour it (act --env PIP_CONSTRAINT / UV_CONSTRAINT).
Nothing about the repository or its workflow changes.

A package the logs saw with more than one version is left unpinned, and so is
the project's own distribution. Installers that resolve on their own (poetry)
do not read the constraints; envpin_report.py measures what was actually
installed, so an unpinned run cannot be mistaken for a pinned one.

Sets: envp, envp_large (one instance per pool repository, id <repo>__envp__pins).

usage:
  make_envpin.py --dataset-regular R.jsonl --dataset-large L.jsonl --repo-data DIR [--env data/environments]
"""
from __future__ import annotations

import argparse
import json
import pathlib
import re
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
import manifests as M  # noqa: E402
from make_blocked import apply_patch, multi_file_diff, own_packages  # noqa: E402

ROOT = pathlib.Path(__file__).resolve().parents[2]
FIELDS = ["instance_id", "metadata", "language", "act_command", "ci_file",
          "patch", "build_files", "env_specs"]
PINS = ".undep-constraints.txt"
ENV = f" --env PIP_CONSTRAINT=/project/{PINS} --env UV_CONSTRAINT=/project/{PINS}"


def norm(name: str) -> str:
    return re.sub(r"[-_.]+", "-", name).lower()


def pins_for(record: dict, own: set[str]) -> tuple[dict, list]:
    """The recorded versions over every job the workflow ran; (pins, jobs used).

    The act command names one job, but act also runs the jobs it needs, and the
    log labels jobs by display name, so jobs are merged rather than matched.
    """
    jobs = list(record)
    seen: dict[str, set] = {}
    for j in jobs:
        for name, vers in record[j]["packages"].items():
            seen.setdefault(name, set()).update(vers)
    pins = {}
    for name, vers in sorted(seen.items()):
        if len(vers) != 1 or name in own:
            continue
        v = next(iter(vers))
        if "+g" in v or re.search(r"\.d20\d{6}", v):
            continue                      # a version built from the checkout itself
        pins[name] = v
    return pins, jobs


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--dataset-regular", required=True)
    ap.add_argument("--dataset-large", required=True)
    ap.add_argument("--repo-data", required=True)
    ap.add_argument("--env", default=str(ROOT / "data/environments"))
    ap.add_argument("--out-root", default=str(ROOT))
    a = ap.parse_args()

    rows = {}
    for sub, path in (("regular", a.dataset_regular), ("large", a.dataset_large)):
        for line in open(path):
            if line.strip():
                r = json.loads(line)
                rows[r["instance_id"]] = (sub, r)
    pool = [json.loads(l) for l in open(ROOT / "pilot/instances.jsonl") if l.strip()]
    repo_data = pathlib.Path(a.repo_data) / "python"
    out = pathlib.Path(a.out_root)

    sets: dict[str, list] = {}
    manifest = {}
    for iid in sorted({p["instance_id"] for p in pool}):
        sub, r = rows[iid]
        repo = repo_data / iid
        bf = r["build_files"][0]
        record = json.load(open(pathlib.Path(a.env) / f"{iid}.json"))
        own = {norm(n) for n in own_packages(repo)} | {norm(r["metadata"]["name"])}
        pins, jobs = pins_for(record, own)
        files = {bf: ((repo / bf).read_text(), apply_patch(repo, bf, r["patch"])),
                 PINS: (None, "".join(f"{n}=={v}\n" for n, v in pins.items()))}
        set_name = "envp" + ("_large" if sub == "large" else "")
        mid = f"{iid}__envp__pins"
        d = out / "predictions" / set_name / "python" / mid
        d.mkdir(parents=True, exist_ok=True)
        (d / "patch.diff").write_text(multi_file_diff(files))
        sets.setdefault(set_name, []).append(
            {**{k: r[k] for k in FIELDS}, "instance_id": mid, "act_command": r["act_command"] + ENV})
        manifest[mid] = {"set": set_name, "instance_id": iid, "jobs": jobs, "pins": len(pins)}

    for set_name, srows in sets.items():
        with open(out / "pilot" / f"{set_name}.jsonl", "w") as f:
            for r in srows:
                f.write(json.dumps(r) + "\n")
        print(f"{set_name}: {len(srows)}", file=sys.stderr)
    json.dump(manifest, open(out / "pilot" / "envpin_manifest.json", "w"), indent=1, sort_keys=True)
    n = sorted(m["pins"] for m in manifest.values())
    print(f"repositories {len(n)}, pins per repository: min {n[0]}, median {n[len(n) // 2]}, max {n[-1]}",
          file=sys.stderr)


if __name__ == "__main__":
    main()
