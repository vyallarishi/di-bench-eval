import sys, pathlib, subprocess, os, shutil
sys.path.insert(0,'/Users/rishivyalla/Downloads/DI-Bench/scripts/gh')
from record_usage import write_recorder
T=pathlib.Path(sys.argv[1]); variant=sys.argv[2]; out=T/f'cand_{variant}.jsonl'
# fresh copy of the repo with the candidate's replacement in place
work=T/f'work_{variant}'
if work.exists(): shutil.rmtree(work)
shutil.copytree(T/'repo', work, ignore=shutil.ignore_patterns('sitecustomize.py','conftest.py','__pycache__','.pytest_cache'))
shutil.copy(T/f'replacement_{variant}.py', work/'app'/'textutil.py')
(work/'app'/'core.py').write_text((T/f'core_{variant}.py').read_text())
(work/'pyproject.toml').write_text('[project]\nname = "app"\ndependencies = []\n')
if out.exists(): out.unlink()
# record the REPLACEMENT at the same call sites: instrument app.textutil
write_recorder(work,'slugger',['slugger','app.textutil'],['app','tests'],out=str(out),site_exclude=['app/textutil.py'])
env=dict(os.environ, PYTHONPATH=f"{T}/site:{work}")
r=subprocess.run([sys.executable,'-m','pytest','-q','tests'],cwd=work,env=env,capture_output=True,text=True)
line=(r.stdout.strip().splitlines() or ['?'])[-1][:60]
print(f'  [{variant}] pytest: {line}   recorded: {sum(1 for _ in open(out)) if out.exists() else 0}')
