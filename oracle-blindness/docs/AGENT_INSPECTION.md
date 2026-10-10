# Reading all nineteen: what the submissions CI accepted actually do

The grader's verdict on the nineteen submissions that pass CI is 1 accepted,
7 rejected, 11 inconclusive. "Inconclusive" is honest but uninformative, and a
reviewer will ask the obvious question: are those eleven plausible rewrites the
gate could not reach, or submissions that never attempted the task? That cannot
be answered from gate verdicts, so every one of the nineteen diffs was read.

**Scope and provenance.** This is a reading of the diffs, performed by the same
automated session that produced and graded them, with each claim tied to what
is in the patch (quoted below) rather than to a judgement about intent. It is
not independent human review. An author should spot-check at least the five
marked **[substitution not equivalent]**, since those are the judgements a
reviewer is most likely to contest.

## The nineteen, by what the diff does

### Correct removals (3)

| pair | what it does |
|---|---|
| `IAMActionHunter` / `pandas` | DataFrame CSV append rewritten with `csv.DictWriter`, header-on-create preserved. **The only one checked against behaviour**: recording existed, usage-site comparison identical. |
| `tplot` / `colorama` | drops `colorama.init()`, the Windows ANSI shim. Behaviour on Linux CI is unchanged; this is the narrowing the hand-written reference for the same pair also made and documented. |
| `bepasty-server` / `xstatic_asciinema_player` | removes one entry from a list of XStatic package names. The dependency supplies a static asset bundle; deleting the name is the removal. |

### Correct but near-trivial: the indirect track (1)

| pair | what it does |
|---|---|
| `bofhound` / `impacket` | manifest only. **The pool records 0 importing files** for this pair: the package is reached through a tool, so deleting the declaration *is* the whole task. Correct, and not comparable to a rewrite. |

### Real rewrites, unverifiable (4)

Substantial reimplementations. CI passes, no recording exists, so the
behavioural gate cannot confirm them and does not pretend to.

| pair | size | what it does |
|---|---|---|
| `cowrie` / `tftpy` | 178 lines | TFTP download reimplemented on Twisted's reactor and protocols |
| `pyTelegramBotAPI` / `requests` | 188 lines | HTTP layer reimplemented on `urllib.request`, with the exception types aliased |
| `humanlayer` / `python_dotenv` | 903 lines, 23 files | a `.env` parser inlined into every example that used `load_dotenv` |
| `eliot` / `boltons` | 36 lines | `boltons.funcutils.wraps` replaced by `functools.wraps` |

### Substitution not equivalent (4)

The finding reading produced that gate verdicts did not. Each passes CI, each
leaves the repository doing something materially different from what the
library did. **None is caught by any gate**, because no recording exists for
the pair; all four are in the "inconclusive" bucket.

| pair | what the diff does | what is lost |
|---|---|---|
| `tda-api` / `authlib` | **two lines**: `from httpx import AsyncClient as AsyncOAuth2Client, Client as OAuth2Client` | an `httpx.Client` is not an OAuth2 client. Token refresh, the authorisation flow, and auth headers are gone; the name is preserved so the call sites compile and the mocked tests pass. |
| `pyrogram` / `pysocks` | proxy branch replaced by `raise RuntimeError("Proxy support requires the 'pysocks' extra…")` | the proxy feature is deleted rather than reimplemented, and says so in its own message |
| `tda-api` / `autopep8` | `autopep8.fix_code(...)` replaced by the unformatted string | generated code is no longer formatted; the tests do not assert on formatting |
| `chalice` / `inquirer` | `inquirer` prompts replaced with `click.prompt` | plausible, but the interactive list-selection contract differs; untested either way |

`tda-api` / `authlib` is the strongest single example in the run — stronger than
the `django` case, because the submission looks like a rewrite. Two lines, an
alias that preserves the name, the library's entire purpose discarded, and a
green suite.

### Rejected, and the rejections are correct (7)

Each was re-derived from the patch rather than trusted from the gate output.

| pair | gates | verified by reading |
|---|---|---|
| `django-cookie-consent` / `django` | G1, G5, G8 | the patch **re-declares `django`** and changes nothing else. Confirmed by applying it: declared set before and after are identical. |
| `openant` / `pyusb` | G1, G8 | 183 lines of real code, but **`pyproject.toml` is never touched** — `pyusb` stays declared — and `import usb.core` is moved into function bodies, so the dependency is still used, lazily. |
| `nbmake` / `pytest` | G5, G7 | **16 test functions deleted, 1 added.** Not a mock repoint: the suite is dismantled. The package also stays installed. |
| `flashbax` / `jaxlib` | G5 | manifest only; `jax` is added back and pulls `jaxlib` transitively |
| `swirl-search` / `certifi` | G5 | writes a 171-line pinned `requirements.txt`; `certifi` still arrives |
| `yapf` / `tomli` | G5 | sound code change, but the package still arrives in the environment |
| `appdaemon` / `aiohttp` | G5 | as above |

## What this changes

**The eleven inconclusive verdicts are not eleven unknowns.** Reading them
gives 3 correct removals, 1 correct-but-trivial, 4 real-but-unverifiable
rewrites, and **4 non-equivalent substitutions that every gate accepts**. The
last group is the paper's result strengthened, not weakened: the structural
gates catch submissions that never removed the dependency, and reading shows a
second, harder class — submissions that remove the dependency and silently drop
what it did — which only a behavioural comparison could catch and which our
coverage does not reach.

**No gate verdict was wrong.** All 7 rejections were re-derived from the
patches. G1 on `openant` looked like a candidate false rejection (183 lines of
genuine work) and is correct: the manifest was never edited. The one acceptance
is sound on inspection as well as on the trace.

**The honest count for RQ5.** Of 19 submissions a test-based oracle accepts,
reading finds **4 correct** (one of them trivial), **4 plausible but
unverifiable**, **4 not behaviourally equivalent**, and **7 rejected** — 3 that
never removed the dependency and 4 where it still arrives in the environment.
The groups partition the nineteen exactly: 4 + 4 + 4 + 7 = 19. A benchmark
reporting 19/100 would be crediting at most 4, and 4 more are unknown.

Two of the seven rejections are also substantial code changes (`yapf` / `tomli`
moves TOML reading to `tomllib` correctly; `appdaemon` / `aiohttp` reworks 154
lines of websocket handling). They are rejected because the package still
arrives in the environment, not because the code is wrong, and that distinction
belongs in the paper: G5 rejects a submission whose *code* may be a sound
removal but whose *environment* is unchanged.
