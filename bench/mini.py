"""A small, independent combinator reducer: the suite's third oracle.

Written from the textbook rules, not from aviary or Avon, so it does not share
their lineage. It knows only S, K, I, B, C, W; every other atom is free.

Terms are tuples: an atom is a str, an application is (fn, arg).
Strategy: normal order (leftmost-outermost) to full normal form, counting one
step per contraction. This is the order aviary and Avon's copy mode use.

Fuel semantics (the suite's convention, shared with aviary and Avon): at most
`fuel` contractions are performed, and the status is FUEL whenever
steps >= fuel, even if the term reached is normal. So a term needing exactly c
contractions reports NORMAL only when fuel >= c + 1.
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

_TOKEN = None


def parse(text: str):
    """Parse the printed form. Only ASCII space separates tokens; any other
    character that is not a parenthesis is part of an atom (as in Avon and
    aviary, where `x<U+00A0>y` is one atom). Iterative, so deep nesting is fine.
    Raises ValueError on an empty term or unbalanced parentheses."""
    import re
    global _TOKEN
    if _TOKEN is None:
        _TOKEN = re.compile(r"\(|\)|[^ ()]+")
    stack = [None]          # accumulators, one per open parenthesis level
    for tok in _TOKEN.findall(text):
        if tok == "(":
            stack.append(None)
        elif tok == ")":
            if len(stack) == 1:
                raise ValueError("unbalanced parentheses")
            item = stack.pop()
            if item is None:
                raise ValueError("empty parentheses")
            stack[-1] = item if stack[-1] is None else (stack[-1], item)
        else:
            stack[-1] = tok if stack[-1] is None else (stack[-1], tok)
    if len(stack) != 1:
        raise ValueError("unbalanced parentheses")
    if stack[0] is None:
        raise ValueError("empty term")
    return stack[0]


def show(t, budget: int | None = None) -> str:
    """Printed form: application to the left, parentheses around an argument
    that is itself an application (the form aviary and Avon both print).

    Terms share subterms, so a small structure can print as an enormous tree.
    With `budget`, printing stops after that many atoms and ends in " ..."
    (as Avon does), which never parses as a normal form."""
    out = []
    atoms = 0
    stack = [("t", t)]
    while stack:
        kind, x = stack.pop()
        if kind == "s":
            out.append(x)
            continue
        if isinstance(x, str):
            out.append(x)
            atoms += 1
            if budget is not None and atoms > budget:
                out.append(" ...")
                break
            continue
        head, args = x, []
        while isinstance(head, tuple):
            args.append(head[1])
            head = head[0]
        args.reverse()
        out.append(head)
        atoms += 1
        if budget is not None and atoms > budget:
            out.append(" ...")
            break
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
    status, steps, t = _reduce(t, fuel)
    if steps >= fuel:
        status = "FUEL"
    return status, steps, t


def reduce_whnf(t, fuel: int):
    """Head reduction to weak head normal form. Returns (status, steps, term),
    status WHNF or FUEL under the same fuel convention as `reduce`."""
    t, steps = _whnf(t, fuel)
    head, args = _spine(t)
    status = "FUEL" if steps >= fuel or _is_redex(head, args) else "WHNF"
    return status, steps, t


def _reduce(t, fuel: int):
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
