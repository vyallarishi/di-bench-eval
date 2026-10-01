#!/usr/bin/env python3
"""Split invisible deletion mutants by mechanism.

usage: mechanism.py <gold_results_dir> <mutation_results_dir> [<out.md>]

For every mutant of a gold-passing instance whose CI still passed after the
dependency was deleted, decide from the CI log whether the package was
installed anyway (a phantom dependency, pulled in transitively or by a tox/CI
install list) or genuinely absent while the tests stayed green (a test blind spot).
"""
import collections, json, pathlib, re, sys

gold_root, mut_root = pathlib.Path(sys.argv[1]), pathlib.Path(sys.argv[2])
out_md = pathlib.Path(sys.argv[3]) if len(sys.argv) > 3 else None
PREFIX = re.compile(r"^\[[^\]]*\]\s*\|?\s*", re.M)


def load(root):
    out = {}
    for f in root.rglob("eval-result.json"):
        try:
            d = json.load(open(f)); out[d["instance_id"]] = (d, f)
        except Exception:
            pass
    return out


def installed_anyway(dep: str, log: str) -> bool:
    name = re.escape(dep).replace(r"\_", "[-_.]").replace(r"\-", "[-_.]").replace(r"\.", "[-_.]")
    pats = [
        rf"(?i)\b{name}-\d",                       # pip: flask-3.0.0 in "Successfully installed"
        rf"(?i)\b{name}==\d",                      # tox / pip freeze: Flask==3.0.0
        rf"(?i)\b(?:Installing|Updating|Downgrading) {name} \(\d",  # poetry
        rf"(?i)Requirement already satisfied: {name}\b",
        rf"(?i)\bcollected packages:.*\b{name}\b",
    ]
    return any(re.search(p, log) for p in pats)


gold = load(gold_root); mut = load(mut_root)
gold_pass = {k for k, (d, _) in gold.items() if d.get("exec") == "pass"}
rows = []
for mid, (d, f) in mut.items():
    base, dep = mid.split("__del__", 1)
    if base not in gold_pass:
        continue
    log = f.parent / "eval-workspace" / "exec-output.log"
    txt = PREFIX.sub("", log.read_text(errors="ignore")) if log.exists() else ""
    rows.append(dict(base=base, dep=dep, exec=d.get("exec"), installed=installed_anyway(dep, txt), has_log=bool(txt)))
inv = [r for r in rows if r["exec"] == "pass"]
vis = [r for r in rows if r["exec"] == "fail"]
mech = collections.Counter("phantom: installed anyway" if r["installed"] else "blind spot: absent, tests pass" for r in inv)
per_inst = collections.defaultdict(lambda: collections.Counter())
for r in rows:
    per_inst[r["base"]]["mutants"] += 1
    if r["exec"] == "pass":
        per_inst[r["base"]]["phantom" if r["installed"] else "blind"] += 1
lines = ["## Mechanism behind invisible deletions (gold-passing instances)", "",
         "| Measure | Value |", "| --- | --- |",
         f"| Mutants of gold-passing instances | {len(rows)} |",
         f"| Deletions that still passed CI | {len(inv)} ({len(inv) / max(len(rows), 1):.3f}) |",
         f"| of which phantom, package installed anyway | {mech['phantom: installed anyway']} |",
         f"| of which blind spot, package absent and tests still pass | {mech['blind spot: absent, tests pass']} |",
         f"| Blind-spot fraction of all mutants | {mech['blind spot: absent, tests pass'] / max(len(rows), 1):.3f} |",
         f"| Visible deletions where the package was indeed absent (sanity) | {sum(not r['installed'] for r in vis)} of {len(vis)} |",
         f"| Instances with at least one blind-spot deletion | {sum(1 for c in per_inst.values() if c['blind'])} of {len(per_inst)} |", "",
         "| Instance | Mutants | Phantom | Blind spot |", "| --- | --- | --- | --- |"]
for base, c in sorted(per_inst.items(), key=lambda kv: (-kv[1]["blind"], kv[0])):
    lines.append(f"| {base} | {c['mutants']} | {c['phantom']} | {c['blind']} |")
lines += ["", "| Instance | Deleted dependency | Mechanism |", "| --- | --- | --- |"]
for r in sorted(inv, key=lambda r: (r["base"], r["dep"])):
    lines.append(f"| {r['base']} | {r['dep']} | {'phantom' if r['installed'] else 'blind spot'} |")
md = "\n".join(lines) + "\n"
print(md)
if out_md:
    out_md.write_text(md)
