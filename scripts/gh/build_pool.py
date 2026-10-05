#!/usr/bin/env python3
"""Assemble the verified removal benchmark from execution results.

A pair (repository, dependency) enters the pool only if CI *fails* when the
dependency is removed, on a repository whose gold manifest *passes* in the same
harness. Three result sets feed it:

  regular / deletion   plain-deletion mutants   <iid>__del__<dep>    (DI-Bench regular)
  regular / blocked    import-blocked mutants   <iid>__block__<dep>  (the 91 log-phantoms re-screened)
  large   / blocked    import-blocked mutants   <iid>__block__<dep>  (DI-Bench large)

A failure only counts if an agent could, in principle, make it pass again by
editing the repository (the pair must be *winnable*). The CI log decides:

  deletion   the missing-module error must be raised from the repository's own
             frame. Raised from a third-party package, the dependency was only
             patching that package's under-declaration -> excluded. A failure
             with no import error at all (a test assertion, a linter) is CI
             detecting the removal through another route -> kept.
  blocked    the blocker's own message must appear and, in the first (unscoped)
             screening, come from a repository frame. When a result from the
             origin-scoped re-screen exists it is authoritative: its message is
             only ever raised for repository frames.

Excluded pairs are written next to the pool (<out>.excluded.jsonl) with the
reason, so the paper can account for every candidate.

Each row carries the static footprint of the removed package (which files import
it, whether a test reaches them, attribute-level uses) and a tier derived from
the non-test footprint:

  indirect  0 files      package reached only indirectly (plugin, entry point, CLI)
  strong    1-2 files    the original pilot's "strong" tier
  medium    3-4 files    the original pilot's "medium" tier
  hard      5+ files

usage: build_pool.py --out pilot/instances.jsonl
         --gold-regular DIR --mutation DIR --blocked-regular DIR
         --gold-large DIR --blocked-large DIR [--repo-data .cache/repo-data]
"""
from __future__ import annotations

import argparse
import collections
import json
import pathlib
import re
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
from footprint import RepoIndex, import_names  # noqa: E402
from manifests import norm, declared  # noqa: E402
from make_blocked import apply_patch  # noqa: E402

BLOCK_MSG = re.compile(r"blocked: dependency")


def load_results(d: pathlib.Path) -> dict[str, dict]:
    """instance_id -> {exec, log_path}. Accepts flat <id>.json or nested eval-result.json."""
    out = {}
    for f in list(d.rglob("eval-result.json")) + list(d.glob("*.json")):
        try:
            r = json.loads(f.read_text())
        except Exception:
            continue
        iid = r.get("instance_id")
        if not iid or "exec" not in r:
            continue
        log = f.parent / "eval-workspace" / "exec-output.log"
        out[iid] = dict(exec=r["exec"], log=log if log.exists() else None)
    return out


def gold_pass(d: pathlib.Path) -> set[str]:
    return {i for i, r in load_results(d).items() if r["exec"] == "pass"}


def split_id(mid: str):
    for sep in ("__block__", "__del__"):
        if sep in mid:
            base, dep = mid.split(sep, 1)
            return base, dep, "blocked" if sep == "__block__" else "deletion"
    return None


ANSI = re.compile(r"\x1b\[[0-9;]*m")
PFX = re.compile(r"^\[[^\]]*\]\s*\|\s?")          # act's "[job/step] | " prefix
PYTEST_FRAME = re.compile(r"^(\S+?):\d+: in ")
PLAIN_FRAME = re.compile(r'^\s*File "([^"]+)", line \d+')
MISSING = re.compile(r"No module named '([\w.]+)'")
FAILED_STEP = re.compile(r"❌\s+Failure - (?:Main )?(.+?)\s*$")


def frame_origin(path: str) -> str:
    if re.search(r"(site|dist)-packages/", path):
        return "foreign"
    if re.search(r"/lib/python3[.\d]*/|<frozen", path):
        return "stdlib"
    if re.search(r"(^|/)(tests?|testing)/|(^|/)test_[^/]+\.py$|conftest\.py$", path):
        return "repo-tests"
    return "repo-code"


def read_log(path: pathlib.Path) -> list[str]:
    return [PFX.sub("", ANSI.sub("", l)).rstrip()
            for l in path.read_text(errors="ignore").splitlines()]


def import_error_origins(lines: list[str], marker: re.Pattern) -> collections.Counter:
    """Origins of the frames that raised each error line matching `marker`."""
    out = collections.Counter()
    for i, l in enumerate(lines):
        if not marker.search(l):
            continue
        origin = "unknown"
        for j in range(i - 1, max(-1, i - 80), -1):
            m = PYTEST_FRAME.match(lines[j]) or PLAIN_FRAME.match(lines[j])
            if m:
                path = m.group(1)
                if "importlib" in path or "<frozen" in path:
                    continue
                if path.endswith(("conftest.py", "sitecustomize.py")) and "find_spec" in lines[j]:
                    continue
                if path.endswith(("conftest.py", "sitecustomize.py")) and "__getattr__" in lines[j]:
                    continue
                origin = frame_origin(path)
                break
        out[origin] += 1
    return out


INSTALL_STEP = re.compile(r"install|lock|setup|depend|poetry|pip|environment|build", re.I)
LINT_STEP = re.compile(r"lint|mypy|flake8|pyright|ruff|type|format|check", re.I)


def names_of(dep: str) -> set[str]:
    """Import roots the removed package could plausibly provide."""
    d = norm(dep)
    names = set(import_names(dep)) | {d}
    names |= set(d.split("_"))            # readability_lxml -> readability, pinecone_client -> pinecone
    return {n for n in names if len(n) > 2}


def classify(r: dict, kind: str, dep: str):
    """(evidence, origin) for a kept pair, or (None, reason) for an excluded one."""
    if r["exec"] != "fail":
        return None, "blind spot: CI passes"
    if r["log"] is None:
        return ("ci_fail_unlogged", "unknown") if kind == "deletion" else (None, "no log")
    lines = read_log(r["log"])
    steps = [FAILED_STEP.search(l).group(1) for l in lines if FAILED_STEP.search(l)]
    step = steps[0] if steps else ""
    if kind != "deletion":
        origins = import_error_origins(lines, BLOCK_MSG)
        if origins:
            if origins["repo-code"] + origins["repo-tests"] or kind == "scoped":
                # the scoped blocker fires only for repository frames (its raising
                # frame is the guard itself), so the marker alone is conclusive
                return "blocked_import_in_repo_frame", "repo"
            return None, "undetermined: blocked import came from another package (needs scoped re-screen)"
        # no block message: the package was not phantom after all, so this is a
        # plain deletion and the deletion rules below apply
    if step and INSTALL_STEP.search(step) and not re.search(r"test|tox|nox|pytest", step, re.I):
        return None, f"install step failed ({step.strip()})"
    origins = import_error_origins(lines, MISSING)
    missing = {m.group(1).split(".")[0] for l in lines for m in [MISSING.search(l)] if m}
    repo = origins["repo-code"] + origins["repo-tests"]
    if repo:
        if missing & names_of(dep):
            return "missing_module_in_repo_frame", "repo"
        return None, f"removal exposed an undeclared sibling dependency ({', '.join(sorted(missing))})"
    if origins["foreign"]:
        return None, "unwinnable or framework-loaded: missing module raised inside another package"
    if origins:
        return None, "missing module raised from an unidentifiable frame"
    if any(re.search(r"would reformat .*(sitecustomize|conftest)\.py", l) for l in lines):
        return None, "construction artifact: formatter rejected the injected blocker file"
    # no import error of any kind: a linter or a test noticed the removal
    if step and LINT_STEP.search(step):
        names = names_of(dep)
        if any(re.search(r"error|E0401|I900|import-not-found|could not be resolved", l)
               and any(n in l.lower() for n in names) for l in lines):
            return "linter_step_failed", "repo"
        return None, f"lint failure that does not name the package ({step.strip()})"
    return "test_failure_without_import_error", "repo"


def tier_of(n_src: int) -> str:
    if n_src == 0:
        return "indirect"
    if n_src <= 2:
        return "strong"
    if n_src <= 4:
        return "medium"
    return "hard"


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", required=True)
    ap.add_argument("--gold-regular", required=True)
    ap.add_argument("--mutation", required=True)
    ap.add_argument("--blocked-regular", required=True)
    ap.add_argument("--gold-large", required=True)
    ap.add_argument("--blocked-large", required=True)
    ap.add_argument("--scoped-regular", default=None, help="origin-scoped re-screen results")
    ap.add_argument("--scoped-large", default=None)
    ap.add_argument("--repo-data", default=".cache/repo-data")
    ap.add_argument("--phantom-pred", default="oracle-blindness/data/phantom_pred.json")
    ap.add_argument("--datasets", nargs="*",
                    default=[".cache/dataset-dibench-regular.jsonl", ".cache/dataset-dibench-large.jsonl"])
    a = ap.parse_args()

    build_file, gold_declared = {}, {}
    repo_data = pathlib.Path(a.repo_data) / "python"
    for ds in a.datasets:
        p = pathlib.Path(ds)
        if not p.exists():
            continue
        for line in open(p):
            if not line.strip():
                continue
            r = json.loads(line)
            iid, bf = r["instance_id"], r["build_files"][0]
            build_file[iid] = bf
            repo = repo_data / iid
            if (repo / bf).exists():
                try:
                    gold_declared[iid] = declared(bf, apply_patch(repo, bf, r["patch"]))
                except Exception:
                    pass

    phantom_pred = {}
    pp = pathlib.Path(a.phantom_pred)
    if pp.exists():
        raw = json.load(open(pp))
        # {"iid": {"dep": bool}} (phantom_predict.py) or [{"instance_id","dependency","predicted"}]
        if isinstance(raw, dict):
            for iid, deps in raw.items():
                for dep, v in deps.items():
                    phantom_pred[(iid, norm(dep))] = bool(v)
        else:
            for e in raw:
                phantom_pred[(e["instance_id"], norm(e["dependency"]))] = bool(
                    e.get("predicted", e.get("phantom_predicted")))

    def blocked_results(broad_dir, scoped_dir):
        """Broad screening results, overridden per mutant by the scoped re-screen."""
        res = {k: dict(v, kind="blocked") for k, v in load_results(pathlib.Path(broad_dir)).items()}
        if scoped_dir and pathlib.Path(scoped_dir).exists():
            for k, v in load_results(pathlib.Path(scoped_dir)).items():
                res[k] = dict(v, kind="scoped")
        return res

    gold_reg, gold_lg = gold_pass(pathlib.Path(a.gold_regular)), gold_pass(pathlib.Path(a.gold_large))
    sources = [
        ("regular", "deletion", gold_reg,
         {k: dict(v, kind="deletion") for k, v in load_results(pathlib.Path(a.mutation)).items()}),
        ("regular", "blocked", gold_reg, blocked_results(a.blocked_regular, a.scoped_regular)),
        ("large", "blocked", gold_lg, blocked_results(a.blocked_large, a.scoped_large)),
    ]
    gold_counts = {"regular": len(gold_reg), "large": len(gold_lg)}

    rows, excluded, seen = [], [], set()
    stats = collections.Counter()
    for subset, family, gold, results in sources:
        for mid, r in results.items():
            s = split_id(mid)
            if not s or s[2] != family:
                continue
            base, dep, _ = s
            if base not in gold:
                stats[f"{subset}/{family}: gold-failing repo"] += 1
                continue
            if base in gold_declared and norm(dep) not in gold_declared[base]:
                stats[f"{subset}/{family}: not a declared dependency (parser artifact)"] += 1
                continue
            stats[f"{subset}/{family}: conditioned"] += 1
            kind = r["kind"]
            ev, why = classify(r, kind, dep)
            key = (base, norm(dep))
            if ev is None:
                stats[f"{subset}/{family}: {why}"] += 1
                excluded.append(dict(instance_id=base, dependency=dep, subset=subset, mutant_id=mid,
                                     screened_by=kind, exec=r["exec"], reason=why))
                continue
            if key in seen:  # a deletion-verified pair also re-screened under blocking
                stats[f"{subset}/{family}: duplicate of deletion-verified pair"] += 1
                continue
            seen.add(key)
            rows.append(dict(instance_id=base, dependency=dep, subset=subset,
                             build_file=build_file.get(base), mutant_id=mid,
                             verified_by=kind, evidence=ev, deletion_ci="fail",
                             phantom_predicted=phantom_pred.get(key)))
            stats[f"{subset}/{family}: VERIFIED ({kind})"] += 1

    # static footprint, one module graph per repository
    idx_cache: dict[str, RepoIndex] = {}
    for row in rows:
        repo = repo_data / row["instance_id"]
        if not repo.is_dir():
            row.update(footprint_files=None, test_reachable=None, source_files={},
                       test_files=[], attribute_uses=None, tier="unknown")
            continue
        idx = idx_cache.get(row["instance_id"])
        if idx is None:
            idx = idx_cache[row["instance_id"]] = RepoIndex(repo)
        fp = idx.footprint(row["dependency"])
        row.update(fp)
        row["tier"] = tier_of(fp["footprint_files"])

    rows.sort(key=lambda r: (r["subset"], r["instance_id"], r["dependency"]))
    out = pathlib.Path(a.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    with open(out, "w") as f:
        for row in rows:
            f.write(json.dumps(row) + "\n")
    exc_path = out.with_suffix(".excluded.jsonl")
    with open(exc_path, "w") as f:
        for e in sorted(excluded, key=lambda e: (e["subset"], e["instance_id"], e["dependency"])):
            f.write(json.dumps(e) + "\n")

    print(f"gold-passing repositories: {gold_counts}")
    for k, v in sorted(stats.items()):
        print(f"  {v:4d}  {k}")
    print(f"\nVERIFIED POOL: {len(rows)} pairs over "
          f"{len({r['instance_id'] for r in rows})} repositories -> {out}")
    tab = collections.Counter((r["subset"], r["tier"]) for r in rows)
    for subset in ("regular", "large"):
        line = "  ".join(f"{t}={tab[(subset, t)]}" for t in ("indirect", "strong", "medium", "hard", "unknown"))
        print(f"  {subset:8s} {line}")
    by = collections.Counter((r["subset"], r["verified_by"], r["evidence"]) for r in rows)
    for k, v in sorted(by.items()):
        print(f"  {v:4d}  {k}")
    print(f"excluded candidates: {len(excluded)} -> {exc_path}")


if __name__ == "__main__":
    main()
