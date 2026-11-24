# combinator-benchmarks

Correctness and speed benchmarks for combinator reducers over SKI, BCKW and
Smullyan's named birds. See `PLAN.md` for the scope and `BENCHMARKS.md` for the
current results.

## Engines

| name | what | counts asserted? |
|---|---|---|
| `aviary` | the reference, `aviary_kernel` from its repo (`$AVIARY_REPO`, default `~/Code/urbit/aviary`) | yes (it sets the pins) |
| `avon-copy` | Avon `batch --strategy=copy --no-jets` (`$AVON_BIN`, default `~/avon/build/avon`) | yes |
| `avon-share` | Avon `batch --strategy=share --no-jets` (graph reduction) | no; fuel edges checked on its own counts |
| `mini` | `bench/mini.py`, a small reducer written from the textbook S K I B C W rules | yes |

Not every engine runs every row, and `bench.check` prints how many rows each
engine skipped:
- Avon reads only S, K and I (it refuses bird-named atoms), so it runs a row
  only when the term contains no bird or defined name.
- mini runs a row only when the term uses no bird outside S K I B C W, and
  only in `nf` mode (it has no WHNF mode).
- avon-share skips the fuel-edge rows, which are derived from copy-mode
  counts. Instead, for each row it passes, it is rerun at its own count c
  (must report FUEL) and at c + 1 (must reproduce its status, count and normal
  form). These reruns appear as extra `.share-edge` checks, so the "checks"
  column in BENCHMARKS.md counts checks, not rows.

## Requirements

- Python 3.10+ (tested on 3.12).
- An aviary checkout with BCKW support (aviary 0.2.0); the older 0.1.0 in
  site-packages lacks it. `$AVIARY_REPO` is put first on `sys.path`, so it
  shadows any installed copy.
- A release build of Avon (`make` in `~/avon`). Results record its version
  line, mtime and hash, because the repo revision alone does not show whether
  the binary was rebuilt.

## Usage

    python3 -m bench.gen       # build manifests/*.jsonl, pinning aviary's counts
    python3 -m bench.check     # run every engine, write results/, exit 1 on any failure
    python3 -m bench.report    # rewrite BENCHMARKS.md
    python3 -m bench.selftest  # plant bugs in mini; every one must be caught

If aviary disagrees with any row's expected status or normal form, `bench.gen`
prints the disagreements, writes nothing for that family, and exits 1.
`bench.check` overwrites `results/`. Both `manifests/` and `results/` are
tracked in git; commit them together with the code that produced them.

## Conventions

- Strategy: normal order (leftmost-outermost) to full normal form, or to weak
  head normal form for `mode: whnf` rows. One step is one contraction.
- **Fuel:** status is FUEL whenever steps >= fuel, checked before looking for
  the next redex. So a term needing c contractions reports NORMAL only when
  fuel >= c + 1; at fuel = c it reports FUEL with the normal form in hand.
  This is aviary's and Avon's behaviour (Avon: `docs/RUNTIME.md`, fuel), and
  `mini.reduce` implements it too.
- Normal forms are compared in a canonical printed form (application to the
  left, parentheses around an argument that is an application). Only ASCII
  space separates tokens; output that does not parse never matches.
  `bench.gen` rejects manifest terms containing other whitespace or
  non-printable characters.
- An Avon line that cannot be parsed, or a term Avon rejects, gives that row
  status ERROR (a failure), not a crash of the whole batch.

## Manifest rows

`id, family, basis, term, source, fuel, mode, expect{status, nf}, expect_src,
note, pin{steps, source}, size`. `expect_src` says where the expectation comes
from: `hand` (worked from the rules), `aviary-rule` (aviary's bird table),
or `fuel-edge` (derived from a pinned count; ids end in `.fuel-1`, `.fuel+0`,
`.fuel+1`). Rows whose expected `nf` is null check status and count only.
