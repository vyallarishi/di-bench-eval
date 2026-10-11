# Does this task occur in the wild?

The paper asks agents to remove a dependency the code uses, which means
rewriting the code. A reviewer's fair question is whether that happens often
enough to be worth a benchmark. This records what we measured, including a
measurement that failed and must not be quoted.

## What we measured, and what it says

The screening is itself the evidence, on the population the paper uses. Of
**622** declared dependencies across 80 gold-passing repositories:

| | n | share |
|---|---|---|
| removal is detected by the tests, so it is a real task | 330 | 53% |
| of those, **at least one repository file imports the package**, so removal requires rewriting code | **302** | **49% of all candidates** |
| declaration only, reached through a plugin or tool (indirect track) | 28 | 4% |
| silent: the tests do not notice | 239 | 38% |
| excluded with a stated reason | 53 | 9% |

**Roughly half of all declared dependencies in this population are ones whose
removal would require writing a replacement.** The median such pair has two
importing files. That is the frequency claim, measured rather than asserted,
and it is about *opportunity* — how often the situation exists — not about how
often maintainers act on it.

## A measurement that failed, recorded so it is not repeated

We also tried to mine real removal commits from upstream git history, to show
maintainers *do* act. On `5j9_wikitextparser` (1,772 commits, 289 touching a
manifest):

- a first query — a commit that drops a declaration **and** edits `.py` in the
  same commit — returned 247 hits, almost all version bumps caught by a loose
  regex, and ~0 after filtering;
- a corrected query — was the dropped package ever imported anywhere in
  history? — returned **3 of 32** dropped packages, of which two are artifacts
  of a `setup.py` → `pyproject.toml` migration.

So one repository yields about one genuine case, and the exercise does not
scale to a number worth printing. **The reason is methodological, not
empirical: the commit is the wrong unit.** Maintainers routinely rewrite the
code first and drop the declaration later, often in a different commit or a
squashed pull request, so a single-commit query structurally cannot see the
event it is looking for.

**Do not cite "1,772 commits yielded zero removals" as evidence that the task
is rare.** It is evidence that our query was wrong. The honest statement is
that we did not measure maintainer behaviour, and that the frequency claim
above is about opportunity.

## What would settle the behavioural question

Two published sources are built for it and should be used rather than
re-mined by hand: the 2024 dataset of dependency-removal commits with their
pull requests, and the study of 19,652 Java projects that found 8,065 with at
least one library removal. The number to extract from them is the share of
removals that rewrite code against the share that merely drop an unused
declaration or swap one tool for another. That is a literature task, not a
compute task, and it is the one paragraph that converts this from a
vulnerability into support.
