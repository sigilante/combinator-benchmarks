"""A small, independent combinator reducer: the suite's third oracle.

Written from the textbook rules, not from aviary or Avon, so it does not share
their lineage. It knows only S, K, I, B, C, W; every other atom is free.

Terms are tuples: an atom is a str, an application is (fn, arg).
Strategy: normal order (leftmost-outermost) to full normal form, counting one
step per contraction. This is the order aviary and Avon's copy mode use.

Fuel semantics: at most `fuel` contractions are performed. A term that needs
exactly `fuel` contractions reports NORMAL; one that needs more reports FUEL.
"""

from __future__ import annotations

import hashlib

# name -> (arity, builder from the argument list)
RULES = {
    "S": (3, lambda a: ((a[0], a[2]), (a[1], a[2]))),
    "K": (2, lambda a: a[0]),
    "I": (1, lambda a: a[0]),
    "B": (3, lambda a: (a[0], (a[1], a[2]))),
    "C": (3, lambda a: ((a[0], a[2]), a[1])),
    "W": (2, lambda a: ((a[0], a[1]), a[1])),
}


# --- parsing and printing -------------------------------------------------

def parse(text: str):
    toks = text.replace("(", " ( ").replace(")", " ) ").split()
    pos = 0

    def seq():
        nonlocal pos
        acc = None
        while pos < len(toks) and toks[pos] != ")":
            t = toks[pos]
            pos += 1
            if t == "(":
                item = seq()
                if pos >= len(toks) or toks[pos] != ")":
                    raise ValueError("unbalanced parentheses")
                pos += 1
            else:
                item = t
            acc = item if acc is None else (acc, item)
        if acc is None:
            raise ValueError("empty term")
        return acc

    t = seq()
    if pos != len(toks):
        raise ValueError("trailing input")
    return t


def show(t) -> str:
    """Printed form: application to the left, parentheses around an argument
    that is itself an application (the form aviary and Avon both print)."""
    out = []
    stack = [("t", t)]
    while stack:
        kind, x = stack.pop()
        if kind == "s":
            out.append(x)
            continue
        if isinstance(x, str):
            out.append(x)
            continue
        head, args = x, []
        while isinstance(head, tuple):
            args.append(head[1])
            head = head[0]
        args.reverse()
        out.append(head)
        for a in reversed(args):
            if isinstance(a, tuple):
                stack.append(("s", ")"))
                stack.append(("t", a))
                stack.append(("s", " ("))
            else:
                stack.append(("t", a))
                stack.append(("s", " "))
    return "".join(out)


def nf_hash(text: str) -> str:
    """Hash of a canonical printed form: parse, then re-print."""
    return hashlib.sha256(show(parse(text)).encode()).hexdigest()[:16]


def size(t) -> int:
    n, stack = 0, [t]
    while stack:
        x = stack.pop()
        if isinstance(x, tuple):
            stack.extend(x)
        else:
            n += 1
    return n


# --- reduction ------------------------------------------------------------

def _spine(t):
    args = []
    while isinstance(t, tuple):
        args.append(t[1])
        t = t[0]
    args.reverse()
    return t, args


def _rebuild(head, args):
    for a in args:
        head = (head, a)
    return head


def _whnf(t, budget):
    """Contract head redexes until none remains or budget runs out.
    Returns (term, steps)."""
    steps = 0
    while True:
        head, args = _spine(t)
        rule = RULES.get(head) if isinstance(head, str) else None
        if rule is None or len(args) < rule[0] or steps >= budget:
            return t, steps
        n, build = rule
        t = _rebuild(build(args[:n]), args[n:])
        steps += 1


def reduce(t, fuel: int):
    """Normal-order reduction to full normal form. Returns (status, steps, term)."""
    steps = 0
    t, s = _whnf(t, fuel)
    steps += s
    # Iterative: reduce arguments left to right, each to normal form.
    # Frame: [head, done_args, todo_args]
    head, args = _spine(t)
    if _is_redex(head, args):
        return "FUEL", steps, t
    root = [head, [], list(args)]
    stack = [root]
    while stack:
        fr = stack[-1]
        if not fr[2]:
            stack.pop()
            built = _rebuild(fr[0], fr[1])
            if stack:
                stack[-1][1].append(built)
            else:
                return "NORMAL", steps, built
            continue
        a = fr[2].pop(0)
        a, s = _whnf(a, fuel - steps)
        steps += s
        h, as_ = _spine(a)
        if _is_redex(h, as_):  # budget ran out mid-argument
            fr[1].append(a)
            return "FUEL", steps, _reassemble(stack)
        stack.append([h, [], list(as_)])
    raise AssertionError("unreachable")


def _is_redex(head, args):
    rule = RULES.get(head) if isinstance(head, str) else None
    return rule is not None and len(args) >= rule[0]


def _reassemble(stack):
    built = None
    for f in reversed(stack):
        done = f[1] + ([built] if built is not None else []) + f[2]
        built = _rebuild(f[0], done)
    return built
