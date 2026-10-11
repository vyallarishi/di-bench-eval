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

## The result

74 controls built over the observable subset, 73 of which apply:

| unit = control | n |
|---|---|
| accepted, or inconclusive with no gate failing | **72** |
| **rejected — a false rejection** | **2** |

**Both rejections are G3, the vendored-copy check, and both have the same
cause.** G3 fingerprints n-gram overlap against the library's own source. A
shim that re-exports a large namespace — `pandas` here, 51 lines of
`X = getattr(_lib, 'X', None)` — shares the library's identifier vocabulary
*by construction*, and the winnowing fingerprint fires on it.

This is a real limitation of G3 that the control exposed, and it is reported
rather than tuned away. It bounds the gate in a specific, stateable way: a
replacement that re-exports many of a library's public names can be
misclassified as a copy of it. The two affected pairs are both `pandas`, the
widest namespace in the pool.

**No behavioural gate rejected any control.** G4a and G4b accepted every one
they could speak on, which is the claim this control was built to test: the
gate's notion of equivalence admits correct submissions it has never seen.

## What this does and does not establish

It establishes that the gate is **not** a rejector. On 72 of 74 mechanically
generated correct removals, it does not fire, and the two failures are
attributable to one named structural check with a stated mechanism.

It does not establish a false-rejection rate on *realistic* removals. These
are correct but degenerate: no replacement logic is written, so they exercise
the manifest, closure and equivalence machinery rather than the hard case of
judging a genuine rewrite. Together with the 172 over-declared removals (1
rejection, also G1-attributable) and the hand-written references, they bound
false rejection from several directions, none of which is the natural
held-out set a reviewer would most want: references written by someone who
did not tune the gate, after the gate was frozen. That remains open and is
stated as open.
