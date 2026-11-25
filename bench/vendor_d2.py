"""Vendor SKIlark's pinned programs into data/d2/ for family D2.

For each SKIlark test module with pinned tables (PROGRAMS, INTERPRETED,
COMPILED), builds every program's unfuelled run term (`u<name>`) in both
forms exactly as that module's fixtures do:

- interpreted: `interpreted(PROGRAMS)`, the module's programs as one set;
- compiled: `compiled(PROGRAMS)` as one set in test_words and test_modes,
  else `compiled({name: program})`, one program at a time.

It records each program's pinned outcome and unfuelled contraction count
(aviary, to weak head normal form, from the module's tables) and the run's
result constructors. Terms go through bench.termstore, so the large shared
interpreter is stored once. Not vendored: test_io (needs a host for its I/O
words) and test_variants (its own loop variants).

With --own, vendors instead this suite's own Joy programs (OWN below) into
data/d5/ for family D5, compiled the same way.

Usage: python3 -m bench.vendor_d2 [--own]   (needs $SKILARK_REPO and $SKIJACK_REPO)
"""

from __future__ import annotations

import importlib
import json
import os
import subprocess
import sys
from pathlib import Path

from . import engines as E  # puts the canonical aviary first on sys.path
from . import termstore

SKILARK = Path(os.environ.get("SKILARK_REPO", Path.home() / "Code/ski/SKIlark"))
SKIJACK = Path(os.environ.get("SKIJACK_REPO", Path.home() / "Code/ski/skijack/python"))
OUT = Path(__file__).resolve().parent.parent / "data" / "d2"

MODULES = ["test_words", "test_modes", "test_combinators", "test_text", "test_types",
           "test_sets", "test_library", "test_pure", "test_numtext", "test_symbols"]
OUT_OWN = OUT.parent / "d5"  # family D5: the "own" programs, vendored by --own
SET_COMPILED = {"test_words", "test_modes"}

#: Joy programs of our own (module "own", family D5, `--own`): definitions
#: and, per program, an expression and its value. Each program checks its own answer: it runs
#: `<expr> <value> = [] [0 0 /] branch`, which leaves an empty stack (RVal [])
#: when the answer is right and errs (RErr, division by zero) when it is not,
#: so the result constructor certifies the value. Expected outcomes come from
#: SKIlark's model of the Joy reference, tests/joyref.py.
#:
#: SKIlark inlines every definition, so none may call itself: recursion is by
#: Joy's combinators. Collatz counts steps with `while`; Ackermann and tak use
#: `genrec`, whose fourth quotation finds the recursion `G` on top of the stack
#: and calls it once per `dup [i] dip` (G kept) and finally by `i`. _DIP2 and
#: _CALL are used only by ack and tak.
_DIP2 = "[[pred] dip] dip"
_CALL = "dup [i] dip"
OWN_DEFS = {
    "ack": "[pop null] [popd succ] [] "
           f"[[pop null] [[pop pred 1] dip i] [[[dup pred swap] dip pred] dip {_CALL} i] ifte] genrec",
    "collatz": "0 swap [1 >] [[succ] dip dup 2 rem 0 = [2 /] [3 * succ] branch] while pop",
    "tl": "[] cons cons cons",
    "tu": "uncons uncons first",
    "tak": "[pop <=] [popd popd] [] "
           f"[[tl dup tu {_DIP2}] dip {_CALL} [swap dup tu rolldown {_DIP2}] dip {_CALL} "
           f"[swap tu rollup {_DIP2}] dip {_CALL} i] genrec",
}
OWN = {  # name: (expression, value)
    "ack11": ("1 1 ack", 3), "ack22": ("2 2 ack", 7), "ack23": ("2 3 ack", 9),
    "ack32": ("3 2 ack", 29),
    "collatz5": ("5 collatz", 5), "collatz6": ("6 collatz", 8),
    "collatz7": ("7 collatz", 16),
    "collatz9": ("9 collatz", 19), "collatz27": ("27 collatz", 111),
    "tak321": ("3 2 1 tak", 2), "tak642": ("6 4 2 tak", 3),
    "tak840": ("8 4 0 tak", 1), "tak1284": ("12 8 4 tak", 5),
}


def _own_tables():
    """PROGRAMS and outcomes of module "own", outcomes from joyref."""
    import joyref
    progs = {n: f"{e} {v} = [] [0 0 /] branch" for n, (e, v) in OWN.items()}
    out = {}
    for n, text in progs.items():
        got = joyref.Joy(dict(OWN_DEFS)).run(text)
        if got != ("RVal", []):
            raise SystemExit(f"own.{n}: joyref gives {got}, not RVal []")
        out[n] = (got, None, None)
    return progs, out


def _rev(path):
    return subprocess.run(["git", "-C", str(path), "rev-parse", "--short", "HEAD"],
                          capture_output=True, text=True).stdout.strip()


def main(modules=MODULES, out=OUT):
    sys.path.insert(1, str(SKIJACK))
    sys.path.insert(1, str(SKILARK))
    sys.path.insert(1, str(SKILARK / "tests"))
    import skilark
    from skilark import compiled, interpreted
    from skijack.export import _ctors
    meta = {"source": f"SKIlark {skilark.__version__} @ {_rev(SKILARK)}, "
                      f"skijack @ {_rev(SKIJACK)}, tests/<module>.py tables",
            "programs": []}
    if modules == ["test_own"]:
        meta["source"] = (f"bench/vendor_d2.py OWN, compiled by SKIlark {skilark.__version__} "
                          f"@ {_rev(SKILARK)}, skijack @ {_rev(SKIJACK)}; outcomes from joyref")
    packer = termstore.Compressor()
    cache_dir = Path(os.environ.get("D2_CACHE", OUT / ".cache"))
    cache_dir.mkdir(parents=True, exist_ok=True)
    for modname in modules:
        P = OWN if modname == "test_own" else importlib.import_module(modname).PROGRAMS
        cache = cache_dir / f"{modname}.json"
        if cache.exists():
            got = json.loads(cache.read_text())
            for k, v in got["texts"].items():
                packer.add(k, v)
            meta["programs"].extend(got["programs"])
            del got
            print(f"{modname}: {len(P)} programs (cached)", flush=True)
            continue
        print(f"{modname}: {len(P)} programs: compiling in a separate process", flush=True)
        # One process per module keeps SKIlark's compile memory from piling up
        # on top of the shared-subterm graph of the modules already read.
        rc = subprocess.run([sys.executable, "-m", "bench.vendor_d2", "--compile", modname]).returncode
        if rc != 0 or not cache.exists():
            raise SystemExit(f"compiling {modname} failed (rc={rc})")
        got = json.loads(cache.read_text())
        for k, v in got["texts"].items():
            packer.add(k, v)
        meta["programs"].extend(got["programs"])
        del got

    packed, store = packer.finish()
    for p in meta["programs"]:
        p["term"] = packed[p["key"]]
    out.mkdir(parents=True, exist_ok=True)
    termstore.save(out / "programs.json.gz", meta)
    termstore.save(out / "store.json.gz", store)
    print(f"wrote {len(meta['programs'])} runs, {len(store)} shared subterms ({meta['source']})")


def compile_module(modname, form_only=None, chunk=None):
    """Compile one module's runs into the cache (run in its own process).
    With `form_only` ("interpreted" or "compiled") and `chunk` ("i/n"), only
    that part is compiled, into a part file; `merge_parts` joins them."""
    sys.path.insert(1, str(SKIJACK))
    sys.path.insert(1, str(SKILARK))
    sys.path.insert(1, str(SKILARK / "tests"))
    from skilark import compiled, interpreted, joy
    from skijack.export import _ctors
    cache = Path(os.environ.get("D2_CACHE", OUT / ".cache")) / f"{modname}.json"
    if modname == "test_own":
        P, table = _own_tables()
        tables = (("interpreted", table), ("compiled", table))
        defs = {**joy.DEFINITIONS, **OWN_DEFS}
    else:
        mod = importlib.import_module(modname)
        P = mod.PROGRAMS
        tables = (("interpreted", mod.INTERPRETED), ("compiled", mod.COMPILED))
        defs = joy.DEFINITIONS
    mod_texts, mod_progs = {}, []
    interp = interpreted(P, defs) if form_only in (None, "interpreted") else None
    comp_set = (compiled(P, defs) if modname in SET_COMPILED and form_only in (None, "compiled")
                else None)
    names = sorted(P)
    if chunk:
        i, n = (int(x) for x in chunk.split("/"))
        names = names[i::n]
    for name in names:
        for form, table in tables:
            if name not in table or (form_only and form != form_only):
                continue
            run = interp if form == "interpreted" else (comp_set or compiled({name: P[name]}, defs))
            outcome, unfuelled, _fuelled = table[name]
            key = f"{modname[5:]}.{name}.{form[0]}"
            mod_texts[key] = E.aviary_pretty(run.e.terms["u" + name])
            mod_progs.append({
                "key": key, "module": modname, "name": name, "form": form,
                "program": P[name], "outcome": [outcome[0], repr(outcome[1])],
                "steps": unfuelled,
                "result_ctors": _ctors(run.t["result"]).split(),
            })
    if form_only or chunk:
        cache = cache.with_name(f"{modname}.part.{form_only or 'all'}.{(chunk or '0/1').replace('/', 'of')}.json")
    tmp = cache.with_suffix(".tmp")  # atomic: a killed run leaves no half file
    tmp.write_text(json.dumps({"texts": mod_texts, "programs": mod_progs}))
    tmp.replace(cache)


def merge_parts(modname):
    """Join a module's part files into its cache file."""
    cache_dir = Path(os.environ.get("D2_CACHE", OUT / ".cache"))
    texts, progs = {}, []
    for part in sorted(cache_dir.glob(f"{modname}.part.*.json")):
        got = json.loads(part.read_text())
        texts.update(got["texts"])
        progs.extend(got["programs"])
    progs.sort(key=lambda p: p["key"])
    tmp = (cache_dir / f"{modname}.json").with_suffix(".tmp")
    tmp.write_text(json.dumps({"texts": texts, "programs": progs}))
    tmp.replace(cache_dir / f"{modname}.json")
    print(f"{modname}: merged {len(progs)} runs")


if __name__ == "__main__":
    if sys.argv[1:2] == ["--merge"]:
        merge_parts(sys.argv[2])
    elif sys.argv[1:2] == ["--compile"]:
        args = sys.argv[2:]
        compile_module(args[0], *(args[1:3] + [None] * (2 - len(args[1:3]))))
    elif sys.argv[1:2] == ["--own"]:
        main(["test_own"], OUT_OWN)
    else:
        main()
