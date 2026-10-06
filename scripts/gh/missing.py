#!/usr/bin/env python3
"""Find which instances of an evaluation set still have no result, and re-run them.

GitHub's hosted runners occasionally stop a job mid-shard ("The runner has
received a shutdown signal"); the shard's results are then never uploaded.
This lists the dataset indices still missing, as contiguous ranges, and can
dispatch one workflow run per range.

usage: missing.py --set SET --subset regular|large --results DIR [DIR ...]
                  [--runs RUN_ID ...] [--dispatch] [--repo vyallarishi/di-bench-eval]

--runs downloads those runs' result artifacts into the first --results DIR first.
Index order is the one prepare.py uses: pilot/<set>.jsonl for pre-built sets,
the Python rows of the release dataset for gold/recovered/mutation.
"""
import argparse
import json
import pathlib
import subprocess

PREBUILT = {"cheats", "agent", "blocked", "blocked_large", "scoped", "scoped_large", "all", "all_large", "trace", "trace_large"}


def expected_ids(s: str, subset: str) -> list[str]:
    if s in PREBUILT:
        return [json.loads(l)["instance_id"] for l in open(f"pilot/{s}.jsonl") if l.strip()]
    rows = [json.loads(l) for l in open(f".cache/dataset-dibench-{subset}.jsonl") if l.strip()]
    return [r["instance_id"] for r in rows if r["language"].lower() == "python"]


def found_ids(dirs) -> set[str]:
    out = set()
    for d in dirs:
        for f in pathlib.Path(d).rglob("eval-result.json"):
            try:
                out.add(json.loads(f.read_text())["instance_id"])
            except Exception:
                pass
    return out


def ranges(idx: list[int]):
    out, start, prev = [], None, None
    for i in idx:
        if start is None:
            start = prev = i
        elif i == prev + 1:
            prev = i
        else:
            out.append((start, prev + 1))
            start = prev = i
    if start is not None:
        out.append((start, prev + 1))
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--set", required=True)
    ap.add_argument("--subset", default="regular", choices=["regular", "large"])
    ap.add_argument("--results", nargs="+", required=True)
    ap.add_argument("--runs", nargs="*", default=[])
    ap.add_argument("--dispatch", action="store_true")
    ap.add_argument("--repo", default="vyallarishi/di-bench-eval")
    ap.add_argument("--timeout", default="1200")
    a = ap.parse_args()

    for run in a.runs:
        dest = pathlib.Path(a.results[0]) / run
        subprocess.run(["gh", "run", "download", run, "-R", a.repo, "-p", f"results-{a.set}*",
                        "-D", str(dest)], capture_output=True, text=True)
    exp = expected_ids(a.set, a.subset)
    have = found_ids(a.results)
    missing = [i for i, iid in enumerate(exp) if iid not in have]
    print(f"{a.set}: {len(exp)} expected, {len(exp) - len(missing)} have results, {len(missing)} missing")
    rs = ranges(missing)
    for s, e in rs:
        print(f"  range {s},{e}  ({e - s} instances: {exp[s]}{' ...' if e - s > 1 else ''})")
    if a.dispatch:
        for s, e in rs:
            r = subprocess.run(["gh", "workflow", "run", "dibench-eval.yml", "-R", a.repo, "--ref", "main",
                                "-f", f"set={a.set}", "-f", f"subset={a.subset}", "-f", f"range={s},{e}",
                                "-f", f"timeout={a.timeout}"], capture_output=True, text=True)
            print(f"  dispatched {s},{e}: {'ok' if r.returncode == 0 else r.stderr.strip()}")


if __name__ == "__main__":
    main()
