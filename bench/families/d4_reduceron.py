"""Family D4: the Reduceron benchmarks, as Avon's skijack ports.

Naylor and Runciman's OrdList, Queens2, Taut, Clausify and PermSort (JFP
2012), ported to skijack in Avon's tests/workloads/reduceron/ and vendored
with their compiled terms in data/d4/ by bench/vendor_d4.py. Each program's
`main` checks its own answer and returns True; the row reduces `main Tt Ff`
to weak head normal form and expects the atom Ff (True is bool's second
constructor). Four rows a program: full size and small (vendor_d4.SMALL),
each compiled with and without skijack's inlining pass.

Full-size runs take ~10^9 contractions even sharing (PermSort ~4 x 10^9),
so they are share-only (`copy: false`, and `share_fuel` 10^10 so PermSort
is not cut at gen's default of 4 x 10^9). Small runs are pinned by the auto
policy like any other row.
"""

from __future__ import annotations

import json
from pathlib import Path

DATA = Path(__file__).resolve().parent.parent.parent / "data" / "d4" / "terms.json"


def rows():
    meta = json.loads(DATA.read_text())
    out = []
    for key, t in sorted(meta["terms"].items()):
        prog, size, inl = key.split(".")
        full = size == "full"
        row = {"id": f"d4.{key}", "family": "D4", "basis": "ski", "term": t["term"],
               "source": f"{meta['source']}: {prog}.ascii.ski"
                         + ("" if full else f", with {t['changed']}"),
               "fuel": None, "mode": "whnf",
               "expect": {"status": "WHNF", "nf": "Ff"}, "expect_src": "self-check",
               "note": f"Reduceron {prog}, {size} size, "
                       f"{'inlined' if inl == 'inl' else 'not inlined'}: main checks its answer",
               "pin_policy": "auto"}
        if full:
            row.update({"copy": False, "skip_aviary": True, "share_fuel": 10_000_000_000})
        out.append(row)
    return out
