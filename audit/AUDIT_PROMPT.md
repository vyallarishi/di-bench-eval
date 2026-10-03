# Adversarial audit request

Paste everything below into a fresh session, working directory
`/Users/rishivyalla/Downloads/DI-Bench`.

---

I need you to adversarially audit a set of empirical claims from a research
project. **Your job is to try to break them, not confirm them.** A previous
session produced both the analysis code and the conclusions, so there is a real
risk it wrote code that produced the answer it expected. Assume that happened
somewhere and find it.

Do not trust any summary, report, or markdown file in this repository. Treat
`reports/*.md` and the PDFs as *claims to be checked*, not evidence. Go back to
the raw per-instance JSON and CI logs every time.

## Ground rules

1. **Re-derive, do not re-run.** Write your own independent code to compute each
   number from the raw artifacts. Do not import or call the original scripts to
   verify the original scripts. If your number disagrees with the claim, work
   out which is right and say so plainly.
2. **No money, no network-heavy work.** Do not call paid APIs, do not launch
   GitHub Actions runs, do not run coding agents. Everything you need is already
   on disk. Read-only web lookups to check a cited paper are fine.
3. **Report negative results.** If a claim survives your attack, say it survives
   and show what you tried. If you cannot check something with what is on disk,
   say that explicitly rather than guessing.
4. **Look for the specific failure mode of motivated reasoning**: filters that
   quietly drop inconvenient cases, classifiers whose default branch happens to
   favour the hypothesis, denominators that changed between claims, samples
   conditioned in a way that manufactures the effect.

## Where everything is

| Path | What it holds |
|---|---|
| `audit/results/gold_honest/` | 96 instances, DI-Bench's own correct answers re-run. Each has `eval-result.json` and `eval-workspace/exec-output.log` |
| `audit/results/gold_raw/`, `audit/results/gold_rerun_*/` | the unmerged originals, before any exclusion |
| `audit/results/mutation_merged/` | 531 deletion mutants with full CI logs |
| `audit/results/cheats/` | 176 constructed fake removals with CI logs |
| `audit/results/agent/` | 28 agent attempts with CI logs |
| `audit/results/static_analysis/` | per-dependency static analysis output |
| `audit/results/phantom_pred.json` | static phantom predictions |
| `audit/results/degenerate_gold.json` | instances excluded as degenerate |
| `audit/scripts/`, `scripts/gh/`, `scripts/graph/`, `pilot/` | the original analysis code — read it critically |
| `.cache/dataset-dibench-regular.jsonl` | the benchmark dataset, including each instance's official correct patch |
| `.cache/repo-data/python/` | the 98 repositories themselves |

A result file looks like `{"instance_id": ..., "exec": "pass"|"fail"|"error", ...}`.
Mutant ids are `<repo>__del__<package>`; cheat ids are `<repo>__<kind>__<package>`
where kind is `stub`, `vendor` or `hide`; agent ids contain `__agent-<model>__`.

Use `/private/tmp/.../scratchpad` for any temporary files.

## Claim 1 — DI-Bench has decayed

**Claimed:** Only **51 of 96** of DI-Bench's own official correct answers still
pass CI, roughly 21 months after release. The failures are blamed on external
drift (an installer dropping old Python versions, a discontinued download,
unpinned libraries releasing breaking versions) rather than on anything the
previous session did wrong.

**Attack it:**

- Recount pass/fail/error directly from `gold_honest`. Does it give 51/96?
- Two instances were excluded as "degenerate" (`degenerate_gold.json`). Read
  their logs in `gold_raw`. Was excluding them justified, or did it move the
  number in a convenient direction? What is the result if you include them?
- Open the logs of all 45 failures yourself and classify the cause
  independently. **Is "external drift" actually true, or are some failures
  caused by the harness being misconfigured?** This is the most important
  question in Claim 1. Specifically check: did any fail because of a missing
  secret, a network timeout, a disk-space problem, a container issue, or the
  sysbox setup — i.e. things that are the experimenters' fault, not drift?
- The harness was modified from upstream (see `dibench/utils/docker.py` and
  `dibench/utils/ci.py` in git history). Could any modification cause failures
  that would not happen on the original harness?
- The claim that `act` reports "Job succeeded" for jobs that never ran: verify
  this is real by finding such a log, and check whether the fix might now be
  *over*-rejecting legitimate passes.

## Claim 2 — Half of dependencies are invisible to the tests

**Claimed:** Deleting one declared dependency and re-running CI goes unnoticed
for **115 of 233** mutants (49.4%) on gold-passing instances. Of those, **91 are
phantoms** (package installed anyway) and **24 are blind spots** (package truly
absent, tests still pass). Sanity check claimed: for 114 of 118 visible
deletions the package was genuinely absent.

**Attack it:**

- Recount from `mutation_merged`. Watch the denominators: 531 total vs 233
  conditioned on gold-passing. Is the conditioning legitimate or does it inflate
  the rate? Report both.
- **The phantom/blind-spot split is the weakest link.** It comes from
  `installed_anyway()` in `scripts/gh/mechanism.py`, which regex-matches package
  names in CI install logs. Read that function adversarially:
  - Can a package name match something unrelated (substring collisions,
    normalisation of `-`/`_`/`.`, case)?
  - If the log is missing or empty, which way does it default, and does that
    default favour the hypothesis?
  - Does it distinguish "installed as a dependency of something else" from
    "installed because a test runner config listed it"? Should it?
  - Write your own classifier from scratch and compare case by case. How many
    of the 91 and the 24 do you disagree with?
- Hand-verify at least 10 of the 24 claimed blind spots by reading the CI log:
  is the package really absent, and do the tests really pass? These 24 carry a
  lot of argumentative weight, so check them properly.
- Were the mutants generated correctly? `scripts/gh/prepare.py` builds them.
  Confirm each deletes exactly one dependency and changes nothing else, by
  applying a sample of mutant patches yourself and diffing the manifests.
- Did any mutant accidentally delete a dependency that was never there?

## Claim 3 — Blindness is predictable statically

**Claimed:** A package-list check (is the package in the requirement closure of
the *other* declared packages, from PyPI metadata) plus an import-reachability
check together predict CI-invisible deletions at **precision 0.81, recall 0.83**.
Package-list alone: 0.97 / 0.62.

**Attack it:**

- Recompute precision and recall yourself from `phantom_pred.json`,
  `static_analysis/`, and the mutation outcomes. Check the confusion matrix by
  hand.
- A precision of 0.97 is suspiciously high. Is it circular? Does the predictor
  have any access, directly or indirectly, to the executed outcome it is
  predicting?
- Check the import-name mapping (`import_names_for` in
  `audit/scripts/analyze_python.py`). It maps package names to import names with
  a hand-written table plus heuristics like stripping a leading `py`. Could
  those heuristics create false matches that help the result?
- What is the baseline? If you always predicted "invisible", what precision
  would you get? Is 0.81 actually better than trivial strategies?

## Claim 4 — Tests accept a third of constructed fakes

**Claimed:** Of 176 constructed fake removals, **61 (34.7%) pass CI**. Hide: 35
of 62 pass, all caught by other checks. Vendor: 18 of 52 pass, all caught. Stub:
8 of 62 pass, **none** caught by install-level checks.

**Attack it:**

- Recount from `cheats/`.
- **Are the fakes actually faithful?** Read `pilot/make_cheats.py`. A stub that
  is trivially broken would fail CI for the wrong reason, and a vendor variant
  that fails to copy properly is not really testing vendoring. Inspect several
  patches of each kind and judge whether they genuinely implement the cheat.
- The "caught" claims come from `pilot/gates.py`. Read it adversarially:
  - The vendor detector uses token-similarity against the library's real source.
    What threshold, and would it fire on an honest rewrite?
  - The stub detector looks for trivial function bodies and shadow packages.
    Would it false-positive on legitimate small helper functions?
  - Verify "0 of 8 stubs caught by install-level gates" by checking those 8 logs
    yourself.
- Is 62/52/62 an unbiased denominator? 10 vendor variants were skipped for
  compiled packages. Does skipping them bias the vendor result?

## Claim 5 — The agent score overstates success

**Claimed:** Across 28 agent runs, CI reports **5 passes** but only **3** are
genuine removals; the other 2 failed other gates. No spontaneous cheating was
observed.

**Attack it:**

- Recount from `agent/` and `gates_agent.json`.
- For each of the 5 CI passes, read the patch and the log and judge for yourself
  whether it is a genuine removal. Do you agree with 3?
- For the 2 rejected: are they genuinely not removals, or were they rejected by
  an overly strict check?
- "No cheating observed" is a negative claim. Look through all 28 patches
  yourself for anything resembling vendoring, stubbing, or test tampering. The
  previous session's detector may be too narrow.
- One run reportedly wrote a "simplified replacement" for a Unicode width
  function. Find it and judge whether that should count as a cheat.

## Also worth attacking, if you have budget left

- **Pipreqs baseline** (claimed P/R/F1 0.65/0.78/0.71 beating a 7B model's
  0.30/0.23/0.26). Re-score from `audit/scripts/score_pipreqs.py` inputs. Is the
  comparison fair — same instances, same matching rules, same normalisation?
- **Benchmark instance pool** (`pilot/instances.jsonl`, claimed 162 pairs in
  three tiers). Verify the tier definitions are applied consistently and that
  "strong tier deletion provably fails CI" is actually true for all 62.
- **Symbol-level reachability** (claimed PyCG covered only 18 of 51 repos and
  scored *worse* than file-level). This one is claimed as a negative result, so
  check whether it was given a fair chance or hobbled by configuration.

## What I want back

A written report with one section per claim containing:

1. The claimed number, and the number you independently derived.
2. **Verdict: CONFIRMED / CONFIRMED WITH CAVEATS / OVERSTATED / WRONG.**
3. The specific attacks you tried and what each showed.
4. Any bug, bias, or questionable choice you found in the analysis code, with
   the file and line.
5. If a number changes, the corrected number and what it does to the argument.

End with an overall judgement: **which of these findings would survive peer
review, and which would not.** Be blunt. I would much rather find a problem now
than after submission.
