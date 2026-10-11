#!/usr/bin/env python3
"""Mutation analysis of the reference removals: how strong is the behavioural gate?

The problem this solves. The gate's evidence for catching semantic counterfeits
rests on the `pseudo_genuine` family, and only the handful of those variants
that happen to land on a pair with a recording can be evaluated. Building more
counterfeits of the same kind does not help: they fall in the same coverage
hole. So generate the counterfeits *where the gate can already see* -- on the
references whose replacement the recorder observes.

Each reference is a correct, hand-written rewrite of a library the project
used. Breaking one in a small way produces a *near-correct* replacement on a
pair that already has a reference trace: harder than a hand-built fake, because
everything except one detail is right. This is mutation analysis, which is the
standard way to measure an oracle's strength (DeMillo, Lipton & Sayward 1978;
Jia & Harman's survey, 2011), so the method needs no defence -- and here the
"oracle under test" is the behavioural gate while the mutants are replacements
rather than the program under test.

What is measured, per mutant: does the project's own suite still pass, and does
the gate catch it. The headline is the conditional: **of the mutants the tests
let through, the fraction the gate catches.** A mutant the tests already kill
is not evidence about the gate.

Operators are the conventional ones, applied only inside the replacement that
the reference added or changed -- never to the project's own code or its tests:

  comparison flipped          <  ->  <=,  ==  ->  !=,  >  ->  >=  ...
  boundary shifted            n  ->  n + 1  /  n - 1 on integer literals
  branch removed              an if body replaced by `pass` (keeps the else)
  constant returned           a return expression replaced by a fixed value
  boolean negated             `not x` -> `x`, `and` -> `or`
  call dropped                f(x) -> x for a single-argument call
  container emptied           a non-empty literal list/dict/set -> empty

usage:
  mutate_reference.py --module PATH [--out DIR] [--limit N] [--list]
"""
from __future__ import annotations

import argparse
import ast
import pathlib
import sys

CMP_SWAP = {
    ast.Lt: ast.LtE, ast.LtE: ast.Lt, ast.Gt: ast.GtE, ast.GtE: ast.Gt,
    ast.Eq: ast.NotEq, ast.NotEq: ast.Eq, ast.In: ast.NotIn, ast.NotIn: ast.In,
    ast.Is: ast.IsNot, ast.IsNot: ast.Is,
}


class Collect(ast.NodeVisitor):
    """Every site a mutation operator could apply to, with its kind."""

    def __init__(self):
        self.sites: list[tuple] = []

    def visit_Compare(self, node):
        for i, op in enumerate(node.ops):
            if type(op) in CMP_SWAP:
                self.sites.append(("comparison", node, i))
        self.generic_visit(node)

    def visit_Constant(self, node):
        if isinstance(node.value, int) and not isinstance(node.value, bool):
            self.sites.append(("boundary+1", node, None))
            self.sites.append(("boundary-1", node, None))
        self.generic_visit(node)

    def visit_If(self, node):
        self.sites.append(("branch", node, None))
        self.generic_visit(node)

    def visit_Return(self, node):
        if node.value is not None and not (
                isinstance(node.value, ast.Constant) and node.value.value is None):
            self.sites.append(("constant return", node, None))
        self.generic_visit(node)

    def visit_UnaryOp(self, node):
        if isinstance(node.op, ast.Not):
            self.sites.append(("negation dropped", node, None))
        self.generic_visit(node)

    def visit_BoolOp(self, node):
        self.sites.append(("and/or swapped", node, None))
        self.generic_visit(node)

    def visit_Call(self, node):
        if len(node.args) == 1 and not node.keywords:
            self.sites.append(("call dropped", node, None))
        self.generic_visit(node)

    def visit_List(self, node):
        # Load context only: emptying a list on the left of an assignment is a
        # syntax change, not a behaviour change.
        if node.elts and isinstance(getattr(node, "ctx", ast.Load()), ast.Load):
            self.sites.append(("container emptied", node, None))
        self.generic_visit(node)

    def visit_Tuple(self, node):
        self.generic_visit(node)

    def visit_Set(self, node):
        if node.elts:
            self.sites.append(("container emptied", node, None))
        self.generic_visit(node)

    def visit_Dict(self, node):
        if node.keys:
            self.sites.append(("container emptied", node, None))
        self.generic_visit(node)


class Apply(ast.NodeTransformer):
    """Apply exactly one mutation, identified by (kind, lineno, col, index)."""

    def __init__(self, kind, key, idx):
        self.kind, self.key, self.idx = kind, key, idx
        self.done = False

    def _is(self, node):
        return (getattr(node, "lineno", None), getattr(node, "col_offset", None)) == self.key

    def visit_Compare(self, node):
        self.generic_visit(node)
        if self.kind == "comparison" and self._is(node) and not self.done:
            ops = list(node.ops)
            ops[self.idx] = CMP_SWAP[type(ops[self.idx])]()
            self.done = True
            return ast.Compare(left=node.left, ops=ops, comparators=node.comparators)
        return node

    def visit_Constant(self, node):
        if self.kind.startswith("boundary") and self._is(node) and not self.done \
                and isinstance(node.value, int) and not isinstance(node.value, bool):
            self.done = True
            return ast.Constant(value=node.value + (1 if self.kind.endswith("+1") else -1))
        return node

    def visit_If(self, node):
        self.generic_visit(node)
        if self.kind == "branch" and self._is(node) and not self.done:
            self.done = True
            return ast.If(test=node.test, body=[ast.Pass()], orelse=node.orelse)
        return node

    def visit_Return(self, node):
        self.generic_visit(node)
        if self.kind == "constant return" and self._is(node) and not self.done:
            self.done = True
            # A plausible wrong answer of a plausible type, not None: returning
            # None usually raises downstream and the tests catch it, which would
            # measure the tests rather than the gate.
            return ast.Return(value=ast.Constant(value=0))
        return node

    def visit_UnaryOp(self, node):
        self.generic_visit(node)
        if self.kind == "negation dropped" and self._is(node) and not self.done \
                and isinstance(node.op, ast.Not):
            self.done = True
            return node.operand
        return node

    def visit_BoolOp(self, node):
        self.generic_visit(node)
        if self.kind == "and/or swapped" and self._is(node) and not self.done:
            self.done = True
            op = ast.Or() if isinstance(node.op, ast.And) else ast.And()
            return ast.BoolOp(op=op, values=node.values)
        return node

    def visit_Call(self, node):
        self.generic_visit(node)
        if self.kind == "call dropped" and self._is(node) and not self.done \
                and len(node.args) == 1 and not node.keywords:
            self.done = True
            return node.args[0]
        return node

    def _empty(self, node, maker):
        self.generic_visit(node)
        if self.kind == "container emptied" and self._is(node) and not self.done:
            self.done = True
            return maker()
        return node

    def visit_List(self, node):
        return self._empty(node, lambda: ast.List(elts=[], ctx=ast.Load()))

    def visit_Set(self, node):
        # an empty set literal is not expressible; use set()
        return self._empty(node, lambda: ast.Call(
            func=ast.Name(id="set", ctx=ast.Load()), args=[], keywords=[]))

    def visit_Dict(self, node):
        return self._empty(node, lambda: ast.Dict(keys=[], values=[]))


def mutants(src: str, limit: int = 0) -> list[tuple[str, str, int]]:
    """(kind, mutated source, line) for every applicable single mutation."""
    tree = ast.parse(src)
    c = Collect()
    c.visit(tree)
    out, seen = [], set()
    for kind, node, idx in c.sites:
        key = (getattr(node, "lineno", None), getattr(node, "col_offset", None))
        tag = (kind, key, idx)
        if tag in seen:
            continue
        seen.add(tag)
        t = Apply(kind, key, idx)
        new = t.visit(ast.parse(src))
        if not t.done:
            continue
        ast.fix_missing_locations(new)
        try:
            text = ast.unparse(new)
            ast.parse(text)                    # the mutant must be valid Python
        except Exception:
            continue
        if text == ast.unparse(ast.parse(src)):   # a no-op mutation
            continue
        out.append((kind, text, key[0] or 0))
        if limit and len(out) >= limit:
            break
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--module", required=True)
    ap.add_argument("--out", default=None)
    ap.add_argument("--limit", type=int, default=0)
    ap.add_argument("--list", action="store_true")
    a = ap.parse_args()
    src = pathlib.Path(a.module).read_text()
    ms = mutants(src, a.limit)
    import collections
    print(f"{len(ms)} mutants of {a.module}")
    for k, n in collections.Counter(k for k, _, _ in ms).most_common():
        print(f"  {n:4d}  {k}")
    if a.out:
        d = pathlib.Path(a.out)
        d.mkdir(parents=True, exist_ok=True)
        for i, (kind, text, line) in enumerate(ms):
            (d / f"m{i:04d}.py").write_text(text)
            (d / f"m{i:04d}.json").write_text(
                f'{{"kind": "{kind}", "line": {line}}}')
        print(f"-> {d}")
    if a.list:
        for i, (kind, _, line) in enumerate(ms):
            print(f"  m{i:04d}  line {line:4d}  {kind}")


if __name__ == "__main__":
    main()
