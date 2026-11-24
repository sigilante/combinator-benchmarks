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
AVON_PRINT_BUDGET = 10_000_000
AVON_BIN = Path(os.environ.get("AVON_BIN", Path.home() / "avon/build/avon"))

# aviary's parser, expander and printer recurse on term depth; Church numerals
# such as C871 nest that deep. 50,000 is enough for every term in the suite.
sys.setrecursionlimit(max(sys.getrecursionlimit(), 50_000))

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


def _dirty(path: Path) -> bool:
    try:
        out = subprocess.run(["git", "-C", str(path), "status", "--porcelain", "--untracked-files=no"],
                             capture_output=True, text=True, check=True).stdout
        return bool(out.strip())
    except Exception:
        return True


def avon_identity() -> dict:
    """What was actually run: the binary's version line, mtime and hash. The
    repo revision alone does not say whether the binary was rebuilt from it."""
    import datetime
    import hashlib
    if not AVON_BIN.exists():
        return {"bin": str(AVON_BIN), "missing": True}
    v = subprocess.run([str(AVON_BIN), "--version"], capture_output=True, text=True).stdout.strip()
    st = AVON_BIN.stat()
    return {"bin": str(AVON_BIN), "version": v,
            "mtime": datetime.datetime.fromtimestamp(st.st_mtime).isoformat(timespec="seconds"),
            "sha256": hashlib.sha256(AVON_BIN.read_bytes()).hexdigest()[:16]}


def provenance() -> dict:
    av = git_rev(AVIARY_REPO) + ("+dirty" if _dirty(AVIARY_REPO) else "")
    avon_repo = AVON_BIN.parent.parent
    return {"aviary": av,
            "avon": git_rev(avon_repo) + ("+dirty" if _dirty(avon_repo) else ""),
            "avon_bin": avon_identity()}


def aviary_parse(text: str):
    return parse_cell(text)[0].expr


def aviary_pretty(term) -> str:
    return _ENV.pretty(term)


def to_basis(text: str, basis: str) -> str:
    """Expand a term written with birds into basis 'ski', 'sk' or 'bckw'."""
    return aviary_pretty(expand(aviary_parse(text), _ENV, BY_KEY[basis]))


class _Deadline:
    """aviary's interrupt flag, set by the clock (polled between contractions)."""

    def __init__(self, seconds):
        import time
        self._t = time.monotonic() + seconds
        self._now = time.monotonic

    def is_set(self):
        return self._now() > self._t


def run_aviary(jobs, whnf=False, timeout=None):
    """aviary is tree rewriting at O(term size) per step, so even ~10^4-step
    rows can take minutes; `timeout` (seconds per job) yields status
    INTERRUPTED rather than a hang."""
    out = []
    for text, fuel in jobs:
        # max_size is set far above any term here; a SIZE status would fail the row.
        r = av_reduce(aviary_parse(text), _ENV, whnf_only=whnf,
                      max_steps=fuel, max_size=10**8,
                      interrupt=_Deadline(timeout) if timeout else None)
        out.append((r.status.name, r.steps, aviary_pretty(r.term)))
    return out


class _Timeout:
    returncode = -1
    stdout = ""
    stderr = "timeout"


def _avon_batch(cmd, texts, timeout=None):
    inp = "".join(t + "\n" for t in texts)
    try:
        p = subprocess.run(cmd, input=inp, capture_output=True, text=True, timeout=timeout)
    except subprocess.TimeoutExpired:
        return _Timeout(), []
    # Split on "\n" only: str.splitlines() also splits on \v, \x1c, U+2028, ...
    lines = p.stdout.split("\n")
    if lines and lines[-1] == "":
        lines.pop()
    return p, lines


def run_avon(jobs, strategy="copy", whnf=False, timeout=None):
    """Run jobs through `avon batch`, one process per distinct fuel value.
    If a batch fails (a term Avon cannot parse stops the whole batch), its
    jobs are rerun one by one, and a job that still fails is reported with
    status ERROR and Avon's stderr in place of a normal form."""
    if not AVON_BIN.exists():
        raise SystemExit(f"Avon binary not found at {AVON_BIN} (build it with `make` in ~/avon, "
                         "or set AVON_BIN, or pass --engines without avon-*)")
    out = [None] * len(jobs)
    by_fuel: dict[int, list[int]] = {}
    for i, (_, fuel) in enumerate(jobs):
        by_fuel.setdefault(fuel, []).append(i)
    for fuel, idxs in by_fuel.items():
        # --budget caps the printed result (default 10^6 nodes, cut with " ...").
        # Raised to 10^7 so normal forms such as 2^20's (~2.1M nodes) print whole.
        # Not higher: a FUEL row prints the term where it stopped, and in copy mode
        # that can hold an enormous discarded argument (10^9 once took this
        # process to 35 GB). A cut normal form fails the row; it cannot pass.
        cmd = [str(AVON_BIN), "batch", f"--strategy={strategy}", "--no-jets", f"--fuel={fuel}",
               f"--budget={AVON_PRINT_BUDGET}"]
        if whnf:
            cmd.append("--whnf")
        p, lines = _avon_batch(cmd, [jobs[i][0] for i in idxs], timeout)
        if p.returncode == 0 and len(lines) == len(idxs):
            per = list(zip(idxs, lines))
        else:
            per = []
            for i in idxs:
                q, ls = _avon_batch(cmd, [jobs[i][0]], timeout)
                if q.returncode == 0 and len(ls) == 1:
                    per.append((i, ls[0]))
                elif isinstance(q, _Timeout):
                    out[i] = ("TIMEOUT", -1, "")
                else:
                    out[i] = ("ERROR", -1, f"rc={q.returncode}: {q.stderr.strip()[:300]}")
        for i, line in per:
            parts = line.split(" ", 2)
            try:
                out[i] = (parts[0], int(parts[1]), parts[2] if len(parts) > 2 else "")
            except (IndexError, ValueError):
                out[i] = ("ERROR", -1, f"unparseable output line: {line[:300]!r}")
    return out


def run_mini(jobs, whnf=False):
    if whnf:
        raise NotImplementedError("mini reduces to full normal form only")
    out = []
    for text, fuel in jobs:
        status, steps, t = mini.reduce(mini.parse(text), fuel)
        out.append((status, steps, mini.show(t, budget=AVON_PRINT_BUDGET)))
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
    "avon-copy": lambda jobs, whnf=False, timeout=None: run_avon(jobs, "copy", whnf, timeout),
    "avon-share": lambda jobs, whnf=False, timeout=None: run_avon(jobs, "share", whnf, timeout),
    "mini": lambda jobs, whnf=False, timeout=None: run_mini(jobs, whnf),
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
