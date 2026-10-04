#!/usr/bin/env python3
"""Symbol-level E3: which declared dependencies are reachable from tests in the
call graph, how large each dependency's used API surface is, and how well the
static graph predicts the executed deletion outcomes.

usage: symbol_reachability.py <cg_dir> <per_dep_csv> <gold_results> <mutation_results> <pipreqs_mapping_or_-> <out.md>
"""
import collections, csv, json, pathlib, re, sys

SKIP_DIRS = {'.git', '.axon', 'node_modules', 'venv', '.venv', 'build', 'dist', 'site-packages', '__pycache__', '.tox', '.eggs'}


def internal_roots(repo):
    """Top-level module names that belong to the repository itself (incl. src/ layouts)."""
    roots = set()
    for base in (repo, repo / 'src'):
        if not base.exists():
            continue
        for p in base.iterdir():
            if p.name in SKIP_DIRS or p.name.startswith('.'):
                continue
            if p.is_dir() and any(p.rglob('*.py')):
                roots.add(p.name)
            elif p.suffix == '.py':
                roots.add(p.stem)
    return roots

REPO_DATA = pathlib.Path('.cache/repo-data/python')

cg_dir, per_dep_csv, gold_dir, mut_dir, mapping_path, out_md = [pathlib.Path(a) if a != '-' else None for a in sys.argv[1:7]]
norm = lambda n: n.lower().replace('-', '_').replace('.', '_')
MANUAL = {'pillow': ['PIL'], 'pyyaml': ['yaml'], 'scikit_learn': ['sklearn'], 'beautifulsoup4': ['bs4'], 'python_dateutil': ['dateutil'],
          'opencv_python': ['cv2'], 'attrs': ['attr', 'attrs'], 'protobuf': ['google'], 'gitpython': ['git'], 'pyjwt': ['jwt'],
          'python_dotenv': ['dotenv'], 'ruamel_yaml': ['ruamel'], 'pycryptodome': ['Crypto'], 'pycryptodomex': ['Cryptodome'],
          'msgpack_python': ['msgpack'], 'typing_extensions': ['typing_extensions'], 'matplotlib': ['matplotlib', 'mpl_toolkits'],
          'ipython': ['IPython'], 'simple_ddl_parser': ['simple_ddl_parser'], 'z3_solver': ['z3'], 'dm_tree': ['tree'],
          'faiss_cpu': ['faiss'], 'termcolor_whl': ['termcolor'], 'django_allauth': ['allauth'], 'importlib_metadata': ['importlib_metadata']}
PIPREQS = collections.defaultdict(set)
if mapping_path and mapping_path.exists():
    for line in open(mapping_path, encoding='utf-8', errors='ignore'):
        if ':' in line:
            imp, pkg = line.strip().split(':', 1); PIPREQS[norm(pkg)].add(imp)


def import_names(dep):
    d = norm(dep); names = {d} | set(MANUAL.get(d, [])) | PIPREQS.get(d, set())
    if d.startswith('python_'): names.add(d[len('python_'):])
    if d.startswith('py') and len(d) > 3: names.add(d[2:])
    return names


def is_test_node(name):
    parts = name.split('.')
    return any(p in ('test', 'tests', 'testing', 'conftest') or p.startswith('test_') or p.endswith('_test') for p in parts)


gold_pass = {json.load(open(f))['instance_id'] for f in gold_dir.rglob('eval-result.json') if json.load(open(f)).get('exec') == 'pass'}
mut = {}
for f in mut_dir.rglob('eval-result.json'):
    d = json.load(open(f)); base, dep = d['instance_id'].split('__del__', 1); mut[(base, dep)] = d.get('exec')
deps_by_inst = collections.defaultdict(list)
for r in csv.DictReader(open(per_dep_csv)):
    deps_by_inst[r['instance_id']].append(r)
status = json.load(open(cg_dir / '_status.json')) if (cg_dir / '_status.json').exists() else {}

rows = []; covered = 0; failed = []
for iid in sorted(gold_pass):
    cgf = cg_dir / f'{iid}.json'
    if not cgf.exists():
        failed.append(iid); continue
    cg = json.load(open(cgf)); covered += 1
    module_nodes = internal_roots(REPO_DATA / iid)
    def external_root(n):
        r = n.split('.')[0]
        return None if (r in module_nodes or n.startswith('<')) else r
    # reachability from test nodes
    seen = set(n for n in cg if is_test_node(n)); stack = list(seen)
    while stack:
        n = stack.pop()
        for c in cg.get(n, []):
            if c not in seen:
                seen.add(c); stack.append(c)
    all_ext = collections.Counter(); reach_ext = collections.Counter(); callsites = collections.Counter()
    for n, cs in cg.items():
        for c in cs:
            r = external_root(c)
            if r:
                all_ext[r] += 1; callsites[(r, c)] += 1
                if n in seen:
                    reach_ext[r] += 1
    for r in deps_by_inst.get(iid, []):
        names = import_names(r['dep'])
        used_syms = {c for (root, c) in callsites if root in names}
        n_callsites = sum(v for (root, c), v in callsites.items() if root in names)
        sym_reach = any(root in names for root in reach_ext)
        sym_used = bool(used_syms)
        ex = mut.get((iid, norm(r['dep'])), mut.get((iid, r['dep'])))
        rows.append(dict(iid=iid, dep=r['dep'], file_imported=r['imported'] == '1', file_reach=r['test_reachable'] == '1',
                         sym_used=sym_used, sym_reach=sym_reach, surface=len(used_syms), callsites=n_callsites, deletion=ex))

def rate(xs):
    return f"{sum(xs)} of {len(xs)} ({sum(xs) / len(xs):.2f})" if xs else 'n/a'
scored = [r for r in rows if r['deletion'] in ('pass', 'fail')]
inv = [r for r in scored if r['deletion'] == 'pass']
pred_unreach = [r for r in scored if not r['sym_reach']]
lines = ["## Symbol-level reachability (PyCG) against executed deletions", "",
         f"Call graphs built for {covered} of {len(gold_pass)} gold-passing repos; PyCG failed on {len(failed)}: {', '.join(failed[:12])}", "",
         "| Measure | Value |", "| --- | --- |",
         f"| Declared deps on covered repos with an executed deletion | {len(scored)} |",
         f"| Symbol-level: used somewhere in the call graph | {rate([r['sym_used'] for r in scored])} |",
         f"| Symbol-level: reachable from a test | {rate([r['sym_reach'] for r in scored])} |",
         f"| File-level: reachable from a test (previous estimate) | {rate([r['file_reach'] for r in scored])} |",
         f"| Executed: deletion invisible to CI | {rate([r['deletion'] == 'pass' for r in scored])} |",
         f"| Static predictor 'not test-reachable' -> precision for invisibility | {rate([r['deletion'] == 'pass' for r in pred_unreach])} |",
         f"| Static predictor 'not test-reachable' -> recall of invisible deletions | {rate([not r['sym_reach'] for r in inv])} |",
         f"| Deletions CI noticed although the graph saw no test path (graph misses) | {sum(1 for r in scored if r['deletion'] == 'fail' and not r['sym_reach'])} |",
         f"| Deletions CI missed although the graph saw a test path (phantoms or weak tests) | {sum(1 for r in scored if r['deletion'] == 'pass' and r['sym_reach'])} |", "",
         "### Used API surface per dependency (difficulty label)", "", "| Surface size (distinct symbols called) | Deps | Deletion invisible |", "| --- | --- | --- |"]
buckets = [(0, 0), (1, 1), (2, 3), (4, 8), (9, 10**6)]
for lo, hi in buckets:
    b = [r for r in scored if lo <= r['surface'] <= hi]
    if b: lines.append(f"| {lo}" + (f" to {hi}" if hi < 10**6 and hi != lo else ("+" if hi == 10**6 else "")) + f" | {len(b)} | {rate([r['deletion'] == 'pass' for r in b])} |")
lines += ["", "| Instance | Dependency | Symbols used | Call sites | Test-reachable (symbol) | Test-reachable (file) | Deletion |", "| --- | --- | --- | --- | --- | --- | --- |"]
for r in sorted(scored, key=lambda r: (r['iid'], r['dep'])):
    lines.append(f"| {r['iid']} | {r['dep']} | {r['surface']} | {r['callsites']} | {r['sym_reach']} | {r['file_reach']} | {r['deletion']} |")
md = "\n".join(lines) + "\n"
print("\n".join(lines[:22]))
out_md.write_text(md)
json.dump(rows, open(out_md.with_suffix('.json'), 'w'), indent=1)
