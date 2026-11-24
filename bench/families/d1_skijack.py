"""Family D1: SKIjack programs and the ski-in-ski quine.

- Level-0 programs from SKIjack's EXAMPLES.md, compiled by skijack and
  vendored in data/d1/terms.json (see bench/vendor_d1.py). Results are Scott
  numerals (zero z s = z, suc n z s = s n) or booleans. A numeral result is
  read back in the same reduction by R = Y SREAD with SREAD r n = n x (B f r),
  which turns the Scott numeral n into the Church readback f (f (... x)), so
  the row checks the value with `expect.numeral` as family C does. A boolean is
  applied to the atoms `yes` and `no`, as SKIjack's tests do. Expected values
  are those SKIjack's EXAMPLES.md and tests state, or arithmetic for the
  numerals built here (`expect_src: "examples"` / `"arith"`).
- The quine t = h <h> of ski-in-ski's appendix (bench/families/quine.py): its
  normal form must equal the structurally computed normal form of <t>
  (`expect.nf_ref: "d1.quine"`, resolved by bench.gen.expected_nf).

All rows are pinned by the auto policy.
"""

from __future__ import annotations

import json
from pathlib import Path

from .. import engines as E
from .. import mini
from . import quine as Q

DATA = Path(__file__).resolve().parent.parent.parent / "data" / "d1" / "terms.json"

E.define("""
SREAD r n -> n x (B f r)
""")
READ = E.to_basis("Y SREAD", "ski")


def _terms():
    d = json.loads(DATA.read_text())
    return d["source"], {k: v["term"] for k, v in d["terms"].items()}


def _nat(T, prog, n):
    """Scott numeral n from a program's own Zero and Suc."""
    t = f"({T[prog + '/Zero']})"
    for _ in range(n):
        t = f"({T[prog + '/Suc']}) ({t})"
    return t


def rows():
    src, T = _terms()
    cases = []  # (id, term, expect, expect_src, note)

    def num(cid, term, value, esrc, note):
        cases.append((cid, f"({READ}) ({term})", {"status": "NORMAL", "numeral": value}, esrc, note))

    def boolean(cid, term, value, esrc, note):
        cases.append((cid, f"({term}) yes no", {"status": "NORMAL", "nf": value}, esrc, note))

    N = lambda n: _nat(T, "sec1-nat", n)
    for f, args, val in [("inc", (4,), 5), ("dec", (3,), 2), ("dec", (0,), 0),
                         ("add", (2, 3), 5), ("add", (20, 30), 50), ("sub", (5, 2), 3),
                         ("sub", (2, 5), 0), ("sub", (40, 15), 25)]:
        term = f"({T['sec1-nat/' + f]}) " + " ".join(f"({N(a)})" for a in args)
        num(f"d1.nat.{f}.{'.'.join(map(str, args))}", term, val, "arith",
            f"EXAMPLES.md section 1: {f} {' '.join(map(str, args))}")
    A = lambda n: _nat(T, "ascii-digits", n)
    num("d1.ascii.mul.6.7", f"({T['ascii-digits/mul']}) ({A(6)}) ({A(7)})", 42, "arith",
        "ascii-digits mul 6 7")
    num("d1.literals.three", T["literals/three"], 3, "examples", "toNum Three")
    num("d1.literals.answer", T["literals/answer"], 42, "examples", "natAdd (toNum Two) 40")
    num("d1.literals.five", T["literals/five"], 5, "examples", "pred 6")
    boolean("d1.literals.isSix.five", f"({T['literals/isSix']}) ({T['literals/five']})", "no",
            "examples", "isSix five")
    boolean("d1.literals.isSix.six",
            f"({T['literals/isSix']}) (({T['literals/Suc']}) ({T['literals/five']}))", "yes",
            "examples", "isSix (Suc five)")
    num("d1.ascii.twelve", T["ascii-digits/twelve"], 12, "examples", 'parseDigits "12"')
    num("d1.ascii.fortyTwo", T["ascii-digits/fortyTwo"], 42, "examples", 'parseDigits "42"')
    boolean("d1.ascii.yes", T["ascii-digits/yes"], "yes", "examples", "isDigit '7'")
    boolean("d1.ascii.no", T["ascii-digits/no"], "no", "examples", "isDigit 'A'")
    num("d1.words.three", T["words-to-numbers/three"], 3, "examples", "words to numbers, level 0")

    out = []
    for cid, term, expect, esrc, note in cases:
        out.append({"id": cid, "family": "D1", "basis": "ski", "term": term,
                    "source": src, "fuel": None, "mode": "nf", "expect": expect,
                    "expect_src": esrc, "note": note, "pin_policy": "auto"})
    t, _ = Q.quine()
    out.append({"id": "d1.quine", "family": "D1", "basis": "ski", "term": mini.show(t),
                "source": "ski-in-ski appendix, Prop. ifix (rebuilt in bench/families/quine.py)",
                "fuel": None, "mode": "nf",
                "expect": {"status": "NORMAL", "nf": None, "nf_ref": "d1.quine"},
                "expect_src": "construction",
                "note": "t = h <h>; its normal form is the normal form of <t> (953,226 leaves)",
                "pin_policy": "auto"})
    return out


def quine_nf() -> str:
    t, _ = Q.quine()
    return mini.show(Q.normal_code(t))
