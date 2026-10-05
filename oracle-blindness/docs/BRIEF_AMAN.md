# Brief: Aman — fix the bibliography and verify every citation

The paper's related work is currently its weakest section: eleven bib entries have wrong venues or describe the wrong paper, roughly twenty-four papers that should be cited aren't, and several entries dated 2026 have never been checked against a real record. A reviewer who finds one miscited paper stops trusting the rest of the section. This is self-contained, needs no execution, and nothing anyone else is doing tonight touches these files.

**Repository: `https://github.com/vyallarishi/DependencyRefactoring`** — the paper's repo, newly created. Clone it and work in `paper/custom.bib`, keeping notes in a new file `docs/CITATION_VERIFICATION.md`.

```bash
git clone https://github.com/vyallarishi/DependencyRefactoring.git
cd DependencyRefactoring
```

Your source of truth for what's wrong is `docs/LIT_REVIEW_AUDIT.md`, section "Appendix — bib entries that support these experiments and need fixing" (line ~325). It lists the specific errors. Don't trust it blindly either — it's one pass by one person, and if you find it wrong, that's a finding too.

---

## Task 1: fix the eleven broken entries

The appendix table names each key and its problem. For each one, find the actual paper, confirm the venue/year/authors/pages from a primary record (ACM DL, IEEE Xplore, ACL Anthology, Springer, or the arXiv abstract page — **not** a Google Scholar snippet, which is frequently wrong about venue), and correct the entry.

Two need more than a field edit:

- **`migrationbench2025`** is cited in the text as if it were library-to-library migration. It is actually Java 8→17/21 JDK migration. Either find a genuine library-migration benchmark to cite there (PyMigBench is the likely candidate) or flag the sentence for rewriting. Note which you did.
- **`libreuse2026`** appears to be a HuggingFace dataset with no paper behind it. If that's right, make it `@misc` with the URL and an access date. If you find an actual paper, even better.

## Task 2: verify every entry dated 2025 or 2026

Several entries claim 2026 venues. Some are real, some may be arXiv preprints that were written up as if accepted, and at least one may not exist in the form cited. For **every** entry with year ≥ 2025, record in `CITATION_VERIFICATION.md`:

| key | claimed venue | what you found | verdict |
|---|---|---|---|

with verdict one of: **confirmed** (primary record matches), **preprint only** (exists on arXiv, no venue — must be cited as `@misc`/`@article` with the arXiv id, not as a conference paper), **wrong venue** (fixed, say what it was), or **cannot find** (flag loudly — a citation nobody can locate is worse than no citation).

Be straightforward about the last category. If something cannot be found, say so plainly rather than guessing at a plausible venue; a fabricated-looking citation in a submission is far more damaging than a missing one.

## Task 3: add the missing papers

The appendix's "To add" list has ~24 entries. For each, create a correct bib entry — verified the same way as Task 2 — and in `CITATION_VERIFICATION.md` write **one sentence on what the paper actually shows** and **which of our claims it supports or contradicts**. That second part is the valuable bit: we need to know if any of these papers already did something we're claiming as new.

Flag immediately, in a separate section headed "Priority — affects our novelty claims", if any of these turn out to have done:
- manifest mutation (removing or altering dependency declarations to test a tool) — Shulepov 2608.27100 is the one we already know about
- a removal or dependency-debloating *benchmark* with execution-based grading
- detection of agents gaming a dependency-related benchmark

Those three would change what the paper can claim to be first at, so they matter more than the rest of the list combined.

## Task 4 (if time): cross-check the citation claims in the text

`paper/acl_latex.tex` cites these works in prose. For each `\citep`/`\citet`, check the sentence actually describes what the cited paper says. Report mismatches as a list of `line number → what the text claims → what the paper shows`. Don't edit the prose; just report, because the paper is being restructured and your edits would be lost.

---

## Ground rules

- **Only touch** `paper/custom.bib` and your new `docs/CITATION_VERIFICATION.md`. Do not edit `paper/acl_latex.tex` (being restructured), `code/harness/*`, or anything in `results/`.
- Keep bib keys stable where they already exist — changing a key breaks every `\cite` in the tex.
- `bibtex`/`biber` must still run clean after your changes. If you add a field a style doesn't know, it'll warn; check.
- Commit incrementally with the key names in the message, so we can see progress.
- Where you're unsure, write the uncertainty down rather than resolving it silently. "Could not confirm the ICML acceptance; arXiv only" is a useful note. A confident wrong venue is not.
