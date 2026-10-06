# What the 226 blind spots actually are

A blind spot is a pair where the declaration was removed, the package was made
unimportable from the repository's own frames, and CI still passed. Reporting
that as one number invites the obvious objection — *maybe those dependencies
simply were not needed* — and the objection is partly right. The population
decomposes, and the decomposition is a better result than the aggregate.

| Category | n | What it means |
|---|---|---|
| **Over-declared** | 149 | No textual trace of the package anywhere in the repository — not imported, not named in any config or workflow. The declaration is simply wrong. |
| **Used without importing** | 23 | Named in config or CI but never imported: a pytest plugin, a console-script entry point, a build backend, a tool the workflow invokes. |
| **Imported, unguarded, untested** | 46 | The code imports it directly, nothing guards the import, and no test exercises that path. **This is oracle blindness in the strict sense.** |
| **Optional by design** | 8 | Every import sits inside `try/except ImportError` with a working fallback (5 pairs), or some do (3). Removing the package is *supposed* to be survivable. |

## Why this matters for the claim

Only the third row is the failure the paper is about: the repository genuinely
needs the package on some path, and the test suite does not cover that path.
**46 of 226.**

The other three rows are real findings but different ones:

- *Over-declaration* (149) is the dependency-bloat result the debloating
  literature already documents, now measured on a benchmark's own instances.
  It is evidence that manifests are noisy, not that oracles are blind.
- *Used without importing* (23) is a limitation of every import-graph-based
  tool, ours included: a static analyser reasoning over imports cannot see
  these, and neither can a reviewer who only reads code.
- *Optional by design* (8) is not a failure at all. `eliot` wraps
  `from orjson import dumps` in `try/except ImportError` and falls back to
  `json.dumps`. CI passing without `orjson` is correct behaviour.

## Consequences we must act on

1. **Do not report 226 as "oracle blindness".** Report the decomposition. The
   strict figure is 46, with the rest named.
2. **The optional-by-design pairs must leave the benchmark.** A task whose
   dependency is explicitly optional has no correct removal to perform — the
   code already handles its absence. Eight pairs, to be excluded with this
   reason recorded.
3. **The page-1 figure must come from the 46.** `eliot/orjson` was the first
   candidate and is exactly the wrong one: a reviewer who opens that file sees
   the `try/except` immediately and stops trusting the paper.
4. **The "used without importing" row is a limitation to state**, not to fix.
   It bounds what any static predictor built on imports can achieve, and we
   should say so before a reviewer does.

## How this was measured

`footprint.py` for the import sites; an AST pass marking every import that
falls inside a `try` whose handler names `ImportError` or `ModuleNotFoundError`;
a textual search of `*.cfg`, `*.toml`, `*.ini` and `.github/workflows/*` for the
package name and its spelling variants. The last is deliberately generous — a
package named anywhere in configuration counts as "possibly used" — so 149
over-declared is a *lower* bound on manifest noise and 23 an upper bound on
non-import use.

## Hand-verification of the optional-by-design pairs

The AST pass only checks that an import lies textually inside a `try` with an
`ImportError` handler; it cannot tell whether the fallback actually works. Four
of the pairs were therefore read directly, and all four have a real fallback:

| Pair | Fallback |
|---|---|
| `AppDaemon_appdaemon` / `pid` | `except ImportError: pid = None` |
| `AppDaemon_appdaemon` / `uvloop` | `except ImportError: uvloop = None` |
| `aws_chalice` / `typing_extensions` | tries `typing.TypedDict` first, falls back *to* the package |
| `gpiozero_gpiozero` / `importlib_resources` | `except ImportError: from importlib import resources` |

The pattern is consistent: backports (`typing_extensions`,
`importlib_resources`) declared for older interpreters, and optional
accelerators or niceties (`uvloop`, `pid`, `orjson`) the code runs without.
`aws_chalice` is the clearest case — the package is the *fallback*, not the
primary path, so on a modern interpreter it is never imported at all.

The remaining four should be read before the exclusion is finalised, but the
category is confirmed.
