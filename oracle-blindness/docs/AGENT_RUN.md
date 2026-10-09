# A frontier model on the benchmark, and what the grader says about its passes

GPT-5.1 attempted 100 of the 330 pairs through the tool-using scaffold in
`pilot/agent_runner.py`. The sample is the determined 100-pair draw described
in `AGENT_SAMPLE.md`; the agent was **not** given the files that import the
package (`AGENT_HINT=0`) and had to locate them itself, which is the harder
and more honest setting. Cost: $10.17 on OpenRouter, 6.89M prompt tokens of
which 2.27M were served from cache, 292,958 completion tokens.

## The attempts

All 100 produced a patch. 98 ended by declaring the task complete rather than
exhausting the 40-step budget, so the failure rate below is not an artifact of
a cheap step limit. 84 patches are in-place edits, 12 change only the
manifest, 4 add a module; 30 touch a test file. The human references mostly
*added* a module, so the agents are solving the task differently from the way
we solved it by hand.

## What CI says

| tier | pass | rate |
|---|---|---|
| narrow (1–2 files) | 13 / 60 | 22% |
| medium (3–4) | 1 / 12 | 8% |
| wide (5+) | 1 / 19 | 5% |
| indirect track | 4 / 9 | 44% |
| **total** | **19 / 100** | **19%** |
| excluding the indirect track | 15 / 91 | 16% |

The indirect track is reported separately and should not be pooled. Those
pairs have no importing file — the package is reached through a plugin, an
entry point, or a tool the workflow invokes — so a passing submission there
deletes a declaration and changes no code. Its 44% is not comparable to the
5–22% on pairs that require a rewrite. The rate falls monotonically with how
much code the removal touches, which is what the tier is supposed to mean and
evidence that the tiers measure something real.

**19 of 100 is the number a conventional benchmark would report**, and it is
the number this paper exists to qualify.

## What the grader says about those 19

| verdict | n |
|---|---|
| accepted by every gate | **1** |
| rejected by a named gate | **7** |
| inconclusive: a gate cannot speak | **11** |

Of 19 submissions a test-based oracle calls correct, **one** survives the full
stack. Seven are rejected, each attributable:

| gate | rejections | what it found |
|---|---|---|
| G5 no phantom use | 6 | the package still arrives, transitively or from a second source |
| G1 declaration gone | 2 | the declaration is still there |
| G8 closure not grown | 2 | the dependency closure grew |
| G7 tests untouched | 1 | tests were modified |

Two rejections rest on a constraint the prompt never stated (a trade, or a
vendored copy), and are counted separately: an agent cannot be faulted for
violating a rule it was not given, so those are reported as the grader
catching a behaviour rather than the model failing a task.

### The clearest single case

`jazzband_django-cookie-consent` / `django`. The task is to remove `django`.
The submission **re-declares `django` and changes nothing**, and the
benchmark's own verdict is `pass`. G1, G5 and G8 all reject it. This is the
paper's thesis in one instance, produced by a frontier model in a real run
rather than by a constructed counterfeit.

`treebeardtech_nbmake` / `pytest` is the other one worth naming: the package
is still installed **and** the tests were modified — the test-weakening
behaviour the counterfeit corpus was built to model, occurring unprompted.

### The accepted one, and why the gate could say so

`RhinoSecurityLabs_IAMActionHunter` / `pandas` replaced a DataFrame CSV write
with `csv.DictWriter`. A recording existed for that pair, the candidate was
re-run under the recorder, and the usage-site comparison is **identical**: the
replacement produces what the library produced on the inputs the suite
exercises. That is the only submission in this run the behavioural gate could
both reach and confirm.

## The honest limit

**G4a is unverified on 18 of the 19.** For 17 of those there is no recording
for the pair at all — coverage is 85 of 330 — and for the rest the suite made
no call into the package. So the behavioural gate contributed one verdict in
this run. The seven rejections rest on the structural gates, which is a weaker
claim than the paper's headline mechanism, and the paper must say so: the
grader's *reach* is the binding constraint, not its precision.

What the result does establish is narrower and still worth stating. A
test-based oracle accepted 19 submissions; of those, 7 are demonstrably not
removals at all, 11 cannot be confirmed, and 1 is confirmed correct. Reporting
19/100 as a solve rate would be reporting, in at least 7 cases, submissions
that leave the dependency in place.
