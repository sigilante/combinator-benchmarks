"""Family D3: Hoon programs compiled through Nock into SKI by SKInock.

urbit/benchmark's Hoon-compiled programs (dec, add, factorial, fibonacci,
ackermann, bigslot) at SKInock's scaled-down subjects, vendored in data/d3/
by bench/vendor_d3.py through the shared-subterm store (the printed terms run
from 12 to 162 MB, 3.6M to 46M leaves). Each row reduces `show main` to
normal form: `main` is the compiled program on its subject, and `show`
rebuilds the product noun as a first-order term (matom, mcell, mnil, mcons,
mt, mf), so the row compares the whole product. The expected normal form is
printed from the product of SKInock's Python Nock evaluator
(`expect_src: "nock-oracle"`), which evaluates by Nock's step rules rather
than by reducing the compiled term (it shares SKInock's `nock` module, the
noun types and formula checks, with the compiler). Rows are
pinned by the auto policy; aviary and mini are left out by their size limits
where the terms are too large for them.
"""

from __future__ import annotations

from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent.parent
PROGRAMS, STORE = "data/d3/programs.json.gz", "data/d3/store.json.gz"


def rows():
    from .. import termstore
    meta = termstore.load(ROOT / PROGRAMS)
    out = []
    for p in meta["programs"]:
        out.append({"id": f"d3.{p['key']}", "family": "D3", "basis": "ski", "term": "",
                    "term_from": {"file": PROGRAMS, "key": p["key"]}, "store": STORE,
                    "source": f"{meta['source']}: {p['name']} on subject {p['subject']}",
                    "fuel": None, "mode": "nf",
                    "expect": {"status": "NORMAL", "nf": p["nf"]}, "expect_src": "nock-oracle",
                    "note": f"{p['name']} {p['subject']} = {p['product']} "
                            f"({p['nock_steps']:,} Nock steps in SKInock's evaluator)",
                    "pin_policy": "auto"})
    return out
