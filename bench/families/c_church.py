"""Family C: Church-numeral arithmetic, parametric (tiers S-XL).

Everything is defined as aviary rules and expanded to SKI, SK and BCKW by
aviary's bracket abstraction (the canonical one). Numerals are Church numerals
written directly (`λf x. f^n x`). A result numeral is read back by applying it
to two fresh atoms `f` and `x`; its normal form must be `f (f (... x))` with
the right number of f's. Expectations come from arithmetic (`expect_src:
"arith"`), never from an engine.

Row parameters are chosen so that the family spans tiers S to XL; see CASES.
"""

from __future__ import annotations

from .. import engines as E

E.define("""
TRUE x y -> x
FALSE x y -> y
CPAIR x y f -> f x y
CFST p -> p TRUE
CSND p -> p FALSE
ISZERO n -> n (K FALSE) TRUE
SUCC n f x -> f (n f x)
ADD m n f x -> m f (n f x)
MUL m n f -> m (n f)
EXP m n -> n m
PSTEP f g h -> h (g f)
PRED n f x -> n (PSTEP f) (K x) I
SUB m n -> n PRED m
FSTEP p -> CPAIR (SUCC (CFST p)) (MUL (SUCC (CFST p)) (CSND p))
FACT n -> CSND (n FSTEP (CPAIR C0 C1))
FACTF r n -> ISZERO n C1 (MUL n (r (PRED n)))
FIBSTEP p -> CPAIR (CSND p) (ADD (CFST p) (CSND p))
FIB n -> CFST (n FIBSTEP (CPAIR C0 C1))
ACKSTEP g n -> n g (g C1)
ACK m -> m ACKSTEP SUCC
HSTEP p -> CPAIR (CSND p) (SUCC (CFST p))
HALF n -> CFST (n HSTEP (CPAIR C0 C0))
EVEN n -> n NOT TRUE
NOT b -> b FALSE TRUE
CSTEP n -> EVEN n (HALF n) (SUCC (MUL C3 n))
COLLF r n k -> ISZERO (PRED n) k (r (CSTEP n) (SUCC k))
""")


def numeral(n: int) -> str:
    """Source text of the Church numeral n, as a fresh rule C<n>."""
    name = f"C{n}"
    if name not in E._ENV.definitions:
        body = "x"
        for _ in range(n):
            body = f"f ({body})"
        E.define(f"{name} f x -> {body}")
    return name


for _k in (0, 1, 2, 3):
    numeral(_k)


def readback(n: int) -> str:
    """Expected normal form of numeral n applied to atoms f, x."""
    # Built iteratively; printed form is f (f (... (f x)...)).
    return "f (" * (n - 1) + ("f x" if n else "x") + ")" * (n - 1) if n else "x"


def fact(n):
    r = 1
    for i in range(2, n + 1):
        r *= i
    return r


def fib(n):
    a, b = 0, 1
    for _ in range(n):
        a, b = b, a + b
    return a


def ack(m, n):
    if m == 0:
        return n + 1
    if m == 1:
        return n + 2
    if m == 2:
        return 2 * n + 3
    if m == 3:
        return 2 ** (n + 3) - 3
    raise ValueError("ack: m <= 3 only")


def collatz_steps(n):
    k = 0
    while n != 1:
        n = n // 2 if n % 2 == 0 else 3 * n + 1
        k += 1
    return k


def tower(k):
    v = 2
    for _ in range(k - 1):
        v = 2 ** v
    return v


def cases():
    """(id, source, expected value) — the value is read back as a numeral."""
    c = []
    for m, n in [(3, 4), (10, 10), (100, 100), (1000, 1000)]:
        c.append((f"c.add.{m}.{n}", f"ADD {numeral(m)} {numeral(n)}", m + n))
    for m, n in [(3, 4), (10, 10), (30, 30), (100, 100)]:
        c.append((f"c.mul.{m}.{n}", f"MUL {numeral(m)} {numeral(n)}", m * n))
    for m, n in [(2, 3), (2, 8), (3, 5), (2, 12), (2, 16)]:
        c.append((f"c.exp.{m}.{n}", f"EXP {numeral(m)} {numeral(n)}", m ** n))
    for k in (2, 3, 4):
        c.append((f"c.tower.{k}", " ".join([numeral(2)] * k), tower(k)))
    for n in (3, 10, 30, 100):
        c.append((f"c.pred.{n}", f"PRED {numeral(n)}", n - 1))
    for m, n in [(10, 3), (30, 10), (100, 30)]:
        c.append((f"c.sub.{m}.{n}", f"SUB {numeral(m)} {numeral(n)}", m - n))
    for n in (3, 5, 7):
        c.append((f"c.fact.pairs.{n}", f"FACT {numeral(n)}", fact(n)))
    for n in (3, 5, 7):
        c.append((f"c.fact.y.{n}", f"Y FACTF {numeral(n)}", fact(n)))
    for n in (5, 10, 20):
        c.append((f"c.fib.{n}", f"FIB {numeral(n)}", fib(n)))
    for m, n in [(1, 2), (2, 2), (2, 10), (3, 1), (3, 3), (3, 5), (3, 7)]:
        c.append((f"c.ack.{m}.{n}", f"ACK {numeral(m)} {numeral(n)}", ack(m, n)))
    for n in (1, 2, 3, 6, 7, 9, 27):
        c.append((f"c.collatz.{n}", f"Y COLLF {numeral(n)} {numeral(0)}", collatz_steps(n)))
    return c


XL = [
    ("c.exp.2.20", f"EXP C2 {numeral(20)}", 2 ** 20),
    ("c.fact.y.8", f"Y FACTF {numeral(8)}", fact(8)),
    ("c.fib.25", f"FIB {numeral(25)}", fib(25)),
    ("c.ack.3.9", f"ACK C3 {numeral(9)}", ack(3, 9)),
    ("c.ack.3.10", f"ACK C3 {numeral(10)}", ack(3, 10)),
    ("c.ack.3.11", f"ACK C3 {numeral(11)}", ack(3, 11)),
    ("c.collatz.97", f"Y COLLF {numeral(97)} C0", collatz_steps(97)),
    ("c.collatz.871", f"Y COLLF {numeral(871)} C0", collatz_steps(871)),
]


# Rows whose copy-mode run would break the machine rule (one job, < 4 GB).
NO_COPY = {
    "c.ack.3.11": "Avon copy peaks at 3.87 GB RSS (626,283,926 contractions, Avon e69cf59)",
}


def rows():
    out = []
    for cid, src, val in cases() + XL:
        full = f"{src} f x"
        for b in ("ski", "bckw"):
            out.append({
                "id": f"{cid}.{b}", "family": "C", "basis": b,
                "term": E.to_basis(full, b), "source": full,
                "fuel": None, "mode": "nf",
                "expect": {"status": "NORMAL", "numeral": val},
                "expect_src": "arith",
                "note": f"value {val}",
                "pin_policy": "auto",
                # BCKW runs only on aviary and mini; keep it only where aviary can pin it.
                "require_aviary": b == "bckw",
            })
            if cid in NO_COPY:
                out[-1]["copy"] = False
                out[-1]["note"] += f"; copy mode not run: {NO_COPY[cid]}"
    return out
