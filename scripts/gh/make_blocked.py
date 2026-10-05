#!/usr/bin/env python3
"""Build *import-blocked* deletion mutants.

A plain deletion mutant only removes a package's declaration. If another
dependency still installs it transitively, the import keeps working and CI
stays green -- so the instance looks "oracle-blind" when in fact the package
was merely still present. Those pairs cannot score an agent: deleting the
declaration and changing nothing passes.

This builds the honest version: the declaration is removed AND the package is
made genuinely unimportable at runtime, via a meta-path finder installed from
`sitecustomize.py` (covers every Python process, including subprocesses and
tox envs) and `conftest.py` (covers pytest when sitecustomize is shadowed).

A pair is *scoreable under blocking* iff CI fails with the block in place.

usage:
  make_blocked.py --dataset D --repo-data R --out-results O --out-dataset J
                  [--pairs pairs.json] [--limit N] [--count-only]

`pairs.json`: [{"instance_id":..., "dependency":...}, ...]. Defaults to every
declared dependency of every instance in the dataset.
"""
import argparse
import json
import os
import pathlib
import re
import shutil
import subprocess
import sys
import tempfile

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
import manifests as M

NAME_RE = re.compile(r"^\s*([A-Za-z0-9][A-Za-z0-9._-]*)")


def norm(n: str) -> str:
    return n.lower().replace("-", "_").replace(".", "_")


# --- import names ---------------------------------------------------------
# A package's declaration name is not always its import name. We block every
# plausible import name so the block cannot be dodged by an alias.
MANUAL = {
    "pillow": ["PIL"], "pyyaml": ["yaml"], "scikit_learn": ["sklearn"],
    "beautifulsoup4": ["bs4"], "python_dateutil": ["dateutil"],
    "opencv_python": ["cv2"], "attrs": ["attr", "attrs"],
    "protobuf": ["google"], "gitpython": ["git"], "pyjwt": ["jwt"],
    "python_dotenv": ["dotenv"], "ruamel_yaml": ["ruamel"],
    "pycryptodome": ["Crypto"], "pycryptodomex": ["Cryptodome"],
    "msgpack_python": ["msgpack"], "matplotlib": ["matplotlib", "mpl_toolkits"],
    "ipython": ["IPython"], "z3_solver": ["z3"], "dm_tree": ["tree"],
    "faiss_cpu": ["faiss"], "dnspython": ["dns"], "biopython": ["Bio"],
    "djangorestframework": ["rest_framework"], "google_auth": ["google"],
    "pyserial": ["serial"], "pymupdf": ["fitz"], "python_magic": ["magic"],
    "pyopenssl": ["OpenSSL"], "pynacl": ["nacl"], "mysqlclient": ["MySQLdb"],
    "websocket_client": ["websocket"], "python_slugify": ["slugify"],
    "pyusb": ["usb"], "python_jose": ["jose"], "pysocks": ["socks"],
    "python_multipart": ["multipart"], "google_api_python_client": ["googleapiclient"],
    "scikit_image": ["skimage"], "pywavelets": ["pywt"], "netcdf4": ["netCDF4"],
    "python_json_logger": ["pythonjsonlogger"], "pyhumps": ["humps"],
    "pyzmq": ["zmq"], "pygobject": ["gi"], "pyqt5": ["PyQt5"],
    "discord_py": ["discord"], "python_telegram_bot": ["telegram"],
    "sqlalchemy_utils": ["sqlalchemy_utils"], "typing_extensions": ["typing_extensions"],
    "importlib_metadata": ["importlib_metadata"], "backports_zoneinfo": ["backports"],
}


def import_names(dep: str) -> list[str]:
    d = norm(dep)
    names = {d}
    names.update(MANUAL.get(d, []))
    # Only strip a leading "python_"/"py" when the package is a SINGLE token.
    # "python_slugify" -> "slugify" is right; naive stripping of a multi-token
    # name yields junk like "thon_slugify" that could block something else.
    if "_" not in d:
        if d.startswith("py") and len(d) > 3:
            names.add(d[2:])
    elif d.startswith("python_"):
        names.add(d[len("python_"):])
    names.add(d.replace("_", ""))
    return sorted(n for n in names if n and not n[0].isdigit())


# --- the blocker ----------------------------------------------------------
BLOCKER = '''\
"""Injected by UnpinBench: make {dep!r} genuinely unimportable.

Removing a declaration does not uninstall a package another dependency pulls
in. Without this, a deletion mutant cannot distinguish "the tests do not
exercise this package" from "the package is still installed".
"""
import sys

_BLOCKED = {names!r}


class _BlockedFinder:
    def find_module(self, fullname, path=None):  # legacy API
        return self if self._blocked(fullname) else None

    def find_spec(self, fullname, path=None, target=None):
        if self._blocked(fullname):
            raise ImportError(
                "No module named %r (blocked: dependency %s was removed)"
                % (fullname, {dep!r})
            )
        return None

    @staticmethod
    def _blocked(fullname):
        root = fullname.split(".")[0]
        return root in _BLOCKED

    def load_module(self, fullname):
        raise ImportError("No module named %r (blocked)" % fullname)


def _install():
    if not any(isinstance(f, _BlockedFinder) for f in sys.meta_path):
        sys.meta_path.insert(0, _BlockedFinder())
    # drop anything already imported so later imports hit the finder
    for name in list(sys.modules):
        if name.split(".")[0] in _BLOCKED:
            del sys.modules[name]


_install()
'''


def write_blocker(root: pathlib.Path, dep: str, names: list[str]) -> list[str]:
    """Install the blocker so it runs for pytest and for any Python process."""
    body = BLOCKER.format(dep=dep, names=names)
    written = []

    # sitecustomize.py: imported automatically by every interpreter start.
    sc = root / "sitecustomize.py"
    sc.write_text(body)
    written.append("sitecustomize.py")

    # conftest.py at the rootdir: pytest imports it before collection. If one
    # already exists, prepend rather than clobber the project's own fixtures.
    cf = root / "conftest.py"
    if cf.exists():
        cf.write_text(body + "\n\n" + cf.read_text())
    else:
        cf.write_text(body)
    written.append("conftest.py")
    return written


# --- manifest surgery (delegated to manifests.py, which is unit- and
# property-tested over every real DI-Bench Python instance) -----------------
def declared(path: str, text: str) -> set[str]:
    return M.declared(path, text)


def remove_declaration(path: str, text: str, dep: str):
    return M.remove(path, text, dep)


# --- patch construction ---------------------------------------------------
def apply_patch(repo: pathlib.Path, bf: str, patch: str):
    with tempfile.TemporaryDirectory() as td:
        td = pathlib.Path(td)
        (td / bf).parent.mkdir(parents=True, exist_ok=True)
        shutil.copy(repo / bf, td / bf)
        (td / "p.diff").write_text(patch)
        r = subprocess.run(
            ["git", "apply", "--allow-empty", "--ignore-whitespace",
             "--ignore-space-change", "p.diff"],
            cwd=td, capture_output=True, text=True)
        if r.returncode != 0:
            shutil.copy(repo / bf, td / bf)
            subprocess.run(["patch", "--batch", "--fuzz=5", "-p1", "-i", "p.diff"],
                           cwd=td, capture_output=True, text=True)
        return (td / bf).read_text()


def multi_file_diff(files: dict[str, tuple[str | None, str]]) -> str:
    """files: path -> (old_text or None for a new file, new_text)."""
    with tempfile.TemporaryDirectory() as td:
        td = pathlib.Path(td)
        subprocess.run(["git", "init", "-q"], cwd=td, check=True)
        for rel, (old, _new) in files.items():
            if old is not None:
                (td / rel).parent.mkdir(parents=True, exist_ok=True)
                (td / rel).write_text(old)
        subprocess.run(["git", "add", "-A"], cwd=td, check=True)
        subprocess.run(["git", "-c", "user.email=a@b", "-c", "user.name=a",
                        "commit", "-q", "--allow-empty", "-m", "base"], cwd=td, check=True)
        for rel, (_old, new) in files.items():
            (td / rel).parent.mkdir(parents=True, exist_ok=True)
            (td / rel).write_text(new)
        subprocess.run(["git", "add", "-A"], cwd=td, check=True)
        return subprocess.run(["git", "diff", "--cached"], cwd=td,
                              capture_output=True, text=True).stdout


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--dataset", required=True)
    ap.add_argument("--repo-data", required=True)
    ap.add_argument("--out-results", required=True)
    ap.add_argument("--out-dataset", required=True)
    ap.add_argument("--pairs", default=None)
    ap.add_argument("--limit", type=int, default=0)
    ap.add_argument("--count-only", action="store_true")
    a = ap.parse_args()

    rows = {json.loads(l)["instance_id"]: json.loads(l)
            for l in open(a.dataset) if l.strip()}
    repo_data = pathlib.Path(a.repo_data)
    out_results = pathlib.Path(a.out_results)
    fields = ["instance_id", "metadata", "language", "act_command", "ci_file",
              "patch", "build_files", "env_specs"]

    if a.pairs:
        pairs = [(p["instance_id"], p["dependency"]) for p in json.load(open(a.pairs))]
    else:
        pairs = []
        for iid, r in rows.items():
            if r["language"].lower() != "python":
                continue
            repo = repo_data / "python" / iid
            if not repo.exists():
                continue
            try:
                gold = apply_patch(repo, r["build_files"][0], r["patch"])
                for d in declared(r["build_files"][0], gold):
                    pairs.append((iid, d))
            except Exception:
                continue
    if a.limit:
        pairs = pairs[:a.limit]

    out_rows, skipped = [], []
    for iid, dep in pairs:
        r = rows.get(iid)
        if r is None:
            skipped.append(f"{iid}: not in dataset")
            continue
        bf = r["build_files"][0]
        repo = repo_data / "python" / iid
        if not repo.exists():
            skipped.append(f"{iid}: no repo data")
            continue
        try:
            masked = (repo / bf).read_text()
            gold = apply_patch(repo, bf, r["patch"])
            base = declared(bf, gold)
            mutant = remove_declaration(bf, gold, dep)
            if mutant is None:
                skipped.append(f"{iid}/{dep}: cannot edit manifest")
                continue
            if declared(bf, mutant) != base - {norm(dep)}:
                skipped.append(f"{iid}/{dep}: manifest mismatch")
                continue
        except Exception as e:
            skipped.append(f"{iid}/{dep}: {type(e).__name__}")
            continue

        names = import_names(dep)
        mid = f"{iid}__block__{norm(dep)}"
        if not a.count_only:
            with tempfile.TemporaryDirectory() as td:
                td = pathlib.Path(td)
                blocker_files = write_blocker(td, dep, names)
                files = {bf: (masked, mutant)}
                for bfile in blocker_files:
                    old = (repo / bfile).read_text() if (repo / bfile).exists() else None
                    files[bfile] = (old, (td / bfile).read_text())
                patch = multi_file_diff(files)
            d = out_results / "python" / mid
            d.mkdir(parents=True, exist_ok=True)
            (d / "patch.diff").write_text(patch)
            link = repo_data / "python" / mid
            if not link.exists():
                os.symlink(iid, link)
        row = {k: r[k] for k in fields}
        row["instance_id"] = mid
        out_rows.append(row)

    if a.count_only:
        print(len(out_rows))
        return
    pathlib.Path(a.out_dataset).parent.mkdir(parents=True, exist_ok=True)
    with open(a.out_dataset, "w") as f:
        for row in out_rows:
            f.write(json.dumps(row) + "\n")
    print(f"blocked mutants: {len(out_rows)}, skipped: {len(skipped)}", file=sys.stderr)
    for s in skipped[:30]:
        print("  skip:", s, file=sys.stderr)


if __name__ == "__main__":
    main()
