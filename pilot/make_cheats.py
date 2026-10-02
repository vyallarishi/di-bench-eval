#!/usr/bin/env python3
"""Generate constructed-cheat variants for removal-task instances.

For each (instance, dependency D) in pilot/instances.jsonl (strong tier by default), build:
  stub    a local package shadowing D whose imported symbols are no-op stubs; D's declaration removed
  vendor  D's own pure-Python package copied into the repo root; D's declaration removed
  hide    D moved from the main dependency list to every optional extra / the poetry dev group
Each variant is written as a patch against the MASKED repo (so the DI-Bench harness can apply it) under
predictions/cheats/python/<iid>__<cheat>__<dep>/patch.diff, plus a dataset row in pilot/cheats.jsonl.

usage: make_cheats.py <dataset.jsonl> <repo_data> <pip_bin> [--tier strong] [--limit N] [--cheats stub,vendor,hide]
"""
import ast, json, os, pathlib, re, shutil, subprocess, sys, tempfile, zipfile
try:
    import tomllib
except ImportError:
    import tomli as tomllib
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1] / 'scripts' / 'gh'))
from prepare import apply_patch_text, git_diff, section_span, balanced_end  # noqa: E402

NAME_RE = re.compile(r"^\s*([A-Za-z0-9][A-Za-z0-9._-]*)")
norm = lambda n: n.lower().replace('-', '_').replace('.', '_')


def pip_cmd(pip):
    """Run pip through its interpreter: venv launchers can fail to exec with a long path."""
    p = pathlib.Path(pip)
    py = p.parent / 'python'
    return [str(py), '-m', 'pip'] if p.name.startswith('pip') and py.exists() else [pip]
ROOT = pathlib.Path(__file__).resolve().parents[1]
OUT = ROOT / 'predictions' / 'cheats' / 'python'


def remove_decl(text, dep):
    """Oracle manifest text with D's declaration removed (same logic as prepare.mutants_for)."""
    data = tomllib.loads(text); po = data.get('tool', {}).get('poetry', {})
    if po:
        span = section_span(text, r"^\[tool\.poetry\.dependencies\]\s*$"); s, e = span; body = text[s:e]
        for key in po.get('dependencies') or {}:
            if norm(key) != norm(dep): continue
            m = re.search(r'^[ \t]*"?' + re.escape(key) + r'"?[ \t]*=[ \t]*', body, re.M)
            k = m.end()
            if body[k] in '[{': k = balanced_end(body, k)
            nl = body.find('\n', k); k = len(body) if nl < 0 else nl + 1
            return text[:s] + body[:m.start()] + body[k:] + text[e:], key
        return None, None
    span = section_span(text, r"^\[project\]\s*$"); s, e = span; body = text[s:e]
    m = re.search(r"^dependencies[ \t]*=[ \t]*\[", body, re.M); a = m.end() - 1; b = balanced_end(body, a)
    entries = data['project'].get('dependencies') or []
    keep = [d for d in entries if norm(NAME_RE.match(d).group(1)) != norm(dep)]
    removed = [d for d in entries if norm(NAME_RE.match(d).group(1)) == norm(dep)]
    arr = "[\n" + "".join(f"    {json.dumps(d)},\n" for d in keep) + "]"
    return text[:s] + body[:a] + arr + body[b:] + text[e:], (removed[0] if removed else None)


def hide_decl(text, dep):
    """Move D out of the main list into optional extras (PEP 621) or the dev group (poetry)."""
    new, spec = remove_decl(text, dep)
    if new is None: return None
    data = tomllib.loads(text)
    if data.get('tool', {}).get('poetry'):
        line = f'{spec} = "*"\n'
        if re.search(r"^\[tool\.poetry\.group\.dev\.dependencies\]\s*$", new, re.M):
            return re.sub(r"(^\[tool\.poetry\.group\.dev\.dependencies\]\s*\n)", r"\1" + line, new, count=1, flags=re.M)
        return new.rstrip('\n') + f"\n\n[tool.poetry.group.dev.dependencies]\n{line}"
    extras = data['project'].get('optional-dependencies') or {}
    if extras:
        for key in extras:
            new = re.sub(r"(^" + re.escape(key) + r"[ \t]*=[ \t]*\[)", r"\1\n    " + json.dumps(spec) + ",", new, count=1, flags=re.M)
        return new
    return new.rstrip('\n') + f"\n\n[project.optional-dependencies]\ntest = [{json.dumps(spec)}]\n"


def imported_symbols(repo, names):
    """{module_name: {symbol,...}} for `from D import x` and attribute uses `D.x` across source files."""
    out = {n: set() for n in names}; star = set()
    for dp, dns, fns in os.walk(repo):
        dns[:] = [d for d in dns if d not in {'.git', 'build', 'dist', '.tox', 'venv', '.venv', 'node_modules', 'site-packages'} and not d.startswith('.')]
        for f in fns:
            if not f.endswith('.py'): continue
            try: tree = ast.parse((pathlib.Path(dp) / f).read_bytes())
            except Exception: continue
            aliases = {}
            for node in ast.walk(tree):
                if isinstance(node, ast.ImportFrom) and node.module and node.module.split('.')[0] in names:
                    root = node.module.split('.')[0]
                    for a in node.names:
                        if a.name == '*': star.add(root)
                        else: out[root].add((node.module, a.name))
                elif isinstance(node, ast.Import):
                    for a in node.names:
                        root = a.name.split('.')[0]
                        if root in names: aliases[a.asname or a.name.split('.')[0]] = (root, a.name)
            src = (pathlib.Path(dp) / f).read_text(errors='ignore')
            for alias, (root, full) in aliases.items():
                for m in re.finditer(r'\b' + re.escape(alias) + r'\.([A-Za-z_][\w]*)', src):
                    out[root].add((full, m.group(1)))
    return out, star


def write_stub_package(dst_root, root, symbols):
    """Create <dst_root>/<root>/__init__.py (+ submodules) with no-op stubs for the used symbols."""
    by_module = {}
    for module, sym in symbols:
        by_module.setdefault(module, set()).add(sym)
    created = []
    for module, syms in by_module.items():
        parts = module.split('.')
        pkg = dst_root / parts[0]; pkg.mkdir(exist_ok=True)
        init = pkg / '__init__.py'
        if not init.exists(): init.write_text('"""Stub replacement."""\n'); created.append(init)
        target = init if len(parts) == 1 else None
        if target is None:
            d = pkg
            for p in parts[1:-1]:
                d = d / p; d.mkdir(exist_ok=True); (d / '__init__.py').touch()
            target = d / (parts[-1] + '.py')
            if not target.exists(): target.write_text('"""Stub replacement."""\n'); created.append(target)
            # make it importable as attribute of the parent package too
            with open(init, 'a') as fh: fh.write(f"from . import {parts[1]}  # noqa\n") if len(parts) == 2 else None
        with open(target, 'a') as fh:
            for s in sorted(syms):
                if s[:1].isupper():
                    fh.write(f"\nclass {s}:\n    def __init__(self, *args, **kwargs):\n        pass\n    def __getattr__(self, name):\n        return lambda *a, **k: None\n    def __call__(self, *args, **kwargs):\n        return None\n")
                else:
                    fh.write(f"\ndef {s}(*args, **kwargs):\n    return None\n")
    return created


def vendor_package(pip, dep, dst_root):
    """pip-download D's wheel and copy its top-level packages into dst_root. Returns copied names or None."""
    with tempfile.TemporaryDirectory() as td:
        r = subprocess.run([*pip_cmd(pip), 'download', '--no-deps', '--only-binary=:all:', '-q', '-d', td, dep], capture_output=True, text=True)
        wheels = list(pathlib.Path(td).glob('*.whl'))
        if r.returncode != 0 or not wheels: return None
        copied = []
        with zipfile.ZipFile(wheels[0]) as z:
            names = z.namelist()
            if any(n.endswith(('.so', '.pyd')) for n in names): return None  # compiled: not vendorable as source
            tops = {n.split('/')[0] for n in names if '/' in n and not n.split('/')[0].endswith(('.dist-info', '.data'))}
            singles = {n for n in names if '/' not in n and n.endswith('.py')}
            for n in names:
                top = n.split('/')[0]
                if (top in tops or n in singles) and not n.endswith('/'):
                    dest = dst_root / n; dest.parent.mkdir(parents=True, exist_ok=True)
                    dest.write_bytes(z.read(n))
            copied = sorted(tops | singles)
        return copied


def snapshot(repo):
    """Files of the repo (relative -> text) excluding .git, for diffing."""
    out = {}
    for dp, dns, fns in os.walk(repo):
        dns[:] = [d for d in dns if d != '.git']
        for f in fns:
            p = pathlib.Path(dp) / f
            try: out[str(p.relative_to(repo))] = p.read_text()
            except Exception: pass
    return out


def multi_diff(old, new):
    """git diff for all changed/added files between two snapshots."""
    with tempfile.TemporaryDirectory() as td:
        td = pathlib.Path(td)
        subprocess.run(['git', 'init', '-q'], cwd=td, check=True)
        for rel, txt in old.items():
            (td / rel).parent.mkdir(parents=True, exist_ok=True); (td / rel).write_text(txt)
        subprocess.run(['git', 'add', '-A'], cwd=td, check=True)
        subprocess.run(['git', '-c', 'user.email=a@b', '-c', 'user.name=a', 'commit', '-q', '-m', 'old'], cwd=td, check=True)
        for rel in set(old) - set(new): (td / rel).unlink()
        for rel, txt in new.items():
            (td / rel).parent.mkdir(parents=True, exist_ok=True); (td / rel).write_text(txt)
        subprocess.run(['git', 'add', '-A'], cwd=td, check=True)
        return subprocess.run(['git', 'diff', '--cached', '--binary'], cwd=td, capture_output=True, text=True).stdout


def main():
    ds, repo_data, pip = sys.argv[1], pathlib.Path(sys.argv[2]), sys.argv[3]
    tier = 'strong'; limit = 0; cheats = ['stub', 'vendor', 'hide']
    for a in sys.argv[4:]:
        if a.startswith('--tier='): tier = a.split('=', 1)[1]
        if a.startswith('--limit='): limit = int(a.split('=', 1)[1])
        if a.startswith('--cheats='): cheats = a.split('=', 1)[1].split(',')
    rows = {json.loads(l)['instance_id']: json.loads(l) for l in open(ds) if l.strip()}
    inst = [json.loads(l) for l in open(ROOT / 'pilot' / 'instances.jsonl') if l.strip()]
    inst = [i for i in inst if i['tier'] == tier]
    if limit: inst = inst[:limit]
    sys.path.insert(0, str(pathlib.Path(os.environ.get('ANALYZE_DIR', '.'))))
    code = open(os.environ['ANALYZE_PY']).read().split('# ---------- build file parsing')[0]
    ns = {}; exec(code, ns); import_names_for = ns['import_names_for']
    out_rows = []; log = []
    for i in inst:
        iid, dep = i['instance_id'], i['dependency']; r = rows[iid]; bf = r['build_files'][0]
        repo = repo_data / iid
        masked = snapshot(repo)
        oracle_text = apply_patch_text(repo, bf, r['patch'])
        base = dict(masked); base[bf] = oracle_text  # starting state = gold
        names = [n for n in import_names_for(dep) if any(re.search(rf'^\s*(from|import)\s+{re.escape(n)}\b', t, re.M) for t in base.values() if isinstance(t, str))]
        if not names: log.append(f'{iid}/{dep}: no import name found, skipped'); continue
        for cheat in cheats:
            with tempfile.TemporaryDirectory() as td:
                td = pathlib.Path(td)
                for rel, txt in base.items():
                    (td / rel).parent.mkdir(parents=True, exist_ok=True); (td / rel).write_text(txt)
                ok = True; note = ''
                if cheat == 'hide':
                    new = hide_decl(oracle_text, dep); ok = new is not None
                    if ok: (td / bf).write_text(new)
                else:
                    new, _ = remove_decl(oracle_text, dep); ok = new is not None
                    if ok: (td / bf).write_text(new)
                    if ok and cheat == 'stub':
                        syms, star = imported_symbols(td, set(names))
                        created = []
                        for root in names:
                            if (td / root).exists() or (td / f'{root}.py').exists(): ok = False; note = 'name clash'; break
                            created += write_stub_package(td, root, syms.get(root, set()) or {(root, '_')})
                        note = note or f'{len(created)} stub files'
                    if ok and cheat == 'vendor':
                        copied = vendor_package(pip, dep, td)
                        if not copied: ok = False; note = 'no pure-python wheel'
                        else: note = f'vendored {copied}'
                if not ok:
                    log.append(f'{iid}/{dep}/{cheat}: skipped ({note})'); continue
                variant = snapshot(td)
                patch = multi_diff(masked, variant)
                mid = f'{iid}__{cheat}__{norm(dep)}'
                d = OUT / mid; d.mkdir(parents=True, exist_ok=True); (d / 'patch.diff').write_text(patch)
                row = {k: r[k] for k in ['instance_id', 'metadata', 'language', 'act_command', 'ci_file', 'patch', 'build_files', 'env_specs']}
                row['instance_id'] = mid; out_rows.append(row)
                log.append(f'{iid}/{dep}/{cheat}: ok ({note}, patch {len(patch)} bytes)')
    with open(ROOT / 'pilot' / 'cheats.jsonl', 'w') as f:
        for row in out_rows: f.write(json.dumps(row) + '\n')
    print('\n'.join(log)); print(f'\nvariants written: {len(out_rows)}')


if __name__ == '__main__':
    main()
