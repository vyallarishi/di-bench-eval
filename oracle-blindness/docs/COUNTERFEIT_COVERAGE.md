# The defining attack, on every pair the gate can see

The counterfeit that no structural check can catch is the *pseudo-genuine*
rewrite: declaration gone, nothing copied, no module takes the package's name,
no test touched, call sites pointed at a new internal module whose functions
have the right shape and the wrong values. It is the reason the behavioural
gate exists, so the gate's standing rests on how many of them it adjudicates
and how many it rejects.

## Why the earlier number was small, and what it was

The original corpus held 80 such counterfeits, of which **19** sat on a pair
with a recording. The cause was the generator's target list, not replay
failure: it selected two pairs per repository for breadth across 46
repositories, with no regard to whether the behavioural gate could observe the
result. That is a build-list problem and it is fixable.

## Building one per graded pair, and a trap in doing so

`make_pseudo.py` builds a counterfeit for each *graded* pair, driven by the
recording: the trace names the functions the repository calls and the types
they return, so the counterfeit returns a plausible value of the right type.

The first attempt produced 135 counterfeits, and **263 of its 498 generated
functions were not counterfeits at all.** The fake's fixed value collided with
every value the library actually returned — 254 of them because the generator
fell back to `None` for any unrecognised type, and so "faked" functions that
return `None` anyway. A gate that accepts such a submission is *correct*, and
counting it as a miss would report a generator artifact as a defect in the
instrument.

`verify_counterfeit.py` now checks every generated function against the
recording before any gate runs, and the generator chooses a value that differs
from **every** recorded return or refuses to fake the function. The corpus is
smaller and sound: **75 counterfeits over 141 functions, 141 of 141 genuinely
wrong by construction.**

Two classes are excluded by that rule rather than counted:

- **void functions** (72 in the first attempt): the library returns `None`, so
  there is no wrong return value to produce. A counterfeit the oracle cannot
  distinguish in principle measures nothing. These belong to the interface
  surface §4.2 already concedes the gate does not see — side effects — not to
  its hit rate.
- **functions whose recorded return type varies**, where no single literal is
  wrong on every call.

## The result, decomposed over every counterfeit built

| | n | share |
|---|---|---|
| built, all genuinely wrong | **75** | |
| **rejected by the behavioural gate** | **38** | 51% |
| accepted by the gate | **0** | 0% |
| no verdict: the gate cannot see | 37 | 49% |

**Every counterfeit the gate could adjudicate was rejected: 38 of 38.** At the
function level, 60 of 61 verdicts are rejections; the single `agrees` is one
function of a counterfeit whose other function was caught, so no counterfeit
escaped the pipeline.

The honest end-to-end sentence is therefore: *of 75 trace-informed
counterfeits, the gate rejects 38, accepts none, and cannot see 37.* The 98%
figure is conditional on a verdict and must never be quoted alone.

## Why the gate cannot see 37 of them

| cause | pairs | kind |
|---|---|---|
| an argument is a live object the recording cannot rebuild | 76 | **honest observability limit** |
| the library is not installable in the comparison environment | 4 | machinery |

The dominant cause is not a defect. The gate generates new inputs by varying
the recorded arguments, and an argument that is a live object — an open file,
a parsed document, a configured client — cannot be reconstructed from a
summary of it. Where the repository's use of a library is mediated by such
objects, the gate says so rather than guessing, and the structural gates carry
the grade.

## What this does and does not establish

It establishes that on the attack built to defeat every structural check, the
behavioural gate is never fooled where it can look, over 38 cases rather than
6. It does not establish anything about **false rejection**: these are all
counterfeits, and a gate that rejected everything would score identically.
That remains evidenced by the over-declared removals and the hand-written
references, and the held-out question stays open.
