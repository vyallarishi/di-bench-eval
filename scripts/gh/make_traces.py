#!/usr/bin/env python3
"""Build a prediction set that records what each library does, under real CI.

The behavioural gate needs a *reference trace*: what the repository's own code
asked the library to do, with the library present. Recording that locally fails
for most instances -- 114 of 154 suites would not run on a developer machine,
though every one of them passes in the container harness. The harness is where
the traces must be produced.

The trick is that the harness already knows how to apply a patch and replay CI.
So the "prediction" here is not a removal at all: it is the gold manifest plus
the usage recorder. CI runs exactly as it normally does, the recorder writes a
trace as a side effect, and the trace is collected from the result artifacts.

Nothing is removed and nothing should fail. An instance whose CI goes red under
this set is a signal the recorder broke that repository, not a finding about the
dependency -- which is why the recorder carries lint suppressions and writes
only to a path outside the repository's own tree.

usage:
  make_traces.py --dataset D --repo-data R --out-results O --out-dataset J
                 [--pairs pairs.json] [--limit N] [--count-only]

`pairs.json`: [{"instance_id":..., "dependency":...}, ...]. Defaults to every
pair in the benchmark pool.
"""
from __future__ import annotations

import argparse
import json
import os
import pathlib
import shutil
import subprocess
import sys
import tempfile

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
import manifests as M  # noqa: E402
from make_blocked import apply_patch, multi_file_diff  # noqa: E402
from make_blocked import import_names, own_packages  # noqa: E402
from record_usage import RECORDER  # noqa: E402

# The harness collects only eval-result.json and the CI log from each instance;
# anything written inside the act container is discarded with it. So the trace
# is emitted to STDOUT, line by line, with a marker prefix -- the CI log is the
# only channel out, and it is one the harness already captures.
#
# Each line is `UNPINTRACE <json>`. Volume is capped because a CI log that
# doubles in size risks truncation by the runner, and the first few hundred
# calls at a site carry the same information as the first few thousand.
TRACE_PATH = "/dev/stdout"
MARKER = "UNPINTRACE "
MAX_CALLS = 2000


def recorder_body(dep: str, names, own, out: str) -> str:
    body = RECORDER.format(dep=dep, names=sorted(set(names)), own=sorted(set(own or [])),
                           out=out, maxcalls=MAX_CALLS, site_exclude=[],
                           usage={}, usage_modules={})
    old_emit = '''        try:
            with open(_OUT, "a") as fh:
                fh.write(_bounded(rec) + "\\n")'''
    # Write to a DUPLICATE of fd 1 taken at interpreter start.
    #
    # pytest's default capture mode is --capture=fd: it redirects file
    # descriptor 1 itself, so neither sys.stdout.write nor os.write(1, ...)
    # reaches the CI log. Measured on tplot: 82 trace lines under
    # --capture=sys and --capture=no, zero under --capture=fd. We cannot add
    # -s to each project's own CI command, so the recorder keeps its own
    # handle: sitecustomize runs at interpreter start, before pytest installs
    # its capture, and a dup of fd 1 taken then still points at the real
    # console for the life of the process.
    new_emit = '''        try:
            os.write(_TRACE_FD, ("%s%s" % (_MARKER, _bounded(rec))
                                 + chr(10)).encode("utf-8", "replace"))'''
    assert old_emit in body, "recorder emit block changed; update make_traces"
    body = body.replace(old_emit, new_emit, 1)
    body = body.replace(
        "_MAXCALLS = ",
        '_MARKER = "%s"\n'
        "try:\n"
        "    _TRACE_FD = os.dup(1)      # before pytest can redirect fd 1\n"
        "except Exception:\n"
        "    _TRACE_FD = 1\n"
        "_MAXCALLS = " % MARKER, 1)
    body = body.replace(
        "_install()\n", "_install()\n" + '\n\ndef _unpinbench_pytest_fd(config):\n    # Loaded through conftest.py rather than sitecustomize.py, this module is\n    # imported after pytest has already redirected fd 1, so the dup above\n    # points at the capture file and every trace line is swallowed. pytest\n    # keeps the real console on its FDCapture.targetfd_save; switch to it.\n    global _TRACE_FD\n    try:\n        cap = config.pluginmanager.get_plugin("capturemanager")\n        out = getattr(getattr(cap, "_global_capturing", None), "out", None)\n        saved = getattr(out, "targetfd_save", None)\n        if saved is not None:\n            _TRACE_FD = saved\n            os.write(_TRACE_FD, ("UnpinBench recorder active (pytest saved fd %d): targets=%r"\n                                 % (saved, _TARGETS) + chr(10)).encode("utf-8", "replace"))\n    except Exception:\n        pass\n\n\npytest_configure = _unpinbench_pytest_fd\n', 1)
    assert "_unpinbench_pytest_fd" in body, "recorder body has no trailing _install() call"
    return body


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--dataset", required=True)
    ap.add_argument("--repo-data", required=True)
    ap.add_argument("--out-results", required=True)
    ap.add_argument("--out-dataset", required=True)
    ap.add_argument("--pairs", default="pilot/instances.jsonl")
    ap.add_argument("--limit", type=int, default=0)
    ap.add_argument("--count-only", action="store_true")
    a = ap.parse_args()

    rows = {json.loads(l)["instance_id"]: json.loads(l)
            for l in open(a.dataset) if l.strip()}
    repo_data = pathlib.Path(a.repo_data)
    out_results = pathlib.Path(a.out_results)
    fields = ["instance_id", "metadata", "language", "act_command", "ci_file",
              "patch", "build_files", "env_specs"]

    pairs = []
    p = pathlib.Path(a.pairs)
    if p.suffix == ".jsonl":
        for line in open(p):
            if line.strip():
                r = json.loads(line)
                pairs.append((r["instance_id"], r["dependency"]))
    else:
        pairs = [(x["instance_id"], x["dependency"]) for x in json.load(open(p))]
    if a.limit:
        pairs = pairs[: a.limit]

    out_rows, skipped = [], []
    for iid, dep in pairs:
        row = rows.get(iid)
        repo = repo_data / "python" / iid
        if row is None or not repo.is_dir():
            skipped.append(f"{iid}: not in this dataset")
            continue
        bf = row["build_files"][0]
        try:
            masked = (repo / bf).read_text()
            gold = apply_patch(repo, bf, row["patch"])
            if M.norm(dep) not in M.declared(bf, gold):
                skipped.append(f"{iid}/{dep}: not declared in gold")
                continue
        except Exception as e:
            skipped.append(f"{iid}/{dep}: {type(e).__name__}")
            continue

        mid = f"{iid}__trace__{M.norm(dep)}"
        if not a.count_only:
            body = recorder_body(dep, import_names(dep), own_packages(repo), TRACE_PATH)
            files = {bf: (masked, gold)}          # restore the gold manifest
            for name in ("sitecustomize.py", "conftest.py"):
                old = (repo / name).read_text() if (repo / name).exists() else None
                marker = ("# >>> UnpinBench injected block (do not edit) >>>\n"
                          + body.rstrip("\n")
                          + "\n# <<< UnpinBench injected block <<<\n")
                files[name] = (old, marker + ("\n" + old if old else ""))
            patch = multi_file_diff(files)
            d = out_results / "python" / mid
            d.mkdir(parents=True, exist_ok=True)
            (d / "patch.diff").write_text(patch)
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
    print(f"trace instances: {len(out_rows)}, skipped: {len(skipped)}", file=sys.stderr)
    for s in skipped[:20]:
        print("  skip:", s, file=sys.stderr)


if __name__ == "__main__":
    main()
