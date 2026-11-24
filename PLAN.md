# combinator-benchmarks: scope (draft, 2026-11-24)

The goal is a benchmark suite over SKI, BCKW and Smullyan's named birds that measures
**correctness** (does an engine reach the right normal form, with the right contraction
count where one is defined?) and **speed** (wall time, peak RSS, contractions per second).

Status: families A and B built and passing on aviary, Avon (copy, share) and mini
(branch `families-ab`). Families C–F not started.

## Engines

| engine | where | bases | strategy | role |
|---|---|---|---|---|
| aviary (`aviary_kernel`) | `~/Code/urbit/aviary` | 50 birds, user rules, SKI/SK/BCKW abstraction | normal order, tree rewriting, no sharing | **reference** for counts; slow (each step costs O(term size)) |
| Avon | `~/avon/build/avon` (release) | S, K, I only | `--strategy=copy` (matches aviary's counts exactly), `--strategy=share` (graph reduction) | speed target; copy mode doubles as a second oracle |
| vine-aviary | `~/Code/vine-aviary` | SKI + 49 birds | interaction nets (strict IVM), lazy, by-need | optional third engine; strict IVM diverges on some terms that have a normal form |

Consequences:
- Bird and BCKW benchmarks run natively on aviary and vine-aviary. For Avon they are first
  expanded to SKI with `aviary_kernel.abstraction.expand(term, env, 'ski')`.
- Contraction counts are asserted for aviary, Avon in copy mode, and mini (the
  independent reducer added after the Poet pass). Share-mode counts
  and wall times are recorded but never asserted.
- Above about 10^6 contractions aviary is too slow to run as the reference. For those rows,
  the pinned count comes from Avon in copy mode, which is held to aviary's counts on every
  smaller row.

## Run with `--no-jets`

Every Avon run in the suite uses `--no-jets`. A separate, labelled jet track can come later,
but numbers from it are not counted as pure-SKI results.

## Size tiers (copy-mode contractions)

| tier | contractions | engines | use |
|---|---|---|---|
| XS | < 10^2 | all | semantics and laziness checks, run in batch |
| S | 10^2–10^4 | all | conformance across engines |
| M | 10^4–10^6 | aviary, Avon, vine | reference-checked speed |
| L | 10^6–10^8 | Avon (copy and share) | speed |
| XL | > 10^8 | Avon share | stress, memory, sharing |

## Families

### A. Semantics micro-suite (XS; correctness)
- **Identities:** `S K K x → x`, `S K S x → x`, `B`, `C` and `W` expansions applied to fresh atoms.
- **Laziness traps:**
  - `K x Ω` must reach x, though a strict engine never stops. This is a known failure for vine's IVM.
  - `S K Ω x` must reach x.
  - `K I Ω` must reach I.
- **Divergence:** Ω = `S I I (S I I)` and `Y` with no argument must end with status FUEL at a set fuel.
- **Booleans and pairs:** Church and Scott encodings, with the expected normal forms pinned.
  *Built:* Church only; Scott encodings not yet built.

### B. The aviary: every bird, every basis (XS–S; correctness)
- For each of aviary's 50 birds, apply it to enough fresh atoms to fire it. Reduce it:
  1. natively in aviary;
  2. as its SKI expansion;
  3. as its SK expansion;
  4. as its BCKW expansion.
- All four must agree on the normal form.
- Built: 49 birds plus 6 sage constructions, each in 4 forms (220 base rows, Y
  among the sages). vine-aviary rows are not yet built. It is the "basis translation is
  correct" test.
- Record the term size and count under each basis. This feeds an expansion-cost table: BCKW
  is usually smaller.
- **Smullyan puzzles as benchmarks:**
  - Fixed-point combinators: Y, Θ = U U, Curry's, Turing's, and `L L`-style sages. Run them
    applied to `K` and to a fuel-bounded body.
  - Mockingbird and lark constructions.
  - Check `x (Y x) =β Y x` to a set depth, not by running to a normal form.
    *Not yet built:* sages are checked only by `X (K x) -> x`; Curry's and
    Turing's fixed points are not yet separate cases.

### C. Church-numeral arithmetic, parametric (S–XL; speed with known answers)
These are generated from λ-terms by bracket abstraction into SKI, SK and BCKW. Each one is
a family indexed by n, so we can plot how the cost scales.
- `add`, `mul`, `exp`, `pred` (Kleene's pred is quadratic, a good stressor), and `sub`.
- **Tower of twos:** `2 2 2 …` by Church exponentiation, up to `2^2^2^2 = 65536`. This
  exercises sharing: copy mode and share mode should diverge sharply.
- **Factorial, Fibonacci:** both via Y and via iteration on Church numerals.
- **Ackermann:**
  - `ack = λm. m (λf n. n f (f 1)) succ`, a tiny pure term (no Y).
  - Its cost explodes: A(2,n) and A(3,n) for n = 1…6 span the S tier to the XL tier.
  - Readback: apply the result numeral to two fresh atoms and count the f's.
- **Collatz:**
  - Count the steps to reach 1 for n = 1…30, and n = 27 (111 steps).
  - Use Church pairs for parity, with Y or bounded iteration.
  - A Scott or binary encoding is a second variant; it is cheaper per step and tests
    a different shape.
- **Divergence check:** `ack 4 2` with a fuel cap, which must end as FUEL.

### D. Compiled programs from the corpus (S–XL; correctness with pinned answers)
- **SKIjack:**
  - The self-interpreter `whnfF` (618 atoms). Its towers have copy counts T0 = 340,
    T1 = 91,556 and T2 = 504,930.
  - T3, which stops at host fuel 400k by design.
  - The appendix quine: 69,268 atoms, 2,855,152 contractions.
  - EXAMPLES §1 `dec`, `add`, `sub`.
- **SKIlark:**
  - The 363 pinned programs, whose counts are already held equal on aviary and Avon (a
    ready-made conformance corpus).
  - Pick about 10 of them for speed, in both the interpreted and the compiled form:
    `5 sumto`, `{1 2 3} [2 <] filter`, qsort, gcd, fact, fib.
  - New programs to add: Collatz (`linrec` with `rem`) and Ackermann (`binrec`). These
    are Joy programs that compile to pure SKI.
- **skinock** (Hoon programs compiled through Nock into SKI; Scott nouns):

  | program | inputs | copy-mode contractions |
  |---|---|---|
  | dec | 5, 20, 100 | 14k to 279k |
  | add | | 29k, 605k |
  | factorial | 3, 5 | 155k, 7.86M |
  | fibonacci | 5, 8 | 203k, 1.52M |
  | ackermann | (1,2), (2,2) | 33k, 192k |
  | bigslot | | 14.0M |

  These are large terms: their DAGs have 6k to 23k nodes, and their printed form runs from
  12 to 158 MB. That makes them parser and memory benchmarks too.
- **Reduceron classics:** OrdList, Queens2, Clausify, Taut and PermSort, from Avon's
  `tests/workloads/reduceron/`. They need SKIjack to compile.

### E. Pure S (S–L; exotic behaviour)
Pure-S terms with known exotic behaviour, drawn from unpublished research notes.
The specific terms and their expected results will be added here after those
results are published.

### F. Shape stressors (synthetic, parametric)
- Deep left spines: `S (S (S … ))` and `I^n x`.
- Wide duplication: `S I I` chains, with `W` repeated.
- Deep right nesting, for recursion limits in parsers and printers.
- Sharing-sensitive terms, where copy mode is exponential and share mode linear.
- Normal forms too large to print, using `--budget`, NF hashes and `--dag`.

## Ground truth and manifest

Each benchmark is a row in a manifest (TSV or JSON):
- `id`, `family`, `tier`, `basis` (ski, sk, bckw or birds);
- `source`: a generator plus its parameters, or a file;
- `fuel`;
- expected `status` (NORMAL, WHNF or FUEL);
- the expected decoded value and/or the normal form's hash;
- the pinned `copy_steps`, and where that pin came from (aviary or avon-copy);
- notes.

Large terms are **generated deterministically by scripts** and not committed. Only
hashes and small terms go in git.

Every claim of an expected value cites its source: a proved theorem, a pinned upstream
test, or a cross-engine agreement. Agreement alone is marked as such.

## Harness (as built: `bench/gen.py`, `check.py`, `report.py`, `selftest.py`, `engines.py`, `mini.py`, `families/`; timing not yet built)
- `bench/run.py`:
  - Drives aviary in-process, Avon (copy and share) through `batch` or `reduce`, and
    vine-aviary optionally.
  - Timing: best of N, user CPU via `getrusage`, as Avon's `reduceron/run.py` does. Peak
    RSS via `/usr/bin/time -l`.
  - Output: a results JSONL file, with the machine, commit and engine version stamped on
    every row.
- `bench/gen/`: Church and λ generators (on aviary's abstraction), the bird×basis
  expander, pure-S builders, and wrappers around SKIjack, SKIlark and skinock.
- Machine rule: one heavy job at a time, under 4 GB, announced on hcom. The L and XL tiers
  count as heavy jobs.

## Open decisions (for Neal)
1. ~~vine-aviary: full engine or optional?~~ Decided 2026-11-25: optional for now (it is
   still changing). Keep its input formats in mind so it can join later.
2. ~~Canonical abstraction?~~ Decided 2026-11-25: aviary's `bracket_abstract`/`expand` is
   canonical. SKIlark's linear abstraction may be used only where it produces identical terms.
3. ~~Publish results?~~ Decided 2026-11-25: no report page. Results go in JSONL plus a
   `BENCHMARKS.md` summary in the repo.

## Poet pass (2026-11-25)
The Poet's main point: matching final answers mostly shows the engines agree with
each other, since Avon copy mode was built to match aviary and family B checks
aviary against its own bird table. Taken up so far:
- **Independent oracle:** `bench/mini.py`, a reducer written from the textbook rules.
- **Fuel-edge rows:** for each pinned count c, fuel c-1, c and c+1.
- **Hostile open terms:** redexes under free heads, partial applications.
- **Metamorphic check:** each case run in SKI, SK and BCKW must agree.
- **Mutation test of the harness:** six wrong rules planted in mini, plus a fuel
  off-by-one; all were caught.

Deferred, because they need changes in the engines or more work:
- mutation-testing Avon itself;
- trace checkpoints (a hash of the term at steps 2^k);
- checking the bird table against Smullyan's book, not aviary's table;
- count formulas for the large tiers, to replace pins taken from Avon;
- pre-shared DAG inputs for share mode;
- a space-leak family;
- per-rule contraction counts;
- rigorous timing (run distributions);
- productive and infinitary terms;
- the ratio to an optimal-reduction floor;
- differential fuzzing with shrinking.

## Next steps
1. Consult the Poet on families we are missing, then let the Hobbit cut the scope.
2. Build families A and B first: they are cheap and catch basis-translation bugs.
3. Then build C (Ackermann, Collatz), the D wrappers, and E.

## Log
- 2026-11-24: scope drafted by lope from surveys of aviary, Avon, vine-aviary, SKIjack,
  SKIlark, skinock and notes/inventory-*.
- 2026-11-25: Neal decided: vine-aviary is optional for now; aviary's abstraction is canonical.
- 2026-11-25: Neal decided: results are reported in a BENCHMARKS.md file, not a page.
- 2026-11-25: families A (309 rows) and B (880 rows) built on branch families-ab; all pass on aviary, avon-copy, avon-share, mini. Fuel convention (FUEL iff steps >= fuel) found and adopted.
- 2026-11-25: Angel and Gnome reviews of families-ab. Fixed: gen aborts without writing on a disagreement; mini implements the fuel convention itself; provenance records Avon binary version/mtime/hash and dirty trees; iterative parser, ASCII-space tokenising, per-row ERROR instead of batch crash; skipped-row counts; share-edge checks compare normal forms; bench/selftest.py (8 planted bugs + 2 corrupted expectations, all caught).
