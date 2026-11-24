"""Family D0: Avon's conformance corpus (vendored in data/d0, see SOURCE).

Each corpus target is a closed level-1 SKIjack executable (an interpreter
applied to its fuel and a quoted object program), stored as a SKIT file, with
the status and copy-mode contraction count that aviary gives reducing it to
weak head normal form under a cap, and the result constructor it reaches.

Two kinds of row per target:

- `d0.<id>`: the target itself, mode whnf, at the corpus's cap as fuel.
  Expected: the corpus's status, and its count as a given pin
  (`pin_policy: "given"`; gen.given_pin has every engine that can reproduce it).
- `d0.<id>.ctor`: the target applied to one marker atom per result
  constructor, `T r_C1 ... r_Cn`. A Scott-encoded value selects the marker of
  its constructor, so the weak head normal form's head must be `r_<ctor>`.
  This checks what the run computed, not only how long it took. Its count is
  new (not in the corpus), so it is pinned by the auto policy.

Not yet checked: the decoded payload (the corpus's last column), which needs
the object type's decoder. Rows with status FUEL have no constructor row.
"""

from __future__ import annotations

from pathlib import Path

from .. import mini, skit

DATA = Path(__file__).resolve().parent.parent.parent / "data" / "d0"


# The corpus's counts were made by skijack.export on aviary; the files were
# last changed in Avon at b7c26c2 (see data/d0/SOURCE).
PIN_SOURCE = "avon tests/conformance@b7c26c2 (aviary, via skijack.export)"


def targets():
    for line in (DATA / "manifest.tsv").read_text().splitlines():
        ident, fname, cap, status, steps, result_ctors, _obj, ctor, payload = line.split("\t")
        yield {
            "id": ident, "file": fname, "cap": int(cap), "status": status,
            "steps": int(steps),
            "ctors": [c.split("/") for c in result_ctors.split()],
            "ctor": None if ctor == "-" else ctor, "payload": payload,
        }


def rows():
    out = []
    for t in targets():
        term = mini.show(skit.read(DATA / t["file"]))
        out.append({
            "id": f"d0.{t['id']}", "family": "D0", "basis": "ski",
            "term": term, "source": f"data/d0/{t['file']}",
            "fuel": t["cap"], "mode": "whnf",
            "expect": {"status": t["status"], "nf": None},
            "expect_src": "corpus",
            "pin": {"steps": t["steps"], "source": PIN_SOURCE},
            "pin_policy": "given",
            "note": f"corpus result: {t['ctor'] or '-'} {t['payload']}",
        })
        if t["status"] == "WHNF" and t["ctor"]:
            markers = " ".join(f"r_{name}" for name, _arity in t["ctors"])
            out.append({
                "id": f"d0.{t['id']}.ctor", "family": "D0", "basis": "ski",
                "term": f"({term}) {markers}", "source": f"data/d0/{t['file']} applied to {markers}",
                "fuel": None, "mode": "whnf",
                "expect": {"status": "WHNF", "nf": None, "head": f"r_{t['ctor']}"},
                "expect_src": "corpus",
                "pin_policy": "auto",
                "note": f"result constructor {t['ctor']} of {' '.join(n for n, _ in t['ctors'])}",
            })
    return out
