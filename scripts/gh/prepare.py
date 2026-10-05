#!/usr/bin/env python3
"""Prepare a results directory and dataset subset for one evaluation set.

Sets:
  gold       prediction = the oracle patch (harness sanity check, EPR ceiling)
  recovered  prediction = patches under predictions/<model>/python/<iid>/patch.diff
  mutation   one prediction per (instance, oracle dependency): the oracle manifest
             with that single dependency deleted. Instance ids become <iid>__del__<dep>
             and repo-data gets a symlink per mutant.
"""
import argparse, json, os, pathlib, re, shutil, subprocess, sys, tempfile, uuid
try:
    import tomllib
except ImportError:  # Python < 3.11
    import tomli as tomllib

NAME_RE = re.compile(r"^\s*([A-Za-z0-9][A-Za-z0-9._-]*)")


def norm(n):
    return n.lower().replace("-", "_").replace(".", "_")


def apply_patch_text(repo: pathlib.Path, bf: str, patch: str):
    with tempfile.TemporaryDirectory() as td:
        td = pathlib.Path(td)
        (td / bf).parent.mkdir(parents=True, exist_ok=True)
        shutil.copy(repo / bf, td / bf)
        (td / "p.diff").write_text(patch)
        r = subprocess.run(["git", "apply", "--allow-empty", "--ignore-whitespace", "--ignore-space-change", "p.diff"], cwd=td, capture_output=True, text=True)
        if r.returncode != 0:
            shutil.copy(repo / bf, td / bf)
            r = subprocess.run(["patch", "--batch", "--fuzz=5", "-p1", "-i", "p.diff"], cwd=td, capture_output=True, text=True)
            if r.returncode != 0:
                return None
        return (td / bf).read_text()


def git_diff(bf: str, old: str, new: str) -> str:
    with tempfile.TemporaryDirectory() as td:
        td = pathlib.Path(td)
        subprocess.run(["git", "init", "-q"], cwd=td, check=True)
        subprocess.run(["git", "-c", "user.email=a@b", "-c", "user.name=a", "commit", "-q", "--allow-empty", "-m", "init"], cwd=td, check=True)
        (td / bf).parent.mkdir(parents=True, exist_ok=True)
        (td / bf).write_text(old)
        subprocess.run(["git", "add", bf], cwd=td, check=True)
        subprocess.run(["git", "-c", "user.email=a@b", "-c", "user.name=a", "commit", "-q", "-m", "old"], cwd=td, check=True)
        (td / bf).write_text(new)
        return subprocess.run(["git", "diff"], cwd=td, capture_output=True, text=True).stdout


def section_span(text: str, header_regex: str):
    m = re.search(header_regex, text, re.M)
    if not m:
        return None
    nxt = re.search(r"^\[", text[m.end():], re.M)
    end = m.end() + nxt.start() if nxt else len(text)
    return m.start(), end


def balanced_end(text: str, i: int) -> int:
    """i points at an opening [ or {; return index after the matching close."""
    depth = 0; in_str = None; j = i
    while j < len(text):
        c = text[j]
        if in_str:
            if c == "\\":
                j += 2; continue
            if c == in_str:
                in_str = None
        elif c in ('"', "'"):
            in_str = c
        elif c in "[{":
            depth += 1
        elif c in "]}":
            depth -= 1
            if depth == 0:
                return j + 1
        j += 1
    return -1


def mutants_for(text: str):
    """Yield (dep_name, mutant_text) for each declared runtime dependency."""
    data = tomllib.loads(text)
    poetry = data.get("tool", {}).get("poetry", {})
    if poetry:
        deps = poetry.get("dependencies") or {}
        span = section_span(text, r"^\[tool\.poetry\.dependencies\]\s*$")
        if not span:
            return
        s, e = span
        body = text[s:e]
        for key in deps:
            if key.lower() == "python":
                continue
            m = re.search(r'^[ \t]*"?' + re.escape(key) + r'"?[ \t]*=[ \t]*', body, re.M)
            if not m:
                continue
            k = m.end()
            if k < len(body) and body[k] in "[{":
                k = balanced_end(body, k)
                if k < 0:
                    continue
            nl = body.find("\n", k)
            k = len(body) if nl < 0 else nl + 1
            yield key, text[:s] + body[: m.start()] + body[k:] + text[e:]
        return
    proj = data.get("project")
    if proj is None:
        return
    span = section_span(text, r"^\[project\]\s*$")
    if not span:
        return
    s, e = span
    body = text[s:e]
    m = re.search(r"^dependencies[ \t]*=[ \t]*\[", body, re.M)
    if not m:
        return
    a = m.end() - 1
    b = balanced_end(body, a)
    if b < 0:
        return
    entries = proj.get("dependencies") or []
    for target in entries:
        tm = NAME_RE.match(target)
        if not tm:
            continue
        keep = [d for d in entries if d != target]
        arr = "[\n" + "".join(f"    {json.dumps(d)},\n" for d in keep) + "]"
        yield tm.group(1), text[:s] + body[:a] + arr + body[b:] + text[e:]


def declared(text: str) -> set:
    data = tomllib.loads(text)
    poetry = data.get("tool", {}).get("poetry", {})
    if poetry:
        return {norm(k) for k in (poetry.get("dependencies") or {}) if k.lower() != "python"}
    out = set()
    for d in data.get("project", {}).get("dependencies", []) or []:
        m = NAME_RE.match(d)
        if m:
            out.add(norm(m.group(1)))
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--set", required=True, choices=["gold", "recovered", "mutation", "cheats", "agent", "blocked", "blocked_large", "scoped", "scoped_large", "all", "all_large"])
    ap.add_argument("--dataset", required=True)
    ap.add_argument("--repo-data", required=True)
    ap.add_argument("--predictions", default="predictions/qwen2.5-coder-7b")
    ap.add_argument("--out-results", required=True)
    ap.add_argument("--out-dataset", required=True)
    ap.add_argument("--limit", type=int, default=0)
    ap.add_argument("--count-only", action="store_true")
    a = ap.parse_args()

    rows = [json.loads(l) for l in open(a.dataset) if l.strip()]
    rows = [r for r in rows if r["language"].lower() == "python"]
    if a.limit > 0:
        rows = rows[: a.limit]
    repo_data = pathlib.Path(a.repo_data)
    out_results = pathlib.Path(a.out_results)
    fields = ["instance_id", "metadata", "language", "act_command", "ci_file", "patch", "build_files", "env_specs"]
    out_rows = []
    skipped = []

    if a.set in ("cheats", "agent", "blocked", "blocked_large", "scoped", "scoped_large", "all", "all_large"):
        # pre-built variants: pilot/<set>.jsonl rows (mutant-style ids <iid>__<kind>__<dep>) and
        # predictions/<set>/python/<id>/patch.diff; each needs a repo-data symlink to its base instance
        src_rows = [json.loads(l) for l in open(pathlib.Path("pilot") / f"{a.set}.jsonl") if l.strip()]
        if a.limit > 0:
            src_rows = src_rows[: a.limit]
        for r in src_rows:
            mid = r["instance_id"]; base = mid.split("__", 1)[0]
            pf = pathlib.Path("predictions") / a.set / "python" / mid / "patch.diff"
            if not pf.exists() or not (repo_data / "python" / base).exists():
                skipped.append(mid); continue
            out_rows.append({k: r[k] for k in fields})
            if not a.count_only:
                d = out_results / "python" / mid
                d.mkdir(parents=True, exist_ok=True)
                (d / "patch.diff").write_text(pf.read_text())
                link = repo_data / "python" / mid
                if not link.exists():
                    os.symlink(base, link)
    elif a.set in ("gold", "recovered"):
        for r in rows:
            iid = r["instance_id"]
            if a.set == "gold":
                patch = r["patch"]
            else:
                pf = pathlib.Path(a.predictions) / "python" / iid / "patch.diff"
                if not pf.exists():
                    skipped.append(iid); continue
                patch = pf.read_text()
            out_rows.append({k: r[k] for k in fields})
            if not a.count_only:
                d = out_results / "python" / iid
                d.mkdir(parents=True, exist_ok=True)
                (d / "patch.diff").write_text(patch)
    else:
        for r in rows:
            iid = r["instance_id"]
            bf = r["build_files"][0]
            repo = repo_data / "python" / iid
            if not repo.exists():
                skipped.append(iid); continue
            masked = (repo / bf).read_text()
            oracle = apply_patch_text(repo, bf, r["patch"])
            if oracle is None:
                skipped.append(iid); continue
            try:
                base = declared(oracle)
            except Exception:
                skipped.append(iid); continue
            for dep, mutant in mutants_for(oracle):
                try:
                    got = declared(mutant)
                except Exception:
                    skipped.append(f"{iid}:{dep}:toml"); continue
                if got != base - {norm(dep)}:
                    skipped.append(f"{iid}:{dep}:mismatch"); continue
                mid = f"{iid}__del__{norm(dep)}"
                row = {k: r[k] for k in fields}
                row["instance_id"] = mid
                out_rows.append(row)
                if not a.count_only:
                    d = out_results / "python" / mid
                    d.mkdir(parents=True, exist_ok=True)
                    (d / "patch.diff").write_text(git_diff(bf, masked, mutant))
                    link = repo_data / "python" / mid
                    if not link.exists():
                        os.symlink(iid, link)

    if a.count_only:
        print(len(out_rows))
        return
    pathlib.Path(a.out_dataset).parent.mkdir(parents=True, exist_ok=True)
    with open(a.out_dataset, "w") as f:
        for r in out_rows:
            f.write(json.dumps(r) + "\n")
    print(f"set={a.set} instances={len(out_rows)} skipped={len(skipped)}", file=sys.stderr)
    if skipped:
        print("skipped:", skipped[:40], file=sys.stderr)


if __name__ == "__main__":
    main()
