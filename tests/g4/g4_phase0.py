import sys, pathlib, subprocess, os
sys.path.insert(0,'/Users/rishivyalla/Downloads/DI-Bench/scripts/gh')
from record_usage import write_recorder
T=pathlib.Path(sys.argv[1]); out=T/sys.argv[2]
if out.exists(): out.unlink()
write_recorder(T/'repo','slugger',['slugger'],['app','tests'],out=str(out))
env=dict(os.environ, PYTHONPATH=f"{T}/site:{T}/repo")
r=subprocess.run([sys.executable,'-m','pytest','-q','tests'],cwd=T/'repo',env=env,capture_output=True,text=True)
print('  pytest:', (r.stdout.strip().splitlines() or ['?'])[-1][:70])
print('  recorded calls:', sum(1 for _ in open(out)) if out.exists() else 0)
