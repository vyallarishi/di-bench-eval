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

Two sources of paired runs:

1. **Purpose-built.** The full pool was re-screened with the current blocker
   as prediction sets `repeat` (161 regular) and `repeat_large` (169 large),
   dispatched after the canonical screening (`all`, `all_large`) that built the
   pool, with the same patches.
2. **Incidental.** The origin-scoped re-screen (`scoped`) and the canonical
   screening (`all`) share 56 pairs with byte-identical patches.

## Results

Incidental pairs, `scoped` vs `all`: 56 compared, 56 byte-identical,
2 pass/pass, 54 fail/fail, **0 flips**.

Purpose-built repeat: *pending — runs 37870222798 and 37870225599; fill from
`flakiness.py --first res_all --second res_repeat --patches-first
predictions/all --patches-second predictions/repeat` and the large pair.*

<!-- AFTER THE RUNS: replace the line above with the counts, name any
flipping instance, and state what happens to the pool and to the blindness
rate if every flipping pair is dropped. -->

## What a flip would mean

A pair whose blocked verdict flips is not a verified pair: its red was not
attributable to the dependency. The rule is that any pair that flips is
removed from the pool and the blindness rate is recomputed without it; the
number is reported with and without. A gold verdict that flips (green then
red with nothing removed) marks the repository itself as unstable and all its
pairs go with it.
