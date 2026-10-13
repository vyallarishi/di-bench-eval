# Independent verification: what to check and how

You are verifying a paper's empirical claims from scratch. Assume nothing in
the paper or in this file is correct. Every number below has a command that
recomputes it; where a command disagrees with the paper, the command wins and
the discrepancy is the finding.

## Setup

```bash
git clone https://github.com/anon-undep/di-bench-eval.git && cd di-bench-eval
python3 -m venv .venv && .venv/bin/python -m pip install -q tomli pytest
mkdir -p .cache && cd .cache
R=https://github.com/microsoft/DI-Bench/releases/download/v1.0
curl -sL -o dataset-dibench-regular.jsonl $R/dataset-dibench-regular.jsonl
curl -sL -o dataset-dibench-large.jsonl   $R/dataset-dibench-large.jsonl
curl -sL -o py.tar.gz $R/dibench-regular-python.tar.gz && mkdir -p repo-data && tar -xzf py.tar.gz -C repo-data
curl -sL -o pyl.tar.gz $R/dibench-large-python.tar.gz && tar -xzf pyl.tar.gz -C repo-data
```

The repository checkouts are ~840 MB compressed. Everything else is in the repo.

## The claims, and the command for each

Run each, then compare with the paper. A mismatch is a defect to report, not
a number to adjust.

| # | claim | command |
|---|---|---|
| 1 | the census: silent pairs and the four causes | `python3 -c "import json,collections;d=json.load(open('oracle-blindness/results/attribution.json'));print(collections.Counter(r['disposition'] for r in d));print(collections.Counter(r['cause'] for r in d if r['disposition']=='silent'))"` |
| 2 | pool composition: 330 pairs, repositories, tiers, footprints | `python3 -c "import json,collections;p=[json.loads(l) for l in open('pilot/instances.jsonl')];print(len(p),len({r['instance_id'] for r in p}));print(collections.Counter(r['tier'] for r in p))"` |
| 3 | counterfeits through the structural gates, per family | `.venv/bin/python scripts/gh/run_variants.py --patches <617-corpus>/patches --dataset .cache/dataset-dibench-regular.jsonl --out /tmp/v.json` |
| 4 | copy detection: 139 copies flagged, 0 false positives | `python3 -c "import json;d=json.load(open('oracle-blindness/results/g3_fingerprint.json'))['result']['sets'];[print(k,v['n'],v['scored'],v['at_threshold']['0.6']) for k,v in d.items()]"` |
| 5 | observability: 714 functions, 23/25/52% | `python3 -c "import json;d=json.load(open('oracle-blindness/results/observability.json'));print({k:v for k,v in d.items() if k!='pairs'})"` |
| 6 | agent results and the per-gate attribution | `python3 scripts/gh/reconcile.py --grades data/verdicts/g3_*.json --ablation data/analysis/ablation_agents.json` |
| 7 | the ablation, rejection separated from abstention | `python3 scripts/gh/ablation.py --grades data/verdicts/g3_*.json` |
| 8 | counterfeits the tests miss | `python3 -c "import json;d=json.load(open('data/family_ci/pseudo_genuine_rebuilt75.json'));ok=[r for r in d['rows'] if r['FP']==0 and r['FN']==1];print(len(ok),sum(1 for r in ok if r['ci']!='pass'),sum(1 for r in ok if r['ci']=='pass'))"` |
| 9 | the gate unit tests | `.venv/bin/python tests/gates/test_gates.py` |
| 10 | line-shift sensitivity | `python3 scripts/gh/lineshift_probe.py --shift 7` |

## Known defects, already found

Report these as confirmed rather than rediscovering them, and check nothing
similar remains:

- **3 gate unit tests fail at HEAD** (`baseline suite passes`,
  `called-but-unasserted function is pseudo-tested`, `fraction reported`), all
  in G4c/mutation. Pre-existing, cause not diagnosed.
- **A pure line shift changes the behavioural verdict.** Sites are keyed by
  `file:line`; the usage level absorbs a shift only where it has coverage,
  which is 969 of 4,278 recorded sites (23%). An attempted fix was reverted
  because it broke the gate tests; the keying is unchanged.
- **The 617-variant corpus was built on a pre-revision pool.** Only ~46% of
  its variants sit on current pool pairs, so any CI run over it has a smaller
  denominator than 617 and the two must not be conflated.
- **`variants_structural.json` predates `gate_vendor`.** It shows 19 vendored
  copies surviving; the current grader rejects all 67. Stamp that file's
  commit separately from the harness head.
- **The block announced in 195 of 300 agent runs.** Non-announcement is
  environmental: the same repositories are silent in trace runs that contain
  no agent edits.

## What is not in this repository

- the counterfeit corpus (`collaborator-b/617_variant_corpus/`) and the hand-written
  references live in `github.com/anon-undep/DependencyRefactoring`
- the harness runs on GitHub Actions in this repository; re-running them needs
  push access and several hours of free-runner time
- no held-out references exist; there are exactly 32

## How to report

For each claim: the command, its output, and whether it matches the paper.
Where it does not, say which is right and why. Where a claim cannot be checked
from what is released, say that rather than inferring it.
