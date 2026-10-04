# Static predictors of CI-invisible deletions vs executed ground truth (E6)

Ground truth: 233 executed deletion mutants on gold-passing DI-Bench Python instances (115 invisible to CI).
Predictors need no execution: PyPI `requires_dist` closure (dependency layer, `scripts/graph/phantom_predict.py`)
and file-level test reachability of import statements (code layer, `analyze_python.py` per-dep output).

| Predictor | Predicted | Precision | Recall |
| --- | --- | --- | --- |
| Dependency layer only (D in closure of the other declared deps) | 73 | 71/73 = 0.97 | 71/115 = 0.62 |
| Code layer only, file level (no test reaches a file importing D) | 70 | 48/70 = 0.69 | 48/115 = 0.42 |
| Combined (either) | 118 | 95/118 = 0.81 | 95/115 = 0.83 |

Symbol level (PyCG, 18 of 51 repos analysable, 45 deletions): not-test-reachable precision 9/19 = 0.47, recall 9/14 = 0.64;
combined with the dependency layer 12/22 = 0.55 precision, 12/14 = 0.86 recall. Used-API-surface 0: invisible 4/5; surface 1: 5/17.
