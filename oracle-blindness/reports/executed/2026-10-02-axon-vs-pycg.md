# Axon vs PyCG call graphs on two repositories (E6 prerequisite)

Axon run through its ingestion pipeline directly (`run_pipeline`, no embeddings, no CLI); PyCG from GitHub
source with a patch for a positional-only-defaults crash and `--max-iter 3`. Script: `scripts/graph/axon_dump.py`.

| Repository | Axon call edges | PyCG internal call edges | Edge overlap (Jaccard) | Shared nodes | Test-reachability agreement on shared nodes |
| --- | --- | --- | --- | --- | --- |
| inducer_cgen | 99 | 310 | 1 (0.002) | 8 | 1.00 |
| your-tools_tbump | 390 | 292 | 138 (0.254) | 109 | 0.99 |

Reading. Axon names callees without their class (`cgen.Constant`) where PyCG names methods fully
(`cgen.AlignValueAttribute.get_decl_pair`), so most cgen edges cannot be matched by name; on tbump, where
functions are module-level, a quarter of edges match and the two tools agree almost perfectly on which
shared nodes a test can reach. Axon models no external symbols: its IMPORTS edges point at internal modules
only, while PyCG records calls into third-party and stdlib symbols. Consequence for the paper: use PyCG for
anything symbol-level that involves third-party APIs (used API surface, external reachability), and treat
Axon as a fast internal-structure graph (0.6 to 0.8 s per repo versus 2 to 240 s for PyCG, which hangs on
some repositories).
