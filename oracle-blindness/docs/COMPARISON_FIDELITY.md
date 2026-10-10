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
comparison can see of it. The traces were recorded twice under the real CI
harness, once with the original summariser and once with the current one, on
the same projects, so the change is measured rather than argued.

| class | before | after |
|---|---|---|
| exact (primitive, or a container of exact elements) | 82.3% | 81.6% |
| array, full content inlined | 3.5% | 3.9% |
| hashed: past a cap, hash of the whole decides | — | 7.2% |
| structural: object compared by public attributes and length | — | 1.3% |
| exception, compared by type | 0.7% | 0.7% |
| **opaque: object by repr only** | **7.9%** | **5.2%** |
| **truncated: past a cap, no hash** | **5.6%** | **0.0%** |
| **decided on the whole value** | **86.5%** | **94.8%** |

Measured on the 84 projects traced by both recorders, 37,914 and 37,947
return values respectively. Truncation is effectively eliminated (2,116
values to 6) because anything past a display cap now carries a hash of the
whole; the remaining 5.2% are objects that expose no public attributes and no
length, for which type and address-stripped repr is all there is.

The opaque class under the original summariser was dominated by generators
(527), `pandas.DataFrame` (450), functions (446), `bytearray` (300, which the
summariser did not recognise as bytes), Flask and Werkzeug responses (521),
and pydantic field and model objects (222). Each of those is now in a class
where equality is decided on content or on observable state.

Coverage of the pool is a separate number from fidelity of a value, and it is
the weaker one: recordings exist for 85 of the 330 pairs. For the remainder
the recorder loaded but the suite made no call into the package (77, which is
a finding rather than a gap: those suites do not exercise the dependency), or
the recorder did not load under that project's test runner (168), or CI was
not green under it (62). The behavioural gate speaks for the pairs it can
observe and says so otherwise.

## One thing that is deliberately not compared: the method receiver

An instance method's first argument is the object the method is called on, and
it is the same object on every call into that instance. Carving its attributes
per call re-serialises the whole object state thousands of times: on
`mandiant_speakeasy` / `pefile`, where `self` is a parsed PE image, the trace
reached 145 MB over 21,394 calls with 98% of the bytes being the receiver,
repeated.

The receiver is therefore summarised by type and address-stripped repr, not
carved. The justification is not the file size: the receiver is not the call's
input, and a replacement is not judged on the internal state of an object the
library itself owns. What the gate compares is the arguments the repository
passed and the value it got back, and those are recorded in full — after the
change, `width("xx")` still records `{"t": "str", "n": 2, "v": "xx"}` as the
argument and the returned integer exactly. Measured on a synthetic library
with a fat receiver: 568 bytes per call against 10,687, a 19-fold reduction
with no loss to either side of the comparison.

The cost is that a removal which changes observable state on a library object
*and* nothing else would not be caught here. That is a narrow case — the
object belongs to the library being deleted — and the usage-level comparison
sees the repository-visible effects.

## What this does and does not change

It changes nothing about the results already reported. The five `pseudo_genuine`
variants that G4b caught were re-run against the re-recorded traces under the
new comparison and are still caught, 5 of 5, each at 300 of 300 generated
inputs (`results/g4b_pseudo_genuine.json`, produced by `g4b_variants.py`). The gate
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


## After the recorder change (corrected runs, 10 Oct)

The same classification over the traces recorded under CI by the current recorder, now
writing through pytest's saved console descriptor so that a recorder loaded through
`conftest.py` is no longer silent (runs 37981747401 and 37981752738;
`results/trace_states.json` lists the outcome per pair, `results/trace_fidelity.txt` the
split):

| class | values | share |
|---|---|---|
| exact | 42,625 | 61.8% |
| array, content inlined | 10,933 | 15.9% |
| opaque (repr only) | 6,416 | 9.3% |
| structural (public attributes and length) | 3,815 | 5.5% |
| hashed (past a cap, hash decides) | 3,754 | 5.4% |
| exception (compared by type) | 853 | 1.2% |
| bytes whose decoded length is below their byte count | 546 | 0.8% |

68,942 return values over 172 traced instances (143 pairs with a green suite);
**89.9%** decided on the whole value, 10.1% on a repr or prefix. 87,675 calls were
recorded; one trace is published capped at 400 records per call site
(`mandiant_speakeasy / pefile`, 21,387 records averaging 6.8 KB, 138 MB, over GitHub's
file limit), keeping all 24 of its sites and all 14 library functions and dropping 18,733
records from the four hottest sites, all of them `exact` integers, which is why the share
is lower than the 92.1% over everything recorded. `cap_traces.py` applies the cap and
writes the counts into the trace's own first line; `trace_fidelity.py` reports them. The
population also changed with the fd fix (recorder never loaded: 168 pairs → 6; traced
pairs 85 → 143), which is why neither figure is the 94.8% measured over the 85 pairs the
earlier runs could see. The last row is not a cap: a `bytes` value is recorded as its UTF-8 decoding with
replacement characters, so an invalid byte sequence decodes to fewer characters than it
has bytes; equality is over the decoded content, and two values that differ only in
invalid bytes mapping to the same replacement character would compare equal (546 values,
all from python-adaptive's pickled learners and speakeasy's buffers).

Coverage of the pool after the fix: traced 143 of 330, loaded but no call 117, not green
under the recorder 64, never loaded 6.
