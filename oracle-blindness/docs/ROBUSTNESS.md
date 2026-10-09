# "Your blind spots are just badly-maintained repositories"

This is the strongest objection to the blindness result, and it deserves a
measured answer rather than an assurance. Four checks, all on the existing data.

## 1. The result is not carried by outliers

One repository, `swirlai_swirl-search`, declares 172 dependencies and supplies
126 of the 239 blind spots. If the finding rested on it, dropping it would move
the number. It does not.

Dropping the *k* most-blind repositories entirely and recomputing:

| Dropped | Repos left | Median rate | Incidence |
|---|---|---|---|
| 0 | 51 | 20.0% | 35 / 51 |
| 1 | 50 | 20.0% | 34 / 50 |
| 3 | 48 | 19.4% | 32 / 48 |
| 5 | 46 | 17.7% | 30 / 46 |
| **10** | **41** | **14.3%** | **25 / 41** |

Removing the ten worst offenders — a fifth of the population, chosen
adversarially — leaves a median of 14.3% and leaves 61% of the remaining
repositories still affected. The effect is distributed, not concentrated.

## 2. The distribution is broad, not bimodal

Across the 51 repositories with at least three candidates:

| Rate | Repositories |
|---|---|
| 0% | 16 |
| 1–10% | 1 |
| 10–25% | 9 |
| 25–50% | 18 |
| over 50% | 7 |

The largest single bucket is 25–50%. This is not a handful of broken projects
dragging an otherwise clean population: it is a spread, with a substantial mode
well away from zero.

## 3. It happens in projects nobody would call badly maintained

| Project | Blind | Of | Rate |
|---|---|---|---|
| `cowrie/cowrie` | 11 | 12 | 92% |
| `tweepy/tweepy` | 2 | 3 | 67% |
| `aws/chalice` | 3 | 7 | 43% |
| `localstack/localstack` | 6 | 15 | 40% |
| `openvinotoolkit/nncf` | 6 | 16 | 38% |
| `NVIDIA/NVFlare` | 5 | 18 | 28% |
| `google-deepmind/dm-haiku` | 1 | 4 | 25% |
| `docker/docker-py` | 1 | 3 | 33% |

**11 of 12** widely-used, actively-maintained projects in the population have at
least one dependency they can lose without their own CI noticing. These are
AWS, NVIDIA, DeepMind and Docker repositories, not abandoned side projects.

## 4. It tracks test coverage, which is the point

Blindness correlates negatively with how much of a repository its tests reach:

| Against | Correlation |
|---|---|
| Share of files that are tests | **−0.34** |
| Share of files reachable from tests | **−0.31** |
| Number of declared dependencies | +0.34 |
| Repository size | +0.11 |

Better-tested repositories are less blind. That is exactly what the mechanism
predicts — the oracle notices a removal only when a test reaches the code that
uses it — and it is the opposite of what a measurement artifact would look like.

Sixteen repositories have **no** blind dependencies at all, which also rules out
the reading that this is universal or inevitable.

## What this licenses, and what it does not

Licensed: *a dependency that CI cannot see is common across the population,
survives adversarial removal of the worst cases, appears in projects maintained
by major organisations, and is more frequent where test coverage is thinner.*

Not licensed: a claim about Python repositories in general. The population is
DI-Bench's, selected for having runnable CI, which is already a quality filter —
and one that biases *against* us, since repositories with working CI are better
engineered than average. The honest reading is that the figure is, if anything,
conservative.
