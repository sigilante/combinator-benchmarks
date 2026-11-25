"""Build manifests/<family>.jsonl.

For each row the family supplies the term and the expected status and normal
form. Rows are pinned by aviary (default), by `auto_pin` (pin_policy "auto")
or by `given_pin` (pin_policy "given"; see README.md, "Where pins come from").
If an engine that pins or confirms a row disagrees with the row's expectation,
the disagreements are printed, nothing is written for that family, and the
exit status is 1. Fuel-edge rows are added for every row that reaches a
normal form or weak head normal form (status S) in c > 0 steps (for auto and
given pins, only up to c = EDGE_MAX):

    fuel = c - 1  -> FUEL
    fuel = c      -> FUEL, with the result reached (the suite's convention:
                     FUEL whenever steps >= fuel)
    fuel = c + 1  -> S

Usage: python3 -m bench.gen [A B ...]
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

from . import engines as E
from . import mini
import os

from .families import a_semantics, b_birds, c_church, d0_avon, d1_skijack, d2_skilark, d4_reduceron, d5_own

FAMILIES = {"A": a_semantics, "B": b_birds, "C": c_church, "D0": d0_avon, "D1": d1_skijack,
            "D2": d2_skilark, "D4": d4_reduceron}
if (Path(__file__).resolve().parent.parent / "data" / "d5").exists():
    FAMILIES["D5"] = d5_own  # only once vendored: python3 -m bench.vendor_d2 --own

# Auto-pinning policy (rows with pin_policy == "auto"):
AVIARY_TIMEOUT = float(os.environ.get("BENCH_AVIARY_TIMEOUT", 10))  # s per row
COPY_FUEL = 1_000_000_000          # copy-mode attempts stop here ...
COPY_TIMEOUT = 120                 # ... or after this many seconds
SHARE_FUEL = 4_000_000_000
SHARE_TIMEOUT = 300
MINI_MAX = 20_000_000              # mini confirms copy counts up to this
EDGE_MAX = 100_000                 # fuel-edge rows only for pins up to this


def tier(steps):
    for name, lim in (("XS", 10**2), ("S", 10**4), ("M", 10**6), ("L", 10**8)):
        if steps < lim:
            return name
    return "XL"


def print_budget(r):
    """How much of a result a row needs printed: all of it to compare a normal
    form, else only enough for the status line and the head."""
    return E.AVON_PRINT_BUDGET if expected_nf(r["expect"]) is not None else E.SMALL_PRINT_BUDGET


def run1(engine, r, fuel, timeout=None):
    """Run one row on one engine at the given fuel, in the row's mode."""
    return E.ENGINES[engine]([(r["term"], fuel, print_budget(r))], whnf=(r["mode"] == "whnf"),
                             timeout=timeout)[0]


def given_pin(r, prov):
    """A row whose pin comes from an outside source (`r["pin"]` already set,
    e.g. Avon's conformance manifest). Every engine that can run the row in
    reasonable time must reproduce the pin and the expectation, or the row is
    rejected. Returns (row, problem or None)."""
    want = r["pin"]["steps"]
    exp = r["expect"]
    engines = []
    for eng in ("avon-copy", "mini", "aviary"):
        if eng.startswith("avon") and not E.avon_can_run(r["term"]):
            continue
        if eng == "mini" and (want > MINI_MAX or not E.mini_can_run(r["term"])):
            continue
        if eng == "aviary" and (r.get("skip_aviary") or not E.aviary_can_run(r["size"])):
            continue  # family says aviary cannot finish this row in time
        st, n, nf = run1(eng, r, r["fuel"], AVIARY_TIMEOUT if eng == "aviary" else COPY_TIMEOUT)
        if eng == "aviary" and st == "INTERRUPTED":
            continue  # too slow to confirm here; not run by check either
        probs = outcome_problems(exp, st, nf) + ([] if n == want else [f"steps {n} != pin {want}"])
        if probs:
            return None, (eng, probs)
        engines.append(eng)
    if not engines:
        return None, ("no engine could confirm the given pin", want)
    if E.avon_can_run(r["term"]):
        st, n, nf = run1("avon-share", r, r["fuel"], SHARE_TIMEOUT)
        probs = outcome_problems(exp, st, nf)
        if probs:
            return None, ("avon-share", probs)
        r["share_ref"] = n
        engines.append("avon-share")
    r["engines"] = engines
    r["pin"]["source"] += "; confirmed by " + ", ".join(e for e in engines if e != "avon-share")
    r["tier"] = tier(want)
    return r, None


def auto_pin(r, prov):
    """Pin a row by the policy in README.md ("Where pins come from").
    Returns (row or None, problem or None)."""
    exp = r["expect"]

    def matches(status, nf):
        return not outcome_problems(exp, status, nf)

    share_fuel = r.get("share_fuel", SHARE_FUEL)  # a family may raise it for one row
    share = run1("avon-share", r, share_fuel, SHARE_TIMEOUT) if E.avon_can_run(r["term"]) else None
    if share is not None:
        if not matches(share[0], share[2]):
            return None, ("avon-share", share[:2])
        r["share_ref"] = share[1]

    if r.get("copy") is False:
        st = "SKIPPED"  # family says copy mode is too costly here; share only
    elif r.get("skip_aviary") or not E.aviary_can_run(r["size"]):
        st = "INTERRUPTED"  # family says aviary cannot finish in time: next source
    else:
        st, n, nf = run1("aviary", r, COPY_FUEL, AVIARY_TIMEOUT)
    if st == "SKIPPED":
        if share is None or r.get("require_aviary"):
            return None, None
        r["pin"] = None
        r["engines"] = ["avon-share"]
    elif st != "INTERRUPTED":
        if not matches(st, nf):
            return None, ("aviary", (st, n))
        r["pin"] = {"steps": n, "source": f"aviary@{prov['aviary']}"}
        r["engines"] = ["aviary", "avon-copy", "avon-share", "mini"]
    elif r.get("require_aviary"):
        return None, None  # dropped, not rejected
    else:
        st, n, nf = run1("avon-copy", r, COPY_FUEL, COPY_TIMEOUT)
        if st in ("NORMAL", "WHNF"):
            if not matches(st, nf):
                return None, ("avon-copy", (st, n))
            src = f"avon-copy@{prov['avon']}"
            engines = ["avon-copy", "avon-share"]
            if n <= MINI_MAX and E.mini_can_run(r["term"]):
                ms, mn, mnf = run1("mini", r, COPY_FUEL)
                if (ms, mn) != (st, n) or not matches(ms, mnf):
                    return None, ("mini disagrees with avon-copy", (ms, mn, st, n))
                src += ", confirmed by mini"
                engines.append("mini")
            r["pin"] = {"steps": n, "source": src}
            r["engines"] = engines
        else:
            if share is None:
                return None, ("no engine finished", (st, n))
            r["pin"] = None
            r["engines"] = ["avon-share"]
            why = {"FUEL": f"out of fuel at {COPY_FUEL:,} contractions",
                   "TIMEOUT": f"timed out after {COPY_TIMEOUT} s"}.get(st, f"status {st}")
            r["note"] += f"; copy mode not pinned: {why}"
    steps = r["pin"]["steps"] if r["pin"] else r["share_ref"]
    r["tier"] = tier(steps)
    r["fuel"] = (2 * r["pin"]["steps"] + 1000) if r["pin"] else share_fuel
    return r, None
ROOT = Path(__file__).resolve().parent.parent


def canon(text: str | None) -> str | None:
    """Canonical printed form; raises ValueError if `text` is not a term."""
    return None if text is None else mini.show(mini.parse(text))


def expected_nf(expect: dict) -> str | None:
    """The expected normal form of a row: `nf_ref` (a name resolved by
    `_nf_ref`, for forms too large to store, e.g. "d1.quine"), else `numeral: n`
    (family C, D1: the Church readback `f (f (... x))` with n f's, which can be
    megabytes long), else the literal `nf`, else None."""
    if expect.get("nf_ref") is not None:
        return _nf_ref(expect["nf_ref"])
    if expect.get("numeral") is not None:
        n = expect["numeral"]
        if not isinstance(n, int) or n < 0:
            raise ValueError(f"numeral must be a natural number, got {n!r}")
        return "x" if n == 0 else "f (" * (n - 1) + "f x" + ")" * (n - 1)
    return expect.get("nf")


def head_of(text: str) -> str | None:
    """The head atom of a printed term: its first token. Printing puts the
    head first, so this survives a print cut off with " ..."."""
    tok = text.replace("(", " ").replace(")", " ").split(maxsplit=1)
    return tok[0] if tok else None


def outcome_problems(expect: dict, status: str, nf: str) -> list:
    """Every way an engine's (status, printed result) misses a row's
    expectation; empty if it meets it. Used by gen, check and timing alike."""
    probs = []
    if status != expect["status"]:
        probs.append(f"status {status} != {expect['status']}")
    want = expected_nf(expect)
    if want is not None and not same_nf(nf, want):
        probs.append(f"nf {nf[:200]!r} != {want[:200]!r}")
    if expect.get("head") is not None and head_of(nf) != expect["head"]:
        probs.append(f"head {head_of(nf)!r} != {expect['head']!r}")
    return probs


_NF_REF_CACHE: dict = {}


def _nf_ref(name: str) -> str:
    """Expected normal forms too large to store in a manifest, computed from
    their construction by the family that defines them."""
    if name not in _NF_REF_CACHE:
        if name == "d1.quine":
            from .families import d1_skijack  # deferred: the families import gen
            _NF_REF_CACHE[name] = d1_skijack.quine_nf()
        else:
            raise ValueError(f"unknown nf_ref {name!r}")
    return _NF_REF_CACHE[name]


def same_nf(got: str, expected: str) -> bool:
    """Compare normal forms; output that does not parse never matches."""
    try:
        return canon(got) == canon(expected)
    except ValueError:
        return False


def _check_term_text(r):
    """Manifest terms use only printable characters, with ASCII space as the
    one separator, so that every engine tokenises them alike."""
    for field in (r["term"], r["expect"].get("nf") or ""):
        bad = [c for c in field if (c.isspace() and c != " ") or not c.isprintable()]
        if bad:
            raise ValueError(f"{r['id']}: term contains {bad[0]!r}")


_STORES: dict = {}
CACHE_MAX = 200_000_000


def materialize(r):
    """A row whose term uses shared subterms (`store`: a termstore file,
    relative to the repo) gets its plain printed term; returns the packed text
    to write back, or None. Engines only ever see plain terms."""
    if not r.get("store"):
        return None
    from . import termstore
    if r.get("term_from"):
        # The term lives in a vendored file, not the manifest: `term_from` names
        # the file, the key, and a wrapper in which "%T" stands for the term.
        src = r["term_from"]
        if src["file"] not in _STORES:
            _STORES[src["file"]] = termstore.load(ROOT / src["file"])
        files = _STORES[src["file"]]
        index = files.setdefault("_index", {p["key"]: p for p in files.get("programs", [])})
        r["term"] = src.get("wrap", "%T").replace("%T", index[src["key"]]["term"])
    if r["store"] not in _STORES:
        _STORES[r["store"]] = (termstore.load(ROOT / r["store"]), {})
    store, cache = _STORES[r["store"]]
    packed = r["term"]
    r["term"] = termstore.expand(packed, store, cache)
    # The cache holds each shared subterm fully expanded; across a family's
    # rows that can reach gigabytes, so it is dropped past CACHE_MAX bytes.
    if sum(map(len, cache.values())) > CACHE_MAX:
        cache.clear()
    return packed


def _release(rows):
    """Put back the packed term of rows built on a store: an expanded term can
    be ~1 MB, and a family keeps all its rows until it writes them."""
    for r in rows:
        if r.get("packed_term") is not None:
            r["term"] = r["packed_term"]


def _packed_row(r):
    """The row as written: the term packed, or empty when it is in a vendored file."""
    if r.get("term_from"):
        r = {**r, "term": ""}
    elif r.get("packed_term") is not None:
        r = {**r, "term": r["packed_term"]}
    return {k: v for k, v in r.items() if k != "packed_term"}


def _row_key(r):
    """A hash of what defines a row before pinning (its packed term or vendored
    key, expectation, fuel, mode, policy and any given pin): a checkpointed
    row is reused only if its definition is unchanged."""
    import hashlib
    fields = {k: r.get(k) for k in ("term", "term_from", "store", "expect", "fuel", "mode",
                                    "pin_policy", "pin", "skip_aviary", "copy", "engines",
                                    "share_fuel")}
    return hashlib.sha256(json.dumps(fields, sort_keys=True).encode()).hexdigest()[:16]


def _save(ck, key, group):
    """Checkpoint a row with its fuel edges as one line, so a kill leaves the
    group whole or (a cut-off last line) absent, never a row without edges."""
    if ck is not None and group:
        rows = [_packed_row(x) for x in group]
        ck.write(json.dumps({"key": key, "rows": rows}, ensure_ascii=False) + "\n")
        ck.flush()


def pin(rows, checkpoint=None):
    """Pin rows. With `checkpoint` (a path), every pinned row and its fuel
    edges are appended there as they are made, and a row already in it is
    taken from it instead of run again, so a killed run resumes. A row is
    checkpointed only once all its runs agreed; rejected rows are run again."""
    prov = E.provenance()
    bad = []
    out = []
    done = {}
    if checkpoint is not None and checkpoint.exists():
        good = []
        for line in checkpoint.read_text().splitlines():
            try:
                group = json.loads(line)
            except json.JSONDecodeError:
                continue  # a line cut off by a kill: that row is run again
            good.append(line)
            done[group["rows"][0]["id"]] = group  # a row, then its fuel edges
        # Keep only whole lines, so what is appended next starts a line.
        checkpoint.write_text("".join(x + "\n" for x in good))
        print(f"   resuming: {len(done)} row groups from {checkpoint.name}", flush=True)
    ck = checkpoint.open("a") if checkpoint is not None else None
    for r in rows:
        key = _row_key(r)
        if r["id"] in done and done[r["id"]]["key"] == key:
            out.extend(done[r["id"]]["rows"])
            continue  # a group whose row changed since is run again
        n_before = len(out)
        packed = materialize(r)
        _check_term_text(r)
        r["size"] = E.leaves(r["term"])
        if packed is not None:
            r["packed_term"] = packed
        if r.get("pin_policy") in ("auto", "given"):
            got, problem = (auto_pin if r["pin_policy"] == "auto" else given_pin)(r, prov)
            if problem:
                bad.append((r["id"], r["expect"]["status"], problem))
            if got is None:
                continue
            out.append(got)
            if (got["pin"] and got["pin"]["steps"] <= EDGE_MAX
                    and got["expect"]["status"] in ("NORMAL", "WHNF")):
                out.extend(_edges(got, got["expect"]["status"]))
            print(f"   {got['id']:24s} {got['tier']:2s} pin={got['pin'] and got['pin']['steps']} "
                  f"share={got.get('share_ref')} via {got['pin'] and got['pin']['source']}", flush=True)
            _release(out[n_before:])
            _save(ck, key, out[n_before:])
            continue
        whnf = r["mode"] == "whnf"
        status, steps, nf = E.run_aviary([(r["term"], r["fuel"])], whnf=whnf)[0]
        exp = r["expect"]
        if outcome_problems(exp, status, nf):
            bad.append((r["id"], exp, (status, steps, nf)))
            continue
        r["pin"] = {"steps": steps, "source": f"aviary@{prov['aviary']}"}
        out.append(r)
        if status in ("NORMAL", "WHNF") and steps > 0:
            out.extend(_edges(r, status))
        _release(out[n_before:])
        _save(ck, key, out[n_before:])
    if ck is not None:
        ck.close()
    return out, bad


def _edges(r, status):
    steps = r["pin"]["steps"]
    if steps <= 0:
        return []
    out = []
    for d, st in ((-1, "FUEL"), (0, "FUEL"), (1, status)):
        e = dict(r)
        e["id"] = f"{r['id']}.fuel{d:+d}"
        e["fuel"] = steps + d
        # At fuel c and c + 1 the result reached is the expected one; at c - 1 only
        # the status (FUEL) and count are known.
        e["expect"] = ({**r["expect"], "status": st} if d >= 0 else {"status": st, "nf": None})
        e["expect_src"] = "fuel-edge"
        e["pin"] = {"steps": steps + min(d, 0), "source": r["pin"]["source"]}
        out.append(e)
    return out


def main(argv):
    fams = argv or list(FAMILIES)
    status = 0
    for f in fams:
        checkpoint = ROOT / "manifests" / f".{f}.partial.jsonl"
        rows, bad = pin(FAMILIES[f].rows(), checkpoint)
        for rid, exp, got in bad:
            print(f"[{f}] an engine disagrees with expectation: {rid}: expected {exp}, got {got}")
        if bad:
            print(f"[{f}] {len(bad)} rows rejected; manifest NOT written")
            status = 1
            continue
        path = ROOT / "manifests" / f"{f}.jsonl"
        with path.open("w") as fh:
            for r in rows:
                fh.write(json.dumps(_packed_row(r), ensure_ascii=False) + "\n")
        checkpoint.unlink(missing_ok=True)
        print(f"[{f}] wrote {len(rows)} rows to {path.relative_to(ROOT)}")
    return status


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
