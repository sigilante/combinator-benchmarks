"""Engine adapters. Each returns a list of (status, steps, nf_text) for a list
of (term_text, fuel) jobs.

- aviary: the reference, imported from its repo (not the older site-packages copy).
- avon-copy / avon-share: the Avon release binary, `batch`, always `--no-jets`.
- mini: bench/mini.py, the independent textbook reducer (S K I B C W only).
"""

from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path

AVIARY_REPO = Path(os.environ.get("AVIARY_REPO", Path.home() / "Code/urbit/aviary"))
AVON_BIN = Path(os.environ.get("AVON_BIN", Path.home() / "avon/build/avon"))

if str(AVIARY_REPO) not in sys.path:
    sys.path.insert(0, str(AVIARY_REPO))

from aviary_kernel.environment import Environment  # noqa: E402
from aviary_kernel.parser import parse_cell  # noqa: E402
from aviary_kernel.reduce import reduce as av_reduce  # noqa: E402
from aviary_kernel.abstraction import expand, BY_KEY  # noqa: E402

from . import mini  # noqa: E402

_ENV = Environment()


def git_rev(path: Path) -> str:
    try:
        return subprocess.run(["git", "-C", str(path), "rev-parse", "--short", "HEAD"],
                              capture_output=True, text=True, check=True).stdout.strip()
    except Exception:
        return "unknown"


def provenance() -> dict:
    return {"aviary": git_rev(AVIARY_REPO), "avon": git_rev(AVON_BIN.parent.parent)}


def aviary_parse(text: str):
    return parse_cell(text)[0].expr


def aviary_pretty(term) -> str:
    return _ENV.pretty(term)


def to_basis(text: str, basis: str) -> str:
    """Expand a term written with birds into basis 'ski', 'sk' or 'bckw'."""
    return aviary_pretty(expand(aviary_parse(text), _ENV, BY_KEY[basis]))


def run_aviary(jobs, whnf=False):
    out = []
    for text, fuel in jobs:
        r = av_reduce(aviary_parse(text), _ENV, whnf_only=whnf,
                      max_steps=fuel, max_size=10**8)
        out.append((r.status.name, r.steps, aviary_pretty(r.term)))
    return out


def run_avon(jobs, strategy="copy", whnf=False):
    """Run jobs through `avon batch`, one process per distinct fuel value."""
    out = [None] * len(jobs)
    by_fuel: dict[int, list[int]] = {}
    for i, (_, fuel) in enumerate(jobs):
        by_fuel.setdefault(fuel, []).append(i)
    for fuel, idxs in by_fuel.items():
        cmd = [str(AVON_BIN), "batch", f"--strategy={strategy}", "--no-jets", f"--fuel={fuel}"]
        if whnf:
            cmd.append("--whnf")
        inp = "".join(jobs[i][0] + "\n" for i in idxs)
        p = subprocess.run(cmd, input=inp, capture_output=True, text=True)
        lines = p.stdout.splitlines()
        if p.returncode != 0 or len(lines) != len(idxs):
            raise RuntimeError(f"avon batch failed (rc={p.returncode}): {p.stderr[:500]}")
        for i, line in zip(idxs, lines):
            parts = line.split(" ", 2)
            out[i] = (parts[0], int(parts[1]), parts[2] if len(parts) > 2 else "")
    return out


def run_mini(jobs, whnf=False):
    if whnf:
        raise NotImplementedError("mini reduces to full normal form only")
    out = []
    for text, fuel in jobs:
        status, steps, t = mini.reduce(mini.parse(text), fuel)
        # The suite's fuel convention (aviary's and Avon's): FUEL whenever
        # steps >= fuel, even if the term reached is normal.
        if steps >= fuel:
            status = "FUEL"
        out.append((status, steps, mini.show(t)))
    return out


def mini_can_run(text: str) -> bool:
    """mini knows S K I B C W; other bird names would be silently free atoms."""
    from aviary_kernel.birds import BY_NAME
    for tok in text.replace("(", " ").replace(")", " ").split():
        if tok in mini.RULES:
            continue
        if tok in BY_NAME or tok in ("Θ", "Theta") or tok in _ENV.definitions:
            return False
    return True


ENGINES = {
    "aviary": run_aviary,
    "avon-copy": lambda jobs, whnf=False: run_avon(jobs, "copy", whnf),
    "avon-share": lambda jobs, whnf=False: run_avon(jobs, "share", whnf),
    "mini": run_mini,
}


def define(src: str) -> None:
    """Register `NAME x y -> body` rules and `NAME := body` aliases in the shared
    aviary environment, so later terms can be expanded to a basis. Names must be
    capitalised and must not clash with a bird."""
    from aviary_kernel.parser import Rule, Alias
    for st in parse_cell(src):
        if isinstance(st, Rule):
            _ENV.define_rule(st.name_token.canonical,
                             tuple(t.canonical for t in st.var_tokens), st.expr)
        elif isinstance(st, Alias):
            _ENV.define_alias(st.name_token.canonical, st.expr)
        else:
            raise ValueError(f"not a definition: {st}")


_SKI_ATOMS = {"S", "K", "I"}


def avon_can_run(text: str) -> bool:
    """Avon reads S, K, I and free atoms; bird names and definitions are refused."""
    from aviary_kernel.birds import BY_NAME
    for tok in text.replace("(", " ").replace(")", " ").split():
        if tok in _SKI_ATOMS:
            continue
        if tok in BY_NAME or tok in ("Θ", "Theta") or tok in _ENV.definitions:
            return False
    return True
