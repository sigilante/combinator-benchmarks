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


#: Print budget for rows that check only status, count or head: the head is
#: the first token, which any budget keeps.
SMALL_PRINT_BUDGET = 64


def _budget(job):
    """A job is (term, fuel) or (term, fuel, print_budget). Printing a large
    result (a WHNF can unfold to millions of nodes) costs far more than the
    reduction, so rows that need no full result pass a small budget."""
    return job[2] if len(job) > 2 and job[2] else AVON_PRINT_BUDGET


def aviary_show(term, budget=None) -> str:
    """aviary's printed form, cut off after `budget` atoms with " ..." (as
    mini.show and Avon's --budget do); without a budget, aviary's own printer."""
    from aviary_kernel.terms import App
    if budget is None:
        return aviary_pretty(term)
    out, atoms, stack = [], 0, [("t", term)]
    while stack:
        kind, x = stack.pop()
        if kind == "s":
            out.append(x)
            continue
        head, args = x, []
        while isinstance(head, App):
            args.append(head.arg)
            head = head.fn
        out.append(aviary_pretty(head))
        atoms += 1
        if atoms > budget:
            out.append(" ...")
            break
        for a in args:  # args were collected last first: push so the first prints first
            if isinstance(a, App):
                stack += [("s", ")"), ("t", a), ("s", " (")]
            else:
                stack += [("t", a), ("s", " ")]
    return "".join(out)


def _aviary_one(job, whnf, timeout):
    text, fuel = job[0], job[1]
    # max_size is set far above any term here; a SIZE status would fail the row.
    r = av_reduce(aviary_parse(text), _ENV, whnf_only=whnf,
                  max_steps=fuel, max_size=10**8,
                  interrupt=_Deadline(timeout) if timeout else None)
    return r.status.name, r.steps, aviary_show(r.term, _budget(job))


def run_aviary(jobs, whnf=False, timeout=None):
    """aviary is tree rewriting at O(term size) per step, so even ~10^4-step
    rows can take minutes; `timeout` (seconds per job) yields status
    INTERRUPTED rather than a hang. Terms over ISOLATE_ABOVE characters run in
    a child process (see _child)."""
    return [_child("aviary", job, whnf, timeout) if len(job[0]) > ISOLATE_ABOVE
            else _aviary_one(job, whnf, timeout) for job in jobs]


AVON_MAX_RSS_MB = int(os.environ.get("BENCH_AVON_MAX_RSS_MB", 3000))  # machine rule: < 4 GB
BIG_FUEL = 10**8  # jobs with at least this much fuel run in their own process


class _Killed:
    """Result of an Avon run stopped by the harness (timeout or memory cap)."""

    def __init__(self, why):
        self.returncode = -1
        self.stdout = ""
        self.stderr = why
        self.why = why


def _rss_mb(pid):
    """Resident memory of `pid` and all its descendants (Avon may run under a
    wrapper such as /usr/bin/time), in MB."""
    out = subprocess.run(["ps", "-A", "-o", "pid=,ppid=,rss="],
                         capture_output=True, text=True).stdout
    kids, rss = {}, {}
    for line in out.splitlines():
        try:
            p, pp, r = (int(x) for x in line.split())
        except ValueError:
            continue
        kids.setdefault(pp, []).append(p)
        rss[p] = r
    total, stack = 0, [pid]
    while stack:
        p = stack.pop()
        total += rss.get(p, 0)
        stack.extend(kids.get(p, []))
    return total / 1024


def _avon_batch(cmd, texts, timeout=None):
    """Run one `avon batch` process with a watchdog: it is killed if it runs
    past `timeout` seconds (status TIMEOUT) or past AVON_MAX_RSS_MB of resident
    memory (status MEMORY). --budget bounds what Avon prints, not its heap; a
    diverging share-mode run can grow by ~500 MB/s."""
    import tempfile
    import time
    inp = "".join(t + "\n" for t in texts)
    with tempfile.TemporaryFile("w+") as fin, tempfile.TemporaryFile("w+") as fout, \
            tempfile.TemporaryFile("w+") as ferr:
        fin.write(inp)
        fin.seek(0)
        proc = subprocess.Popen(cmd, stdin=fin, stdout=fout, stderr=ferr, text=True)
        start = time.monotonic()
        delay = 0.01
        killed = None
        usage = None
        while True:
            # wait4 reaps the child with its own rusage (it and its descendants,
            # e.g. avon under /usr/bin/time), excluding the watchdog's `ps` runs.
            pid, status, ru = os.wait4(proc.pid, os.WNOHANG)
            if pid:
                usage = ru
                proc.returncode = os.waitstatus_to_exitcode(status)
                break
            if timeout is not None and time.monotonic() - start > timeout:
                killed = "TIMEOUT"
            elif _rss_mb(proc.pid) > AVON_MAX_RSS_MB:
                killed = "MEMORY"
            if killed:
                proc.kill()
                proc.wait()
                return _Killed(killed), []
            time.sleep(delay)
            delay = min(delay * 2, 0.1)
        fout.seek(0)
        ferr.seek(0)
        p = subprocess.CompletedProcess(cmd, proc.returncode, fout.read(), ferr.read())
        p.cpu = usage.ru_utime + usage.ru_stime
    # Split on "\n" only: str.splitlines() also splits on \v, \x1c, U+2028, ...
    lines = p.stdout.split("\n")
    if lines and lines[-1] == "":
        lines.pop()
    return p, lines


def run_avon(jobs, strategy="copy", whnf=False, timeout=None):
    """Run jobs through `avon batch`, one process per distinct fuel value (and
    one per job from BIG_FUEL up), each under the watchdog in `_avon_batch`.
    A batch stopped by the watchdog fails all its jobs (TIMEOUT or MEMORY);
    it is not rerun. A batch that fails otherwise (a term Avon cannot parse
    stops the whole batch) is rerun one job at a time, and a job that still
    fails gets status ERROR with Avon's stderr in place of a normal form."""
    if not AVON_BIN.exists():
        raise SystemExit(f"Avon binary not found at {AVON_BIN} (build it with `make` in ~/avon, "
                         "or set AVON_BIN, or pass --engines without avon-*)")
    out = [None] * len(jobs)
    groups: dict[tuple, list[int]] = {}
    for i, job in enumerate(jobs):
        fuel, budget = job[1], _budget(job)
        groups.setdefault((fuel, budget, i if fuel >= BIG_FUEL else -1), []).append(i)
    for (fuel, budget, _), idxs in groups.items():
        # --budget caps the printed result (default 10^6 nodes, cut with " ...").
        # Raised to 10^7 so normal forms such as 2^20's (~2.1M nodes) print whole.
        # Not higher: a FUEL row prints the term where it stopped, and in copy mode
        # that can hold an enormous discarded argument (10^9 once took this
        # process to 35 GB). A cut normal form fails the row; it cannot pass.
        cmd = [str(AVON_BIN), "batch", f"--strategy={strategy}", "--no-jets", f"--fuel={fuel}",
               f"--budget={budget}"]
        if whnf:
            cmd.append("--whnf")
        p, lines = _avon_batch(cmd, [jobs[i][0] for i in idxs], timeout)
        if isinstance(p, _Killed):
            for i in idxs:
                out[i] = (p.why, -1, "")
            continue
        if p.returncode == 0 and len(lines) == len(idxs):
            per = list(zip(idxs, lines))
        else:
            per = []
            for i in idxs:
                q, ls = _avon_batch(cmd, [jobs[i][0]], timeout)
                if q.returncode == 0 and len(ls) == 1:
                    per.append((i, ls[0]))
                elif isinstance(q, _Killed):
                    out[i] = (q.why, -1, "")
                else:
                    out[i] = ("ERROR", -1, f"rc={q.returncode}: {q.stderr.strip()[:300]}")
        for i, line in per:
            parts = line.split(" ", 2)
            try:
                out[i] = (parts[0], int(parts[1]), parts[2] if len(parts) > 2 else "")
            except (IndexError, ValueError):
                out[i] = ("ERROR", -1, f"unparseable output line: {line[:300]!r}")
    return out


#: Terms longer than this (characters) are reduced by mini and by aviary in a
#: child process: on SKIlark's multi-million-step runs mini's term grows by
#: ~2 GB, and aviary holds ~550 bytes a leaf, which CPython keeps after the
#: run, so in the caller it would pile up. Smaller terms stay in-process
#: (bench.selftest patches mini's rules in-process).
ISOLATE_ABOVE = 100_000


def _mini_one(job, whnf):
    text, fuel = job[0], job[1]
    if whnf:
        status, steps, t = mini.reduce_whnf(mini.parse(text), fuel)
    else:
        status, steps, t = mini.reduce(mini.parse(text), fuel)
    return status, steps, mini.show(t, budget=_budget(job))


def _child(engine, job, whnf, timeout=None):
    """One mini or aviary job in a fresh interpreter (python3 -m bench.engines
    --child), whose memory is freed when it exits."""
    import json
    p = subprocess.run([sys.executable, "-m", "bench.engines", "--child"],
                       input=json.dumps({"engine": engine, "job": list(job), "whnf": whnf,
                                         "timeout": timeout}),
                       capture_output=True, text=True,
                       cwd=Path(__file__).resolve().parent.parent)
    try:
        if p.returncode == 0:
            return tuple(json.loads(p.stdout))
    except ValueError:
        pass
    # Status CRASHED (stderr's tail in place of the normal form): never an
    # expected status, so the row fails and the error is reported.
    return ("CRASHED", 0, p.stderr[-500:])


def _mini_safe(job, whnf):
    """In-process mini, failing as the child does: CRASHED, not an exception."""
    try:
        return _mini_one(job, whnf)
    except (ValueError, RecursionError) as e:
        return ("CRASHED", 0, repr(e)[-500:])


def run_mini(jobs, whnf=False):
    return [_child("mini", job, whnf) if len(job[0]) > ISOLATE_ABOVE else _mini_safe(job, whnf)
            for job in jobs]


#: aviary holds the whole tree as Python objects, ~550 bytes a leaf: a
#: 5.2M-leaf SKIlark term passed 2.8 GB, while terms of up to 1.13M leaves ran
#: within the 3 GB cap (D2's compiled `words` runs). It is not run on terms of
#: more than AVIARY_MAX_LEAVES leaves (gen and check both).
AVIARY_MAX_LEAVES = 1_500_000

#: mini parses the whole term into Python tuples in its child process: D2's
#: largest, 19.5M leaves, ran with the check at a 2.5 GB peak. Larger terms
#: (D3's factorial and fibonacci, 21M to 46M leaves) are not run on mini.
MINI_MAX_LEAVES = 20_000_000


def leaves(text: str) -> int:
    """Leaf count of a printed term (its atoms), without parsing it."""
    import re
    return sum(1 for _ in re.finditer(r"[^ ()]+", text))


def aviary_can_run(size: int | None) -> bool:
    """Whether a term of `size` leaves fits aviary (None: size unknown, yes)."""
    return size is None or size <= AVIARY_MAX_LEAVES


def mini_can_run(text: str) -> bool:
    """mini knows S K I B C W; other bird names would be silently free atoms.
    Terms of more than MINI_MAX_LEAVES leaves are refused too."""
    if len(text) > 2 * MINI_MAX_LEAVES and leaves(text) > MINI_MAX_LEAVES:
        return False  # (n leaves need at least 2n - 1 characters, so short texts skip the count)
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


if __name__ == "__main__" and sys.argv[1:] == ["--child"]:
    import json
    req = json.loads(sys.stdin.read())
    job = tuple(req["job"])
    res = (_mini_one(job, req["whnf"]) if req["engine"] == "mini"
           else _aviary_one(job, req["whnf"], req["timeout"]))
    print(json.dumps(res))
