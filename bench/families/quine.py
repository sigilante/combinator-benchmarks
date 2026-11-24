r"""The quine of ski-in-ski's appendix, rebuilt from its construction
(ski-in-ski appendix, Prop. ifix; reference script notes/checks/quine.py in
the research tree): Scott codes over S|K|I|App with four continuations,
Turing's fixed point, the requoter R, and t = h <h> with h = \y. App' y (R y).

t reduces to <t>. <t> itself is not a normal form: the code of an
application is App m n with App = \m n a b c d. d m n, and its SKI form
applied to two arguments still has redexes. Its normal form is computed
structurally (`normal_code`): a leaf's code is already normal, and
[a][b][c][d] (d M N) = K (K (K (S (S I (K M)) (K N)))) for normal M, N.
So the normal form of t must be exactly normal_code(t), an expected answer
derived from the construction and the abstraction rules, not from an engine.

Premise, not checked here: t ->> <t> (the appendix's Prop. ifix, mechanized in
lean-ski as Ifix.quine; the reference script checks it only observationally,
by decoding). The engines reaching exactly normal_code(t) is the empirical
check of the whole chain.
Terms are mini terms (str atoms, (fn, arg) tuples).
"""

from __future__ import annotations

from functools import lru_cache


def _app(*xs):
    t = xs[0]
    for x in xs[1:]:
        t = (t, x)
    return t


def _free_in(x, t):
    stack = [t]
    while stack:
        u = stack.pop()
        if isinstance(u, tuple):
            stack.extend(u)
        elif u == x:
            return True
    return False


def _abs(x, m):
    """Curry bracket abstraction with eta (the construction's own)."""
    if m == x:
        return "I"
    if not _free_in(x, m):
        return ("K", m)
    f, a = m
    if a == x and not _free_in(x, f):
        return f
    return (("S", _abs(x, f)), _abs(x, a))


def _lam(xs, body):
    for x in reversed(xs):
        body = _abs(x, body)
    return body


ENC_S = _lam("abcd", "a")
ENC_K = _lam("abcd", "b")
ENC_I = _lam("abcd", "c")
APP_C = _lam("mnabcd", _app("d", "m", "n"))


def enc(t):
    """The Scott code <t>, by an iterative post-order walk. Memoized by node
    identity, so equal but distinct subterms are encoded again (harmless)."""
    if isinstance(t, str):
        return {"S": ENC_S, "K": ENC_K, "I": ENC_I}[t]
    # post-order without recursion
    out = {}
    stack = [(t, False)]
    while stack:
        u, done = stack.pop()
        if isinstance(u, str):
            out[id(u), u] = {"S": ENC_S, "K": ENC_K, "I": ENC_I}[u]
            continue
        if done:
            out[id(u), None] = _app(APP_C, _get(out, u[0]), _get(out, u[1]))
        else:
            stack.append((u, True))
            stack.append((u[1], False))
            stack.append((u[0], False))
    return _get(out, t)


def _get(out, u):
    return out[(id(u), u)] if isinstance(u, str) else out[(id(u), None)]


@lru_cache(maxsize=1)
def quine():
    """(t, <t>)."""
    A = _lam("xy", _app("y", _app("x", "x", "y")))
    theta = (A, A)

    def app_p(u, v):  # App' u v = App (App <App> u) v
        return _app(APP_C, _app(APP_C, enc(APP_C), u), v)

    rgen = _lam("rq", _app("q", enc(ENC_S), enc(ENC_K), enc(ENC_I),
                           _lam("fa", app_p(_app("r", "f"), _app("r", "a")))))
    R = (theta, rgen)
    h = _lam("y", _app(APP_C, "y", _app(R, "y")))
    t = (h, enc(h))
    return t, enc(t)


def normal_code(t):
    """The normal form of <t>, built structurally (no reduction)."""
    leaf = {"S": ENC_S, "K": ENC_K, "I": ENC_I}
    out = {}
    stack = [(t, False)]
    while stack:
        u, done = stack.pop()
        if isinstance(u, str):
            continue
        if done:
            m = leaf[u[0]] if isinstance(u[0], str) else out[id(u[0])]
            n = leaf[u[1]] if isinstance(u[1], str) else out[id(u[1])]
            out[id(u)] = ("K", ("K", ("K", (("S", (("S", "I"), ("K", m))), ("K", n)))))
        elif id(u) not in out:
            stack.append((u, True))
            stack.append((u[1], False))
            stack.append((u[0], False))
    return leaf[t] if isinstance(t, str) else out[id(t)]
