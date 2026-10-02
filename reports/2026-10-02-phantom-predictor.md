# Dependency-graph phantom predictor vs executed deletions (E6, dependency layer)

Predictor: for each declared dependency D of a gold-passing instance, D is predicted phantom if D lies in the
transitive requires-closure (PyPI `requires_dist`, extras-conditioned requirements ignored, depth 6) of the
other declared dependencies. No execution involved. Script: `scripts/graph/phantom_predict.py`.

Ground truth: the executed deletion mutants (run 36882143947 + re-run), with "phantom" = deletion passed CI
and the CI log shows the package was installed anyway (`scripts/gh/mechanism.py`).

| Measure | Value |
| --- | --- |
| Deletions with a prediction (gold-passing instances) | 233 |
| Predicted phantom | 73 |
| Executed phantoms | 91 |
| Predictor precision | 68 of 73 (0.93) |
| Predictor recall | 68 of 91 (0.75) |
| Predicted phantoms that CI nevertheless noticed | 2 |

Misses are mostly packages pulled in by tox or CI install lists rather than by declared dependencies, and
closure cut-offs from environment markers. Both are visible in the CI logs and could be added as a third
layer (the CI-declared layer) of the dependency graph.
