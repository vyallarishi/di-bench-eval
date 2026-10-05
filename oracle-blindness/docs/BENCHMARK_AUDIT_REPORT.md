# Benchmark Audit Report

*Independent adversarial audit of the removal benchmark in `oracle-blindness/data/pool_2026-10-05/`.
Auditor was not involved in construction. Every number, label and rule was treated as a claim to be tested.*

**Audited artifact:** `instances_preview.jsonl` (277 pairs, 73 repositories), `excluded.jsonl` (402 candidates),
builder `scripts/gh/build_pool.py`, blocker `scripts/gh/make_blocked.py`, features `scripts/gh/footprint.py`,
manifests `scripts/gh/manifests.py`.

**Evidence base.** All 12 result artifacts were downloaded from `vyallarishi/di-bench-eval`
(1,572 result records over 1,260 distinct instance ids, ~1 GB of CI logs). **All 277 pool pairs
have a CI log and all were re-derived from the raw log by machine.** Winnability was sampled
(36 pairs read; 5 removals actually written and executed). The blocker was attacked with 15
constructed bypasses in a purpose-built repository.

**Bottom line.** The benchmark's core machinery is sound: gold passes everywhere, the manifest
editor is correct on 1,121 real removals, static features reproduce exactly, and the scoped
blocker resists 13 of 15 attacks. The defects are in the **shipped pool file**, not the design:
it was built in legacy mixed mode, 35 pairs still carry a verdict from the blocker the project
itself documents as unsound, 11 pairs must be removed, and 43 wrongly-excluded pairs should be
admitted. The pool is also stale — it predates results that have since landed.

---

## 1. Pairs that must be removed (11)

| instance_id | dependency | subset/tier | Why |
|---|---|---|---|
| `swirlai_swirl-search` | `blis` | large/indirect | **Scoped re-screen PASSES** (run 37372621768); pool kept the broad `fail`. Block was raised by `thinc` in site-packages. |
| `swirlai_swirl-search` | `cymem` | large/indirect | Same: scoped = pass, broad = fail. |
| `swirlai_swirl-search` | `murmurhash` | large/indirect | Same: scoped = pass, broad = fail. |
| `swirlai_swirl-search` | `preshed` | large/indirect | Only attributing frame is `thinc/backends/numpy_ops.pyx` — a **Cython frame from site-packages** that `frame_origin()` reads as repo-code. Foreign-origin ⇒ unwinnable. |
| `rwth-i6_returnn` | `typing` | large/indirect | `typing` is **stdlib** since 3.5. 183 repo files import it. Blocking it severs the stdlib module; no edit can win. |
| `swirlai_swirl-search` | `statistics` | large/indirect | `statistics` is a **stdlib** module name. Same defect. |
| `mu-editor_mu` | `click` | large/indirect | CI fails at `from click import _unicodefun` **inside `black`** (`site-packages/black/__init__.py:1358`). A foreign tool broken by the guard, not repo use of click. |
| `mu-editor_mu` | `flake8` | large/indirect | Fails at `python: No module named flake8` — invoking the flake8 *tool* from the Makefile. Tooling failure, not repo use. |
| `mu-editor_mu` | `virtualenv` | large/indirect | `test_create_virtual_environment_on_disk` creates a **real venv on disk** via `python -m virtualenv` (unmocked, `tests/virtual_environment/test_virtual_environment.py:161-169`). No code edit passes it. |
| `geopy_geopy` | `geographiclib` | large/strong | **`patch.diff` contains no manifest edit** — only `conftest.py` and `sitecustomize.py`. The declaration was never removed, so the pair does not implement the benchmark's own task. |
| `jazzband_django-revproxy` | `urllib3` | regular/strong | The test suite's mock infrastructure is *built from* `urllib3.HTTPResponse` / `HTTPHeaderDict` (`tests/utils.py:3,23,31`) and patches `urllib3.PoolManager.urlopen`. Tests define correctness in terms of D. |

**Also quarantine, pending re-screen: 35 pairs** whose verdict rests **only** on the broad
(unscoped) blocker — never re-screened scoped. The project's own `GRADER_DESIGN.md` says the
broad blocker over-counts and that scoping "is not a refinement, it is a correctness requirement."
Three of the four pairs that *were* re-screened flipped `fail → pass`, so this population is known
to contain false positives. I re-checked all 35 by frame origin: 34 show genuine repo-origin
frames and will very likely survive; **`aws_chalice/click` shows zero block messages** and is
labelled `blocked_import_in_repo_frame` on a log that contains no block at all (its real,
sound evidence is a pylint `E0401` — i.e. the label is wrong even though the pair is good).

---

## 2. Rules that are wrong

**R1 — `frame_origin()` misreads Cython/extension frames as repository code.**
`build_pool.py:107-114` detects foreignness by the substring `site-packages/`. Cython tracebacks
emit the *build-relative* path: `thinc/backends/numpy_ops.pyx:1: in init thinc.backends.numpy_ops`.
Verified counterexample — this string classifies as `repo-code`. This is the exact mechanism that
put `swirl/preshed` (and the blis/cymem/murmurhash family) into the pool. Machine sweep: 5 `.pyx`
frames and 1 `<string>` frame are counted as repo-origin across the pool; 1 pair
(`swirl/preshed`) is attributed **solely** by such a frame.

**R2 — `names_of()` splits on `_` and matches the wrong module.**
`build_pool.py:149-154` adds every underscore-separated token. Machine-checked: **47 of the 206
distinct pool dependencies gain spurious tokens** — `flask_sqlalchemy → {flask, sqlalchemy}`,
`requests_oauthlib → {requests, oauthlib}`, `python_dateutil → {python}`, `zope_interface → {zope, interface}`.
A `No module named 'flask'` would therefore "verify" the removal of `flask_sqlalchemy`.
**22 pool pairs are admitted by the `missing_module_in_repo_frame` rule while carrying such a token.**
I inspected their logs and found no pair where the wrong token is what actually matched — so this is
a latent defect, not (yet) a realised mislabel. It must still be fixed: the rule is one unlucky log away
from admitting a wrong pair, and it is not defensible as written.

**R3 — `test_failure_without_import_error` is a catch-all default, and it admits construction artifacts.**
`build_pool.py:198` returns this evidence for *any* CI failure that matched none of the earlier
patterns. Hand-read all 18 such pool pairs: 3 are `mu-editor` tool failures (removed above); the
7 `bepasty` pairs are genuine but are only admitted *because no rule matched* — their real failure
(`AttributeError: module 'xstatic.pkg' has no attribute 'pygments'`) occurs in
`.tox/.../site-packages/bepasty/...`, which `frame_origin()` calls **foreign**. They are right for
the wrong reason. The remaining 8 are genuine. The rule's name also overstates: `mu-editor/virtualenv`
and `mu-editor/flake8` failed in **Makefile lint/coverage steps**, not tests.

**R4 — `LINT_STEP` is over-broad.** `build_pool.py:146` matches the bare token `check`, so steps
named "Run checks", "Check links" or "Run PRCheck" are treated as linter steps. In practice this
caused no bad admission (all 7 `linter_step_failed` pairs name the real package in a repo file —
verified individually), but the guard is wrong in principle. By contrast `INSTALL_STEP` (line 145)
with its `test|tox|nox|pytest` guard behaves correctly on all 26 realistic step names I tested.

**R5 — `import_names()` is missing distribution→module mappings, causing wrong exclusions** (see §4).

**R6 — stdlib-shadowing distributions are not detected.** `footprint.py:95` drops any import whose
root is in `sys.stdlib_module_names`, so a distribution named `typing` or `statistics` gets
`footprint_files = 0` *and* its 183 real import sites are invisible. Both such pairs in the pool are
unwinnable and both are mislabelled `tier=indirect`.

---

## 3. Labels that are wrong

- **`tier` / `footprint_files` wrong for 2 pairs** — `rwth-i6_returnn/typing` (recorded 0 source files;
  actually 183) and `swirlai_swirl-search/statistics` (recorded 0; actually 2). Cause: R6.
- **`evidence` wrong for 1 pair** — `aws_chalice/click` is `blocked_import_in_repo_frame` on a log
  with **zero** block messages; the true evidence is `linter_step_failed`.
- **`verified_by` is misleading for 94 pairs.** They are labelled `deletion`, meaning they were
  screened *without* the blocker. A deletion-only failure proves the package was uninstalled by the
  manifest edit — a different and weaker condition than the blocked screening. The pool is not a
  single-mechanism benchmark, though `build_pool.py`'s docstring describes one.
- **`phantom_predicted` is `null` for 144 of 277 pairs (52%)** — a documented field absent for the
  majority of the pool.
- **Labels that are right:** tier is consistent with `tier_of()` on **all 277** rows (0 errors), and
  recomputing `footprint_files`, `test_reachable`, `attribute_uses` and `test_files` from scratch on
  a random 30 pairs reproduced the stored values **exactly** (0 mismatches).

---

## 4. Exclusions that were wrong

**E1 — 43 pairs were excluded as "undetermined" but are now admissible (the pool is stale).**
107 candidates were parked awaiting the scoped re-screen. Those results **have since landed**:
44 now have a scoped `fail`, and re-running the project's own `classify()` admits **43** of them
(17 `blocked_import_in_repo_frame`, 25 `test_failure_without_import_error`, 1 `missing_module_in_repo_frame`).
Examples: `docker_docker-py/urllib3`, `aws_chalice/jmespath`, `instadeepai_flashbax/jax`,
`jupyter_jupyter_console/prompt_toolkit`, `python-adaptive_adaptive/sortedcontainers`.
A further 29 still have no scoped result and 34 now pass (correctly excluded).

**E2 — 3 of 5 "removal exposed an undeclared sibling dependency" exclusions are wrong.**
The "sibling" is the *same package's own import name*, which `import_names()` does not know:

| Excluded pair | Reported "sibling" | Reality |
|---|---|---|
| `kcroker_dpsprep/fpdf2` | `fpdf` | `fpdf2` **ships the `fpdf` module**. Fails at `dpsprep/text.py:8` (repo code). Should be admitted. |
| `kcroker_dpsprep/djvulibre_python` | `djvu` | `djvulibre-python` **ships `djvu`**. Fails at `dpsprep/images.py:3` (repo code). Should be admitted. |
| `pystorm_streamparse/fabric39` | `fabric` | `fabric39` **ships `fabric`**. Fails at `streamparse/bootstrap/__init__.py:10` (repo code). Should be admitted. |
| `codypiersall_pynng/cffi` | `_cffi_backend` | `_cffi_backend` is cffi's own C extension. Arguably admissible; the repo frame is `pynng/__init__.py:3`. |
| `python-adaptive_adaptive/scipy` | `numpy` | **Correctly excluded** — numpy really is a different package. |

**E3 — "blind spot: CI passes" (257) conflates two different things, and at least 1 is a false blind spot.**
The blocker **never fired** in any of the 257 logs. For 115 screened by deletion that is expected
(the phantom-install result). But 142 were screened *under blocking*, and 23 of those have a
non-zero repo footprint reachable from tests — i.e. the blocker should have fired.
Root cause found for `tournesol-app_tournesol/numpy`: **CI runs in a subdirectory**
(`workdir=solidago`, `rootdir: /project/solidago`), so the blocker written to the repository root is
never imported. numpy is installed, imported, and 130 tests pass. That is a **blocker-installation
failure, not an oracle blind spot**, and it inflates the headline blindness number. The other 22
are plausible genuine blind spots but each needs the same check.

**E4 — exclusions that are right.** I read ≥5 examples of every reason string. "install step failed" (12),
"unwinnable or framework-loaded" (17), "construction artifact" (1, `google_mobly/pywin32` — black
reformatting the injected file, exactly as the blocker's header comment anticipates) and
"lint failure that does not name the package" (1) all check out. The 17 framework-loaded exclusions
are genuinely foreign-origin; `GRADER_DESIGN.md` already states this over-excludes Django/pytest-plugin
cases, which my reading confirms as a real but *conservative* loss.

---

## 5. Weaknesses that must be stated as limitations

**L1 — The pool is not a census of its candidate universe.** `pilot/all.jsonl` + `pilot/all_large.jsonl`
list 622 candidates; pool + excluded account for 679 rows but **176 candidates (148 regular, 28 large)
were never screened at all**. "Every candidate pair that was dropped is listed in excluded.jsonl" is
therefore not true as stated — a large block was never screened rather than dropped.

**L2 — Two screening mechanisms are mixed.** 183 blocked + 94 deletion. The paper must not describe
this file as a single uniform screening; `build_pool.py --canonical` exists but was not used for it.

**L3 — Winnability is systematically threatened by test-suite coupling.** Across a 36-pair stratified
sample (both subsets, all four tiers), the dominant obstacle is not code difficulty but that the
repository's **own tests import D**. Where the tests construct D's objects or patch `D.x` by dotted
path, "remove D and keep CI green" silently requires rewriting the tests that define correctness.
I judge at least `django-revproxy/urllib3` and `mu-editor/virtualenv` unwinnable on these grounds;
several more (`tweepy/requests_oauthlib`, `aws_chalice/click`, `python-socketio/python_engineio`,
`m-burst/flake8_plugin_utils`) are at best very hard and should be tiered or flagged.
*Note:* "a sibling still installs D" does **not** make a pair unwinnable under the scoped blocker —
I verified for `torchode/sympy`, `SDGym/tqdm`, `skforecast/{numpy,tqdm}` and
`namedivider-python/numpy` that the blocked import is raised from a repository frame, so
installation is irrelevant. A naive reading of transitive requirements over-calls unwinnability here.

**L4 — Non-import runtime dependencies are invisible to the static features.** `nbmake/ipykernel`
(needs a `python3` kernelspec) and `mu-editor/virtualenv` (shells out to `python -m virtualenv`)
have zero import sites, so any import-count difficulty heuristic rates them trivial while they are
in fact near-impossible. `tier=indirect` is doing dangerous work here.

**L5 — Blocker leaks (deliberate escape only).** Of 15 attacks, 13 are blocked, including
`importlib.import_module` with a runtime-built name, `exec`/`eval` strings, `subprocess python -c`,
`multiprocessing` spawn children, `del sys.modules` + re-import, and `importlib.reload`. Two leak:
`object.__getattribute__(mod, "_real")` reaches through the `_Guard`, and `pkgutil.iter_modules()`
still lists the module. Neither is reachable by accident, but both should be documented since the
grader will face an adaptive agent.

**L6 — Blocker installation is not guaranteed.** The blocker is written only to the repository root.
When CI runs in a subdirectory (tournesol) it never loads, and the run is silently recorded as a
pass. Every "blind spot" must be corroborated by evidence the blocker was actually active.

**L7 — `_is_repo_file` resolves paths literally.** On a platform where the checkout path is a symlink
(e.g. macOS `/tmp` → `/private/tmp`), `_ROOT` and `os.path.abspath(frame)` disagree and **every
repository frame is classified foreign, disabling the block entirely**. I hit this while testing and
had to move the fixture off the symlinked path. CI on Linux is unaffected, but local reproduction
will silently produce wrong results.

**L8 — One screening run is the oracle.** No pair in the pool was screened twice *within* the same
mechanism, so intra-mechanism flakiness is unmeasured by construction (see §6 for what *is* measured).

---

## 6. Things that checked out

| Check | Scope | Result |
|---|---|---|
| **Gold passes** (promise #1) | **all 73 pool repositories**, across 5 gold runs + 4 local result dirs | **73/73 pass, 0 conflicts, 0 failures.** Fully verified. |
| **Evidence re-derivation** | **all 277 pairs**, re-derived from raw logs | **273/277 agree** with the stored label. The 4 disagreements are §1 findings. |
| **Reproducibility / flakiness** | 312 instance ids with >1 result | **0 verdicts differ within a screening family.** The 3 observed flips are broad→scoped, i.e. a mechanism change, not flakiness. |
| **Manifest editing** | `test_manifests.py --full`: 145 instances, **1,121 real dependencies** | 1,121 clean removals, **0 incorrect**, 0 declined. Poetry groups, extras, markers, setup.py, setup.cfg, requirements all pass. |
| **Manifest patch scope** | **all 183 blocked-screened pool patches** | 182 edit exactly one manifest and nothing else; 1 (`geopy`) edits none (§1). 0 patches touch >1 manifest. The 94 deletion patches are not in this checkout and were **not** verified. |
| **Static features** | 30 random pairs recomputed from scratch | **0 mismatches** on `footprint_files`, `test_reachable`, `attribute_uses`, `test_files`. |
| **Tier consistency** | **all 277 rows** | **0 deviations** from `tier_of()`. |
| **Import-name mapping** | **all 206 distinct pool dependencies** | No implausible mapping. Only 2 misses, both stdlib-shadowing (§2 R6). |
| **Blocker robustness** | 15 constructed bypasses | **13 blocked**, 2 deliberate-escape leaks (§L5). |
| **`own_packages()`** | all 73 pool repositories | **0 collisions** between a repo's own top-level names and a removed dependency. 1 repo returns empty (`tournesol`). |
| **Platform-marker no-ops** | all 277 pairs | **0 pairs** whose dependency is excluded from Linux by an environment marker. |
| **Documented numbers** | README + memory note | All reproduce **exactly**: gold 51/96; deletions 115/233 = 49.4%; cheats 61/176 = 34.7%; `instances.jsonl` 162 pairs/47 repos; result-dir counts 96/531/176/52; pool "277 over 73"; "107 undetermined". |
| **Winnability, demonstrated** | 5 removals written and executed under the scoped blocker | All 5 pass — see below. |

**Removals I actually wrote and ran** (declaration removed, scoped blocker active, dependency
confirmed unimportable from repository frames):

1. `csachs_pyproject-flake8 / tomli` — switched to stdlib `tomllib`. Repo's own command
   (`unittest discover -s test`): **2 tests, OK**.
2. `miguelgrinberg_python-socketio / bidict` — wrote a ~25-line bidirectional dict
   (incl. the `_fwdm`/`_invm` internals the repo actually uses). **68 tests pass**
   (`test_manager.py`, `test_pubsub_manager.py`); `import bidict` raises the block.
3. `martenlienen_torchode / sympy` — the symbolic derivation returns a constant 3×7 matrix;
   computed it once and inlined it. Weights **match the sympy result exactly**; sympy blocked.
4. `airbnb_omniduct / sqlparse` — wrote quote/comment-aware `split()` and `format()`.
   Correct on semicolons inside string literals and on comment stripping; sqlparse blocked.
5. `google-research_cascades / openai` — replaced `openai.Completion.create` with a ~20-line
   `urllib.request` shim; openai blocked. CI has no API key, so the network path is never exercised.

---

## 7. The number I stand behind

**232 pairs.**

That is 277 − 11 removed (§1) − 34 further quarantined as broad-only (§1; the 35th, `swirl/preshed`,
is already in the removal list), and it does **not** yet include
the 43 pairs that should be admitted from "undetermined" (§4 E1) or the 3 wrongly excluded for a
phantom sibling (§4 E2). A corrected rebuild would plausibly land near **278** — a similar total to
today's, but not the same set.

**"Verified" for those 232 means, precisely:**

- *Checked for 100% of them, by machine, against the raw CI logs:* the repository's gold manifest
  passes CI in this harness; the screening run recorded `fail`; the first error, the frame that
  raised it and the failing step were independently re-derived from the log and agree with the
  stored `evidence`; the failure is attributed to a frame that is not in `site-packages`; the
  declared tier matches `tier_of(footprint_files)`.
- *Checked for 100% of the 183 blocked-screened pairs:* the mutant patch removes exactly one
  declaration from exactly one manifest and changes nothing else but the injected blocker files.
- *Checked for 100% of the 73 repositories:* gold passes, with no verdict conflict across repeated runs.

**What I could only sample, and what therefore is not covered by that word:**

- **Winnability.** Read 36 pairs; *executed* 5. The promise "an agent could edit the repository so
  that CI passes" is **unverified for 227 of the 232**. Given that my 36-pair sample surfaced two
  unwinnable pairs and several very hard ones — all from test-suite coupling that no current rule
  detects — I expect further unwinnable pairs remain in the pool. This is the benchmark's largest
  open risk and must not be reported as verified.
- **Manifest-patch correctness for the 94 deletion-screened pairs** (patches absent from this checkout).
- **Blocker activation.** Verified by construction for all 183 blocked patches, but verified to have
  actually *fired at run time* only where a block message appears in the log. The tournesol case
  proves silent non-activation is real.
- **Behavioural correctness of any removal.** Out of scope here; that is what `GRADER_DESIGN.md`'s
  G4 is for, and it is not yet built.

I do **not** report this benchmark as 100% verified. The parts of the promise I verified exhaustively
are gold-passing, removal-detection attribution, label consistency and manifest-edit scope. The part
I could not — winnability — is the one a reviewer is most likely to attack, and the one where I
already found counterexamples.
