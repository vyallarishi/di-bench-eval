# How much of a value the behavioural comparison can see

The behavioural gates (G4a on recorded inputs, G4b on generated ones) decide
whether a replacement returns what the library returned. They do not compare
objects; they compare *summaries* of objects, because the library is about to
be deleted and a live object from it cannot be kept, and because deep equality
of arbitrary Python objects is undefined in general. A summary can be less
than the value. Where it is, two different values summarise the same way and
a divergence there is invisible to the gate. This document states what the
summary captures, measures how much of the recorded traces fall in each class,
and records the change that moved most values into the class where equality
is decided on the whole.

## What is compared, by class of value

| class | summary | equality |
|---|---|---|
| primitive (`None`, bool, int, float, str, bytes) | the value, with str/bytes capped at 300 characters for display | exact; floats within 1e-9 relative, NaN equals NaN |
| container (list, tuple, set, dict), depth ≤ 3 | up to 20 elements, each summarised | length and element-wise |
| anything past a cap | the display prefix **plus a SHA-1 of the whole** | the hash decides; the prefix is for reading |
| array-like (`shape`/`dtype`/`size`) | shape, dtype; full content inlined if ≤ 64 elements, else a hash of `tobytes()`; tables hash their CSV | shape and content |
| function, class, generator | type and qualified name | by name; what it produces is recorded when the repository calls it |
| any other object | type, address-stripped repr, `len()` if it has one, and its **public non-callable attributes**, summarised recursively to depth 2 | type, repr, length, and every attribute |

The attribute rule is the state-carving idea of Elbaum et al. (FSE 2006) and
Rostra (Xie, Marinov & Notkin, ASE 2004): compare an object by the state the
program can observe through its interface, not by identity. A replacement
that returns a plausible object of the right type must therefore match what
the repository can read from it — a `Response` its status, headers and body; a
pydantic `FieldInfo` its default, alias and constraints — not merely print the
same first 300 characters.

A record is bounded at 32 KB because the trace travels through the CI log.
When a record is over the bound, expanded structure is replaced by a hash of
that structure. Equality over the shrunk form is equality over the full
summary; only readability is lost. The rules live in
`record_usage.values_equal` and the summariser in `record_usage.RECORDER`;
G4b compares through the same summariser (`record_usage.summarize`), so the
two gates cannot disagree about what "same" means.

## Measured coverage

`trace_fidelity.py` classifies every recorded return value by what the
comparison can see of it. Over the 38,381 return values in the 86 reference
traces recorded by the **earlier** recorder (repr-only objects, no hashes):

| class | values | share |
|---|---|---|
| exact | 31,321 | 81.6% |
| array, full content inlined | 1,333 | 3.5% |
| exception (compared by type) | 295 | 0.8% |
| opaque: object by repr only | 3,316 | 8.6% |
| truncated: past a cap, no hash | 2,116 | 5.5% |

So 85.8% of recorded values were decided on the whole value and 14.2% on a
repr or a prefix. The opaque class was dominated by generators (527),
`pandas.DataFrame` (450), functions (446), `bytearray` (300, which the earlier
summariser did not recognise as bytes), Flask/Werkzeug responses (521), and
pydantic field and model objects (222).

The new recorder changes the class of each of those: bytearrays are bytes;
functions and generators are identified by name; DataFrames hash their
content; responses and pydantic objects are compared by attributes; anything
past a cap is hashed. The re-recorded traces will be measured with the same
script and the table above repeated for them; until then the paper quotes the
**earlier** coverage as the lower bound and does not quote a number for the
new recorder.

<!-- AFTER RE-RECORDING: run `python3 scripts/gh/trace_fidelity.py` on the
new traces and add the second table here. Numbers above are from the traces
committed in a6c5e2e. -->

## What this does and does not change

It changes nothing about the results already reported. The five `pseudo_genuine`
variants that G4b caught were re-run under the new comparison and are still
caught, 5 of 5, each at 300 of 300 generated inputs
(`results/g4b_pseudo_genuine.json`, produced by `g4b_variants.py`). The gate
test suite (25 two-way cases) and the G4 fixture (honest / pseudo / hollow)
are unchanged. The false-rejection measurement does not depend on the summary
form.

It does not make the comparison complete. A generator's output is seen only
if the repository consumes it through a recorded call; a private attribute is
not compared; an object with no public attributes and no length is still a
repr. Coverage is therefore reported per trace rather than assumed, and a
G4a pass on a pair whose values are mostly repr-only is weaker evidence than
a pass on a pair whose values are mostly exact. The grade carries that
coverage.
