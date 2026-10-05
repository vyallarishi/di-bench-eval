#!/usr/bin/env python3
"""Install a generated module into a repository, idempotently.

Both the import blocker and the usage recorder work the same way: a generated
module must run in every interpreter the test suite starts. Two files achieve
that between them:

  sitecustomize.py   imported automatically at interpreter start, so it covers
                     subprocesses, tox and nox environments, and `python -c`
  conftest.py        imported by pytest before collection, which covers the
                     case where the project ships its own sitecustomize.py or
                     runs with `-S`

`conftest.py` often already exists and holds the project's fixtures, so the
generated code is spliced in between markers rather than appended. The markers
make the install **idempotent**: installing twice replaces the block instead of
stacking a second copy. That matters more than it sounds. Two stacked recorder
blocks mean two recorders with different output paths, the last one silently
winning, which is exactly the bug this module exists to prevent.

A stale `__pycache__/sitecustomize.*.pyc` can shadow a rewritten
sitecustomize.py, so it is removed too.
"""
from __future__ import annotations

import pathlib

MARK_BEGIN = "# >>> UnpinBench injected block (do not edit) >>>"
MARK_END = "# <<< UnpinBench injected block <<<"


def splice(path: pathlib.Path, body: str) -> None:
    """Write `body` into `path` between markers, replacing any previous block."""
    block = f"{MARK_BEGIN}\n{body.rstrip(chr(10))}\n{MARK_END}\n"
    if not path.exists():
        path.write_text(block)
        return
    old = path.read_text()
    if MARK_BEGIN in old and MARK_END in old:
        pre, rest = old.split(MARK_BEGIN, 1)
        _stale, post = rest.split(MARK_END, 1)
        path.write_text(pre + block + post.lstrip("\n"))
    else:
        path.write_text(block + "\n" + old)


def install(root: pathlib.Path, body: str) -> list[str]:
    """Install `body` as sitecustomize.py and conftest.py under `root`."""
    for name in ("sitecustomize.py", "conftest.py"):
        splice(root / name, body)
    cache = root / "__pycache__"
    if cache.is_dir():
        for pyc in cache.glob("sitecustomize.*"):
            pyc.unlink()
    return ["sitecustomize.py", "conftest.py"]


def uninstall(root: pathlib.Path) -> list[str]:
    """Remove injected blocks, deleting files that held nothing else."""
    removed = []
    for name in ("sitecustomize.py", "conftest.py"):
        p = root / name
        if not p.exists():
            continue
        old = p.read_text()
        if MARK_BEGIN not in old:
            continue
        pre, rest = old.split(MARK_BEGIN, 1)
        _b, post = rest.split(MARK_END, 1)
        rest_text = (pre + post).strip()
        if rest_text:
            p.write_text(pre + post.lstrip("\n"))
        else:
            p.unlink()
        removed.append(name)
    return removed
