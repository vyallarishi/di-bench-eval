"""Attribute every screened candidate: footprint, guard status, configuration mention.
Mirrors BLIND_SPOT_ANATOMY.md: import footprint from the AST, guard check via optional_deps,
textual search of *.cfg, *.toml, *.ini and .github/workflows/* for the package name and
spelling variants, excluding the instance's own build files."""
import json, pathlib, re, sys, collections
sys.path.insert(0, 'scripts/gh')
import footprint as FP, optional_deps as OD
S = pathlib.Path(sys.argv[1])
rows = {}
for f in ['pilot/all.jsonl', 'pilot/all_large.jsonl']:
    for l in open(f):
        if l.strip():
            r = json.loads(l); rows[r['instance_id']] = r
def cands(path):
    return [json.loads(l) for l in open(path) if l.strip()]
pool = cands('oracle-blindness/data/instances.jsonl'); blind = cands('oracle-blindness/data/instances.blind.jsonl'); exc = cands('oracle-blindness/data/instances.excluded.jsonl')
allc = [(r, 'pair') for r in pool] + [(r, 'silent') for r in blind] + [(r, 'excluded') for r in exc]
idx = {}
def variants(dep):
    d = dep.lower(); out = {d, d.replace('-', '_'), d.replace('_', '-'), d.replace('_', ''), d.replace('-', '')}
    out |= set(FP.import_names(dep)); return {v for v in out if len(v) > 2}
def config_mention(repo, dep, build_files):
    pats = [re.compile(r'(?<![A-Za-z0-9])' + re.escape(v) + r'(?![A-Za-z0-9])', re.I) for v in variants(dep)]
    files = [p for p in repo.rglob('*') if p.is_file() and (p.suffix in ('.cfg', '.toml', '.ini') or '.github/workflows' in str(p)) and '.tox' not in str(p) and 'site-packages' not in str(p)]
    hits = []
    for p in files:
        rel = str(p.relative_to(repo))
        if rel in build_files: continue
        try: txt = p.read_text(errors='replace')
        except Exception: continue
        if any(pt.search(txt) for pt in pats): hits.append(rel)
    return hits
out = []
for r, disp in allc:
    iid, dep = r['instance_id'], r['dependency']
    repo = pathlib.Path('.cache/repo-data/python') / iid
    if iid not in idx: idx[iid] = FP.RepoIndex(repo)
    fp = idx[iid].footprint(dep)
    src = {k: v for k, v in fp['source_files'].items() if not v['is_test']}
    od = OD.classify(repo, dep)
    conf = config_mention(repo, dep, set(rows.get(iid, {}).get('build_files', [])))
    if not src and not fp['test_files']: cause = 'over-declared' if not conf else 'used without importing'
    else:
        v = od.get('verdict') or od.get('status') or str(od)[:40]
        cause = 'optional by design' if v in ('recovers', 'fallback_to') else 'imported, unguarded, untested'
    out.append(dict(instance_id=iid, dependency=dep, disposition=disp, footprint_files=fp['footprint_files'], test_files=fp['test_files'], test_reachable=fp['test_reachable'], guard=od.get('verdict', od), config_mentions=conf, cause=cause if disp == 'silent' else None))
json.dump(out, open(S / 'attribution.json', 'w'), indent=0)
c = collections.Counter(o['cause'] for o in out if o['disposition'] == 'silent'); print('silent causes', dict(c))
print('sample od keys', list(od.keys()))
