# Session brief: write reference solutions for the removal benchmark

You are writing the **ground truth** for a benchmark. For each assigned (repository, dependency) pair you must actually remove the dependency: edit the repository so it no longer needs the package, and get the repository's own test suite passing with the package made unimportable. Your output is a patch per pair plus a short note. These patches are what every other measurement in the paper is calibrated against, so a patch that only appears to work is worse than no patch at all.

## The task, precisely

**Repository: `https://github.com/vyallarishi/DependencyRefactoring`**

```bash
git clone https://github.com/vyallarishi/DependencyRefactoring.git
cd DependencyRefactoring
```

The benchmark pool is `benchmark/instances.jsonl` (built by `code/harness/build_pool.py --canonical`; if it does not exist yet, use the snapshot `data/pool_2026-10-05/instances_preview.jsonl` and say which you used). Each row is one pair:

```
instance_id        the repository, checked out at .cache/repo-data/python/<instance_id>
dependency         the package D to remove
build_file         the manifest that declares D
tier               indirect / strong / medium / hard, by how many non-test files import D
source_files       the files that import D, with the import statements and use counts
test_files         which of those are tests
mutant_id          <instance_id>__block__<dep>, the screening mutant
```

For a pair to be *solved*, all of the following must hold:

1. **D's declaration is gone** from `build_file`. Nothing else in the manifest changes.
2. **The repository does not import D anywhere** — not in source, not in tests, not in config, not through an entry point or a plugin hook.
3. **The test suite passes** with D unimportable from the repository's own frames (the mechanism below). You run this locally; the full CI replay happens later.
4. **No test was weakened.** You may not delete a test, skip it, loosen an assertion, mark it `xfail`, or narrow its parametrisation. If a test exists only to test D-specific behaviour and genuinely cannot survive the removal, stop and record the pair as *unwinnable* with that reason — do not fix it by editing the test.
5. **No new third-party package.** You may not swap D for another PyPI package. Standard library, code you write yourself, and packages the manifest *already* declares are all fine.
6. **No vendored copy.** You may not paste D's source into the repository. Writing a small, purpose-built replacement for the one thing the repository actually used is exactly what is wanted; copying D's implementation is not. If the honest replacement would be more than ~150 lines, that is a signal the pair belongs in a harder tier — note it.
7. **Behaviour is preserved** on everything the repository exercises. If D did real work (parsing, formatting, numerics), your replacement must produce the same results, not merely satisfy the assertions that happen to exist.

## How to run the tests with D blocked

`code/harness/make_blocked.py` generates the blocker; read `BLOCKER` in that file to understand it. Blocking is origin-scoped: imports from the repository's own code and tests are refused, imports from third-party packages still work. To set it up for one pair:

```python
import sys, pathlib; sys.path.insert(0, 'code/harness')
from make_blocked import write_blocker, import_names, own_packages
repo = pathlib.Path('.cache/repo-data/python/<instance_id>')
write_blocker(repo, '<dependency>', import_names('<dependency>'), own_packages(repo))
```

That writes `sitecustomize.py` and `conftest.py` into the repository. Then install the project's dependencies **minus D** and run its tests the way its CI does (read `ci_file` in the dataset row — `.cache/dataset-dibench-regular.jsonl` or `-large.jsonl` — to see the real commands). Use a venv or a container per repository; do not install these projects into your system Python. Expect an `ImportError` mentioning `blocked: dependency <D> was removed` for any import you missed — that message is your check that the blocker is actually live, so confirm you can produce it *before* you start editing.

**Verify the blocker is working before trusting a pass.** A test suite that passes because the blocker never loaded is the main way this task goes wrong. Check: with the unmodified repository and the blocker installed, the suite must *fail*. If it passes, the blocker is not loading (wrong rootdir, `sitecustomize` shadowed, tests run in a subprocess with a different interpreter) — fix that first and say what you did.

## What to produce, per pair

Write into `references/<mutant_id>/`:

- `patch.diff` — the complete solution as a git diff against the repository's state at `.cache/repo-data/python/<instance_id>`, **including** the manifest edit, **excluding** the blocker files (`sitecustomize.py`, `conftest.py` additions) since the harness injects those itself.
- `NOTES.md` — what D was used for; what you replaced it with and why; every file you changed; the exact command you ran and its result (paste the final test summary line); anything that worried you.

Pairs you could not solve go in `references/UNWINNABLE.md`: pair, the specific blocker (a test asserts on D's own API; D is a build backend; D is required by a declared sibling so it stays installed; the repository's CI installs it regardless), and what evidence you have. **An honest unwinnable finding is a valuable result, not a failure** — it means the pool must drop that pair, and the benchmark gets more trustworthy. Do not stretch a solution to avoid reporting one.

## Coordinating with the parallel session

A second person (Aman, following `docs/BRIEF_AMAN.md`) is writing reference removals at the same
time. Before starting, read `references/CLAIMS.md` and append a line per pair you intend to do:
`<instance_id> / <dependency> — <you> — in progress`. Commit and push that immediately.

**Work from the top of each list; the other session works from the bottom.** Check CLAIMS.md
before each pair.

## Which pairs, and how many

Work in this order:

1. **Every pair in `benchmark/agent_instances_16.jsonl`** if it still exists and its pairs are in the pool — these are the ones agents were evaluated on, so references here directly measure false rejection.
2. **A stratified sample across tiers and both subsets**: aim for 10 `strong`, 10 `medium`, 10 `hard`, 10 `indirect`. `indirect` pairs (D is never imported directly) are the most interesting and the most likely to be unwinnable — do not skip them because they are awkward.

Pick within each tier by whatever is fastest to set up; record the selection rule you used so the sample is reproducible. If you run short of time, finish fewer pairs completely rather than many partially. Report the count.

## Reporting

Finish with `references/SUMMARY.md`:

- Pairs attempted, solved, unwinnable, abandoned-for-time.
- A table: pair, tier, lines changed, files changed, what replaced D, test result.
- For solved pairs, the distribution of effort — this is the paper's evidence that the task is non-trivial but feasible.
- Every unwinnable pair with its reason, as a list the pool owner can act on directly.
- Anything you learned about the blocker, the harness, or the pool labels that looks wrong. Label disagreements matter: if `source_files` missed a file that imports D, or the tier looks wrong given what you had to change, say so with the pair id.

Commit as you go (one commit per few pairs is fine) so nothing is lost. Do not modify `pilot/instances.jsonl`, `code/harness/*`, or anything under `results/` — report problems instead of fixing them, since changing the pool mid-audit invalidates the measurements built on it.
