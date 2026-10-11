# Does the gate accept correct removals it has never seen?

The counterfeit study shows the behavioural gate rejects every fake it can
observe: 38 of 38 adjudicated, none accepted. On its own that is consistent
with a degenerate gate that rejects everything not byte-identical, and the
only evidence against that reading was five hand-written references the gate
had been **tuned on** — after four changes made while grading those same
references, having initially rejected 7 of 11.

A gate with no demonstrated positive class is a rejector. This is the control
that tests for one, on inputs that could not have been tuned for because
nobody wrote them.

## The construction

Re-point a repository's imports at a thin module of its own that forwards
every call to the library:

```python
"""Forwarding shim for wcwidth: every call reaches the library."""
import wcwidth as _lib

wcswidth = getattr(_lib, 'wcswidth', None)
```

The declaration leaves the manifest, the call sites change, a new module
appears — the submission has the shape of a removal. And the behaviour is
*provably* identical, because the same function object executes: verified by
object identity, not by comparing outputs. The gate **must** accept it, and
any rejection is a false rejection on an input generated mechanically from the
observable subset.

**Stated plainly, because the write-up has to:** this is a *degenerate*
removal. The library is still installed and still does the work. It does not
test whether a replacement is correct; it tests whether the gate's notion of
behavioural equivalence is sound. It is a control, not a task, and it stands
beside human-written references rather than replacing them.

## What this control can and cannot be run through

**It is not a pipeline must-accept, and the first version of this document
wrongly implied it was.** A forwarding shim imports the library from
repository code, and gate 2 is the scoped import block: repository code
importing the removed package fails. So under the full pipeline every control
is rejected at G2, correctly — the package is still being imported, which is
what G2 exists to detect.

That was verified rather than assumed. A shim built exactly as this script
emits one, run under the block:

```
ImportError: No module named 'wcwidth' (blocked: dependency wcwidth was removed)
```

Two consequences. First, the result below is **scoped to G1, G3, G4a, G7 and
G8** — the gates that judge the *form* of a submission and its behaviour,
with G2 asserted rather than executed. Second, the shim does **not** evade the
block through `getattr` indirection, so the counterfeit corpus is not missing
a reflection family: `getattr` on an already-imported module cannot bypass an
import-time hook.

## The result

74 controls built over the observable subset, 73 of which apply. **Unit =
control; gates G1, G3, G4a, G7, G8 only:**

| | n |
|---|---|
| no gate fired | **72** |
| **flagged — a false positive** | **2** |

**Both rejections are G3, the vendored-copy check, and both have the same
cause.** G3 fingerprints n-gram overlap against the library's own source. A
shim that re-exports a large namespace — `pandas` here, 51 lines of
`X = getattr(_lib, 'X', None)` — shares the library's identifier vocabulary
*by construction*, and the winnowing fingerprint fires on it.

This is a real limitation of G3 that the control exposed, and it is reported
rather than tuned away. State its scope honestly: 2 of 74 measures **G3's
precision on namespace-re-exporting shims**, a pattern genuine rewrites do not
exhibit, so it bounds this control family rather than G3's false-rejection
rate on real removals. The two affected pairs are both `pandas`, the widest
namespace in the pool.

**No behavioural gate reported a divergence on any control**, which is the
claim this control was built to test.

But be precise about which cynical reading that refutes. "The gate rejects any
structural change" is refuted: renamed call sites, a new module, re-pointed
imports, 74 times, zero divergence. "The gate rejects any output difference,
however benign" is **untouched** — these controls are behaviour-*identical* by
construction, so the canonicalisation layer that must forgive a correct
rewrite returning `1.0` where the library returned `1`, or a differently
ordered dict, has still never been tested against a submission that is correct
but not identical. A gate doing exact-match-on-summaries would produce this
table and the counterfeit table both. Only references written after the gate
was frozen, by someone who did not tune it, can separate those two gates.

## Which pairs got a control

One per pair of the observable subset (84), since a control needs a function
whose return the gate can compare and whose arguments it can vary. 74 were
built: 8 had no import line the rewriter could repoint and 2 had no importing
file or no recorded function. The denominator is the observable subset, not
the 172 traced pairs.

## What this does and does not establish

It establishes that the gate is **not** a rejector of structural change. On 72
of 74 mechanically generated behaviour-identical submissions, no gate in the
scoped set fires, and the two that do are attributable to one named structural
check with a stated mechanism.

It does not establish a false-rejection rate on *realistic* removals. These
are correct but degenerate: no replacement logic is written, so they exercise
the manifest, closure and equivalence machinery rather than the hard case of
judging a genuine rewrite. Together with the 172 over-declared removals (1
rejection, also G1-attributable) and the hand-written references, they bound
false rejection from several directions, none of which is the natural
held-out set a reviewer would most want: references written by someone who
did not tune the gate, after the gate was frozen. That remains open and is
stated as open.
