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

Avon reads only S, K and I, so it runs a row only when the term contains no
bird names; mini runs a row only when the term uses no bird outside
S K I B C W.

## Usage

    python3 -m bench.gen       # build manifests/*.jsonl, pinning aviary's counts
    python3 -m bench.check     # run every engine, write results/, exit 1 on any failure
    python3 -m bench.report    # rewrite BENCHMARKS.md

`bench.gen` refuses to pin a row whose aviary result disagrees with the row's
expected status or normal form.

## Conventions

- Strategy: normal order (leftmost-outermost) to full normal form, or to weak
  head normal form for `mode: whnf` rows. One step is one contraction.
- **Fuel:** status is FUEL whenever steps >= fuel, checked before looking for
  the next redex. So a term needing c contractions reports NORMAL only when
  fuel >= c + 1; at fuel = c it reports FUEL with the normal form in hand.
  This is aviary's and Avon's behaviour, and mini follows it.
- Normal forms are compared in a canonical printed form (application to the
  left, parentheses around an argument that is an application).

## Manifest rows

`id, family, basis, term, source, fuel, mode, expect{status, nf}, expect_src,
note, pin{steps, source}, size`. `expect_src` says where the expectation comes
from: `hand` (worked from the rules), `aviary-rule` (aviary's bird table),
or `fuel-edge` (derived from a pinned count).
