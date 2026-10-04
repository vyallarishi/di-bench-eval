"""Static analysis of DI-Bench Python regular: textual scoring of Qwen patches,
oracle-dependency import footprint, test-reachability proxy, F2 feasibility."""
import ast, collections, glob, json, os, pathlib, re, shutil, subprocess, sys, tempfile, tomllib

ROOT = pathlib.Path('/Users/rishivyalla/Downloads/DI-Bench')
DATA = ROOT / '.cache/repo-data/python'
QWEN = ROOT / 'Kaggle_Baseline_Results/all-in-one-qwen2.5-coder:7b/python'
OUT = pathlib.Path(sys.argv[1]) if len(sys.argv) > 1 else pathlib.Path('.')
STDLIB = set(sys.stdlib_module_names) | {'__future__', '_typeshed'}
NAME_RE = re.compile(r'^\s*([A-Za-z0-9][A-Za-z0-9._-]*)')
SKIP_DIRS = {'.git', '.axon', 'node_modules', 'venv', '.venv', 'build', 'dist', 'site-packages', '__pycache__', '.tox', '.eggs', 'docs', 'doc', 'examples', 'example', 'benchmarks', 'bench'}
TEST_DIR_NAMES = {'tests', 'test', 'testing', 'unittests', 'unit_tests', 'integration_tests'}

def norm(n):
    return n.lower().replace('-', '_').replace('.', '_')

# ---------- import-name <-> package-name mapping ----------
MANUAL = {
    'pillow': ['PIL'], 'pyyaml': ['yaml'], 'scikit_learn': ['sklearn'], 'beautifulsoup4': ['bs4'],
    'python_dateutil': ['dateutil'], 'opencv_python': ['cv2'], 'opencv_python_headless': ['cv2'],
    'attrs': ['attr', 'attrs'], 'protobuf': ['google'], 'grpcio': ['grpc'], 'gitpython': ['git'],
    'pyjwt': ['jwt'], 'python_dotenv': ['dotenv'], 'ruamel_yaml': ['ruamel'], 'pycryptodome': ['Crypto'],
    'pycryptodomex': ['Cryptodome'], 'psycopg2_binary': ['psycopg2'], 'msgpack_python': ['msgpack'],
    'pyserial': ['serial'], 'pymupdf': ['fitz'], 'python_magic': ['magic'], 'pywin32': ['win32api', 'win32con'],
    'importlib_resources': ['importlib_resources'], 'typing_extensions': ['typing_extensions'],
    'pytest_cov': [], 'pytest_asyncio': [], 'pytest_mock': [], 'setuptools_scm': [], 'wheel': [],
    'markdown': ['markdown'], 'python_slugify': ['slugify'], 'pysocks': ['socks'], 'python_multipart': ['multipart'],
    'google_api_python_client': ['googleapiclient'], 'google_auth': ['google'], 'google_cloud_storage': ['google'],
    'azure_storage_blob': ['azure'], 'boto3': ['boto3'], 'docutils': ['docutils'], 'backports_zoneinfo': ['backports'],
    'pyopenssl': ['OpenSSL'], 'pynacl': ['nacl'], 'websocket_client': ['websocket'], 'sqlalchemy': ['sqlalchemy'],
    'biopython': ['Bio'], 'mysqlclient': ['MySQLdb'], 'pymysql': ['pymysql'], 'tensorflow_cpu': ['tensorflow'],
    'discord_py': ['discord'], 'python_telegram_bot': ['telegram'], 'pyzmq': ['zmq'], 'pygobject': ['gi'],
    'pyqt5': ['PyQt5'], 'pyside6': ['PySide6'], 'matplotlib': ['matplotlib', 'mpl_toolkits'],
    'ipython': ['IPython'], 'jupyter_core': ['jupyter_core'], 'tomli': ['tomli'], 'typer': ['typer'],
    'py': ['py'], 'pycparser': ['pycparser'], 'aiohttp': ['aiohttp'], 'lxml': ['lxml'], 'xlrd': ['xlrd'],
    'python_jose': ['jose'], 'pyinstaller': ['PyInstaller'], 'markupsafe': ['markupsafe'], 'jinja2': ['jinja2'],
    'ujson': ['ujson'], 'orjson': ['orjson'], 'simplejson': ['simplejson'], 'pyperclip': ['pyperclip'],
    'colorama': ['colorama'], 'tqdm': ['tqdm'], 'six': ['six'], 'requests': ['requests'], 'numpy': ['numpy'],
    'pandas': ['pandas'], 'scipy': ['scipy'], 'click': ['click'], 'rich': ['rich'], 'httpx': ['httpx'],
    'pydantic': ['pydantic'], 'fastapi': ['fastapi'], 'flask': ['flask'], 'django': ['django'],
    'python_json_logger': ['pythonjsonlogger'], 'pyhumps': ['humps'], 'pyrsistent': ['pyrsistent'],
    'xmltodict': ['xmltodict'], 'toml': ['toml'], 'tomlkit': ['tomlkit'], 'pytz': ['pytz'], 'tzdata': [],
    'certifi': ['certifi'], 'charset_normalizer': ['charset_normalizer'], 'idna': ['idna'], 'urllib3': ['urllib3'],
    'shapely': ['shapely'], 'pyproj': ['pyproj'], 'geopandas': ['geopandas'], 'fiona': ['fiona'],
    'networkx': ['networkx'], 'sympy': ['sympy'], 'numba': ['numba'], 'torch': ['torch'], 'torchvision': ['torchvision'],
    'scikit_image': ['skimage'], 'imageio': ['imageio'], 'pywavelets': ['pywt'], 'h5py': ['h5py'],
    'tables': ['tables'], 'pyarrow': ['pyarrow'], 'fsspec': ['fsspec'], 's3fs': ['s3fs'], 'zarr': ['zarr'],
    'xarray': ['xarray'], 'netcdf4': ['netCDF4'], 'cftime': ['cftime'], 'dask': ['dask'], 'distributed': ['distributed'],
}
PIPREQS_MAP = {}
for cand in glob.glob('/private/tmp/claude-501/**/venv/lib/python3.11/site-packages/pipreqs/mapping', recursive=True):
    for line in open(cand, encoding='utf-8', errors='ignore'):
        if ':' in line:
            imp, pkg = line.strip().split(':', 1)
            PIPREQS_MAP.setdefault(norm(pkg), set()).add(imp)
    break

def import_names_for(dep):
    d = norm(dep)
    names = set()
    if d in MANUAL:
        names |= set(MANUAL[d])
    if d in PIPREQS_MAP:
        names |= PIPREQS_MAP[d]
    names.add(d)
    if d.startswith('python_'):
        names.add(d[len('python_'):])
    if d.startswith('py') and len(d) > 3:
        names.add(d[2:])
    return {n for n in names}

# ---------- build file parsing (mimics DI-Bench scheme choice) ----------
def parse_pyproject(text):
    try:
        d = tomllib.loads(text)
    except Exception:
        return None, 'toml_error'
    poetry = d.get('tool', {}).get('poetry', {})
    if poetry:
        deps = {norm(k) for k in (poetry.get('dependencies') or {}) if k.lower() != 'python'}
        return deps, 'poetry'
    if 'project' in d:
        deps = set()
        for s in d['project'].get('dependencies') or []:
            m = NAME_RE.match(s)
            if m:
                deps.add(norm(m.group(1)))
        return deps, 'pep621'
    return None, 'unsupported'

def apply_patch_to_file(repo, build_file, patch_text):
    if not patch_text.strip():
        return None
    with tempfile.TemporaryDirectory() as td:
        dst = pathlib.Path(td) / build_file
        dst.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy(repo / build_file, dst)
        pf = pathlib.Path(td) / 'p.diff'
        pf.write_text(patch_text)
        r = subprocess.run(['patch', '--batch', '--fuzz=5', '-p1', '-i', 'p.diff'], cwd=td, capture_output=True, text=True)
        if r.returncode != 0:
            shutil.copy(repo / build_file, dst)
            r = subprocess.run(['git', 'apply', '--allow-empty', '--ignore-whitespace', '--ignore-space-change', 'p.diff'], cwd=td, capture_output=True, text=True)
            if r.returncode != 0:
                return None
        return dst.read_text()

FENCE_RE = re.compile(r"```[a-zA-Z0-9_-]*\n(.*?)```", re.S)
def recover_from_trajs(iid):
    """Recover the model's intended build file from the raw assistant output."""
    tj = QWEN / iid / 'trajs.json'
    if not tj.exists():
        return None
    try:
        d = json.load(open(tj))
    except Exception:
        return None
    a = ''.join(m.get('content') or '' for m in d if m.get('role') == 'assistant')
    best = None
    for block in FENCE_RE.findall(a):
        if '[project' in block or '[tool.poetry' in block or 'dependencies' in block:
            if best is None or len(block) > len(best):
                best = block
    return best

# ---------- module graph ----------
def is_test_path(rel):
    parts = rel.parts
    if any(p in TEST_DIR_NAMES for p in parts[:-1]):
        return True
    name = parts[-1]
    return name.startswith('test_') or name.endswith('_test.py') or name == 'conftest.py' or name == 'tests.py'

def module_graph(repo):
    files = []
    for dp, dns, fns in os.walk(repo):
        dns[:] = [d for d in dns if d not in SKIP_DIRS and not d.startswith('.')]
        for f in fns:
            if f.endswith('.py'):
                files.append(pathlib.Path(dp) / f)
    roots = [repo] + [repo / 'src'] + [p for p in repo.glob('*/') if (p / '__init__.py').exists()]
    mod_of = {}
    for f in files:
        rel = f.relative_to(repo)
        for r in (repo / 'src', repo):
            try:
                rr = f.relative_to(r)
            except ValueError:
                continue
            parts = list(rr.with_suffix('').parts)
            if parts[-1] == '__init__':
                parts = parts[:-1]
            mod = '.'.join(parts)
            if mod:
                mod_of.setdefault(mod, f)
            break
    file_mod = {}
    for mod, f in mod_of.items():
        file_mod.setdefault(f, mod)
    internal_top = {m.split('.')[0] for m in mod_of}
    info = {}
    for f in files:
        try:
            tree = ast.parse(f.read_bytes())
        except Exception:
            continue
        thirds, internals = set(), set()
        mymod = file_mod.get(f, '')
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                for a in node.names:
                    top = a.name.split('.')[0]
                    if top in STDLIB:
                        continue
                    if top in internal_top:
                        internals.add(a.name)
                    else:
                        thirds.add(top)
            elif isinstance(node, ast.ImportFrom):
                if node.level and node.level > 0:
                    base = mymod.split('.')
                    if f.name != '__init__.py':
                        base = base[:-1]
                    base = base[:len(base) - (node.level - 1)] if node.level > 1 else base
                    target = '.'.join(base + ([node.module] if node.module else []))
                    internals.add(target)
                    for a in node.names:
                        internals.add(target + '.' + a.name if target else a.name)
                elif node.module:
                    top = node.module.split('.')[0]
                    if top in STDLIB:
                        continue
                    if top in internal_top:
                        internals.add(node.module)
                        for a in node.names:
                            internals.add(node.module + '.' + a.name)
                    else:
                        thirds.add(top)
        info[f] = dict(thirds=thirds, internals=internals, test=is_test_path(f.relative_to(repo)))
    def resolve(name):
        parts = name.split('.')
        for i in range(len(parts), 0, -1):
            m = '.'.join(parts[:i])
            if m in mod_of:
                return mod_of[m]
        return None
    edges = {f: {resolve(n) for n in d['internals']} - {None} for f, d in info.items()}
    return info, edges

def reachable_from_tests(info, edges):
    seen = set(f for f, d in info.items() if d['test'])
    stack = list(seen)
    while stack:
        f = stack.pop()
        for g in edges.get(f, ()):
            if g not in seen:
                seen.add(g)
                stack.append(g)
    return seen

# ---------- main ----------
rows = [json.loads(l) for l in open(ROOT / '.cache/dataset-dibench-regular.jsonl')]
py = [r for r in rows if r['language'] == 'python']
per = []
DEPROWS = []
agg = collections.Counter()
never_imported_examples = collections.Counter()
qwen_fp_examples = collections.Counter()
for r in py:
    iid = r['instance_id']
    repo = DATA / iid
    bf = r['build_files'][0]
    masked = (repo / bf).read_text()
    oracle_text = apply_patch_to_file(repo, bf, r['patch'])
    o_deps, scheme = parse_pyproject(oracle_text) if oracle_text else (None, 'apply_fail')
    rec = dict(instance_id=iid, scheme=scheme)
    if o_deps is None:
        rec['status'] = 'oracle_' + scheme
        per.append(rec); agg['oracle_fail'] += 1
        continue
    rec['n_oracle'] = len(o_deps)
    # Qwen
    qp = QWEN / iid / 'patch.diff'
    q_text = qp.read_text() if qp.exists() else ''
    q_deps = None
    if q_text.strip():
        q_file = apply_patch_to_file(repo, bf, q_text)
        if q_file is not None:
            # Kaggle run artifact: the file-listing header line leaked into the file content
            lines = q_file.splitlines()
            stripped = 0
            while lines and lines[0].strip() in (bf, pathlib.Path(bf).name):
                lines.pop(0); stripped += 1
            if stripped:
                agg['qwen_header_leak_fixed'] += 1
                q_file = '\n'.join(lines) + '\n'
            q_deps, q_scheme = parse_pyproject(q_file)
            # DI-Bench parses the model testbed with scheme chosen by *that* file; masked file keeps sections, so same scheme
    asrun_deps = q_deps
    if q_deps is None:
        rec['qwen_status'] = 'empty_or_unparseable'
        agg['qwen_empty_or_fail'] += 1
        asrun_deps = set()
    else:
        rec['qwen_status'] = 'ok'
    # as-run scoring (what DI-Bench's evaluator would see from the Kaggle patches)
    tp = len(asrun_deps & o_deps); fp = len(asrun_deps - o_deps); fn = len(o_deps - asrun_deps)
    rec.update(asrun_tp=tp, asrun_fp=fp, asrun_fn=fn)
    agg['asrun_tp'] += tp; agg['asrun_fp'] += fp; agg['asrun_fn'] += fn; agg['asrun_exact_set'] += int(asrun_deps == o_deps)
    # recovered scoring (model's actual output re-parsed from the trajectory)
    rec_text = recover_from_trajs(iid)
    r_deps = None
    if rec_text:
        r_deps, _ = parse_pyproject(rec_text)
    if r_deps is None:
        rec['recovered_status'] = 'unparseable'
        agg['recovered_unparseable'] += 1
        r_deps = set()
    else:
        rec['recovered_status'] = 'ok'
    q_deps = r_deps
    tp = len(q_deps & o_deps); fp = len(q_deps - o_deps); fn = len(o_deps - q_deps)
    rec.update(q_tp=tp, q_fp=fp, q_fn=fn, q_exact_set=int(q_deps == o_deps), q_predicted_empty=int(len(q_deps) == 0))
    agg['q_tp'] += tp; agg['q_fp'] += fp; agg['q_fn'] += fn; agg['q_exact_set'] += int(q_deps == o_deps); agg['q_predicted_empty'] += int(len(q_deps) == 0)
    # module graph
    info, edges = module_graph(repo)
    reach = reachable_from_tests(info, edges)
    all_thirds = collections.Counter()
    nontest_files_importing = collections.defaultdict(set)
    reach_thirds = set()
    for f, d in info.items():
        for t in d['thirds']:
            all_thirds[t] += 1
            if not d['test']:
                nontest_files_importing[t].add(f)
        if f in reach:
            reach_thirds |= d['thirds']
    n_files = len(info); n_test = sum(d['test'] for d in info.values())
    rec.update(n_py_files=n_files, n_test_files=n_test, n_reached_files=len(reach))
    imported, test_reach, never = 0, 0, 0
    small_footprint = 0
    for dep in o_deps:
        names = import_names_for(dep)
        hit = [n for n in names if n in all_thirds]
        foot = len(set().union(*[nontest_files_importing[n] for n in hit])) if hit else 0
        reach_flag = bool(hit) and any(n in reach_thirds for n in hit)
        DEPROWS.append(dict(instance_id=iid, dep=dep, imported=int(bool(hit)), test_reachable=int(reach_flag), footprint_files=foot, predicted_by_qwen=int(dep in q_deps)))
        if hit:
            imported += 1
            if reach_flag:
                test_reach += 1
            if 1 <= foot <= 2:
                small_footprint += 1
        else:
            never += 1
            never_imported_examples[dep] += 1
    rec.update(o_imported=imported, o_test_reachable=test_reach, o_never_imported=never, o_small_footprint=small_footprint)
    agg['o_total'] += len(o_deps); agg['o_imported'] += imported; agg['o_test_reachable'] += test_reach; agg['o_never'] += never
    agg['o_small_footprint'] += small_footprint
    agg['repos_with_small_footprint'] += int(small_footprint > 0)
    agg['repos_with_invisible_dep'] += int(imported - test_reach > 0 or never > 0)
    agg['repos_with_unreached_imported_dep'] += int(imported - test_reach > 0)
    # Qwen over-declaration: predicted deps not in oracle and never imported anywhere
    q_fp_never = 0
    for dep in q_deps - o_deps:
        if not [n for n in import_names_for(dep) if n in all_thirds]:
            q_fp_never += 1
            qwen_fp_examples[dep] += 1
    rec['q_fp_never_imported'] = q_fp_never
    agg['q_fp_never_imported'] += q_fp_never
    agg['n'] += 1
    per.append(rec)

def prf(tp, fp, fn):
    p = tp / (tp + fp) if tp + fp else 0.0
    r_ = tp / (tp + fn) if tp + fn else 0.0
    f = 2 * p * r_ / (p + r_) if p + r_ else 0.0
    return round(p, 3), round(r_, 3), round(f, 3)

summary = dict(
    n_instances=agg['n'], oracle_fail=agg['oracle_fail'], qwen_empty_or_fail=agg['qwen_empty_or_fail'], qwen_header_leak_fixed=agg['qwen_header_leak_fixed'],
    asrun_name_only_micro_PRF=prf(agg['asrun_tp'], agg['asrun_fp'], agg['asrun_fn']), asrun_exact_name_set_rate=round(agg['asrun_exact_set'] / max(agg['n'], 1), 3),
    recovered_unparseable=agg['recovered_unparseable'], qwen_predicted_empty_set=agg['q_predicted_empty'],
    qwen_name_only_micro_PRF=prf(agg['q_tp'], agg['q_fp'], agg['q_fn']),
    qwen_exact_name_set_rate=round(agg['q_exact_set'] / max(agg['n'], 1), 3),
    qwen_fp_total=agg['q_fp'], qwen_fp_never_imported=agg['q_fp_never_imported'],
    oracle_deps_total=agg['o_total'], oracle_imported=agg['o_imported'], oracle_test_reachable=agg['o_test_reachable'],
    oracle_never_imported=agg['o_never'],
    oracle_imported_but_not_test_reachable=agg['o_imported'] - agg['o_test_reachable'],
    repos_with_unreached_imported_dep=agg['repos_with_unreached_imported_dep'],
    repos_with_any_invisible_dep=agg['repos_with_invisible_dep'],
    oracle_small_footprint_deps=agg['o_small_footprint'], repos_with_small_footprint_dep=agg['repos_with_small_footprint'],
    pipreqs_mapping_loaded=len(PIPREQS_MAP) > 0,
    never_imported_top=never_imported_examples.most_common(25),
    qwen_fp_never_imported_top=qwen_fp_examples.most_common(20),
)
OUT.mkdir(parents=True, exist_ok=True)
json.dump(summary, open(OUT / 'summary_python.json', 'w'), indent=1)
import csv
with open(OUT / 'per_dep_python.csv', 'w', newline='') as fh:
    w = csv.DictWriter(fh, fieldnames=list(DEPROWS[0].keys())); w.writeheader(); w.writerows(DEPROWS)
with open(OUT / 'per_instance_python.csv', 'w', newline='') as fh:
    keys = sorted({k for r in per for k in r})
    w = csv.DictWriter(fh, fieldnames=keys); w.writeheader(); w.writerows(per)
print(json.dumps(summary, indent=1))
