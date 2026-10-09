# Results ledger: every number the results section may quote, with its source

Compiled 10 October 2026 from the files named. Nothing here comes from an earlier
document; where a recomputation differs from a figure in an older doc, both are
given and the recomputed one is the one to quote, because its script is in the
repository (`scripts/gh/attribute.py`, `scripts/gh/flakiness.py`,
`scripts/gh/extract_traces.py`, `scripts/gh/trace_fidelity.py`,
`scripts/gh/false_rejection.py`, `scripts/gh/g4b_variants.py`).

## RQ1  How often is the CI oracle silent, and why

| figure | value | source |
|---|---|---|
| candidates screened | 622 over 80 gold-passing repositories | `data/instances*.jsonl` |
| verified pairs | 330 over 73 repositories (narrow 196, medium 41, wide 65, indirect 28) | `data/instances.jsonl` |
| silent | 239 | `data/instances.blind.jsonl` |
| excluded with reason | 53 | `data/instances.excluded.jsonl` |
| silent, attributed: over-declared / used without importing / optional by design / strict | **173 / 14 / 5 / 47** | `results/attribution.json` (BLIND_SPOT_ANATOMY.md had 172 / 13 / 5 / 49 from an uncommitted pass) |
| strict cases, repositories | 47 over 28 repositories | same |
| per-repository silent rate, repositories with ≥3 candidates | median **20.0%**, incidence **35 of 51** | `results/robustness.json` |
| pooled | 239 / 622 | same |
| drop the k most-silent repositories, k = 1, 3, 5, 10 | median 20.0 / 19.4 / 17.7 / **14.3**%; incidence 34/50, 32/48, 30/46, 25/41 | same |
| rate distribution over the 51 | 0%: 16; 1–10%: 1; 10–25%: 13; 25–50%: 15; >50%: 6 | same |
| correlation of rate with test-file share / test-reachable share / candidate count | **−0.34 / −0.31 / +0.34** | same |
| major-organisation repositories with ≥1 silent candidate | 11 of 12 (mandiant/speakeasy 0 of 6 is the exception) | same |
| silent cases in repositories where the block demonstrably attributed a repository frame | **222 of 239**; unconfirmed 17 (cowrie 11, sail 5, semchunk 1) | `results/trace_states.json` + pool evidence |
| rates excluding the 17 unconfirmed | median 19.4%, incidence 33 of 50, drop-10 median 12.5% | `results/robustness.json` (`rates_confirmed`) |
| gold rot | 51 of 96 regular; 29 of 45 large (in both runs) | `results/flakiness/gold_*.json` |
| verdict stability | verified 330/330 same; blind 226/226 same (13 are re-screens, not flips); gold 96/96 and 45/45 same | `results/flakiness/*.json`, `docs/FLAKINESS.md` |

## RQ2  Does the blindness belong to the oracle or to one benchmark

Per candidate, over the 569 screened candidates (622 − 53 excluded), from `results/oracle_overlap.json`:

| CI | static import check | collection-only | n |
|---|---|---|---|
| detects | detects | detects | 223 |
| detects | detects | silent | 75 |
| detects | silent | detects | 24 |
| detects | silent | silent | 8 |
| silent | detects | silent | **47** |
| silent | silent | silent | 192 |

Silent counts: CI 239, import check 224, collection-only 322. The import check
detects exactly the 47 strict cases CI misses and misses 32 that CI detects
(reached without an import). Derived, not observed: the import-check verdict is
"an unguarded import exists" (`attribution.json`), the collection-only verdict
is "the screening log shows a collection-stage error" (`results/collection_stage.json`).

## RQ3  Static prediction

Recomputed against the canonical screening from `results/attribution.json` (test
reachability over the current footprint code) and `data/phantom_pred.json` (closure
baseline, regular subset only):

| set | n | silent | test reachability: predicted / P / R / F1 | closure baseline: predicted / P / R / F1 |
|---|---|---|---|---|
| all screened candidates | 569 | 239 | 262 / **0.80 / 0.88 / 0.84** | — |
| candidates with a closure prediction | 214 | 53 | 68 / 0.62 / 0.79 / 0.69 | 76 / **0.34 / 0.49 / 0.40** |

The target is *silence*; a candidate with no importing file satisfies "no test reaches an
importing file" vacuously, which is why the all-candidate figure is higher. Predicting
*strict blindness* among the 350 candidates that have a footprint, by unreachability
alone: P 0.53, R 0.49, F1 0.51. `docs/PREDICTOR.md` reported 0.65 / 0.77 on the 214 with
an earlier footprint pass; the closure baseline reproduces exactly (of 76 flagged, CI
notices 50).

## RQ4  Structural gates

From `results/variants_structural.json` (617 variants, G2/G4a/G5 not run in that pass):

| kind | n | rejected | by |
|---|---|---|---|
| hide | 77 | 77 | G1 |
| trade | 73 | 73 | G8 |
| weaken tests | 80 | 78 | G7 |
| stub | 80 | 65 | G3 (65), G8 (8), G1 (1) |
| smart stub | 80 | 65 | G3 (65), G8 (8), G1 (1) |
| vendor (named copy) | 67 | 48 | G3 (46), G8 (14), G1 (1) |
| pseudo-genuine | 80 | **0** | — |
| honest deletion (control) | 80 | 1 | G1+G8 (TheHive4py/requests: declaration still present in the variant) |

CI verdicts, replication corpus (`results/cheats/`, 176 variants): hide 35 of 62 pass
the tests, vendor 18 of 52, stub 8 of 62.

False rejection, over-declared removals (`results/false_rejection.json`, re-run with the
screening logs and the vacuous-pass rule): **166 accepted, 5 inconclusive (G8 could not
resolve), 1 flagged by G1** (mu-editor/wheel: moved to `extras_require`, not removed —
a correct flag). 0 false rejections of 172.

## RQ5  The removed library as oracle

| figure | value | source |
|---|---|---|
| recordings | 85 pairs of 330, 37,947 calls (re-recorded with the current recorder) | `results/trace_states.json`, `data/traces/` |
| recorder outcome over the 330 | traced 85; loaded, no call 77; never loaded 168; CI not green under the recorder 62 | same |
| comparison decides on the whole value | **94.8%** (was 85.8%) | `docs/COMPARISON_FIDELITY.md` |
| pseudo-genuine with a recording | 10 of 80 with the current recordings (13 with the earlier ones); superseded by the pending re-run | `results/g4b_pseudo_genuine.json` |
| evaluable | 4 rewrites, 5 functions; **all rejected, 300 of 300 inputs each**; 3 no reconstructible input; rest no recording | same |
| references, CI under the block | **30 of 32 pass**; 2 fail on the workflow's lint step (humanlayer/python_dotenv: mypy on an edited test; inscriptis/requests: flake8 D401 and S310) | `results/references_ci.json` |
| references, structural gates | 30 pass every structural gate; the 2 above rejected by G2 only; G4a pending | `results/references_structural.json` |
| references, behavioural gate (replay on recorded inputs, local run, each reference's replacement module named as a target) | 21 inconclusive (the local run recorded no library calls); **4 accepted** (wcwidth, python_dateutil, python_slugify, boltons: every recorded call reproduced); **7 rejected as "missing"** | `results/references_g4.json` |

The seven rejections are false, and each has a mechanism: the pandas reference inlines the work into the calling function, so there is no callable to observe; the two tbump references (docopt, cli_ui) route calls through a new repository module that was named as a target but from which no call was recorded, an instrumentation gap still open; iso8601, colorama (130 of 4494 paired), flask_sqlalchemy and pytools (30 of 73 paired) pair some calls and miss the rest, where the rewrite changed the call's shape or site. On real rewrites the library-boundary replay therefore rejects 7 of 11 evaluable references. Recording at the enclosing project function rather than at the library boundary, which the design document proposed, is the remedy and is not implemented. The generated-neighbour layer was not run on the references, since it pairs library and replacement functions by name and a rewrite renames them.

**Pending re-runs (dispatched 9 October 18:28Z, runs 37973530805, 37973536037,
37973540628, 37973545522):** the recorder and the block were found to lose their output
whenever they load through `conftest.py` rather than `sitecustomize.py`, because pytest
has redirected fd 1 by then. Both now write through pytest's saved console descriptor.
The trace sets and the blind-side sets were regenerated and re-dispatched; the recording
coverage and the activation confirmation above will be replaced by their results.

## RQ6  Benchmark and agents

Pilot: 4 agents on 15 tasks, 52 attempts, 7 pass CI (DeepSeek-V3.2 5 of 15, GPT-5.1
1 of 16, Claude Sonnet 5 1 of 8, Qwen3-Coder 0 of 13). Gate verdicts on the 7: *pending
(authors)*. Source: `results/agent_final/`.

## Open items for the authors

1. Agent pilot through the seven gates.
2. The two reference lint failures: rephrase the docstring and add a `noqa` for S310
   in the inscriptis reference; add return annotations to the two test functions in the
   humanlayer reference; re-dispatch `references`.
3. Reference provenance for §3.3: who wrote them, selection, written before the gates.
4. Corpus provenance for §4.3.
