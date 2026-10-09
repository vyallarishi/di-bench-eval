# Is this one benchmark's problem, or the oracle's?

The obvious objection to everything measured here is that it describes
DI-Bench and nothing else. It does not, and the argument can be made on our own
data without running anything new.

Three published pipelines grade dependency work by execution, and they do not
share an oracle. They sit on a spectrum:

| Pipeline | What it checks |
|---|---|
| **DI-Bench** | the repository's own CI suite passes |
| **EnvBench** | `pyright` reports zero `reportMissingImports` |
| **Repo2Run** | `pytest --collect-only` succeeds, then tests run — success is judged *regardless of whether they pass* |

CI is the strictest of the three. So a failure mode that defeats CI defeats the
others by construction, and the only question is by how much.

## The same removals, three oracles

Each of our 569 screened removals is a question all three can be asked: *would
you notice this dependency leaving?* CI's answer we measured. The others follow
from what they check.

| Oracle | Notices | Blind | Blind % |
|---|---|---|---|
| CI replay (DI-Bench) | 330 | 239 | **42%** |
| Static import check (EnvBench) | 302 | 267 | **47%** |
| Collection-only (Repo2Run) | ≤ 302 | ≥ 267 | **≥ 47%** |

The static import check is blind to everything CI is blind to, **plus 28 more**:
removals CI notices but no import analysis can, because the package is reached
through a plugin, a console-script entry point, or a tool the workflow invokes.
`mu-editor` is the clearest case — `click`, `flake8` and `virtualenv` are all
used without the project importing them.

Collection-only is weaker again: a suite that collects but fails is still a
pass, so every removal the import check misses, it misses too, and others
besides.

## What this licenses the paper to say

Not *"DI-Bench has a problem"* but *"execution-based dependency evaluation has a
problem, and the strictest oracle in the family is the least affected."* A
reviewer cannot deflect by naming a pipeline we did not test, because the
untested ones are weaker than the one we did.

## What it does not license

The 42% is measured; the 47% is **derived**, not observed. It follows from what
EnvBench's oracle checks — one `pyright` invocation counting unresolved imports
— applied to footprints we computed ourselves. We have not run EnvBench's
harness over its own 329 repositories, and the figure is a projection onto our
population, not a measurement on theirs.

That distinction belongs in the paper. The ordering is sound and the mechanism
is verified in their source; the precise number for their population is not
ours to claim.
