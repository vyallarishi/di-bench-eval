# Session brief: write the paper

You are writing an ACL main-track submission from a finished body of work. The
experiments are done and measured; your job is the paper. You were not involved
in the work, which is an advantage: you will write what the evidence supports
rather than what the authors hoped for.

**Repository:** `https://github.com/vyallarishi/DependencyRefactoring`

```bash
git clone https://github.com/vyallarishi/DependencyRefactoring.git
cd DependencyRefactoring
```

## Read in this order

1. `docs/THE_STORY.md` — the whole argument in plain language, five pages. Read
   it first and read it twice. Every number in it is current.
2. `docs/WRITING_PLAYBOOK.md` — how the papers we will be compared against are
   built: abstract ordering, intro paragraph by paragraph, how to critique a
   benchmark without sounding like a polemic, what ACL requires. **Follow its
   structural template.** It also contains the single most important fact for
   the introduction: the benchmark we build on states our target premise in its
   own text and dismisses the concern in its own limitations section. Quote
   that early.
3. `paper/acl_latex.tex` — the current draft. The abstract, contributions,
   census table, pool description, gate table, predictor section and
   Limitations are up to date. The rest is older and must be checked against
   the docs below before any number is kept.
4. `docs/BLIND_SPOT_ANATOMY.md`, `docs/ROBUSTNESS.md`, `docs/CROSS_ORACLE.md`,
   `docs/PREDICTOR.md`, `docs/GRADER_DESIGN.md`, `docs/LEAKAGE.md` — one per
   result, each with the exact figures and the honest caveats. These are the
   source of truth for every claim.
5. `docs/BENCHMARK_AUDIT_REPORT.md` — an independent adversarial audit. Not for
   citing; for knowing what a hostile reader will look for.

Do not read `docs/STALENESS.md`, the `BRIEF_*.md` files, or anything under
`sushane/`. They are process, not results.

## The structure, which is decided

Four parts, in this order. Do not reorder them.

**Part 1 — a task nobody measures.** Removing a dependency the code actually
uses, by rewriting the code. Inference benchmarks restore declarations;
debloating tools remove unused ones; migration benchmarks swap libraries. This
sits in the gap. Keep it short.

**Part 2 — the oracle is blind.** The benchmark grades by "do the tests still
pass." We screened every dependency of every gold-passing repository, made each
one genuinely unimportable, and re-ran the real test suite. 622 candidates, all
accounted for. 239 passed anyway. **Lead with the decomposition, not the
total:** 172 over-declared, 49 oracle-blind in the strict sense, 13 used
without importing, 5 optional by design. Report the per-repository median
(20.0%) and incidence (35 of 51), never the pooled rate alone — one repository
supplies 126 of the 239. Include gold rot: 51 of 96 of the benchmark's own
answers no longer pass. Include the robustness checks from `ROBUSTNESS.md`:
dropping the ten worst repositories leaves the median at 14.3%; 11 of 12
widely-used projects are affected; blindness correlates −0.34 with test
coverage. Include the cross-oracle comparison from `CROSS_ORACLE.md` with its
stated caveat that the 47% is derived, not observed.

**Part 3 — a benchmark where the oracle can see.** 330 verified pairs over 73
repositories, four tiers. Every candidate's disposition published: kept, blind,
or excluded with a written reason. The admission rule: a failure counts only if
it arises from the repository's own use of the package. State what is excluded
and why — optional-by-design, second install source, failure inside another
package, stdlib-shadowing names.

**Part 4 — a grader.** Eight gates; a removal must pass all of them, and the
tests remain one of them — the grader supplements CI, it does not replace it.
Say that explicitly or invite the obvious objection. The gate table over 617
constructed variants: each family caught by its intended gate, the honest
deletion left alone 79 of 80, and `pseudo_genuine` surviving every structural
gate 80 of 80. Then the idea everything rests on, stated once and prominently:
**in a removal task the removed library is a canonical oracle, present and
recordable before it is taken away.** The behavioural gate records what the
library did, then checks the replacement against it — on the recorded inputs
(G4a) and on generated neighbours of them (G4b, after RGT; cite Ye, Martinez &
Monperrus, EMSE 2021). Results: 12 of 12 CI-passing cheats rejected; 5 of 5
evaluable `pseudo_genuine` variants caught at 300 of 300 inputs; 38,381 calls
recorded from 86 projects' real test runs. False rejection: 0 of 172
known-correct removals, against RGT's 2.3% for their technique.

**Limitations** — already written in the tex, mandatory for ACL, outside the
page limit. Keep its content; it leads with the two weakest points on purpose.

## Rules

- **Every number comes from a doc.** If a figure in the tex is not in one of the
  docs above, it is stale: find the current value or cut the sentence. The
  predictor's old 0.81/0.83 is withdrawn; `PREDICTOR.md` has the replacement
  and the reason.
- **State what is derived separately from what is measured.** The playbook and
  the docs mark these. Do not blur them.
- **No process history.** Nothing about bugs found, fixes applied, audits run,
  or what was tried first. The reader gets what exists.
- **Numbered research questions**, used as results-section titles. The playbook
  explains why.
- **A worked example on page 1 or 2.** Use `5j9_wikitextparser` / `wcwidth`:
  one import, two call sites, a library that measures terminal column width.
  `THE_STORY.md` has the real fake that beats every structural gate — the
  function returning `{'0': 1}` where the library returns `1`. Show it.
- **Related work must differentiate from STING and PatchDiff explicitly** — the
  playbook has the three differences. The strongest is that we find a failure
  mode that is not about assertion strength at all.
- **Contributions bulleted on page 2 at the latest.**
- Keep the existing bib keys; `BIBLIOGRAPHY_TODO.md` lists which entries are
  known to be wrong, so flag rather than cite those.

## What to hand back

The complete `paper/acl_latex.tex`, compiling, every section consistent with the
docs. Plus a short `paper/CLAIMS.md`: one line per quantitative claim in the
paper, with the doc and figure it comes from. That list is how the authors will
check your work, so make it complete.
