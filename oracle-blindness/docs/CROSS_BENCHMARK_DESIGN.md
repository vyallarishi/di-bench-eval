# Generalising the oracle result across dependency pipelines

The single reviewer sentence that would keep this paper out of a main track is *"this is a finding about DI-Bench."* This document is the answer: the same deletion probe, applied to every execution-graded dependency/environment pipeline we can run, showing that the failure is a property of the **oracle class**, not of one benchmark.

What makes this more than a repetition is that these pipelines **do not share an oracle**. They sit on a spectrum of strictness, and the probe's outcome is predictable from the oracle's design — which turns four separate measurements into one argument.

## The spectrum, verified in code and prose

| Pipeline | Oracle, exactly | Can it see a wrong dependency set? |
|---|---|---|
| **Repo2Run** (arXiv 2502.13681, ByteDance; 420 Python repos) | `pytest --collect-only -q` must succeed, then tests run — success is judged "regardless of whether they pass or fail" | **No, by construction.** Only collection must work. A declaration set that imports cleanly passes even if every test fails. |
| **EnvBench** (arXiv 2503.14443, JetBrains, DL4C@ICLR 2025; 329 Python repos) | `pyright --level error --outputjson`, then count diagnostics with `rule == "reportMissingImports"`; success = exit 0 **and** zero such diagnostics (`evaluation/scripts/python_build.sh:39-48`) | **No, by construction.** Counts unresolved imports only. Any dependency whose deletion still leaves imports resolvable scores zero issues. Over-declaration is never penalised. |
| **DI-Bench** (Findings of ACL 2025; 581 repos, 4 languages) | the repository's own CI replayed; score 1 iff all tests pass | **Partially — and this is what we measured.** Strongest oracle of the three, and still blind to ~half of single-dependency deletions. |
| **SetupBench** (arXiv 2507.09063; 93 instances) | per-task "deterministic success commands" | **No minimality check.** Verifies functional presence; an agent that over-installs satisfies it. |

The argument writes itself: **the strongest oracle in the family is CI, and CI is blind half the time. The others are weaker than CI.** A reviewer cannot answer that by pointing at a benchmark we did not test, because the ones we did not test are weaker still.

## Why EnvBench and Repo2Run need no new experiment to indict

Their oracles are *analytically* blind, and we can state the result as a proof rather than a measurement:

- EnvBench: deleting a declaration changes `reportMissingImports` only if the package is unimportable afterwards. A phantom install leaves it importable, so the diagnostic count is unchanged and the instance still scores success. The 115-of-233 phantom population we already measured is, by this argument, invisible to EnvBench's oracle *with certainty*, not probability.
- Repo2Run: collection succeeding is strictly weaker than tests passing. Any deletion invisible to CI is invisible to collection-only. Our DI-Bench blind spots are therefore a **lower bound** on Repo2Run's.

This is the cheap, rigorous half. It costs no compute and it is the part a reviewer cannot argue with.

## Pilot result: EnvBench's oracle is insensitive to the declared set (measured)

Run on a synthetic two-dependency project, using the oracle exactly as
`evaluation/scripts/python_build.sh` implements it (`pyright --level error
--outputjson`, count diagnostics with `rule == "reportMissingImports"`):

| Manipulation | reportMissingImports | EnvBench verdict |
|---|---|---|
| Both dependencies declared and installed (baseline) | 0 | success |
| One declaration **deleted**, package still installed | 0 | success |
| Four never-imported packages **added** to the manifest | 0 | success |
| **Every** declaration removed, packages still installed | 0 | success |
| Import of a package that is neither installed nor stubbed (control) | 1 | fail |

The oracle is insensitive in both directions. It measures *whether imports
resolve in the environment as configured*, which is a different property from
*whether the declared dependency set is correct*. An empty dependency list
scores success provided the packages are present. Over-declaration is never
penalised.

**A second, independent effect found while building the control.** Pyright
bundles typeshed stubs, so an import resolves even when the package is absent
from the environment entirely. Our first control run therefore reported zero
missing imports with `tabulate` genuinely uninstalled — the bundled stub
satisfied it. Of the 201 stub packages shipped with pyright, **30 of the 206
distinct dependencies in our own pool (15%) are covered**, including
`cachetools`, `colorama`, `croniter`, `flake8`, `jmespath` and `jsonschema`.
For those packages the oracle cannot detect absence from the environment
either, which is a stronger statement than insensitivity to the manifest.

**Caveats to state in the paper, not to hide.** This is a synthetic project,
not EnvBench's 329 repositories, and it demonstrates the *mechanism* rather
than a rate. The honest claim is analytic — the oracle counts unresolved
imports and nothing else, so any manipulation that leaves imports resolvable
is invisible to it by construction — with the table as a demonstration. A rate
over EnvBench's own repositories needs their Docker image and a working
environment per repo, which the dataset does not ship (see risks below).

## What we should actually run, and in what order

**Tier 1 — EnvBench, revised.** EnvBench ships **no gold environment**: an
agent produces `bootstrap_script.sh` and the oracle runs afterwards. So the
deletion probe as applied to DI-Bench has no baseline to delete from, and the
original plan in this document was wrong.

Two things replace it, both cheap:

1. *The analytic statement plus the demonstration table above.* This is the
   defensible core and it is already done.
2. *A rate over real repositories, agent-free.* For each of the 329 Python
   repositories: install the declared dependency set, confirm the oracle
   reports success, then delete one declaration at a time and re-run. No agent
   and no gold script needed, because we construct the working environment
   ourselves from the manifest. Instances whose dependencies will not install
   are reported as excluded, exactly as in our own funnel. This yields a
   comparable rate and is worth doing if the install step is tractable for a
   decent fraction of the 329.

Report both. The analytic argument cannot be attacked; the rate makes it vivid.

**Tier 2 — Repo2Run, sampled.** Its harness builds Docker images per repo, so it is heavier. Sample 40–60 repositories, run the deletion probe against `pytest --collect-only`, and report. The analytic argument carries the rest.

**Tier 3 — SetupBench, discussion only.** 93 instances, task-specific success commands, no minimality check. Treat as a documented case of the same oracle class rather than a measurement. Do not overclaim from 93 heterogeneous tasks.

## How this reshapes the paper

The contribution becomes two-level, and the title should change to match:

1. **Oracle blindness is a property of execution-graded dependency evaluation**, demonstrated across four independently built pipelines whose oracles span collection-only, static-import, and full-CI strictness. The failure is *worse* the weaker the oracle, exactly as predicted.
2. **For the removal task specifically, a sound oracle exists** — the removed library — and here is the grader that uses it, with its detection and false-rejection rates.

Section 2 of the paper (the "two problems" framing) becomes: *no benchmark measures removal, and no grader can certify it* — now supported across the family rather than on one target.

## Honest risks, recorded before we run

- **EnvBench has no gold environments — checked and confirmed.** The dataset
  provides repository metadata, contents, READMEs and workflows, but no
  reference install script; its best agent configures only 6.69% of Python
  repos. Tier 1 is therefore restructured as above: we build the environment
  from the manifest ourselves rather than relying on a shipped baseline.
- **The typeshed-stub effect cuts both ways.** It strengthens the claim about
  the oracle, but it also means our own `pyright`-based measurements must
  disable bundled stubs (or report with and without) to be interpretable.
- **Different repository populations.** EnvBench deliberately excludes repos configurable by deterministic scripts; DI-Bench requires CI. Overlap is probably small, so we cannot pool the numbers — report per benchmark, never aggregated.
- **Scope discipline.** Four shallow measurements are worth less than one deep benchmark plus a validated grader. If Tier 1 is not clean within a day, cut to the analytic argument and keep the depth.
- **Our own tooling assumes DI-Bench's layout.** `manifests.py` is reusable (format-based, not benchmark-specific); `make_blocked.py` is reusable; `build_pool.py` and the workflow are not. Budget for a small EnvBench-specific driver rather than bending the existing one.

## Sources

- Repo2Run — arXiv 2502.13681; `github.com/bytedance/Repo2Run`
- EnvBench — arXiv 2503.14443, DL4C@ICLR 2025; `github.com/JetBrains-Research/EnvBench`; oracle at `evaluation/scripts/python_build.sh`
- DI-Bench — Findings of ACL 2025; arXiv 2501.13699
- SetupBench — arXiv 2507.09063
