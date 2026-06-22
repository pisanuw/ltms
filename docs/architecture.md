---
title: Architecture
nav_order: 3
---

# Architecture

The system is built **bottom-up**, each layer adding exactly one capability and
remaining small enough to read in one sitting:

```
terms + unification        shared substrate: s-expression terms, occurs-checked unify
   │
TRE                        pattern-directed forward chaining (belief = "in the database")
   │
JTMS + JTRE                justification-based belief: IN/OUT, two-phase retraction
   │
LTMS core                  belief over clauses via Boolean Constraint Propagation
   │
LTRE                       reasoning engine: assert!/assume!/retract!, belief-conditioned rules
   │
advanced facilities        indirect proof, closed-world assumptions, dependency-directed search
   │
CLTMS                      optional logical completeness via prime implicates
```

The thread through all of it: **separate *what* you believe from *why*.** Once
inferences record their justifications, the system can explain itself, retract a
premise and automatically un-derive its consequences, and search without losing
reusable work.

## Modules at a glance

| Layer | Module | What it provides |
|---|---|---|
| Terms + unification | [`terms`](https://github.com/pisanuw/ltms/blob/main/src/ltms/terms.py), [`unify`](https://github.com/pisanuw/ltms/blob/main/src/ltms/unify.py) | s-expression terms, occurs-checked unification |
| TRE | [`tre/`](https://github.com/pisanuw/ltms/tree/main/src/ltms/tre/) | pattern-directed forward chaining (no belief revision) |
| JTMS + JTRE | [`jtms`](https://github.com/pisanuw/ltms/blob/main/src/ltms/jtms.py), [`jtre`](https://github.com/pisanuw/ltms/blob/main/src/ltms/jtre.py) | justification-based belief, IN/OUT, two-phase retraction |
| LTMS core | [`core`](https://github.com/pisanuw/ltms/blob/main/src/ltms/core.py), [`normalize`](https://github.com/pisanuw/ltms/blob/main/src/ltms/normalize.py) | clausal BCP, assumptions, nogoods, CNF |
| LTRE | [`ltre`](https://github.com/pisanuw/ltms/blob/main/src/ltms/ltre.py) | reasoning engine: `assert!`/`assume!`/`retract!`, belief-conditioned rules |
| Facilities | [`indirect`](https://github.com/pisanuw/ltms/blob/main/src/ltms/indirect.py), [`cwa`](https://github.com/pisanuw/ltms/blob/main/src/ltms/cwa.py), [`dds`](https://github.com/pisanuw/ltms/blob/main/src/ltms/dds.py) | indirect proof, closed-world assumptions, dependency-directed search |
| Completeness | [`cltms`](https://github.com/pisanuw/ltms/blob/main/src/ltms/cltms.py) | prime implicates / `complete()` (optional logical completeness) |
| Watched literals | [`watched`](https://github.com/pisanuw/ltms/blob/main/src/ltms/watched.py) | `WatchedLTMS`, a SAT-style 2-watched-literals BCP engine |
| Explanation | [`explain`](https://github.com/pisanuw/ltms/blob/main/src/ltms/explain.py) | `why_node`, `explain_node` (well-founded proofs) |
| File DSL | [`dsl`](https://github.com/pisanuw/ltms/blob/main/src/ltms/dsl.py) | read world models from `.kb` files, separate from Python |

## The ideas, in plain language

### Terms and unification

One Robinson-style unifier is shared by every layer. Terms are s-expressions
(Python tuples); a `Var` is a logic variable; bindings are a dict copied on
extend. `unify(a, b, bindings)` returns the extended bindings or a `FAIL`
sentinel — and because an *empty* binding set is a legitimate success, success is
tested against `FAIL`, never by truthiness. Binding a fresh variable is gated by
an **occurs-check** so `?x = (F ?x)` is rejected.

### TRE — pattern-directed inference

The minimal forward chainer, where belief simply means "present in the database."
Facts and rules are **car-indexed** by their leftmost symbol, so only facts and
rules in the same bucket are ever unified. Asserting a *new* fact queues the rules
in its bucket; defining a rule back-tests it against existing facts — so arrival
order does not matter (a bidirectional incremental join). Rule bodies are plain
Python callables receiving the bindings, which keeps everything `eval`-free.

### JTMS — justification-based truth maintenance

The simplest TMS, worth building first because the LTMS reuses its patterns. A
node is labelled `IN` or `OUT`, where **`OUT` is not the same as false** — it
means "not currently derivable." A justification is a definite (Horn) clause
`antecedents ⇒ consequence`. The subtle part is **retraction, which is strictly
two-phase**: first mark `OUT` everything whose current support flowed through the
retracted node, and only *then* search for alternative support. Interleaving the
two phases would admit ill-founded circular support (`B` because `C`, `C` because
`B`) — the precise bug the split exists to prevent.

### LTMS core — Boolean Constraint Propagation

The heart of the project: a sound-but-incomplete propositional reasoner. It
generalizes the JTMS — the engine supplies **arbitrary clauses** (and whole
formulas via `add_formula`, which CNF-normalizes), not just Horn rules — and
**negation is just the label**, so there is no separate negation node. A node is
three-valued: `UNKNOWN` / `TRUE` / `FALSE`.

Propagation is driven by two **incremental per-clause counters** maintained as
node labels change, so the hot path never rescans a clause's literals:

- **`pvs`** ("potential violators") counts the literals not yet labelled opposite
  to their sign.
- **`sats`** counts the literals currently satisfying the clause.

From these: a clause is **violated** when `pvs == 0`, **unit/forcing** when
`pvs == 1` (force the lone `UNKNOWN` literal), and **satisfied** when `sats > 0`.
A satisfying literal still counts toward `pvs`, because a later retraction could
turn it back into a violator — so satisfied clauses are never discarded.
Contradictions are **deferred**: violated clauses are accumulated during
propagation and dispatched only at the end of the top-level operation, because
raising mid-BCP would corrupt half-updated counters. Retraction mirrors the JTMS
two-phase split (`propagate_unknownness` then `find_alternative_support`).

This BCP is **unit-resolution only**, so it is sound but deliberately *not*
complete: it leaves some entailed literals `UNKNOWN` (`{x∨¬y, x∨y}` does not force
`x`) and misses some contradictions. That is expected and acceptable — full
completeness is the optional CLTMS layer.

### LTRE — the reasoning engine

Forward-chaining, pattern-directed inference where **the engine does the rule
matching (universal instantiation) and the LTMS does all the propositional
reasoning**. Each ground proposition interns to one node (the stored form is
always unsigned, so `P` and `(not P)` share a node). `assert!` translates a
formula directly into clauses; `assume!` builds a **guard node** and installs
`guard ⇒ formula` so the clauses can be switched off by retracting the guard.
Rules can trigger on a datum merely existing (`:INTERN`) or on it becoming `:TRUE`
/ `:FALSE`; a rule that matches before the label exists is **parked** on the node
and fired later by an LTMS→LTRE enqueue bridge. Multi-condition rules nest, giving
a cartesian-product join.

### Advanced facilities

All three exploit the contradiction-handler stack:

- **Indirect proof** assumes `¬fact`, runs the rules, and if that produces a
  contradiction implicating the assumption, retracts it and records a nogood that
  now justifies `fact`.
- **Closed-world assumptions** close a predicate by treating "not currently
  derivable" as false, with a handler that unwinds cleanly if a closed assumption
  is later invalidated.
- **Dependency-directed search** explores mutually-exclusive choice sets
  depth-first, and on a contradiction throws the surviving assumptions back and
  records a nogood so the same dead end is never re-entered (backjumping, not
  chronological backtracking).

### Completeness (CLTMS)

Optionally makes BCP logically complete by adding **prime implicates** — clauses
that are logically redundant but let unit propagation reach conclusions it
otherwise could not — computed via **consensus (resolution)**. It is gated by a
flag defaulting to *delay* (accumulate, then run on an explicit `complete()`),
because the prime-implicate set can be astronomically large. Most uses can skip
this entirely; base-BCP incompleteness is normally fine.

### Watched literals

[`WatchedLTMS`](https://github.com/pisanuw/ltms/blob/main/src/ltms/watched.py) is
an alternative BCP engine using the SAT world's **2-watched-literals** scheme
instead of per-clause counters. It is validated by differential testing to give
identical forced labels and contradictions as the counter-based LTMS over random
CNF, and to be sound against PySAT's Minisat22. The counter-based core remains the
default because it stays faithful to the book.

## Design decisions

- **Pure Python, src layout, instance-based engines** (no global state); terms are
  tuples, variables are a `Var` class, bindings are dicts, and a `FAIL` sentinel
  distinguishes failure from empty success.
- **Rule bodies are Python callables**, never `eval`'d strings.
- **Soundness over raw speed.** For genuinely hard SAT queries, delegate to PySAT
  rather than reinventing a fast CDCL solver in Python — the value of this code is
  the *readable, explainable, cheaply-incremental* justification + BCP core.

For a deeper engineering digest see
[STUDY-NOTES.md](https://github.com/pisanuw/ltms/blob/main/STUDY-NOTES.md), and for
the session-by-session build order see
[PLAN.md](https://github.com/pisanuw/ltms/blob/main/PLAN.md).
