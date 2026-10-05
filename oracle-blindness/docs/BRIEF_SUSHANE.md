# Brief: Sushane — land G7/G8 and run your predictors on our data

Your test-weakening and closure-growth work becomes two gates in the paper's grader, and your predictor needs scoring against our execution results. Four tasks, in priority order. Nothing here collides with what anyone else is doing.

**Repository: `https://github.com/vyallarishi/DependencyRefactoring`** — this is the paper's repo, newly created. Everything for the paper lives here now; the old `di-bench-eval` repo is only the CI runner and you can ignore it.

```bash
git clone https://github.com/vyallarishi/DependencyRefactoring.git
cd DependencyRefactoring
```

Push directly to `main` or open a PR, either is fine — but **push something**, because right now none of your code is in any repo, and we are citing numbers from it (the 79-of-80 test-weakening result) that we cannot regenerate. That is the single biggest risk in your part of the paper.

Layout you'll need:

```
code/harness/        the screening and grading code (build_pool.py, make_blocked.py, ...)
benchmark/           instance lists (instances.jsonl, cheats.jsonl, ...) and gates.py
benchmark/patches/   the actual patches, one dir per set: cheats/ agent/ all/ ...
results/             per-instance CI results
data/                pool snapshots and static-analysis inputs
docs/                this brief, the grader design, the audit report
```

---

## Task 1 (most important): push your G7 and G8 code as it stands

Do not clean it up first. Push it working-as-is, then we refine.

Put it in `code/harness/` as two modules with this shape, so it drops into the existing grader without a rewrite:

```python
# code/harness/gate_tests.py          (G7: test oracle untouched)
def check(patch_text: str, repo: pathlib.Path) -> dict:
    """Return {"pass": bool, "reason": str, "evidence": {...}}."""

# code/harness/gate_closure.py        (G8: closure not grown)
def check(patch_text: str, repo: pathlib.Path, dep: str,
          before: set[str] | None = None, after: set[str] | None = None) -> dict:
    """Same return shape. `before`/`after` are resolved package sets when the
    caller has them; otherwise resolve them yourself and say how."""
```

**G7 — test oracle untouched.** Fail the patch if it weakens the suite: a test function deleted, a `skip`/`xfail` marker added, an assertion removed, a parametrisation narrowed, a test file deleted. Your finding that this *cannot* be caught structurally (skipping a test doesn't change the import graph) is exactly why the gate must read the test diff — put that sentence in the docstring, it's the reason the gate exists.

Edge case that matters: an agent legitimately *adding* a new test must not fail the gate. Only weakening counts. There's a rough version in `benchmark/gates.py` (search `weakened`) that counts removed-vs-added assertions; if yours is better, replace it and say what it does differently.

**G8 — closure not grown.** Fail the patch if a new third-party package appears in the resolved dependency set, or if the resolved set is not a subset of the original minus D. "Swap `requests` for `httpx`" must fail. Packages already declared in the manifest are fine. Be explicit in the docstring about how you resolve (pip dry-run, `requires_dist`, lock file), because that choice is a limitation we have to state in the paper.

**Validation to include:** run both against your 597 variants, and commit the per-family caught/missed table as `results/sushane_gates.md`. If G7 reproduces your 79-of-80, say so — that number goes in the paper and must be regenerable from committed code.

---

## Task 2: run your predictor against our real execution results

Your `score_predictors.py` was scored on your own data. We now have CI-replay ground truth for hundreds of (repository, dependency) pairs, which is a much stronger test of the same predictor.

Data in `data/pool_2026-10-05/`:
- `instances_preview.jsonl` — pairs where removal *is* detected by CI
- `excluded.jsonl` — candidates dropped, with the reason
- a `.blind.jsonl` of pairs where **CI passed although the dependency was gone** — the true blind spots, and the most interesting prediction target

One caveat you need, from the audit in `docs/BENCHMARK_AUDIT_REPORT.md`: some recorded "blind spots" are **not** blind spots — in at least one case (`tournesol`) CI runs in a subdirectory, so our import blocker never loaded and the suite passed for an unrelated reason. The blocker now announces itself in the log and such runs are reclassified "inconclusive". **Use the regenerated files if they're present; if you work from the snapshot, exclude any pair whose reason mentions "inconclusive".**

Produce `results/predictor_scores.md`: precision, recall, F1 for "will CI notice this removal", broken down by the `tier` field, with the confusion matrix and a list of the pairs it gets wrong. **The misses are worth more than the score** — a systematic miss is a finding for the paper, not a failure.

---

## Task 3: run your cheat classifier over our cheats and agent patches

We have 176 constructed cheats (62 hide, 62 stub, 52 vendor) in `benchmark/patches/cheats/python/<id>/patch.diff` with CI results in `results/cheats/`, plus 52 real agent patches in `benchmark/patches/agent/python/` with results in `results/agent_final/`.

Run your classifier over both. Output `results/cheat_classification.md`: how it labels each family, and specifically **which of the 52 agent patches it flags**. If it flags an agent patch that CI passed, we need to know — that's a candidate "an agent cheated and CI didn't notice", which is a headline result if it holds up.

---

## Task 4 (if time): your smart-stub family as a gate test set

Your pseudo-genuine stubs are the acceptance test for the behavioural gate (G4) being built now — by your own result they're the family *no structural signal* catches. Package them as patches in the same layout, `benchmark/patches/pseudo/python/<iid>__pseudo__<dep>/patch.diff`, with a `benchmark/pseudo.jsonl` whose rows match the format in `benchmark/cheats.jsonl`. Then they can run through the full grader and the claim "G4 catches what nothing else can" gets measured instead of asserted.

---

## Ground rules

- **Don't modify** `benchmark/instances.jsonl`, `code/harness/build_pool.py`, `code/harness/make_blocked.py`, or existing files under `results/`. Those are changing right now and we'd conflict.
- New files anywhere are fine. New results go in new files.
- If a number you previously reported doesn't reproduce from committed code, say so in the commit message. A number we can't regenerate can't go in the paper.
- Worth skimming first: `docs/GRADER_DESIGN.md` for where G7/G8 sit among the eight gates, and `docs/BENCHMARK_AUDIT_REPORT.md` for what an independent audit already found wrong (it's blunt, and useful).
- Commit messages: say what the code decides, not what you did.
