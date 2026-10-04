#!/usr/bin/env python3
"""Join evaluation sets against the gold run.

usage: join.py <gold_results_dir> <other_results_dir> [<out.md>]

Gold failures are environment or test drift, so every other number is reported
twice: over all instances, and conditioned on instances whose gold patch passes.
"""
import collections, json, pathlib, sys


def load(root):
    out = {}
    for f in pathlib.Path(root).rglob("eval-result.json"):
        try:
            d = json.load(open(f)); out[d["instance_id"]] = d
        except Exception:
            pass
    return out


gold = load(sys.argv[1]); other = load(sys.argv[2])
out_md = pathlib.Path(sys.argv[3]) if len(sys.argv) > 3 else None
gold_pass = {k for k, v in gold.items() if v.get("exec") == "pass"}
lines = [f"Gold: {len(gold_pass)} of {len(gold)} instances pass ({len(gold_pass) / max(len(gold), 1):.3f})", ""]
is_mut = any("__del__" in k for k in other)
if not is_mut:
    rows = list(other.values())
    on_gold = [r for r in rows if r["instance_id"] in gold_pass]
    def epr(rs):
        return (sum(r.get("exec") == "pass" for r in rs), len(rs))
    a, n = epr(rows); b, m = epr(on_gold)
    lines += ["| Measure | All instances | Gold-passing instances only |", "| --- | --- | --- |",
              f"| Instances | {n} | {m} |", f"| Execution pass | {a} | {b} |",
              f"| Execution pass rate | {a / max(n, 1):.3f} | {b / max(m, 1):.3f} |"]
    fails_on_gold_fail = [r["instance_id"] for r in rows if r.get("exec") == "fail" and r["instance_id"] not in gold_pass]
    lines += ["", f"Model failures on instances where gold also fails (uninformative): {len(fails_on_gold_fail)}"]
else:
    by_base = collections.defaultdict(list)
    for k, v in other.items():
        base, dep = k.split("__del__", 1); by_base[base].append((dep, v.get("exec")))
    tot = inv = 0; tot_g = inv_g = 0; inst_g = 0; inst_g_inv = 0
    invisible = []
    for base, lst in by_base.items():
        for dep, ex in lst:
            tot += 1; inv += ex == "pass"
            if base in gold_pass:
                tot_g += 1; inv_g += ex == "pass"
                if ex == "pass": invisible.append(f"{base} / {dep}")
        if base in gold_pass:
            inst_g += 1; inst_g_inv += any(ex == "pass" for _, ex in lst)
    lines += ["| Measure | All mutants | Mutants of gold-passing instances |", "| --- | --- | --- |",
              f"| Deletion mutants | {tot} | {tot_g} |", f"| Deletions that still pass CI | {inv} | {inv_g} |",
              f"| Dependency mutation score (invisible fraction) | {inv / max(tot, 1):.3f} | {inv_g / max(tot_g, 1):.3f} |",
              f"| Gold-passing instances with at least one invisible dependency | | {inst_g_inv} of {inst_g} |", "",
              "Invisible dependencies on gold-passing instances:", ""] + [f"- {x}" for x in sorted(invisible)]
md = "\n".join(lines) + "\n"
print(md)
if out_md:
    out_md.write_text(md)
