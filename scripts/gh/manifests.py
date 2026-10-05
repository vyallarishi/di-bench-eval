#!/usr/bin/env python3
"""Read and edit Python dependency manifests in every format DI-Bench uses.

Four formats appear across the regular and large subsets:

  pyproject.toml   PEP 621 `[project] dependencies` or `[tool.poetry.dependencies]`
  requirements.txt one requirement per line, `#` comments, `-r`/`-e` directives
  setup.py         `install_requires=[...]` inside the `setup(...)` call
  setup.cfg        `[options] install_requires` as an indented block

Two operations, both purely textual so that unrelated formatting is preserved
and the resulting diff touches only the dependency being removed:

  declared(path, text) -> {normalised package name, ...}
  remove(path, text, dep) -> new text, or None when it cannot be done safely

`remove` returns None rather than guessing whenever the declaration is laid out
in a way the editor cannot handle precisely (for example a Poetry inline table
spanning several lines). Callers skip those pairs; a wrong edit is far worse
than a missing instance.
"""
from __future__ import annotations

import re

try:
    import tomllib
except ImportError:  # Python < 3.11
    import tomli as tomllib

NAME_RE = re.compile(r"^\s*([A-Za-z0-9][A-Za-z0-9._-]*)")
# A requirements.txt line that is a directive rather than a requirement.
DIRECTIVE = re.compile(r"^\s*-")


def norm(n: str) -> str:
    return n.lower().replace("-", "_").replace(".", "_")


def kind(path: str) -> str:
    base = path.split("/")[-1]
    if base.endswith("pyproject.toml"):
        return "pyproject"
    if base.endswith("setup.py"):
        return "setup_py"
    if base.endswith("setup.cfg"):
        return "setup_cfg"
    if base.endswith((".txt", ".in")):
        return "requirements"
    return "unknown"


# --------------------------------------------------------------------------
# shared helpers
# --------------------------------------------------------------------------
def _section_span(text: str, header_regex: str):
    m = re.search(header_regex, text, re.M)
    if not m:
        return None
    nxt = re.search(r"^\[", text[m.end():], re.M)
    return m.start(), (m.end() + nxt.start() if nxt else len(text))


def _balanced_end(text: str, i: int) -> int:
    """Index just past the bracket/brace opened at `i`, honouring strings."""
    depth = 0
    in_str = None
    j = i
    while j < len(text):
        c = text[j]
        if in_str:
            if c == "\\":
                j += 2
                continue
            if c == in_str:
                in_str = None
        elif c in ('"', "'"):
            in_str = c
        elif c in "[{(":
            depth += 1
        elif c in "]})":
            depth -= 1
            if depth == 0:
                return j + 1
        j += 1
    return -1


def _req_name(s: str) -> str | None:
    """Package name from a requirement string, or None if it is not one."""
    s = s.strip()
    if not s or s.startswith("#") or DIRECTIVE.match(s):
        return None
    s = s.split("#", 1)[0].strip()          # trailing comment
    s = re.split(r"[;@]", s, 1)[0].strip()  # marker / direct URL
    s = re.sub(r"\[.*?\]", "", s)           # extras
    m = NAME_RE.match(s)
    return norm(m.group(1)) if m else None


# --------------------------------------------------------------------------
# pyproject.toml
# --------------------------------------------------------------------------
def _pyproject_declared(text: str) -> set[str]:
    data = tomllib.loads(text)
    po = data.get("tool", {}).get("poetry", {})
    if po:
        return {norm(k) for k in (po.get("dependencies") or {}) if k.lower() != "python"}
    out = set()
    for d in data.get("project", {}).get("dependencies", []) or []:
        n = _req_name(d)
        if n:
            out.add(n)
    return out


def _pyproject_remove(text: str, dep: str):
    import json as _json

    data = tomllib.loads(text)
    po = data.get("tool", {}).get("poetry", {})
    if po:
        span = _section_span(text, r"^\[tool\.poetry\.dependencies\]\s*$")
        if not span:
            return None
        s, e = span
        body = text[s:e]
        for key in po.get("dependencies") or {}:
            if norm(key) != norm(dep):
                continue
            m = re.search(r'^[ \t]*"?' + re.escape(key) + r'"?[ \t]*=[ \t]*', body, re.M)
            if not m:
                return None
            k = m.end()
            if k < len(body) and body[k] in "[{":
                k = _balanced_end(body, k)
                if k < 0:
                    return None
            nl = body.find("\n", k)
            k = len(body) if nl < 0 else nl + 1
            return text[:s] + body[:m.start()] + body[k:] + text[e:]
        return None

    span = _section_span(text, r"^\[project\]\s*$")
    if not span:
        return None
    s, e = span
    body = text[s:e]
    m = re.search(r"^dependencies[ \t]*=[ \t]*\[", body, re.M)
    if not m:
        return None
    a = m.end() - 1
    b = _balanced_end(body, a)
    if b < 0:
        return None
    entries = data["project"].get("dependencies") or []
    keep = [d for d in entries if _req_name(d) != norm(dep)]
    if len(keep) == len(entries):
        return None
    arr = "[\n" + "".join(f"    {_json.dumps(d)},\n" for d in keep) + "]"
    return text[:s] + body[:a] + arr + body[b:] + text[e:]


# --------------------------------------------------------------------------
# requirements.txt
# --------------------------------------------------------------------------
def _requirements_declared(text: str) -> set[str]:
    out = set()
    for line in text.splitlines():
        n = _req_name(line)
        if n:
            out.add(n)
    return out


def _requirements_remove(text: str, dep: str):
    """Drop the line declaring `dep`, preserving line endings elsewhere."""
    target = norm(dep)
    lines = text.splitlines(keepends=True)
    out, removed = [], 0
    for line in lines:
        if _req_name(line) == target:
            removed += 1
            continue
        out.append(line)
    return "".join(out) if removed else None


# --------------------------------------------------------------------------
# setup.py
# --------------------------------------------------------------------------
def _setup_py_list_span(text: str):
    """Span of the install_requires list literal, or None."""
    m = re.search(r"install_requires\s*=\s*\[", text)
    if not m:
        return None
    a = m.end() - 1
    b = _balanced_end(text, a)
    return (a, b) if b > 0 else None


def _setup_py_entries(text: str):
    """(start, end, requirement string) for each literal entry in the list."""
    span = _setup_py_list_span(text)
    if not span:
        return []
    a, b = span
    inner = text[a + 1:b - 1]
    out = []
    for m in re.finditer(r"""(['"])(.*?)\1""", inner, re.S):
        out.append((a + 1 + m.start(), a + 1 + m.end(), m.group(2)))
    return out


def _setup_py_declared(text: str) -> set[str]:
    out = set()
    for _s, _e, req in _setup_py_entries(text):
        n = _req_name(req)
        if n:
            out.add(n)
    return out


def _setup_py_remove(text: str, dep: str):
    """Remove one entry, plus its trailing comma/comment, from install_requires.

    Variables or comprehensions inside the list are left alone; if the target is
    not a plain literal we return None rather than risk a malformed edit.
    """
    target = norm(dep)
    hits = [(s, e, r) for (s, e, r) in _setup_py_entries(text) if _req_name(r) == target]
    if len(hits) != 1:
        return None
    s, e, _req = hits[0]
    # swallow a following comma and any same-line trailing comment
    j = e
    while j < len(text) and text[j] in " \t":
        j += 1
    if j < len(text) and text[j] == ",":
        j += 1
    k = j
    while k < len(text) and text[k] in " \t":
        k += 1
    if k < len(text) and text[k] == "#":
        nl = text.find("\n", k)
        j = len(text) if nl < 0 else nl
    # if the entry was alone on its line, drop the whole line
    line_start = text.rfind("\n", 0, s) + 1
    if not text[line_start:s].strip():
        nl = text.find("\n", j)
        if nl >= 0 and not text[j:nl].strip():
            return text[:line_start] + text[nl + 1:]
    return text[:s] + text[j:]


# --------------------------------------------------------------------------
# setup.cfg
# --------------------------------------------------------------------------
def _setup_cfg_block(text: str):
    """(start, end) of the indented install_requires block, or None."""
    m = re.search(r"^install_requires\s*=[ \t]*\n", text, re.M)
    if not m:
        return None
    start = m.end()
    i = start
    for line in text[start:].splitlines(keepends=True):
        if line.strip() and not line[:1].isspace():
            break
        i += len(line)
    return start, i


def _setup_cfg_declared(text: str) -> set[str]:
    span = _setup_cfg_block(text)
    if not span:
        # single-line form: install_requires = a, b
        m = re.search(r"^install_requires\s*=[ \t]*(.+)$", text, re.M)
        if not m:
            return set()
        return {n for n in (_req_name(p) for p in m.group(1).split(",")) if n}
    s, e = span
    out = set()
    for line in text[s:e].splitlines():
        n = _req_name(line)
        if n:
            out.add(n)
    return out


def _setup_cfg_remove(text: str, dep: str):
    target = norm(dep)
    span = _setup_cfg_block(text)
    if not span:
        return None
    s, e = span
    kept, removed = [], 0
    for line in text[s:e].splitlines(keepends=True):
        if _req_name(line) == target:
            removed += 1
            continue
        kept.append(line)
    if not removed:
        return None
    return text[:s] + "".join(kept) + text[e:]


# --------------------------------------------------------------------------
# public API
# --------------------------------------------------------------------------
_DECLARED = {
    "pyproject": _pyproject_declared,
    "requirements": _requirements_declared,
    "setup_py": _setup_py_declared,
    "setup_cfg": _setup_cfg_declared,
}
_REMOVE = {
    "pyproject": _pyproject_remove,
    "requirements": _requirements_remove,
    "setup_py": _setup_py_remove,
    "setup_cfg": _setup_cfg_remove,
}


def declared(path: str, text: str) -> set[str]:
    fn = _DECLARED.get(kind(path))
    return fn(text) if fn else set()


def remove(path: str, text: str, dep: str):
    """Manifest text with `dep`'s declaration removed, or None if unsafe.

    Always verify the result with `declared` before use: a caller should accept
    the edit only when the declared set shrinks by exactly `dep`.
    """
    fn = _REMOVE.get(kind(path))
    if not fn:
        return None
    try:
        return fn(text, dep)
    except Exception:
        return None
