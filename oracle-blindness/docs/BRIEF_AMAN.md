# Brief: Aman — get the benchmark to a state nobody can attack

## What this is about

We have a benchmark of **355 (repository, dependency) pairs**. Each one is a task: remove that dependency from that repository and keep its tests passing. An independent adversarial audit checked everything about this benchmark that could be checked mechanically, and it all held up. One thing it could not establish, and that one thing is the only opening a reviewer has.

**The open question: is every pair actually solvable?**

We believe each pair is solvable, because a rule says so. For five of them somebody actually sat down, removed the dependency, and got the tests passing. For the other 350 nobody has. The audit sampled 36 pairs by reading them and found **two that are genuinely impossible** — no edit to the repository could ever make them pass. Two in 36 means there are almost certainly more hiding in the 355.

An impossible task in a published benchmark is the kind of thing that sinks a paper. A reviewer finds one, and from that point on they disbelieve everything else we claim.

**Your job: close that question, so we can stop worrying about the benchmark and put all our effort into the grader.**

## What success looks like

When you are finished, we should be able to say this and have it be true:

> Every pair in this benchmark has been checked by a human. Pairs that are impossible have been removed, and we can say exactly which and why.

That is the whole goal. Nothing in this brief matters more than that sentence being honest.

Concretely, by the end we need:

1. **A verdict on every one of the 355 pairs**, with your reasoning recorded for each. Solvable, impossible, or genuinely uncertain. "Uncertain" is an acceptable verdict as long as it's rare and you say what you'd need in order to decide.

2. **The impossible pairs identified and justified.** This is the most valuable thing you will produce. Each one needs enough evidence that we can remove it from the benchmark and defend the removal if asked. If you find twenty, that's twenty attacks a reviewer can no longer make.

3. **Some pairs proven solvable by actually solving them.** Where it's feasible, there is no substitute for having removed the dependency for real and seen the tests pass. These also become the ground truth the grader is measured against, so they're doing double duty. More is better; how many is realistic is partly for you to find out.

4. **An honest account of your own coverage.** For each pair: did you decide this by reading, by reasoning, or by actually doing it? Those are different strengths of evidence and the paper has to report them separately rather than blur them.

5. **Anything about the benchmark that looks wrong.** You will be the first person to look at all of these closely. If a pair is mislabelled, if our recorded information about it is inaccurate, if something seems off — tell us. Don't fix it, just report it clearly enough to act on.

## How much of this needs to be done by hand

Our honest expectation is that **most of this is manual work.** Reading a repository, working out what a dependency is actually doing there, and judging whether it can be removed is a human judgement, and the audit's experience suggests there is no shortcut for the hard cases.

That said — **if you find a faster or more reliable way to establish any part of it, that is strictly better, and we want to hear about it.** If something can be decided mechanically with confidence, decide it mechanically and tell us how, so we can state it in the paper as a property rather than a sample. A method that lets us cover more pairs with more confidence is worth more than the pairs themselves. Just don't let a shortcut quietly lower the standard: anything decided automatically still has to be something we'd defend to a sceptical reader.

## What you're working with

**Repository: `https://github.com/vyallarishi/DependencyRefactoring`**

```bash
git clone https://github.com/vyallarishi/DependencyRefactoring.git
cd DependencyRefactoring
```

- `benchmark/instances.jsonl` — the 355 pairs, with what we know about each
- `docs/BENCHMARK_AUDIT_REPORT.md` — **read this first.** The independent audit. It tells you what has already been checked, names the two impossible pairs it found, and flags several more as suspicious. Blunt and specific.
- `docs/REFERENCE_SOLUTIONS_PROMPT.md` — the rules a removal has to satisfy to count as solved. Those rules are not negotiable; they're what stops a "solution" from being a cheat.
- `code/harness/` — our tooling, including the mechanism that makes a dependency genuinely unimportable so you can tell a real removal from an apparent one.
- `benchmark/patches/` — for each pair, exactly what we did to it.

Rishi is also producing reference solutions in a parallel session. Coordinate through `references/CLAIMS.md` so you don't duplicate each other.

## Things worth knowing before you start

- **The audit already found two impossible pairs** (`jazzband_django-revproxy / urllib3` and `mu-editor_mu / virtualenv`) and flagged four more as very hard. Those six are a sensible place to begin: confirming or overturning them is immediately useful either way, and it will calibrate you on what "impossible" looks like here.
- **The riskiest pairs are the ones where the repository's own tests use the dependency**, because then removing it collides with tests we are not allowed to weaken. There are 112 of those. The audit expects most remaining impossible pairs to be in that group.
- **40 pairs have no visible use of the dependency anywhere in the code.** Those are strange by definition and deserve suspicion.
- **Our tooling has had real bugs**, including one that made a check silently do nothing while appearing to work. If something looks too easy or a result seems impossible, distrust it and say so. We would much rather hear "this doesn't add up" than get a clean report built on a broken measurement.

## Ground rules

- **Don't change the benchmark.** Not `benchmark/instances.jsonl`, not the harness code, not existing results. We are actively measuring against them and a change mid-flight invalidates the measurements. Report, don't repair.
- **Write things down as you go, and push often.** Partial work that's visible is worth far more than complete work that isn't. If you decide something about a pair, record it immediately — a verdict you remember but didn't write down is lost.
- **Never stretch a pair to make it work.** If the only way to pass the tests is to weaken a test, swap in a different package, or copy the library's code, the pair is impossible and that's the finding. Reporting it is the win, not a failure.
- **Record uncertainty as uncertainty.** "I think this is solvable but the way the tests mock this dependency worries me" is genuinely useful. A confident wrong verdict that leaves an impossible task in a published benchmark is the single worst outcome here.
- **Say when something defeats you for a boring reason.** The environment won't build, the suite needs a database, it takes an hour to run. That's not failure, it's information, and we need it recorded rather than silently skipped.

## Why this matters

Everything else in the paper is in reasonable shape. The measurement half is done and the grader is being built now. This is the one piece standing between us and being able to say the benchmark is sound — and it's the piece a reviewer will go after first, because it's the one we currently can't fully defend.

If you get this done, the benchmark stops being a risk and becomes the thing the paper is built on.
