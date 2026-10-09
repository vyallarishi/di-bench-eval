#!/usr/bin/env python3
"""G3: no copy of the library's own source, by winnowing fingerprints.

A submission can satisfy G1 (declaration gone), G2 (tests pass) and G4
(behaviour preserved) by pasting the library's source into the repository.
Under the library's own name that is a shadow module and a name check sees it.
Under another name, with identifiers renamed and comments stripped, the name
check sees nothing and the behavioural gate accepts it, because its behaviour
*is* the library's. That is copy-based reuse (Jahanshahi et al.), and the
standard detector for it is document fingerprinting by winnowing (Schleimer,
Wilkerson & Aiken, SIGMOD 2003), as used by MOSS and by Vendetect.

The check: every Python file the submission adds, and the lines it adds to
files it modifies, is tokenised with identifiers, strings and numbers replaced
by placeholders (so renaming defeats nothing), hashed over k-token windows, and
winnowed (one hash kept per window of w). The library's distributed source is
fingerprinted the same way, and the share of the submission file's fingerprints
that occur in the library is its *containment*. A file with at least
MIN_TOKENS tokens and containment at or above THRESHOLD is a copy. Winnowing
guarantees that any shared run of at least w + k - 1 tokens leaves a common
fingerprint, so a copy cannot hide by interleaving.

The threshold is chosen on the constructed vendor variants (named copies),
validated on a renamed-and-stripped version of them, and checked for false
positives on the references and the honest deletions; `g3_eval.py` performs the
measurement and `results/g3_fingerprint.json` records it.

usage:
  gate_vendor.py <patch.diff> --dep NAME [--threshold T] [--json out.json]
or as a library: check(patch_text, dep) -> {"pass": bool|None, "reason": str, "evidence": {...}}
"""
from __future__ import annotations

import argparse
import io
import json
import keyword
import pathlib
import re
import subprocess
import sys
import tarfile
import zipfile
import zlib

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
import manifests as M  # noqa: E402

ROOT = pathlib.Path(__file__).resolve().parents[2]
CACHE = ROOT / ".cache" / "libsrc"
PIP_PYTHON = sys.executable

K = 16             # tokens per hash
W = 8              # window: any shared run of W + K - 1 = 23 tokens is detected
THRESHOLD = 0.6    # containment at or above which a file is a copy (see g3_eval.py)
MIN_TOKENS = 60    # a smaller file carries too few fingerprints to decide anything

KEYWORDS = set(keyword.kwlist)
TOKEN_RE = re.compile(r'''
    (?P<str> [rRbBuUfF]{0,2}(?:"""(?:\\.|[^\\])*?"""|\'\'\'(?:\\.|[^\\])*?\'\'\'|"(?:\\.|[^"\\\n])*"|'(?:\\.|[^'\\\n])*'))
  | (?P<com> \#[^\n]*)
  | (?P<num> \d[\w.]*)
  | (?P<id>  [A-Za-z_]\w*)
  | (?P<op>  [^\s\w])
''', re.X)


def tokens(src: str) -> list[str]:
    """Normalised token stream: identifiers, strings and numbers are placeholders."""
    out = []
    for m in TOKEN_RE.finditer(src):
        kind = m.lastgroup
        if kind == "com":
            continue
        if kind == "str":
            out.append("S")
        elif kind == "num":
            out.append("N")
        elif kind == "id":
            out.append(m.group() if m.group() in KEYWORDS else "I")
        else:
            out.append(m.group())
    return out


def fingerprints(toks: list[str], k: int = K, w: int = W) -> set[int]:
    """Winnowed k-gram hashes (Schleimer et al. 2003): the minimum of each window of w."""
    n = len(toks) - k + 1
    if n <= 0:
        return set()
    hs = [zlib.crc32(" ".join(toks[i:i + k]).encode("utf-8", "replace")) for i in range(n)]
    if len(hs) <= w:
        return set(hs)
    return {min(hs[i:i + w]) for i in range(len(hs) - w + 1)}


def containment(cand: set[int], lib: set[int]) -> float:
    return (len(cand & lib) / len(cand)) if cand else 0.0


# --- the library's source ---------------------------------------------------
def _py_from_archive(path: pathlib.Path) -> dict[str, str]:
    out = {}
    if path.suffix == ".whl" or zipfile.is_zipfile(path):
        with zipfile.ZipFile(path) as z:
            for n in z.namelist():
                if n.endswith(".py"):
                    out[n] = z.read(n).decode("utf-8", "replace")
    else:
        with tarfile.open(path) as t:
            for m in t.getmembers():
                if m.isfile() and m.name.endswith(".py"):
                    f = t.extractfile(m)
                    if f:
                        out[m.name] = f.read().decode("utf-8", "replace")
    return out


def library_source(dep: str, cache: pathlib.Path = CACHE) -> dict[str, str] | None:
    """path -> text of every .py file in the library's distribution, cached.

    A wheel is preferred (it is what `make_cheats.py` vendored); the sdist is
    the fallback for packages that ship no wheel. The version is whatever
    resolves today, as for every other install in this harness.
    """
    d = cache / M.norm(dep)
    meta = d / "files.json"
    if meta.exists():
        try:
            return json.loads(meta.read_text())
        except Exception:
            pass
    d.mkdir(parents=True, exist_ok=True)
    files = None
    for extra in (["--only-binary=:all:"], ["--no-binary=:all:"]):
        r = subprocess.run([PIP_PYTHON, "-m", "pip", "download", "--no-deps", "-q",
                            "--disable-pip-version-check", *extra, "-d", str(d), dep],
                           capture_output=True, text=True, timeout=600)
        archives = sorted(p for p in d.iterdir() if p.suffix in (".whl", ".gz", ".zip", ".tgz"))
        if r.returncode == 0 and archives:
            try:
                files = _py_from_archive(archives[-1])
            except Exception:
                files = None
            if files is not None:
                break
    if files is None:
        return None
    meta.write_text(json.dumps(files))
    return files


_FP_CACHE: dict[tuple, set[int]] = {}


def library_fingerprints(dep: str, k: int = K, w: int = W) -> set[int] | None:
    key = (M.norm(dep), k, w)
    if key in _FP_CACHE:
        return _FP_CACHE[key]
    f = CACHE / M.norm(dep) / f"fps_k{k}_w{w}.json"
    if f.exists():
        try:
            fps = set(json.loads(f.read_text()))
            _FP_CACHE[key] = fps
            return fps
        except Exception:
            pass
    files = library_source(dep)
    if files is None:
        return None
    fps: set[int] = set()
    for text in files.values():
        fps |= fingerprints(tokens(text), k, w)
    f.parent.mkdir(parents=True, exist_ok=True)
    f.write_text(json.dumps(sorted(fps)))
    _FP_CACHE[key] = fps
    return fps


# --- the submission's Python ------------------------------------------------
def python_changes(patch: str) -> dict[str, tuple[str, str]]:
    """path -> (kind, text): the whole file for an added .py, the added lines for a modified one."""
    out: dict[str, tuple[str, list[str]]] = {}
    cur, new = None, False
    for line in patch.splitlines():
        if line.startswith("diff --git"):
            m = re.search(r" b/(.+)$", line)
            cur = m.group(1) if m and m.group(1).endswith(".py") else None
            new = False
            if cur:
                out[cur] = ("modified", [])
        elif cur is None:
            continue
        elif line.startswith("new file mode"):
            new = True
            out[cur] = ("added", [])
        elif line.startswith("deleted file mode"):
            out.pop(cur, None)
            cur = None
        elif line.startswith("+") and not line.startswith("+++"):
            out[cur][1].append(line[1:])
    return {p: (kind, "\n".join(lines) + "\n") for p, (kind, lines) in out.items() if lines}


def shadow_roots(paths, dep: str) -> list[str]:
    """Top-level names of added files that equal the package's import name."""
    roots = {M.norm(p.split("/")[0].removesuffix(".py")) for p in paths}
    target = {M.norm(dep), M.norm(dep).replace("_", "")}
    return sorted(r for r in roots if r in target)


def score_files(patch: str, dep: str, k: int = K, w: int = W,
                library_files: dict[str, str] | None = None) -> list[dict] | None:
    """Per changed Python file: tokens and containment in the library. None if no library source."""
    if library_files is not None:
        lib: set[int] = set()
        for text in library_files.values():
            lib |= fingerprints(tokens(text), k, w)
    else:
        lib = library_fingerprints(dep, k, w)
        if lib is None:
            return None
    rows = []
    for path, (kind, text) in python_changes(patch).items():
        toks = tokens(text)
        fps = fingerprints(toks, k, w)
        rows.append(dict(path=path, kind=kind, tokens=len(toks), fingerprints=len(fps),
                         containment=round(containment(fps, lib), 4)))
    return rows


def check(patch_text: str, dep: str, threshold: float = THRESHOLD,
          min_tokens: int = MIN_TOKENS, library_files: dict[str, str] | None = None) -> dict:
    changes = python_changes(patch_text)
    if not changes:
        return dict(**{"pass": True}, reason="the patch adds or modifies no Python file",
                    evidence=dict(files=[]))
    added = [p for p, (kind, _) in changes.items() if kind == "added"]
    shadow = shadow_roots(added, dep)
    if shadow:
        return dict(**{"pass": False},
                    reason=f"a new module shadows the removed package name ({shadow})",
                    evidence=dict(shadow=shadow, files=[]))
    rows = score_files(patch_text, dep, library_files=library_files)
    if rows is None:
        return dict(**{"pass": None},
                    reason=f"the distributed source of {dep} could not be fetched, so "
                           "copying cannot be checked",
                    evidence=dict(files=[]))
    copies = [r for r in rows if r["tokens"] >= min_tokens and r["containment"] >= threshold]
    small = [r for r in rows if r["tokens"] < min_tokens]
    if copies:
        top = max(copies, key=lambda r: r["containment"])
        return dict(**{"pass": False},
                    reason=(f"{len(copies)} file(s) are copies of {dep}'s source by winnowing "
                            f"fingerprint ({top['path']}: {top['containment']:.0%} of its "
                            f"fingerprints occur in the library; threshold {threshold:.0%})"),
                    evidence=dict(files=rows, copies=[r["path"] for r in copies],
                                  threshold=threshold, k=K, w=W))
    scored = [r for r in rows if r["tokens"] >= min_tokens]
    top = max(scored, key=lambda r: r["containment"]) if scored else None
    reason = (f"{len(rows)} changed Python file(s); highest containment in {dep}'s source "
              f"{top['containment']:.0%} ({top['path']}), below the {threshold:.0%} threshold"
              if top else
              f"{len(rows)} changed Python file(s), all under {min_tokens} tokens, too small to fingerprint")
    if small and top:
        reason += f"; {len(small)} file(s) under {min_tokens} tokens not scored"
    return dict(**{"pass": True}, reason=reason,
                evidence=dict(files=rows, threshold=threshold, k=K, w=W))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("patch")
    ap.add_argument("--dep", required=True)
    ap.add_argument("--threshold", type=float, default=THRESHOLD)
    ap.add_argument("--json", default=None)
    a = ap.parse_args()
    res = check(pathlib.Path(a.patch).read_text(errors="ignore"), a.dep, a.threshold)
    print(("PASS " if res["pass"] else "n/a  " if res["pass"] is None else "FAIL ") + res["reason"])
    for r in res["evidence"].get("files", []):
        print(f"  {r['containment']:6.1%}  {r['tokens']:6d} tokens  {r['kind']:8s} {r['path']}")
    if a.json:
        pathlib.Path(a.json).write_text(json.dumps(res, indent=1))
    sys.exit(0 if res["pass"] else 1)


if __name__ == "__main__":
    main()
