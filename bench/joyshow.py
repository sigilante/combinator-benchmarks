"""Read a SKIlark run's result back as a first-order term (families D2, D5).

A SKIlark run reduces to a Scott-encoded result (RVal of a stack, RErr,
RTime, RIO). `show_term(types)` is a closed S, K, I term that, applied to
such a result, rebuilds it over free atoms, so that the normal form of
`show (run)` *is* the result, printed (as family D3's `show` does for Nock
nouns):

    result   RVal s -> v_val <stack>;  RErr -> v_err;  RTime -> v_time;  RIO -> v_io
    stack    Empty -> v_nil;  Push i rest -> v_push <item> <rest>   (top first)
    item     Num n -> v_num <num>;  Logical b -> v_bool v_false|v_true;
             Char n -> v_char <num>;  Str t -> v_str <text>;  Set m -> v_set <members>;
             Quot q -> v_quot;  Sym w -> v_sym   (not read: see below)
    num      Pos m -> v_pos <nat>;  Neg m -> v_neg <nat>   (Neg m is -(m+1));
             a natural where the program's numbers are naturals
    nat      Zero -> v_z;  Suc p -> v_s <nat>
    text     TNil -> v_tnil;  TCons n rest -> v_tcons <num> <rest>
    members  SNil -> v_snil;  SCons m rest -> v_scons <nat> <rest>

`types` is the run's own type table ({type: [[ctor, arity], ...]}, recorded
by `python3 -m bench.vendor_d2 --types`): the compiled form keeps only the
constructors a program uses, so the result and item constructors' positions
differ from run to run. Each constructor is matched by its position in that
table, as SKIlark's own reader (`peel`) does; the other types must have the
orders listed above.

Raises ValueError on a type whose order differs from the above, an item or
result constructor with no reader, or a negative number where the program's
numbers are naturals; KeyError on an unknown outcome constructor. RErr, RTime
and RIO carry no payload here (none is read).

Quotations and symbols are shown as the bare atoms v_quot and v_sym: a
compiled quotation is a function (SKIlark reads it by running it), an
interpreted one a program over some thirty word constructors; neither is
read here. `expected_nf(outcome, types)` is the normal form a pinned outcome
must give, from SKIlark's own reading of it (its test tables'
`(ctor, payload)`), with every quotation and symbol as that atom.

The term is built from rules by aviary's bracket abstraction (the suite's
canonical one) and fixed points by Y.
"""

from __future__ import annotations

import ast
import hashlib
import json

from . import engines as E, mini

_CACHE: dict = {}


def _sig(types) -> str:
    return hashlib.sha256(json.dumps(types, sort_keys=True).encode()).hexdigest()[:10]


def _order(types, name, want):
    got = [c for c, _a in types[name]]
    if got != want:
        raise ValueError(f"type {name}: constructors {got}, expected {want}")


def _rules(types, tag):
    n = lambda base: f"Js{base}{tag}"
    L = [f"{n('Natr')} r m -> m v_z ({n('Natc')} r)",
         f"{n('Natc')} r p -> v_s (r p)",
         f"{n('Nat')} := Y {n('Natr')}"]
    _order(types, "nat", ["Zero", "Suc"])
    if "int" in types:
        _order(types, "int", ["Pos", "Neg"])
        L += [f"{n('Num')} m -> m {n('Pos')} {n('Neg')}",
              f"{n('Pos')} p -> v_pos ({n('Nat')} p)",
              f"{n('Neg')} p -> v_neg ({n('Nat')} p)"]
    else:
        L.append(f"{n('Num')} := {n('Nat')}")
    handler = {"Num": n("INum"), "Quot": "(K v_quot)", "Sym": "(K v_sym)", "Char": n("IChr")}
    L += [f"{n('INum')} x -> v_num ({n('Num')} x)",
          f"{n('IChr')} x -> v_char ({n('Num')} x)"]
    if "logical" in types:
        _order(types, "logical", ["False", "True"])
        L.append(f"{n('ILog')} b -> v_bool (b v_false v_true)")
        handler["Logical"] = n("ILog")
    if "text" in types:
        _order(types, "text", ["TNil", "TCons"])
        L += [f"{n('Txtr')} r x -> x v_tnil ({n('Txtc')} r)",
              f"{n('Txtc')} r c rest -> v_tcons ({n('Num')} c) (r rest)",
              f"{n('Txt')} := Y {n('Txtr')}",
              f"{n('IStr')} x -> v_str ({n('Txt')} x)"]
        handler["Str"] = n("IStr")
    if "set" in types:
        _order(types, "set", ["SNil", "SCons"])
        L += [f"{n('Setr')} r x -> x v_snil ({n('Setc')} r)",
              f"{n('Setc')} r m rest -> v_scons ({n('Nat')} m) (r rest)",
              f"{n('Set')} := Y {n('Setr')}",
              f"{n('ISet')} x -> v_set ({n('Set')} x)"]
        handler["Set"] = n("ISet")
    for c, a in types["item"]:
        if a != 1 or c not in handler:
            raise ValueError(f"item constructor {c}/{a} has no reader")
    L.append(f"{n('Item')} i -> i " + " ".join(handler[c] for c, _a in types["item"]))
    _order(types, "stack", ["Empty", "Push"])
    L += [f"{n('Stkr')} r s -> s v_nil ({n('Stkc')} r)",
          f"{n('Stkc')} r i rest -> v_push ({n('Item')} i) (r rest)",
          f"{n('Stk')} := Y {n('Stkr')}",
          f"{n('Val')} s -> v_val ({n('Stk')} s)"]
    res = {"RVal": n("Val"), "RErr": "v_err", "RTime": "v_time", "RIO": "(K (K (K v_io)))"}
    arity = {"RVal": 1, "RErr": 0, "RTime": 0, "RIO": 3}
    for c, a in types["result"]:
        if arity.get(c) != a:
            raise ValueError(f"result constructor {c}/{a} has no reader")
    L.append(f"{n('Res')} x -> x " + " ".join(res[c] for c, _a in types["result"]))
    return "\n".join(L), n("Res")


def show_term(types) -> str:
    """The closed S, K, I term that reads back a result of this type table."""
    key = _sig(types)
    if key not in _CACHE:
        rules, root = _rules(types, key.upper())
        E.define(rules)
        _CACHE[key] = E.to_basis(root, "ski")
    return _CACHE[key]


def expected_nf(outcome, types) -> str:
    """The normal form `show (run)` must reach for a pinned outcome
    `[ctor, repr(payload)]` (payload: the stack bottom first, as SKIlark's
    tables give it)."""
    ctor, payload = outcome
    if ctor != "RVal":
        return {"RErr": "v_err", "RTime": "v_time", "RIO": "v_io"}[ctor]

    def nat(k):
        if k < 0:
            raise ValueError(f"negative natural {k}")
        return "v_z" if k == 0 else f"v_s ({nat(k - 1)})"

    def num(k):
        if "int" in types:
            return f"v_pos ({nat(k)})" if k >= 0 else f"v_neg ({nat(-k - 1)})"
        return nat(k)

    def item(v):
        if isinstance(v, bool):
            return f"v_bool v_{'true' if v else 'false'}"
        if isinstance(v, int):
            return f"v_num ({num(v)})"
        if isinstance(v, list):  # an interpreted quotation, read as its elements
            return "v_quot"
        tag = v[0]
        if tag == "quot":         # a compiled quotation, read by running it
            return "v_quot"
        if tag == "Sym":
            return "v_sym"
        if tag == "Char":
            return f"v_char ({num(v[1])})"
        if tag == "Str":
            codes = [ord(c) for c in v[1]] if isinstance(v[1], str) else list(v[1])
            t = "v_tnil"
            for c in reversed(codes):
                t = f"v_tcons ({num(c)}) ({t})"
            return f"v_str ({t})"
        if tag == "Set":
            t = "v_snil"
            for m in reversed(v[1]):
                t = f"v_scons ({nat(m)}) ({t})"
            return f"v_set ({t})"
        raise ValueError(f"no reading for item {v!r}")

    s = "v_nil"
    for v in ast.literal_eval(payload):  # bottom first: the last item is the top
        s = f"v_push ({item(v)}) ({s})"
    return mini.show(mini.parse(f"v_val ({s})"))


def unread(nf: str) -> list:
    """The atoms in an expected normal form that stand for values not read
    (v_quot, v_sym)."""
    toks = set(nf.replace("(", " ").replace(")", " ").split())
    return sorted(toks & {"v_quot", "v_sym"})
