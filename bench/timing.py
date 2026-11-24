"""Time engines on the larger rows of a manifest.

For each base row (not a fuel-edge row) of tier M, L or XL, for each engine
that the row lists:
- avon-share and avon-copy run `avon reduce --no-jets` under `/usr/bin/time -l`,
  giving user+sys CPU time and peak RSS for the whole process (parse, reduce,
  print).
- mini runs in-process (user CPU via resource.getrusage), for rows up to
  MINI_MAX contractions.
Runs are interleaved across engines (engine order rotates per round), so slow
drift on the machine is spread over all engines rather than landing on one.
Every run's status, count and normal form are checked as in bench.check; a
wrong answer is reported and its time is not used.

Writes results/timing-<family>.jsonl with every run, and prints a summary
(median and min CPU seconds, peak RSS, contractions per CPU second).

Usage: python3 -m bench.timing C [--runs N] [--tiers M,L,XL]
"""

from __future__ import annotations

import json
import re
import resource
import statistics
import subprocess
import sys
import tempfile
import time
from pathlib import Path

from . import engines as E
from . import mini
from .check import applicable
from .gen import ROOT, same_nf, expected_nf

MINI_MAX = 5_000_000
TIMEOUT = 900


def _avon(strategy, path, fuel):
    cmd = ["/usr/bin/time", "-l", str(E.AVON_BIN), "reduce", f"--strategy={strategy}",
           "--no-jets", f"--fuel={fuel}", f"--budget={E.AVON_PRINT_BUDGET}", path]
    r0 = resource.getrusage(resource.RUSAGE_CHILDREN)
    try:
        p = subprocess.run(cmd, capture_output=True, text=True, timeout=TIMEOUT)
    except subprocess.TimeoutExpired:
        return {"status": "TIMEOUT"}
    r1 = resource.getrusage(resource.RUSAGE_CHILDREN)
    # CPU from getrusage (microsecond resolution; /usr/bin/time prints only
    # hundredths). It covers avon and the small `time` wrapper around it.
    cpu = (r1.ru_utime - r0.ru_utime) + (r1.ru_stime - r0.ru_stime)
    m = re.search(r"([\d.]+)\s+real\s+([\d.]+)\s+user\s+([\d.]+)\s+sys", p.stderr)
    rss = re.search(r"(\d+)\s+maximum resident set size", p.stderr)
    lines = p.stdout.split("\n")
    head = lines[0].split()
    if p.returncode != 0 or len(head) != 2 or not m:
        return {"status": "ERROR", "stderr": p.stderr[-300:]}
    return {"status": head[0], "steps": int(head[1]), "nf": lines[1] if len(lines) > 1 else "",
            "wall": float(m.group(1)), "cpu": cpu,
            "rss_mb": int(rss.group(1)) / 2**20 if rss else None}


def _mini(term, fuel):
    t = mini.parse(term)
    r0 = resource.getrusage(resource.RUSAGE_SELF)
    w0 = time.perf_counter()
    status, steps, nf = mini.reduce(t, fuel)
    w1 = time.perf_counter()
    r1 = resource.getrusage(resource.RUSAGE_SELF)
    return {"status": status, "steps": steps, "nf": mini.show(nf), "wall": w1 - w0,
            "cpu": (r1.ru_utime - r0.ru_utime) + (r1.ru_stime - r0.ru_stime), "rss_mb": None}


def main(argv):
    fam, runs, tiers = None, 3, {"M", "L", "XL"}
    it = iter(argv)
    for a in it:
        if a == "--runs":
            runs = int(next(it))
        elif a == "--tiers":
            tiers = set(next(it).split(","))
        else:
            fam = a
    fam = fam or "C"
    rows = [json.loads(l) for l in (ROOT / "manifests" / f"{fam}.jsonl").open()]
    rows = [r for r in rows if r["expect_src"] != "fuel-edge" and r.get("tier") in tiers]
    prov = E.provenance()
    out_path = ROOT / "results" / f"timing-{fam}.jsonl"
    summary = []
    with out_path.open("w") as fh, tempfile.TemporaryDirectory() as td:
        fh.write(json.dumps({"provenance": prov, "runs": runs}) + "\n")
        for r in rows:
            path = str(Path(td) / "t.ski")
            Path(path).write_text(r["term"] + "\n")
            engines = [e for e in ("avon-share", "avon-copy", "mini") if applicable(e, r)]
            if "mini" in engines and (r["pin"] is None or r["pin"]["steps"] > MINI_MAX):
                engines.remove("mini")
            got = {e: [] for e in engines}
            for k in range(runs):
                order = engines[k % len(engines):] + engines[:k % len(engines)] if engines else []
                for e in order:
                    if e == "mini":
                        res = _mini(r["term"], r["fuel"])
                    else:
                        res = _avon(e.split("-")[1], path, r["fuel"])
                    ok = (res.get("status") == r["expect"]["status"]
                          and same_nf(res.get("nf", ""), expected_nf(r["expect"])))
                    if e != "avon-share" and r["pin"] is not None:
                        ok = ok and res.get("steps") == r["pin"]["steps"]
                    res.pop("nf", None)
                    res.update({"id": r["id"], "engine": e, "run": k, "ok": ok})
                    fh.write(json.dumps(res) + "\n")
                    fh.flush()
                    got[e].append(res)
            for e, rs in got.items():
                good = [x for x in rs if x["ok"]]
                if not good:
                    summary.append((r["id"], r["tier"], e, None, None, None, None, len(rs)))
                    print(f"{r['id']:24s} {r['tier']:2s} {e:10s} ALL {len(rs)} RUNS WRONG: "
                          f"{[(x.get('status'), x.get('steps')) for x in rs]}", flush=True)
                    continue
                cpus = [x["cpu"] for x in good]
                med = statistics.median(cpus)
                rss = max((x["rss_mb"] or 0) for x in good) or None
                rate = good[0]["steps"] / med if med > 0 else None
                summary.append((r["id"], r["tier"], e, good[0]["steps"], med, min(cpus), rss, len(rs) - len(good)))
                print(f"{r['id']:24s} {r['tier']:2s} {e:10s} steps={good[0]['steps']:>12,} "
                      f"cpu med={med:9.4f}s min={min(cpus):9.4f}s rss={rss or 0:7.1f}MB "
                      f"rate={(rate or 0) / 1e6:7.1f}M/s bad={len(rs) - len(good)}", flush=True)
    bad = sum(s[-1] for s in summary)
    print(f"wrote {out_path.relative_to(ROOT)}; {bad} runs gave a wrong answer")
    return 1 if bad else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
