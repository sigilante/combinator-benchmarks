# combinator-benchmarks

Correctness and speed benchmarks for combinator reducers over SKI, BCKW and
Smullyan's named birds. See `PLAN.md` for the scope and `BENCHMARKS.md` for the
current results.

## Families

| family | what it is | rows | source of the terms |
|---|---|---:|---|
| A | Semantics micro-suite: each rule on fresh atoms, laziness traps (`K x Ω`), divergence, partial application, Church booleans and pairs | 309 | written by hand |
| B | The aviary: Smullyan's birds (49, plus 6 sages) natively and as SKI, SK and BCKW expansions, which must agree | 880 | aviary's birds and bracket abstraction |
| C | Church-numeral arithmetic, parametric in n: add, mul, exp, towers of twos, pred, sub, factorial, Fibonacci, Ackermann, Collatz | 280 | λ-terms by aviary's bracket abstraction |
| D | Compiled programs, one sub-family per corpus: | | |
| [D0](#family-d0-avons-conformance-corpus) | Avon's conformance corpus: SKIjack executables (self-interpreter towers, parsers, scry programs) | 340 | Avon's SKIT files |
| [D1](#family-d1-skijack-programs-and-the-quine) | SKIjack programs and the quine | 77 | SKIjack |
| [D2](#family-d2-skilarks-pinned-joy-programs) | SKIlark's pinned Joy programs, results read back | 9,522 | SKIlark (Joy to SKI) |
| [D3](#family-d3-hoon-programs-through-nock-skinock) | Hoon programs through Nock | 24 | SKInock (urbit/benchmark) |
| [D4](#family-d4-the-reduceron-benchmarks) | The Reduceron benchmarks (OrdList, Queens2, Taut, Clausify, PermSort) | 20 | Avon's SKIjack ports of Naylor and Runciman's suite |
| [D5](#family-d5-joy-programs-of-our-own) | Joy programs of our own (Collatz, Ackermann, tak) | 78 | SKIlark |
| E | Pure S: terms with exotic behaviour (cold engines, busy beavers) | planned | [paper-combinators](https://github.com/sigilante/paper-combinators) |
| [F](#family-f-shape-stressors) | Shape stressors: deep, long, wide and exponential terms | 90 | built by the suite |
| [G](#family-g-busy-beaver-champions) | Busy-beaver champions | 60 | BusyBeaverWiki *SKI Calculus* |

Rows include fuel-edge variants. Each family's terms and expected results are in
`manifests/<family>.jsonl`; large terms live under `data/` (see the family's section).

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
  of at most 20,000,000 leaves.
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
While it runs, `bench.gen` appends each pinned row to
`manifests/.<family>.partial.jsonl` (untracked), one line per row with its
fuel edges; a rerun takes rows from there instead of running them again, so a
killed build resumes. A line cut off by the kill is dropped, and a row whose
definition (term, expectation, fuel, mode, policy) has changed is run again.
The file is removed once the manifest is written. It does not notice a
changed engine: delete it to rebuild from scratch after updating Avon or
aviary.
`bench.check` overwrites `results/`. Both `manifests/` and `results/` are
tracked in git; commit them together with the code that produced them.

## Where pins come from

Families A and B are pinned by aviary. Rows with `pin_policy: "given"` (D0, F)
carry a pin from an outside source (D0's corpus; for F, a closed form in the
term's size), which `given_pin` keeps only if every
engine that can run the row in time (Avon copy, mini, aviary within its
timeout) reproduces it and the expectation exactly. Its source then ends
"confirmed by" and the engines that reproduced it in this build; the count
itself remains the outside source's (for D2, SKIlark's own aviary run, which
this build does not repeat on rows marked `skip_aviary` or too large for
aviary). Family C and D0's
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
regenerates it from `$SKIJACK_REPO`, default `~/Code/ski/skijack/python`;
checking never needs skijack). Results are Scott numerals or
booleans:

- A numeral result is read back inside the same reduction by
  `R = Y SREAD`, `SREAD r n = n x (B f r)`, which turns a Scott numeral into
  the Church readback `f (f (... x))`; the row then checks `expect.numeral`.
- A boolean is applied to the atoms `yes` and `no`, as SKIjack's tests do.
- Expected values are SKIjack's own (`expect_src: "examples"`: the literals,
  ascii-digits and words-to-numbers rows, as SKIjack's EXAMPLES.md and tests
  state them) or arithmetic on numerals built here (`"arith"`: the eight
  `d1.nat.*` rows and `d1.ascii.mul.6.7`; EXAMPLES.md shows only some of these
  instances, e.g. `add 2 3`).
- Rows pinned by aviary carry `aviary@bfba908+dirty`: the checkout had an
  uncommitted notebook edit, so those pins cannot be reproduced from a commit
  alone; Avon copy and mini reproduce every one of them.

`d1.quine` (its expected normal form is not stored in the manifest; `nf_ref`
names the function in `bench/families/d1_skijack.py` that computes it) is the
quine `t = h <h>` of the ski-in-ski appendix, rebuilt from its
construction in `bench/families/quine.py` (69,268 leaves, as the appendix
says). Its normal form must equal the normal form of its code `<t>`, which
the module computes structurally, without reduction (953,226 leaves;
`expect.nf_ref: "d1.quine"`, `expect_src: "construction"`). The appendix's
2,855,152 contractions count a probing readback, not this reduction.

## Family D2: SKIlark's pinned Joy programs

`data/d2/` vendors every pinned run of ten SKIlark test modules (`words`,
`modes`, `combinators`, `text`, `types`, `sets`, `library`, `pure`, `numtext`,
`symbols`): 472 Joy programs, each interpreted and compiled, 944 runs. Not
vendored: `test_io` (its I/O words need a host) and `test_variants` (its own
loop variants). `python3 -m bench.vendor_d2` rebuilds the data from
`$SKILARK_REPO` and `$SKIJACK_REPO`, compiling each module in its own process
exactly as that module's fixtures do (interpreted as one set; compiled one
program at a time, except `words` and `modes`, which compile as one set); the
pins depend on this.

Every interpreted run carries the same ~77k-leaf interpreter, so the terms are
stored through `bench/termstore.py`: subterms of at least 1,000 leaves shared
in the hash-consed graph of all runs are kept once (`store.json.gz`) and
referenced as `@<hash>`; manifest rows name their run by key (`term_from`)
instead of embedding it. Plain text would be ~800 MB; the gzipped data is
~0.7 MB. Engines always receive the plain printed term.

Rows mirror D0: `d2.<module>.<name>.<i|c>` checks the status and SKIlark's
pinned unfuelled count (aviary, to weak head normal form, cap 5,000,000) as a
given pin; `.ctor` checks the result constructor (`RVal`, `RErr`, ...) by
marker head; `.val` checks the result itself, payload included (except
quotations and symbols, read only by kind: see below).
aviary is skipped (`skip_aviary`) on interpreted runs and on compiled runs of
over 20,000 contractions (`.val` rows too).

**Reading results back (`.val`).** `bench/joyshow.py` builds, for a run's type
table, a closed S, K, I term `show` that turns a Scott-encoded result into a
first-order term over free atoms: `v_val` of the stack as `v_push <item>
<rest>` ... `v_nil` (top first), items as `v_num` with an integer `v_pos` /
`v_neg` of a unary natural (`v_s` ... `v_z`; `Neg m` is -(m+1)), `v_bool
v_true|v_false`, `v_char`, `v_str` of `v_tcons` codes, `v_set` of `v_scons`
members; `v_err` and `v_time` for the other ends. The `.val` row reduces `show
(run)` to full normal form (mode `nf`), which must equal the pinned outcome
written that way (`expect.nf`, from SKIlark's own reading in its test tables).
The compiled form keeps only the constructors a program uses, so each run's
type table is recorded with it (`python3 -m bench.vendor_d2 --types`, read
from the SKIjack source SKIlark generates, at the vendored revisions; the
result constructors' names, order and arities are checked against the
vendored ones, the other tables are not checked against the compiled term,
but a wrong one would misread by position and fail). Vendoring rewrites
`programs.json.gz` without the tables: run `--types` after it, or `bench.gen`
refuses to build D2 and D5. Quotations and
symbols are not read: they print as the bare atoms `v_quot` and `v_sym`, so
for the 92 runs whose result holds one, the stack's shape and its other items
are checked and that item only by kind (the row's note says so). Reading the
payload forces work the weak head normal form leaves undone, so `.val` rows
are pinned afresh by the auto policy.

## Family D3: Hoon programs through Nock (SKInock)

urbit/benchmark's Hoon-compiled programs (dec, add, factorial, fibonacci,
ackermann, bigslot; MIT), compiled from Nock to SKI by SKInock (MIT) at the
scaled-down subjects of SKInock's own benchmark (`skinock.bench.SCALED`): 12
runs. `python3 -m bench.vendor_d3` builds each run's term straight from
SKInock's term graph into the shared-subterm store (`data/d3/`, about 16 KB
compressed), since printed the terms run from 12 to 162 MB (3.6M to 46M
leaves). Each row reduces `show main` to normal form: `main` is the compiled
program on its subject, and SKInock's `show` rebuilds the product noun as a
first-order term (`matom`, `mcell`, and bits as `mcons mt|mf ... mnil`, least
significant first), so the row compares the whole product. The expected normal
form is printed from the product of SKInock's Python Nock evaluator
(`expect_src: "nock-oracle"`). The evaluator and the compiler share SKInock's
`nock` module (noun types, formula checks) and take the same formula and
subject; what is independent is the evaluation, Nock's step rules against SKI
reduction of the compiled term. Rows are pinned by
the auto policy: avon-copy pins all 12 (13k to 13.3M contractions), mini
confirms the 8 within its size limit (all but factorial and fibonacci), and
aviary runs none (all are past its limit).

## Family D4: the Reduceron benchmarks

Naylor and Runciman's OrdList, Queens2, Taut, Clausify and PermSort (*The
Reduceron reconfigured and re-evaluated*, JFP 2012), as ported to skijack in
Avon's `tests/workloads/reduceron/`. `python3 -m bench.vendor_d4` copies the
sources to `data/d4/src/` and compiles them into `data/d4/terms.json`. Each
port's `main` checks its own answer and returns True, so a row reduces
`main Tt Ff` to weak head normal form and expects the atom `Ff`
(`expect_src: "self-check"`). Each program has four rows: full size and
small, each compiled with and without skijack's inlining pass
(`d4.<program>.<full|small>.<inl|noinl>`).

- **Full** is the port as Avon has it: boolean lists of 12, 11 queens, 16
  names, 80 conjuncts, 10 numbers. Each run takes about 10^9 contractions
  even with sharing (PermSort about 4 x 10^9), so these rows are share-only
  (`copy: false`, `share_fuel` 10^10).
- **Small** replaces one line (`SMALL` in `bench/vendor_d4.py`, recorded in
  each row's `source`) and keeps `main` a check whose answer is True:
  OrdList at length 6, 6 queens (4 solutions), Taut over 4 names, Clausify
  of 1 conjunct (the answer is one clause for any count, by Avon's
  `clausify_ref.py`), PermSort from 5. Small rows are pinned by the auto policy.
  Clausify stays costly: one conjunct takes ~4.5 x 10^8 contractions copying, too
  many for mini; with two, copy mode passes 10^9.

aviary is tried on the small rows and finishes none within its 10 s, so their
pins come from avon-copy, confirmed by mini for all but Clausify; it is not
run on the full rows (`skip_aviary`).

## Family D5: Joy programs of our own

Joy programs written for this suite (`data/d5/`, from
`python3 -m bench.vendor_d2 --own`; definitions and programs in
`OWN` and `OWN_DEFS` of `bench/vendor_d2.py`), compiled by SKIlark the same
way as D2's: Ackermann (`ack`, (1,1) to
(3,2)), Collatz step counts (`collatz`, from 5, 6, 7, 9 and 27) and Takeuchi's
`tak` ((3,2,1) to (12,8,4)). `bench.gen` lists D5 only when `data/d5/`
exists. SKIlark inlines definitions, so none calls
itself: Collatz loops with `while`, and Ackermann and tak recurse through
`genrec`. Each program checks its own answer:
`<expr> <value> = [] [0 0 /] branch` ends with an empty stack when the value is
right and errs (division by zero) when it is not. So the `.ctor` row, whose
head must be `r_RVal`, certifies the computed value, given that SKIlark's
`=`, `branch` and `/` behave as Joy's do (checked in joyref, not here). The
plain `.i`/`.c` rows check only status and count; their note records the
expected outcome. The `.val` rows read the result back as D2's do: it must be
`v_val v_nil`, the empty stack. The expected outcome, `RVal []`, comes from SKIlark's model of
the Joy reference (`tests/joyref.py`; `expect_src: "joyref"`); there is no
outside pin, so all three rows are pinned by the auto policy. Rows are built as
D2's (`d5.own.<name>.<i|c>`), except that aviary is tried (within its timeout)
on every compiled run, since no count says in advance which are too long.
Interpreted runs are skipped; of the compiled runs, none finished on aviary
within its 10 s in the current build, so no D5 row runs on aviary; pins come from avon-copy, confirmed by mini where mini can run.

Copy mode is the weak point here. In Collatz, `dup` copies a number not yet
computed, and each copy recomputes it, so copy-mode counts grow exponentially with
the step count (`collatz6.c`: 31.8M contractions copying, 110k sharing). The
runs of collatz 7, 9 and 27 in both forms, and tak (8,4,0) and (12,8,4)
interpreted, ran out of copy-mode fuel (10^9 contractions, as each row's note
records) and are not pinned; avon-share
alone runs them, and its count is the row's share reference. Their `.ctor` and `.val` rows still
certify the value (head `r_RVal`; the empty stack), on that one engine, and
are likewise share-only. `collatz5` is small enough
for copy mode and mini.

## Family F: shape stressors

Synthetic terms built to a shape (`bench/families/f_shapes.py`), each with a
normal form and a copy-mode count that follow from the shape by the rules
(`expect_src: "construction"`, `pin_policy: "given"`, the pin's source naming
the closed form), so every engine that can run a row must reproduce both:

| shape | term | sizes n | normal form | copy-mode count |
|---|---|---|---|---|
| `left` | `I I ... I x` | 10^3 to 10^7 | `x` | n |
| `right` | `I (I (... (I x)))` | 10^3 to 10^7 | `x` | n |
| `snorm` | `S (S (... (S K)))` | 10^3 to 10^6 | the term itself | 0 |
| `wide` | `x (I y) ... (I y)` | 10^3 to 10^6 | `x y ... y` | n |
| `dup` | `D (D (... (D x)))`, D = `S I I` | 4 to 20 | binary tree of 2^n `x`s | 3 (2^n - 1) |
| `dupki` | the same on `K I` | 4 to 28 | `I` | 7 · 2^(n-1) - 4 |
| `wi` (BCKW) | the same with D = `W I` | 4 to 16 | as `dup` | 2 (2^n - 1) |

Deep nesting tests recursion in parsers, reducers and printers; `snorm` has
nothing to reduce and only tests printing a deep normal form. `dup` and
`dupki` are sensitive to sharing: copy mode copies the unreduced argument and
reduces it twice, so its count doubles with each D, while Avon's share mode
counts 3n and 4n - 1 (recorded as `share_ref`, not asserted). `dupki.32` and
`dupki.64` (about 1.5 × 10^10 and 6.5 × 10^19 copy-mode contractions) are
share-only (`pin_policy: "auto"`, `pin: null`; their normal form `I` is by
construction and checked by Avon share mode alone). Terms and normal forms over 10,000 characters are not stored in
the manifest: the row names them (`term_ref`, `expect.nf_ref`) and the family
rebuilds them.

aviary is not run past limits measured on it (aviary bfba908): its parser
recurses once per level of nesting and exceeds Python's recursion limit
between depth 2 × 10^4 and 3 × 10^4 (and right nesting is already slow: about
13 s at 2 × 10^4); on long spines its time grows quadratically (left spine:
1.3 s at n = 3,000, 15.5 s at 10^4; `wide`: 35 s at 10^4). Beyond those
`skip_aviary` rows, aviary also drops out of any row it cannot finish within
gen's aviary timeout (e.g. `dup` from n = 16, `dupki` from 20, `wi.16`). Avon
copy runs every S, K, I row except the two share-only ones; mini runs all but
`dupki.24` and `dupki.28` (past its 2 × 10^7 confirmation limit); the `wi`
rows run on mini and aviary only. Not built: normal forms too large to print
whole (the harness compares printed normal forms; there is no hash check).

## Family G: busy-beaver champions

The champion terms of the BusyBeaverWiki page *SKI Calculus*
(<https://wiki.bbchallenge.org/wiki/SKI_Calculus>, oldid 10480, CC BY 4.0;
`CHAMPIONS` in `bench/families/g_busybeaver.py`). For each n the page gives the
largest normal form Xi_0(n) of a terminating term of n combinators and a term
that reaches it. The page does not say how it measures a normal form; the leaf
count matches every value checked here, so each row expects the champion's
normal form to have exactly the page's value in leaves (`expect.leaves`,
`expect_src: "corpus"`); the size is checked, not the structure. This is an expected value from outside the suite: no
engine of ours produced it. Rows: the S, K, I table for n = 5 to 11 (6 to 1,563
leaves), the S-and-K table where it differs, n = 6 and 9 to 13 (10 to 7,811),
and the BCKW table for n = 4 and 5 (11 and 47; run on aviary and mini only,
since Avon reads only S, K and I). For n <= 4 the value is n and the rows would be trivial; beyond the listed n the values
(2^2^513 and up) cannot be reached. All rows are cheap (at most 1,561 copy-mode
contractions), so this is a correctness family. The wiki refuses scripted
fetches, so the terms were transcribed from a report of the page, not checked
against its text; each reduces to its stated value on every engine here.

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
- **Size limits.** aviary is not run on terms of more than 1,500,000 leaves
  (`engines.AVIARY_MAX_LEAVES`; a 5.2M-leaf term passed 2.8 GB), in `gen` or
  `check`; this is separate from a family's `skip_aviary`. mini is not run on
  terms of more than 20,000,000 leaves (`engines.MINI_MAX_LEAVES`; D2's largest,
  19.5M, ran at a 2.5 GB peak). mini and aviary
  reduce terms of more than 100,000 characters in a child process
  (`engines.ISOLATE_ABOVE`), whose memory is freed when it exits; a child
  that fails gives status CRASHED, a failure. `bench.timing` leaves mini out
  on such terms, since it times mini in-process.
- **Printing is bounded per row** (`gen.print_budget`), in all three engines:
  10^7 atoms where a normal form is compared, 64 where only status, count or
  head is checked.
  Output cut off by the budget never matches a normal form.
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
| `expect.leaves` | family G: the normal form must print whole and have exactly this many leaves (mode nf; also on `.fuel+0` rows, whose FUEL result is that normal form) |
| `expect.nf_ref` | expected normal form too large to store, computed by its family (`d1.quine`; `f.<shape>.<n>`) |
| `expect.head` | expected head atom of the result (D0 constructor rows: the marker `r_<ctor>`) |
| `expect_src` | `hand` (worked from the rules), `joyref` (SKIlark's model of the Joy reference), `aviary-rule` (aviary's bird table), `arith` (arithmetic), `corpus` (an outside corpus's recorded outcome), `examples` (SKIjack's stated results), `construction` (derived from how the term was built), `self-check` (the program checks its own answer; D4), `nock-oracle` (SKInock's Python Nock evaluator, by Nock's step rules; D3), `fuel-edge` (derived from a pin) |
| `pin` | `{steps, source}`, or null for a share-only row |
| `engines` | engines that run the row (absent: all that can read it) |
| `tier`, `size`, `share_ref` | tier; term size in leaves; Avon share count when built (recorded, not asserted) |
| `store`, `term_from` | shared-subterm store the term's `@` references resolve in; vendored file, key and wrapper (`%T` = the term) the term is read from (D2, D5) |
| `term_ref` | family F: the term is not stored (`term` is empty); its family rebuilds it from this name, `f.<shape>.<n>` |
| `skip_aviary` | aviary cannot finish the row in time; it is not run there |
| `share_fuel` | the share-mode fuel `auto_pin` uses, and a share-only row's `fuel` (default 4 x 10^9) |
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
