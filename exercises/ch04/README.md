# Chapter 4 — Pattern-Directed Inference Systems (TRE / LTRE)

Study solutions for the exercises in Forbus & de Kleer, *Building Problem
Solvers*, chapter 4. Exercise statements below are **paraphrases** (the original
text is copyrighted), each followed by an answer. The difficulty stars from the
book are kept as a rough guide.

This chapter's machinery (the `Tre` pattern-directed forward chainer and its
truth-maintained sibling `LTRE`) lives in the `ltms` package, so most exercises
can be **demonstrated in code**. Runnable demonstrations are in
[`solutions.py`](./solutions.py); each is flagged below as **[demonstrated in
code]**.

Run the demonstrations:

```bash
# from the repository root
. .venv/bin/activate
python exercises/ch04/solutions.py
```

---

## Exercise 1 (*) — Why is order-independence useful? **[demonstrated in code]**

*Paraphrase:* Explain why it matters that a pattern-directed inference system
reaches the same conclusions regardless of the order in which facts and rules
arrive.

**Answer.** Order-independence (confluence) means the set of derivable facts
depends only on the database contents and rule set, not on the asserting
sequence or rule-firing order. This matters because:

- **Correctness / predictability.** The author of a rule set does not have to
  reason about interleavings; the same knowledge base always yields the same
  closure. Debugging is local: a missing conclusion is a missing rule or fact,
  never an accident of timing.
- **Incremental and modular assertion.** Facts can stream in from many sources
  (a parser, a user, other rules) in any order, and rules can be loaded at any
  time, yet still see all relevant data. TRE guarantees this by funneling both
  "new fact meets old rules" and "new rule meets old facts" through one match
  point (`_try_rule_on`), so a rule added *after* its triggering fact is still
  tested against that fact (see `add_rule`, which loops over existing facts).
- **Composability of knowledge sources.** Independent rule modules can be merged
  without worrying about load order — a prerequisite for the blackboard idea in
  exercise 7.

The trade-off is that order-independence forbids relying on firing order for
control (e.g. cut-like pruning); control must be expressed declaratively
(tests, conditions) instead. The code demo builds the same fact+rule in two
orders (rule-then-fact and fact-then-rule) and confirms identical conclusions.

---

## Exercise 2 — Solve a logic-textbook problem **[demonstrated in code]**

*Paraphrase:* Take a problem from a logic textbook and (a) solve it by hand in a
KM\*-style natural-deduction system, then (b) encode it for the natural-deduction
rule set and see whether the prover (THE) can derive the result.

**Chosen problem (constructive dilemma):** From `A ∨ B`, `A → C`, `B → C`,
derive `C`.

**(a) By hand (KM\*-style natural deduction).**

```
1. A ∨ B            premise
2. A → C            premise
3. B → C            premise
4. | A              assumption (case 1)
5. | C              → -elim (modus ponens) 2,4
6. | B              assumption (case 2)
7. | C              → -elim 3,6
8. C                ∨ -elim (proof by cases) 1, 4-5, 6-7
```

The crux is `∨`-elimination: we must show `C` follows from *each* disjunct
separately.

**(b) In the implemented prover.** Plain LTRE assertion + Boolean constraint
propagation (BCP) already does **modus ponens** for free: asserting `man(socrates)`
and `man(x) → mortal(x)` immediately makes `mortal(socrates)` true. But the
constructive dilemma is **not** a unit-propagation consequence (BCP alone leaves
`C` unknown, as the demo shows: `c_before_indirect_proof = False`). Deriving `C`
requires reasoning by cases, which the package supplies as
`try_indirect_proof`: it assumes `¬C`, runs propagation, finds the resulting
clause set unsatisfiable, and concludes `C`. The demo confirms
`c_proved_by_cases = True` and afterwards `c_now_true = True`.

This is exactly the BPS lesson: a forward chainer with TMS gives you the easy
deductions (and-elim, modus ponens) directly; the harder rules requiring case
splits or assumptions need the explicit proof procedures.

---

## Exercise 3 — `unify` and full unification **[demonstrated in code]**

### (a) (*) How does the naive `unify` fail on `(Foo ?x ?x)` vs `(Foo ?x ?x)`?

*Paraphrase:* Explain why the simplistic unifier mishandles patterns where the
same variable (or variables on both sides) recurs, using the example of two
patterns each shaped `(Foo ?x ?x)`.

**Answer.** A "one-way" matcher (the kind used for matching a *pattern* against a
*ground fact*) binds variables on only one side and never records that a variable
on the *other* side must take a value. The BPS bug is that such a matcher treats
the second pattern's variables as constants. Two failure modes:

1. **Shared variable not enforced.** Matching `(Foo ?x ?x)` against another
   `(Foo ?x ?x)` where the right side's `?x` is *also* a variable: a one-way
   matcher would bind the left `?x` to the right `?x` on the first argument, then
   on the second argument it sees left `?x` already bound (to right `?x`) and
   "succeeds" without ever checking/propagating that the two positions of the
   right pattern must agree. With genuinely distinct variables `(Foo ?y ?z)`, a
   broken matcher would bind `?x ↦ ?y` then `?x ↦ ?z` and either overwrite
   silently or fail spuriously — instead of recognizing that `?y` and `?z` must
   be **the same** variable.
2. **No occurs-check / no chaining**, so it cannot tell `?x = ?y, ?y = ?z`
   collapses to one equivalence class.

### (b) (\*\*) Implement `full-unify`.

**Answer.** Full (two-sided) unification is exactly Robinson's algorithm with an
occurs-check, and it is **already implemented** in `ltms.unify.unify`
(`src/ltms/unify.py`). Key properties the demo exhibits:

- `unify(('Foo',?x,?x), ('Foo',?y,?z))` returns `{?x: ?y, ?y: ?z}`; substituting
  back yields `('Foo', ?z, ?z)` — the two right-hand variables are forced equal,
  which is the case a one-way matcher gets wrong.
- `unify(('Foo',?x,?x), ('Foo','a','b'))` correctly **fails** (`?x` cannot be both
  `a` and `b`).
- `unify(('Foo',?x,?x), ('Foo','a','a'))` succeeds with `?x ↦ a`.
- `unify(?x, ('g', ?x))` **fails** the occurs-check (no infinite/cyclic term).

So the package's substrate already provides the `full-unify` the exercise asks
the reader to write; the demo verifies all four cases. (Note: BPS deliberately
uses the *one-way* matcher in the rule engine because database facts are ground,
which is why this distinction is an exercise rather than a default.)

---

## Exercise 4 (\*\*) — `multi-fetch` **[demonstrated in code]**

*Paraphrase:* Write `multi-fetch`, which takes several patterns and returns the
sets of assertions matching them (with bindings shared consistently across the
patterns).

**Answer.** `multi_fetch(engine, patterns)` in `solutions.py` computes the
relational **join**: it threads a list of binding environments through the
patterns one at a time, and for each environment substitutes the bindings so far
into the next pattern, then unifies the partially-grounded pattern against every
fact in that pattern's dbclass bucket, keeping only consistent extensions. The
result is every environment under which *all* patterns simultaneously match.

Demo: with facts `parent(ann,bob)`, `parent(cy,dee)`, `employed(ann)`,
`employed(ed)`, the patterns `[(parent ?x ?y), (employed ?x)]` yield the single
joint solution `?x=ann, ?y=bob` (the only person who is both a parent and
employed). This reuses the engine's `get_dbclass` indexing so it only scans
relevant facts, exactly as BPS intends.

---

## Exercise 5 (\*\*) — `show-rule` **[demonstrated in code]**

*Paraphrase:* Write `show-rule`, which looks a rule up by the integer in its
counter field and prints a detailed description, showing the trigger and the
environment separately.

**Answer.** `show_rule(engine, counter)` in `solutions.py` scans the engine's
`dbclass_table`, finds the `Rule` whose `counter` matches, and prints its
trigger pattern, the firing condition (`INTERN` / `TRUE` / `FALSE`), the seed
environment (shown separately from the trigger, as required), and the dbclass it
is indexed under. The `Rule` dataclass exposes exactly these fields
(`counter`, `trigger`, `condition`, `environment`, `dbclass`), so the public
objects returned by `add_rule` carry everything needed. Demo output:

```
Rule #1
  trigger:     ('implies', ?x, ?y)
  fires when:  TRUE
  environment: (empty)
  indexed under dbclass: implies
```

---

## Exercise 6 — More efficient AND/BICONDITIONAL introduction

### (a) (*) Lazy conjunct lookup **[demonstrated in code]**

*Paraphrase:* Rewrite AND-INTRODUCTION and BICONDITIONAL-INTRODUCTION so they
attempt to establish the second constituent only after the first has been
proved, avoiding wasted work when the first is unprovable.

**Answer.** The fix is to use a **nested (conjunctive) rule**: install an outer
rule that triggers on (a proof of) the first constituent, and only *inside its
body* install the rule that watches for the second. If the first constituent is
never established, the second is never even looked up.

`demo_lazy_and_introduction` implements this. The outer rule fires on
`proved(a)`; only then does it add the inner rule watching `proved(b)`; only when
both fire is the conjunction asserted. The demo runs it both ways:

- first conjunct unprovable → the second is examined **0** times, no conjunction
  produced;
- first conjunct holds → the second is examined **1** time and the conjunction is
  asserted.

The same nesting works for BICONDITIONAL-INTRODUCTION (prove `A→B` first, only
then look for `B→A`). This mirrors BPS's recommendation to write the rule as two
chained triggers rather than two independent ones.

### (b) (*) What assumption do the lazy versions rely on?

*Paraphrase:* The optimized rules make an important assumption about the rule set
as a whole — identify it and say how it could be violated.

**Answer.** The lazy ordering assumes the work to establish the first constituent
is **independent of** (and not cheaper after) establishing the second — i.e. the
two sub-proofs do not help each other, so it is always at least as good to do the
"first" one first. More precisely it assumes:

1. **No cross-dependence / no synergy.** Proving the second constituent must not
   be a prerequisite for, or a shortcut to, proving the first. If proving `B`
   would in fact make `A` easy (or even possible), then refusing to look at `B`
   until `A` is done can lose the proof or do strictly more work.
2. **Cost ordering is stable.** It assumes the first constituent is the cheaper /
   more-likely-to-fail one to test first; if the first is actually the expensive
   one, the optimization can be a pessimization.
3. **Forward-chaining monotonicity.** It assumes that whether `A` is provable
   does not change once we start (no retraction reordering), so "A not yet proved"
   safely means "do not bother with B."

**How it is violated:** suppose another rule derives `A` *from* `B`
(`B → A`). Then a fact set that supports `B` (and hence `A`) would still let a
*symmetric* AND-INTRODUCTION conclude `A ∧ B`, but the lazy version, seeing `A`
not yet proved and never examining `B`, never triggers the chain that would have
produced `A` in the first place — so it misses the conjunction. The optimization
is only sound when the rule set has no such ordering-sensitive interactions,
which is the global property the exercise is pointing at.

---

## Exercise 7 — Blackboard systems on TRE knowledge sources

### (a) (*) Two TRE design decisions that must change

*Paraphrase:* Identify two design choices in TRE that would have to be changed
before TRE-based problem solvers could serve as blackboard knowledge sources,
and explain the problems they cause.

**Answer (two of several valid choices):**

1. **Run-to-quiescence control (`run_rules` drains the whole queue).** TRE's
   control loop fires every queued rule until the agenda is empty, with no
   external scheduler and no resource limits. Blackboard systems need
   **opportunistic, interruptible control** — a controller that picks *which*
   knowledge source runs next based on the current blackboard state and a budget,
   and can preempt one KS to run a more promising one (real-time concern). A KS
   that always runs to completion cannot yield, cannot be prioritized, and cannot
   meet deadlines.

2. **A single private, monotonic, non-retractable database per engine.** TRE
   facts are global within one engine, never retracted, and there is no notion of
   *who* posted a fact or *which level* of a solution it belongs to. Blackboards
   need a **shared, structured, multi-level workspace** that all KSs read and
   write, with provenance and the ability to revise/remove hypotheses. Plain TRE
   gives no way for separate KSs to communicate selectively or to retract
   superseded hypotheses (the latter really wants the JTMS/LTRE layer from later
   chapters).

(Other defensible answers: LIFO agenda discipline gives no control over *order*
of attention; rule indexing by leftmost symbol couples KSs to a shared vocabulary;
no event/trigger mechanism for "blackboard changed.")

### (b) (\*\*\*) Implement a blackboard shell **[partially demonstrated in code]**

*Paraphrase:* Build a shell for blackboard systems using an extended TRE as the
basis for knowledge sources.

**Answer.** A full shell (scheduler with priorities, preemption, a structured
multi-level blackboard, KS activation records) is beyond a short demo, but
`demo_blackboard_sketch` shows the essential architecture with the public API:

- Each **knowledge source** is its own `Tre` engine with its own rules
  (KS1 turns observations into hypotheses; KS2 confirms hypotheses that have
  corroborating evidence).
- A **shared blackboard** is a list that KS rule bodies post to.
- An explicit **controller / scheduler** cycles the KSs and moves new blackboard
  entries from one KS to the next between activations — this explicit control
  loop is precisely the design decision that plain TRE's `run_rules` lacked
  (answer 7a).

The demo posts `observed(fire)`, lets KS1 derive `hypothesis(fire)`, copies that
onto KS2's database alongside `evidence(fire)`, and KS2 produces
`confirmed(fire)`. A production shell would add: priority queues of pending KS
activations, a budget per cycle, change-events that wake KSs, and retraction of
disconfirmed hypotheses (best done by swapping the `Tre` substrate for the
LTMS-backed `LTRE`).

---

## Summary of code coverage

| Ex | Topic | Status |
|----|-------|--------|
| 1 | Order-independence | demonstrated (both arrival orders agree) |
| 2 | Logic problem (modus ponens + constructive dilemma) | demonstrated (BCP + `try_indirect_proof`) |
| 3 | Full unification, both-sides variables | demonstrated (already in `ltms.unify`) |
| 4 | `multi-fetch` (pattern join) | demonstrated |
| 5 | `show-rule` by counter | demonstrated |
| 6a | Lazy AND/BICONDITIONAL introduction | demonstrated (nested rules) |
| 6b | Assumption it relies on | paper answer |
| 7a | TRE design decisions to change | paper answer |
| 7b | Blackboard shell | sketched in code + paper answer |
