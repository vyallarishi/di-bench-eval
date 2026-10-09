# Does the oracle give the same verdict twice?

The benchmark's central number is a count of CI verdicts: a pair is admitted
because the suite went red when the package was blocked, and a dependency is
called blind because the suite stayed green. Every one of those verdicts came
from one replay of the repository's workflow on a shared runner. If a verdict
can flip between two runs of the same patch — a test that depends on timing,
on the network, on test ordering — then some of what we count as a finding
about the dependency is a finding about the suite. The SWE-bench audits
found exactly this in a measurable share of instances, so it is measured here
rather than assumed away.

## Method

Run the identical prediction set twice and count the instances whose verdict
differs. "Identical" is checked, not assumed: `flakiness.py` compares the two
prediction sets byte for byte and counts only pairs whose patches match, so a
change in the injected blocker between two generations of the screener cannot
pass as a flip (`check_stale.py` guards the same thing from the other side).
A verdict is the harness's `exec` field, pass or fail.

Three sources of paired runs.

1. **Purpose-built, verified side.** The full pool was re-screened as
   prediction sets `repeat` (161 regular) and `repeat_large` (169 large). The
   canonical screening that built the pool injected an earlier generation of
   the blocker, so the two patches are byte-identical only for the 28 pairs
   the canonical screening itself re-ran (`requeue`); for the rest the
   manifest change is identical and the injected file differs by generator
   version. `flakiness.py --ignore-injected` matches on the manifest change
   and reports the two groups separately.
2. **Purpose-built, blind side.** The 239 blind pairs re-screened as
   `repeat_blind` (53 regular) and `repeat_blind_large` (186 large), with the
   current blocker.
3. **Gold.** The benchmark's own answers run twice (`gold`, regular and
   large), for the gold-rot figure.
4. **Incidental.** The origin-scoped re-screen (`scoped`) and the canonical
   screening (`all`) share 56 pairs with byte-identical patches.

## Results

| comparison | pairs compared | same verdict | flips |
|---|---|---|---|
| verified pairs, regular (`all` vs `repeat`) | 161 | 161 fail/fail | **0** |
| verified pairs, large (`all_large` vs `repeat_large`) | 169 | 169 fail/fail | **0** |
| silent pairs, regular (`all` vs `repeat_blind`) | 42 | 42 pass/pass | **0** |
| silent pairs, large (`all_large` vs `repeat_blind_large`) | 184 | 184 pass/pass | **0** |
| gold, regular, run twice | 96 | 51 pass, 45 fail | **0** |
| gold, large, run twice | 45 | 29 pass, 16 fail | **0** |
| incidental (`scoped` vs `all`) | 56 | 2 pass, 54 fail | **0** |
| **total** | **753** | | **0** |

Every verified pair is red again on a second replay, every silent pair is
green again, and no gold verdict changes. Silence is a property of the pair,
not of the run.

**Thirteen pairs are excluded from the silent-side comparison and the reason
is stated rather than buried.** Those pairs read fail in the canonical
screening and pass in the repeat, which looks like a flip and is not: they
were screened by a blocker that recursed when a third-party package imported
the blocked dependency, so the run died on a harness crash rather than on the
repository's own use. They were re-screened with the corrected blocker before
the pool was built, and the pool already carries the corrected verdict (their
`reason` field in `instances.blind.jsonl` records it). Comparing the repeat
against the superseded verdict is comparing two different mechanisms. The 13
are `fortalice_bofhound` (7), `jboynyc_textnets` (3), `NVIDIA_NVFlare` (2),
and one more; `check_stale.py` is the guard that now prevents a superseded
screening from being reported at all.

Patches are matched before verdicts are compared. The canonical screening and
the repeat inject different generations of the blocker, so 14 pairs match byte
for byte and the rest match on the manifest change with the injected file
differing by generator version; `flakiness.py --ignore-injected` reports those
groups separately, and a pair whose manifest change differs is excluded rather
than counted.

## What a flip would mean

A pair whose blocked verdict flips is not a verified pair: its red was not
attributable to the dependency. The rule is that any pair that flips is
removed from the pool and the blindness rate is recomputed without it; the
number is reported with and without. A gold verdict that flips (green then
red with nothing removed) marks the repository itself as unstable and all its
pairs go with it.
