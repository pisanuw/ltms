# Chapter 6 -- Introduction to Truth Maintenance Systems (Exercises)

Solutions to the Section 6.7 exercises in Forbus & de Kleer, *Building Problem
Solvers*. Each exercise is restated in our own words (the book text is
copyrighted) and then answered. Where an exercise can be shown concretely with
the `ltms` package, it is marked **[demonstrated in code]** and exercised by
`solutions.py`.

The chapter introduces the Justification-based TMS (JTMS): a network of
propositional **nodes** whose two-valued belief label (`IN` = currently
believed / `OUT` = not currently derivable) is maintained automatically as
**justifications** (`antecedents => consequence`, i.e. definite/Horn clauses)
and **premises/assumptions** are added and retracted. The package's `JTMS` and
the rule-engine wrapper `JTre` implement exactly this.

---

## Exercise 1 (*) -- Recording multiplication as TMS inference

**Paraphrase.** Multiplying two numbers `x` and `y` to get `z` can be treated
as an inference step. Explain how a TMS would record such a multiplication, give
a task where caching multiplications through a TMS yields a roughly 10^10
speedup, and judge whether treating multiplication as inference is generally
worthwhile.

**Answer.**

*How a TMS records the multiplication.* Treat the two inputs as TMS nodes
(`x=6`, `y=7`) and the product as a third node (`z=42`). The act of multiplying
is recorded as a single justification whose antecedents are the two input nodes
and whose consequence is the product node, with the multiplier procedure named
as the informant:

```
(x=6) , (y=7)  ==[multiply]==>  (z=42)
```

Once installed, the TMS gives three things for free:

1. **Caching.** The product node is now `IN`; asking for `6*7` again is a label
   lookup, not a re-multiplication.
2. **Dependency tracking.** `assumptions_of_node(z)` returns `{x, y}`, so the
   system knows exactly which inputs the answer depends on.
3. **Automatic invalidation (truth maintenance).** If the assumption `x=6` is
   retracted, the justification is no longer satisfied and the TMS relabels
   `z=42` to `OUT` automatically. We never recompute or manually invalidate;
   that is the whole point of a TMS.

This exercise is **[demonstrated in code]**: see `ex1_multiplication_as_inference`,
which builds the two-input/one-product justification, reads back the
dependencies, and watches the product fall `OUT` when an input is retracted.

*A task with a ~10^10 speedup.* The win comes when the *same* product is
demanded astronomically often while the inputs change rarely. A concrete
scenario: an iterative numerical / constraint solver that, on each of N outer
iterations, re-evaluates a large expression graph in which a particular
sub-product `x*y` appears, but where `x` and `y` are held fixed (they are
assumptions that only flip occasionally). Without caching, the product is
recomputed once per demand; with a TMS it is computed once and thereafter
served as an `IN`-label lookup, recomputed only on the rare retraction of `x` or
`y`. If the product is demanded ~10^10 times between input changes, the TMS does
~1 multiply where the naive scheme does ~10^10, i.e. a 10^10-fold reduction in
multiplications. More generally any setting with an extreme demand-to-change
ratio (memoized dynamic programming, repeated propagation over a stable
constraint network, a spreadsheet recalc where one cell is read by 10^10 formula
evaluations) exhibits the same effect.

*Is it a good idea on average?* No, not on average. A hardware multiply is a few
nanoseconds, whereas interning two input nodes, allocating a justification,
running belief propagation, and storing the dependency record costs orders of
magnitude more time and memory **per operation**. For the overwhelming majority
of multiplications -- which are computed once and never revisited, or whose
inputs change as often as they are read -- the bookkeeping is pure overhead and
the cache is never reused. Treating multiplication as inference only pays off in
the special regime above: very expensive or very frequently-redemanded results
over inputs that are stable and that you also need to *retract and revise*. The
deciding factor is not the multiply itself but whether you need dependency-driven
invalidation; if you do not, plain memoization is cheaper than a TMS, and if
results never repeat, even memoization loses.

---

## Exercise 2 (**) -- A justification-only TMS

**Paraphrase.** Implement the most minimal TMS that accepts only justifications
as input -- no premises, no contradictions, no assumptions. State when such a
stripped-down TMS would be useful.

**Answer.**

*What "justifications only" means.* A justification is `antecedents =>
consequence`. The minimal engine maintains, for every node, a single bit
(`IN`/`OUT`) and a current supporting justification. The rules are:

- A node is `IN` iff it has at least one justification all of whose antecedents
  are `IN`; otherwise it is `OUT`.
- Adding a justification can only flip nodes `OUT -> IN` via a monotone forward
  sweep (find a newly-satisfiable justification, label its consequence `IN`,
  repeat on that node's consequences).
- There are no premises, no assumptions, and no contradiction nodes, so there is
  no retraction and no dependency-directed backtracking -- belief only ever
  grows. (A node with a *justification that has no antecedents* would be a
  premise; the spec forbids that, so the only way anything becomes `IN` is by a
  chain bottoming out in nodes that some justification makes `IN` -- in practice
  you seed belief by directly setting one or more base nodes `IN` before
  propagating.)

A faithful minimal implementation is given below as `MiniTMS`
**[demonstrated in code]** (function `ex2_minimal_tms`). It is deliberately ~30
lines: a node has a label and an antecedent/consequence adjacency, and
`justify` runs one forward closure. It supports `seed` (mark a base node `IN`),
`justify`, and `is_in`.

```python
class MiniTMS:
    def node(self, datum) -> int: ...        # create a node, returns id, starts OUT
    def seed(self, n) -> None: ...           # mark a base node IN, propagate
    def justify(self, conseq, antecedents): ...  # add antecedents => conseq, propagate
    def is_in(self, n) -> bool: ...
```

`solutions.py` also shows the package's full `JTMS`/`JTre` doing the same job
(it is a strict superset: it *adds* premises, assumptions, retraction, and
contradiction signalling on top of justifications), and contrasts the two so the
"what's missing in the minimal version" is explicit.

*When is a justification-only TMS useful?* When belief is **monotone** -- facts
are only ever added, never withdrawn -- so you never need retraction,
assumptions, or backtracking. In that regime the only services you want from a
TMS are (a) caching: don't recompute a conclusion you already derived, and
(b) explanation: record *why* each conclusion holds (its supporting
justification / derivation chain). Concrete fits:

- A forward-chaining production system or deductive database that only asserts,
  used to answer "how was this derived?" (justification = proof step).
- Incremental, additive materialized views where you want provenance but data is
  append-only.
- The teaching/bootstrapping case: it is the smallest core that the JTMS, and
  then the LTMS, are built on top of, so it is the right thing to implement
  first when learning how a TMS works.

The moment you need to *change your mind* -- retract an input, explore
mutually exclusive assumptions, or detect and recover from a contradiction --
the justification-only TMS is insufficient and you need at least the full JTMS
(assumptions + two-phase retraction + contradiction signalling), which is what
the `ltms` package provides.

---

## Running

```bash
# from the repository root
. .venv/bin/activate
python exercises/ch06/solutions.py
```

This prints a dict of labeled results for the two demonstrated exercises.
