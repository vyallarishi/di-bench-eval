import json, pathlib, re, subprocess, tempfile, shutil, tomllib, sys, collections
ROOT = pathlib.Path('/Users/rishivyalla/Downloads/DI-Bench'); DATA = ROOT / '.cache/repo-data/python'
S = pathlib.Path(sys.argv[1]); variant = sys.argv[2]
NAME_RE = re.compile(r'^\s*([A-Za-z0-9][A-Za-z0-9._-]*)')
norm = lambda n: n.lower().replace('-', '_').replace('.', '_')
def apply_patch(repo, bf, patch):
    with tempfile.TemporaryDirectory() as td:
        td = pathlib.Path(td); shutil.copy(repo / bf, td / bf); (td / 'p.diff').write_text(patch)
        r = subprocess.run(['patch', '--batch', '--fuzz=5', '-p1', '-i', 'p.diff'], cwd=td, capture_output=True, text=True)
        return (td / bf).read_text() if r.returncode == 0 else None
def parse_pyproject(text):
    d = tomllib.loads(text); po = d.get('tool', {}).get('poetry', {})
    if po: return {norm(k) for k in (po.get('dependencies') or {}) if k.lower() != 'python'}
    return {norm(NAME_RE.match(s).group(1)) for s in d.get('project', {}).get('dependencies', []) if NAME_RE.match(s)}
rows = [json.loads(l) for l in open(ROOT / '.cache/dataset-dibench-regular.jsonl')]
agg = collections.Counter(); done = 0; missing = []
for r in rows:
    if r['language'] != 'python': continue
    iid = r['instance_id']; f = S / f'pipreqs_{variant}' / f'{iid}.txt'
    if not f.exists(): missing.append(iid); continue
    o = parse_pyproject(apply_patch(DATA / iid, r['build_files'][0], r['patch']))
    pred = set()
    for line in f.read_text().splitlines():
        m = NAME_RE.match(line)
        if m: pred.add(norm(m.group(1)))
    err = (S / f'pipreqs_{variant}' / f'{iid}.err').read_text()
    if not pred and ('Error' in err or 'Traceback' in err): agg['tool_error'] += 1
    tp = len(pred & o); fp = len(pred - o); fn = len(o - pred)
    agg['tp'] += tp; agg['fp'] += fp; agg['fn'] += fn; agg['exact'] += int(pred == o); agg['empty_pred'] += int(not pred); done += 1
p = agg['tp'] / max(agg['tp'] + agg['fp'], 1); rc = agg['tp'] / max(agg['tp'] + agg['fn'], 1); f1 = 2 * p * rc / max(p + rc, 1e-9)
print(json.dumps(dict(variant=variant, scored=done, missing=len(missing), tool_error=agg['tool_error'], empty_pred=agg['empty_pred'],
      name_only_micro_PRF=[round(p, 3), round(rc, 3), round(f1, 3)], exact_set_rate=round(agg['exact'] / max(done, 1), 3), tp=agg['tp'], fp=agg['fp'], fn=agg['fn'])))
