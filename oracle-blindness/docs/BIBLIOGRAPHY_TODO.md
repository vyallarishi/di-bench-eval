# Bibliography work (unassigned, parked)

This was Aman's brief until the audit made winnability the priority; it is parked here rather
than dropped, because it still has to happen before submission and it is the kind of thing a
reviewer notices.

The source of truth for what is wrong is `LIT_REVIEW_AUDIT.md`, appendix "bib entries that
support these experiments and need fixing".

1. **Eleven entries are wrong** — wrong venue, wrong year, or describing a different paper.
   `migrationbench2025` is the worst: cited as library-to-library migration, actually Java 8→17
   JDK migration, so the sentence citing it is wrong too.
2. **Every entry dated 2025–2026 needs verifying against a primary record** (ACM DL, IEEE
   Xplore, ACL Anthology, Springer, or the arXiv abstract page — not a Scholar snippet). Classify
   each as confirmed / preprint-only / wrong-venue / cannot-find. A citation nobody can locate is
   worse than no citation, so "cannot find" must be reported, never guessed around.
3. **~24 papers are missing** (the appendix's "To add" list). For each, one sentence on what it
   shows and which of our claims it supports or contradicts.
4. **Priority within that list**: flag immediately anything that already did manifest mutation,
   a removal/debloating benchmark with execution-based grading, or detection of agents gaming a
   dependency benchmark. Those change what we can claim to be first at. Shulepov 2608.27100 is
   the one we already know about.
5. **Cross-check prose citations** in `paper/acl_latex.tex`: does each sentence describe what the
   cited paper actually says? Report, don't edit — the paper is being restructured.

Constraints when someone picks this up: keep bib keys stable (changing one breaks every `\cite`),
and `bibtex`/`biber` must still run clean.
