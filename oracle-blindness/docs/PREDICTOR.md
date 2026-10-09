# The static predictor, re-measured

An earlier experiment asked whether CI-invisible deletions could be predicted
without running anything, and reported precision 0.81 / recall 0.83 for two
static signals combined. That number was measured against the *first* screening,
which deleted declarations without blocking imports. The benchmark no longer
works that way, so the claim was re-measured against the canonical screening.

**It does not reproduce, and the reason is substantive rather than a defect.**

## What the numbers are now

Evaluated on the 214 pairs where both the old predictions and the canonical
screening are available (53 of them invisible):

| Predictor | Predicted | Precision | Recall | F1 |
|---|---|---|---|---|
| Dependency layer | 76 | 0.34 | 0.49 | 0.40 |
| Code layer | 63 | **0.65** | **0.77** | **0.71** |
| Both (disjunction) | 113 | 0.42 | 0.89 | 0.57 |

Previously claimed: dependency 0.97/0.62, code 0.69/0.42, combined 0.81/0.83.

The two layers have swapped places. The code layer is now the stronger of the
two and roughly matches its old recall; the dependency layer has collapsed.

## Why the dependency layer collapsed

It predicts *phantoms*: a package that stays installed because another
dependency requires it, so deleting the declaration changes nothing and CI
notices nothing. Against the original screening that was exactly right.

The canonical screening also makes the package **unimportable from the
repository's own code**. Under that regime a phantom is no longer invisible:
the package may well still be installed, but the project cannot reach it, so
CI fails like any other removal.

The measurement bears this out. Of the 76 pairs the dependency layer calls
phantom, **50 were noticed by CI anyway** and only 26 stayed silent. The layer
is predicting a failure mode the new screening is designed to eliminate.

So the collapse is evidence the import blocking works, not evidence the
predictor was wrong. It was answering a question we stopped asking.

## What this means for the paper

The combined 0.81/0.83 claim is withdrawn. What can be said instead:

- **Test reachability alone predicts blindness at 0.65 precision / 0.77 recall**,
  from import statements only, with no container and no test run. That is a
  usable signal for curating instances and for flagging scores that deserve
  suspicion.
- **Dependency-closure membership no longer predicts invisibility**, because
  blocking the import removes the mechanism it detects. Reporting this is more
  interesting than the original claim: it is a direct measurement of what the
  blocking changes.

The honest framing is one layer, one number, and an explanation of why the
second layer stopped working.
