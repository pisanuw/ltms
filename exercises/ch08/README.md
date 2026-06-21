# Chapter 8 -- Putting the JTMS to Work (JTRE / JSAINT)

Forbus & de Kleer, *Building Problem Solvers*, Section 8.8 Exercises.

This chapter builds **JTRE** (a JTMS-backed, pattern-directed forward rule
engine) and on top of it **JSAINT** (a symbolic-integration problem solver
modeled on Slagle's SAINT, using an agenda of goals and best-first control).

What the `ltms` package implements: the truth-maintenance substrate and rule
engines (JTMS, JTre, Tre, LTRE, dependency-directed search). It does **not**
ship JSAINT, the integration-operator language (`definteg`), the simplifier
(`simplify.lisp`), or the `j-queens` solver. So exercises that probe rule-engine
*mechanics* are demonstrated in `solutions.py`; the JSAINT/simplifier design
exercises are answered in prose here.

Each exercise below gives a paraphrase (not the book's wording) followed by an
answer. Difficulty stars from the source are noted as (\*).

Run the demonstrations:

```
# from the repository root
. .venv/bin/activate
python exercises/ch08/solutions.py
```

---

## Exercise 1 -- the dangers of arbitrary `:TEST` code in triggers

The `:TEST` option lets a rule attach an arbitrary predicate to its trigger.
Parts examine why that is dangerous and how to fence it in.

### 1a (\*) Two disasters from a `:TEST` that runs `(fetch ...)` -- DEMONSTRATED

**Paraphrase.** The given rule's `:TEST` calls `fetch` against the live
database. Name two ways this can go wrong, with examples.

**Answer.**

1. **Arbitrary computation during matching.** A `:TEST` is ordinary Lisp run by
   the matcher, so it can loop forever, raise, be slow, or perform side effects.
   The matcher is on the critical path of every assertion, so a bad test stalls
   or corrupts the whole engine. Example: a `:TEST` that recursively calls the
   prover, or one that mutates the database, turns a single `assert!` into an
   unbounded or self-modifying computation.

2. **Order-dependent, dependency-blind belief.** A `:TEST` that consults current
   belief (`fetch '(using trap-door-code)`) makes the rule's firing a function
   of *assertion order* rather than of its trigger bindings, and creates **no
   dependency link** to the consulted fact. So: if `(using trap-door-code)` is
   asserted *after* `(prime-number 7)`, the suggestion is never produced; and if
   `(using trap-door-code)` is later retracted, `(suggest-code-key 7)` wrongly
   stays believed because the JTMS recorded no justification through the tested
   fact. This breaks the TMS's whole reason for existing.

`solutions.py::_ex1a_unsafe_test` builds the same facts in two orders and shows
the conclusion appears in one order and not the other
(`order_dependent_bug = True`), exactly disaster (2).

### 1b (\*) A safe sublanguage for tests

**Paraphrase.** Pick a Common Lisp subset such that any `:TEST` written in it
cannot trigger the disasters above.

**Answer.** Restrict `:TEST` to a **pure, terminating, side-effect-free
predicate over the trigger's bindings only**. A workable subset: variables bound
by the trigger and constants; total arithmetic/comparison predicates (`=`, `<`,
`>`, `numberp`, `eq`, `equal`, `member` on a *constant* list); boolean
combinators (`and`, `or`, `not`); and `let` over the above. Explicitly banned:
any database access (`fetch`, `assert!`, `referent`), any I/O, any unbounded
recursion or iteration, `apply`/`funcall`/`eval`, and assignment (`setf`). With
those gone, a test is a pure function of the bindings, so it cannot loop on
external state, cannot perform side effects, and cannot make belief depend on
order or on un-tracked facts.

### 1c (\*\*) Enforce the sublanguage in `junify.lsp`

**Paraphrase.** Modify the unifier/rule-installer to reject `:TEST` forms that
escape the safe subset.

**Answer (design).** At rule-definition time, before the test is compiled, walk
the test S-expression with a whitelist checker: every operator symbol must be in
the allowed set, every leaf must be a constant or a variable that appears in the
trigger, and any quoted list argument (e.g. for `member`) must be literal. Reject
(signal an error at macro-expansion time) on the first disallowed symbol or
free variable. Because the check is purely syntactic over the whitelist, it is
linear in the test's size and runs once per rule definition, not per match.

### 1d (\*\*) Evaluate the sublanguage by finding useful tests it forbids

**Paraphrase.** Find plausible, useful `:TEST`s that the safe subset cannot
express.

**Answer.** Several legitimate tests need information the pure subset bans:

- *Type/structure lookups in a taxonomy* ("is `?x` a subclass of `polynomial`?")
  require consulting the database, which is banned.
- *Numeric tolerance against a stored constant* ("is `?x` within current epsilon")
  needs a global parameter, which is external state.
- *Cheap pre-pruning by querying whether a needed fact already exists*
  (a controlled `fetch`) is exactly disaster (2) but is sometimes a sound,
  monotone optimization when the queried fact is itself a premise.

The conclusion: pure-function tests are safe but under-expressive. The proper
fix is not richer tests but **moving database conditions into the trigger
conjunction** (where the TMS records dependencies) and reserving `:TEST` for
pure arithmetic/structural guards.

---

## Exercise 2 (\*\*) Store a rule as one cons cell instead of a `rule` struct

**Paraphrase.** Since a rule can be re-found from its class, and the
JTRE/class backpointers plus the counter are redundant, rewrite `jrules.lsp` to
store a rule in a single cons cell. How much harder is debugging, is it worth
it, and how do you get both?

**Answer.** A rule needs, at minimum, its trigger pattern and its body, so a
single `(trigger . body)` cons cell suffices; the JTRE handle is available as
the dynamic argument to `run-rules`, and the class is recoverable by car-indexing
the trigger. **Debugging gets much harder:** with no counter you lose stable rule
identity for tracing/`why`; with no backpointers you cannot cheaply ask "what
class is this rule in" or print a readable rule, and breakpoints on a specific
rule become awkward. **Is it worth it?** Only under real memory pressure with
huge rule sets; for normal use the struct's clarity dominates. **Best of both:**
keep the compact cons-cell representation as the *stored* form but reconstruct a
transient struct (or attach a weak debug table keyed by the cons cell) only when
debugging is enabled, so production pays nothing and debugging keeps full
metadata. This is a representation/conditional-compilation tradeoff, not a
correctness change, so it is described rather than demonstrated.

---

## Exercise 3 (\*\*) Conjunctive triggers: fire only when all conditions hold -- DEMONSTRATED

**Paraphrase.** Change the rule system so a multi-trigger rule runs only when
the belief conditions of *all* its triggers hold at the same time.

**Answer.** The base engine fires a rule per single matched trigger. A
conjunctive rule `((:IN p)(:IN q) ...)` is implemented by **nesting**: the rule
on the first trigger, when it fires, installs a rule on the second trigger that
captures the first's bindings, and so on; the innermost body is the user body.
Because every level fires only under its IN condition, the body runs only when
*all* triggers are simultaneously believed, and the JTMS justification linking
the conclusion to all antecedents means the conclusion is withdrawn if any
antecedent later goes OUT.

`solutions.py::_ex3_conjunctive_trigger` shows `(mumble a)` is **not** believed
after only `(foo a)`, and **is** believed once `(bar a)` is also asserted
(`mumble_after_foo_only = False`, `mumble_after_both = True`). This nesting
pattern is exactly how JTRE compiles a multi-clause `rule` macro.

---

## Exercise 4 (\*\*) Remove a rule struct once a ground trigger has matched -- DEMONSTRATED

**Paraphrase.** A rule whose look-ahead trigger is fully ground (e.g. `(bar A)`)
can match at most one fact, so once it fires the rule struct is dead and should
be removed. Make JTRE detect and discard such rules after use.

**Answer.** Detection test: when the nested rule for the second trigger is
installed, its pattern is already fully ground (no unbound variables) because the
first trigger bound them. Such a rule can succeed at most once, so after its body
runs it should de-register itself from its dbclass so the matcher never reconsiders
it. A clean implementation: have `run-rules` (or the body wrapper) check whether
the just-fired rule's trigger is ground, and if so splice it out of its class's
rule list.

`solutions.py` shows both halves:

- `_ex4_one_shot_rule` uses a one-shot guard so the body fires **exactly once**
  even after the matching datum is re-justified (`body_invocations = 1`).
- `_ex4_match_count` confirms a ground trigger `(bar a)` has exactly one
  successful match (`successful_matches_for_ground_trigger = 1`), so the rule is
  indeed dead weight afterward.

---

## Exercise 5 (\*\*) Generalize `TRY-IN-CONTEXT` for cached partial solutions + nogoods

**Paraphrase.** The `j-queens` version of `TRY-IN-CONTEXT` misbehaves in a
solver that caches partial solutions *as well as* nogoods. Give an example and
fix it.

**Answer (design).** `TRY-IN-CONTEXT` assumes a choice, runs, and on
contradiction backs out. The bug appears when a previously **cached partial
solution** already commits some of the same choices: enabling the new assumption
can re-derive a *cached* (still-believed) fact whose support is a different,
earlier context, so the routine either (a) treats an already-true choice as fresh
and double-counts/over-constrains, or (b) misattributes a nogood to the current
assumption when the real culprit is a cached assumption. Concrete example: queens
where columns 1-2 are a cached partial solution and the routine tries column 3;
the contradiction is between column 3 and the *cached* column 1, but
`TRY-IN-CONTEXT` blames only column 3 and learns a nogood that is too specific
(or too general). **Fix:** before assuming, check `is_true`/`is_false` for the
choice (skip if already forced, as `dd_search` does), and when a contradiction
fires, compute the responsible assumptions from the violated clause and record
the nogood over *that* assumption set rather than the single current choice. The
package's `dd_search` already embodies the corrected discipline: it skips choices
already true/false, and its handler calls `assumptions_of_clause` to learn a
nogood over the actual culprits (see `src/ltms/dds.py`). So the generalized
`TRY-IN-CONTEXT` is structurally `dd_search`'s per-choice body.

---

## Exercise 6 -- why two operators implement one integral law

The power rule `int u^n du = u^(n+1)/(n+1)` (n != -1) is split across two
operators (`Integral-of-SQR`, `Integral-of-Polyterm`); likewise simple-e vs
e-integral.

### 6a (\*) Which JSAINT feature forces the duplication?

**Paraphrase.** What about JSAINT makes two operators necessary for one law?

**Answer.** Operators in JSAINT are **pattern-triggered**: an operator applies
only when the goal *syntactically* matches its trigger pattern. `x^2` and
`x^n` (general n) are different surface forms, and there is no unification that
covers a literal square *and* an arbitrary exponent within a single trigger
pattern (the matcher has no "this constant or any exponent" construct). So one
operator handles the special-cased shape, another the general shape. The
duplication is a limitation of purely syntactic pattern matching, not of the
mathematics.

### 6b (\*) Two ways to fuse them into one operator

**Paraphrase.** Propose two extensions letting one operator cover the whole law.

**Answer.**

1. **Pre-normalize the expression** so the special cases collapse into the
   general form: rewrite `x` as `x^1` and `x^2` into the canonical `(expt x n)`
   before operators run, leaving a single `Integral-of-Polyterm` to match all
   `(expt x ?n)` with a `:TEST` that `?n != -1`.

2. **Enrich the trigger language** with predicate-bearing patterns (see Ex. 14):
   a single operator with trigger `(expt x (? n (and (numberp n) (/= n -1))))`
   that matches any non-`-1` exponent. This needs the higher-order pattern
   facility of Exercise 14.

---

## Exercise 7 (\*) Logical status of a control term like `integrate` -- DEMONSTRATED

**Paraphrase.** Is a control term such as `(integrate ...)` best seen as an
ordinary predicate, a modal operator, or a connective? Discuss tradeoffs.

**Answer.** All three readings are defensible:

- **Standard predicate** (`integrate(expr, result)` as a fact). Pro: it lives in
  the same database and TMS as domain facts, so goals get dependencies, can be
  retracted, and explanations compose uniformly; this is what JSAINT actually
  does and it is simple. Con: it conflates *object-level* truth ("this is the
  integral") with *control-level* intent ("work on integrating this"), which can
  be philosophically muddy.

- **Modal operator** (`Goal(integrate expr)`). Pro: cleanly separates "I want to
  integrate" from "the integral equals". Con: needs modal inference machinery the
  JTMS does not provide; heavyweight.

- **Connective.** Poor fit: a connective combines truth values of subformulas,
  but `integrate` denotes a *task*, not a truth function of its argument.

**Tradeoff verdict:** the predicate view wins in practice because it reuses the
TMS for free; the modal view is cleaner semantically but costs machinery JSAINT
does not have.

`solutions.py::_ex7_control_term_is_proposition` demonstrates the predicate
reading: an `(integrate ...)` goal is asserted, justifies a result, and when the
goal is **retracted** the result is withdrawn by the TMS
(`result_while_goal_in = True`, `result_after_goal_retracted = False`) -- i.e. it
behaves like a first-class, dependency-tracked proposition.

---

## Exercise 8 (\*\*) Operators whose applicability is unknown until subgoals solve

**Paraphrase.** Method design assumes that if the subgoals it proposes are
solved, their results always combine into a solution. Are there techniques where
applicability cannot be known until after the subgoals are solved? If so, extend
`definteg` to allow them.

**Answer.** Yes. Some integration techniques are *speculative*: you cannot tell
in advance that the recombination will succeed.

- **Integration by parts** (Ex. 12): you only know it helped if `int v du` turns
  out simpler than `int u dv`; sometimes it loops or grows.
- **u-substitution** (Ex. 11): the substitution is useful only if, after
  back-substitution, the result is expressible in the original variable.
- **Trigonometric substitution**: valid only over the domain where the chosen
  identity holds, knowable only after the subproblem's form is seen.

These are *generate-and-test* operators. **Extension to `definteg`:** add an
optional `:combine` / `:validate` clause that runs *after* the subgoals report
results. The operator proposes subgoals as usual, but its conclusion is justified
only if the post-hoc validator accepts the assembled results; otherwise the
operator's attempt is abandoned (and, in a TMS, a nogood records that this
operator does not apply to this goal). This makes operator applicability a
function of subgoal *results*, not just the goal's surface form.

---

## Exercise 9 (\*\*) Add run-time and storage bounds to JSAINT

**Paraphrase.** JSAINT's resource bounds are only internal counters; add wall-clock
and memory limits so hopeless problems do not run forever.

**Answer (design).** Wrap the agenda loop with two external governors checked
once per agenda step: (1) a deadline = start time + budget; if exceeded, stop and
report "resource exhausted". (2) a storage cap = a ceiling on the number of TMS
nodes / database facts / open subgoals; if exceeded, stop. Both are cheap
per-iteration checks. The bounds should be *parameters* so callers can tune them.
On exhaustion JSAINT should return a partial-progress report rather than an error,
and (if a TMS is used) mark the top goal's failure so the same problem is not
re-attempted under the same budget. This is operational instrumentation around the
existing control loop; no package code is needed to state it.

---

## Exercise 10 -- improving difficulty estimation and goal selection

### 10a (\*\*) Make difficulty depend on connection to the original problem

**Paraphrase.** Discuss tradeoffs of letting difficulty estimation depend on how
a subgoal connects back to the root problem.

**Answer.** Pro: context-sensitive estimates avoid wasting effort on subgoals
that are locally easy but embedded in a globally hopeless approach, and let the
estimate inherit information (e.g. depth, sibling count) from the path to the
root. Con: estimates become non-local and order-dependent, harder to cache and
reuse across approaches (the same subexpression may get different scores in
different contexts), and the bookkeeping to maintain the connection grows the
agenda's cost. The tradeoff is **focus vs reusability/coherence of caching**.

### 10b (\*\*) Let difficulty depend on the problem/operator kind

**Paraphrase.** Some operators are better than others; revise difficulty
estimation to weight by operator/problem kind.

**Answer.** Attach a per-operator *reliability/cost prior* (learned or
hand-tuned): operators that historically lead to quick solutions (standard
forms, table lookups) lower a goal's estimated difficulty; speculative operators
(by-parts, substitution) raise it. Estimate a goal's difficulty as a combination
of the cheapest applicable operator's prior and the subgoal structure that
operator induces. This biases best-first search toward high-yield operators
first.

### 10c (\*\*) Increase coherence so the solver finishes a near-done approach

**Paraphrase.** With a flat agenda, the solver can look incoherent: it may pick a
fresh subgoal of a 48-step approach over the last subgoal of a 12-step approach,
even when both look equally hard locally. Devise a scheme for more coherent
behavior.

**Answer.** Add a **global, approach-aware** term to the agenda's priority, not
just local difficulty:

- *Completion bonus*: prefer subgoals that finish an approach (few remaining
  siblings up the path to the root) -- e.g. priority gets a bonus inversely
  proportional to remaining subgoals in that branch.
- *Sunk-investment / least-commitment*: prefer continuing the approach with the
  fewest outstanding subgoals overall, so the solver "sees a plan through"
  instead of thrashing between approaches.

So priority = local-difficulty estimate adjusted by (remaining-work-in-this-
approach) and (total-work-of-this-approach). In the example, P1 (last of 12)
gets the completion bonus over P2 (first of 48), matching human preference.

---

## Exercise 11 -- complex u-substitution

### 11a (\*\*) A simple symbolic differentiator using `match` rules -- DEMONSTRATED

**Paraphrase.** u-substitution needs derivatives. Write `match`/rule-based rules
for a basic symbolic differentiation system.

**Answer.** Implemented in `solutions.py::_ex11a_symbolic_diff` as forward-chaining
`Tre` rules over expression terms: `d/dx c = 0`, `d/dx x = 1`,
`d/dx x^n = n*x^(n-1)`, and the sum rule `d(a+b) = da + db` (which requests the
sub-derivatives, then a nested rule combines them once both arrive). Running it on
`x^3 + 5` yields `("+", ("*", ("const",3), ("^",("var",),2)), ("const",0))`,
i.e. `3x^2 + 0`. Product/quotient/chain rules extend the same pattern.

### 11b (\*\*) What knowledge sources make good substitution suggestions?

**Paraphrase.** Good suggestions are critical; what knowledge should the system
draw on?

**Answer.** Useful suggestion sources: (1) **composite subexpressions** -- an
inner function `g(x)` inside `f(g(x))` suggests `u = g(x)` (chain-rule inversion);
(2) **derivative co-occurrence** -- if `g'(x)` (up to a constant) already appears
as a factor, `u = g(x)` is very likely to work; (3) **known standard forms** --
suggest substitutions that transform the integrand toward a table entry; (4)
**argument of transcendental functions** -- the argument of `ln`, `exp`, `sin`
(e.g. `3x` in `ln(3x)`) is a natural `u`. These are the heuristics SAINT used.

### 11c (\*\*\*) A facility for defining substitution methods

**Paraphrase.** Implement a mechanism for declaring substitution methods.

**Answer (design).** A `defsubst` macro declaring: a *trigger pattern* matching
candidate integrands; a *suggestion* binding `u` and computing `du` (using the
differentiator from 11a); a *rewrite* producing the transformed integrand in
terms of `u`; and a *back-substitution* step. The facility posts the transformed
problem as a subgoal, and on its solution applies back-substitution and (per
Ex. 8) validates that the result is expressible in the original variable before
justifying the answer. Not demonstrated (requires the full JSAINT goal machinery),
but the differentiator it depends on is demonstrated in 11a.

---

## Exercise 12 -- integration by parts

### 12a (\*) Problems implementing `int u dv = uv - int v du`

**Paraphrase.** What difficulties arise implementing integration by parts? (Hint:
`int x ln(x) dx`.)

**Answer.** Three problems: (1) **Choice of u/dv is unconstrained** -- any
factorization of the integrand into `u` and `dv` is a candidate, so the operator
is highly non-deterministic and can explode the search. (2) **No guarantee of
progress** -- `int v du` may be no simpler, or may regenerate the original
(parts applied to `int x ln x` with the wrong split loops back). (3)
**Applicability is post-hoc** (this is exactly Ex. 8): you only know the split
helped after solving the `int v du` subgoal. With `int x ln x dx` the productive
split is `u = ln x, dv = x dx`, giving `(x^2/2)ln x - int (x/2) dx`; the other
split makes things worse.

### 12b (\*\*\*) Extend JSAINT to do integration by parts

**Paraphrase.** Implement by-parts in JSAINT.

**Answer (design).** Add a by-parts operator that, for a product integrand,
proposes a small set of *heuristically ranked* (u, dv) splits (e.g. LIATE
ordering: pick `u` as the logarithmic/inverse-trig/algebraic factor), each
spawning a subgoal `int v du`. Use the Ex. 8 `:validate` extension so the
conclusion is justified only if the subgoal yields something strictly simpler
than the original, and record a nogood when a split loops. Ranking the splits and
bounding recursion depth keeps the branching factor manageable. Not demonstrated
(no JSAINT in package).

---

## Exercise 13 (\*\*\*) A more efficient like-terms combiner for the simplifier

**Paraphrase.** The `simplify.lisp` combine-like-terms rule (`3x + x -> 4x`) is
elegant but tries all bindings for the segment variables even when the sum has no
products. Implement a smarter scheme that scans for common subexpressions and
uses their positions to drive simplification, and compare performance.

**Answer (design).** The inefficiency is that segment patterns (`??pre`, `??mid`,
`??post`) make the matcher enumerate every split of the sum for every rule. A
targeted scheme: in one pass over the sum, build an index mapping each *base term*
(the `thing`) to the positions and coefficients where it occurs (a coefficient of
1 for a bare `thing`, the literal factor for `(* c thing)`). Any base term with
two or more entries is a merge candidate, and the merge is computed directly by
summing coefficients -- no backtracking search over segment splits. Sums with no
repeated base term do O(n) work and trigger zero merges, versus the original's
combinatorial split enumeration. Performance: the indexed method is O(n log n)
(or O(n) with hashing) per pass vs the rule-based method's worst-case exponential
split enumeration; on sums with no products it is the difference between one scan
and a full pattern search. Described, not demonstrated (no simplifier in package),
though the package's `Tre`/`fetch` indexing illustrates the same car-indexing
idea that makes the targeted scan cheap.

---

## Exercise 14 (\*\*\*) A higher-order pattern language

**Paraphrase.** The `move-constant-outside` trigger `(* ?const ?nonconst)` only
matches one shape and misses `(* 5 c (expt x t))` and `(* (log x) 5)`. Design a
higher-order pattern language expressing ideas like "if a product has a nontrivial
subset of constant factors, pull them out," and add it to JSAINT.

**Answer (design).** Introduce *set/segment patterns with predicates*: a pattern
construct that binds a **subset** of an associative-commutative operator's
arguments by a predicate, e.g.
`(* (?subset consts constantp) (?subset rest (not constantp)))`
meaning "partition the product's factors into the constant ones and the rest."
The matcher, knowing `*` is AC, partitions the argument multiset by the predicate
rather than relying on positional order, which fixes all three failing examples at
once (order-independent, multiple constants, subset extraction). The
move-constant rule becomes a single declaration: integral of the product = product
of the constant factors times the integral of the non-constant product. This
generalizes the special-casing of Ex. 6/13. Adding it to JSAINT means extending
the trigger compiler to handle `?subset` patterns over AC operators. Described,
not demonstrated.

---

## Exercise 15 (\*\*\*\*) Extend JSAINT to SAINT's full range

**Paraphrase.** Combine the previous extensions so JSAINT solves at least the
problems SAINT could.

**Answer.** This is an integration project: fold in u-substitution (Ex. 11),
integration by parts (Ex. 12), post-hoc validating operators (Ex. 8), the
predicate/subset pattern language (Ex. 14), the unified power/exp operators
(Ex. 6), the efficient simplifier (Ex. 13), and better agenda control (Ex. 10).
Together these give the heuristic transformations, the standard-form table, and
the search control that let SAINT solve MIT freshman-calculus integrals. Pure
engineering on top of JSAINT; no new principle, and out of scope for the package.

---

## Exercise 16 (\*\*\*\*) Reconstruct the LEX learning system on JSAINT

**Paraphrase.** Using JSAINT as a base, rebuild Mitchell/Utgoff/Banerji's LEX
learning system.

**Answer.** LEX learns *when* to apply each integration operator. On top of
JSAINT you would add: (1) a **problem generator** proposing training integrals;
(2) the JSAINT **problem solver** as the performance element; (3) a **critic**
that labels operator applications on a solution path as positive (on the shortest
solution) or negative; and (4) a **generalizer** doing version-space (candidate-
elimination) learning over a *grammar of operator preconditions*, maintaining the
S (most-specific) and G (most-general) boundary sets for each operator's
applicability condition. The learned, refined preconditions then replace the
hand-coded operator triggers, closing the loop. This is a full research-scale
reconstruction; described only.

---

## Summary

| Ex | Topic | Status |
|----|-------|--------|
| 1a | `:TEST` disasters (order-dependence) | **Demonstrated** |
| 1b-d | Safe test sublanguage; enforce; evaluate | Prose |
| 2 | Cons-cell rule representation | Prose |
| 3 | Conjunctive (all-conditions) triggers | **Demonstrated** |
| 4 | One-shot removal of ground-trigger rules | **Demonstrated** |
| 5 | Generalize `TRY-IN-CONTEXT` (cache + nogoods) | Prose (maps to `dd_search`) |
| 6 | Why two operators for one law; how to fuse | Prose |
| 7 | Logical status of control terms | **Demonstrated** |
| 8 | Post-hoc-applicable operators | Prose |
| 9 | Run-time / storage bounds | Prose |
| 10 | Difficulty estimation & coherence | Prose |
| 11a | Symbolic differentiation rules | **Demonstrated** |
| 11b-c | Suggestion sources; `defsubst` | Prose |
| 12 | Integration by parts | Prose |
| 13 | Efficient like-terms combiner | Prose |
| 14 | Higher-order pattern language | Prose |
| 15 | Extend JSAINT to SAINT's range | Prose |
| 16 | Reconstruct LEX on JSAINT | Prose |

The JSAINT-specific exercises (6, 8-16) are prose because JSAINT, its
integration-operator language, and the simplifier are not part of the `ltms`
package, which provides the JTMS / JTRE substrate beneath them.
