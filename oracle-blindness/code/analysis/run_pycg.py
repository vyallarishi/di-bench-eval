#!/usr/bin/env python3
"""Run PyCG over one or more repositories and store call graphs as JSON.

usage: run_pycg.py <pycg_python> <repo_data_dir> <out_dir> <instance_id>... [--timeout S]
"""
import json, os, pathlib, subprocess, sys, time

SKIP = {'.git', '.axon', 'node_modules', 'venv', '.venv', 'build', 'dist', 'site-packages', '__pycache__', '.tox', '.eggs', '.mypy_cache', '.pytest_cache'}


def py_files(repo: pathlib.Path):
    out = []
    for dp, dns, fns in os.walk(repo):
        dns[:] = [d for d in dns if d not in SKIP and not d.startswith('.')]
        for f in fns:
            if f.endswith('.py'):
                out.append(os.path.relpath(os.path.join(dp, f), repo))
    return sorted(out)


def main():
    args = [a for a in sys.argv[1:] if not a.startswith('--')]
    timeout = 600
    max_iter = 3
    for a in sys.argv[1:]:
        if a.startswith('--timeout='):
            timeout = int(a.split('=', 1)[1])
        if a.startswith('--max-iter='):
            max_iter = int(a.split('=', 1)[1])
    py, repo_data, out_dir, ids = args[0], pathlib.Path(args[1]), pathlib.Path(args[2]), args[3:]
    for a in sys.argv[1:]:
        if a.startswith('--ids-file='):
            ids = [l.strip() for l in open(a.split('=', 1)[1]) if l.strip()]
    out_dir.mkdir(parents=True, exist_ok=True)
    status = {}
    for iid in ids:
        repo = repo_data / iid
        files = py_files(repo)
        out = out_dir / f'{iid}.json'
        if out.exists() and out.stat().st_size > 2:
            status[iid] = 'cached'; continue
        t0 = time.time()
        try:
            r = subprocess.run([py, '-m', 'pycg', '--package', '.', '--max-iter', str(max_iter), *files, '-o', str(out)], cwd=repo, capture_output=True, text=True, timeout=timeout)
            ok = r.returncode == 0 and out.exists() and out.stat().st_size > 2
            status[iid] = f"ok {len(files)} files {time.time() - t0:.0f}s" if ok else f"fail rc={r.returncode}: {(r.stderr or r.stdout)[-200:].strip()}"
        except subprocess.TimeoutExpired:
            status[iid] = f'timeout after {timeout}s'
        print(iid, '->', status[iid], flush=True)
    json.dump(status, open(out_dir / '_status.json', 'w'), indent=1)


if __name__ == '__main__':
    main()
