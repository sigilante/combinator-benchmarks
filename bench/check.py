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
# Importing gen imports the families, whose definitions (e.g. NOT, PAIR) must be
# registered in aviary's environment before avon_can_run/mini_can_run are asked.
from .gen import same_nf, expected_nf, outcome_problems, ROOT

COUNTED = {"aviary", "avon-copy", "mini"}
TIMEOUT = 600  # seconds per engine batch; a timeout fails the row


def applicable(engine, row):
    if "engines" in row and engine not in row["engines"]:
        return False
    if engine == "aviary":
        return True
    if engine == "avon-share" and row["expect_src"] == "fuel-edge":
        return False  # edges come from copy counts; share is edge-checked on its own counts
    if engine.startswith("avon"):
        return E.avon_can_run(row["term"])
    if engine == "mini":
        return E.mini_can_run(row["term"])
    return False


def validate(row):
    """Problems with a manifest row itself; any problem fails the row."""
    probs = []
    for key in ("id", "term", "fuel", "mode", "expect", "expect_src", "pin"):
        if key not in row:
            probs.append(f"missing field {key!r}")
    if probs:
        return probs
    if row["mode"] not in ("nf", "whnf"):
        probs.append(f"mode {row['mode']!r} is not nf or whnf")
    exp = row["expect"]
    if exp.get("status") not in ("NORMAL", "WHNF", "FUEL"):
        probs.append(f"expected status {exp.get('status')!r}")
    try:
        want = expected_nf(exp)
    except ValueError as e:
        probs.append(str(e))
        want = None
    if exp.get("status") == "NORMAL" and want is None:
        probs.append("NORMAL row without an expected normal form")
    if "engines" in row:
        bad = [e for e in row["engines"] if e not in E.ENGINES]
        if bad or not row["engines"]:
            probs.append(f"engines {row['engines']!r} (known: {sorted(E.ENGINES)})")
    if row["pin"] is None and row.get("engines") != ["avon-share"]:
        probs.append("pin is null but the row is not share-only")
    if not isinstance(row["fuel"], int) or row["fuel"] < 0:
        probs.append(f"fuel {row['fuel']!r}")
    return probs


def check_family(fam, engines):
    rows = []
    results, fails = [], []
    tally = Counter()
    for n, line in enumerate((ROOT / "manifests" / f"{fam}.jsonl").open(), 1):
        try:
            r = json.loads(line)
        except json.JSONDecodeError as e:
            rec = {"id": f"{fam}:line{n}", "engine": "manifest", "ok": False,
                   "problems": [f"bad JSON: {e}"]}
            results.append(rec)
            fails.append(rec)
            continue
        probs = validate(r)
        if probs:
            rec = {"id": r.get("id", f"{fam}:line{n}"), "engine": "manifest", "ok": False,
                   "problems": probs}
            results.append(rec)
            fails.append(rec)
            tally[("manifest", "fail")] += 1
            continue
        rows.append(r)
    for eng in engines:
        for mode in ("nf", "whnf"):
            sel = [r for r in rows if r["mode"] == mode and applicable(eng, r)]
            tally[(eng, "skip")] += sum(1 for r in rows if r["mode"] == mode) - len(sel)
            if not sel:
                continue
            got = E.ENGINES[eng]([(r["term"], r["fuel"]) for r in sel], whnf=(mode == "whnf"),
                                 timeout=TIMEOUT)
            for r, (status, steps, nf) in zip(sel, got):
                exp = r["expect"]
                probs = outcome_problems(exp, status, nf)
                if eng in COUNTED and r["pin"] is not None and steps != r["pin"]["steps"]:
                    probs.append(f"steps {steps} != pin {r['pin']['steps']}")
                if eng == "avon-share" and r.get("share_ref") is not None and steps != r["share_ref"]:
                    # A regression pin on Avon's own share count, not a correctness claim.
                    probs.append(f"share steps {steps} != share_ref {r['share_ref']} (regression)")
                tally[(eng, "fail" if probs else "pass")] += 1
                rec = {"id": r["id"], "engine": eng, "status": status, "steps": steps,
                       "pin": r["pin"] and r["pin"]["steps"], "ok": not probs, "problems": probs}
                results.append(rec)
                if probs:
                    fails.append(rec)
    # A row that none of the selected engines ran was checked by nothing; when
    # every engine is selected, that is a failure, not a skip.
    if set(engines) == set(E.ENGINES):
        ran = {x["id"] for x in results}
        for r in rows:
            if r["id"] not in ran:
                rec = {"id": r["id"], "engine": "none", "ok": False,
                       "problems": ["no engine can run this row"]}
                results.append(rec)
                fails.append(rec)
                tally[("none", "fail")] += 1
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
            got = E.ENGINES["avon-share"](jobs, whnf=(mode == "whnf"), timeout=TIMEOUT)
            for i, x in enumerate(sel):
                (s0, n0, _), (s1, n1, nf1) = got[2 * i], got[2 * i + 1]
                probs = []
                exp_nf = expected_nf(base[x["id"]]["expect"])
                if exp_nf is not None and not same_nf(nf1, exp_nf):
                    probs.append(f"share fuel=c+1: nf {nf1[:200]!r} != {exp_nf[:200]!r}")
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
    skipped = {eng: tally[(eng, "skip")] for eng in engines}
    out = ROOT / "results" / f"check-{fam}.jsonl"
    with out.open("w") as fh:
        fh.write(json.dumps({"provenance": E.provenance(), "not_applicable": skipped}) + "\n")
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
    fams = fams or ["A", "B", "C"] + sorted(p.stem for p in (ROOT / "manifests").glob("D*.jsonl"))
    unknown = [e for e in engines if e not in E.ENGINES]
    if unknown:
        raise SystemExit(f"unknown engine(s) {unknown}; choose from {sorted(E.ENGINES)}")
    rc = 0
    for fam in fams:
        rows, tally, fails = check_family(fam, engines)
        print(f"== {fam}: {len(rows)} rows")
        for eng in engines:
            p, f, k = tally[(eng, "pass")], tally[(eng, "fail")], tally[(eng, "skip")]
            print(f"   {eng:11s} {p:5d} pass {f:4d} fail {k:5d} rows not applicable")
        for extra in ("manifest", "none"):
            if tally[(extra, "fail")]:
                print(f"   {extra:11s} {tally[(extra, 'fail')]:4d} rows failed before any engine ran them")
        for rec in fails[:40]:
            print(f"   FAIL {rec['engine']}: {rec['id']}: {'; '.join(rec['problems'])}")
        if len(fails) > 40:
            print(f"   ... {len(fails) - 40} more in results/check-{fam}.jsonl")
        rc |= bool(fails)
    return rc


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
