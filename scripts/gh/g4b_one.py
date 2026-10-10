"""Compare one (library fn, replacement fn) pair. Run as a subprocess: loading
an arbitrary third-party library in-process can and does kill the parent."""
import sys, json, pathlib, importlib, importlib.util, tempfile
sys.path.insert(0, '/Users/rishivyalla/Downloads/DI-Bench/scripts/gh')
from gate_differential import compare_callables
spec = json.load(open(sys.argv[1])) if pathlib.Path(sys.argv[1]).exists() else json.loads(sys.argv[1])
try:
    # try every plausible import name: a distribution's import name often
    # differs from its package name (python-slugify ships `slugify`), and
    # picking the first alphabetically imported the wrong thing.
    lib = None
    for name in spec['import_names']:
        try:
            lib = importlib.import_module(name); break
        except Exception:
            continue
    if lib is None:
        print(json.dumps(dict(outcome='library not importable',
                              reason='tried ' + ','.join(spec['import_names'])))); sys.exit(0)
    # The replacement is loaded under an ALIAS, never under its own name: a
    # stub or a vendored copy takes the library's import name, and loading it
    # as that name would hand back the library already imported above.
    td = pathlib.Path(tempfile.mkdtemp())
    for rel, src in spec['files'].items():
        f = td / rel; f.parent.mkdir(parents=True, exist_ok=True); f.write_text(src)
    rel = spec['defining']
    parts = rel[:-3].split('/') if rel.endswith('.py') else rel.split('/')
    if parts and parts[-1] == '__init__':
        parts = parts[:-1]
    if len(parts) == 1 and (td / rel).name != '__init__.py' and not (td / parts[0]).is_dir():
        sp = importlib.util.spec_from_file_location('cand_' + parts[0], td / rel)
        m = importlib.util.module_from_spec(sp); sys.modules[sp.name] = m; sp.loader.exec_module(m)
    else:
        root = parts[0]; alias = 'cand_' + root
        init = td / root / '__init__.py'
        if not init.exists():
            init.write_text('')
        sp = importlib.util.spec_from_file_location(alias, init, submodule_search_locations=[str(td / root)])
        pkg = importlib.util.module_from_spec(sp); sys.modules[alias] = pkg; sp.loader.exec_module(pkg)
        m = pkg if len(parts) == 1 else importlib.import_module(alias + '.' + '.'.join(parts[1:]))
    fn = spec['fn']
    # the library's callable by the qualified name the recorder saw
    # (pkg.sub.fn), falling back to the top-level attribute
    lib_fn = None
    q = (spec['calls'][0].get('q') or '') if spec.get('calls') else ''
    if '.' in q:
        try:
            obj = importlib.import_module(q.rsplit('.', 1)[0])
            lib_fn = getattr(obj, q.rsplit('.', 1)[1], None)
        except Exception:
            try:
                head, *rest = q.split('.')
                obj = importlib.import_module(head)
                for part in rest:
                    obj = getattr(obj, part)
                lib_fn = obj
            except Exception:
                lib_fn = None
    if lib_fn is None:
        lib_fn = getattr(lib, fn, None)
    if lib_fn is None or not hasattr(m, fn):
        print(json.dumps(dict(outcome='function not on both'))); sys.exit(0)
    r = compare_callables(lib_fn, getattr(m, fn), spec["calls"], n=spec.get("n", 300), seed=0)
    print(json.dumps(dict(outcome=('CAUGHT' if r['pass'] is False
                                   else 'agrees' if r['pass'] else 'cannot speak'),
                          reason=r['reason'][:160],
                          divergent=r['evidence'].get('divergent'),
                          tried=r['evidence'].get('tried'))))
except Exception as e:
    print(json.dumps(dict(outcome='error', reason=f'{type(e).__name__}: {e}'[:120])))
