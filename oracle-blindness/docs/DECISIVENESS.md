# How often does the grader return a verdict?

A grader that abstains most of the time is principled and useless. The
benchmark's practical value depends on the share of submissions it decides,
so that share is reported as a first-class number rather than left implicit.

## The number

From the GPT-5.1 run, 100 submissions over the sample of 100 pairs:

| population | rejected | inconclusive | accepted | **decisive** |
|---|---|---|---|---|
| all 100 submissions | 88 | 11 | 1 | **89%** |
| the 59 on **graded** pairs (a recording exists) | 55 | 3 | 1 | **95%** |

On the graded subset — the subset we recommend for comparing systems — the
grader returns a definitive verdict on **95%** of submissions.

## Why an earlier figure looked much worse

The figure "11 of 19 inconclusive" is true and misleading: it conditions on
the 19 submissions that *passed CI*, which is a small and unrepresentative
slice. Most submissions fail a structural gate or the tests, and those are
decided. Conditioning on CI passes measures the hardest cases for the
behavioural gate, not the grader's yield.

Both numbers belong in the paper, with the conditioning stated: the grader is
decisive on 95% of submissions overall, and on the submissions CI accepts —
where the behavioural gate is the only thing left to consult — it abstains on
11 of 19, because a recording does not exist for most of those pairs.

## What raises it

Decisiveness is bounded by recording coverage, not by the gate's logic: 143
of 330 pairs have a recording, and a submission on a pair without one can
only be decided structurally. The coverage figure is therefore the quantity
to improve, and the graded subset exists so that a user who wants decisive
grading can have it.
