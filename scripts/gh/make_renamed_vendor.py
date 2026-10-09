#!/usr/bin/env python3
"""Construct the renamed-vendor set: vendor variants with every identifier renamed and comments stripped.

The named vendor variants copy the library verbatim, so a name check catches
some and a token comparison catches more. The question G3 must answer is
whether it still sees a copy when nothing textual survives but the structure:
every identifier mapped to a fresh name by a deterministic table, every
comment and docstring removed. This script builds that set from N vendor
variants of a corpus so the fingerprint check can be validated on it.

The renaming is applied to every NAME token that is not a keyword, including
attribute names and builtins, so the result is not runnable; the gate is
static and that is irrelevant to it. Keeping builtins would only make the copy
easier to detect.

usage: make_renamed_vendor.py --corpus DIR --out DIR [--n 20]
"""
from __future__ import annotations

import argparse
import io
import keyword
import pathlib
import re
import tokenize


def rename_source(src: str, table: dict[str, str]) -> str:
    out = []
    try:
        toks = list(tokenize.generate_tokens(io.StringIO(src).readline))
    except (tokenize.TokenError, IndentationError, SyntaxError):
        return src
    prev_sig = None          # previous significant token type, to spot docstrings
    for t in toks:
        tt, ts = t.type, t.string
        if tt == tokenize.COMMENT:
            continue
        if tt == tokenize.STRING and prev_sig in (None, tokenize.NEWLINE, tokenize.INDENT,
                                                   tokenize.DEDENT, tokenize.NL):
            ts = "0"          # a docstring becomes a bare constant
        if tt == tokenize.NAME and not keyword.iskeyword(ts):
            if ts not in table:
                table[ts] = "v%s" % _b36(len(table))
            ts = table[ts]
        if tt not in (tokenize.NL, tokenize.COMMENT, tokenize.ENCODING):
            prev_sig = tt
        out.append((tt, ts))
    return tokenize.untokenize(out)


def _b36(n: int) -> str:
    s = ""
    while True:
        n, r = divmod(n, 36)
        s = "0123456789abcdefghijklmnopqrstuvwxyz"[r] + s
        if not n:
            return s


def rename_patch(patch: str) -> str:
    """Rename inside every added .py file of a patch; other files pass through."""
    table: dict[str, str] = {}
    out, buf, cur_py = [], [], False

    def flush():
        if cur_py and buf:
            src = "\n".join(l[1:] for l in buf) + "\n"
            new = rename_source(src, table)
            out.extend("+" + l for l in new.splitlines())
        else:
            out.extend(buf)
        buf.clear()

    for line in patch.splitlines():
        if line.startswith("diff --git"):
            flush()
            m = re.search(r" b/(.+)$", line)
            cur_py = bool(m and m.group(1).endswith(".py"))
            out.append(line)
        elif line.startswith("+") and not line.startswith("+++"):
            buf.append(line)
        else:
            flush()
            out.append(line)
    flush()
    return "\n".join(out) + "\n"


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--corpus", required=True)
    ap.add_argument("--out", required=True)
    ap.add_argument("--n", type=int, default=20)
    a = ap.parse_args()
    dirs = sorted(p for p in pathlib.Path(a.corpus).iterdir()
                  if "__vendor__" in p.name and (p / "patch.diff").exists())[: a.n]
    for d in dirs:
        o = pathlib.Path(a.out) / d.name.replace("__vendor__", "__vendor_renamed__")
        o.mkdir(parents=True, exist_ok=True)
        (o / "patch.diff").write_text(rename_patch((d / "patch.diff").read_text(errors="replace")))
        print(" ", o.name)
    print(f"{len(dirs)} renamed vendor variants -> {a.out}")


if __name__ == "__main__":
    main()
