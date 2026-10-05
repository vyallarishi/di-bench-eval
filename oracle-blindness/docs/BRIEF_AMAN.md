# Brief: Aman — close the verifiability gap

An independent adversarial audit of our benchmark (`docs/BENCHMARK_AUDIT_REPORT.md` — read §7 first) checked five of the six promises the benchmark makes and passed them exhaustively. It could not verify the sixth, and that one is the only opening a reviewer has:

> **Winnability.** Read 36 pairs; *executed* 5. The promise "an agent could edit the repository so that CI passes" is **unverified for 227 of the 232**. Given that my 36-pair sample surfaced two unwinnable pairs and several very hard ones — all from test-suite coupling that no current rule detects — I expect further unwinnable pairs remain in the pool.

Your job is to close that gap. Not to analyse it — to close it.

**There is only one thing that closes it: a removal that was actually written and actually passed.** Every other route (better static rules, more log forensics, cleverer heuristics) produces more *evidence about* winnability, and a reviewer can always answer evidence with "but did you try?". A committed patch that passes the repository's own CI with the dependency unimportable cannot be argued with. So this brief is mostly labour, and that is deliberate.

**Repository: `https://github.com/vyallarishi/DependencyRefactoring`**

```bash
git clone https://github.com/vyallarishi/DependencyRefactoring.git
cd DependencyRefactoring
```

You and a parallel session (Rishi is running one from `docs/REFERENCE_SOLUTIONS_PROMPT.md`) are both writing reference removals. **Claim your pairs first** (Task 0) so you don't duplicate work.

---

## Task 0: claim your pairs (do this before anything else)

Create `references/CLAIMS.md` with a line per pair you intend to do: `<instance_id> / <dependency> — aman — in progress`. Commit and push it immediately, then update as you go. Check it before starting a pair in case the other session claimed it.

Take pairs from the **bottom** of the lists below; the other session is instructed to work from the top.

## Task 1: the tractable 61 — prove the easy case is really easy

`benchmark/instances.jsonl` (or `data/pool_2026-10-05/instances_preview.jsonl` if the rebuild hasn't landed) has **61 regular pairs where the package is imported in exactly one source file and no test imports it**. The audit wrote 5 removals of this shape and all 5 passed, so this population is believed winnable — but "believed" is the word a reviewer attacks.

Do as many as you can, in this order of value: **a pair that turns out NOT to be winnable is worth more than ten that are**, because it must come out of the pool.

Method per pair, and follow it exactly — the audit found that skipping the verification step is how people fool themselves:

```python
import sys, pathlib; sys.path.insert(0, 'code/harness')
from make_blocked import write_blocker, import_names, own_packages
repo = pathlib.Path('.cache/repo-data/python/<instance_id>')
write_blocker(repo, '<dep>', import_names('<dep>'), own_packages(repo))
```

1. **Before editing anything**, run the repository's test suite with the blocker installed. It **must fail**. If it passes, the blocker never loaded — stop, and record the pair under "blocker did not load" in your report, because that is a finding about the harness, not about the pair. (This really happens: `tournesol` runs its suite from a subdirectory, so the blocker at the repo root was never imported and 130 tests passed with the package installed.)
2. Remove the declaration from the manifest. Remove the code's use of the package.
3. Run the suite again. It must pass, **without** you having touched a test: no deleted test, no added `skip`/`xfail`, no loosened assertion, no narrowed parametrisation. If the only way through is to change a test, the pair is **unwinnable** — report it, don't fix it.
4. No new third-party package (stdlib and already-declared packages are fine), and no pasting the library's source in. A small purpose-built replacement for what the repo actually used is exactly right.

Output per solved pair, in `references/<instance_id>__block__<dep>/`:
- `patch.diff` — manifest edit + code changes, as a git diff against the repo checkout; **exclude** `sitecustomize.py` and `conftest.py` (the harness injects those)
- `NOTES.md` — what the package did, what replaced it, files changed, the exact command you ran, and the final test summary line pasted verbatim

## Task 2: the risk population — 53 pairs where the repository's own tests import D

This is where the audit expects the remaining unwinnable pairs, and it is the higher-value half of your work even though you'll solve fewer.

Filter the pool for pairs with a non-empty `test_files`. For each, you do **not** have to write the removal — you have to **decide and document** whether a removal is possible without weakening the suite, by reading the tests:

| Pattern you find in the tests | Verdict |
|---|---|
| Tests import D only as a helper (fixture data, a formatter for output) | likely winnable — say what the replacement would be |
| Tests construct D's objects and pass them to our code | hard — the test would need the replacement type; judge and argue it |
| Tests patch `D.something` by dotted path (`mock.patch("D.X")`) | likely unwinnable — the test names D as the thing under test |
| Tests assert on D's own exception types or error messages | unwinnable — correctness is defined in terms of D |
| Tests shell out to D as a tool (`python -m D`) | unwinnable — no code edit changes it |

Write this up as `references/TEST_COUPLING.md`: one row per pair with the pattern, the file:line you based it on, and a verdict of **winnable / hard / unwinnable**. For every **unwinnable**, that pair must leave the pool, so be specific enough that someone can act on it without redoing your reading.

The audit already judged `jazzband_django-revproxy / urllib3` and `mu-editor_mu / virtualenv` unwinnable on these grounds, and flagged `tweepy / requests_oauthlib`, `aws_chalice / click`, `python-socketio / python_engineio`, `m-burst / flake8_plugin_utils` as at-best-very-hard. Start with those six: confirm or overturn each. **Overturning one is a real result** — say so plainly if the audit was wrong.

## Task 3: make the risk machine-detectable

Once you've read ~20 pairs in Task 2 you'll know the patterns better than any of us. Write `code/harness/test_coupling.py`:

```python
def check(repo: pathlib.Path, dep: str, test_files: list[str]) -> dict:
    """Return {"risk": "low"|"hard"|"unwinnable", "signals": [...], "evidence": [...]}."""
```

Detect, by parsing the test files: imports of D, `mock.patch` targets whose dotted path starts with D, `pytest.raises(D.SomeError)`, subprocess/`python -m` invocations of D, and D's types in fixture signatures or annotations. Return the file:line evidence for each signal.

This is what lets the paper say the risk is *measured over the whole pool* rather than sampled — which is precisely the gap the audit identified. Validate it against your own Task 2 verdicts and report where it disagrees with you; **your reading wins**, and a disagreement means the detector needs work, not that your verdict was wrong.

## Task 4 (only if Tasks 1–3 are done): the other verification holes

Smaller gaps the audit named, in descending value:

- **176 candidates were never screened at all** (§L1). The claim "every dropped candidate is listed with a reason" isn't true yet. Check whether the rebuild covers them (`python code/harness/missing.py --set all --results results/all`) and report what's still missing.
- **94 pairs' mutant patches weren't verifiable** because the patches weren't in the audited checkout (§6). Confirm each removes exactly one declaration and nothing else.
- **Two blocker leaks** (§L5): `object.__getattribute__(mod, "_real")` reaches through the guard, and `pkgutil.iter_modules()` still lists the module. Neither happens by accident, but an adaptive agent could use them. Propose fixes.

---

## What to hand back

`references/SUMMARY_AMAN.md`:

- Pairs attempted / solved / unwinnable / blocked-did-not-load, with the full table
- **The unwinnable list, front and centre** — this is the deliverable that most improves the benchmark
- Where `test_coupling.py` disagrees with your reading
- How long a typical removal took you, split by tier. The paper needs this: it's the evidence that the task is non-trivial but feasible, and right now we have a sample of five.

## Ground rules

- **Do not modify** `benchmark/instances.jsonl`, `code/harness/build_pool.py`, `code/harness/make_blocked.py`, or existing files under `results/`. Report problems; don't fix the pool yourself, because measurements are being built on it right now.
- New files anywhere are fine. `code/harness/test_coupling.py` is yours.
- Commit and push after **every** pair, even an unfinished one. Partial work that's pushed is worth more than complete work that isn't.
- If a pair defeats you for a reason that isn't "unwinnable" — environment won't build, tests need a database, suite takes an hour — record it as **abandoned, with the reason**. That's honest and useful. Don't let it sit silently.
- Where you're unsure, write the uncertainty down. "I think this is winnable but the mock patching worries me" is useful. A confident wrong verdict that puts an unwinnable pair in a published benchmark is the thing we are trying to prevent.
