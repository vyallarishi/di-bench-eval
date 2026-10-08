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

## What is checked

`code/harness/check_leakage.py` reports, per pair, every file other than the
build file that declares the package, and whether CI installs from it. The first
is reported; the second is disqualifying.
