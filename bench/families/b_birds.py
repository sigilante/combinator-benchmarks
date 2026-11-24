"""Family B: every bird in every basis (tier XS-S).

Each of aviary's birds is applied to as many fresh atoms as its arity and
reduced natively and as its SKI, SK and BCKW expansions. The expected normal
form is the bird's defining equation instantiated with those atoms
(`expect_src: "aviary-rule"`). Note that this source is aviary's own table, so
a wrong rule in aviary would pass here; aviary's tests check its table against
Rathman's chart, and the mini reducer checks the SKI/SK/BCKW rows from the
textbook S K I B C W rules alone.

Sage birds (Y, and Smullyan's constructions) have no normal form when applied
to an atom; they are checked by `X (K x1) -> x1`.
"""

from aviary_kernel.birds import BIRDS
from aviary_kernel.terms import Atom, App

from .. import engines as E

BASES = ("native", "ski", "sk", "bckw")

# Smullyan-style sage constructions (To Mock a Mockingbird, ch. 13 and 18),
# each checked only by X (K x1) -> x1 here.
SAGES = [
    ("Y", "Y"),
    ("theta", "U U"),
    ("bml", "B M L"),
    ("bm_cbm", "B M (C B M)"),
    ("sll", "S L L"),
    ("lol", "L O (L O)"),
]


def _subst(t, m):
    if isinstance(t, Atom):
        return m.get(t.name, t)
    return App(_subst(t.fn, m), _subst(t.arg, m))


def _basis_term(src, b):
    return src if b == "native" else E.to_basis(src, b)


def rows():
    out = []
    for bird in BIRDS:
        if bird.name == "Y":
            continue  # covered by SAGES
        atoms = [f"x{i+1}" for i in range(bird.arity)]
        src = " ".join([bird.name] + atoms)
        expect = E.aviary_pretty(_subst(bird.rule, {f: Atom(a) for f, a in zip(bird.formals, atoms)}))
        safe = bird.name.replace("*", "s").replace("'", "p").replace("Ê", "Ehat") \
            .replace("Φ", "Phi").replace("Ψ", "Psi")
        for b in BASES:
            out.append({
                "id": f"b.{safe}.{b}", "family": "B", "basis": b,
                "term": _basis_term(src, b), "source": src,
                "fuel": 10_000, "mode": "nf",
                "expect": {"status": "NORMAL", "nf": expect},
                "expect_src": "aviary-rule",
                "note": f"{bird.bird_name}: {bird.name} {' '.join(bird.formals)} = {E.aviary_pretty(bird.rule)}",
            })
    for name, sage in SAGES:
        src = f"{sage} (K x1)" if " " not in sage else f"({sage}) (K x1)"
        for b in BASES:
            out.append({
                "id": f"b.sage.{name}.{b}", "family": "B", "basis": b,
                "term": _basis_term(src, b), "source": src,
                "fuel": 10_000, "mode": "nf",
                "expect": {"status": "NORMAL", "nf": "x1"},
                "expect_src": "hand",
                "note": f"sage bird {sage}: X (K x) = x",
            })
    return out
