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

| comparison | pairs | same verdict | flips |
|---|---|---|---|
| verified pairs, `all` vs `repeat` (regular) | 161 (same manifest change) | 161 fail/fail | **0** |
| verified pairs, `all_large` vs `repeat_large` | 169 (same manifest change) | 169 fail/fail | **0** |
| of which byte-identical, `requeue` vs `repeat` | 10 + 4 | 14 fail/fail | **0** |
| incidental, `scoped` vs `all` | 56 (byte-identical) | 2 pass/pass, 54 fail/fail | **0** |
| blind pairs, `all` vs `repeat_blind` (regular) | 53 | *pending* | |
| blind pairs, `all_large` vs `repeat_blind_large` | 186 | *pending* | |
| gold, regular, twice | 96 | *pending* | |
| gold, large, twice | 50 | *pending* | |

So far: 330 of 330 verified pairs are red again on a second execution, and
the 56 incidental pairs agree. The blind side and the gold side are the runs
still to land; the table is complete only when they do.

<!-- PENDING: runs 37892594154 (repeat_blind), 37892602364 (repeat_blind_large),
37892606428 (gold regular), 37892610569 (gold large). Fill with
flakiness.py --first <baseline> --second <repeat> --patches-* --ignore-injected
(blind: baseline res_all / res_all_large, patches predictions/all vs
predictions/repeat_blind*); gold: audit/results/gold_honest and res_gold_large*
vs the new gold runs, no patch check needed (gold patch is the dataset's). -->

## What a flip would mean

A pair whose blocked verdict flips is not a verified pair: its red was not
attributable to the dependency. The rule is that any pair that flips is
removed from the pool and the blindness rate is recomputed without it; the
number is reported with and without. A gold verdict that flips (green then
red with nothing removed) marks the repository itself as unstable and all its
pairs go with it.
