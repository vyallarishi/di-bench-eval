# Which results were built by a superseded tool, and what it cost

An injected file is generated code embedded in every prediction patch, so a
patch is a frozen copy of whatever the generator produced on the day it ran.
Fixing the generator does not fix a dispatched set. That is how 622 screening
patches came to carry a recursion bug that had already been fixed, and why the
defect surfaced a day later from someone reading CI logs rather than code.

`code/harness/check_stale.py` compares what each prediction set contains against
what the generator produces now, and names the difference. It exits non-zero on
any stale set.

## Current state

| Set | Patches | Status |
|---|---|---|
| `all`, `all_large` | 622 | **stale** — built the pool |
| `blocked`, `blocked_large` | 673 | stale — superseded by `all` |
| `scoped`, `scoped_large` | 383 | stale — superseded by `all` |
| `requeue`, `requeue_large` | 28 | current |
| `trace`, `trace_large` | 348 | current |

The screening sets lack three fixes: the flag-based install guard, the
resolved-path origin test, and the activation announcement.

## What that actually cost, measured rather than assumed

**The recursion guard: 28 pairs, removed.** A third-party import of the blocked
package recursed between the conftest and sitecustomize finders until
`RecursionError`. Those instances failed inside the injected finder, not on the
dependency. Found by searching the pool's own logs for `RecursionError` in
`find_spec`. Quarantined and re-screened with the fixed blocker.

**The symlink fix and the announcement: no effect on the pool.** Both would make
the blocker inert, and an inert blocker emits no block message. Of the 320
remaining pairs, **271 carry the block message**, which is positive proof the
blocker was live. The other **49** were admitted on evidence that does not
depend on the blocker at all:

| Evidence | n |
|---|---|
| CI failure with no import error | 36 |
| Missing-module error from a repository frame | 10 |
| Linter named the package | 3 |

Each of those is CI noticing the *declaration removal*. An inert blocker would
not change the verdict, so the admissions stand.

The symlink defect is also specific to macOS, where `/tmp` resolves through a
symlink. The GitHub runners check out to a real path and the container mounts
`/project` directly, so `abspath == realpath` there.

## The process failure, stated plainly

The fix was cheap. Not knowing the dispatched results were stale was expensive:
a published pool size, a README, and a paper table were all built on it. The
checker exists so that the next fix-after-dispatch is caught by a command rather
than by a colleague.
