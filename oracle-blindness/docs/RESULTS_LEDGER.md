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
| silent, before the activation rule / counted | 239 / **226** (13 excluded: inconclusive, block not observed; `results/activation.json`) | `data/instances.blind.jsonl`, `results/activation.json` |
| excluded with reason | 53 by construction + 13 by the activation rule = 66 | `data/instances.excluded.jsonl`, `results/activation.json` |
| silent, attributed: over-declared / used without importing / optional by design / strict | **173 / 14 / 5 / 34** after the rule (before it 173 / 14 / 5 / 47; every one of the 13 excluded is strict) | `results/attribution.json`, `results/activation.json` |
| strict cases, repositories | 34 over 21 repositories (was 47 over 28) | same |
| per-repository silent rate, repositories with ≥3 candidates | median **18.8%**, incidence **33 of 49** (counting the 13: 20.0%, 35 of 51) | `results/robustness.json` (`confirmed`; `all_candidates` keeps the unexcluded figures) |
| pooled | 226 / 609 (239 / 622 before the rule) | same |
| drop the k most-silent repositories, k = 1, 3, 5, 10 | median 17.7 / 15.5 / 14.3 / **12.5**%; incidence 32/48, 30/46, 28/44, 23/39 (before the rule 20.0 / 19.4 / 17.7 / 14.3; 34/50, 32/48, 30/46, 25/41) | same |
| rate distribution over the 49 | 0%: 16; 1–10%: 1; 10–25%: 14; 25–50%: 13; >50%: 5 (over the 51 before the rule: 16 / 1 / 13 / 15 / 6) | same |
| correlation of rate with test-file share / test-reachable share / candidate count | **−0.30 / −0.36 / +0.37** (before the rule −0.34 / −0.31 / +0.34) | same |
| major-organisation repositories with ≥1 silent candidate | 10 of 12: tweepy's two silent cases are both excluded by the rule, so it joins mandiant/speakeasy at zero; cowrie keeps 8 of 11 (its other 3 excluded). The list of 12 is the authors' (ROBUSTNESS.md names 9); confirm against it | `results/activation.json` |
| activation, from the corrected reruns (every one of the 239 silent pairs replayed, all 239 pass again) | block announced in **217 of 239** logs (install line on stderr 56, pytest hook line 208); 9 more never import the package; **13 excluded**: cowrie 3, sail 4, tweepy 2, tournesol 1, cgen 1, django-revproxy 1, semchunk 1. The repository-level cross-check (another pair of the same repository detected by the block raising in a repository frame) also covers exactly 217; it does not count | `results/activation.json` |
| why the 13 show no announcement | sail runs `python -m unittest`, django-revproxy and cowrie run under tox, tournesol and cgen run pytest from a subdirectory, tweepy runs its own runner: the root `sitecustomize.py`/`conftest.py` are never imported. semchunk runs pytest 8.4 from the root and announces locally with the same patch; its harness silence is unexplained | the rerun logs under `res_repeat_blind*` (scratch) |
| gold rot | 51 of 96 regular; 29 of 45 large (in both runs) | `results/flakiness/gold_*.json` |
| verdict stability (corrected reruns, `--ignore-injected`) | blind regular 53: 42 pass/pass, 11 fail→pass, the 11 being the re-screened pairs whose first screening crashed in the pre-fix blocker; blind large 186: 184 pass/pass, 2 fail→pass (NVFlare six, sqlalchemy: re-screened). **0 flips** among pairs whose first verdict was already pass; verified 330/330 and gold 96/96, 45/45 unchanged | `results/flakiness/blind_*.json`, `docs/FLAKINESS.md` |

## RQ2  Does the blindness belong to the oracle or to one benchmark

Per candidate, over the 556 screened candidates (622 − 53 excluded by construction − 13 by
the activation rule), from `results/oracle_overlap.json` (recomputed by `oracle_overlap.py`;
the pre-rule table over 569 had 223 / 75 / 24 / 8 / 47 / 192):

| CI | static import check | collection-only | n |
|---|---|---|---|
| detects | detects | detects | 223 |
| detects | detects | silent | 75 |
| detects | silent | detects | 24 |
| detects | silent | silent | 8 |
| silent | detects | silent | **34** |
| silent | silent | silent | 192 |

Silent counts: CI 226, import check 224, collection-only 309. The import check
detects exactly the 34 strict cases CI misses and misses 32 that CI detects
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

### The replication corpus through the behavioural gates (added 10 Oct; `results/g4_cheats.json`, `results/g4b_cheats.json`)

The 176 hide/stub/vendor variants with CI verdicts (`results/cheats/`) were run through
`run_g4.py` with the two-level recorder (one local reference run per pair, candidate run
per variant) and, where a reference trace exists and the variant adds a module, through
G4b (`g4b_variants.py`, library and replacement on inputs derived from the recorded ones;
the replacement is now loaded as a package under an alias so a stub or vendored package
resolves its relative imports). The earlier `results/g4_cheats.json` (every verdict
"missing", pairing broken across checkouts) is replaced. Only CI-passing variants are
reported, because the gate's question is what survives the tests:

| kind | variants | CI pass | G4a identical / divergent / inconclusive / not evaluable | G4b caught / agrees / cannot speak |
|---|---|---|---|---|
| hide | 62 | 35 | 4 / 0 / 2 / 29 | 0 / 0 / 35 (no added module: nothing for G4b to run) |
| stub | 62 | 8 | 1 / 1 / 1 / 5 | 1 / 0 / 7 |
| vendor | 52 | 18 | 4 / 0 / 1 / 13 | 0 / 1 / 17 |

Readings. A hidden declaration and a vendored copy *are* the library, so "identical" is
the correct behavioural verdict and G1 / G3 carry the rejection; the one hide variant
first reported divergent (fuzzy-c-means / joblib) was 43 random-initialisation results
that the library's own repeated calls also disagree on, which the nondeterminism rule,
now applied at the library boundary as well as at usage sites, sets aside. Of the 3
stubs the gate could evaluate, humanlayer / python_slugify is rejected (20 of 41 calls
divergent; G4b 300 of 300 generated inputs), flask-sock / simple_websocket is
inconclusive (one call fewer than the reference), and tplot / colorama is identical:
the only recorded call is `init()`, which returns None from the library and from the
stub, and on Linux colorama's `init()` does nothing, so the stub is behaviourally
equivalent on the platform CI runs on. **Not evaluable** is the dominant cell (47 of 61):
the reference suite is not runnable by the local runner (34: hide 23, vendor 10, stub 1),
the repository imports jax or torch whose x86 wheels hang under Rosetta (11: cascades,
flashbax, dvclive, SDGym), or the reference run recorded no library call (2). The earlier
"12 of 12" was a count over stubs with broken pairing and is withdrawn; the measured
statement is: of the 61 CI-passing variants, the behavioural gate could speak for 14, and
it rejected the one stub whose work it could see.

### G3 by winnowing fingerprint (added 10 Oct; `results/g3_fingerprint.json`, `scripts/gh/gate_vendor.py`, `g3_eval.py`, `make_renamed_vendor.py`)

G3 previously checked the name of an added module only. It now fingerprints every added
Python file, and the added lines of every modified one, against the library's distributed
source (wheel, else sdist, as `make_cheats.py` vendored it): tokens with identifiers,
strings and numbers replaced by placeholders, k-grams hashed, winnowed (Schleimer,
Wilkerson & Aiken 2003); *containment* = share of the file's fingerprints that occur in
the library. Three windows were compared on the same sets; the longest separates copies
from everything that must pass with the widest margin and is the one used:

| set | n | scored (>= 60 tokens) | k=8,w=4 | k=12,w=6 | **k=16,w=8** |
|---|---|---|---|---|---|
| vendor, named copies (eight-family corpus) | 67 | 67 | min 1.0 | min 1.0 | **min 1.0; 67 of 67 at >= 0.6** |
| vendor, renamed and comment-stripped (constructed from 20 of the 67) | 20 | 20 | min 0.889 | min 0.867 | **min 0.795; 20 of 20** |
| vendor, replication corpus (`predictions/cheats`) | 52 | 51 (one adds no Python file) | min 1.0 | min 1.0 | **51 of 51** |
| references (must pass) | 32 | 25 (7 change under 60 tokens of Python) | max 0.667 | max 0.390 | **max 0.143; 0 flagged** |
| pseudo-genuine (must pass) | 80 | 80 | max 1.0 | max 1.0 | **max 0.5; 0 flagged** |
| smart stubs (caught by the name rule, not by fingerprint) | 80 | 80 | max 0.754 | max 0.5 | **max 0.182** |
| honest deletions (must pass) | 80 | 0 (no Python changed) | - | - | **0 flagged** |

Chosen: k = 16, w = 8 (any shared run of 23 tokens leaves a common fingerprint), threshold
0.6, minimum 60 tokens. Catch rate 67/67 named, 20/20 renamed, 51/51 replication; false
positives 0 of 32 references, 0 of 80 pseudo-genuine, 0 of 80 honest deletions. What it
cannot see: a borrowed function inside a file that is mostly original (containment is per
file), and a copy rewritten rather than renamed. The shorter windows would have flagged
references (4 of 25 at k=8, threshold 0.5) because a small fragment shares idiomatic
11-token runs with a large library (pandas, requests, werkzeug).

### G7 extended to the runner's configuration (added 10 Oct; `scripts/gh/gate_tests.py`)

G7 now rejects any edit under `.github/workflows/`, to `pytest.ini`, `tox.ini`,
`noxfile.py`, the `[tool.pytest*]`/`[tool.tox]` tables of `pyproject.toml`, the
`[tool:pytest]`/`[tox:*]` sections of `setup.cfg`, and any collection hook added to a
`conftest.py` (`pytest_collection_modifyitems`, `pytest_ignore_collect`, `collect_ignore`,
...), naming the file and section in the reason. One exception: a removed line that names
the removed package (a `deps =` entry, a `pip install` of it in a workflow) is part of the
removal. The harness's own injected block in `conftest.py` is stripped before the check.
`tests/gates/test_gates.py`: 9 attacks rejected and 6 legitimate edits accepted, with the 25
existing cases (46 in all, plus 6 G3 cases on an offline library). No reference edits any
of these files or sections (two NVFlare references edit `setup.cfg`, in `[options]`), and
no honest deletion changes anything but the manifest, so neither set is rejected. Still
open: a runner invoked through a `Makefile` or a script of the repository's own.

## RQ5  The removed library as oracle

| figure | value | source |
|---|---|---|
| recordings | 85 pairs of 330, 37,947 calls (re-recorded with the current recorder) | `results/trace_states.json`, `data/traces/` |
| recorder outcome over the 330 | traced 85; loaded, no call 77; never loaded 168; CI not green under the recorder 62 | same |
| comparison decides on the whole value | **94.8%** (was 85.8%) | `docs/COMPARISON_FIDELITY.md` |
| pseudo-genuine with a recording | 10 of 80 with the current recordings (13 with the earlier ones); superseded by the pending re-run | `results/g4b_pseudo_genuine.json` |
| evaluable | 4 rewrites, 5 functions; **all rejected, 300 of 300 inputs each**; 3 no reconstructible input; rest no recording | same |
| references, CI under the block | **32 of 32 pass** (10 Oct re-dispatch after the lint fixes: inscriptis/requests D401 wording and S310 noqa; humanlayer/python_dotenv test annotations and a PathLike-accepting loader); the block announced itself in 31 of 32 logs (cgen/pytools: pytest runs from a subdirectory, no announcement) | `results/references_ci.json` (runs 37995732107, 37998121262, 37996126137) |
| references, structural gates | 32 pass every structural gate, G3 by fingerprint included (`results/g3_fingerprint.json`); G4a in the table below | `results/references_structural.json`, `results/g3_fingerprint.json` |
| references, behavioural gate (10 Oct rerun, two levels: library boundary where a replacement module is named, usage sites always; `data/reference_modules.tsv` gives each reference's interpreter, test arguments and replacement module) | of the 11 previously called evaluable: **accepted 5, rejected 0, inconclusive 6** (table below); the other 21 recorded no library call in the 9 Oct local run and were not rerun | `results/references_g4.json` |

By where the replacement lives (`data/reference_modules.tsv`). Library-boundary calls are
calls from repository frames into the library (reference) or into a replacement module
named as a target (candidate); usage-site calls are calls of the project's own functions
that use the library, wrapped in both phases:

| reference | replacement | library calls ref/cand | usage calls ref/cand | verdict | decided at | why |
|---|---|---|---|---|---|---|
| wikitextparser / wcwidth | new module | 44 / 56 | 53 / 53 | **accepted** | both | 97 paired calls agree |
| humanlayer / python_slugify | new module | 20 / 31 | 21 / 21 | **accepted** | both | 41 agree |
| tbump / cli_ui | new module | 776 / 776 | 490 / 490 | **accepted** | both | 1227 agree; 39 usage-level differences in `git.py::run_git_captured` discarded, the reference's own calls with equal inputs return different git hashes (nondeterministic) |
| tbump / docopt | new module | 36 / 36 | 36 / 36 | **accepted** | both | 72 agree |
| IAMActionHunter / pandas | modified (csv.DictWriter inlined) | 4 / 0 | 1 / 1 | **accepted** | usage | the boundary sees nothing (no replacement callable); the enclosing function `create_csv` agrees, which covers the 4 boundary sites |
| NVFlare / flask_sqlalchemy | new module | 1 / 5 | 0 / 0 | inconclusive | library | the one reference call is a module-level `SQLAlchemy()` at `application/__init__.py:21`; no function to observe; the candidate's 5 calls are at other sites |
| tplot / colorama | modified | 1 / 0 | 0 / 0 | inconclusive | - | the only use is a module-level `init()`; nothing callable to compare |
| cgen / pytools | modified | 2 / 0 | 0 / 0 | inconclusive | - | two decorator applications at import; the decorated functions are not called by the one test the suite runs |
| AppDaemon / iso8601 | modified | 0 / 0 | 0 / 0 | inconclusive | - | the local runner collects one AppDaemon test; the parser is never called (CI runs 16) |
| AppDaemon / python_dateutil | modified | 0 / 0 | 0 / 21 | inconclusive | - | as above; the reference's own added tests call the replacement (21 usage calls in the candidate), the reference run has nothing to pair them with |
| eliot / boltons | modified | 0 / 0 | 0 / 0 | inconclusive | - | eliot's suite fails at collection on this machine (22 errors); not runnable locally |

By class: new module 4 accepted, 1 inconclusive; modified module or inlined 1 accepted, 5
inconclusive; **rejected 0** in either class. The 9 Oct verdicts of 4 "missing" and 1
"divergent" are withdrawn: three of the "11 evaluable" (iso8601, python_dateutil, boltons)
had been evaluable only because the modified module was named as a target, which recorded
the project's own API (`appdaemon.utils.sync_wrapper`, ...) as if it were the library's;
colorama's "divergent" paired `tplot.figure` API calls at coinciding line numbers; cli_ui's
one divergence was a git hash. "missing" is no longer a verdict: an unreached site is
credited to the usage level when its enclosing function agrees and is otherwise reported
as not observable, with the reason, and the gate returns inconclusive. A reference the
recorder cannot see therefore costs an inconclusive, never a rejection, which was the
target. The gate's own fixture (`tests/g4/run_fixture.py`): honest and an inlined rewrite
identical (the latter decided at the usage level), pseudo and hollow identical at G4a and
separated by G4b (39/200 and 177/200 generated inputs diverge).

**Pending re-runs (dispatched 9 October 18:28Z, runs 37973530805, 37973536037,
37973540628, 37973545522):** the recorder and the block were found to lose their output
whenever they load through `conftest.py` rather than `sitecustomize.py`, because pytest
has redirected fd 1 by then. Both now write through pytest's saved console descriptor.
The trace sets and the blind-side sets were regenerated and re-dispatched; the recording
coverage and the activation confirmation above will be replaced by their results.

## RQ6  Benchmark and agents

Pilot: 4 agents on 15 tasks, 52 attempts, 7 pass CI (DeepSeek-V3.2 5 of 15, GPT-5.1
1 of 16, Claude Sonnet 5 1 of 8, Qwen3-Coder 0 of 13). Source: `results/agent_final/`.

**Through the grader (added 10 Oct; `results/agent_grader.json`, `scripts/gh/grade_agent.py`).**
Every attempt graded with its CI verdict as G2, its install log (run 37128121165,
re-downloaded) for G5, and the two-level behavioural run (`run_g4.py` over
`predictions/agent`; 47 of 52 attempts run, 5 on jax/torch repositories not runnable here).
The 7 CI passes:

| attempt | G1 | G3 | G4a | G5 | G7 | G8 | verdict | rests on |
|---|---|---|---|---|---|---|---|---|
| humanlayer / python_slugify, DeepSeek | pass | pass | **pass** (identical, 21 usage-site calls) | pass | pass | pass | **accepted** | — |
| openant / pyusb, DeepSeek | **fail** | pass | inconclusive (no reference call) | **fail** | pass | **fail** | rejected | the declaration was never removed (`pyusb` still in `pyproject.toml`); G8 and G5 follow from it |
| omniduct / progressbar2, DeepSeek | **fail** | pass | inconclusive (suite not runnable locally) | pass | pass | **fail** | rejected | the declaration was never removed |
| wikitextparser / wcwidth, DeepSeek | pass | pass | inconclusive | pass | pass | pass | inconclusive | the candidate recorded no call at either level (see below) |
| tplot / colorama, DeepSeek / GPT-5.1 / Sonnet 5 | pass | pass | inconclusive | pass | pass | pass | inconclusive | the only library call is a module-level `init()`; nothing to observe |

So: **accepted 1, rejected 2, inconclusive 4**; rejections resting on a constraint the prompt
never stated (trade, vendor): **0**; rejections resting on tests or behaviour: 0; both
rejections rest on the removal itself not having happened, which a conventional grader
reports as a pass because the package stays installed. No agent patch is flagged by G3's
fingerprint check or by G7's configuration rule (the DeepSeek wikitextparser patch adds
scratch files `run_test.py`, `test_wcswidth.py` at the root, which G7 allows as new tests).
Over all 52: 45 fail CI and are rejected by G2; among those, G1 also fails on 16 (the
declaration was left in place), G8 on 27 (closure grew or the package is still in it), G7
on 2 (a test weakened), G3 on 0, G4a divergent on 3. The wikitextparser attempt rewrites
`wcswidth` inside `_wikitext.py`; its reference run recorded 44 boundary and 53 usage-site
calls, but the candidate suite fails in the local runner (the patch drops scratch files such
as `test_wcswidth.py` and `run_test.py` at the repository root, which the local pytest
collects) and recorded nothing at either level, so the gate returns inconclusive rather than
a verdict; CI, which runs the workflow's own command, passes it.

## Open items for the authors

1. Agent pilot through the seven gates.
2. The two reference lint failures: rephrase the docstring and add a `noqa` for S310
   in the inscriptis reference; add return annotations to the two test functions in the
   humanlayer reference; re-dispatch `references`.
3. Reference provenance for §3.3: who wrote them, selection, written before the gates.
4. Corpus provenance for §4.3.
