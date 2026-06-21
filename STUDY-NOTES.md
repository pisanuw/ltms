# STUDY-NOTES.md — How the BPS LTMS / reasoning engine works, and how to port it

Original engineering digest distilled from a study of the BPS Common Lisp
reference (`refs/bps-lisp/`, gitignored) and the relevant book chapters, plus a
verified survey of comparable systems. This is analysis and porting guidance in
our own words — it is not a copy of the book. Companion to [PLAN.md](PLAN.md).

Layered bottom-up: **terms+unify → TRE → (JTMS) → LTMS core → LTRE → advanced → (CLTMS)**.

---

## 1. Terms, variables, unification (shared by every layer)

One Robinson-style unifier is shared verbatim across TRE and LTMS.

- **Terms** are s-expressions (Lisp lists). A **variable** is a symbol whose name
  starts with `?`. **Bindings** are an alist threaded through recursion.
- `unify(a, b, bindings)` returns the (possibly extended) bindings **or** the
  sentinel `:FAIL`. **Crucial:** the empty binding list is a *legitimate
  success* ("unified, no new bindings"), so success is tested as `≠ :FAIL`,
  never by truthiness.
- `unify_variable` follows existing bindings (chasing the chain) and only binds a
  fresh variable after the **occurs-check** (`free-in?`), which rejects
  `?x = (F ?x)`. `free-in?` returns "safe to bind" — note the inverted naming.
- There is **no standardize-apart / renaming**: rules carry a seed environment
  and patterns match against *ground* database facts, so the two sides are
  assumed to share no variables.
- Two matching strategies coexist: **interpreted** `unify` (used by `fetch` and
  TRE) and **open-coded** matchers (`funify.lisp`: a rule trigger is compiled to
  explicit `consp`/`equal` tests). The open-coded path is a pure speed
  optimization with identical semantics.

**Port.** `Var` class (drop the `?name` hack); bindings = dict copied on extend;
`FAIL = object()` distinct from `{}`. Port `unify`/`unify_variable`/`free_in`
directly (keep the `a == b` fast-path first, keep the occurs-check). Replace
`sublis` with a recursive `substitute` that fully resolves chains. **Skip
`funify` entirely in v1.** Idiom map: `defstruct`→`@dataclass`; special
`*var*`→explicit arg or `contextvars`; `push/pop`→`list.append/pop`;
`assoc`→`dict`; `eval`'d `let` body→a Python callable taking the bindings dict.

---

## 2. TRE — the pattern-directed inference engine (no truth maintenance)

The minimal forward-chainer. Belief = "present in the database," full stop.

- **State** (per engine instance, not global): `dbclass_table` (hash:
  leftmost-symbol → bucket of facts+rules), a **LIFO queue** of
  `(body, bindings)` activations, counters.
- **Car-indexing:** every fact and trigger is keyed by its leftmost constant
  symbol (`get_dbclass`). Only facts and rules in the same bucket are ever
  unified — the only indexing BPS has. A variable in head position is an error
  unless bound.
- **`assert!`** inserts a fact (dedup by `equal`) and, *only if new*, queues the
  rules in its bucket via `try_rule_on`. **It does not run them.**
- **`rule` / `add_rule`** stores `(trigger, body, environment)` (the environment
  = bindings captured at creation, enabling lexically-nested rules) and
  back-tests it against existing facts. So fact-vs-rule arrival order is
  irrelevant (**bidirectional incremental join**).
- **`try_rule_on`** is the single match point: `unify(fact, trigger, env)`; on
  success enqueue `(body, bindings)`.
- **`run_rules`** drains the queue to quiescence; bodies may assert more facts /
  define more rules, pushing more work. **Conjunctive ("A and B and C")
  matching exists only via nested rules** — there is no multi-trigger syntax in
  TRE. No deletion, no retraction; rules have indefinite extent.

**Port.** `body(bindings, engine)` callable; nesting = body calls
`engine.add_rule(...)` (closure captures bindings). Thread the active
environment into `get_dbclass` explicitly (Lisp uses `boundp` + `*ENV*` — two
binding notions — because `run-rule` binds pattern-var *symbols* as real Lisp
variables; Python has no such implicit binding). LIFO or FIFO both correct (book
declares order-independent). Don't add loop detection (`(integer ?x) →
(integer ?x+1)` loops by design).

---

## 3. The shared TMS substrate (reused by JTMS and LTMS)

Both TMSes sit on the same skeleton; factor it out:

- **One `Datum` per ground proposition, one `TmsNode` per `Datum`.** The engine
  layer talks to the TMS only through `datum.tms_node`.
- **dbclass indexing + `unify`-based `fetch`** — identical to TRE, TMS-agnostic.
- **Enqueue hook:** when a node's belief changes, its parked `in/true`-rules (or
  `out/false`-rules) are pushed onto the engine's rule queue and **cleared**
  (one-shot). The hook only *queues* — it must never call back into the TMS
  mid-propagation (the DB may be transiently inconsistent).
- **Contradiction protocol:** a **stack** of handler callbacks; each returns
  truthy iff it resolved the contradiction; the dispatcher tries them top-down.
  `checking_contradictions` flag + `with_contradiction_check` /
  `with_contradiction_handler` context managers (unwind-protect = try/finally).
- **Explanation:** well-founded support → a proof DAG back to enabled
  assumptions; `assumptions_of_node`, `why_node`.

---

## 4. JTMS — justification-based TMS (optional stepping stone + contrast)

The *simplest* TMS; worth building first to nail the patterns LTMS reuses.

- A node has a **two-valued** label `IN`/`OUT` (**`OUT` ≠ false**; it means "not
  currently derivable" — the JTMS can never derive a negation: that is *the*
  JTMS↔LTMS difference). `support` is overloaded three ways: `nil` (OUT) | a
  `just` struct (derived; empty antecedents ⇒ premise) | the
  `:ENABLED-ASSUMPTION` sentinel.
- A **justification** is logically a definite (Horn) clause `antecedents ⇒
  consequence`. `J` grows monotonically; justifications are never deleted.
- **Adding a justification / enabling an assumption** only flips `OUT→IN` via a
  monotone forward sweep (`propagate-inness`), gated by `check-justification`
  (consequence OUT and all antecedents IN).
- **Retraction is the hard case — strictly two-phase:**
  1. `propagate-outness`: label `OUT` every node whose *current support* (by
     identity, `is`) flows through the retracted node.
  2. `find-alternative-support`: *only after phase 1*, search forgotten nodes
     for any other satisfied justification and re-propagate.
  Interleaving admits **ill-founded circular support** (`B←C`, `C←B`) — the bug
  the two-phase split exists to prevent.
- The JTMS **only signals** contradictions (a `contradictory?` node that is IN);
  it never resolves them. Dependency-directed backtracking is the engine's job,
  built on `assumptions_of_node` (which returns the assumptions of *one*
  well-founded support — not all, not minimal).

**Port.** `support` tri-value with an `ENABLED_ASSUMPTION` sentinel compared by
`is`; identity (`is`) test in `propagate-outness`; a per-call `visited` set
instead of the `mark` field; keep propagation purely forward and monotone within
each op (this is exactly where the LTMS diverges with bidirectional BCP).

---

## 5. LTMS core — Boolean Constraint Propagation (the heart of the project)

A sound-but-incomplete propositional reasoner. It generalizes the JTMS: the
engine supplies **arbitrary clauses** (and full formulas via `add_formula`,
which CNF-normalizes), not just Horn justifications. **Negation is just the
label**, so there is no separate negation node.

### Data model
- `TmsNode`: three-valued `label` (`UNKNOWN`/`TRUE`/`FALSE`); `support` (`None` |
  `ENABLED_ASSUMPTION` | the forcing `Clause` = well-founded support);
  `true_clauses` / `false_clauses` (clauses where the node appears
  positively / negatively — the BCP watch index); interned `true_literal` /
  `false_literal`; parked `true_rules` / `false_rules`.
- `Clause`: `literals` = list of `(node, sign)` sorted by `node.index`; plus the
  two incremental counters below.

### The counter trick (this is the whole performance story — get it exactly right)
- **`pvs`** ("potential violators") `= (#literals UNKNOWN) + (#literals
  currently satisfying)`. Equivalently: literals **not** yet labeled opposite to
  their sign.
- **`sats`** `= #literals currently satisfying`.
- Therefore: **violated ⇔ `pvs == 0`; unit/forcing ⇔ `pvs == 1`; satisfied ⇔
  `sats > 0`.** A satisfying literal still counts toward `pvs` (because if its
  assumption is later retracted it could become a violator again) — so
  **satisfied clauses are never discarded**; their counters must stay live for
  correct retraction.
- Maintained incrementally in `set_truth`: on `node→TRUE`, `decf pvs` of clauses
  in `false_clauses`, `incf sats` of clauses in `true_clauses` (symmetric for
  FALSE). When `pvs` drops below 2, queue the clause for checking. **Never
  rescan literals on the hot path.**

### Propagation
- **`check_clauses`** drains a work list: for each clause, if violated **record
  it** (don't raise), else if `pvs == 1` force the lone UNKNOWN literal via
  `set_truth` (re-guard that it is still UNKNOWN — another clause may have
  labeled it this round).
- **Contradictions are deferred:** accumulate violated clauses during
  propagation; dispatch only at the end of the top-level op
  (`check_for_contradictions`). Raising mid-BCP corrupts half-updated counters.
- **`add_formula`** → `normalize` to CNF (a `negate` flag folds DeMorgan
  in-line; `:IMPLIES`, `:IFF`, `:OR`, `:AND`, `:NOT`, `:TAXONOMY`), then
  `simplify_clause`/`sort_clause` (sort by node index → dedup adjacent, drop
  tautologies). Edge cases: `(:OR)` = FALSE = a single empty clause `[[]]`;
  `(:AND)` = TRUE = no clauses `[]`.

### Retraction (two-phase, as in JTMS)
1. `propagate_unknownness`: set the assumption and everything it transitively
   forced to `UNKNOWN`, incrementing counters back up; `clause_consequent`
   identifies the node a clause forced (a satisfied literal whose `node.support
   is this clause`).
2. `find_alternative_support`: re-run `check_clauses` on the freed nodes' clause
   lists to see if some other unit clause re-forces them.

### Contradiction handling
- `avoid_all`: get `assumptions_of_clause`, pick a culprit, **retract it, *then*
  `add_nogood`** (a clause = the negation of the conjunction of the contradicted
  assumptions). Order matters — nogood-before-retract would instantly re-violate
  and loop.

### Soundness, not completeness (expected, acceptable)
BCP is unit-resolution only. It leaves some entailed literals UNKNOWN
(`{x∨¬y, x∨y}` does not force `x`) and misses some contradictions (the 4-clause
non-Horn set on `x,y`). Do **not** try to make base BCP complete — that is the
optional CLTMS layer.

### Things that are Chapter-13 (CLTMS) only — stub/omit in the base port
`complete`, `queue`, `conses`, `delay-sat`, `cons-size`, clause `status`,
`full-add-clause`, `ipia`, `propagate-more-unknownness`, `walk-trie`. They exist
in `ltms.lisp` only to avoid redefinition.

---

## 6. LTRE — the reasoning engine layered on the LTMS

Forward-chaining, pattern-directed inference where **the engine does universal
instantiation (rule matching) and the LTMS does all propositional reasoning.**

- **`Datum` ↔ `TmsNode`** 1:1 via `referent`/`insert` (interns a ground form;
  the stored form is **always unsigned** — `(:NOT P)` and `P` share one node).
  Belief read by inverting the label for negated queries.
- **`assert!`** uses *direct translation*: `build_tms_formula` replaces simple
  props with their nodes (connectives stay), then `add_formula` installs clauses
  — **no node is created for the compound**.
- **`assume!`** is asymmetric and load-bearing: for a compound it builds a
  **guard node `N_F`** and installs `(:IMPLIES N_F formula)` so the clauses can
  be switched off by `enable`/`retract` of `N_F`. Re-assuming with the same
  reason is a no-op; a different reason errors; `retract!` requires the matching
  informant.
- **Rules** compile to a matcher + a body. Trigger conditions: `:INTERN` (fires
  when the datum merely exists), `:TRUE`, `:FALSE`. A `:TRUE`/`:FALSE` rule that
  matches before the node has the label is **parked** on
  `node.true_rules`/`false_rules`; the **LTMS→LTRE enqueue bridge** (installed in
  `create_ltre`) pushes it onto the rule queue when `set_truth` later assigns
  that label. Multi-trigger rules nest (each fired trigger installs the next →
  cartesian-product join). Rules **enqueue, not run**; `run_rules` drains.
- **Queries:** `fetch` (leftmost must be ground), `true?`/`false?`/`known?`/
  `unknown?` (sign-inverting). `contradiction(losers)` installs a
  `:DECLARED-CONTRADICTION` clause.

**Port.** `build_tms_formula` returns node objects at the leaves; rule bodies are
callables receiving a bindings dict; `:VAR`/`:TEST` → kwargs; `rassert!` just
builds the tuple with bound values (no `quotize`). Engine = instance, not the
`*LTRE*` global.

---

## 7. Advanced LTRE facilities (all exploit the handler stack)

- **Indirect proof** (`try_indirect_proof`): `assuming (:NOT fact)`, run rules;
  a pushed handler checks if `fact`'s node is among the contradiction's
  assumptions — if so, retract it and `add_nogood` to justify `fact`.
- **Closed-world assumptions** (`cwa.py` + set-rules): close a set by fetching
  `has-member` facts, `assume!` a `(set CWA members)` form, and reify a
  `CWA-JUSTIFICATION` that a rule turns *once* into an `:IMPLIES` clause; a
  handler detects an invalidated CWA in a contradiction's support and unwinds.
  Defensive ordering matters (retract old → assume new → justify); a known
  lingering-CWA edge exists (book Exercise 5).
- **Dependency-directed search** (`dds.py`): depth-first over mutually-exclusive
  choice sets; `assuming` each choice, run rules, recurse; a per-choice handler
  catches contradictions implicating that choice, throws the surviving
  assumptions back as `:LOSERS`, and records a nogood
  `(:NOT (:AND choice ...losers))`. **Capture assumption labels (signed) before
  any retraction** or the nogoods are wrong.

**Port.** Lisp `catch`/`throw` markers → custom exceptions carrying a marker
identity + payload, caught at the matching recursion level; `assuming` /
`with_assumptions` / `with_closed_set` must be exception-safe (try/finally).

---

## 8. CLTMS — completeness (optional, advanced; Session 8)

Makes BCP logically complete by adding **prime implicates** (logically
redundant but BCP-useful clauses) computed via **consensus (resolution)**.

- Governed by a tri-valued `complete` flag: `None` (plain BCP) / `True` (eager)
  / `DELAY` (accumulate, run on explicit `complete_ltms()` — recommended).
- Two performance pillars: a **trie / discrimination tree** keyed on
  index-sorted literals for one-descent subsumption checks; and a **lazy "full
  LTMS"** where `set_truth` only marks satisfied clauses `DIRTY` and consensus is
  triggered **only by retraction** (`propagate_more_unknownness`) or explicit
  completion. The engine is **IPIA** (incremental Tison); Tison's ordering
  restriction is what avoids exponential re-derivation.
- `tms_env` reads ATMS-style environment labels off prime implicates (CMS), the
  bridge to the ATMS — exponential, keep experimental.

**Port order (if/when):** trie+subsumption → `consensus` (return a *fresh* list;
drop the Lisp reused-cons hack) → IPIA → `add_formula` CNF-with-subsumption →
`tms_env`. Default to `DELAY`; the prime-implicate set can be astronomically
large. Most projects can skip this entirely — base BCP incompleteness is
normally fine.

---

## 9. Where the LTMS sits among modern systems (what to borrow)

The LTMS = clause store + BCP + per-node justification + DDB + explanation. Each
modern system re-implements one primitive (verified survey; full citations in
`refs/workflow-output.md`, gitignored):

- **SAT (DPLL/CDCL):** DPLL's inner loop **is** BCP (unit propagation). CDCL's
  clause learning = persisting nogoods (vs transient DDB); the implication graph
  = the justification network. → Use **watched literals** from the SAT world;
  delegate hard queries to **PySAT** (MIT; `solve(assumptions=...)` mirrors
  premise sets, `get_core()` mirrors DDB). Don't write a fast CDCL in Python.
- **ASP (clingo/clasp):** CDCL over grounded nogoods + nonmonotonic stable
  models — a *different semantics*; note as future direction, don't fold in.
- **Datalog provenance / Souffle proof trees / semiring provenance:** the
  justification graph as an algebraic annotation → model the `explain` API on
  minimal proof trees (why- vs how-provenance).
- **Differential dataflow / IVM (Materialize):** signed-delta propagation is the
  modern form of incremental retraction → borrow the discipline for efficient
  "retract a premise."
- **Production rules (CLIPS `logical` CE, Jess, Drools `insertLogical`):** a
  JTMS embedded in forward chaining → borrow the *assert-under-support* public
  API ergonomics.
- **Soar i-support** = a real cognitive-architecture TMS; **ACT-R** = the
  explicit non-TMS contrast (subsymbolic decay); **Cyc microtheories** = the
  ATMS multi-context idea.

**Bottom line.** Keep the LTMS's justification+BCP as the *readable, explainable,
cheaply-incremental* core (its real value), and treat PySAT/CDCL as a pluggable
heavy-query backend rather than something to reinvent.

---

## 10. Existing implementations (use as reference, not dependency)

Verified: **no faithful Python LTMS exists.** Closest references:
- `namin/biohacker` (Racket `ltms.rkt` + `cltms.rkt`) — primary external check.
- `death/bps` / QRG `bps1024.zip` — original Lisp ground truth (BPS code license
  permits derivative works *with the notice retained*).
- `jphmrst/bps` (Haskell/Scala JTMS+ATMS) — clean typed *structure* to study,
  but **restrictive license**: read, don't copy; and it has no LTMS.
- Python TMS repos are all ATMS/JTMS toys. **PyPI `pytms` is an unrelated
  transport simulator** — do not depend on it or reuse the name.

See [PLAN.md](PLAN.md) for the session-by-session build order.
