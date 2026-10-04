#!/usr/bin/env python3
"""Aggregate eval-result.json files into a markdown summary (and JSON)."""
import collections, json, pathlib, sys

root = pathlib.Path(sys.argv[1])
out_md = pathlib.Path(sys.argv[2]) if len(sys.argv) > 2 else None
rows = []
for f in sorted(root.rglob("eval-result.json")):
    try:
        rows.append(json.load(open(f)))
    except Exception:
        pass
n = len(rows)
passed = sum(r.get("exec") == "pass" for r in rows)
failed = sum(r.get("exec") == "fail" for r in rows)
other = n - passed - failed
tp = fp = fn = 0
for r in rows:
    t = ((r.get("text") or {}).get("name_only")) or {}
    tp += t.get("TP", 0); fp += t.get("FP", 0); fn += t.get("FN", 0)
P = tp / (tp + fp) if tp + fp else 0.0
R = tp / (tp + fn) if tp + fn else 0.0
F = 2 * P * R / (P + R) if P + R else 0.0
lines = ["## DI-Bench evaluation summary", "", "| Measure | Value |", "| --- | --- |",
         f"| Instances with a result | {n} |", f"| Execution pass | {passed} |", f"| Execution fail | {failed} |",
         f"| No execution result | {other} |", f"| Execution pass rate | {passed / n:.3f} |" if n else "| Execution pass rate | n/a |",
         f"| Name-only precision / recall / F1 | {P:.3f} / {R:.3f} / {F:.3f} |", ""]
mut = [r for r in rows if "__del__" in r.get("instance_id", "")]
summary = dict(n=n, exec_pass=passed, exec_fail=failed, exec_none=other, name_only=dict(TP=tp, FP=fp, FN=fn, P=P, R=R, F1=F))
if mut:
    invisible = [r for r in mut if r.get("exec") == "pass"]
    by_inst = collections.defaultdict(lambda: [0, 0])
    for r in mut:
        base = r["instance_id"].split("__del__")[0]
        by_inst[base][1] += 1
        if r.get("exec") == "pass":
            by_inst[base][0] += 1
    inst_with_inv = sum(1 for v in by_inst.values() if v[0] > 0)
    lines += ["### Dependency mutation score", "", "| Measure | Value |", "| --- | --- |",
              f"| Deletion mutants evaluated | {len(mut)} |",
              f"| Deletions that still pass CI (invisible to EPR) | {len(invisible)} |",
              f"| Invisible fraction | {len(invisible) / len(mut):.3f} |",
              f"| Instances covered | {len(by_inst)} |", f"| Instances with at least one invisible dependency | {inst_with_inv} |", "",
              "| Instance | Deleted dependency | CI result |", "| --- | --- | --- |"]
    for r in sorted(mut, key=lambda r: r["instance_id"]):
        base, dep = r["instance_id"].split("__del__", 1)
        lines.append(f"| {base} | {dep} | {r.get('exec')} |")
    summary["mutation"] = dict(n=len(mut), invisible=len(invisible), instances=len(by_inst), instances_with_invisible=inst_with_inv,
                               invisible_list=[r["instance_id"] for r in invisible])
else:
    lines += ["| Instance | Execution | name-only TP / FP / FN |", "| --- | --- | --- |"]
    for r in sorted(rows, key=lambda r: r.get("instance_id", "")):
        t = ((r.get("text") or {}).get("name_only")) or {}
        lines.append(f"| {r.get('instance_id')} | {r.get('exec')} | {t.get('TP', 0)} / {t.get('FP', 0)} / {t.get('FN', 0)} |")
md = "\n".join(lines) + "\n"
print(md)
if out_md:
    out_md.write_text(md)
    out_md.with_suffix(".json").write_text(json.dumps(summary, indent=1))
