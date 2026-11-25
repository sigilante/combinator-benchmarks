"""Vendor Avon's Reduceron ports into data/d4/ for family D4.

The five ports of Naylor and Runciman's Reduceron benchmarks (JFP 2012) in
Avon's tests/workloads/reduceron/ are skijack programs whose `main` checks
its own answer and returns True. Each is copied to data/d4/src/ and compiled
by skijack, with and without its inlining pass (Avon's run.py compiles with
it by default), at two sizes:

- full: the port as Avon has it (lists of 12, 11 queens, 16 names, 80
  conjuncts, 10 numbers);
- small: the same program with `main` cut down (SMALL below) so that copy
  mode and mini can run it too. Each small `main` is still a check whose
  answer is True: the OrdList property holds at any length (6 here), 6 queens
  have 4 solutions, the Taut proposition is a tautology for any list of names
  (4 here), Clausify's answer is one clause ([0], []) for any count (1 here;
  Avon's clausify_ref.py), and PermSort sorts any countdown (from 5 here).
  Clausify is costly even so: with 2 conjuncts copy mode passes 10^9.

The run term is `main Tt Ff`: True is bool's second constructor, so the
expected result is the atom Ff.

Usage: python3 -m bench.vendor_d4   (needs ~/avon, or $AVON_REPO, and $SKIJACK_REPO)
"""

from __future__ import annotations

import json
import os
import subprocess
import sys
from pathlib import Path

AVON = Path(os.environ.get("AVON_REPO", Path.home() / "avon"))
SKIJACK = Path(os.environ.get("SKIJACK_REPO", Path.home() / "Code/ski/skijack"))
SRC = AVON / "tests" / "workloads" / "reduceron"
OUT = Path(__file__).resolve().parent.parent / "data" / "d4"
PROGS = ("ordlist", "queens2", "taut", "clausify", "permsort")

_S = lambda n: "(" + "Suc (" * n + "Zero" + ")" * (n + 1)  # Scott numeral n
#: program: (the full port's `main` line, the small one's)
SMALL = {
    "ordlist": (None, f"main = top {_S(6)}"),
    "queens2": (None, "main = eqNat (nqueens n6) (add n2 n2)"),
    "taut": ("names = ", "names = NCons va (NCons vb (NCons vc (NCons vd NNil)))"),
    "clausify": (None, f"main = check (clausify (foldrP con atom (replicate {_S(1)} bigp)))"),
    "permsort": (None, f"main = eqList (permSort (countdown {_S(5)})) (upto (Suc Zero) {_S(5)})"),
}


def _small(text, prog):
    prefix, line = SMALL[prog]
    prefix = prefix or "main = "
    lines = text.splitlines()
    hits = [i for i, l in enumerate(lines) if l.startswith(prefix)]
    if len(hits) != 1:
        raise SystemExit(f"{prog}: expected one line starting {prefix!r}, found {len(hits)}")
    lines[hits[0]] = line
    return "\n".join(lines) + "\n"


def _rev(path):
    return subprocess.run(["git", "-C", str(path), "rev-parse", "--short", "HEAD"],
                          capture_output=True, text=True).stdout.strip()


def main():
    sys.path.insert(0, str(SKIJACK / "python"))
    sys.setrecursionlimit(1_000_000)
    import skijack as sj
    from aviary_kernel.terms import pretty
    (OUT / "src").mkdir(parents=True, exist_ok=True)
    terms = {}
    for prog in PROGS:
        full = (SRC / f"{prog}.ascii.ski").read_text()
        (OUT / "src" / f"{prog}.ascii.ski").write_text(full)
        for size, text in (("full", full), ("small", _small(full, prog))):
            for inline in (True, False):
                exp = sj.compile(text, lexicon="ascii", inline=inline)
                key = f"{prog}.{size}.{'inl' if inline else 'noinl'}"
                terms[key] = {"term": pretty(exp.terms["main"]) + " Tt Ff",
                              "changed": SMALL[prog][1] if size == "small" else None}
    meta = {"source": f"Avon tests/workloads/reduceron @ {_rev(AVON)}, compiled by skijack "
                      f"@ {_rev(SKIJACK)}", "terms": terms}
    (OUT / "LICENSE.avon").write_text((AVON / "LICENSE").read_text())
    (OUT / "SOURCE").write_text(
        f"src/*.ascii.ski: copied from Avon (github.com/sigilante/avon, MIT, LICENSE.avon)\n"
        f"tests/workloads/reduceron/ at {_rev(AVON)}: skijack ports of Naylor and Runciman's\n"
        f"Reduceron benchmarks (JFP 2012). terms.json: compiled from them by\n"
        f"bench/vendor_d4.py with skijack at {_rev(SKIJACK)}.\n")
    (OUT / "terms.json").write_text(json.dumps(meta, indent=1, sort_keys=True) + "\n")
    print(f"wrote {len(terms)} terms ({meta['source']})")


if __name__ == "__main__":
    main()
