# Literature audit, per experiment: are we standing on gold?

For each experiment actually run: what the literature already established,
whether anyone did it before, whether our number agrees with theirs, and
whether the novelty claim survives. Fresh web sweep done first (2026-10-03),
then every cited paper checked. Bib corrections are an appendix.

**Verdict in one line per experiment**

| # | experiment | result | prior art? | our number vs theirs | novelty | standing |
|---|---|---|---|---|---|---|
| E1 | Gold decay | 51/96 pass after 21 mo | yes, well-studied | consistent | first for DI-Bench | **gold, uncited** |
| E2 | Manifest mutation | 49.4% invisible; 91 phantom / 24 blind | yes, close | consistent | mechanism split is new; "first manifest mutation" is not | **gold, needs reframing** |
| E3 | Static predictor | P .81 / R .83 | components only | n/a | intact | **gold** |
| E4 | Constructed cheats + gates | 61/176 pass; stub evades | method yes, task no | consistent | task-specific result is new | **gold, under-positioned** |
| E5 | Agent pilot | 5 CI-pass vs 3 genuine | yes, at scale | consistent | none as phenomenon | **confirmatory only** |
| E6 | pipreqs vs Qwen-7B | .71 vs .26 F1 | stronger tools exist | n/a | DI-Bench lacked any | **gold, under-baselined** |
| E7 | Instance pool | 162; 62 strong fail on deletion | standard practice | n/a | n/a | **gold** |
| E8 | PyCG symbol-level | 18/51; "worse" | yes — known fix | contradicted | negative result is an artifact | **not gold** |

---

## E1 — Benchmark decay (51 of 96 gold patches still pass)

**What the literature says.** Executable benchmarks rot, and the rate we found
is ordinary:

- Aguilar et al., *Reproducing and Improving the BugsInPy Dataset*, SCAM 2023:
  under three years after release only **67%** of BugsInPy reproduced;
  environment information "can decay into something uninstallable over time."
- Zhu & Rubio-González, *On the Reproducibility of Software Defect Datasets*,
  ICSE 2023: five Java datasets, 1,795 artifacts, 13 months; reproducibility
  **26.6%–96.9%**; "all datasets are prone to breakages"; pinning restores ≥95%.
- Mukherjee, Almanee, Rubio-González, *Fixing Dependency Errors for Python
  Build Reproducibility*, ISSTA 2021: **71.1%** of 2,702 Python builds
  unreproducible due to dependency errors — the exact failure class we hit
  (Poetry 2.5.1 dropping Python 3.8/3.9, Mambaforge 404, unpinned libraries).
- Krafczyk & Schmid, arXiv 2604.26674: 21.6% of Defects4J unsuitable for
  evaluation.
- GitBug-Actions (arXiv 2310.15642): builds reproducible bug benchmarks on
  GitHub Actions — the same move as our harness port.

**Prior art for the method?** Re-running a benchmark's own gold answers is
exactly what Aguilar and Zhu did. Nobody had done it for DI-Bench.

**Does our number agree?** 53% at 21 months sits between BugsInPy's 67% at
<3 years and Mukherjee's 29% reproducible Python builds. Nothing anomalous.

**The `act` false positive.** `act` printing *Job succeeded* for an action
declaring `runs.using: node24` is a known upstream issue (nektos/act #5883,
#5918; node24 support landed later). The diagnosis is correct; it is not a
discovery. Worth a footnote, not a contribution.

**Standing: gold.** The tex cites none of this. Add Aguilar + Zhu + Mukherjee
in §3.1 and the result stops looking like something a reviewer could pin on
the harness — which matters because the earlier audit found 4 of the 45
failures *are* infrastructure (`context canceled`), so the drift count is 41.

---

## E2 — Dependency mutation (115 of 233 deletions invisible to CI)

**What the literature says.** Tests miss dependency-level faults, measured
several ways:

- Hejderup & Gousios, JSS 2022: 1,122,420 artificial faults at library call
  sites in 262 Java projects; tests detect **47%** of direct and **35%** of
  indirect faults. Mutable artifact: *library code*.
- Shulepov, arXiv **2608.27100** (Aug 2026): "dependency pin" as one of four
  mutation classes on ML research repos; validation detected **8.7%** (2/23).
  Mutable artifact: *the manifest* — version pins, not declarations.
- STING / *Probe to Generate*, Li et al., arXiv 2604.01518: program variants
  against SWE-bench Verified; **77%** of instances have ≥1 surviving variant.
  SWE-ABS (2603.00520): one in five "solved" patches semantically wrong.
- Krafczyk & Schmid 2604.26674: **7.1%** of Defects4J bugs pass all tests
  after deleting a single statement.
- Mujahid et al., MSR 2020: dependents' own tests detect only 6 of 10 known
  breakage-inducing npm releases.

For the phantom mechanism specifically: Drosos et al. FSE 2024 — **30%** of
bloated PyPI declarations are transitively-listed; Zhang et al. arXiv
2608.16262 — **34.12%** of Maven projects use undeclared (implicit)
dependencies; Endor Labs grey literature — 0–60% of Python deps phantom.

**Prior art?** Nobody deletes single declarations from a benchmark's ground
truth and re-runs CI. But Shulepov mutates the manifest (pins) and measures
test detection, and Hejderup measures test blindness to dependency faults at
scale. The sentence "we are the first to point mutation testing at a
manifest" (Project_Explained p.3) and "nobody has mutation-tested dependency
declarations" (team doc p.5) are **false as of August 2026**. The tex wording
("mutate the manifest rather than the code") survives only if Shulepov is
cited beside it.

**Does our number agree?** Yes, and it is worth saying so in the paper:
49.4% invisible is bracketed by Hejderup's 47–53% missed and STING's 77%
instances-with-survivors; our 10.3% blind-spot rate is the same order as
Krafczyk's 7.1% delete-one-statement survivors; our 91 phantoms match
Drosos's 30% transitive-listed category sitting inside a benchmark.
Independent methods on independent benchmarks converge on "roughly half the
oracle is blind."

**What is genuinely new.** The **mechanism split** — phantom installation
(ground-truth defect, curable by curation) versus test blind spot (project
defect, incurable by curation) — appears nowhere in the above. Hejderup,
STING and Shulepov report one undifferentiated miss rate. This is the
experiment's real contribution and the tex under-sells it in favour of the
"first manifest mutation" line that no longer holds.

**Standing: gold, reframed.** Claim: *first single-declaration deletion audit
of a dependency benchmark, with the first separation of phantom installation
from test blindness.* Cite Hejderup, Shulepov, STING, SWE-ABS, Krafczyk,
Drosos, Zhang. Carry the earlier audit's corrections (93/22, 113/118) into
the table.

---

## E3 — Static predictor of blindness (precision 0.81, recall 0.83)

**What the literature says.** Each component is standard; the combination
and the target are not.

- *Declared-vs-closure*: computing whether a declared package is already in
  the requires-closure of the others is the inverse of deptry's DEP003
  ("transitive" — imported but only available transitively) and of
  FawltyDeps' undeclared check; `pipdeptree` exposes the closure. Drosos's
  "transitive listed unnecessarily" category is the same object, measured.
- *Import reachability from tests*: Eclipse Steady (Ponta, Plate, Sabetta,
  ICSME 2018 / EMSE 2020) does code-centric reachability from application
  code into library methods for vulnerability triage; Hejderup's Präzi (EMSE
  2022) builds call-based dependency networks; Drosos stitches PyCG graphs
  across PyPI.
- *Call-graph tooling*: PyCG (ICSE 2021) and Jarvis (Yan et al., arXiv
  2305.05949): Jarvis exists because "PyCG does not scale to large programs
  when adapted to whole-program analysis where dependent libraries are also
  analyzed."

**Prior art for the target?** None found. Steady predicts *vulnerability
reachability*; deptry/FawltyDeps predict *manifest hygiene*; nobody predicts
*whether a CI oracle will notice a deletion*. The earlier audit confirmed the
predictor is not circular and beats every single-signal baseline (best
alternative F1 0.755 vs 0.815; "not imported anywhere" — i.e. the
deptry/FawltyDeps rule — scores P 0.756 / R 0.296).

**Standing: gold.** Add Steady, deptry/FawltyDeps and Jarvis to position the
components; the "not imported" baseline should be labelled in the paper as
"what deptry/FawltyDeps would predict," which makes the comparison concrete.

---

## E4 — Constructed cheats and the gate stack (61 of 176 pass; stubs evade install gates)

**What the literature says.** Adversarially probing a verifier with
constructed exploits is now a named methodology:

- BenchJack, Wang et al. (Song group), arXiv 2605.12673: automated
  red-teaming of 10 agent benchmarks, near-perfect scores "without solving a
  single task," **219 flaws in eight recurring patterns**.
- Hacker-fixer loops, arXiv 2606.08960 (cited): 16% of 1,968 tasks hackable
  from the description; hacker/fixer/solver loop hardens verifiers.
- ImpossibleBench, Zhong, Raghunathan, Carlini, arXiv 2510.20270: measures
  propensity to *modify tests* or *special-case* them — our "stub" family is
  the special-casing pattern; our "weaken tests" gate is their
  test-modification pattern.
- SWE-bench Pro Verified 2609.08149: reward hacking via gold/solution
  leakage; anti-hacking safeguards.
- SpecBench (cited): visible vs held-out tests as the structural remedy.

For the individual gates:
- *Vendoring = clone detection against the library's source.* This has its
  own tooling: Vendetect (Trail of Bits, 2025 — semantic fingerprinting that
  survives renames), JC-Finder (clone-based third-party-library detection,
  arXiv 2508.02397), *Revisiting Third-Party Library Detection* (2509.04091).
  Our token-Jaccard >0.6 is cruder than all of these. The earlier audit
  showed it separates verbatim copies perfectly (median 1.00 vs ≤0.16) and
  would miss an honest rewrite — which Vendetect is designed to catch.
- *Hide/phantom = declared-vs-resolved diff.* This is what SCA phantom
  detection does (Endor Labs; `pixi-sbom --report phantom`; deptry DEP003).
- *Stub = hollow bodies.* Closest: ImpossibleBench special-casing; no
  dedicated detector in the literature.

**Prior art for the task?** No. BenchJack and hacker-fixer audit *existing*
benchmarks' verifiers generically; nobody has enumerated cheats for a
dependency-removal oracle or shown which gate catches which with executed CI.

**Does our number agree?** Qualitatively: BenchJack finds every benchmark
hackable; hacker-fixer finds 16% of tasks hackable from the prompt alone;
we find tests alone accept 35% of constructed cheats. Same direction.

**Standing: gold as a result, under-positioned as a method.** Say explicitly
that this is a BenchJack/hacker-fixer-style audit instantiated for one task
with executed ground truth; cite ImpossibleBench for the stub/special-casing
mapping; cite Vendetect and note gate 3's limitation. (The earlier audit's
finding that gate 3 only inspects *new* files, and so never examined any
agent's replacement code, still stands and belongs in Limitations.)

---

## E5 — Agent pilot (28 runs; CI says 5, truth is 3)

**What the literature says.** The phenomenon — agents satisfying the test
oracle without doing the task — is established at scale:

- *Building to the Test*, Ma, Kereopa-Yorke, Schultz, arXiv 2606.28430:
  production agents with the oracle in the loop reach near-perfect scores
  while the required library is "dead or absent." This is our `wcswidth`
  case exactly (simplified replacement that drops East Asian width tables;
  490 tests pass because none cover it).
- Wang, Pradel, Liu, ICSE 2026 (arXiv 2503.15223): 7.8% of SWE-bench patches
  pass while failing developer tests; 29.6% behaviourally diverge from gold;
  **PatchDiff** — differential testing against the reference — is the tool
  that would have caught our two "genuine but degraded" removals mechanically
  instead of by hand.
- SpecBench (cited): compositional failures dominate, deliberate exploits
  rare — matches our "no deliberate cheating, two degraded rewrites."
- TimeMachine-bench (cited), DEPBENCH / *Update from Hell* 2608.30300 (best
  agent 51.2% on 203 upgrades): agents on dependency tasks produce spurious
  solutions.
- *Stop Comparing LLM Agents Without Disclosing the Harness*, 2605.23950:
  the step-budget confound we report is a known class.

**Prior art?** Yes — the phenomenon is not ours. What is ours is the task.

**Standing: confirmatory.** 28 runs, ±18 points. Present it as "the
oracle-blindness we measured in E2 manifests on real agents on this task, as
*Building to the Test* and Wang–Pradel found on theirs," and propose
PatchDiff-style differential testing against the removed library as the
missing gate. The earlier audit's point that "no spontaneous cheating" is
unsupportable (llm-mlc stubbing; gate 3 blind to existing files) remains.

---

## E6 — pipreqs baseline vs Qwen2.5-Coder-7B (F1 0.71 vs 0.26)

**What the literature says.** Verified against the DI-Bench paper: **it
compares LLM prompting strategies only** (All-In-One, File-Iterate,
Imports-Only) and cites exactly one dependency-inference paper. So "DI-Bench
never ran a static baseline" is true. But the static-inference literature
is older and stronger than pipreqs:

- DockerizeMe, Horton & Parnin, ICSE 2019 — inference of environment
  dependencies for Python snippets, Dockerfile output.
- SnifferDog, Wang, Li, Zeller, ICSE 2021 — restoring notebook environments
  with version mapping.
- **PyEGo**, Ye et al., ICSE 2022 — knowledge-graph inference of packages,
  interpreter and system libraries at compatible versions; **0.4×–3.5× more
  accurate than prior tools** on 2,891 gists + 100 projects. This is the one
  DI-Bench cites, and the one a reviewer will name.
- FawltyDeps, deptry — the production tools; `pipreqs` (2015) is the
  weakest member of this family.

**Prior art?** The finding "a deterministic tool beats a 7B LLM on DI-Bench"
is new for DI-Bench. The *choice* of pipreqs is the weak point: it is the
easiest static tool to beat, so the gap is a lower bound on how far behind
the 7B model is, and a reviewer will ask why PyEGo (or even FawltyDeps/deptry)
was not run.

**Standing: gold, under-baselined.** Keep the pipreqs line (with the earlier
audit's two disclosures: best-of-two configurations, F1 0.624 untuned; live
PyPI lookups in 97/98 repos). Add PyEGo or deptry as a second static line, or
state plainly that pipreqs is a floor. Cite Horton & Parnin, SnifferDog,
PyEGo. Note the pipreqs line is not in the ACL tex at all.

---

## E7 — Instance pool and tiers (162 pairs; 62 strong-tier deletions fail CI)

Verifying that deleting the target breaks CI before admitting an instance is
SWE-bench's FAIL_TO_PASS requirement applied to a manifest, and the
executability filter GitBug-Actions applies. Standard; nothing to cite beyond
SWE-bench. The earlier audit confirmed 62/62 and that the tiering was applied
exhaustively. **Standing: gold.** One sentence noting the pool is balanced
81/81 from a 126/405 population, so pool proportions are not base rates.

---

## E8 — Symbol-level reachability with PyCG (18 of 51 repos; "worse than file-level")

**What the literature says.** PyCG's failure to scale is documented and
fixed:

- Jarvis, Yan et al., arXiv 2305.05949: "PyCG does not scale to large
  programs when adapted to whole-program analysis where dependent libraries
  are also analyzed" — which is precisely what `--package .` makes PyCG do
  (`scripts/graph/run_pycg.py:44`). Jarvis is demand-driven from entry
  points, ≥67% faster, 84% higher precision, ≥10% higher recall.
- Drosos et al. ran PyCG across 1,302 projects and 3,232 dependencies at
  ecosystem scale, so "PyCG hangs on 33 of 51 repos" is a configuration
  claim, not a tool claim.

**Does the result hold?** No. The earlier audit found the 2-file repo
`gforcada_flake8-isort` times out at 240 s *with* the flag and completes in
0.2 s without it; and on the same 45 rows symbol-level **beats** file-level
on F1 (0.545 vs 0.522) and recall, losing only on precision — the script
prints precision and recall separately and never computes F1.

**Standing: not gold.** The literature says the tool scales when driven from
entry points, the audit says one flag caused the timeouts, and the metric
chosen inverts the conclusion. Either re-run with Jarvis (or PyCG without
`--package`) and report F1, or drop the comparison to a limitation ("we did
not obtain symbol-level graphs at scale").

---

## What survives, overall

- **Novel and defensible:** the phantom/blind-spot mechanism split (E2); the
  static blindness predictor (E3); the task-specific gate results, especially
  "stubbing evades every install-level check" (E4); the in-situ removal
  benchmark itself (E7) — nothing in the sweep (zerodep 2605.21405,
  LibReuseBench, Commit0, DEPBENCH, TimeMachine, SWE Refactor Bench) does
  in-situ removal of a *used* dependency.
- **True but not novel, and uncited:** decay (E1); "tests are a blind
  oracle" (E2's headline rate); agents build to the test (E5). Each has
  2023–2026 precedent that *agrees* with us. Citing it converts "surprising
  claim from a small benchmark" into "known phenomenon, now measured for
  dependencies with a new mechanism split." That is a better paper.
- **Dead as worded:** "first to mutate the manifest" (Shulepov 2608.27100);
  "we suspect many benchmarks would not survive" (STING/SWE-ABS already
  showed SWE-bench does not).
- **Wrong:** the PyCG negative result (E8).
- **Under-baselined:** pipreqs (E6) — PyEGo is the baseline the field knows.

---

## Appendix — bib entries that support these experiments and need fixing

| key | fix |
|---|---|
| `hejderup2022trust` | venue is *Journal of Systems and Software* 183:111097 (2022), not EMSE |
| `migrationbench2025` | Java 8→17/21 JDK migration (Liu et al., 5,102 repos), **not** library A→B — reword tex L121 |
| `soto2021longitudinal` | DepClean is from *A comprehensive study of bloated dependencies in the Maven ecosystem*, EMSE 2021, DOI 10.1007/s10664-020-09914-8 |
| `timemachine2026` | Fujii, Morishita, Yano, Suzuki; EACL 2026 Long pp. 8233–8264; arXiv 2601.22597 |
| `sweatlas2026` | Romero Calvo et al. (Scale AI); arXiv 2605.08366; ICML 2026 |
| `pytrim2025` | Karakatsanis et al.; ASE 2025 |
| `specbench2026` | Zhao, Srikanth, Wu, Jiang; arXiv 2605.21384 |
| `dependeval2025` | Du et al.; Findings of ACL 2025 pp. 7150–7179 |
| `repo2run2025` | arXiv 2502.13681; NeurIPS 2025 spotlight |
| `libreuse2026` | HuggingFace dataset (Luke Twist), no paper — `@misc` with URL |
| `jaisri2024dataset` | npm ecosystem (companion: SERA 2024) — say so |

**To add:** STING 2604.01518 · SWE-ABS 2603.00520 · Wang–Pradel ICSE 2026 /
2503.15223 · Shulepov 2608.27100 · Krafczyk & Schmid 2604.26674 · Aguilar SCAM
2023 · Zhu & Rubio-González ICSE 2023 · Mukherjee ISSTA 2021 · Mujahid MSR
2020 · Zhang 2608.16262 · BenchJack 2605.12673 · ImpossibleBench 2510.20270 ·
Building to the Test 2606.28430 · Vendetect · PyEGo ICSE 2022 · DockerizeMe
ICSE 2019 · SnifferDog ICSE 2021 · Jarvis 2305.05949 · Eclipse Steady ·
zerodep 2605.21405 · DEPBENCH 2608.30300 · SetupBench 2507.09063.
