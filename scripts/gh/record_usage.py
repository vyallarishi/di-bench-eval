#!/usr/bin/env python3
"""Phase 0 of the behavioural gate: record what the library actually did.

Before the agent runs, with the library still installed, we run the repository's
test suite once and record every call the repository's own code makes into the
removed package D: the qualified name, the arguments, the return value, and any
exception. That recording is the oracle G4 grades against. The agent never sees
it.

The recorder is a module injected into the repository as `sitecustomize.py`, so
it is active in every interpreter the suite starts, including subprocesses and
tox environments. It installs an import hook that wraps D's public callables on
first import, then filters by *frame origin* exactly as the blocker does: only
calls made from the repository's own files are recorded, so D's internal calls
and other packages' use of D do not pollute the trace.

Values are captured as *summaries*, not objects: a repr capped in length, plus a
type tag and, for containers and numerics, a structural fingerprint. Deep
equality of arbitrary objects is undecidable in general and pickling a live
object from a library we are about to delete is self-defeating, so the
comparison in G4a is defined over these summaries and the normalisation rules
are published with the benchmark.

usage (as a library):
    from record_usage import write_recorder
    write_recorder(repo, dep, import_names(dep), own_packages(repo), out="usage.jsonl")

then run the suite; each process appends JSON lines to `out`.
"""
from __future__ import annotations

import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
import inject  # noqa: E402

RECORDER = '''\
# fmt: off
# flake8: noqa
# ruff: noqa
# pylint: skip-file
# mypy: ignore-errors
# isort: skip_file
"""Injected by UnpinBench: record calls this repository makes into {dep!r}."""
import json
import os
import sys
import threading

_TARGETS = {names!r}
_DEP = {dep!r}
_OWN = {own!r}
_OUT = {out!r}
_MAXREPR = 300
_MAXCALLS = {maxcalls}

_ROOT = os.path.dirname(os.path.abspath(__file__))
_SELF = {{os.path.abspath(__file__)}}
_VENV = ("/.venv/", "/venv/", "/.tox/", "/.nox/", "/.eggs/", "/node_modules/", "/.git/")
_STDLIB = os.path.dirname(os.__file__)
_lock = threading.Lock()
_count = [0]
_depth = threading.local()
_fcache = {{}}


def _is_repo_file(fn):
    if fn in _fcache:
        return _fcache[fn]
    if not fn or fn.startswith("<"):
        r = None if fn.startswith("<frozen") else True
    elif "site-packages" in fn or "dist-packages" in fn:
        tail = fn.split("-packages", 1)[1].lstrip("/").split("/")
        r = bool(tail) and tail[0].split(".")[0] in _OWN
    elif fn.startswith(_STDLIB + "/") or "/importlib/" in fn:
        r = None
    elif any(v in fn for v in _VENV):
        r = False
    elif not os.path.isabs(fn):
        r = True
    elif os.path.abspath(fn).startswith(_ROOT + "/"):
        r = None if os.path.abspath(fn) in _SELF else True
    else:
        r = False
    _fcache[fn] = r
    return r


def _caller():
    """(repo_origin, 'file:line') of the nearest frame outside the recorder."""
    f = sys._getframe(2)
    while f is not None:
        fn = f.f_code.co_filename
        if os.path.abspath(fn) not in _SELF:
            r = _is_repo_file(fn)
            if r is not None:
                try:
                    rel = os.path.relpath(os.path.abspath(fn), _ROOT)
                except ValueError:
                    rel = fn
                return r, "%s:%d" % (rel, f.f_lineno)
        f = f.f_back
    return False, "?"


def _summary(v, _d=0):
    """Type-tagged, length-capped structural summary of a value."""
    t = type(v)
    name = getattr(t, "__name__", "?")
    if v is None or isinstance(v, bool):
        return {{"t": name, "v": v}}
    if isinstance(v, int):
        return {{"t": "int", "v": v}}
    if isinstance(v, float):
        # bit pattern so NaN/-0.0 compare exactly; G4a applies a tolerance rule
        return {{"t": "float", "v": repr(v)}}
    if isinstance(v, (str, bytes)):
        s = v if isinstance(v, str) else v.decode("utf-8", "replace")
        return {{"t": name, "n": len(v), "v": s[:_MAXREPR]}}
    if isinstance(v, (list, tuple, set, frozenset)) and _d < 3:
        items = list(v)[:20]
        return {{"t": name, "n": len(v), "items": [_summary(i, _d + 1) for i in items]}}
    if isinstance(v, dict) and _d < 3:
        keys = sorted(map(str, list(v)))[:20]
        return {{"t": "dict", "n": len(v),
                "items": [[k, _summary(v[k] if k in v else v.get(k), _d + 1)] for k in keys if k in v]}}
    mod = getattr(t, "__module__", "") or ""
    out = {{"t": name, "mod": mod.split(".")[0]}}
    try:
        r = repr(v)[:_MAXREPR]
    except Exception:
        r = "<unreprable>"
    # a default repr carries the object's address, which differs on every run;
    # keep the type only, so comparison is not defeated by allocation
    import re as _re
    out["r"] = _re.sub(r" at 0x[0-9a-fA-F]+", " at 0xADDR", r)
    # structural fingerprint for array-likes, so numerics are comparable at all
    for attr in ("shape", "dtype", "size"):
        a = getattr(v, attr, None)
        if a is not None and not callable(a):
            out[attr] = str(a)[:64]
    try:
        if hasattr(v, "tolist") and getattr(v, "size", 1 << 30) <= 64:
            out["list"] = _summary(v.tolist(), _d + 1)
    except Exception:
        pass
    return out


def _emit(rec):
    with _lock:
        if _count[0] >= _MAXCALLS:
            return
        _count[0] += 1
        try:
            with open(_OUT, "a") as fh:
                fh.write(json.dumps(rec, default=str) + "\\n")
        except Exception:
            pass


def _wrap(fn, qual):
    def wrapper(*args, **kwargs):
        if getattr(_depth, "n", 0):          # ignore D calling itself
            return fn(*args, **kwargs)
        is_repo, site = _caller()
        if not is_repo:
            return fn(*args, **kwargs)
        _depth.n = getattr(_depth, "n", 0) + 1
        try:
            try:
                out = fn(*args, **kwargs)
            except BaseException as e:
                _emit({{"q": qual, "site": site, "pid": os.getpid(),
                       "args": [_summary(a) for a in args[:8]],
                       "kwargs": {{k: _summary(v) for k, v in list(kwargs.items())[:8]}},
                       "raised": type(e).__name__, "msg": str(e)[:200]}})
                raise
            _emit({{"q": qual, "site": site, "pid": os.getpid(),
                   "args": [_summary(a) for a in args[:8]],
                   "kwargs": {{k: _summary(v) for k, v in list(kwargs.items())[:8]}},
                   "ret": _summary(out)}})
            return out
        finally:
            _depth.n -= 1
    try:
        wrapper.__name__ = getattr(fn, "__name__", "wrapped")
        wrapper.__qualname__ = qual
        wrapper.__doc__ = getattr(fn, "__doc__", None)
        wrapper.__wrapped__ = fn
    except Exception:
        pass
    return wrapper


def _instrument(mod, prefix, depth=0):
    """Wrap public callables on a module and its public classes, in place."""
    import inspect
    for name in list(vars(mod)):
        if name.startswith("_"):
            continue
        try:
            obj = getattr(mod, name)
        except Exception:
            continue
        qual = prefix + "." + name
        try:
            if inspect.isclass(obj):
                if depth < 1 and (getattr(obj, "__module__", "") or "").split(".")[0] in _TARGETS:
                    for mname in list(vars(obj)):
                        if mname.startswith("_") and mname not in ("__init__", "__call__"):
                            continue
                        try:
                            m = inspect.getattr_static(obj, mname)
                        except Exception:
                            continue
                        if isinstance(m, staticmethod):
                            setattr(obj, mname, staticmethod(_wrap(m.__func__, qual + "." + mname)))
                        elif isinstance(m, classmethod):
                            setattr(obj, mname, classmethod(_wrap(m.__func__, qual + "." + mname)))
                        elif inspect.isfunction(m):
                            setattr(obj, mname, _wrap(m, qual + "." + mname))
            elif inspect.isfunction(obj) or inspect.isbuiltin(obj):
                setattr(mod, name, _wrap(obj, qual))
        except Exception:
            continue


class _Hook:
    """Instrument each target module the first time it finishes importing."""

    def __init__(self):
        self._seen = set()

    def find_module(self, fullname, path=None):
        return None

    def find_spec(self, fullname, path=None, target=None):
        root = fullname.split(".")[0]
        if root not in _TARGETS or fullname in self._seen:
            return None
        for finder in sys.meta_path:
            if finder is self or not hasattr(finder, "find_spec"):
                continue
            spec = finder.find_spec(fullname, path, target)
            if spec is None or spec.loader is None or not hasattr(spec.loader, "exec_module"):
                continue
            inner, hook = spec.loader, self

            class _L:
                def create_module(self, s):
                    return inner.create_module(s) if hasattr(inner, "create_module") else None

                def exec_module(self, module):
                    inner.exec_module(module)
                    hook._seen.add(module.__name__)
                    try:
                        _instrument(module, module.__name__)
                    except Exception:
                        pass

                def __getattr__(self, k):
                    return getattr(inner, k)

            spec.loader = _L()
            return spec
        return None


def _install():
    if not any(isinstance(f, _Hook) for f in sys.meta_path):
        sys.meta_path.insert(0, _Hook())
    for name in list(sys.modules):          # force re-import so the hook sees it
        if name.split(".")[0] in _TARGETS:
            del sys.modules[name]


_install()
'''


def write_recorder(root: pathlib.Path, dep: str, names, own=None,
                   out: str = "usage.jsonl", maxcalls: int = 20000) -> list[str]:
    """Install the recorder as sitecustomize.py + conftest.py in `root`."""
    body = RECORDER.format(dep=dep, names=sorted(set(names)), own=sorted(set(own or [])),
                           out=str(out), maxcalls=maxcalls)
    return inject.install(root, body)


# --------------------------------------------------------------------------
# trace comparison, used by G4a
# --------------------------------------------------------------------------
FLOAT_TOL = 1e-9


def _floats_equal(a: str, b: str) -> bool:
    try:
        x, y = float(a), float(b)
    except (TypeError, ValueError):
        return a == b
    if x != x and y != y:      # both NaN
        return True
    if x == y:
        return True
    scale = max(abs(x), abs(y), 1.0)
    return abs(x - y) <= FLOAT_TOL * scale


def values_equal(a, b) -> bool:
    """Equality over recorded summaries. The normalisation rules, stated once.

    - floats compare within a relative tolerance; NaN equals NaN
    - containers compare by length and element-wise, order-sensitively except
      for set and dict, whose summaries are already order-normalised
    - opaque objects compare by type name and capped repr; a differing repr on
      an object whose type matches is reported as a *difference*, not a pass,
      because the alternative is to ignore every non-primitive result
    """
    if type(a) is not type(b):
        return False
    if not isinstance(a, dict):
        return a == b
    if a.get("t") != b.get("t") or a.get("n") != b.get("n"):
        return False
    t = a.get("t")
    if t == "float":
        return _floats_equal(a.get("v"), b.get("v"))
    if "items" in a or "items" in b:
        ia, ib = a.get("items") or [], b.get("items") or []
        if len(ia) != len(ib):
            return False
        return all(values_equal(x, y) for x, y in zip(ia, ib))
    for k in ("v", "r", "shape", "dtype", "size"):
        if a.get(k) != b.get(k):
            if k == "r" and a.get("t") == b.get("t"):
                return False
            return False
    if "list" in a or "list" in b:
        return values_equal(a.get("list"), b.get("list"))
    return True


def call_key(rec: dict) -> tuple:
    """Identity of a recorded call, for pairing reference against candidate."""
    import json as _j
    return (rec.get("q"), rec.get("site"),
            _j.dumps(rec.get("args"), sort_keys=True, default=str),
            _j.dumps(rec.get("kwargs"), sort_keys=True, default=str))
