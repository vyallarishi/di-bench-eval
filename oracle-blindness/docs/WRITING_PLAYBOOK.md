# Writing playbook: what strong papers in our genre actually do

A reading of the papers our submission will be compared against, for structure and rhetoric rather than content. Sources at the bottom. Our paper sits between three genres, and the reviewer pool is drawn from all three:

- **benchmark critique** — SWE-Bench+, The SWE-Bench Illusion, ABC
- **oracle strengthening** — STING, PatchDiff, the APR patch-correctness line
- **benchmark contribution** — DI-Bench itself, which we both extend and attack

---

## 1. The single most important finding: DI-Bench states our target premise outright

From the DI-Bench paper (Findings of ACL 2025), §5 Metrics:

> "Whether the tests pass is the most direct and reliable indicator of the correctness of the generated dependencies."

And its Limitations section, item ❸, *anticipates our result and dismisses it*:

> "Test coverage for each repository may not be exhaustive, meaning some test cases might not encompass every possible code path. However, as the tests were developed by project contributors, the results are expected to reflect practical settings accurately."

This is the ideal setup. We are not inventing a concern; we are **measuring a concern the authors raised and set aside**, and showing the expectation is false in roughly half of cases. Our paper should quote this limitation verbatim early — it establishes that the question is legitimate, pre-empts "nobody thought tests were perfect", and makes the contribution empirical rather than rhetorical.

Note also what DI-Bench does *not* do, which we verified by reading: **nowhere does it discuss over-declaration, transitive installs satisfying a missing declaration, or any false positive of the execution oracle.** That gap is ours to fill.

## 2. Use the ABC vocabulary — it gives reviewers a frame they already accept

"Establishing Best Practices for Building Rigorous Agentic Benchmarks" (NeurIPS) introduces the **Agentic Benchmark Checklist**, with three axes and 43 items:

- **Task Validity** (10 items): a task is solvable *iff* the agent has the target capability. Violations are false positives (shortcuts) or false negatives (impossible tasks).
- **Outcome Validity** (20 items): the grade truly indicates task success.
- **Benchmark Reporting** (13 items): reproducibility, and *quantitative* disclosure of known flaws.

Applied to ten widely used benchmarks: **7 had Task Validity flaws, 7 had Outcome Validity flaws, and all 10 had reporting gaps.** SWE-bench Verified is named for "insufficient test coverage" with overestimation ~100% relative; TAU-bench counted inaction as success (38% trivial success).

**How we use this.** Our two contributions map exactly onto their two axes, and we should say so in the introduction:

| Our contribution | ABC axis |
|---|---|
| Deletions CI never notices | an **Outcome Validity** failure, measured |
| Unwinnable pairs excluded by frame origin; reference removals | **Task Validity**, established |
| Eight-gate grader | an **Outcome Validity** fix |
| Construction funnel + `excluded.jsonl` + audit report | **Benchmark Reporting**, satisfied |

Their reporting axis also *demands* what we already have: quantitative disclosure of known flaws, pre- and post-mitigation numbers. Our audit report is an asset, not an embarrassment — it is literally what the checklist asks for, and almost no benchmark paper ships one.

## 3. STING is our nearest sibling — differentiate explicitly or a reviewer will

STING (arXiv 2604.01518) does mutation-reveals-weak-oracle on SWE-bench Verified: generate semantically altered program variants, see which survive the tests, then generate tests to kill the survivors. 77% of instances had a surviving variant; agent resolve rates dropped 4.2–9.0 points.

The logic is *the same shape as ours*. The differences we must state plainly, probably in a paragraph of Related Work and again in the intro:

1. **What is mutated.** STING mutates *program code*; we mutate the *dependency declaration*. Theirs is a classic mutation operator; ours changes the environment the code runs in, which no mutation-testing tool models.
2. **The oracle problem.** STING must *synthesise* tests to kill survivors, and so inherits the question of whether a generated test encodes intent. We don't synthesise anything: **the removed library is itself the reference**, running, with recordable behaviour. This is the sentence our paper turns on.
3. **Failure mode discovered.** STING finds weak assertions. We find a failure that is not about assertion strength at all — the *phantom install*, where the package is still importable because another dependency pulls it in. No amount of test strengthening fixes that; it is an environment-isolation problem.

Point 3 is our strongest differentiator. Lead with it.

## 4. PatchDiff shows how to claim novelty honestly for a composed technique

PatchDiff (ICSE 2026) uses differential testing between a candidate patch and the developer's oracle patch; 29.6% of plausible SWE-bench patches diverge behaviourally, ~11% estimated incorrect, inflating resolution rates by 6.4 points.

Their novelty sentence claims **application, not mechanism** — differential testing targeted at patches. They are explicit that 66.2% of suspicious patches have *uncertain* correctness because requirements are under-specified, and they defend the approach on the grounds that divergence is concrete evidence and manual inspection gets cheaper.

**For us this is both a template and an advantage.** Same honest framing ("every component exists; the composition and the oracle observation are ours"), but we are strictly better placed on their weakest point: they compare against a *human patch that may itself be wrong*, whereas we compare against *the library that was actually there*. Say that, once, without gloating.

## 5. Structural template, synthesised

What the four papers share, and what we should adopt:

**Abstract ordering** (SWE-Bench+, STING, PatchDiff are identical in shape): establish the standard practice → name the presupposition it rests on → say the presupposition fails → quantify → state the downstream effect on reported numbers → name the artifact.

STING's first three sentences are the cleanest model in the set:

> "Benchmarks driven by test suites, notably SWE-bench, have become the de facto standard... In practice, however, insufficiently strong test suites can admit plausible yet semantically incorrect patches, inflating reported success rates. We introduce STING, a framework for..."

**Introduction, paragraph by paragraph** (composite of SWE-Bench+ and STING):

1. The domain and why evaluation matters.
2. The benchmark and its adoption — *establish its legitimacy before questioning it*. Both critique papers do this, and it is why they read as science rather than polemic.
3. The presupposition, named explicitly. STING: "The reliability of this protocol, however, hinges on a key presupposition: that the regression tests encode the intended behavior of the fix with sufficient completeness."
4. The rhetorical question. SWE-Bench+: "However, are the LLMs actually resolving the issues in SWE-bench?" Ours is close to: *does a passing test suite tell you a dependency is gone?*
5. A worked example, with a figure, on page 1 or 2. STING's Figure 1 shows oracle patch vs. plausible patch vs. the test that should have caught it. **We need this and don't have it yet** — one real instance where a dependency is deleted and CI stays green, with the phantom install visible.
6. What we did, in two or three sentences.
7. Findings, with numbers in the prose.
8. Contributions as a bulleted list, **on page 2 at the latest** (the systems-writing advice is unanimous and reviewers complain loudly when it is later).

**Research questions.** STING numbers them (RQ1–RQ4) and uses them as results-section titles verbatim; SWE-Bench+ uses one rhetorical question and no numbered RQs. Numbered RQs suit us because we have four distinct measurements, and ACL reviewers read them as organisation rather than padding.

**Threats/limitations.** Non-negotiable for us: **ACL requires a section titled "Limitations", after the conclusion, outside the page limit, and papers without one are rejected without review.** Note that neither SWE-Bench+ nor The SWE-Bench Illusion has a real limitations section — the Illusion paper has none at all, which is a weakness we should not copy. STING has a proper Threats to Validity section. Ours should be the strongest in the set, because we have an independent audit to draw on: the honest statement that winnability is demonstrated for a sample and verified-by-rule for the rest belongs there, stated plainly, with the number.

## 6. How to handle the "unrealistic mutants" objection

This objection is coming, and STING shows the accepted answer: a layered filter plus an explicit conservatism argument.

> "Residual equivalent variants may remain, but they would primarily make our test-weakness analysis more conservative."

**Our version is stronger and we should make it loudly**: our mutation is not synthetic at all. Deleting a dependency declaration is an operation developers perform constantly — the debloating literature documents it (PyTrim: 39 of 971 packages had removable bloat, 6 PRs merged; the Bloat beneath Python's Scales study got 30 of 36 PRs merged removing 35 dependencies). We are not asking "what if someone made this edit"; we are asking "what happens when someone makes *the* edit the ecosystem is actively making".

The precedent also means we must cite the debloating line carefully and *not* claim to be first at dependency removal as a task. There is a May 2026 study, "Dependency Debloating in Python: How Developers Do It and How Well Tools Support It" (artifact on Zenodo, full text restricted) that is close to our task framing — **Aman or whoever picks up the bibliography must get the full text and check it for overlap before we claim anything about removal as a task.** From the artifact page it appears to be a developer-behaviour study with tool evaluation, not an agent benchmark with an execution oracle, but that must be confirmed rather than assumed.

## 7. Diplomatic phrasing that works

Collected verbatim, for reuse:

- Position as completing, not demolishing: "However, a systematic evaluation of the quality of SWE-bench remains missing. In this paper, we addressed this gap."
- Acknowledge intent while identifying the oversight: variants "address limitations in existing benchmarks, however neither addresses [the specific problem], which was the primary motivation for our study."
- Frame as protecting credibility, not attacking it (the Illusion paper's stance throughout): diagnostics exist to make the benchmark trustworthy.
- The Illusion paper's conclusion recommends changes to *practice* (temporal controls, cross-repo validation) rather than abandoning the benchmark.

For us: DI-Bench's contribution is real and we build on it directly — we use their repositories, their harness, their CI replay. The paper should say so without hedging. Our finding is about the **oracle**, which is a property of the task, not a mistake by its authors; the same oracle underlies every execution-graded dependency benchmark. That framing is both true and much more publishable than "DI-Bench is broken".

## 7b. Controlled perturbation as a diagnostic: a method precedent

Li et al., *LLMs Can Easily Learn to Reason from Demonstrations* (arXiv 2502.07374)
is not a comparison paper -- different genre entirely, reasoning distillation
rather than benchmark validity -- but its **method** is the same shape as ours
and is worth citing as precedent for the design.

They perturb training data along two axes and measure which the system is
actually sensitive to. *Content* perturbations (wrong final answers, corrupted
digits, removed reasoning keywords) barely move performance: training on
entirely wrong answers costs 3.2%. *Structural* perturbations (shuffling,
inserting, deleting reasoning steps) degrade it sharply. The conclusion is
drawn from what the system fails to notice.

That is our logic. We perturb a repository and measure whether the oracle
notices. Three things to borrow:

**The two-axis framing.** Theirs is content vs. structure. Ours is naturally
*declaration-level* (remove the declaration; a phantom install leaves the
package importable) vs. *environment-level* (remove it and block the import).
We have been describing these as two screening mechanisms, which is accurate
but flat. Framing them as a perturbation taxonomy is cleaner and makes the
phantom/blind-spot split fall out of the design rather than arrive as an
afterthought.

**Dose-response, not a binary.** They perturb at 20/50/67/100% and show the
trend, which is far harder to dismiss than a single number. The analogue here
is removing 1, 2, 3, N dependencies at once and plotting detection against
dose. We currently report one binary per pair. This is cheap to add and would
turn a number into a curve.

**The negative control earns the headline.** Their 100%-digit-corruption row
collapses to 2.7%, which proves the setup *can* register catastrophic damage --
so robustness at 70% is a finding rather than a broken measurement. Our
gold-baseline check plays exactly this role and should be presented the same
way: here is the condition under which the oracle does fire, therefore its
silence elsewhere means something. Given how many of our own harness bugs
produced plausible-looking silence, this is not a rhetorical nicety.

Cite for the method. Do not cite as a venue model or put it in the Related Work
core.

## 8. What we are missing, concretely

From this reading, the gaps between what we have and what a strong submission needs:

1. **A page-1 worked example figure.** Every strong paper in the set has one. Pick the most legible phantom-install case and show: the manifest with the dependency deleted, the CI log still green, and the transitive path that kept the package importable.
2. **Numbered RQs** that the results sections are titled with.
3. **A construction funnel table** — candidates → gold-passing → screened → attributable → pool, with every exclusion counted. ABC's reporting axis asks for this and almost nobody provides it.
4. **The Limitations section**, treated as a feature. Winnability sampled, not proven, with the number.
5. **An explicit differentiation paragraph vs. STING, PatchDiff and the debloating line**, in Related Work *and* compressed into one sentence in the intro.
6. **The one-sentence key insight**, stated on page 1 and never restated differently. Current best form: *in a removal task the removed library is a canonical oracle — the one artifact every other repository-change benchmark lacks.*

---

## Sources

- DI-Bench — Findings of ACL 2025, `aclanthology.org/2025.findings-acl.528`, arXiv 2501.13699
- SWE-Bench+ — arXiv 2410.06992
- The SWE-Bench Illusion — arXiv 2506.12286
- STING, *Are Benchmark Tests Strong Enough?* — arXiv 2604.01518
- PatchDiff, *Are "Solved Issues" in SWE-bench Really Solved Correctly?* — arXiv 2503.15223, ICSE 2026
- Establishing Best Practices for Building Rigorous Agentic Benchmarks (ABC) — arXiv 2507.02825, NeurIPS
- PyTrim — arXiv 2510.00674, ASE 2025
- Bloat beneath Python's Scales — TOSEM, `dl.acm.org/doi/10.1145/3660821`
- Dependency Debloating in Python: How Developers Do It — Zenodo 20274119 (full text restricted; **must be checked**)
- EACL/ACL 2026 call for papers — mandatory Limitations section
- Li, Cao, Griggs et al. *LLMs Can Easily Learn to Reason from Demonstrations* — arXiv 2502.07374 (method precedent for controlled perturbation; not a comparison paper)
