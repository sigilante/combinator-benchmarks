"""Can the checker fail? Plant bugs in mini and require each to be caught.

Each mutant replaces one of mini's rules (or its fuel accounting) and runs the
check on families A and B with mini alone. A mutant survives if it causes no
failure; any survivor makes this script exit 1. Also checks that a corrupted
pin and a corrupted expected normal form are caught.

Usage: python3 -m bench.selftest
"""

from __future__ import annotations

import sys

from . import check, mini

MUTANTS = {
    "S swaps its last two arguments": ("S", (3, lambda a: ((a[0], a[1]), (a[2], a[1])))),
    "S drops the shared argument":    ("S", (3, lambda a: ((a[0], a[2]), a[1]))),
    "K keeps the second argument":    ("K", (2, lambda a: a[1])),
    "B behaves as C":                 ("B", (3, lambda a: ((a[0], a[2]), a[1]))),
    "W does not duplicate":           ("W", (2, lambda a: (a[0], a[1]))),
    "C nests instead of swapping":    ("C", (3, lambda a: (a[0], (a[2], a[1])))),
}


def failures(fams=("A", "B")):
    return sum(len(check.check_family(f, ["mini"])[2]) for f in fams)


def main():
    survivors = []
    base = failures()
    if base:
        print(f"baseline is not clean: {base} failures")
        return 1
    orig = dict(mini.RULES)
    try:
        for name, (k, rule) in MUTANTS.items():
            mini.RULES[k] = rule
            n = failures()
            mini.RULES.clear()
            mini.RULES.update(orig)
            print(f"  {n:4d} failures  {name}")
            if n == 0:
                survivors.append(name)
    finally:
        mini.RULES.clear()
        mini.RULES.update(orig)

    whnf = mini._whnf
    mini._whnf = lambda t, b: whnf(t, b + 1)
    try:
        n = failures()
    finally:
        mini._whnf = whnf
    print(f"  {n:4d} failures  fuel off by one")
    if n == 0:
        survivors.append("fuel off by one")

    # Corrupt the expectations instead of the engine.
    import json
    from .gen import ROOT
    path = ROOT / "manifests" / "A.jsonl"
    saved = path.read_text()
    try:
        rows = [json.loads(l) for l in saved.splitlines()]
        for label, mutate in (("pin off by one", lambda r: r["pin"].__setitem__("steps", r["pin"]["steps"] + 1)),
                              ("wrong expected nf", lambda r: r["expect"].__setitem__("nf", "x9"))):
            rr = json.loads(json.dumps(rows))
            target = next(r for r in rr if r["id"] == "a.s.ski")
            mutate(target)
            path.write_text("".join(json.dumps(r, ensure_ascii=False) + "\n" for r in rr))
            n = len(check.check_family("A", ["mini"])[2])
            print(f"  {n:4d} failures  {label}")
            if n == 0:
                survivors.append(label)
    finally:
        path.write_text(saved)

    # Leave results/ as a clean run would.
    for f in ("A", "B"):
        check.check_family(f, list(check.E.ENGINES))
    if survivors:
        print("SURVIVED:", ", ".join(survivors))
        return 1
    print("all mutants caught")
    return 0


if __name__ == "__main__":
    sys.exit(main())
