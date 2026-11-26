#!/usr/bin/env python3
"""Read a run of the gold manifests and compare what it installed with the record.

For every repository in the result directories: whether the workflow passed,
and, for each package the record pins, whether this run installed the recorded
version, another version, or printed no version for it. Works on a pinned run
(the envp sets) and on a plain gold run alike, so the two can be compared.

usage:  envpin_report.py RESULTS_DIR [RESULTS_DIR ...] [--env data/environments] [--out report.json]
"""
from __future__ import annotations

import argparse
import collections
import json
import pathlib
import re
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
from env_snapshot import read_log  # noqa: E402

ROOT = pathlib.Path(__file__).resolve().parents[2]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("roots", nargs="+")
    ap.add_argument("--env", default=str(ROOT / "data/environments"))
    ap.add_argument("--out", default=None)
    a = ap.parse_args()

    manifest = json.load(open(ROOT / "pilot/envpin_manifest.json"))
    repos = {m["instance_id"] for m in manifest.values()}
    report = {}
    for root in a.roots:
        for res in pathlib.Path(root).rglob("eval-result.json"):
            inst = res.parent.name
            repo = inst.split("__")[0]
            if repo not in repos or ("__" in inst and "__envp__" not in inst):
                continue
            pins = {}
            pin_file = ROOT / "predictions" / manifest[f"{repo}__envp__pins"]["set"] / "python" / \
                f"{repo}__envp__pins" / "patch.diff"
            for line in pin_file.read_text().splitlines():
                m = re.match(r"^\+([A-Za-z0-9_.\-]+)==(\S+)$", line)
                if m:
                    pins[m.group(1)] = m.group(2)
            got: dict[str, set] = collections.defaultdict(set)
            log = res.parent / "eval-workspace" / "exec-output.log"
            if log.exists():
                for j in read_log(log).values():
                    for name, vers in j["packages"].items():
                        got[name] |= vers
            same = sum(1 for n, v in pins.items() if got.get(n) == {v})
            other = sorted(n for n, v in pins.items() if got.get(n) and got[n] != {v})
            report[repo] = {"exec": json.load(open(res)).get("exec"), "pinned": "__envp__" in inst,
                            "pins": len(pins), "same": same, "different": len(other),
                            "not_printed": len(pins) - same - len(other), "different_names": other[:12]}

    n = len(report)
    print(f"repositories read: {n} of {len(repos)}")
    print("workflow:", dict(collections.Counter(r["exec"] for r in report.values())))
    tot = {k: sum(r[k] for r in report.values()) for k in ("pins", "same", "different", "not_printed")}
    seen = tot["same"] + tot["different"]
    print(f"recorded versions: {tot['pins']}; printed by this run {seen}, of which identical {tot['same']} "
          f"({100 * tot['same'] / max(seen, 1):.1f}%), different {tot['different']}; not printed {tot['not_printed']}")
    print("repositories with every printed version identical:",
          sum(1 for r in report.values() if r["different"] == 0 and r["same"] > 0))
    for repo, r in sorted(report.items()):
        if r["exec"] != "pass" or r["different"]:
            print(f"  {repo}: {r['exec']}, {r['same']} same, {r['different']} different {r['different_names'][:5]}")
    if a.out:
        json.dump(report, open(a.out, "w"), indent=1, sort_keys=True)


if __name__ == "__main__":
    main()
