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

    python3 -m bench.gen       # build manifests/*.jsonl and pin each row's count
    python3 -m bench.check     # run every engine, write results/, exit 1 on any failure
    python3 -m bench.report    # rewrite BENCHMARKS.md
    python3 -m bench.selftest  # plant bugs in mini; every one must be caught
    python3 -m bench.timing C  # CPU time and peak RSS on the larger rows

If aviary disagrees with any row's expected status or normal form, `bench.gen`
prints the disagreements, writes nothing for that family, and exits 1.
`bench.check` overwrites `results/`. Both `manifests/` and `results/` are
tracked in git; commit them together with the code that produced them.

## Where pins come from

Families A and B are pinned by aviary. Rows with `pin_policy: "given"` (D0)
carry a pin from an outside source, which `given_pin` keeps only if every
engine that can run the row in time (Avon copy, mini, aviary within its
timeout) reproduces it and the expectation exactly. Family C and D0's
constructor rows (`pin_policy: "auto"`) are pinned row by row (`bench/gen.py`,
`auto_pin`):

1. **aviary**, if it finishes within `BENCH_AVIARY_TIMEOUT` seconds (default
   10). aviary rewrites the whole tree at every step, so its reach depends on
   the term's size as well as its count: in the current manifest it pins rows
   of up to 21,542 contractions, but times out on some of under 5,000. All four
   engines then run the row.
2. Otherwise **Avon copy mode** (fuel 10^9, 120 s). If the count is at most
   2x10^7, **mini** must reproduce it exactly; the pin source then reads
   `avon-copy@<rev>, confirmed by mini`. Above that the pin is Avon's alone and
   says so.
3. Otherwise the row is **share-only**: no count is pinned, and the check is
   the arithmetic answer alone (`pin: null`, `engines: ["avon-share"]`).

**Pins depend on the machine.** Which step pins a row, and so the row's
`pin.source` and `engines`, depends on whether aviary beats the timeout on the
machine that ran `bench.gen`; so does whether a BCKW row is kept at all. The
pinned *counts* do not depend on it: every source is held to the same count.
A row's `pin.source` says which engine pinned it, and a `+dirty` suffix marks
an aviary checkout with uncommitted changes (currently only its demo notebook).

**Fuel.** Pinned rows run at fuel 2 × pin + 1000. Share-only rows run at fuel
4×10^9 with a 300 s timeout. A share-only row's note says why copy mode was not
pinned: it ran out of fuel at 10^9 (`FUEL`), timed out at 120 s (`TIMEOUT`), or
the family excluded it (`copy: false`, with the measured reason).

**Tiers of share-only rows** come from Avon's share-mode count, so such a row
can be tier M although copy mode needs more than 10^9 contractions
(`c.collatz.9`). BENCHMARKS.md marks these rows.

For family C the expected normal form comes from arithmetic, and for D0 the
expected status and constructor come from the corpus; never from an engine; `gen` rejects the family if any engine that pins a row disagrees with
it. BCKW rows are kept only where aviary pins them, since Avon cannot run
them. Each row records `tier` (XS < 10^2 <= S < 10^4 <= M < 10^6 <= L < 10^8
<= XL, by its pinned count, or by Avon's share count for share-only rows) and
`share_ref`, Avon's share-mode count when the manifest was built (recorded,
not asserted). Fuel-edge rows are added only for pins up to 10^5.

## Family D0: Avon's conformance corpus

`data/d0/` vendors Avon's `tests/conformance` corpus (MIT; see `data/d0/SOURCE`):
45 closed SKIjack level-1 executables (self-interpreter towers, the T3 table,
parsers, scry programs) as SKIT files (`bench/skit.py` decodes them; it is
written from the format description, not from Avon's or skijack's code). Each
target gives two rows (one if the target ends in FUEL, which has no constructor):

- `d0.<id>`: reduce to weak head normal form under the corpus's cap; the
  status and copy count come from the corpus (`pin_policy: "given"`, made by
  skijack on aviary), and `bench.gen` keeps a row only if every engine that
  can run it in time (Avon copy, mini, aviary within its timeout) reproduces
  that count exactly.
- `d0.<id>.ctor`: the target applied to one marker atom per result
  constructor (`r_Nothing r_Just`, ...). Its weak head normal form must have the
  expected constructor's marker as its head (`expect.head`). This checks the
  answer, not only the cost. Pinned by the auto policy.

The decoded payload (the corpus's last column) is not checked yet.

## Family D1: SKIjack programs and the quine

`data/d1/terms.json` vendors closed SKI terms compiled by skijack 0.2.6 from
four corpus programs of SKIjack's EXAMPLES.md (`python3 -m bench.vendor_d1`
regenerates it; checking never needs skijack). Results are Scott numerals or
booleans:

- A numeral result is read back inside the same reduction by
  `R = Y SREAD`, `SREAD r n = n x (B f r)`, which turns a Scott numeral into
  the Church readback `f (f (... x))`; the row then checks `expect.numeral`.
- A boolean is applied to the atoms `yes` and `no`, as SKIjack's tests do.
- Expected values are SKIjack's own (`expect_src: "examples"`) or arithmetic on
  numerals built here (`"arith"`).

`d1.quine` is the quine `t = h <h>` of the ski-in-ski appendix, rebuilt from its
construction in `bench/families/quine.py` (69,268 leaves, as the appendix
says). Its normal form must equal the normal form of its code `<t>`, which
the module computes structurally, without reduction (953,226 leaves;
`expect.nf_ref: "d1.quine"`, `expect_src: "construction"`). The appendix's
2,855,152 contractions count a probing readback, not this reduction.

## Timing

    python3 -m bench.timing C --runs 3     # tiers M, L, XL

Times `avon reduce` (parse, reduce and print: the whole process) and mini
(in-process, rows up to 5x10^6 contractions). CPU time is the only time metric:
user + system seconds from `getrusage`, which for Avon covers the avon process
and the small `/usr/bin/time` wrapper that reports its peak RSS. Process start
and parsing dominate small rows, so contractions per second are reported only
for rows of at least 10^6 contractions. Runs are interleaved across engines. A run whose answer
is wrong is reported and not timed. Results go to `results/timing-<fam>.jsonl`.

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
- **Every Avon run is watched.** It is killed at `BENCH_AVON_MAX_RSS_MB`
  (default 3000) of resident memory, summed over its process tree, giving
  status MEMORY, or at its timeout, giving status TIMEOUT. `--budget` bounds
  only what Avon prints; a diverging share-mode run can otherwise grow by
  ~500 MB/s. A batch the watchdog stops fails all its rows and is not rerun.
  Jobs with fuel of at least 10^8 run in their own process.
- **Manifests are validated** before anything runs: required fields, a known
  `mode` and `expect.status`, known engine names, an expected normal form on
  every NORMAL row, `pin: null` only on share-only rows, a natural `numeral`.
  A row that fails validation, or that no engine runs when all engines are
  selected, is a failure, not a skip.
  WHNF rows may legitimately carry no expected term (status and count only,
  as for D0's targets); their constructor rows carry an `expect.head`.
- avon-share's count is held to `share_ref` where a row records one. This is a
  regression pin on Avon's own share-mode count, not a correctness claim.

## Manifest rows

| field | meaning |
|---|---|
| `id` | unique; fuel-edge rows end in `.fuel-1`, `.fuel+0`, `.fuel+1` |
| `family`, `basis` | family letter; `ski`, `sk`, `bckw` or `native` |
| `term`, `source` | the term run, and the source it was expanded from |
| `fuel`, `mode` | fuel; `nf` (full normal form) or `whnf` |
| `expect.status` | `NORMAL`, `WHNF` or `FUEL` |
| `expect.nf` | expected normal form, or null (check status and count only) |
| `expect.numeral` | family C: expected Church readback `f (f (... x))` with this many `f` |
| `expect.nf_ref` | expected normal form too large to store, computed by its family (`d1.quine`) |
| `expect.head` | expected head atom of the result (D0 constructor rows: the marker `r_<ctor>`) |
| `expect_src` | `hand` (worked from the rules), `aviary-rule` (aviary's bird table), `arith` (arithmetic), `corpus` (an outside corpus's recorded outcome), `examples` (SKIjack's stated results), `construction` (derived from how the term was built), `fuel-edge` (derived from a pin) |
| `pin` | `{steps, source}`, or null for a share-only row |
| `engines` | engines that run the row (absent: all that can read it) |
| `tier`, `size`, `share_ref` | tier; term size in leaves; Avon share count when built (recorded, not asserted) |
| `pin_policy` | absent: aviary pins the row; `auto`: `auto_pin` (see below); `given`: the pin comes with the row from an outside source and must be reproduced (`given_pin`) |
| `require_aviary`, `copy` | `auto_pin` inputs: drop the row unless aviary pins it; `false` = never run copy mode |
| `note` | free text, including why a row is share-only |

## Related work

- thma, *lambda-ski: Implementing a small functional language with a
  combinator based graph-reduction machine*, GitHub repository (Apache-2.0),
  <https://github.com/thma/lambda-ski>, accessed 2026-11-25. A Haskell
  compiler from a small λ-language to combinators (SKI plus B, C, Y and
  arithmetic primitives) with graph reduction. Its `benchmark/` directory
  times factorial, fibonacci, ackermann and tak under several abstraction
  and reduction variants (Criterion wall-clock times; no contraction counts).
  Our Church-numeral family C covers the first three in pure SKI, without
  primitives; tak is planned.
- *SKI Calculus*, BusyBeaverWiki, <https://wiki.bbchallenge.org/wiki/SKI_Calculus>
  (oldid 10480, CC BY 4.0), accessed 2026-11-25. Busy-beaver champions for SKI,
  SK and BCKW terms: the largest normal form (in leaves) of a terminating term of
  each size. Planned as family G.
