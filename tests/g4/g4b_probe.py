"""G4b in miniature: generate neighbouring inputs from the recorded ones and
re-run both the library and the candidate. This is the step G4a cannot do,
because G4a is confined to the inputs the suite happened to exercise."""
import importlib.util, json, random, string, sys
sys.path.insert(0,'/private/tmp/claude-501/-Users-rishivyalla-Downloads-DI-Bench/96b75840-a33c-4f14-bdc8-66aeb44cb8cb/scratchpad/g4test/site')
import slugger
T='/private/tmp/claude-501/-Users-rishivyalla-Downloads-DI-Bench/96b75840-a33c-4f14-bdc8-66aeb44cb8cb/scratchpad/g4test'

def load(p,n):
    sp=importlib.util.spec_from_file_location(n,p); m=importlib.util.module_from_spec(sp); sp.loader.exec_module(m); return m

def neighbours(seed, rnd, k=200):
    """Mutate a recorded string argument: the distribution comes from the trace."""
    out=[seed]
    alphabet=string.ascii_letters+string.digits+" -_,.!?'\"/\\&%#@()[]{}:;\t"
    for _ in range(k):
        s=list(seed)
        for _ in range(rnd.randint(1,3)):
            op=rnd.choice(('ins','del','sub','dup'))
            if not s: op='ins'
            i=rnd.randrange(len(s)+1) if op=='ins' else rnd.randrange(len(s))
            if op=='ins': s.insert(i, rnd.choice(alphabet))
            elif op=='del': s.pop(i)
            elif op=='sub': s[i]=rnd.choice(alphabet)
            else: s.insert(i, s[i])
        out.append(''.join(s))
    return out

# recorded calls give us both the call shape and the seed values
recs=[json.loads(l) for l in open(f'{T}/reference.jsonl')]
print(f'seeded from {len(recs)} recorded calls\n')
mods={v:load(f'{T}/replacement_{v}.py',v) for v in ('honest','pseudo','hollow')}
rnd=random.Random(0)
print(f"{'candidate':10s} {'inputs':>8s} {'divergences':>12s}  first counterexample")
for name,m in mods.items():
    total=div=0; first=None
    for r in recs:
        fn=r['q'].split('.')[-1]
        seed=r['args'][0].get('v')
        rest=[a.get('v') for a in r['args'][1:]]
        for s in neighbours(seed, rnd):
            total+=1
            try: a=getattr(slugger,fn)(s,*rest)
            except Exception as e: a=('raised',type(e).__name__)
            try: b=getattr(m,fn)(s,*rest)
            except Exception as e: b=('raised',type(e).__name__)
            if a!=b:
                div+=1
                if first is None: first=(fn,s,a,b)
    verdict='PASS' if div==0 else 'FAIL'
    fc=f'{first[0]}({first[1]!r}) lib={first[2]!r} cand={first[3]!r}' if first else '-'
    print(f'{name:10s} {total:8d} {div:12d}  {fc[:72]}   -> G4b {verdict}')
