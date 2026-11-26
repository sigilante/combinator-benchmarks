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

    # Corrupt a single manifest row in each way the harness once let through.
    import copy
    import os
    base = next(json.loads(l) for l in (ROOT / "manifests" / "C.jsonl").open()
                if json.loads(l)["id"] == "c.mul.3.4.ski")
    corruptions = {
        "no expected nf": lambda r: r["expect"].pop("numeral"),
        "pin null on a pinned row": lambda r: r.__setitem__("pin", None),
        "empty engines": lambda r: r.__setitem__("engines", []),
        "misspelt engines": lambda r: r.__setitem__("engines", ["avon_copy"]),
        "bad mode": lambda r: r.__setitem__("mode", "NF"),
        "negative numeral": lambda r: r["expect"].__setitem__("numeral", -1),
        "share_ref off by one": lambda r: r.__setitem__("share_ref", r["share_ref"] + 1),
    }
    zpath = ROOT / "manifests" / "Z.jsonl"
    try:
        for label, mutate in corruptions.items():
            r = copy.deepcopy(base)
            mutate(r)
            zpath.write_text(json.dumps(r) + "\n")
            n = len(check.check_family("Z", list(check.E.ENGINES))[2])
            print(f"  {n:4d} failures  manifest row: {label}")
            if n == 0:
                survivors.append(label)
    finally:
        zpath.unlink(missing_ok=True)
        (ROOT / "results" / "check-Z.jsonl").unlink(missing_ok=True)

    # mini's stack-based head reducer against the original spine-rebuilding one.
    import random
    rng = random.Random(7)

    def rnd(d):
        if d == 0 or rng.random() < 0.3:
            return rng.choice(["S", "K", "I", "B", "C", "W", "x", "y"])
        return (rnd(d - 1), rnd(d - 1))
    diffs = 0
    for _ in range(5000):
        t, f = rnd(7), rng.choice([0, 1, 2, 3, 5, 8, 20, 100, 1000])
        diffs += mini._whnf(t, f) != mini._whnf_reference(t, f)
    print(f"  {'ok' if not diffs else 'FAIL':>4}      mini head reducer = reference on 5000 random terms ({diffs} differ)")
    if diffs:
        survivors.append("mini head reducer differs from its reference")

    # D1's readback: R (a Scott numeral n) must normalise to the Church
    # readback of n, on mini (which shares no code with the term's builder).
    from .families import d1_skijack as D1
    from .gen import expected_nf
    _src, T = D1._terms()
    for n in range(6):
        st, _steps, nf = mini.reduce(mini.parse(f"({D1.READ}) ({D1._nat(T, 'sec1-nat', n)})"), 10**6)
        ok = st == "NORMAL" and mini.show(nf) == expected_nf({"numeral": n})
        print(f"  {'ok' if ok else 'FAIL':>4}      D1 readback of Scott {n}")
        if not ok:
            survivors.append(f"D1 readback of {n} is wrong")

    # gen's checkpoint: a resume after a torn last line, or after a row was
    # changed, must give what an uninterrupted run gives.
    import json, tempfile
    from pathlib import Path
    from . import gen

    def ck_rows(t1):
        return [{"id": f"t.{i}", "family": "T", "basis": "ski",
                 "term": t1 if i == 1 else f"K x{i} (I x9)", "fuel": None, "mode": "nf",
                 "expect": {"status": "NORMAL", "nf": f"x{i}"}, "expect_src": "hand",
                 "pin_policy": "auto", "note": ""} for i in range(3)]

    def canon(rs):
        return [json.dumps(gen._packed_row(r), sort_keys=True) for r in rs]

    import contextlib, io
    with tempfile.TemporaryDirectory() as td, contextlib.redirect_stdout(io.StringIO()):
        ckp = Path(td) / "ck.jsonl"
        full, _ = gen.pin(ck_rows("K x1 (I x9)"))
        gen.pin(ck_rows("K x1 (I x9)"), ckp)
        lines = ckp.read_text().splitlines()
        ckp.write_text(lines[0] + "\n" + lines[1][: len(lines[1]) // 2])  # a kill mid-line
        torn_ok = (canon(gen.pin(ck_rows("K x1 (I x9)"), ckp)[0]) == canon(full)
                   and canon(gen.pin(ck_rows("K x1 (I x9)"), ckp)[0]) == canon(full))
        changed = gen.pin(ck_rows("I (K x1 (I x9))"), ckp)[0]
        stale_ok = [r["pin"]["steps"] for r in changed if r["id"] == "t.1"] == [2]
    for ok, label in ((torn_ok, "gen checkpoint resumes after a torn line"),
                      (stale_ok, "gen checkpoint re-runs a changed row")):
        print(f"  {'ok' if ok else 'FAIL':>4}      {label}")
        if not ok:
            survivors.append(label)

    # Family G's expectation is a leaf count: a wrong count, or a result cut
    # off before it could be counted, must fail.
    from .gen import outcome_problems
    lv = {"status": "NORMAL", "nf": None, "leaves": 6}
    for ok, label in ((not outcome_problems(lv, "NORMAL", "S S (S S) (S S)"), "leaf count 6 passes"),
                      (bool(outcome_problems(lv, "NORMAL", "S S (S S) S")), "leaf count 5 != 6 fails"),
                      (bool(outcome_problems(lv, "NORMAL", "S S (S S) ...")), "a cut result fails")):
        print(f"  {'ok' if ok else 'FAIL':>4}      {label}")
        if not ok:
            survivors.append(label)

    # Family F stores big terms by name (term_ref): materialize must rebuild
    # exactly the named term and give back the empty manifest term, an
    # unknown name must be refused, and a wrong normal form must still fail.
    ref = {"id": "f.right.3", "term": "", "term_ref": "f.right.3", "expect": {}}
    back = gen.materialize(ref)
    bad_ref = {"id": "x", "term": "", "term_ref": "g.right.3", "expect": {}}
    try:
        gen.materialize(bad_ref)
        refused = False
    except ValueError:
        refused = True
    fx = {"status": "NORMAL", "nf_ref": "f.dup.2"}
    for ok, label in ((back == "" and ref["term"] == "I (I (I x))", "term_ref rebuilds its term"),
                      (refused, "an unknown term_ref is refused"),
                      (not outcome_problems(fx, "NORMAL", "x x (x x)"), "nf_ref f.dup.2 passes"),
                      (bool(outcome_problems(fx, "NORMAL", "x x (x x) x")), "a wrong nf against nf_ref fails"),
                      (bool(check.validate({"id": "f.left.5.fuel+1", "term": "", "term_ref": "f.right.5",
                                            "fuel": 6, "mode": "nf", "expect": {"status": "NORMAL", "nf": "x"},
                                            "expect_src": "fuel-edge", "pin": {"steps": 5, "source": "t"}})),
                       "a swapped term_ref fails validation"),
                      (not check.validate({"id": "f.left.5.fuel+1", "term": "", "term_ref": "f.left.5",
                                           "fuel": 6, "mode": "nf", "expect": {"status": "NORMAL", "nf": "x"},
                                           "expect_src": "fuel-edge", "pin": {"steps": 5, "source": "t"}}),
                       "a row's own term_ref validates")):
        print(f"  {'ok' if ok else 'FAIL':>4}      {label}")
        if not ok:
            survivors.append(label)

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
