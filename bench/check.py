"""Run every applicable engine over manifests and report disagreements.

Checks per row and engine:
- status equals the expected status;
- normal form equals the expected one (when the row gives one), compared in
  canonical printed form;
- contraction count equals the pin, for count-asserting engines only
  (aviary, avon-copy, mini). avon-share's count is recorded, never asserted.

Usage: python3 -m bench.check [A B ...] [--engines aviary,avon-copy,...]
Writes results/check-<family>.jsonl and prints a summary.
"""

from __future__ import annotations

import json
import sys
from collections import Counter
from pathlib import Path

from . import engines as E
from .gen import canon, ROOT

COUNTED = {"aviary", "avon-copy", "mini"}


def applicable(engine, row):
    if engine == "aviary":
        return True
    if engine == "avon-share" and row["expect_src"] == "fuel-edge":
        return False  # edges come from copy counts; share is edge-checked on its own counts
    if engine.startswith("avon"):
        return E.avon_can_run(row["term"])
    if engine == "mini":
        return row["mode"] == "nf" and E.mini_can_run(row["term"])
    return False


def check_family(fam, engines):
    rows = [json.loads(l) for l in (ROOT / "manifests" / f"{fam}.jsonl").open()]
    results, fails = [], []
    tally = Counter()
    for eng in engines:
        for mode in ("nf", "whnf"):
            sel = [r for r in rows if r["mode"] == mode and applicable(eng, r)]
            if not sel:
                continue
            got = E.ENGINES[eng]([(r["term"], r["fuel"]) for r in sel], whnf=(mode == "whnf"))
            for r, (status, steps, nf) in zip(sel, got):
                exp = r["expect"]
                probs = []
                if status != exp["status"]:
                    probs.append(f"status {status} != {exp['status']}")
                if exp["nf"] is not None and canon(nf) != canon(exp["nf"]):
                    probs.append(f"nf {nf!r} != {exp['nf']!r}")
                if eng in COUNTED and steps != r["pin"]["steps"]:
                    probs.append(f"steps {steps} != pin {r['pin']['steps']}")
                tally[(eng, "fail" if probs else "pass")] += 1
                rec = {"id": r["id"], "engine": eng, "status": status, "steps": steps,
                       "pin": r["pin"]["steps"], "ok": not probs, "problems": probs}
                results.append(rec)
                if probs:
                    fails.append(rec)
    if "avon-share" in engines:
        # Fuel edges on share mode's own counts: c -> FUEL, c + 1 -> its status.
        base = {r["id"]: r for r in rows}
        done = [x for x in results if x["engine"] == "avon-share" and x["ok"]
                and x["status"] in ("NORMAL", "WHNF") and x["steps"] > 0]
        for mode in ("nf", "whnf"):
            sel = [x for x in done if base[x["id"]]["mode"] == mode]
            jobs = [(base[x["id"]]["term"], x["steps"] + d) for x in sel for d in (0, 1)]
            if not jobs:
                continue
            got = E.ENGINES["avon-share"](jobs, whnf=(mode == "whnf"))
            for i, x in enumerate(sel):
                (s0, n0, _), (s1, n1, _) = got[2 * i], got[2 * i + 1]
                probs = []
                if s0 != "FUEL":
                    probs.append(f"share fuel=c: {s0} != FUEL")
                if (s1, n1) != (x["status"], x["steps"]):
                    probs.append(f"share fuel=c+1: {s1} {n1} != {x['status']} {x['steps']}")
                tally[("avon-share", "fail" if probs else "pass")] += 1
                rec = {"id": x["id"] + ".share-edge", "engine": "avon-share", "status": s1,
                       "steps": n1, "pin": None, "ok": not probs, "problems": probs}
                results.append(rec)
                if probs:
                    fails.append(rec)
    out = ROOT / "results" / f"check-{fam}.jsonl"
    with out.open("w") as fh:
        fh.write(json.dumps({"provenance": E.provenance()}) + "\n")
        for rec in results:
            fh.write(json.dumps(rec, ensure_ascii=False) + "\n")
    return rows, tally, fails


def main(argv):
    engines = list(E.ENGINES)
    fams = []
    it = iter(argv)
    for a in it:
        if a == "--engines":
            engines = next(it).split(",")
        else:
            fams.append(a)
    fams = fams or ["A", "B"]
    rc = 0
    for fam in fams:
        rows, tally, fails = check_family(fam, engines)
        print(f"== {fam}: {len(rows)} rows")
        for eng in engines:
            p, f = tally[(eng, "pass")], tally[(eng, "fail")]
            print(f"   {eng:11s} {p:5d} pass {f:4d} fail")
        for rec in fails[:40]:
            print(f"   FAIL {rec['engine']}: {rec['id']}: {'; '.join(rec['problems'])}")
        if len(fails) > 40:
            print(f"   ... {len(fails) - 40} more in results/check-{fam}.jsonl")
        rc |= bool(fails)
    return rc


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
