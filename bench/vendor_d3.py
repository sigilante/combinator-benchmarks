"""Vendor SKInock's compiled Hoon programs into data/d3/ for family D3.

SKInock (github.com/sigilante/SKInock, MIT) compiles Nock formulas to closed
SKI terms. Its benchmark (`skinock.bench`) runs urbit/benchmark's
Hoon-compiled programs (MIT) at scaled-down subjects; this script takes the
same programs and subjects (`skinock.bench.SCALED`). For each run it records:

- the term `show main` (`skinock.avon.term_text`): `main` is the compiled
  program applied to its subject, and `show` rebuilds the product noun as a
  first-order term over the free atoms matom, mcell, merr, mnil, mcons, mt
  and mf, so the normal form *is* the product, printed;
- the product by SKInock's Python Nock evaluator (`skinock.nock`), the
  oracle its own tests use, and the normal form that product must print as
  (`expected_nf` below, the inverse of `skinock.avon._parse_nf`).

Terms are built straight from SKInock's term graph into a bench.termstore
store (the printed forms run to 150 MB; the graphs are a few thousand
nodes), so nothing large is printed here.

Usage: python3 -m bench.vendor_d3   (needs $SKINOCK_REPO, $SKIJACK_REPO and
urbit/benchmark at ~/Code/urbit/benchmark)
"""

from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path

from . import engines as E  # noqa: F401  (puts the canonical aviary first on sys.path)
from . import mini, termstore

SKINOCK = Path(os.environ.get("SKINOCK_REPO", Path.home() / "Code/ski/skinock"))
SKIJACK = Path(os.environ.get("SKIJACK_REPO", Path.home() / "Code/ski/skijack"))
OUT = Path(__file__).resolve().parent.parent / "data" / "d3"


def expected_nf(noun) -> str:
    """The normal form of `show main` for a product noun: an atom n is
    `matom <bits>`, its bits least significant first as `mcons mt|mf ...`
    ending in `mnil`; a cell is `mcell <head> <tail>`."""
    def bits(n):
        out = []
        while n:
            out.append("mt" if n & 1 else "mf")
            n >>= 1
        t = "mnil"
        for b in reversed(out):
            t = f"mcons {b} ({t})"
        return t

    def go(x):
        if isinstance(x, tuple):
            return f"mcell ({go(x[0])}) ({go(x[1])})"
        return f"matom ({bits(x)})"
    return mini.show(mini.parse(go(noun)))


def _rev(path):
    r = subprocess.run(["git", "-C", str(path), "rev-parse", "--short", "HEAD"],
                       capture_output=True, text=True).stdout.strip()
    return r or "?"


def main():
    sys.path[1:1] = [str(SKINOCK / "python"), str(SKIJACK / "python")]
    sys.setrecursionlimit(1_000_000)
    from aviary_kernel.terms import Atom
    from skinock import bench as SB, nock as N
    from skinock.avon import _SHOW
    from skinock.run import Program

    packer = termstore.Compressor()

    def of_text(t):  # skinock's show term, a tuple tree of names
        return t if isinstance(t, str) else packer.node(of_text(t[0]), of_text(t[1]))
    show = of_text(_SHOW)

    def of_term(root):  # an aviary term, a DAG by identity, iterative post-order
        memo, stack = {}, [(root, False)]
        while stack:
            t, done = stack.pop()
            if id(t) in memo:
                continue
            if isinstance(t, Atom):
                memo[id(t)] = t.name
            elif done:
                memo[id(t)] = packer.node(memo[id(t.fn)], memo[id(t.arg)])
            else:
                stack += [(t, True), (t.arg, False), (t.fn, False)]
        return memo[id(root)]

    progs = []
    for name, subjects in SB.SCALED.items():
        _subj0, formula = SB.load(name)
        for s in subjects:
            ev = N.Evaluator(fuel=50_000_000)
            want = ev.nock(s, formula)  # a crash or fuel here is a bug: raise
            p = Program(formula, s)
            key = f"{name}.{N.show(s).replace(' ', '_').strip('[]')}"
            packer.add_node(key, packer.node(show, of_term(p.main)))
            progs.append({"key": key, "name": name, "subject": N.show(s),
                          "product": N.show(want), "nock_steps": ev.steps,
                          "nf": expected_nf(want)})
            print(f"{key}: product {N.show(want)}, {ev.steps:,} Nock steps", flush=True)
    packed, store = packer.finish()
    for p in progs:
        p["term"] = packed[p["key"]]
    meta = {"source": f"SKInock @ {_rev(SKINOCK)} (skinock.bench programs and subjects, "
                      f"term skinock.avon.term_text), skijack @ {_rev(SKIJACK)}, "
                      f"urbit/benchmark @ {_rev(Path(SB.BAR).parent.parent)}",
            "programs": progs}
    OUT.mkdir(parents=True, exist_ok=True)
    termstore.save(OUT / "programs.json.gz", meta)
    termstore.save(OUT / "store.json.gz", store)
    (OUT / "LICENSE.skinock").write_text((SKINOCK / "LICENSE").read_text())
    print(f"wrote {len(progs)} runs, {len(store)} shared subterms ({meta['source']})")


if __name__ == "__main__":
    main()
