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
import hashlib
import json
import os
import re as _re
import sys
import threading

_TARGETS = {names!r}
_DEP = {dep!r}
_OWN = {own!r}
_OUT = {out!r}
_MAXREPR = 300
_MAXCALLS = {maxcalls}
_SITE_EXCLUDE = {site_exclude!r}   # files whose calls are internal to the replacement
_USAGE = {usage!r}                 # repo-relative file -> project functions recorded at the usage site
_USAGE_MODULES = {usage_modules!r} # importable module name -> repo-relative files it may be loaded from

_ROOT = os.path.dirname(os.path.abspath(__file__))
_REAL_ROOT = os.path.realpath(_ROOT)
_SELF = {{os.path.abspath(__file__)}}
_REAL_SELF = {{os.path.realpath(p) for p in _SELF}}
_VENV = ("/.venv/", "/venv/", "/.tox/", "/.nox/", "/.eggs/", "/node_modules/", "/.git/")
_STDLIB = os.path.dirname(os.__file__)
_lock = threading.Lock()
_count = [0]
_ucount = [0]
_depth = threading.local()
_busy = threading.local()      # set while a record is being summarised; calls made then are not recorded
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
    else:
        # Compare RESOLVED paths. abspath() alone is not enough: on macOS a
        # temporary checkout is handed to us as /var/folders/... while frames
        # report /private/var/folders/..., and any symlinked checkout on Linux
        # does the same. The prefix test then fails for every repository
        # frame, the whole repository is classified foreign, and the tool
        # silently does nothing -- a blocker that blocks nothing, or a
        # recorder that records nothing. In a CI log that is indistinguishable
        # from a dependency the tests never exercise, which is the one
        # confusion this project cannot afford.
        real = os.path.realpath(fn)
        if real.startswith(_REAL_ROOT + os.sep):
            r = None if (os.path.abspath(fn) in _SELF or real in _REAL_SELF) else True
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
                    rel = os.path.relpath(os.path.realpath(fn), os.path.realpath(_ROOT))
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
    if isinstance(v, memoryview):
        v = v.tobytes()
    if isinstance(v, (str, bytes, bytearray)):
        s = v if isinstance(v, str) else bytes(v).decode("utf-8", "replace")
        out = {{"t": name, "n": len(v), "v": s[:_MAXREPR]}}
        if len(s) > _MAXREPR:
            # the prefix is for reading; the hash is what equality uses, so a
            # replacement that differs only past the cap is still caught
            out["h"] = hashlib.sha1(s.encode("utf-8", "replace")).hexdigest()[:16]
        return out
    if isinstance(v, (list, tuple, set, frozenset)) and _d < 3:
        items = list(v)[:20]
        out = {{"t": name, "n": len(v), "items": [_summary(i, _d + 1) for i in items]}}
        if len(v) > 20:
            out["h"] = _fingerprint(v)
        return out
    if isinstance(v, dict) and _d < 3:
        keys = sorted(map(str, list(v)))[:20]
        out = {{"t": "dict", "n": len(v),
               "items": [[k, _summary(v[k] if k in v else v.get(k), _d + 1)] for k in keys if k in v]}}
        if len(v) > 20:
            out["h"] = _fingerprint(v)
        return out
    mod = getattr(t, "__module__", "") or ""
    out = {{"t": name, "mod": mod.split(".")[0]}}
    if callable(v) or name in ("generator", "coroutine", "async_generator"):
        # A function or a lazy iterator has no value to compare until it is
        # used; the recorder sees that use as a later call if the repository
        # makes it. Record what it is, not a repr with an address in it.
        q = getattr(v, "__qualname__", None) or getattr(
            getattr(v, "gi_code", None) or getattr(v, "cr_code", None), "co_name", None)
        out["r"] = "<%s %s>" % (name, q or "?")
        return out
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
        elif hasattr(v, "to_numpy") and getattr(v, "size", 1 << 30) <= 64:
            out["list"] = _summary(v.to_numpy().tolist(), _d + 1)
    except Exception:
        pass
    # arrays and tables larger than the inline cap: hash the whole content,
    # not the elided repr pandas and numpy print
    try:
        if "list" not in out and getattr(v, "size", 0) and hasattr(v, "tobytes"):
            out["h"] = hashlib.sha1(v.tobytes()).hexdigest()[:16]
        elif "list" not in out and hasattr(v, "to_csv") and getattr(v, "size", 1 << 30) <= 1000000:
            out["h"] = hashlib.sha1(str(v.to_csv()).encode("utf-8", "replace")).hexdigest()[:16]
    except Exception:
        pass
    # Observable structure. A repr can omit most of an object's state, and a
    # replacement that returns a plausible-looking object of the right type
    # could differ in exactly what the repr leaves out. Record the public,
    # non-callable attributes (the interface the repository can actually read)
    # and the length if it has one, depth-bounded like containers. This is the
    # state-carving idea of Elbaum et al.: compare what is observable through
    # the interface, not the object's identity.
    if _d < 2:
        try:
            attrs = {{}}
            d = getattr(v, "__dict__", None)
            if isinstance(d, dict):
                for k in sorted(d)[:16]:
                    if k.startswith("_") or callable(d[k]):
                        continue
                    attrs[k] = _summary(d[k], _d + 1)
            elif hasattr(v, "_fields"):
                for k in list(v._fields)[:16]:
                    attrs[k] = _summary(getattr(v, k), _d + 1)
            if attrs:
                out["attrs"] = attrs
        except Exception:
            pass
        try:
            if hasattr(v, "__len__"):
                out["len"] = len(v)
        except Exception:
            pass
    return out


def _fingerprint(v):
    """Deterministic hash of a whole value, address-stripped."""
    try:
        r = _re.sub(r" at 0x[0-9a-fA-F]+", " at 0xADDR", repr(v))
    except Exception:
        return None
    return hashlib.sha1(r.encode("utf-8", "replace")).hexdigest()[:16]


_MAXREC = 32768


def _shrink(s):
    """Replace a summary's expanded structure by a hash of that structure.

    Equality over the shrunk form is equality over the full summary, since the
    hash is taken of the summary itself; only readability is lost.
    """
    if isinstance(s, dict) and ("attrs" in s or "items" in s or "list" in s):
        out = dict((k, v) for k, v in s.items() if k not in ("attrs", "items", "list"))
        out["h"] = hashlib.sha1(json.dumps(s, sort_keys=True, default=str)
                                .encode("utf-8", "replace")).hexdigest()[:16]
        return out
    return s


def _bounded(rec):
    """A record no larger than _MAXREC bytes: the trace travels through a CI
    log, and one deep object must not crowd out the rest of the run."""
    line = json.dumps(rec, default=str)
    if len(line) <= _MAXREC:
        return line
    rec = dict(rec)
    if "ret" in rec:
        rec["ret"] = _shrink(rec["ret"])
    rec["args"] = [_shrink(a) for a in rec.get("args", [])]
    rec["kwargs"] = dict((k, _shrink(v)) for k, v in rec.get("kwargs", {{}}).items())
    return json.dumps(rec, default=str)


def _emit(rec, counter=None):
    counter = _count if counter is None else counter
    with _lock:
        if counter[0] >= _MAXCALLS:
            return
        counter[0] += 1
        try:
            with open(_OUT, "a") as fh:
                fh.write(_bounded(rec) + "\\n")
        except Exception as e:
            # Never silent: a trace that fails to write is indistinguishable
            # from a dependency the tests do not exercise, and that ambiguity
            # is exactly what the behavioural gate must not have.
            try:
                sys.stderr.write("UnpinBench recorder: write to %s failed: %s: %s"
                                 % (_OUT, type(e).__name__, e) + chr(10))
                sys.stderr.flush()
            except Exception:
                pass


def _record_call(qual, site, args, kwargs, out=None, exc=None, level=None,
                 method=False, counter=None):
    """Summarise one call and write it. Calls the summariser itself provokes
    (a project __repr__ that reaches a wrapped function) are not recorded."""
    if getattr(_busy, "on", False):
        return
    _busy.on = True
    try:
        rec = {{"q": qual, "site": site, "pid": os.getpid()}}
        if level:
            rec["level"] = level
            rec["m"] = method
        rec["args"] = [_summary(a) for a in args[:8]]
        rec["kwargs"] = {{k: _summary(v) for k, v in list(kwargs.items())[:8]}}
        if exc is not None:
            rec["raised"] = type(exc).__name__
            rec["msg"] = str(exc)[:200]
        else:
            rec["ret"] = _summary(out)
        _emit(rec, counter)
    except Exception:
        pass
    finally:
        _busy.on = False


def _wrap(fn, qual):
    def wrapper(*args, **kwargs):
        if getattr(_depth, "n", 0) or getattr(_busy, "on", False):   # D calling itself; summariser
            return fn(*args, **kwargs)
        is_repo, site = _caller()
        if not is_repo:
            return fn(*args, **kwargs)
        if site.split(":")[0] in _SITE_EXCLUDE:      # the replacement calling itself
            return fn(*args, **kwargs)
        _depth.n = getattr(_depth, "n", 0) + 1
        try:
            try:
                out = fn(*args, **kwargs)
            except BaseException as e:
                _record_call(qual, site, args, kwargs, exc=e)
                raise
            _record_call(qual, site, args, kwargs, out=out)
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


# --- usage-site recording ---------------------------------------------------
# A replacement that lives inside a modified module, or is inlined at the call
# site, is not a callable the library-boundary hook can wrap: naming the
# modified module records the project's own API, and an inlined rewrite makes
# no call at all. The project's functions that USE the library keep their
# names across the change, so they are wrapped instead, in both phases, and
# their arguments and results are recorded under the function's qualified
# name. G4a pairs those records by function and order.
def _uwrap(fn, key, method):
    import functools
    import inspect
    if inspect.iscoroutinefunction(fn):
        async def wrapper(*args, **kwargs):
            if getattr(_busy, "on", False):
                return await fn(*args, **kwargs)
            try:
                out = await fn(*args, **kwargs)
            except BaseException as e:
                _record_call(key, key, args, kwargs, exc=e, level="usage", method=method, counter=_ucount)
                raise
            _record_call(key, key, args, kwargs, out=out, level="usage", method=method, counter=_ucount)
            return out
    else:
        def wrapper(*args, **kwargs):
            if getattr(_busy, "on", False):
                return fn(*args, **kwargs)
            try:
                out = fn(*args, **kwargs)
            except BaseException as e:
                _record_call(key, key, args, kwargs, exc=e, level="usage", method=method, counter=_ucount)
                raise
            _record_call(key, key, args, kwargs, out=out, level="usage", method=method, counter=_ucount)
            return out
    try:
        functools.update_wrapper(wrapper, fn)
    except Exception:
        pass
    return wrapper


def _wrap_usage(module, rel):
    """Wrap the usage-site functions of `module` if it really is the file `rel`."""
    import inspect
    try:
        f = getattr(module, "__file__", None) or ""
        if os.path.relpath(os.path.realpath(f), _REAL_ROOT) != rel:
            return
    except Exception:
        return
    if getattr(module, "_unpinbench_usage_wrapped", None) == rel:
        return
    try:
        setattr(module, "_unpinbench_usage_wrapped", rel)
    except Exception:
        pass
    for qual in _USAGE.get(rel, []):
        parts = qual.split(".")
        owner = module
        for p in parts[:-1]:
            owner = getattr(owner, p, None)
            if owner is None:
                break
        if owner is None:
            continue
        name = parts[-1]
        try:
            raw = inspect.getattr_static(owner, name)
        except Exception:
            continue
        key = rel + "::" + qual
        try:
            if isinstance(raw, staticmethod):
                setattr(owner, name, staticmethod(_uwrap(raw.__func__, key, False)))
            elif isinstance(raw, classmethod):
                setattr(owner, name, classmethod(_uwrap(raw.__func__, key, True)))
            elif (inspect.isfunction(raw) and not inspect.isgeneratorfunction(raw)
                  and not inspect.isasyncgenfunction(raw)):
                # a generator's value is only seen when consumed, which the
                # recorder cannot attribute; such functions are left alone
                setattr(owner, name, _uwrap(raw, key, inspect.isclass(owner)))
        except Exception:
            continue


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
                mod_name = getattr(obj, "__module__", "") or ""
                if depth < 1 and (mod_name.split(".")[0] in _TARGETS or mod_name in _TARGETS):
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
        # A target is either a top-level package (the library, e.g. "slugger")
        # or an explicit dotted module (the replacement, e.g. "app.textutil").
        # Matching only the root would never instrument a replacement that
        # lives inside the repository's own package.
        if fullname in self._seen:
            return None
        is_target = fullname.split(".")[0] in _TARGETS or fullname in _TARGETS
        is_usage = fullname in _USAGE_MODULES
        if not (is_target or is_usage):
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
                    if is_target:
                        try:
                            _instrument(module, module.__name__)
                        except Exception:
                            pass
                    if is_usage:
                        for rel in _USAGE_MODULES.get(module.__name__, []):
                            try:
                                _wrap_usage(module, rel)
                            except Exception:
                                pass

                def __getattr__(self, k):
                    return getattr(inner, k)

            spec.loader = _L()
            return spec
        return None


_FLAG = "_unpinbench_recorder_" + "_".join(sorted(_TARGETS))


def _install():
    # sitecustomize.py and conftest.py both carry this module, so they define
    # two distinct _Hook classes. isinstance() cannot recognise the other's
    # instance, and two installed hooks delegate to each other forever
    # (RecursionError at the first import). Guard on a marker instead.
    if getattr(sys, _FLAG, False):
        return
    setattr(sys, _FLAG, True)
    sys.meta_path.insert(0, _Hook())
    for name in list(sys.modules):          # force re-import so the hook sees it
        if name.split(".")[0] in _TARGETS:
            del sys.modules[name]
    for name in list(sys.modules):          # a usage module loaded before us is wrapped in place
        if name in _USAGE_MODULES:
            for rel in _USAGE_MODULES[name]:
                try:
                    _wrap_usage(sys.modules[name], rel)
                except Exception:
                    pass
    try:
        sys.stderr.write("UnpinBench recorder active: targets=%r out=%s pid=%d"
                         % (_TARGETS, _OUT, os.getpid()) + chr(10))
        sys.stderr.flush()
    except Exception:
        pass


_install()
'''


def module_names_for(rel: str) -> set[str]:
    """Names under which the repository file `rel` may be imported.

    Generous on purpose: the recorder verifies a candidate by the loaded
    module's __file__ before wrapping anything, so a wrong guess costs nothing.
    """
    p = rel[:-3] if rel.endswith(".py") else rel
    parts = p.split("/")
    if parts and parts[-1] == "__init__":
        parts = parts[:-1]
    if not parts:
        return set()
    names = {".".join(parts), parts[-1]}
    if len(parts) > 1:
        names.add(".".join(parts[1:]))          # src/ layouts, or a package directory on sys.path
    return {n for n in names if n and not n[0].isdigit()}


def write_recorder(root: pathlib.Path, dep: str, names, own=None,
                   out: str = "usage.jsonl", maxcalls: int = 20000,
                   site_exclude=(), usage=None) -> list[str]:
    """Install the recorder as sitecustomize.py + conftest.py in `root`.

    `names` may contain top-level package names (the library being removed) and
    dotted module names (a replacement inside the repository, e.g.
    "app.textutil"), so the same instrumentation records the reference run and
    the candidate run at the same call sites.

    `site_exclude` lists repository files whose calls into a target are
    internal to the replacement rather than uses by the project, so they are
    not recorded.

    `usage` maps a repository-relative file to the qualified names of the
    project functions in it that use the library (see `usage_functions`);
    those are wrapped too, and their calls recorded with ``"level": "usage"``.
    """
    usage = {rel: sorted(set(fns)) for rel, fns in (usage or {}).items() if fns}
    usage_modules: dict[str, list[str]] = {}
    for rel in usage:
        for m in module_names_for(rel):
            usage_modules.setdefault(m, []).append(rel)
    body = RECORDER.format(dep=dep, names=sorted(set(names)), own=sorted(set(own or [])),
                           out=str(out), maxcalls=maxcalls,
                           site_exclude=sorted(set(site_exclude)),
                           usage=dict(sorted(usage.items())),
                           usage_modules={k: sorted(v) for k, v in sorted(usage_modules.items())})
    return inject.install(root, body)


def _summary_namespace() -> dict:
    """Execute the recorder's summary functions in isolation."""
    src = RECORDER.format(dep="", names=[], own=[], out="", maxcalls=0, site_exclude=[],
                          usage={}, usage_modules={})
    start = src.index("def _summary(")
    end = src.index("def _emit(")
    ns: dict = {}
    exec("import hashlib, re as _re\n_MAXREPR = 300\n" + src[start:end], ns)
    return ns


_NS = None


def summarize(v):
    """The recorder's own summary of a live value, for tools outside the recorder.

    G4b runs the library and the candidate in-process and compares what they
    return; it must compare with the same summary and the same equality as
    G4a, or the two gates would disagree about what "same" means.
    """
    global _NS
    if _NS is None:
        _NS = _summary_namespace()
    return _NS["_summary"](v)


# --------------------------------------------------------------------------
# usage sites: which project functions use the library
# --------------------------------------------------------------------------
import ast as _ast
import os as _os
import re as _re

_TEST_PATH = _re.compile(
    r"(^|/)(tests?|testing|unittests?|integration_tests)/|"
    r"(^|/)test_[^/]*\.py$|_test\.py$|(^|/)conftest\.py$|(^|/)tests\.py$")
_SKIP_DIRS = {".git", ".axon", "node_modules", "venv", ".venv", "build", "dist",
              "site-packages", "__pycache__", ".tox", ".nox", ".eggs", "docs", "doc",
              "examples", "example"}


def is_test_path(rel: str) -> bool:
    return bool(_TEST_PATH.search(rel))


def _py_files(repo: pathlib.Path):
    for dp, dns, fns in _os.walk(repo):
        dns[:] = [d for d in dns if d not in _SKIP_DIRS and not d.startswith(".")]
        for f in fns:
            if f.endswith(".py"):
                yield pathlib.Path(dp) / f


def defs_index(tree) -> list[tuple[int, int, str, bool]]:
    """(first line, last line, qualified name, wrappable) for every def.

    A def is wrappable when it can be reached by attribute access from the
    module: a module-level function, or a method of a class at any nesting
    of classes. A function nested inside another function cannot be wrapped
    from outside, so a site inside it is attributed to the nearest wrappable
    ancestor instead.
    """
    out = []

    def visit(node, stack, in_func):
        for child in _ast.iter_child_nodes(node):
            if isinstance(child, (_ast.FunctionDef, _ast.AsyncFunctionDef)):
                qual = ".".join(stack + [child.name])
                out.append((child.lineno, getattr(child, "end_lineno", child.lineno) or child.lineno,
                            qual, not in_func))
                visit(child, stack + [child.name], True)
            elif isinstance(child, _ast.ClassDef):
                visit(child, stack + [child.name], in_func)
            else:
                visit(child, stack, in_func)
    visit(tree, [], False)
    return out


def enclosing_function(defs, line: int) -> str | None:
    """Innermost wrappable def containing `line`, or None for module-level code."""
    best = None
    for lo, hi, qual, ok in defs:
        if ok and lo <= line <= hi and (best is None or lo > best[0]):
            best = (lo, hi, qual)
    return best[2] if best else None


def static_use_sites(repo: pathlib.Path, names) -> dict[str, set[int]]:
    """repo-relative file -> lines on which a name bound from the library is used.

    Any use counts, not only a call: an attribute read such as ``Fore.RED`` is
    a use of the library whose effect shows in what the enclosing function
    returns, and the library-boundary recorder never sees it. ``import *``
    binds names the scan cannot resolve, so such a file contributes nothing.
    """
    names = set(names)
    out: dict[str, set[int]] = {}
    for f in _py_files(repo):
        rel = str(f.relative_to(repo))
        if is_test_path(rel):
            continue
        try:
            tree = _ast.parse(f.read_bytes())
        except Exception:
            continue
        aliases = set()
        for node in _ast.walk(tree):
            if isinstance(node, _ast.Import):
                for a in node.names:
                    if a.name.split(".")[0] in names:
                        aliases.add((a.asname or a.name).split(".")[0])
            elif isinstance(node, _ast.ImportFrom) and node.module and not node.level:
                if node.module.split(".")[0] in names:
                    for a in node.names:
                        if a.name != "*":
                            aliases.add(a.asname or a.name)
        if not aliases:
            continue
        lines = set()
        for node in _ast.walk(tree):
            if isinstance(node, _ast.Name) and node.id in aliases:
                lines.add(node.lineno)
            # A library decorator (`@memoize_method`) is a use whose effect
            # shows in the decorated function's results; the decorator line
            # sits above the def, so attribute it to the def's own line.
            if isinstance(node, (_ast.FunctionDef, _ast.AsyncFunctionDef)):
                for dec in node.decorator_list:
                    if any(isinstance(n, _ast.Name) and n.id in aliases for n in _ast.walk(dec)):
                        lines.add(node.lineno)
        if lines:
            out[rel] = lines
    return out


def parse_site(site) -> tuple[str, int] | None:
    """('rel/path.py', line) from a recorded site, whatever checkout recorded it."""
    if not isinstance(site, str) or ":" not in site:
        return None
    path, _, line = site.rpartition(":")
    if not line.isdigit():
        return None
    path = _re.sub(r"^(?:\.\./)+", "", path)
    path = _re.sub(r"^.*?/(?:ref|cand)/", "", path)
    return path, int(line)


def usage_functions(repo: pathlib.Path, names, records=()) -> dict[str, list[str]]:
    """repo-relative file -> qualified names of the project functions that use the library.

    The static scan supplies the candidates; recorded call sites (library-boundary
    records from a reference run) are added so that a use the scan could not
    resolve is still covered. Test files are never usage sites: a test
    function returns nothing, so comparing it would verify nothing.
    """
    sites = {rel: set(ls) for rel, ls in static_use_sites(repo, names).items()}
    for r in records:
        if r.get("level") == "usage":
            continue
        ps = parse_site(r.get("site"))
        if ps and not is_test_path(ps[0]) and (repo / ps[0]).exists():
            sites.setdefault(ps[0], set()).add(ps[1])
    out: dict[str, list[str]] = {}
    for rel, lines in sorted(sites.items()):
        try:
            tree = _ast.parse((repo / rel).read_bytes())
        except Exception:
            continue
        defs = defs_index(tree)
        fns = {enclosing_function(defs, ln) for ln in lines}
        fns.discard(None)
        if fns:
            out[rel] = sorted(fns)
    return out


def site_functions(repo: pathlib.Path, records) -> dict[str, str]:
    """recorded site -> 'rel::qualname' of its enclosing wrappable function, where one exists."""
    cache: dict[str, list] = {}
    out: dict[str, str] = {}
    for r in records:
        if r.get("level") == "usage":
            continue
        site = r.get("site")
        ps = parse_site(site)
        if not ps or is_test_path(ps[0]):
            continue
        rel, line = ps
        if rel not in cache:
            try:
                cache[rel] = defs_index(_ast.parse((repo / rel).read_bytes()))
            except Exception:
                cache[rel] = []
        fn = enclosing_function(cache[rel], line)
        if fn:
            out[site] = rel + "::" + fn
    return out


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
    - a value longer than the display cap carries a hash of the whole; the
      hash decides equality, so nothing past the cap is invisible
    - opaque objects compare by type name, address-stripped repr, length, and
      their public non-callable attributes recursively (depth 2); a differing
      repr or attribute is reported as a *difference*, not a pass
    """
    if type(a) is not type(b):
        return False
    if not isinstance(a, dict):
        return a == b
    if a.get("n") != b.get("n"):
        return False
    if a.get("t") != b.get("t"):
        # A replacement returns its own class where the library returned its
        # own: a type name is not behaviour. Two values of different type are
        # equal when both are containers with equal elements, or both are
        # objects with equal public attributes and length. A primitive against
        # anything else is still a difference.
        structural = (("items" in a and "items" in b) or ("attrs" in a and "attrs" in b)
                      or ("list" in a and "list" in b))
        if not structural:
            return False
    t = a.get("t")
    if t == "float":
        return _floats_equal(a.get("v"), b.get("v"))
    if "h" in a or "h" in b:
        # a truncated or large value: the hash of the whole thing decides, not
        # the prefix or the elided repr
        return (a.get("h") == b.get("h") and a.get("n") == b.get("n")
                and a.get("shape") == b.get("shape"))
    if "items" in a or "items" in b:
        ia, ib = a.get("items") or [], b.get("items") or []
        if len(ia) != len(ib):
            return False
        return all(values_equal(x, y) for x, y in zip(ia, ib))
    if "attrs" in a or "attrs" in b:
        aa, bb = a.get("attrs") or {}, b.get("attrs") or {}
        if set(aa) != set(bb) or not all(values_equal(aa[k], bb[k]) for k in aa):
            return False
    if a.get("len") != b.get("len"):
        return False
    for k in ("v", "r", "shape", "dtype", "size"):
        if a.get(k) != b.get(k):
            if k == "r" and ("attrs" in a or "attrs" in b or a.get("t") != b.get("t")):
                continue        # the repr names the class; the attributes decided
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
