"""Shared-subterm storage for families whose terms repeat large pieces.

SKIlark's interpreted programs each carry the same ~77k-leaf interpreter, and
family D2's 944 runs as plain text would be ~800 MB. `compress` finds the subterms of
at least MIN_SIZE leaves that occur in two or more of a set of terms, stores
each once under a content hash, and writes the terms with `@<hash>` tokens in
their place. `expand` restores the plain printed term, which is all any
engine ever sees. Hashes are of the canonical printed text, so a store can be
checked against its own entries. The restored text may carry extra
parentheses where a shared subterm stood in head position ("(K I x) y" for
"K I x y"); it parses to the same term.
"""

from __future__ import annotations

import hashlib
import json
from pathlib import Path

from . import mini

MIN_SIZE = 1000


def _parse_interned(text, table):
    """Parse a printed term into a hash-consed DAG: structurally equal subterms
    are one node (the same tuple), shared across every term parsed with the
    same table. Iterative, like mini.parse."""
    import re
    stack = [None]
    for tok in re.findall(r"\(|\)|[^ ()]+", text):
        if tok == "(":
            stack.append(None)
            continue
        if tok == ")":
            item = stack.pop()
        else:
            item = table.setdefault(tok, tok)
        if stack[-1] is None:
            stack[-1] = item
        else:
            key = (id(stack[-1]), id(item))
            node = table.get(key)
            if node is None:
                node = (stack[-1], item)
                table[key] = node
            stack[-1] = node
    return stack[0]


class Compressor:
    """Incremental `compress`: add terms one at a time (only the hash-consed
    DAG is kept, not the text), then call finish()."""

    def __init__(self):
        self.table, self.roots = {}, {}

    def add(self, name, text):
        self.roots[name] = _parse_interned(text, self.table)

    def node(self, f, a):
        """The interned application of two interned nodes (or leaf names):
        for building a term from a graph without printing it."""
        f, a = self.table.setdefault(f, f) if isinstance(f, str) else f, \
            self.table.setdefault(a, a) if isinstance(a, str) else a
        key = (id(f), id(a))
        n = self.table.get(key)
        if n is None:
            n = self.table[key] = (f, a)
        return n

    def add_node(self, name, root):
        """Add a term already interned through `node` (or `add`'s table)."""
        self.roots[name] = root

    def finish(self):
        return _compress_roots(self.roots)


def compress(texts: dict) -> tuple[dict, dict]:
    """texts: name -> printed term. Returns (name -> text with @refs,
    store: ref -> text with @refs). A subterm of at least MIN_SIZE leaves is
    stored once if it has two or more parents in the hash-consed DAG of all
    the terms (or is itself a whole term occurring twice)."""
    table = {}
    return _compress_roots({k: _parse_interned(v, table) for k, v in texts.items()})


def _compress_roots(roots):
    # Unique nodes, children before parents.
    order, seen = [], set()
    for t in roots.values():
        stack = [(t, False)]
        while stack:
            u, done = stack.pop()
            if done:
                order.append(u)
                continue
            if id(u) in seen:
                continue
            seen.add(id(u))
            stack.append((u, True))
            if isinstance(u, tuple):
                stack.append((u[1], False))
                stack.append((u[0], False))
    size, parents = {}, {}
    for u in order:
        size[id(u)] = 1 if isinstance(u, str) else size[id(u[0])] + size[id(u[1])]
        if isinstance(u, tuple):
            for c in u:
                parents[id(c)] = parents.get(id(c), 0) + 1
    for t in roots.values():
        parents[id(t)] = parents.get(id(t), 0) + 1
    shared = {id(u) for u in order if size[id(u)] >= MIN_SIZE and parents.get(id(u), 0) >= 2}
    refs, store = {}, {}

    def ref_of(u):
        if id(u) not in refs:
            r = hashlib.sha256(mini.show(u).encode()).hexdigest()[:16]
            refs[id(u)] = r
            store[r] = render(u, True)
        return refs[id(u)]

    def render(t, top):
        out = []
        stack = [("t", t, top)]
        while stack:
            kind, x, is_top = stack.pop()
            if kind == "s":
                out.append(x)
                continue
            if not is_top and id(x) in shared:
                out.append("@" + ref_of(x))
                continue
            if isinstance(x, str):
                out.append(x)
                continue
            head, args = x, []
            while isinstance(head, tuple) and (head is x or id(head) not in shared):
                args.append(head[1])
                head = head[0]
            args.reverse()
            items = [("t", head, False)]
            for a in args:
                if isinstance(a, tuple) and id(a) not in shared:
                    items += [("s", " (", False), ("t", a, False), ("s", ")", False)]
                else:
                    items += [("s", " ", False), ("t", a, False)]
            stack.extend(reversed(items))
        return "".join(out)

    out = {k: render(t, False) for k, t in roots.items()}
    return out, store


def expand(text: str, store: dict, _cache: dict | None = None) -> str:
    """Replace every @ref token by its stored term, recursively. A reference
    in argument position expands inside parentheses."""
    cache = {} if _cache is None else _cache

    def full(ref):
        if ref not in cache:
            cache[ref] = expand(store[ref], store, cache)
        return cache[ref]

    parts = []
    for tok in text.split(" "):
        # a token may carry parentheses around it: "(@abc", "@abc)", "@abc))"
        core = tok.lstrip("(").rstrip(")")
        if core.startswith("@"):
            pre = tok[: len(tok) - len(tok.lstrip("("))]
            post = tok[len(tok.rstrip(")")):]
            parts.append(f"{pre}({full(core[1:])}){post}")
        else:
            parts.append(tok)
    return " ".join(parts)


def save(path: Path, store: dict):
    """Write JSON; gzip-compressed when the name ends in .gz (deterministic:
    no timestamp in the gzip header)."""
    data = (json.dumps(store, sort_keys=True) + "\n").encode()
    if str(path).endswith(".gz"):
        import gzip
        with open(path, "wb") as fh, gzip.GzipFile(fileobj=fh, mode="wb", mtime=0) as gz:
            gz.write(data)
    else:
        path.write_bytes(data)


def load(path: Path) -> dict:
    if str(path).endswith(".gz"):
        import gzip
        with gzip.open(path, "rb") as gz:
            return json.loads(gz.read())
    return json.loads(Path(path).read_text())
