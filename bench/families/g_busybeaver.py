"""Family G: busy-beaver champions of the SKI calculus.

From the BusyBeaverWiki page *SKI Calculus* (https://wiki.bbchallenge.org/
wiki/SKI_Calculus, oldid 10480, CC BY 4.0). Its function Xi_0(n) is the
largest normal form of a terminating term of n combinators, and the page
lists a champion term for each n. The page does not say how it measures a
normal form; the leaf count matches every value runnable here, so each row
expects the champion's normal form to have exactly the page's value in
leaves (`expect.leaves`, `expect_src: "corpus"`). Normal forms are unique,
so the page's "any reduction order" and our engines' normal order agree.

Rows: the main (S, K, I) table for n = 5 to 11, the S-and-K table where it
differs from the main one for n = 6, 9 to 13, and the BCKW table for n = 4
and 5 (aviary and mini only: Avon reads S, K and I). For n <= 4 the
champions are already normal (value = n) and are left out; for larger n the
values (2^2^513 and up) cannot be reached. A "≥" on the page bounds Xi_0(n),
not the champion's own value, which the page states exactly.
"""

from __future__ import annotations

SOURCE = ("BusyBeaverWiki, SKI Calculus, https://wiki.bbchallenge.org/wiki/SKI_Calculus "
          "(oldid 10480, CC BY 4.0)")

#: (table, n, champion as the page writes it, value: leaves of its normal form)
CHAMPIONS = [
    ("ski", 5, "SSS(SS)", 6),
    ("ski", 6, "SSS(SI)S", 17),
    ("ski", 7, "SSS(S(SS))S", 41),
    ("ski", 8, "SSK(S(SS)S)S", 80),
    ("ski", 9, "S(SI)(SS)(SS)SS", 1561),
    ("ski", 10, "S(S(SI)(SS)(SS)SS)", 1562),
    ("ski", 11, "SS(S(SI)(SS)(SS)SS)", 1563),
    ("sk", 6, "SSS(SS)S", 10),
    ("sk", 9, "S(SS)(SS)(SS)SS", 169),
    ("sk", 10, "SS(SS)(SSS)SSS", 1561),
    ("sk", 11, "S(SS(SS)(SSS)SSS)", 1562),
    ("sk", 12, "S(S(SS(SS)(SSS)SSS))", 1563),
    ("sk", 13, "S(SS)(SS)(SS(SS(SSS)))S", 7811),
    ("bckw", 4, "WW(WB)", 11),
    ("bckw", 5, "W(WW)(WB)", 47),
]


def spaced(compact: str) -> str:
    """The page's juxtaposed single letters ("SSS(SS)") as a term ("S S S (S S)")."""
    out = []
    for ch in compact:
        if ch == "(":
            out.append(" (" if out and out[-1] not in ("(", " (") else "(")
        elif ch == ")":
            out.append(")")
        else:
            out.append(ch if not out or out[-1] in ("(", " (") else " " + ch)
    return "".join(out)


def rows():
    out = []
    for table, n, compact, value in CHAMPIONS:
        term = spaced(compact)
        if sum(c.isalpha() for c in term) != n:
            raise ValueError(f"{table} n={n}: {compact} has {sum(c.isalpha() for c in term)} combinators")
        out.append({"id": f"g.{table}.{n}", "family": "G", "basis": table, "term": term,
                    "source": SOURCE, "fuel": None, "mode": "nf",
                    "expect": {"status": "NORMAL", "nf": None, "leaves": value},
                    "expect_src": "corpus",
                    "note": f"Xi_0 champion, {table.upper()} table, n = {n} ({compact}): "
                            f"normal form of {value} leaves",
                    "pin_policy": "auto"})
    return out
