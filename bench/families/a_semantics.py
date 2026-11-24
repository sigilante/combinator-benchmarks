"""Family A: semantics checks (tier XS).

Each case gives a source term (S/K/I, birds, or names defined below), the
expected result, and the bases it runs in. The expected normal form is written
in source form and expanded into each basis alongside the term, so the same case
checks that SKI, SK and BCKW agree (a metamorphic check).

Expected results come from the reduction rules by hand (`expect_src: "hand"`).
Cases whose result contains a partial application are SKI-only, because in
other bases a partial S is not printed as S.
"""

from .. import engines as E

ALL = ("ski", "sk", "bckw")
SKI = ("ski",)
OMEGA = "(S I I (S I I))"

E.define("""
NOT b -> b (K I) K
AND p q -> p q (K I)
OR p q -> p K q
PAIR x y f -> f x y
FST p -> p K
SND p -> p (K I)
""")

# (id, term, expected status, expected nf or None, bases, fuel, mode, note)
CASES = [
    # identities
    ("a.i", "I x1", "NORMAL", "x1", ALL, 100, "nf", "I"),
    ("a.skk", "S K K x1", "NORMAL", "x1", SKI, 100, "nf", "I = S K K"),
    ("a.sks", "S K S x1", "NORMAL", "x1", SKI, 100, "nf", "I = S K X for any X"),
    ("a.k", "K x1 x2", "NORMAL", "x1", ALL, 100, "nf", "K"),
    ("a.s", "S x1 x2 x3", "NORMAL", "x1 x3 (x2 x3)", ALL, 100, "nf", "S"),
    ("a.b", "B x1 x2 x3", "NORMAL", "x1 (x2 x3)", ALL, 100, "nf", "B"),
    ("a.c", "C x1 x2 x3", "NORMAL", "x1 x3 x2", ALL, 100, "nf", "C"),
    ("a.w", "W x1 x2", "NORMAL", "x1 x2 x2", ALL, 100, "nf", "W"),
    # laziness: the argument that is never used must never be reduced
    ("a.k_omega", f"K x1 {OMEGA}", "NORMAL", "x1", ALL, 1000, "nf", "laziness: K drops a divergent argument"),
    ("a.sk_omega", f"S K {OMEGA} x1", "NORMAL", "x1", SKI, 1000, "nf", "laziness: S K _ x = x"),
    ("a.ki_omega", f"K I {OMEGA}", "NORMAL", "I", ALL, 1000, "nf", "laziness: K I drops Omega"),
    ("a.ki_omega_x", f"K I {OMEGA} x1", "NORMAL", "x1", ALL, 1000, "nf", "laziness, applied"),
    ("a.pair_fst_omega", f"FST (PAIR x1 {OMEGA})", "NORMAL", "x1", ALL, 1000, "nf", "laziness under pairs"),
    # divergence
    ("a.omega", "S I I (S I I)", "FUEL", None, SKI, 1000, "nf", "Omega has no normal form"),
    ("a.omega_whnf", "S I I (S I I)", "FUEL", None, SKI, 1000, "whnf", "Omega has no WHNF"),
    ("a.y_f", "Y x1", "FUEL", None, ALL, 1000, "nf", "Y f has no normal form"),
    ("a.y_k", "Y (K x1)", "NORMAL", "x1", ALL, 1000, "nf", "Y (K x) = x"),
    ("a.theta_k", "Θ (K x1)", "NORMAL", "x1", ALL, 1000, "nf", "Turing's Theta = U U"),
    ("a.mm", "M M", "FUEL", None, ALL, 1000, "nf", "M M = Omega"),
    # open terms: reduction must continue under a free head
    ("a.head_atom", "x1 (I x2) (K x3 x4)", "NORMAL", "x1 x2 x3", ALL, 100, "nf", "args of a free head"),
    ("a.deep_arg", "x1 (x2 (x3 (I x4)))", "NORMAL", "x1 (x2 (x3 x4))", ALL, 100, "nf", "redex deep in args"),
    ("a.late_arg", "x1 x2 x3 x4 (K x5 x6)", "NORMAL", "x1 x2 x3 x4 x5", ALL, 100, "nf", "redex in the last arg"),
    # partial applications: their arguments must be normalised too
    ("a.partial_k", "K (I x1)", "NORMAL", "K x1", SKI, 100, "nf", "partial K"),
    ("a.partial_s1", "S (K (I x1))", "NORMAL", "S (K x1)", SKI, 100, "nf", "partial S, one arg"),
    ("a.partial_s2", "S (I x1) (I x2)", "NORMAL", "S x1 x2", SKI, 100, "nf", "partial S, two args"),
    ("a.partial_whnf", "S (I x1) (I x2)", "WHNF", None, SKI, 100, "whnf", "partial S is already WHNF"),
    # sharing-sensitive: copy duplicates the redex, share does not
    ("a.dup", "S I I (I x1)", "NORMAL", "x1 x1", ALL, 100, "nf", "duplicated redex"),
    ("a.dup2", "W (W x1) (K x2 x3)", "NORMAL", "x1 x2 x2 x2", ALL, 100, "nf", "nested W duplicates a redex"),
    # booleans and pairs (Church)
    ("a.not_t", "NOT K x1 x2", "NORMAL", "x2", ALL, 100, "nf", "not true"),
    ("a.not_f", "NOT (K I) x1 x2", "NORMAL", "x1", ALL, 100, "nf", "not false"),
    ("a.and_tf", "AND K (K I) x1 x2", "NORMAL", "x2", ALL, 100, "nf", "and true false"),
    ("a.or_ft", "OR (K I) K x1 x2", "NORMAL", "x1", ALL, 100, "nf", "or false true"),
    ("a.snd", "SND (PAIR x1 x2)", "NORMAL", "x2", ALL, 100, "nf", "snd"),
    # long names and odd atom spellings
    ("a.names", "foo_bar (I baz9) (K q_ x9)", "NORMAL", "foo_bar baz9 q_", ALL, 100, "nf", "multi-character atoms"),
]


def rows():
    out = []
    for cid, term, status, nf, bases, fuel, mode, note in CASES:
        for b in bases:
            out.append({
                "id": f"{cid}.{b}",
                "family": "A",
                "basis": b,
                "term": E.to_basis(term, b),
                "source": term,
                "fuel": fuel,
                "mode": mode,
                "expect": {"status": status,
                           "nf": E.to_basis(nf, b) if nf is not None else None},
                "expect_src": "hand",
                "note": note,
            })
    return out
