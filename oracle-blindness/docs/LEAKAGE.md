# Does the repository give the answer away?

A repository carries more than its build file. Lock files, `requirements*.txt`,
`tox.ini` and CI configuration can all name the same package, and an agent can
read every one of them. Two different problems hide under that, and only one is
a defect.

## The defect: a second install source

If CI installs from a file *other* than the one the task asks the agent to edit,
and that file also declares the package, then deleting the declaration removes
nothing. The package still arrives. Such a task is not winnable by doing the
right thing, and is trivially passable by doing nothing.

Measured across the pool: **5 pairs**, now excluded with the reason recorded.

| Instance | Dependency | CI installs from |
|---|---|---|
| `aws_chalice` | `botocore`, `jmespath`, `six` | `requirements-test.txt` |
| `abersheeran_kui` | `pydantic`, `typing_extensions` | `pdm.lock` |

`aws_chalice` is the clearest: its workflow runs
`pip install -r requirements-test.txt`, so `setup.py` is not the file that
decides what gets installed.

## Not a defect: the name appearing elsewhere

**18 pairs** name the dependency in a file CI never installs from — a docs
requirements file, a dev lock, a tox environment. These stay in the pool, for
two reasons.

The task is not *guess which dependency to remove*. The agent is told which one.
So a file that names it leaks nothing: there is no hidden answer to leak.

And the grader does not reward finding the name. It asks whether the code was
rewritten so the project no longer needs the library, and checks that against
what the library actually did at run time. Reading `docs/requirements.txt`
does not help with any of that.

What these files *would* leak is the answer to DI-Bench's original task —
inferring the dependency set — which is why that benchmark masks them. Our task
is the inverse, so the masking matters less, but the distinction is worth
stating rather than assuming.

## The other question: does the *evaluation* leak into the workspace?

The section above asks whether the repository gives the answer away. This asks
whether we do. The agent's workspace is a copy of the masked checkout with the
gold manifest restored, built by walking the tree and copying every file except
`.git` — so anything our own tooling has ever written into a checkout travels
with it, and a stale copy would hand the agent the grader's instrumentation.

Four things would be disqualifying, and `check_agent_leakage.py` looks for all
four in every checkout: our injected import block or usage recorder (written
into a checkout as `sitecustomize.py` and `conftest.py`), a recorded trace (which
names every call the repository makes into the package, i.e. the behavioural
gate's oracle), an evaluation artifact (`eval-result.json`, a prediction patch,
a results directory), and a gold answer from another pair.

**Result on the 73 repositories of the pool: clean.** No injected file, trace,
or evaluation artifact in any checkout.

That is the static check. The stronger one reads what the agents actually saw:
across the 100 trajectories of the GPT-5.1 run, 1,138 `read_file` results and
every `list_files` and `grep` output, **no evaluation-internal string appears
at all** — no `UnpinBench`, no install flag, no finder class, no trace marker,
no `eval-result`. No agent opened `sitecustomize.py` or `conftest.py`, and no
agent patch contains our block. The grading instrumentation is applied after
the agent finishes, to a fresh checkout, which is why.

One false positive is worth recording because it shows the check is doing
something: `NVIDIA_NVFlare` ships its own `nvflight/patch.diff`, which a
filename rule flagged as ours. It is upstream, dated with the original
checkout, and carries none of our markers. The rule now requires a marker or
a root-level path.

### What the prompt reveals

The task prompt names the package to remove, the build file to edit, and asks
that the suite keep passing. It does not mention the grader, the gates, the
import block, the recorder, or the traces — verified by inspection of the
prompt template rather than by assertion. An agent therefore cannot aim at a
gate it has not been told about, which is what makes the counterfeit families
in the gate table a fair model of unprompted behaviour.

## What is checked

`code/harness/check_leakage.py` reports, per pair, every file other than the
build file that declares the package, and whether CI installs from it. The first
is reported; the second is disqualifying.
