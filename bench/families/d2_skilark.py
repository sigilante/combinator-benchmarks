"""Family D2: SKIlark's pinned Joy programs (vendored in data/d2/ by
bench/vendor_d2.py: programs.json and the shared-subterm store store.json).

Each pinned program gives up to two runs (interpreted, compiled), and each
run two rows, as in D0:

- `d2.<module>.<name>.<i|c>`: the unfuelled run term reduced to weak head
  normal form under SKIlark's cap (5,000,000); the count is SKIlark's pinned
  one (aviary), a given pin every engine that runs the row must reproduce.
- `... .ctor`: the run applied to one marker atom per constructor of its
  result type; the head must be the marker of the pinned outcome's
  constructor (RVal, RErr, ...). The stack an RVal carries (the pinned
  outcome's payload, recorded in `note`) is not checked yet.

Family D5 (bench/families/d5_own.py) builds its rows here too, from
data/d5: Joy programs of this suite (bench/vendor_d2.py OWN: Ackermann,
Collatz, tak), not SKIlark's. Each checks its own answer and errs when it is
wrong, so its `.ctor` row (head r_RVal) certifies the value. They have no
SKIlark pin: both rows are pinned by the auto policy, and their expected
outcome comes from SKIlark's Joy reference model (`expect_src: "joyref"`).

aviary is skipped (`skip_aviary`) for interpreted runs and for compiled runs
of over 20,000 contractions: it rewrites the whole tree per step and cannot
finish them in time.
"""

from __future__ import annotations

from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent.parent
CAP = 5_000_000


def rows(family="D2", data="data/d2"):
    from .. import termstore
    STORE, PROGRAMS = f"{data}/store.json.gz", f"{data}/programs.json.gz"
    prefix = family.lower()
    meta = termstore.load(ROOT / PROGRAMS)
    src = meta["source"]
    out = []
    for p in meta["programs"]:
        own = p["steps"] is None
        skip_av = p["form"] == "interpreted" or (not own and p["steps"] > 20_000)
        base = {"family": family, "basis": "ski", "store": STORE, "mode": "whnf",
                "source": f"{src}: {p['module']}.{p['name']} ({p['form']}): {p['program']}",
                "skip_aviary": skip_av}
        src_kind = "joyref" if own else "corpus"
        pin = ({"pin_policy": "auto"} if own else
               {"pin": {"steps": p["steps"], "source": f"SKIlark {p['module']}.py (aviary)"},
                "pin_policy": "given"})
        out.append({**base, "id": f"{prefix}.{p['key']}", "term": "",
                    "term_from": {"file": PROGRAMS, "key": p["key"]}, "fuel": CAP,
                    "expect": {"status": "WHNF", "nf": None}, "expect_src": src_kind, **pin,
                    "note": f"{'joyref' if own else 'pinned'} outcome "
                            f"{p['outcome'][0]} {p['outcome'][1]}"})
        markers = " ".join("r_" + c.split("/")[0] for c in p["result_ctors"])
        out.append({**base, "id": f"{prefix}.{p['key']}.ctor", "term": "",
                    "term_from": {"file": PROGRAMS, "key": p["key"], "wrap": f"(%T) {markers}"},
                    "fuel": None, "expect": {"status": "WHNF", "nf": None,
                                             "head": "r_" + p["outcome"][0]},
                    "expect_src": src_kind, "pin_policy": "auto",
                    "note": f"result constructor {p['outcome'][0]} of {' '.join(p['result_ctors'])}"})
    return out
