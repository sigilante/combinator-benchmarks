"""Family F: shape stressors (synthetic, parametric).

Terms built to a shape, each with a result and a contraction count that
follow from the shape by the reduction rules (`expect_src: "construction"`,
`pin_policy: "given"`, the pin's source giving the closed form), so every
engine that can run a row must reproduce both:

- `f.left.<n>`: the left spine `I I ... I x`, n I's. Normal form x in n
  contractions.
- `f.right.<n>`: the right nesting `I (I (... (I x)))`, n deep. Normal form x
  in n contractions: recursion depth in parsers and reducers.
- `f.snorm.<n>`: `S (S (... (S K)))`, n S's, already normal (each S has one
  argument), so 0 contractions: the normal form is the term itself, n deep,
  and must be printed whole: recursion depth in printers.
- `f.wide.<n>`: `x (I y) ... (I y)`, n arguments under a free head. Normal
  form `x y ... y` in n contractions: a long spine whose arguments must each
  be normalised.
- `f.dup.<n>`: D (D (... (D x))) with D = S I I, n D's. D t -> I t (I t) ->
  t (I t) -> t t in three contractions; copy mode copies t unreduced, so it is
  reduced twice: 3 (2^n - 1) contractions; the normal form is the full binary
  tree of x's with 2^n leaves. Sharing reduces each t once (Avon share mode
  counts 3n, recorded as share_ref, not expected).
- `f.dupki.<n>`: the same chain on K I. Here t -> I, so the chain collapses:
  normal form I, in 7 * 2^(n-1) - 4 copy-mode contractions (T(1) = 3,
  T(n) = 2 T(n-1) + 4: D t -> I t (I t) -> t (I t), t to I, I (I t) -> I t,
  t to I again). A small normal form behind an exponential copy-mode count:
  for n = 32 and 64 (about 1.5e10 and 6.5e19 contractions) no copy engine can
  finish, and the rows are share-only (`copy: False`; share mode counts 4n - 1).
- `f.wi.<n>` (BCKW): the chain with D = W I: W I t -> I t t -> t t, two
  contractions, 2 (2^n - 1) in all; same normal form as f.dup. Avon reads only
  S, K and I, so only aviary and mini can run these (aviary where it finishes
  within gen's timeout: not wi.16).

aviary, a reference interpreter, is not run on rows past its measured limits
(2026-11-26, aviary bfba908): its parser recurses per level of nesting and
exceeds Python's recursion limit between depth 2 * 10^4 and 3 * 10^4 (right,
snorm; right is already ~13 s at 2 * 10^4); its time grows quadratically on long spines (left: 1.3 s at n = 3,000,
15.5 s at 10^4; wide: 35 s at 10^4). Rows it cannot finish within gen's
aviary timeout (e.g. dup from n = 16, dupki from 20) are left to the other
engines either way. Every row is pin_policy "given" with a closed-form pin,
except the two share-only dupki rows (pin_policy "auto", no pin).

A row's term_ref, and its nf_ref if any, must be the row's own id (less any
fuel-edge suffix); check.validate enforces this.

Terms and normal forms over INLINE_MAX characters are not stored in the
manifest: the row names them (`term_ref`, `expect.nf_ref`, both "f.<shape>.<n>")
and `term` / `nf` below rebuild them.
"""

from __future__ import annotations

INLINE_MAX = 10_000

SOURCE = "bench/families/f_shapes.py (construction)"


def _nest(n, f, x):
    """f (f (... (f x))), n f's, with no parentheses around an atomic x."""
    inner = f"{f} {x}" if " " not in x else f"{f} ({x})"
    return f"{f} (" * (n - 1) + inner + ")" * (n - 1)


def _tree(n):
    """The normal form of f.dup.<n> and f.wi.<n>: N_0 = x, N_k = N_{k-1} N_{k-1}."""
    t = "x"
    for _ in range(n):
        t = f"{t} ({t})" if " " in t else f"{t} {t}"
    return t


def _shape(name):
    _f, shape, n = name.split(".")
    return shape, int(n)


def term(name):
    shape, n = _shape(name)
    return {
        "left": lambda: "I " * n + "x",
        "right": lambda: _nest(n, "I", "x"),
        "snorm": lambda: _nest(n, "S", "K"),
        "wide": lambda: "x" + " (I y)" * n,
        "dup": lambda: _nest(n, "S I I", "x"),
        "dupki": lambda: _nest(n, "S I I", "K I"),
        "wi": lambda: _nest(n, "W I", "x"),
    }[shape]()


def nf(name):
    shape, n = _shape(name)
    return {
        "left": lambda: "x",
        "right": lambda: "x",
        "snorm": lambda: term(name),
        "wide": lambda: "x" + " y" * n,
        "dup": lambda: _tree(n),
        "dupki": lambda: "I",
        "wi": lambda: _tree(n),
    }[shape]()


def steps(name):
    shape, n = _shape(name)
    return {
        "left": n, "right": n, "snorm": 0, "wide": n,
        "dup": 3 * (2**n - 1), "dupki": 7 * 2**(n - 1) - 4, "wi": 2 * (2**n - 1),
    }[shape]


CLOSED_FORM = {
    "left": "n", "right": "n", "snorm": "0", "wide": "n",
    "dup": "3 (2^n - 1)", "dupki": "7 * 2^(n-1) - 4", "wi": "2 (2^n - 1)",
}

#: (shape, basis, sizes, sizes at which aviary is not run)
PLAN = [
    ("left", "ski", [10**3, 10**4, 10**5, 10**6, 10**7], {10**5, 10**6, 10**7}),
    ("right", "ski", [10**3, 10**4, 10**5, 10**6, 10**7], {10**5, 10**6, 10**7}),
    ("snorm", "ski", [10**3, 10**4, 10**5, 10**6], {10**5, 10**6}),
    ("wide", "ski", [10**3, 10**4, 10**5, 10**6], {10**5, 10**6}),
    ("dup", "ski", [4, 8, 12, 16, 20], set()),
    ("dupki", "ski", [4, 8, 12, 16, 20, 24, 28], set()),
    ("wi", "bckw", [4, 8, 12, 16], set()),
]
SHARE_ONLY = [("dupki", 32), ("dupki", 64)]

NOTE = {
    "left": "left spine I I ... I x, n = {n}",
    "right": "right nesting I (I (... x)), depth {n}",
    "snorm": "normal term S (S (... (S K))), depth {n}: printed whole",
    "wide": "x (I y) ... (I y), {n} arguments",
    "dup": "D^{n} x, D = S I I: normal form of 2^{n} leaves",
    "dupki": "D^{n} (K I), D = S I I: normal form I, copy mode exponential",
    "wi": "(W I)^{n} x: normal form of 2^{n} leaves",
}


def _row(shape, basis, n):
    name = f"f.{shape}.{n}"
    t, want = term(name), nf(name)
    r = {"id": name, "family": "F", "basis": basis, "source": SOURCE,
         "mode": "nf", "expect_src": "construction",
         "note": NOTE[shape].format(n=n)}
    if len(t) > INLINE_MAX:
        r["term"], r["term_ref"] = "", name
    else:
        r["term"] = t
    r["expect"] = ({"status": "NORMAL", "nf_ref": name} if len(want) > INLINE_MAX
                   else {"status": "NORMAL", "nf": want})
    return r


def rows():
    out = []
    for shape, basis, sizes, no_aviary in PLAN:
        for n in sizes:
            r = _row(shape, basis, n)
            k = steps(r["id"])
            r.update(fuel=2 * k + 1000, pin_policy="given",
                     pin={"steps": k, "source": f"closed form {CLOSED_FORM[shape]}"})
            if n in no_aviary:
                r["skip_aviary"] = True
                r["note"] += "; aviary not run (past its measured limit, see family docstring)"
            out.append(r)
    for shape, n in SHARE_ONLY:
        r = _row(shape, "ski", n)
        r.update(fuel=None, pin_policy="auto", copy=False,
                 note=r["note"] + f"; share-only: copy mode would take {steps(r['id']):.2e} "
                                  f"contractions ({CLOSED_FORM[shape]})")
        out.append(r)
    return out
