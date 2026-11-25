# combinator-benchmarks: scope (draft, 2026-11-24)

The goal is a benchmark suite over SKI, BCKW and Smullyan's named birds that measures
**correctness** (does an engine reach the right normal form, with the right contraction
count where one is defined?) and **speed** (wall time, peak RSS, contractions per second).

Status: families A and B on master (pushed 2026-11-25). Family C built on branch `family-c`
(84 base rows, 280 with fuel edges; all pass; timed). Families D–G not started.

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
- **Tak** (Takeuchi's function), as in thma/lambda-ski's `benchmark/` set (factorial,
  fibonacci, ackermann, tak): not yet built. It needs Church comparison (`LEQ`) and Y;
  a standard Gabriel benchmark that stresses deep non-tail recursion.

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

### G. Busy-beaver champions (public; bbchallenge wiki)
From the BusyBeaverWiki page *SKI Calculus* (CC BY 4.0, oldid 10480). Ξ₀(n) is the largest
normal form, **measured in leaves**, of a terminating SKI term of size n (any reduction order).
Checked 2026-11-25 on Avon copy and share: every champion below gives exactly the wiki's value.
- **SKI table, n = 5–11:** values 6, 17, 41, 80, 1561, 1562, 1563, at most 789 copy-mode
  contractions. Also SK-variant champions (n = 6: 10; n = 9: 169; n = 10–13: 1561–7811).
- **BCKW table, n = 4–5:** `WW(WB)` → 11 and `W(WW)(WB)` → 47 (aviary and mini only).
- **Larger n:** values from 2^2^513 up to beyond Graham's number. Not runnable; at most a
  fuel-capped smoke test, never an expected-value row.
- Value: an expected answer from an outside source, not from our engines. Cheap in steps,
  so mostly a correctness family.
Not yet built.

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
- 2026-11-25: thma/lambda-ski cited in README (Related work); tak added to family C's to-do list. Family E's specifics redacted before the first public push, since they are unpublished.
- 2026-11-25: Read OpenReview BfCwzmyaMO (CombStruct4Lean, withdrawn): 282 Lean 4 combinatorics problems (graphs, colourings, tournaments); no combinatory logic, so not cited. Reference downloads live in refs/, gitignored (public repo).

- 2026-11-25: bbchallenge wiki SKI busy-beaver champions verified on Avon (NF leaf count matches for n = 5-11 and SK n = 6, 9); planned as family G.
- 2026-11-25: Family C built (branch family-c): Church add/mul/exp/tower/pred/sub/fact (pairs, Y)/fib/Ackermann/Collatz, SKI plus BCKW where aviary pins in time. Pins: aviary when it finishes in 10 s, else avon-copy confirmed by mini (<= 2e7), else share-only. Found and fixed a 35 GB runaway (print budget 1e9 on fuel-edge FUEL terms, in Avon and in mini). Ack(3,11) share-only (copy peaks 3.87 GB). Timing: Avon copy runs 150-270 Mcontr/s, share 50-65 Mcontr/s; share wins by up to 60,000x in contractions on Collatz, but loses wall time on Ackermann(3,10) (2.1 s vs 1.0 s).
- 2026-11-25 (correction to the family C line above, after Angel review): family C has 85 base rows (54 SKI, 31 BCKW), 280 with fuel edges. On rows of at least 10^7 contractions Avon copy runs 120-271 Mcontr/s and share 50-60.
- 2026-11-25: Angel and Gnome reviews of family-c. Fixed: docs (aviary reach, machine-dependent pins, fuel policy, row schema, rates only from 10^6 contractions); manifest validation (NORMAL rows need an expected nf, engine names, pin null only on share-only rows); rows run by no engine fail; share counts held to share_ref (regression); Avon watchdog (3 GB summed over the process tree, timeout) in check and timing; timed-out batches fail closed instead of being rerun singly; mini timing includes parse and bounded print. selftest covers the corrupted-row cases.
- 2026-11-25: The timing rerun in a025637 is unreliable on two counts: valo's formal check overlapped it (machine load ~18-20), and Avon CPU included the watchdog's `ps` processes (RUSAGE_CHILDREN). Fixed the second: Avon CPU now comes from wait4 on the avon child. Timing records the load average. Rerun pending a quiet machine.
- 2026-11-25: Family D0 built (branch family-d0): Avon's conformance corpus vendored (45 targets, 340 rows with constructor rows and fuel edges). Every corpus count reproduced by Avon copy and mini (and aviary where fast). Avon share counts for the towers (323 / 63,520 / 314,309) equal vine-aviary's by-need counts reported by deli: independent agreement. New: SKIT decoder, mini WHNF mode, expect.head, given-pin policy.
- 2026-11-25: Angel review of family-d0: docs fixed (schema adds expect.head, expect_src corpus, pin_policy given; given pins in 'Where pins come from'; FUEL targets give one row; SOURCE lists the corpus files not vendored; gen docstring covers WHNF edges). Side effect recorded: mini's WHNF mode adds mini to family A's two whnf rows (307 -> 309 mini checks).
- 2026-11-25: Gnome review of family-d0: no false pass found (mini WHNF = aviary on 1,500 fuzzed terms; given_pin rejected every corruption). Fixed: strict SKIT decoder (exact length, zero reserved bytes and padding), head_of tolerates a parenthesised head. D0 merged and pushed.

- 2026-11-25: Family D1 built (branch family-d1): 19 SKIjack EXAMPLES level-0 rows (Scott numerals read back to Church in-term; booleans by yes/no) and the ski-in-ski quine. Rebuilt quine has 69,268 leaves as the appendix states; its NF equals the structurally computed normal form of <t> (953,226 leaves) on Avon copy, share and mini. 77 rows with fuel edges. Not done: drift check of D0's towers against current skijack.
- 2026-11-25: Angel review of family-d1: values, readback and quine reconstruction confirmed (tuple-identical to notes/checks/quine.py; abstraction step and NF argument sound). Fixed: the premise t ->> <t> stated as the appendix's, arith/examples split and +dirty pins in README, nf_ref documented, selftest covers the D1 readback. D1 merged and pushed.
- 2026-11-25: Family D2 in progress (branch family-d2): SKIlark's ten pinned test modules vendored (472 programs, 944 runs; SKIlark 0.9.0 @ 6d10046) through a hash-consed shared-subterm store (800 MB text -> 0.7 MB gzipped). Found on the way: SKIlark's test_pure compiled programs need ~2.7 GB each to compile; mini's cost was in printing unfolded WHNF results, now bounded per row (64 nodes when only status/head is checked); mini head reduction rewritten stack-based (checked equal to the old loop on 20,000 random terms). The memory cap script now watches the whole process tree.
- 2026-11-25: First D2 build killed by the 3 GB cap at row ~1,310 of 1,888 (no disagreements before it): gen kept every row's expanded term (~1 MB each) and an unbounded expansion cache. Fixed: rows are held packed and expanded only while run (gen, check in chunks of 64, timing one at a time), the cache is dropped past 200 MB, and gen checkpoints each pinned row to manifests/.<F>.partial.jsonl so a killed run resumes. Added family D5 (own Joy programs: Ackermann, Collatz, tak; self-checking, outcomes from joyref), not yet vendored.
- 2026-11-25: D2 built: 1,888 rows (944 runs x base and .ctor) plus fuel edges, 6,484 in all; no disagreements; peak 2.25 GB. Two more kills on the way, both fixed: mini on multi-million-step rows grew the generator by ~2 GB (now in a child process above 100,000 characters), and aviary on a 5.2M-leaf compiled term (now not run above 1,500,000 leaves; it ran fine up to 1.13M). Angel review: D5 kept out of gen's default list until vendored; timing honours whnf mode and print budgets; checkpoint written one group per line and tolerant of a cut-off line; limits and "confirmed by" documented.
- 2026-11-25: Gnome review of family-d2 (probes on tiny rows; resume, termstore round trip, chunked expansion and the mini child confirmed as documented). Fixed: a torn checkpoint line swallowed the next group appended (the file is now rewritten to whole lines on resume); checkpoint groups keyed by a hash of the row's definition, so an edited row is re-run; a row with no term crashed check; in-process mini errors now give CRASHED like the child's. Both checkpoint cases are in the selftest.
- 2026-11-25: First full D2 check killed by the cap (3.47 GB) after ~2.5 h, no results written: check expanded 64 rows at a time whatever their size (D2 terms reach ~60 MB), and aviary ran in-process and printed whole result terms. Fixed: chunks bounded at 32 MB of text as well as 64 rows; aviary, like mini, runs terms over 100,000 characters in a child process; aviary output bounded by the row's print budget (aviary_show, equal to aviary's printer and to mini's cut-off on 2,000 random terms). Smoke check on 46 D2 rows, including the six largest: all pass, peak 1.8 GB.
- 2026-11-25: D2 full check clean (6,484 rows; aviary 1,072, avon-copy 6,484, avon-share 3,776, mini 6,484 pass; peak 2.49 GB). A, B, C, D0, D1 re-checked on the changed engines: all pass. Report regenerated.
- 2026-11-25: Family D5 built: own Joy programs rewritten without self-reference (SKIlark inlines definitions; first compile hit RecursionError): Collatz by while, Ackermann and tak by genrec; collatz5 added. 26 runs, 52 rows; all 13 programs give their value on joyref. Check clean: avon-copy 36, avon-share 104, mini 24 pass, aviary none (interpreted skipped; no compiled run finished within 10 s). Copy mode blows up on Collatz (collatz6.c 31.8M vs 110k shared); 16 rows are share-only.
- 2026-11-25: Angel review of family-d5: no mismatch in pins, engines, share-only rows or the .ctor head check; Joy definitions verified on extra inputs. Fixed wording: aviary (interpreted skipped, compiled tried), copy limit hit (fuel, per row notes), collatz5 listed, D5 gated on data/d5, d2_skilark docstring.
- 2026-11-26: Family D4 built: Avon's five Reduceron ports (ordlist, queens2, taut, clausify, permsort), full and small, inlined and not: 20 rows. Full rows share-only (~1e9 contractions; permsort.full.noinl 4,000,853,681, past the default share fuel, hence the new per-row share_fuel, 1e10 here). Small rows pinned by avon-copy, mini confirming all but clausify (4.5e8). Check clean: avon-copy 10, avon-share 40, mini 8; aviary none. Selftest passes.
- 2026-11-26: Angel review of family-d4: sanctioned; small variants verified as true checks, pins, share-only rows and share_fuel consistent with check and timing. Fixed: share-only reason in full rows' notes (manifest notes updated in place, nothing else changed), share_fuel noted in _row_key docstring, duplicated copy field doc removed.
- 2026-11-26: Family G built: 15 BusyBeaverWiki champions (SKI n=5-11, SK n=6,9-13, BCKW n=4,5), expectation = leaf count of the normal form (new expect.leaves, accepted by check's validation; selftest covers it). 60 rows with fuel edges; check clean on all four engines. Champions came from the subagent report of oldid 10480 (the wiki refuses scripted fetches), each confirmed on every engine.
- 2026-11-26: Angel review of family-g: leaf check not foolable by truncation, None or status; spaced() faithful. Fixed: provenance stated (transcribed from a fetched report, not the page text), normal-order wording, BCKW engines restricted at run time, leaves on .fuel+0 rows documented, size-not-structure stated, wrong 'n<=4 already normal' claim removed (S S S S is a redex); check now requires leaves to be a positive int and mode nf.
