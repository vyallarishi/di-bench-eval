# What any behavioural oracle can see, measured

The paper's thesis is that an oracle should be measured rather than assumed.
We applied that to the test suite and built a grader on the removed library.
This document applies it to **our own oracle**, because two experiments
measured its boundary without being designed to.

The first: building counterfeits for every graded pair produced 498 fake
functions, and **254 of them were not fakes** — the library function returns
`None`, so there is no wrong return value to produce. The second: grading them
showed the dominant reason the gate cannot speak is an argument that is a live
object the recording cannot rebuild.

Neither is a defect in the instrument. Both are properties of how real code
uses libraries, and a return-value oracle is blind to them *in principle*. So
they are worth measuring rather than apologising for.

## The measurement

Over **68,943 recorded calls** across the 172 traced pairs:

| per call | n |
|---|---|
| returns a value | 42,756 |
| returns `None` (side-effect only) | 26,187 |
| arguments reconstructible from the recording | 13,225 |
| at least one argument is a live object | 55,718 |

Per **(pair, function)**, n = 714:

| | n | share |
|---|---|---|
| **observable**: returns a value *and* arguments reconstructible | **164** | **23%** |
| returns `None` on every recorded call | 179 | 25% |
| returns a value but takes a live object | 371 | 52% |

**Fewer than a quarter of the ways these repositories use their dependencies
are visible to a return-value oracle at all.** A call that returns nothing
cannot be caught by comparing return values; a call whose arguments are an
open file, a parsed document or a configured client cannot be re-run on new
inputs, because the recording holds a summary of the object and not the
object.

## A third tier, defined here rather than derived by a reader

The benchmark already distinguishes two populations. This adds the third, and
it is the honest denominator for anyone comparing systems on behavioural
grounds:

| tier | pairs | what it means |
|---|---|---|
| **detected** | 330 | the test suite notices the removal; the task is real |
| **graded** | 172 | a recording exists, so the behavioural gate may speak |
| **observable** | **84** | at least one function returns a value from reconstructible arguments, so the gate can return a verdict on a well-formed rewrite |

Defining the observable subset explains, in advance, why a future agent run
will carry inconclusive verdicts, and it is why the counterfeit study
adjudicates 38 of 75: the rest sit outside this boundary.

## What it means for the grader's design

It bounds what *any* oracle of this shape can achieve, ours included, and it
argues that the gate's conservatism is the right default: where a call is
side-effect-only or carries unreconstructible state, the gate returns
inconclusive instead of guessing, and the structural gates carry the grade.

It also marks the direction a stronger oracle would take — comparing observable
*state* after a call rather than only its return value, which is the carving
idea the recorder already applies to objects it can reach. That would move
part of the 25% and some of the 52% into view, and it is future work rather
than a claim here.
