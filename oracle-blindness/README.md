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

Rebuilt 2026-10-06 by a single canonical screening of the **complete candidate
universe**: every dependency declared by every repository whose gold manifest
passes CI in our harness, each removed and made unimportable from the
repository's own frames. 622 of 622 candidates screened, nothing missing.

| Finding | Value | Where it comes from |
|---|---|---|
| DI-Bench gold patches still passing | 51 of 96 (regular), 32 of 50 (large) | `results/gold_honest/` |
| Candidates screened | 622 over 80 repositories | `data/instances*.jsonl` |
| **Verified removal pairs** | **355 over 74 repositories** | `data/instances.jsonl` |
| **Oracle blind spots** (CI passes without the package) | **226** | `data/instances.blind.jsonl` |
| Excluded, with a stated reason | 41 | `data/instances.excluded.jsonl` |
| Constructed cheats passing CI | 61 of 176 (34.7%) | `results/cheats/` |
| Stubs evading every install-level gate | 8 of 8 | `results/gates_cheats.json` |

### How to report the blindness rate

**Do not quote the pooled rate alone.** Dependency-weighted it is 38.6%
(220/570 over repositories with at least three candidates), but a single
repository, `swirlai_swirl-search`, declares 172 dependencies and contributes
126 of the 226 blind spots. Pooling therefore measures that repository more
than it measures the phenomenon.

| Statistic | Value |
|---|---|
| Median per-repository blindness rate | **18.8%** |
| Mean per-repository blindness rate | 22.6% |
| Pooled, dependency-weighted | 38.6% |
| Pooled, excluding `swirl-search` | 23.6% |
| Repositories with at least one blind spot | **35 of 51** |

The defensible headline is the per-repository median and the
35-of-51 incidence: **in most repositories a fifth of declared dependencies
can be removed without CI noticing, and 69% of repositories have at least one
such dependency.** The spread matters too: five repositories with five or more
candidates have *no* blind spots at all, so this is a property of test-suite
coverage rather than something universal.

A `swirl-search` blind spot was hand-checked: 67 tests genuinely run and pass
with `amqp` blocked. The population is real, not a harness artifact.

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

- `instances.jsonl` — the benchmark: 355 pairs over 74 repositories, four tiers
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
