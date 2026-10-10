# Two experiments that change what the grader results are (from the results critique)

For the session working on scripts/gh. The paper session will not touch scripts.

## 1. Mutation analysis of the references (highest leverage, cheap)

The behavioural gate's evaluation rests on 4 counterfeit rewrites and 4 development-tuned
references. Grow n where the gate can see: take every reference whose replacement the
recorder can observe (a new module named as a target: wcwidth, python_slugify, cli_ui,
docopt, and any that the usage-site recorder now makes observable) and mutate the
*replacement*: flip a comparison operator, negate a condition, drop a branch, off-by-one
on an integer literal, return a constant of the right type, swap two arguments. Each
mutant is a near-correct counterfeit on an observable pair; each reference yields dozens.

Measure, per mutant: (a) tests pass or fail under the block (G2); (b) G4a verdict on
recorded inputs; (c) G4b verdict on generated inputs. Report, per reference and in total:
mutants killed by the tests, killed by the behavioural gate, killed by neither, and the
share killed by the gate among those the tests miss. That is the oracle-strength
measurement the field expects (mutation score), and it sits exactly where the gate can
see, so it avoids the 5-of-80 coverage problem. Exclude equivalent mutants by the usual
rule (identical output on every generated input is reported, not counted as a miss).
Write results to results/reference_mutants.json; add the numbers to RESULTS_LEDGER.md.

## 2. Pilot verdicts before anything else in RQ5

The agent attempts are the only grader evidence not constructed by us. Run every attempt
through the grader (task 5 of the brief) and report, for each CI pass: which gate rejects
it, or inconclusive with the reason. A CI pass the behavioural gate catches is the
strongest single result the paper can have; say so in the ledger if one exists.

## Note for both sessions

TeX control-sequence names cannot contain digits: `\nRefsG3Flagged` and `\nAgentRunG4Unverified` broke the build and were renamed with words (`GThree`, `GFour`). Use letters only in numbers.tex.
