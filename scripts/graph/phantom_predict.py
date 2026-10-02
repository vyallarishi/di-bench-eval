#!/usr/bin/env python3
"""Dependency-graph phantom predictor.

For every declared dependency D of an instance, decide statically whether D is
also in the transitive requires-closure of the OTHER declared dependencies,
using PyPI metadata (requires_dist, extras-conditioned requirements ignored).
If so, deleting D's declaration leaves D installed: a phantom.

usage: phantom_predict.py <dataset.jsonl> <repo_data> <gold_results_dir> <out.json> [--instances a,b,c]
"""
import json, pathlib, re, subprocess, sys, tempfile, shutil, functools, urllib.request, time

try:
    import tomllib
except ImportError:
    import tomli as tomllib
NAME_RE = re.compile(r"^\s*([A-Za-z0-9][A-Za-z0-9._-]*)")
norm = lambda n: n.lower().replace('-', '_').replace('.', '_')
CACHE = {}


def apply_patch(repo, bf, patch):
    with tempfile.TemporaryDirectory() as td:
        td = pathlib.Path(td); shutil.copy(repo / bf, td / bf); (td / 'p.diff').write_text(patch)
        r = subprocess.run(['git', 'apply', '--allow-empty', '--ignore-whitespace', '--ignore-space-change', 'p.diff'], cwd=td, capture_output=True, text=True)
        if r.returncode != 0:
            shutil.copy(repo / bf, td / bf)
            subprocess.run(['patch', '--batch', '--fuzz=5', '-p1', '-i', 'p.diff'], cwd=td, capture_output=True, text=True)
        return (td / bf).read_text()


def declared(text):
    d = tomllib.loads(text); po = d.get('tool', {}).get('poetry', {})
    if po:
        return [k for k in (po.get('dependencies') or {}) if k.lower() != 'python']
    return [NAME_RE.match(x).group(1) for x in d.get('project', {}).get('dependencies', []) or [] if NAME_RE.match(x)]


def requires(pkg):
    """Direct unconditional requirements of a package's latest release, from PyPI."""
    key = norm(pkg)
    if key in CACHE:
        return CACHE[key]
    out = set()
    try:
        with urllib.request.urlopen(f'https://pypi.org/pypi/{pkg}/json', timeout=20) as r:
            data = json.load(r)
        for req in data.get('info', {}).get('requires_dist') or []:
            if 'extra ==' in req or 'extra==' in req:
                continue
            m = NAME_RE.match(req)
            if m:
                out.add(norm(m.group(1)))
    except Exception:
        pass
    CACHE[key] = out
    time.sleep(0.05)
    return out


def closure(pkgs, depth=6):
    seen = set(); frontier = {norm(p) for p in pkgs}
    for _ in range(depth):
        nxt = set()
        for p in frontier:
            if p in seen:
                continue
            seen.add(p)
            nxt |= requires(p) - seen
        frontier = nxt
        if not frontier:
            break
    return seen | frontier


def main():
    ds, repo_data, gold_dir, out = sys.argv[1], pathlib.Path(sys.argv[2]), pathlib.Path(sys.argv[3]), pathlib.Path(sys.argv[4])
    only = None
    for a in sys.argv[5:]:
        if a.startswith('--instances='):
            only = set(a.split('=', 1)[1].split(','))
    gold_pass = {json.load(open(f))['instance_id'] for f in gold_dir.rglob('eval-result.json') if json.load(open(f)).get('exec') == 'pass'}
    rows = [json.loads(l) for l in open(ds) if l.strip()]
    result = {}
    for r in rows:
        iid = r['instance_id']
        if r['language'].lower() != 'python' or iid not in gold_pass or (only and iid not in only):
            continue
        bf = r['build_files'][0]
        deps = declared(apply_patch(repo_data / iid, bf, r['patch']))
        per = {}
        for d in deps:
            others = [o for o in deps if o != d]
            per[norm(d)] = norm(d) in closure(others)
        result[iid] = per
        print(iid, sum(per.values()), 'of', len(per), 'predicted phantom', flush=True)
    json.dump(result, open(out, 'w'), indent=1)


if __name__ == '__main__':
    main()
