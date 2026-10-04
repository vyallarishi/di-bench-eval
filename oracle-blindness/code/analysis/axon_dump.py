#!/usr/bin/env python3
"""Dump Axon's in-memory graph for a repo (no CLI, no embeddings) and compare its
call graph with PyCG's on the same repo.

usage: axon_dump.py <repo_dir> <pycg_json> <out_json>
"""
import collections, json, os, pathlib, sys, time
from axon.core.ingestion.pipeline import run_pipeline
from axon.core.graph.model import NodeLabel, RelType

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

repo = pathlib.Path(sys.argv[1]).resolve(); pycg_path = pathlib.Path(sys.argv[2]); out = pathlib.Path(sys.argv[3])
t0 = time.time()
graph, result = run_pipeline(repo, storage=None, embeddings=False)
secs = time.time() - t0
nodes = {n.id: n for n in graph.iter_nodes()}
label_counts = collections.Counter(n.label.value for n in nodes.values())
rels = list(graph.iter_relationships())
rel_counts = collections.Counter(r.type.value for r in rels)


def qual(n):
    """module.function name comparable with PyCG's naming."""
    fp = n.file_path or ''
    rel = os.path.relpath(fp, repo) if os.path.isabs(fp) else fp
    if rel.startswith('src/'):
        rel = rel[4:]
    mod = rel[:-3].replace('/', '.') if rel.endswith('.py') else rel.replace('/', '.')
    if mod.endswith('.__init__'):
        mod = mod[:-9]
    return f"{mod}.{n.name}" if n.name and mod else (n.name or mod)


calls = collections.defaultdict(set)
for r in rels:
    if r.type == RelType.CALLS and r.source in nodes and r.target in nodes:
        calls[qual(nodes[r.source])].add(qual(nodes[r.target]))
imports = collections.Counter()
for r in rels:
    if r.type == RelType.IMPORTS and r.target in nodes:
        imports[nodes[r.target].name.split('.')[0]] += 1
axon_edges = {(a, b) for a, bs in calls.items() for b in bs}

pycg = json.load(open(pycg_path))
module_nodes = internal_roots(repo)
pycg_internal = {(a, b) for a, bs in pycg.items() for b in bs if b.split('.')[0] in module_nodes and a.split('.')[0] in module_nodes}
pycg_external_roots = collections.Counter(b.split('.')[0] for bs in pycg.values() for b in bs if b.split('.')[0] not in module_nodes and not b.startswith('<'))
axon_edges = {(a, b) for (a, b) in axon_edges if a.split('.')[0] in module_nodes and b.split('.')[0] in module_nodes}


def is_test(name):
    return any(p in ('test', 'tests', 'testing') or p.startswith('test_') for p in name.split('.'))


def reach(edges, starts):
    adj = collections.defaultdict(set)
    for a, b in edges:
        adj[a].add(b)
    seen = set(starts); stack = list(starts)
    while stack:
        x = stack.pop()
        for y in adj.get(x, ()):
            if y not in seen:
                seen.add(y); stack.append(y)
    return seen


ax_nodes = {a for e in axon_edges for a in e}; py_nodes = {a for e in pycg_internal for a in e}
ax_reach = reach(axon_edges, {n for n in ax_nodes if is_test(n)}); py_reach = reach(pycg_internal, {n for n in py_nodes if is_test(n)})
common_nodes = ax_nodes & py_nodes
summary = dict(
    repo=repo.name, axon_seconds=round(secs, 1), axon_nodes=dict(label_counts), axon_rels=dict(rel_counts),
    axon_call_edges=len(axon_edges), pycg_internal_call_edges=len(pycg_internal),
    edge_overlap=len(axon_edges & pycg_internal),
    edge_jaccard=round(len(axon_edges & pycg_internal) / max(len(axon_edges | pycg_internal), 1), 3),
    node_overlap=len(common_nodes), axon_only_nodes=len(ax_nodes - py_nodes), pycg_only_nodes=len(py_nodes - ax_nodes),
    test_reachable_agreement_on_common_nodes=round(sum((n in ax_reach) == (n in py_reach) for n in common_nodes) / max(len(common_nodes), 1), 3),
    axon_import_roots=dict(imports.most_common(15)), pycg_external_call_roots=dict(pycg_external_roots.most_common(15)),
    sample_axon_edges=sorted(axon_edges)[:5], sample_pycg_edges=sorted(pycg_internal)[:5],
)
json.dump(summary, open(out, 'w'), indent=1)
print(json.dumps(summary, indent=1))
