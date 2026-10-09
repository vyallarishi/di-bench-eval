#!/usr/bin/env python3
"""Run the behavioural gate over the hand-written references, one at a time.

Each reference has its own interpreter (the version its CI runs), its own test
arguments, and, when the replacement is a new module, the module's dotted name
for the candidate phase; `oracle-blindness/data/reference_modules.tsv` holds
all three. A reference whose replacement lives inside a modified module is not
named as a target: naming it would record the project's own API as if it were
the library's, and the usage-site level observes it instead.

usage:
  run_references_g4.py --out results.json --keep DIR [--ids a,b] [--only-evaluable]
"""
from __future__ import annotations

import argparse
import json
import os
import pathlib
import subprocess
import sys

HERE = pathlib.Path(__file__).resolve().parent
ROOT = HERE.parents[1]
PYTHONS = {
    "3.8": os.path.expanduser("~/.local/share/uv/python/cpython-3.8.20-macos-x86_64-none/bin/python3"),
    "3.9": os.path.expanduser("~/.local/share/uv/python/cpython-3.9.25-macos-x86_64-none/bin/python3"),
    "3.10": os.path.expanduser("~/.local/share/uv/python/cpython-3.10.22-macos-x86_64-none/bin/python3"),
    "3.11": "/usr/local/bin/python3.11",
}
# the 11 references on which the 9 October run recorded library calls
EVALUABLE = {
    "5j9_wikitextparser__ref__wcwidth", "AppDaemon_appdaemon__ref__iso8601",
    "AppDaemon_appdaemon__ref__python_dateutil", "JeroenDelcour_tplot__ref__colorama",
    "NVIDIA_NVFlare__ref__flask_sqlalchemy", "RhinoSecurityLabs_IAMActionHunter__ref__pandas",
    "humanlayer_humanlayer__ref__python_slugify", "inducer_cgen__ref__pytools",
    "itamarst_eliot__ref__boltons", "your-tools_tbump__ref__cli_ui", "your-tools_tbump__ref__docopt",
}


def table():
    rows = []
    for line in (ROOT / "oracle-blindness/data/reference_modules.tsv").read_text().splitlines():
        if not line.strip() or line.startswith("#"):
            continue
        parts = line.split("\t")
        while len(parts) < 6:
            parts.append("")
        rows.append(dict(set=parts[0], id=parts[1], module=parts[2], kind=parts[3],
                         python=parts[4], test_args=parts[5].strip()))
    return rows


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", required=True)
    ap.add_argument("--keep", required=True)
    ap.add_argument("--ids", default=None)
    ap.add_argument("--only-evaluable", action="store_true")
    ap.add_argument("--timeout", type=int, default=1500)
    a = ap.parse_args()
    want = set(a.ids.split(",")) if a.ids else None
    results = []
    for row in table():
        if want and row["id"] not in want:
            continue
        if a.only_evaluable and row["id"] not in EVALUABLE:
            continue
        ds = ".cache/dataset-dibench-large.jsonl" if row["set"].endswith("large") else ".cache/dataset-dibench-regular.jsonl"
        out = pathlib.Path(a.keep) / f"{row['id']}.json"
        cmd = [sys.executable, str(HERE / "run_g4.py"), "--patches", f"predictions/{row['set']}/python",
               "--dataset", ds, "--repo-data", ".cache/repo-data", "--ids", row["id"],
               "--out", str(out), "--keep", str(pathlib.Path(a.keep) / row["id"]),
               "--python", PYTHONS[row["python"]], "--timeout", str(a.timeout),
               "--test-command", "{py} -m pytest -q -p no:cacheprovider " + row["test_args"]]
        if row["kind"] == "new" and row["module"]:
            cmd += ["--replacement-module", row["module"]]
        print(f"== {row['id']} (python {row['python']}, {row['kind']}: {row['module']})", flush=True)
        r = subprocess.run(cmd, cwd=ROOT, text=True, capture_output=True)
        print(r.stdout[-1500:], r.stderr[-800:] if r.returncode else "", flush=True)
        try:
            rec = json.loads(out.read_text())[0]
        except Exception as e:
            rec = dict(id=row["id"], status="driver error", why=str(e)[:200])
        rec.update(set=row["set"], replacement_kind=row["kind"], ci_python=row["python"])
        results.append(rec)
        pathlib.Path(a.out).write_text(json.dumps(results, indent=1, default=str))
    print(f"-> {a.out} ({len(results)} references)")


if __name__ == "__main__":
    main()
