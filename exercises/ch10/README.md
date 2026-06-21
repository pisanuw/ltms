# Chapter 10 — Putting an LTMS to Work (LTRE): exercises

Worked solutions for the LTRE chapter. Statements are **paraphrased in our own
words** (originals are copyrighted); answers and code are original. Runnable
parts are in [solutions.py](solutions.py).

---

**1 (★) — Why a rule keyed on `(:TRUE (:NOT ?x))` cannot fire.**
Paraphrase: explain why a rule whose trigger is "the negation of `?x` is true"
never matches anything.
Answer: there is no node (and no datum) for a negation. `(:NOT P)` is just the
*false* label of `P`'s node, and the rule matcher indexes triggers by the
leftmost symbol of the **stored, unsigned** form. A datum is never interned under
`:NOT`, so nothing is ever filed under that pattern and the matcher finds no
candidate. The correct way to react to "`?x` is false" is a `:FALSE` trigger on
the pattern `?x` itself (in our API, `add_rule(pattern, body,
condition=Trigger.FALSE)`).

**2 (★★) — Add an XOR connective.** *(demonstrated in code)*
Paraphrase: extend the engine with exclusive-or.
Answer: XOR needs no new propagation machinery — it is a derived connective with
the CNF expansion `a ⊕ b ≡ (a ∨ b) ∧ ¬(a ∧ b)`. To "add it to the engine" you
register that rewrite in the formula normalizer (alongside `implies`/`iff`); we
show it as a one-line term macro `xor(a, b)` in `solutions.py` and confirm both
directions propagate (`p` true ⇒ `q` false, `p` false ⇒ `q` true). For an
n-ary "exactly one" use the existing `taxonomy` connective.

**3 — Abduction: what would make a fact believed.**
- **a (★★) `NEEDS`** *(demonstrated in code)*: paraphrase — given a fact and a
  desired truth value, return sets of facts that, if known, would entail it.
  Answer: one-step abduction reads directly off the clauses. For each clause that
  contains the goal literal, the clause forces the goal exactly when all of its
  *other* literals are false; that pins each of those nodes to a definite signed
  fact, giving one candidate support set. `needs()` implements this and finds
  `{a, b}` for a goal `c` constrained by `(a ∧ b) → c`. Deeper (multi-step)
  abduction recurses: replace a needed fact by *its* `needs` sets until reaching
  allowable assumptions.
- **b (★★) restrict to assumable forms**: add a pattern pool and keep only
  support sets all of whose facts match an allowed pattern — a filter over the
  sets `needs` returns.
- **c (★★) `LABDUCE`, minimum-cost explanation**: assign a cost per assumption
  class; do the recursive search of (a)+(b) and keep the explanation minimizing
  summed cost (a uniform-cost / branch-and-bound search over support sets).
  Sketch only.

**4 (★★) — More informative indirect proofs.**
Paraphrase: make `try_indirect_proof` report *why*, not just yes/no, without
adding TMS nodes or clauses.
Answer: when the assumed negation produces a contradiction, the responsible
assumptions are exactly `assumptions_of_clause` of the violated clause (minus the
assumed-negation node). Return that set as the proof's premises before retracting
the assumption and installing the nogood — it is already computed during
resolution, so no new nodes/clauses are needed.

**5 (★) — Fix the lingering closed-world assumption.**
Paraphrase: a CWA left enabled after a `With-Closed-Set` body can still cause
contradictions; add one line to prevent it.
Answer: retract the closure on exit. Our `closed_world` context manager already
does exactly this in its `finally` clause (it withdraws every fact it assumed
false), so the lingering-CWA bug cannot occur with it. The "one line" is the
unconditional retract-on-unwind.

**6 (★★★) — Detecting "the dog that didn't bark".**
Paraphrase: the CWA notices when we *gain* members of a set but not when we
*lose* information about it; suggest a discipline to catch that.
Answer: make set-membership monotonic information explicit. Maintain, per closed
set, the justification linking its closure to the specific facts it was based on,
and re-close (retract + re-assume) whenever any of those supporting facts is
itself retracted. In practice: never let a CWA outlive the facts it summarized —
treat *loss* of a constituent as a trigger to recompute the closure, not just
*gain*. (Discipline/answer only.)

**7a (★) — N-queens with DD-Search.** *(demonstrated in code)*
Paraphrase: solve N-queens using dependency-directed search.
Answer: one choice set per row (the column of that row's queen), with a nogood
for every attacking pair (same column or same diagonal). `dd_search` then
assigns rows depth-first, learning a nogood whenever a placement conflicts.
`n_queens(n)` returns all solutions; counts match the known values
(4→2, 5→10, 6→4).

**7b (★★) — Cryptarithmetic with DD-Search.**
Paraphrase: solve puzzles like SEND+MORE=MONEY.
Answer (sketch, same shape as 7a): choice sets are the digit assignments per
letter (0–9), with nogoods enforcing all-different and the column-sum/carry
arithmetic. `dd_search` over the letters with arithmetic constraints as
contradictions yields the solution; not implemented here but structurally
identical to N-queens.

**8 (★★) — "Logic puzzles" (zebra-style).**
Paraphrase: solve constraint puzzles with a scenario, clues, and questions.
Answer (sketch): model each attribute slot as a choice set (e.g. which house has
which pet), encode the clues as nogoods / implications, and run `dd_search`;
read the answer off the unique satisfying assignment. Same machinery as 7a/7b on
a richer constraint set.

---

Run the demonstrations:

```bash
python exercises/ch10/solutions.py
```
