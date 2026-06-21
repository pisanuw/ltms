# Chapter 5 Exercises: Extending Pattern-Directed Inference Systems (FTRE)

Forbus & de Kleer, *Building Problem Solvers*, Chapter 5.

**Analysis only.** FTRE (the focused, resource-bounded, environment/context based
TRE built in this chapter) is explicitly a non-goal for this package (see
`BRIEFING.md`: porting FTRE is out of scope). Therefore these are **conceptual
answers only**: algorithm sketches, derivations, complexity arguments, and
design discussion. **No code was written and nothing was executed**, so
`codeRuns = false` for this chapter.

Exercise statements below are my own paraphrases of the textbook problems (the
original wording is copyrighted). Difficulty stars from the source are noted in
brackets. Where a problem is open-ended I state my assumptions.

A short orientation on the FTRE concepts these problems lean on:

- **FTRE** is a TRE plus a notion of *logical environment / context*. Reasoning
  happens under assumptions; a *context* is the set of assumptions currently in
  force, organized as a **stack** (hence the inherent depth-first search).
- **a-rule** ("assumption rule") is a rule that introduces an assumption and
  reasons inside the resulting subcontext, then pops back out. This is how
  things like indirect proof (assume `(not P)`, look for a contradiction) are
  built.
- Rules are compiled: FTRE turns each trigger pattern into a generated **match
  procedure** and the rule body into a generated **body procedure**, which are
  installed as named Lisp functions. `build-rule` / `generate-match-body` /
  `generate-unify-tests` are the code-generation pieces.
- `*bound-vars*` tracks which pattern variables are already bound while the
  multi-trigger match code is being generated, so later triggers can reuse
  earlier bindings.
- `rlet` binds FTRE variables for use in rule bodies; `rassert!`,  `fetch`,
  `seek-in-context`, `show`, `*context*` are the runtime primitives referenced
  by several problems.

---

## Exercise 1 [*] — Are the `consp` and car-equality tests redundant?

**Paraphrase.** In the `match` code of Figure 5.2 the first two checks are
`(consp p)` and an equality test on the `car`. Given the class/type structure
already in place, are these two tests actually needed?

**Answer.** They are not strictly redundant, and the reason is *who calls match
and on what*. The dbclass index keys assertions on the predicate symbol (the
`car` of a pattern), but the index gives you only a coarse bucket of *candidate*
data items, not a guarantee about the shape of each individual item.

- The `consp` test guards against being handed an atom where a list is expected.
  Even if the class structure routes by predicate, recursion into a pattern
  walks into positions whose runtime contents are not themselves classified
  (e.g. a variable bound to an atom, an integer constituent, `nil`). At those
  inner positions the generated code still calls `match`/unify recursively, and
  there is nothing upstream that has proven `(consp p)`. Dropping it would risk a
  `car`/`cdr` on a non-cons.
- The car-equality test is what actually distinguishes patterns that *share a
  dbclass bucket but differ structurally*. The class only fixes the top-level
  predicate of the trigger; it does not re-verify equality at recursive
  positions, and constants embedded deeper in a pattern still must be compared.

**Conclusion.** At the top level, the dbclass dispatch *does* make the
predicate-symbol comparison partly redundant for the outermost car, so one
could special-case the top call. But because match is recursive and the same
code runs at inner positions where no class guarantee holds, removing the tests
in general is unsafe. Keeping them is the conservative, correct choice; the cost
is two cheap tests per node.

---

## Exercise 2 [*] — Why error if an a-rule has multiple triggers?

**Paraphrase.** `do-rule` raises an error when an assumption-making rule
(a-rule) is defined with more than one trigger. Why is that restriction sensible?

**Answer.** An a-rule's whole job is to *introduce an assumption and open a
subcontext* keyed to the binding that triggered it. With a single trigger the
semantics are clean: one matching assertion → one well-defined assumption →
one subcontext to explore and then pop.

Multiple triggers break this in several ways:

1. **Which match opens the context?** With N triggers a rule fires only when all
   N patterns are simultaneously matched. It is ambiguous *when* and *under
   which combined binding* the assumption should be made, and assumptions are
   supposed to be atomic, not conjunctions silently bundled by the matcher.
2. **Joins multiply firings.** Multi-trigger rules fire once per consistent
   combination of matches (a relational join). For ordinary deductive rules
   that is fine; for assumption rules it would spawn a combinatorial number of
   subcontexts, exploding the search and the assumption count in ways the user
   never declared.
3. **Stack discipline.** The context stack assumes a disciplined push/pop per
   assumption. A join with partial matches arriving at different times makes the
   push/pop nesting ill-defined.

Signalling an error forces the designer to express assumptions one trigger at a
time, keeping the assumption-context correspondence one-to-one and the search
tree predictable. (If a conjunction must drive an assumption, the user can build
an intermediate deduced fact with a normal rule, then trigger the a-rule on that
single fact.)

---

## Exercise 3 [*] — `unless`/`when` body vs. `:test` clause for indirect proof

**Paraphrase.** Two formulations of an indirect-proof a-rule are given. Version 1
puts the guard conditions inside the rule body using `unless`; Version 2 hoists
the same conditions into a `:test` on the trigger. Explain why they are not
equivalent and give pros/cons of each.

**Answer.**

The conditions are: not already known (`fetch ?p`), `?p` is not literally
`contradiction`, and `?p` is a simple proposition.

*Why not equivalent — it is about **when** the test runs and what it costs.*

- **Version 2 (`:test` on trigger).** The test is part of *matching*. The rule
  is only ever *queued/fired* for bindings that pass the test. A binding that
  fails the test produces **no rule instance at all** — no entry on the rule
  stack, no assumption, no work. The test is evaluated during the match phase,
  once per candidate binding, before any body machinery exists.
- **Version 1 (`unless` in body).** The rule *does* match and *does* fire for
  every `(show ?p)`. A rule instance is created and run; only then does the body
  decide to do nothing. So a binding that should be skipped still incurs the cost
  of instantiating and invoking the rule, and (depending on bookkeeping) may
  leave a fired-rule record.

So they compute the same *net assertions*, but they differ observably in: number
of rule firings, whatever counters/traces the engine keeps, and — subtly — in
how they interact with re-triggering. A `:test` that references only
trigger-bound variables is a pure filter on the match; an `unless` body can in
principle reference state computed *after* matching and can have side effects in
its non-skipped branch, giving it more expressive power.

*Trade-offs.*

| | Version 1 (`unless` body) | Version 2 (`:test`) |
|---|---|---|
| Efficiency | Worse: instantiates + runs rejected instances | Better: rejected bindings never become instances |
| Bookkeeping cleanliness | Pollutes firing counts / "rules run" stats | Keeps stats meaningful |
| Expressiveness | Can guard on values computed in the body, do partial work | Limited to a predicate over the match bindings |
| Readability | Guard sits next to the action it protects | Guard sits with the pattern; intent (a pure filter) is explicit |

**Recommendation.** Because all three guards here are pure functions of the match
binding `?p`, they belong in `:test` (Version 2): it is strictly cheaper and
keeps instrumentation honest. Use the body-`unless` form only when the guard
depends on something not known until the body runs.

---

## Exercise 4 [**] — Per-dbclass stacks instead of a linear search

**Paraphrase.** To avoid linearly scanning the global rule and data stacks during
matching, give each `dbclass` its own facts-stack and rules-stack. Implement
this, analyze the complexity, and measure whether it beats centralized stacks.

**Design.** Replace the two global stacks with per-class fields. When a fact is
asserted, push it onto `(facts dbclass-of-fact)`; when a rule is installed, push
it onto `(rules dbclass-of-trigger)`. Matching a new fact F against pending
rules now scans only `(rules class(F))`; running a new rule R now scans only
`(facts class(F))` for each of R's triggers. The dbclass lookup is an O(1) hash.

**Complexity.**

- *Centralized.* Each new fact is matched against the entire rule stack:
  Θ(R_total) candidate tests per fact, most of which fail the predicate check.
  Total matching work ≈ Θ(F · R) where F, R are total facts and rules.
- *Per-class.* Each new fact is matched only against rules whose trigger
  predicate equals the fact's predicate: Θ(R_c) where c = class(F). Summed,
  total work ≈ Σ_c (F_c · R_c). If there are K classes and facts/rules are
  spread evenly, F_c ≈ F/K and R_c ≈ R/K, giving ≈ Σ_c (F/K)(R/K) =
  K·(FR/K²) = **FR/K** — a factor-of-K speedup. The win grows with the number
  of distinct predicates.

**When it does NOT help.** If almost everything is in one dbclass (one dominant
predicate), K ≈ 1 and you regain the centralized cost plus a little hashing
overhead. There is also a small constant-factor cost: hashing per assert and
storing many small stacks instead of two big ones.

**Experimental protocol (what I would do, not run here).** Take the chapter's
KM*/natural-deduction benchmark suite, instrument both versions to count
`unify`/`match` attempts and wall-clock time, and plot vs. problem size. Expect
the per-class version to win on inputs with many predicates and to roughly tie
on inputs dominated by one predicate. *Not executed — analysis only.*

---

## Exercise 5 [**] — N-queens entirely in FTRE rules

**Paraphrase.** A purist says any task-specific Lisp in the rule bodies defeats
the point of a good PDIS. Test this by solving N-queens using FTRE rules alone —
all state and intermediate results live in the database, minimal non-FTRE
primitives in bodies. Compare to the Section 5.3.1 solver.

**Design sketch (rules only).**

- *Representation.* Assert the board structure as facts: `(square ?r ?c)` for
  each cell, `(queen ?r ?c)` for a placed queen, `(row ?r)` for rows that still
  need a queen.
- *Placement as assumptions.* For each row, an **a-rule** introduces an
  assumption `(queen ?r ?c)` for some column ?c — this is the choice point. The
  context stack gives exactly the depth-first backtracking N-queens needs: one
  assumed queen per row, pushed deeper as rows fill.
- *Constraints as contradiction rules.* Deductive rules detect attacks purely
  from the database:
  - same column: `(queen ?r1 ?c)` and `(queen ?r2 ?c)` with `?r1 ≠ ?r2`
  - same diagonal: `(queen ?r1 ?c1)`, `(queen ?r2 ?c2)` with
    `|?r1−?r2| = |?c1−?c2|`.
  When such a pattern matches, assert `contradiction`, which prunes the current
  context (pops the bad assumption) and forces the a-rule to try the next column.
  Row attacks are impossible by construction (one queen assumed per row).
- *Goal.* When every `(row ?r)` has a corresponding `(queen ?r ?c)` with no
  contradiction in the live context, the surviving context's assumptions are a
  solution.

The only genuinely awkward bits are the *arithmetic* tests (`≠`, absolute
difference for diagonals) and equality — these are the irreducible non-FTRE
primitives. The purist position is largely vindicated: search control
(choice + backtracking) maps cleanly onto a-rules + the context stack, and
constraint checking maps onto deductive rules. Lisp leaks in only for primitive
arithmetic comparison, which a richer pattern language could absorb.

**Comparison to Section 5.3.1.** The all-rules version is *more declarative and
more general* (constraints are independent facts; you could add board variants
by adding rules) but *slower and more memory-hungry*: every partial placement and
every constraint check becomes asserted facts and fired rules, with
match/index overhead the hand-written Lisp solver avoids. It also explores the
same DFS tree but pays PDIS bookkeeping at each node. So: cleaner and more
extensible, measurably slower — the classic declarative-vs-procedural trade-off.
*No benchmark executed — analysis only.*

---

## Exercise 6 [*] — A rule that fires only when nothing matches its trigger

**Paraphrase.** Suppose you want a new rule type that fires precisely when **no**
assertion in the database matches its trigger pattern (negation-as-failure).
What is it good for and how hard is it to implement?

**Uses.** This is closure / default reasoning:

- **Closed-world defaults:** "if there is no fact asserting the train is late,
  conclude it is on time."
- **Triggering fallback strategy** when no specialized method applied.
- **Detecting exhaustion** of a search frontier ("no remaining open goals").
- It is the operational basis of the closed-world assumption already present in
  this package's LTRE work.

**Implementation difficulty — moderate, and semantically tricky.** The hard part
is *non-monotonicity*. Positive rules fire when a match *appears*; this rule must
fire when a match is *absent* — but absence is not a stable, monotone property.

A workable scheme:

1. Index the negative rule under the trigger's dbclass like a normal rule, but
   mark it "negative."
2. Fire it (run its body) only after the database has stabilized — i.e. as a
   *quiescence* check: when no normal rules remain to run for that class and no
   matching assertion exists, run the negative rule's body.
3. **Maintain a dependency.** If a later assertion *does* match the pattern, you
   must retract the conclusions the negative rule drew. This is exactly a
   justification: the negative conclusion is supported by "absence of any P," so
   it needs TMS support (a default/assumption justification) to be withdrawn
   when P arrives.

So in a plain FTRE it is implementable but fragile (must control firing order
and live with non-monotonic surprises); done properly it really wants a TMS
underneath (which is why our package handles this via the closed-world
machinery rather than ad-hoc negative rules).

---

## Exercise 7 [*] — When the "cheapest expression" heuristic in `generate-match-body` fails

**Paraphrase.** When a freshly bound pattern variable can be computed several
ways, `generate-match-body` uses a heuristic to pick the supposedly cheapest
access expression. Show a case where the heuristic picks wrong; how could we
guarantee the optimum, and is it worth it?

**Answer.** The heuristic is local/greedy: among the access paths available *at
the point the variable first becomes bound*, choose the one that looks cheapest
(e.g. fewest `car`/`cdr` steps from an already-bound term). It fails whenever a
locally cheaper choice forces *more total work later*.

**Failure case.** Suppose variable `?x` first appears in trigger 1 deep inside a
structure — reachable via, say, `(cadr (caddr t1))` (cost 5 ops from `t1`) — and
also appears at the very top of trigger 2 as `(car t2)` (cost 1 op). The greedy
choice computes `?x` from trigger 2 because it is cheaper *for ?x*. But suppose
*nothing else* in trigger 2 is needed early, whereas computing `?x` from
trigger 1's path also computes intermediate subterms (`(caddr t1)`) that the
match needs *anyway* for another variable `?y`. By choosing the locally cheaper
trigger-2 path, the generated code recomputes `(caddr t1)` later for `?y`,
duplicating work. The globally cheaper plan shares the trigger-1 traversal.
A second failure mode: the heuristic counts cons-cell steps but ignores that one
candidate sits behind an *expensive `:test`* or a low-selectivity trigger, so the
"cheap" expression is on the path that is reached far more often.

**Guaranteeing the optimum.** Treat it as global subexpression optimization:
build the set of all access paths to every variable across all triggers, then
choose a *minimum-cost set of computations that covers all needed variables*,
sharing common subexpressions (common-subexpression elimination over the
car/cdr DAG). This is a small optimization problem (can be cast as min-cost
covering / DAG scheduling). With realistic cost weights (including selectivity)
it finds the true optimum.

**Is it worth it?** Usually no. Triggers are tiny (a handful of positions), the
greedy choice is right the vast majority of the time, and match procedures are
compiled once and reused, so even a suboptimal plan is amortized over many runs.
The optimizer adds compile-time complexity for a payoff that matters only for
pathologically deep/wide triggers. Worth it only if a profile shows match time
dominating on large rule sets — otherwise keep the heuristic.

---

## Exercise 8 [*] — `rlet` does not check that bound vars are FTRE variables

**Paraphrase.** `rlet` binds variables without verifying they are genuine FTRE
variables. Is that a problem?

**Answer.** It is a latent correctness/robustness hazard rather than an
everyday bug.

- **What can go wrong.** If a name passed to `rlet` is *not* a real FTRE pattern
  variable (e.g. a plain symbol, a typo, or something that collides with a Lisp
  special/global), the binding silently establishes a value that the match/body
  machinery will not treat as a logic variable. The result is a rule that runs
  but binds the "wrong" thing: a variable the body reads stays unbound (or holds
  a stale global), producing silently incorrect inferences instead of a clean
  error. Typos become semantic bugs, not syntax errors.
- **Why it usually does not bite.** In practice `rlet` is used by rule authors
  who pass the same variables that appear in triggers, so the names are correct
  by construction, and the macro expansion would error loudly only on truly
  malformed input.

**Verdict.** It is a problem of *defensiveness and debuggability*, not of normal
operation. The cheap fix is to add a check that each name is a recognized FTRE
variable (same predicate the matcher uses) and signal an error otherwise — this
converts a class of silent wrong-answer bugs into immediate, localized errors.
For a research/teaching system the omission is tolerable; for a library others
build on, add the check.

---

## Exercise 9 [**] — Automatic reordering of rule triggers

**Paraphrase.** FTRE makes the designer specify both *which* triggers a rule has
and the *order* they are tested. Build a rule system that automatically reorders
triggers for efficiency, and discuss manual vs. automatic ordering trade-offs.

**Why order matters.** Multi-trigger matching is a join. The cost is dominated by
the size of intermediate match sets, exactly as in database join ordering:
testing the most *selective* (fewest matches) and most *constraining* (binds
variables that prune later triggers) trigger first shrinks the candidate set the
other triggers must be checked against.

**Automatic-reordering design.**

1. **Statistics.** For each trigger predicate keep a running estimate of its
   selectivity — e.g. the number of assertions in its dbclass, and how often it
   participates in successful vs. failed matches.
2. **Binding analysis.** Compute, for each trigger, which variables it *binds*
   vs. *requires*. A valid order must bind a variable before a later trigger
   needs it (a partial-order constraint); among valid orders, prefer the one
   that minimizes estimated intermediate size.
3. **Greedy join ordering.** At rule-install time, pick first the trigger that is
   cheapest and most selective and respects binding constraints; then repeatedly
   pick the next trigger that adds the fewest expected new matches given the
   variables already bound. (Full optimality is the join-ordering problem, which
   is exponential; greedy with selectivity estimates is the standard practical
   choice.)
4. **Optional adaptivity.** Re-derive the order if statistics drift a lot during
   a long run.

**Trade-offs, manual vs. automatic.**

- *Manual:* the author can encode domain knowledge the statistics never capture
  ("this trigger is rare even though its class is big"), and ordering is stable
  and predictable. But it is error-prone, brittle as the rule set grows, and the
  optimal order may depend on data the author cannot foresee.
- *Automatic:* adapts to actual data distributions and relieves the author, but
  relies on selectivity estimates that can be wrong, adds install-time (or
  runtime) overhead, and makes performance harder to reason about and reproduce.

**Recommendation.** Automatic greedy ordering with an *author override* hook: use
estimates by default, let the author pin an order when they know better.

---

## Exercise 10 — `*bound-vars*` carries variables the match procedure does not use

**Paraphrase.** `build-rule` threads `*bound-vars*` (all variables bound so far)
into generated match procedures, but a match procedure really only needs the
variables actually mentioned in its trigger. So we generate procedures with
unused parameters and pass more data than necessary.

### 10a [*] — Can passing the extra info ever cause wrong results?

**No, not by itself.** Extra parameters that the match body never reads are
inert: correctness depends only on the values of the variables the code *does*
use, and those are passed correctly. The extra arguments cost memory/time
(consing the binding environment, larger argument lists, defeated tail/GC
opportunities) but cannot change the computed answer. The one caveat is
indirect: if a bug elsewhere caused an extra "unused" variable to actually be
referenced, it could matter — but that is a bug in the consumer, not a
consequence of passing the data per se.

### 10b [**] — Make match procedures receive only what they need

**Plan.** During `build-rule`, for each trigger compute
`needed = vars-mentioned-in(trigger) ∩ *bound-vars*` (the already-bound variables
this trigger's match actually references). Generate the match procedure's lambda
list from `needed` instead of from all of `*bound-vars*`, and at the call site
pass only those arguments (project the current binding environment down to
`needed`). Everything else is unchanged: the body procedure still receives the
full binding (it genuinely may use all of it). This is a straightforward
liveness/used-variable analysis over the trigger pattern at code-generation time.

### 10c [*] — Is the optimization worthwhile?

**Marginal.** It shrinks argument lists and the data shuffled per match attempt,
which can matter in the *hottest* inner matching loops of large problems, and it
makes generated code clearer. But triggers are small and modern Lisp handles
extra arguments cheaply, so the speedup is usually in the noise. Worth doing if
profiling shows match-call overhead dominating or if you want cleaner generated
code; otherwise low priority.

### 10d [*] — Same optimization for the body procedure?

**No (or much less so).** The body is *arbitrary user code* and can reference any
variable in scope, including ones not obviously mentioned (through macros,
`rlet`, helper calls, quasiquote). The code generator cannot in general prove a
variable is unused in a body the way it can for a structural trigger pattern. So
trimming the body's environment risks dropping a variable the body actually
needs. You *could* do a conservative analysis and trim only provably-dead
variables, but the safe and simple choice is to keep the full binding for the
body. The asymmetry is the point: trigger reference sets are statically
computable; body reference sets are not, in general.

---

## Exercise 11 — Open-coded unification for more constituent types

The current `generate-unify-tests` only handles symbols, conses, and integers.

### 11a [**] — Handle floating-point comparisons

**Plan.** Extend `generate-unify-tests` so that when a pattern constituent or a
bound value is a float, it emits a float comparison instead of `eql`. The subtle
issue is that exact equality on floats is the wrong default (rounding makes
`0.1 + 0.2 ≠ 0.3`). Options:

1. Emit a *tolerance* comparison `(< (abs (- a b)) *epsilon*)` for floats, with a
   configurable `*epsilon*`. This matches user intuition but breaks the usual
   transitivity/hashing assumptions of `eql`-based indexing.
2. Emit exact `=` and document that float patterns mean exact bit-equality.

Either way the generator must first dispatch on type: `(typecase x (float ...)
(integer (eql ...)) (symbol (eq ...)) (cons ... recurse ...))`. Mixed int/float
comparisons should be decided explicitly (coerce, or treat as non-matching).

### 11b [**] — User-defined types and identity tests

**Plan.** Add an extensibility hook: a registry mapping a *type recognizer* to a
*matching/identity predicate* and (optionally) a *decomposition* function for
recursing into substructure. `generate-unify-tests` consults the registry: for a
constituent, find the first registered type whose recognizer accepts it and emit
its identity test (for strings → `string=`, for arrays → elementwise compare or
`equalp`, for a struct → a user-supplied accessor-based comparison or recursion
into fields). This lets a user "teach" FTRE about strings, arrays, and structs
as pattern constituents without touching the generator's core, by registering
`(recognizer test [decomposer])` triples.

### 11c [*] — Dangers of allowing arbitrary data structures as constituents

- **Equality semantics become ambiguous.** What does it mean to unify two
  arrays/structs — identity, shallow, or deep equality? The wrong default gives
  silently wrong matches.
- **Indexing/hashing breaks.** The dbclass index relies on cheap, stable
  equality/hash of constituents. Arbitrary structures may be mutable, lack a
  good hash, or compare expensively, undermining the indexing the whole system's
  efficiency rests on.
- **Mutability.** If a structure used inside an asserted pattern is mutated
  later, the database's notion of "what was asserted" silently changes, which can
  corrupt the TMS/justification bookkeeping.
- **Cost and termination.** Deep comparison of large structures can dominate
  match time; cyclic structures can make naive recursion loop.

The safe rule: only admit *immutable* constituents with a cheap, well-defined
equality and hash.

---

## Exercise 12 — Resource bound: total number of assumptions

### 12a [**] — Limit total assumptions an FTRE may introduce

**Plan.** Add a global counter `*assumptions-made*` and a limit
`*max-assumptions*`. Increment the counter wherever an assumption is actually
introduced (the a-rule firing / context push that creates a new assumption).
Before introducing a new assumption, check `(< *assumptions-made*
*max-assumptions*)`; if the limit is reached, refuse to make the assumption
(treat that branch as cut off — like a resource-exhaustion failure) rather than
erroring out, so the search degrades gracefully and any already-found results
remain valid. Reset the counter when the FTRE is reset. This is a *total*
(cumulative) bound, distinct from a per-path depth bound.

### 12b [*] — Interaction with the existing assumption-depth bound

The two bounds are orthogonal but jointly restrictive:

- **Depth bound** limits how deep any *single* chain of nested assumptions goes —
  it shapes the *height* of the search tree (longest stack of simultaneously-held
  assumptions).
- **Total bound** limits the *cumulative* number of assumptions across the whole
  run — it shapes the *total nodes explored* (sum over all branches).

A search can hit the total bound while every individual path is shallow (a broad,
bushy tree of shallow assumptions), or hit the depth bound while having made few
total assumptions (one long thin chain). Whichever binds first cuts the search.
Importantly, with depth bound D and total bound T, you are guaranteed to explore
at most T assumption nodes and never a stack deeper than D; but neither bound
alone guarantees completeness, and tightening either can make a solvable problem
look unsolvable (incompleteness from resource exhaustion). They should be tuned
together: depth to bound proof length, total to bound overall effort.

---

## Exercise 13 [**] — Iterative deepening in FTRE; evaluate on KM*

**Paraphrase.** Implement iterative deepening (cf. Chapter 3, Exercise 8) in
FTRE and measure it on KM* problems.

**Plan.** Iterative deepening = repeated depth-limited DFS with the limit
increasing by one each round, combining DFS's low memory with BFS's optimal
(shallowest-solution-first) behavior. In FTRE the natural depth measure is the
*assumption depth* (length of the context stack), which already has a bound knob
(Exercise 12). Algorithm:

```
for limit = 0, 1, 2, ... up to max:
    reset FTRE database (clear assumptions/derived facts, keep rules)
    set *max-assumption-depth* = limit
    run FTRE on the problem
    if solved? -> return solution
```

Each round re-derives shallow consequences (the well-known IDDFS redundancy), but
because the branching factor of natural-deduction search makes the deepest level
dominate, total work stays within a constant factor of a single full-depth DFS,
while guaranteeing the shallowest proof is found first and keeping memory linear
in depth.

**Evaluation (what I would measure, not run).** On the KM* benchmark suite,
compare against plain bounded DFS on: (1) whether the *shortest* proof is found,
(2) rules fired and assertions created, (3) peak memory. Expectation: iterative
deepening finds shorter/cleaner proofs and uses less peak memory, at the cost of
some redundant re-derivation per round; it should shine on problems where plain
DFS dives into a deep fruitless branch first. *Analysis only — not executed.*

---

## Exercise 14 [**] — Eliminate redundant car/cdr in match procedures

**Paraphrase.** The generated match procedures redundantly recompute `car`/`cdr`
on the same substructure. Rewrite the rule code to use internal variables that
are set as the matcher walks the structure, avoiding recomputation.

**Plan.** This is common-subexpression elimination plus a *walking pointer*
strategy in the code generator:

1. As `generate-match-body` descends a trigger pattern, maintain a mapping from
   each *structural position already reached* (e.g. "cadr of t1") to a freshly
   generated `let`-bound temporary holding that subterm's value.
2. Emit, at the point a node is first reached, `(let ((tmp (car cur))) ...)` /
   `(setq cur (cdr cur))` style bindings, then refer to `tmp`/`cur` thereafter
   instead of re-emitting the full access path. Walking with a single mutable
   `cur` pointer (advanced by `cdr`) avoids both repeated `cdr` chains and the
   re-traversal across multiple variable references to the same position.
3. Constituent tests and variable bindings then read the temporaries, never the
   raw access expressions.

**Effect.** Match cost for a trigger of size n drops from "sum of access-path
lengths over all referenced positions" (which can be O(n²) for deep nesting where
each leaf re-walks its prefix) to O(n) — each cons cell visited once. This is
exactly the optimization Exercise 7's global plan also wants; combine them.
Correctness is preserved because the temporaries hold the same values, just
computed once. *Code not written — analysis only.*

---

## Exercise 15 [**] — Reclaim memory: avoid permanently-defined match/body functions

**Paraphrase.** Implementing rules as *named* Lisp procedures means their
function cells live forever (infinite extent). Throwing away an FTRE does not
free the memory of its generated match/body procedures. Build a version that
avoids this.

**Problem.** `(defun rule-match-37 ...)` installs a global function binding that
survives even after the FTRE that needed it is discarded; the symbol and its
compiled function stay reachable, so the GC cannot collect them. Many short-lived
FTREs leak generated code.

**Solutions.**

1. **Anonymous closures instead of named functions.** Generate the match/body
   code as `(lambda ...)` (e.g. via `coerce ... 'function` or `compile nil
   lambda`) and store the resulting function *objects* in the rule structure
   itself (in a slot), rather than in a symbol's function cell. When the FTRE and
   its rules are dropped, the function objects become unreachable and are
   collected normally. This is the cleanest fix and the design our package
   already follows in spirit (rule bodies are first-class callables stored on the
   engine, not global definitions).
2. **Uninterned / gensym names + explicit `fmakunbound`.** If named functions are
   kept for debuggability, intern them under gensyms tied to the FTRE and call
   `fmakunbound` on teardown to release the function cells. More bookkeeping and
   error-prone (you must track every name).
3. **Per-FTRE package** that is deleted on teardown, taking its symbols with it.

**Recommendation.** Store compiled closures as rule slots (option 1). It removes
the leak by construction and avoids global namespace pollution.

---

## Exercise 16 [*] — Purpose of `(= *context* ,*context*)` in `seek-in-context`'s goal rule

**Paraphrase.** The goal-detection rule inside `seek-in-context` includes the
test `(= *context* ,*context*)`. What is it for, and give an example where
removing it causes a problem.

**Answer.** `seek-in-context` sets up a rule to watch for a goal pattern *within
a specific logical context*. The quasiquote captures the context value that was
current *when the goal was posted* (`,*context*`), and the runtime test
`(= *context* ...)` compares it against the context current *when a candidate
match fires*. The test ensures the goal is only considered satisfied by an
assertion believed **in (or appropriate to) the very context that asked for it**,
not by something that happens to be true in a *different* assumption context.

**Why needed — the stack is reused.** Because contexts are a stack of
assumptions explored depth-first, the same goal-watching rule can still be live
while the engine has pushed into, or popped out to, a *different* context. A
match arriving while a different set of assumptions is in force is not a valid
proof of the original goal under the original assumptions.

**Failure example.** Suppose under context C1 (assumptions A) we seek `P` to find
a contradiction (indirect proof). The engine pushes context C2 (assumptions A ∪
{B}) for some sub-exploration, and inside C2 derives `P` *because of B*. Without
the `(= *context* ...)` guard, the goal rule fires and reports that `P` was found
"for C1" — but `P` was only true given the extra assumption B that C1 never made.
You would conclude the contradiction (and accept the indirect proof) on the basis
of an assumption that is not actually in force at the goal's context: an unsound
result. The context-equality test blocks exactly this cross-context leakage.

---

## Exercise 17 — Control predicates `premise` and `goal`

`premise(x)` means *x is believed as an assumption of the problem*; `goal(x)`
means *x is the proposition we are trying to prove*. Instead of bare assuming `P`
we assert `premise(P)`; instead of asserting `show(P)` we assert `goal(P)`.

### 17a [**] — Implement the semantics with one FTRE rule each

**`premise` rule.** A rule triggered by `(premise ?x)` whose body actually makes
`?x` believed as an assumption of the problem — i.e. it asserts/assumes `?x`
into the current (top-level) context with assumption status. Sketch:

```
(rule ((premise ?x))
      (assume! ?x :premise))      ; install ?x as a problem assumption
```

So `premise` is a thin control wrapper: matching it triggers the actual
assumption of its argument, while leaving `(premise ?x)` itself in the database
as a marker that the system can later inspect (used by `solved?`).

### 17b [**] — `solved?` procedure

**`goal` rule.** A rule triggered by `(goal ?x)` that posts `?x` as a thing to
show, i.e. behaves like asserting `(show ?x)`:

```
(rule ((goal ?x))
      (rassert! (show ?x)))
```

**`solved?(ftre)`.** Because the goal is now explicit in the database as
`(goal ?x)`, the engine can self-check success: `solved?` looks up every asserted
`(goal ?x)` and returns non-nil iff, for each, `?x` is currently *believed*
(`fetch ?x` succeeds / it is in / it is supported in the current context).

```
solved?(ftre):
    goals = all x such that (goal x) is asserted
    return goals is non-empty and for every x in goals: believed?(x)
```

The advantage the predicates buy: the system can decide *on its own* whether the
user's stated problem has been solved, without the caller hard-coding which
proposition to check — the goal is data in the database, not external knowledge.
(If "solved" should mean *any* goal proved rather than all, use `some` instead of
`every`; I assume "all stated goals" here and note the assumption.)

---

## Exercise 18 — Tuning up the `fnd` rule set

The `fnd` (natural-deduction "find a proof") rules pass the basic tests but can
be improved. (This problem is hands-on with the book's `fnd.lisp` /
`fnd-ex.lisp`; below is the approach, since the system is not implemented here.)

### 18a [**] — `myfnd-ex.lsp` extending `fnd.lisp` with `premise`/`goal`

**Approach.** Copy `fnd.lisp` to `myfnd-ex.lsp` and add the two control-predicate
rules from Exercise 17 (`premise`→assume, `goal`→show + enable `solved?`).
Restate the standard example problems using `premise(...)` for givens and
`goal(...)` for the conclusion. Run each example and record, per example:
(1) solved? yes/no, (2) number of rules fired, (3) number of assertions created.
*Instrumentation only — nothing executed here.*

### 18b [*] — Diagnose the failing examples

**Approach / likely findings.** For each unsolved example, trace which rule
*should* have fired and did not. Typical natural-deduction gaps are: a missing or
overly-restrictive introduction/elimination rule (e.g. an `or`-elimination case
not covered), a goal that requires *backward* chaining (subgoaling via `show`)
that the forward rules never set up, or a needed assumption that is never made
because no a-rule's trigger matches the problem's encoding. Write up the specific
missing inference per example. The recurring root cause is usually that the rule
set chains *forward* well but lacks the goal-directed subgoaling to attack
certain conclusions — which is exactly what `goal`/`show` control is meant to
supply.

### 18c [**] — Fix the rule set so all examples solve

**Approach.** Following the book's hint ("an ounce of analysis"), the fix is
small and general rather than many special cases: add the goal-directed control
that lets the prover *work backward* from `goal(P)` to the subgoals that would
prove `P` (e.g. to prove an implication, assume the antecedent and show the
consequent; to prove a conjunction, show each conjunct; to prove via indirect
proof, `seek-in-context (not P) contradiction`). Adding these few
`show`-driven subgoaling rules — driven by the now-explicit `goal` predicate —
closes the failing cases generally, instead of patching each example. Strive for
one clean rule per logical connective rather than example-specific hacks.

---

## Exercise 19 — From stack-based contexts to context trees (non-DFS search)

The stack organization of logical environments forces depth-first search. Other
strategies (best-first, beam) are sometimes preferable.

### 19a [*] — What parts of FTRE must change for a context tree?

- **Context representation.** Replace the single push/pop *stack* with a *tree*
  of contexts, where each node records its parent context plus the one assumption
  that distinguishes it (so a node's full assumption set = its parent's set ∪ its
  new assumption).
- **a-rule semantics.** Instead of *push assumption / explore / pop*, an a-rule
  fired in context C must *create a child context* C' = C + assumption and add C'
  to a frontier of unexpanded contexts, then **return** rather than recurse.
- **Control loop / scheduler.** Add an explicit agenda of "fringe" contexts and a
  selection step: pop the *best* fringe context (by a user-supplied criterion)
  and make it current, rather than always descending the most recent.
- **"Current context" plumbing.** Everything that reads `*context*` and assumes
  it is the top of a stack must instead read the currently-selected tree node;
  belief/`fetch` must be evaluated relative to a node's accumulated assumption
  set (walk to root), not a stack.

### 19b [***] — Design and implement tree-based FTRE

**Design.**

- *Node:* `{parent, added-assumption, derived-facts, status}`. Believed-in-node =
  facts derivable from the union of assumptions along node→root.
- *Frontier:* a priority structure of unexpanded nodes.
- *Expansion:* selecting a node makes it current and runs deductive rules to
  quiescence in it; each enabled a-rule produces one child per assumption choice,
  each pushed onto the frontier with a priority from the user's evaluation
  function `f(node)`.
- *Search policy via the comparator:* best-first = order frontier by `f`;
  beam search = at each level keep only the top-k children and discard the rest;
  DFS = LIFO (recovers the original behavior, a useful sanity check).
- *Belief evaluation:* cache each node's derived set; on selecting a child, start
  from the parent's cached beliefs and add only the new assumption's
  consequences (incremental), to avoid recomputation.

This is essentially turning FTRE's implicit DFS recursion into an explicit
agenda-driven graph search — closer in spirit to an ATMS-style multi-context
view than the single-context stack. *Design only; not implemented.*

### 19c [**] — Compare tree-based vs. stack-based FTRE

**Approach / expectation.** Run both on a suite of natural-deduction problems,
measuring rules fired, assertions created, peak memory, and time to first/best
solution. Expectations: the **stack** version is leaner in memory (one context
at a time, O(depth)) and faster when the first DFS path is good; the **tree**
version uses more memory (must hold many fringe contexts and their cached
beliefs) but finds better/shorter solutions sooner on problems where DFS would
plunge into a deep wrong branch, because best-first/beam can jump to a promising
context. Net: tree wins on *quality and worst-case search shape*, stack wins on
*memory and best-case speed*. The right choice is problem-dependent; a good
evaluation function is what makes the tree version pay off. *Analysis only.*

---

## Exercise 20 — Extend KM* to first-order predicate calculus

KM* is purely propositional.

### 20a [***] — Add quantifier inference rules following KM*'s structure

Mirror KM*'s connective pattern (each connective has an introduction and an
elimination rule) for the quantifiers:

- **Universal introduction (∀I).** To prove `(for-all ?x P(?x))`: introduce a
  *fresh, arbitrary* constant `a` (an eigenvariable that appears in no current
  assumption), prove `P(a)`; then conclude `(for-all ?x P(?x))`. The freshness
  side-condition is the crux — the constant must not occur free in any premise or
  in the goal's other parts, else the proof is unsound.
- **Universal elimination (∀E).** From `(for-all ?x P(?x))` and any term `t`,
  conclude `P(t)` (instantiate the bound variable with any term).
- **Existential introduction (∃I).** From `P(t)` for some term `t`, conclude
  `(there-is ?x P(?x))` (witness `t` exists).
- **Existential elimination (∃E).** From `(there-is ?x P(?x))`, introduce a fresh
  constant `a` (the *witness*, again an eigenvariable not occurring elsewhere),
  assume `P(a)`, and if you can derive a conclusion `Q` that does **not** mention
  `a`, conclude `Q`. The eigenvariable condition (the witness name must not
  escape into the conclusion) is what keeps ∃E sound.

The hard, genuinely first-order parts are: (1) **fresh-constant generation** with
correct **scope/occurrence side-conditions** for ∀I and ∃E, and (2)
**substitution** `P(?x ↦ t)` that respects variable capture (rename bound
variables to avoid capturing free variables of `t`). These are exactly the issues
absent from the propositional system.

### 20b [***] — Implement and test

**Approach.** Add the four rules above to KM*, plus machinery for: generating
eigenvariables, checking occurrence side-conditions, and capture-avoiding
substitution. Test on standard first-order theorems and inferences — e.g.
`∀x P(x) ⊢ ∃x P(x)` (with non-empty domain), Barbara-style syllogisms
(`∀x (P(x)→Q(x)), ∀x (Q(x)→R(x)) ⊢ ∀x (P(x)→R(x))`), quantifier-duality
(`¬∀x P(x) ⊢ ∃x ¬P(x)`), and prenex manipulations — verifying both that valid
arguments are proved and that the side-conditions correctly *block* the classic
unsound "proofs" (e.g. illegitimately generalizing over a constant that appears
in a premise). *Implementation and testing described, not carried out here.*

---

*End of Chapter 5 analysis. No code written; no programs executed (`codeRuns =
false`). FTRE is out of scope for this package per `BRIEFING.md`.*
