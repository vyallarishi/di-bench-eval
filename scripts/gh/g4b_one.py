"""Compare one (library fn, replacement fn) pair. Run as a subprocess: loading
an arbitrary third-party library in-process can and does kill the parent."""
import sys, json, pathlib, importlib, importlib.util, tempfile
sys.path.insert(0, '/Users/rishivyalla/Downloads/DI-Bench/scripts/gh')
from gate_differential import compare_callables
spec = json.loads(sys.argv[1])
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
    td = pathlib.Path(tempfile.mkdtemp()); (td/'c.py').write_text(spec['src'])
    sp = importlib.util.spec_from_file_location('c', td/'c.py')
    m = importlib.util.module_from_spec(sp); sp.loader.exec_module(m)
    fn = spec['fn']
    if not hasattr(lib, fn) or not hasattr(m, fn):
        print(json.dumps(dict(outcome='function not on both'))); sys.exit(0)
    r = compare_callables(getattr(lib, fn), getattr(m, fn), spec['calls'], n=300, seed=0)
    print(json.dumps(dict(outcome=('CAUGHT' if r['pass'] is False
                                   else 'agrees' if r['pass'] else 'cannot speak'),
                          reason=r['reason'][:160],
                          divergent=r['evidence'].get('divergent'),
                          tried=r['evidence'].get('tried'))))
except Exception as e:
    print(json.dumps(dict(outcome='error', reason=f'{type(e).__name__}: {e}'[:120])))
