# Oracle Blindness in Dependency Benchmarks

Everything for the paper *Remove This Dependency: Why Passing Tests Cannot Tell
You a Dependency Is Gone*. Self-contained: no preliminary DI-Bench exploration,
no Axon, no earlier BTP material.

## Layout

```
paper/        ACL submission source
code/         everything we wrote or modified
data/         benchmark instances and static analysis inputs
results/      855 per-instance execution results
reports/      generated result tables
docs/         explainers and audits
```

## The headline numbers

One canonical screening of the **complete candidate universe**: every dependency
declared by every repository whose gold manifest passes CI in our harness, each
removed and made unimportable from the repository's own frames. **622 of 622
candidates screened**, and every one is accounted for.

| | n | |
|---|---|---|
| Candidates screened | **622** | over 80 gold-passing repositories |
| **Verified removal pairs** | **348** | over 74 repositories — the benchmark |
| Oracle blind spots (CI passes without the package) | **226** | see the decomposition below |
| Excluded, each with a stated reason | **48** | `data/instances.excluded.jsonl` |

Pool composition: 174 regular / 174 large; tiers strong 197, hard 68, medium 42,
indirect 41.

### The blind spots are four different things

Reporting 226 as "oracle blindness" would not survive scrutiny, and should not.
`docs/BLIND_SPOT_ANATOMY.md` has the detail:

| Category | n | What it is |
|---|---|---|
| Over-declared | 149 | no trace of the package anywhere in the repository |
| Used without importing | 23 | a plugin, entry point, build backend or CI tool |
| **Imported, unguarded, untested** | **46** | **oracle blindness in the strict sense** |
| Optional by design | 8 | `try/except ImportError` with a working fallback |

**The strict figure is 46.** Over-declaration is the dependency-bloat result the
debloating literature already documents, measured here on a benchmark's own
instances. "Used without importing" bounds what any import-graph predictor can
achieve, ours included, and belongs in Limitations.

### How to report the rate

**Never quote the pooled rate alone.** Dependency-weighted it is 38.6%, but
`swirlai_swirl-search` declares 172 dependencies and supplies 126 of the 226
blind spots, so pooling measures that repository more than the phenomenon.

| Statistic | Value |
|---|---|
| **Median per-repository blindness rate** | **18.8%** |
| Pooled, dependency-weighted | 38.6% |
| Pooled, excluding `swirl-search` | 23.6% |
| **Repositories with at least one blind spot** | **35 of 51** |

Five repositories with five or more candidates have none at all, so this tracks
test-suite coverage rather than being universal.

### The grader

Structural gates over all 617 constructed cheat variants (`results/variants_structural.json`):

| family | n | rejected | caught by |
|---|---|---|---|
| hide | 77 | 77 | G1 |
| trade | 73 | 73 | G8 |
| weaken_tests | 80 | 78 | G7 |
| stub | 80 | 65 | G3 |
| stub_smart | 80 | 65 | G3 |
| vendor | 67 | 48 | G3 |
| *mutant* (honest deletion) | 80 | *1* | correct: nothing should object |
| **pseudo_genuine** | **80** | **0** | **nothing structural catches it** |

The last row is why the behavioural gate exists, and it reproduces Sushane's
finding from an independent implementation. G2, G4a and G5 did not run in that
pass, so no family above is cleared by them.

**False rejection is not yet measured.** Detection without it is half a result —
a gate that rejected everything would score perfectly in that table. It needs
reference removals, and none exist on disk yet.

## paper/

- `acl_latex.tex` — submission source, ACL format. Needs `acl.sty` and
  `acl_natbib.bst` from the official template placed alongside it.
- `custom.bib` — bibliography. **Several 2026 entries are marked for
  verification before camera-ready.**

## code/

**`analysis/`** — measurement, the paper's core
- `prepare.py` — builds evaluation sets, including the 531 deletion mutants
- `mechanism.py` — splits invisible deletions into phantom vs blind spot (F3)
- `join.py` — conditions any result set on gold-passing instances
- `phantom_predict.py` — dependency-layer predictor from PyPI metadata (F4)
- `analyze_python.py` — import footprint and test reachability (F4 code layer)
- `symbol_reachability.py`, `run_pycg.py`, `axon_dump.py` — symbol-level
  analysis. **See the F11 warning below.**
- `score_pipreqs.py` — static baseline (F9)
- `summarize.py` — result aggregation

**`benchmark/`** — the removal benchmark
- `make_cheats.py` — generates hide / vendor / stub variants (F5)
- `gates.py` — the six-gate oracle
- `review_sheet.py` — hand-audit sheet generator

**`agent/`** — the agent harness
- `agent_runner.py` — SWE-agent-style scaffold: 100-line viewer, range-based
  edit with syntax linting, observation collapsing, temperature 0, pass@1
- `run_overnight.sh` — multi-model driver with per-model budget guards

**`harness-patches/`** — the four DI-Bench files we changed. Apply these over a
clean DI-Bench checkout.
- `dibench_utils_docker.py` — adds `DIBENCH_CONTAINER_MODE` so the harness runs
  on CI runners; adds an image cache mount
- `dibench_utils_ci.py` — preloads cached act images; **treats a non-zero act
  exit or a job with no executed steps as failure** (upstream reports "Job
  succeeded" for jobs that never start)
- `dibench_eval.py` — per-instance crash isolation; explicit index range
- `dibench_utils_buildfile_python.py` — fake-package check no longer crashes on
  VCS-URL dependencies

`dibench-eval.yml` — GitHub Actions workflow. Runs on free runners with sysbox.

## data/

- `instances.jsonl` — the benchmark: 348 pairs over 74 repositories, four tiers
- `instances.blind.jsonl` — the 226 oracle blind spots, a result in their own right
- `instances.excluded.jsonl` — all 41 dropped candidates, each with its reason
- `audit_sheet_final.md` — stratified 40-pair hand-audit sheet
- `agent_instances_16.jsonl` — the 16-instance agent subset
- `cheats.jsonl`, `agent.jsonl` — evaluation set definitions
- `per_dep_python.csv` — per-dependency import footprint and reachability
- `phantom_pred.json` — static phantom predictions

Not included: the DI-Bench repositories (219 MB) and dataset. Fetch from the
[DI-Bench release](https://github.com/microsoft/DI-Bench/releases) into
`.cache/repo-data/python/`.

## results/

One JSON per instance, `{"instance_id", "exec": "pass"|"fail"|"error", ...}`.
CI logs excluded for size; regenerate by re-running the workflow.

| Directory | Count | What |
|---|---|---|
| `gold_honest/` | 96 | DI-Bench's own answers re-run |
| `mutation_merged/` | 531 | single-dependency deletions |
| `cheats/` | 176 | constructed fakes |
| `agent_final/` | 52 | four models on the removal task |

## Known issues, read before submitting

**F11 — the symbol-level result is wrong.** We reported PyCG covering 18 of 51
repositories and scoring worse than file-level. An audit found `--package .` in
`run_pycg.py` forces whole-program analysis, which is the documented
non-scaling configuration; a 2-file repository that times out at 240 s with the
flag finishes in 0.2 s without it. On the same rows symbol-level **beats**
file-level on F1 (0.545 vs 0.522). Re-run without the flag or demote to a
limitation. **Do not publish as a negative result.**

**F8 — "no spontaneous cheating" is not supportable as worded.** `gates.py`
inspects only newly added files, so it never examined agents' modifications to
existing files. Report as absence of evidence.

**Two "first" claims are false.** Manifest mutation (version pins) was done by
Shulepov, arXiv 2608.27100, August 2026. The novel contribution is the
phantom/blind-spot mechanism split, not manifest mutation itself.

**Citations.** `docs/LIT_REVIEW_AUDIT.md` lists ~20 papers to add and 11 bib
entries to correct.

## Reproducing

```bash
pip install -e .            # DI-Bench, then apply code/harness-patches/
python code/analysis/prepare.py --set mutation ...   # build mutants
# dispatch code/dibench-eval.yml on GitHub Actions
python code/analysis/join.py results/gold_honest results/mutation_merged
python code/analysis/mechanism.py results/gold_honest results/mutation_merged
```

Static analyses need no execution and run locally in seconds.

## docs/

- `All_Findings.pdf` — twelve findings with significance and role in the argument
- `Project_Explained.pdf` — the work explained from first principles
- `Remove_This_Dependency.pdf` — the team working document
- `LIT_REVIEW_AUDIT.md` — per-experiment novelty audit against the literature
- `AUDIT_PROMPT.md` — adversarial audit prompt for an independent session
