"""Build manifests/<family>.jsonl.

For each row the family supplies the term and the expected status and normal
form. This script runs aviary (the reference) once. If aviary disagrees with
any row's expectation, it prints the disagreements, writes nothing for that
family, and exits 1. Otherwise it pins aviary's contraction count, and
adds fuel-edge rows for every row that reaches a normal form in c > 0 steps:

    fuel = c - 1  -> FUEL
    fuel = c      -> FUEL, with the normal form reached (the suite's convention:
                     FUEL whenever steps >= fuel)
    fuel = c + 1  -> NORMAL

Usage: python3 -m bench.gen [A B ...]
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

from . import engines as E
from . import mini
from .families import a_semantics, b_birds

FAMILIES = {"A": a_semantics, "B": b_birds}
ROOT = Path(__file__).resolve().parent.parent


def canon(text: str | None) -> str | None:
    """Canonical printed form; raises ValueError if `text` is not a term."""
    return None if text is None else mini.show(mini.parse(text))


def same_nf(got: str, expected: str) -> bool:
    """Compare normal forms; output that does not parse never matches."""
    try:
        return canon(got) == canon(expected)
    except ValueError:
        return False


def _check_term_text(r):
    """Manifest terms use only printable characters, with ASCII space as the
    one separator, so that every engine tokenises them alike."""
    for field in (r["term"], r["expect"]["nf"] or ""):
        bad = [c for c in field if (c.isspace() and c != " ") or not c.isprintable()]
        if bad:
            raise ValueError(f"{r['id']}: term contains {bad[0]!r}")


def pin(rows):
    prov = E.provenance()
    bad = []
    out = []
    for r in rows:
        _check_term_text(r)
        whnf = r["mode"] == "whnf"
        status, steps, nf = E.run_aviary([(r["term"], r["fuel"])], whnf=whnf)[0]
        exp = r["expect"]
        ok = status == exp["status"] and (exp["nf"] is None or same_nf(nf, exp["nf"]))
        if not ok:
            bad.append((r["id"], exp, (status, steps, nf)))
            continue
        r["pin"] = {"steps": steps, "source": f"aviary@{prov['aviary']}"}
        r["size"] = mini.size(mini.parse(r["term"]))
        out.append(r)
        if status in ("NORMAL", "WHNF") and steps > 0:
            for d, st in ((-1, "FUEL"), (0, "FUEL"), (1, status)):
                e = dict(r)
                e["id"] = f"{r['id']}.fuel{d:+d}"
                e["fuel"] = steps + d
                e["expect"] = {"status": st, "nf": exp["nf"] if d >= 0 else None}
                e["expect_src"] = "fuel-edge"
                e["pin"] = {"steps": steps + min(d, 0), "source": r["pin"]["source"]}
                out.append(e)
    return out, bad


def main(argv):
    fams = argv or list(FAMILIES)
    status = 0
    for f in fams:
        rows, bad = pin(FAMILIES[f].rows())
        for rid, exp, got in bad:
            print(f"[{f}] aviary disagrees with expectation: {rid}: expected {exp}, got {got}")
        if bad:
            print(f"[{f}] {len(bad)} rows rejected; manifest NOT written")
            status = 1
            continue
        path = ROOT / "manifests" / f"{f}.jsonl"
        with path.open("w") as fh:
            for r in rows:
                fh.write(json.dumps(r, ensure_ascii=False) + "\n")
        print(f"[{f}] wrote {len(rows)} rows to {path.relative_to(ROOT)}")
    return status


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
