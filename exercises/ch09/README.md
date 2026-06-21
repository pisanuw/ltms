# Chapter 9 — Logic-Based Truth Maintenance Systems: exercises

Worked solutions for the LTMS chapter. Problem statements are **paraphrased in
our own words** (the originals are copyrighted); the answers and code are
original. Runnable demonstrations live in [solutions.py](solutions.py) and are
exercised by the test suite (`pytest tests/test_exercises.py`).

Difficulty is shown as the book's star rating (★ = easy … ★★★★ = research-level).

---

**1 (★) — Why no extra "all true ⇒ ⊥" justification for a disjunctive clause.**
Paraphrase: when encoding `A ∨ B ∨ C`, why is it enough to record the clause
itself, without adding a separate justification?
Answer: in an LTMS a clause *is* the constraint. The single clause already
licenses BCP in every direction: if any two literals are known false the third
is forced, and if all three are false the clause is violated (a contradiction).
There is nothing a separate justification node would add — negation is carried
by the node label, not by extra nodes, so the clause alone captures the full
propositional content.

**2 (★) — With all nogoods present, search is backtrack-free.**
Paraphrase: argue that if every nogood is recorded, dependency-directed search
never has to backtrack.
Answer: a nogood is a clause forbidding an assumption combination known to be
inconsistent. If *all* nogoods are present, then whenever a partial assignment
can still be extended to a solution, no recorded nogood is violated, so BCP
never derives a contradiction from it; and whenever an extension is doomed, the
relevant nogood fires *as a unit* and forces the search away from the bad choice
before it is taken. Every choice BCP leaves open is therefore part of some
solution, so the search descends to a solution without ever undoing a committed
choice. (The catch, of course, is that the set of all nogoods can be
exponential — this is why we learn them lazily.)

**3 (★) — Clause blow-up of a big `add-formula`.** *(demonstrated in code)*
Paraphrase: count the clauses produced by converting a large disjunction of
conjunctions (a fault model with 13 disjuncts) to CNF, and judge whether that is
practical.
Answer: CNF of a disjunction of conjunctions is the cross product — one clause
per way of picking a conjunct from each disjunct — so the raw count is the
product of the disjuncts' sizes. The 13 disjuncts have sizes
`[4,4,4,4,4,4, 2, 3,3,3,3,3,3]`, giving `4⁶ · 2 · 3⁶ = 5,971,968` clauses.
That is plainly impractical: it is exactly the motivation for the
completeness/no-CNF techniques of Chapter 13. `ex3_clause_count` verifies the
cross-product rule on a small disjoint case and reports the full count.

**4 (★★) — CNF size of a TAXONOMY over n nodes.** *(demonstrated in code)*
Paraphrase: how many conjuncts does an "exactly one of n" taxonomy become in
CNF?
Answer: `n(n-1)/2 + 1`. "Exactly one" = "at least one" (a single n-literal
disjunction) **and** "no two together" (one 2-literal clause per pair, i.e.
`C(n,2)` clauses). `ex4_taxonomy_cnf_size` confirms this for n = 2…7 against our
`normalize`.

**5 (★) — All implicates ⇒ BCP is complete.** *(demonstrated in code)*
Paraphrase: prove that BCP becomes logically complete once every implicate is in
the database.
Answer: BCP is unit resolution. A literal `ℓ` is entailed iff the empty clause is
derivable from the clauses together with `¬ℓ`; by completeness of resolution
that derivation exists, and its final step is the resolution producing either
the unit `ℓ` (a prime implicate) or `□`. If all implicates are already present,
that unit/empty clause is already in the database, so a *single* BCP step forces
`ℓ` (or signals the contradiction). Hence with all implicates present BCP forces
every entailed literal and detects every inconsistency — it is complete.
`ex5_completeness` shows `complete()` (a) forcing `x` for `{x∨¬y, x∨y}` and
(b) detecting the unsatisfiable four-clause set on `{x,y}`.

**6 (★★) — Let the user justify / enable / retract whole clauses.**
Paraphrase: extend the LTMS so clauses themselves can be switched on and off.
Answer (design, realized via the existing API): give each switchable clause a
fresh *guard* assumption node `g` and install `g ⇒ clause` instead of the bare
clause (for `A∨B∨C`, install `¬g ∨ A ∨ B ∨ C`). Enabling/retracting the clause
is then just `enable_assumption(g, TRUE)` / `retract_assumption(g)`; while `g`
is out, the guard literal is non-false so the clause can never fire or be
violated. This is exactly the mechanism our `LTRE.assume` already uses for
compound formulas (the guarded `(implies N_F formula)`), so "justifiable
clauses" need no core change — only the guard convention.

**7a (★) — Why stopping BCP at the first violated clause is wrong (as written).**
Paraphrase: what breaks if BCP halts the moment it sees one violated clause?
Answer: our `set_truth` updates the per-clause counters *as it goes*. If we throw
out of BCP at the first violation, later clauses never get their counters
decremented for the assignment in progress, so the engine is left in a
half-updated, inconsistent state; a subsequent retraction then restores the
counters incorrectly and belief is corrupted. That is why our engine *records*
each violated clause and keeps propagating, dispatching contradictions only once
the operation has finished (the deferred-dispatch discipline).

**7b (★★★) — Redesign BCP to stop at the first violation, correctly.**
Answer (design): keep a single "earliest violated clause" field instead of a
list, and finish the counter bookkeeping for the current `set_truth` before
unwinding (do not abandon the loop mid-update). On the next top-level operation,
check that field first. The watched-literals engine (`ltms/watched.py`) is the
natural home for this: a conflict there is detected by a single clause whose two
watches are both false, and the propagation queue can be drained/cleared
atomically, so stopping early leaves no half-updated counters to repair.

**7c (★★) — Avoid consing the to-check queue.**
Answer: our queue is a Python `list` reused per operation (amortized O(1)
append/pop, cleared between operations) rather than freshly allocated cons cells;
the watched-literals engine removes the per-assignment scan entirely by only
re-examining the clauses on a falsified literal's watch list. Either way no
per-clause allocation happens in the hot path.

**8 (★★★) / 12 (★★★★) — BCP / a full LTMS without expanding to CNF.**
Paraphrase: run constraint propagation directly on formulas, substituting known
truth values and simplifying, instead of converting to clauses.
Answer (design): represent each formula as a tree and keep, per formula, a count
of undetermined leaves. When a leaf becomes known, substitute `TRUE`/`FALSE` and
simplify bottom-up (`x ∧ TRUE → x`, `x ∨ TRUE → TRUE`, etc.). If a formula
simplifies to a single undetermined literal, force it; if it simplifies to
`FALSE`, signal a contradiction; record which formula forced the literal for
well-founded support. This is "formula-BCP", which is strictly stronger than
clausal BCP on the CNF and avoids the blow-up of Exercise 3 — at the cost of a
more complex propagator. Not implemented here (we use the CNF path); flagged as
the natural follow-on.

**9 (★★) — Track whether a label is fixed or variable.**
Answer: a node's label is *fixed* iff its well-founded support bottoms out only
in premises (unit clauses / non-retractable support) — equivalently
`assumptions_of_node(n)` is empty. Cache a `fixed` flag, recomputed lazily from
support, and prefer a fixed label when choosing among supports. We already
expose the needed primitive (`assumptions_of_node`); the flag is a thin cache
over it.

**10 (★★) — Garbage-collect permanently-satisfied clauses.**
Answer: a clause is permanently satisfied when one of its literals is
permanently true — i.e. that literal's node is fixed (Exercise 9) and satisfies
the clause. Such a clause can never again become unit or violated, so it can be
removed from the node clause-lists and discarded. A periodic sweep over
satisfied clauses checking `fixed` membership reclaims them safely.

**11 (★★) — An LTMS that encodes clauses the JTMS way.**
Answer: emulate each n-literal clause with the JTMS's definite-justification
machinery by adding, for every literal, a justification deriving that literal
from the negations of the others (the n "rotations" of the clause). With a
node-per-sign (P and ¬P) encoding this reproduces clausal BCP using only Horn
justifications — at n× the justifications and double the nodes, which is exactly
why the LTMS uses clauses directly. (Our JTMS in `ltms/jtms.py` supports this
encoding; the LTMS exists to avoid its overhead.)

---

Run the demonstrations:

```bash
python exercises/ch09/solutions.py
```
