# Chapter 18 — Symbolic Relaxation Systems: exercises (analysis)

The relaxation system of this chapter (WALTZER — symbolic constraint
propagation over cells with finite value domains, plus the temporal/interval
database) is **not implemented** in this package, so these are written analyses.
Problem statements are **paraphrased** (originals are copyrighted); the answers
are original.

---

**1 (★★) — Explain why a cell value was excluded or forced.**
Paraphrase: write `explain-exclusion` that produces a readable account of why a
value was eliminated from (or forced into) a cell, with an optional depth bound.
Answer: record, on each value-elimination, the constraint and the neighboring
cell-states that triggered it (its "support") — the same well-founded-support
idea this whole book builds on. `explain-exclusion(cell, value, depth)` then
walks that support graph backward from the elimination, emitting one step per
constraint firing, and stops at `depth` levels (or at user-supplied premises).
Bounding the depth keeps explanations of long propagation chains readable.

**2 — Add a JTMS to WALTZER for a detailed trace.**
- **a (★★) conventions.** Represent each *cell = value* possibility as a JTMS
  node; a constraint that rules out a value installs a justification whose
  antecedents are the neighbor cell-value nodes responsible. "Value v is still
  possible for cell c" is then an OUT node for "v excluded from c"; belief
  revision falls out of the JTMS automatically.
- **b (★★) efficiency.** With `k` cells and domain size `d`, there are up to
  `k·d` nodes. Each constraint between two cells can, in the worst case, justify
  the exclusion of each of the `d` values of one cell from each of the `d`
  values of the other, i.e. `O(d²)` justifications per constraint edge, so
  `O(E·d²)` justifications for `E` edges. That quadratic-in-domain blow-up is
  the price of a full trace; it is why production relaxation systems trace
  selectively.

**3 — Saving and comparing network states; breadth-first search.**
- **a (★) save states.** Snapshot each cell's current value-domain (the set of
  still-possible values) under a name; restoring reinstalls those domains.
- **b (★) diff states.** Compare two snapshots cell-by-cell, returning the cells
  whose domains differ and how (values gained/lost) in a machine-readable form.
- **c (★★) breadth-first `search-network`.** Replace the depth-first completion
  search with a queue of partial networks; expand the shallowest first. BFS
  finds a shallowest solution and avoids deep dead-ends, but stores many partial
  states at once (memory heavy); DFS uses little memory but can chase long dead
  branches. Which wins depends on solution depth vs branching — BFS for shallow
  solutions with wide search, DFS for deep narrow ones.

**4 (★★) — An impossible figure given to scene analysis.**
Paraphrase: what do you expect / want / actually get when the line-labeling
scene analyzer is handed an impossible figure?
Answer: *expect/should:* propagation drives some cell's value-domain empty —
i.e. no consistent labeling exists — and the system should report "no
interpretation" (an empty domain is the relaxation analogue of a contradiction).
*Actually:* a pure arc-consistency relaxer may instead reach a non-empty but
globally inconsistent fixpoint (arc consistency is incomplete, like BCP), so it
can fail to *prove* impossibility without an added search/backtracking step.

**5 (★) — Make the temporal-database interface robust.**
Paraphrase: the `interval` / `t-assert` interface is fragile; identify the
problems and rewrite them.
Answer: typical fragilities are no validation of endpoints (start after end),
silent acceptance of duplicate or contradictory interval relations, and no
detection of relation inconsistency on assertion. Robust versions validate
inputs, normalize relations to a canonical form, and run the transitivity
closure on assert so contradictions surface immediately rather than later.

**6 (★★★) — Run rules when temporal conditions hold.**
Paraphrase: let users attach rules that fire when particular temporal relations
become true (e.g. two operations needing the same machine would overlap).
Answer: index pattern-triggered rules by the temporal relation they wait on;
when the transitivity closure newly establishes a relation between two intervals,
wake the rules whose patterns match — the temporal analogue of the
pattern-directed rule engines earlier in the book, with the interval network
playing the role of the fact database.

**7 (★★) — Merge Allen's `starts`/`finishes`/`during` into `within`.**
Answer: (a) the transitivity table shrinks — collapsing three relations into one
removes rows/columns and merges their entries, so it is smaller and its
compositions are coarser (a composition that used to yield a specific one of the
three now yields `within`). (b) Reasoning becomes weaker: you can no longer
distinguish sharing an endpoint from being strictly inside, so some inferences
Allen's full algebra supports are lost. It is a precision-for-compactness trade.

**8 (★★★) — Implement Randell & Cohn's spatial vocabulary in WALTZER.**
Paraphrase: build the qualitative-spatial relations of Randell and Cohn on top
of the WALTZER constraint machinery and exercise it on their published examples.
Answer (analysis/design): the target is RCC-8 (region connection calculus), the
topology-flavored analogue of Allen's temporal algebra — a set of eight
jointly-exhaustive, pairwise-disjoint base relations between regions:
disconnected (DC), externally connected (EC), partial overlap (PO), equal (EQ),
tangential and non-tangential proper part (TPP, NTPP) and their converses
(TPPi, NTPPi). Implementation mirrors the Allen interval code in this chapter:
(1) make each ordered region pair a WALTZER cell whose value-domain is the
subset of the eight relations still possible; (2) supply RCC-8's published
**composition (transitivity) table** (an 8×8 table of relation-sets) as the
constraint that, given R(a,b) and R(b,c), prunes the domain of R(a,c) to the
table entry's set; (3) propagate to arc/path consistency exactly as the temporal
network does. Asserting a relation narrows a cell to a singleton; propagation
either reaches a fixpoint (consistent scene) or empties a domain (inconsistent
spatial layout). Test it on the Randell/Cohn worked examples (e.g. an egg inside
a cup, then taken out) by asserting the relation sequence and checking the
inferred relations match. Note that, as with Allen and with BCP, path
consistency is *incomplete* for RCC-8 in general, so global consistency may need
backtracking search layered on top of the relaxation step.

**9 (★★★★) — Reference intervals that scale to very large temporal databases.**
Paraphrase: design a reference-interval scheme so that temporal reasoning stays
tractable as the number of stored intervals grows very large.
Answer (analysis/design): the scaling problem is that naive Allen-style
reasoning is quadratic-to-cubic — every pair of intervals can carry an explicit
relation (`O(n²)` storage) and computing/maintaining the path-consistency
closure costs `O(n³)`, which is hopeless at large `n`. The fix is a **reference
hierarchy** (Allen & Kautz–style "reference intervals"): cluster intervals under
a smaller set of reference intervals (e.g. one per event/episode, day, or
process), store *precise* Allen relations only **within** a cluster and only
**between reference intervals** across clusters, and derive a cross-cluster
relation between two ordinary intervals **on demand** by composing
local→reference→reference→local. This trades exact all-pairs relations for a
two-level (or k-level tree) structure: with `m` clusters of size `≈ n/m`,
intra-cluster storage is `O(m·(n/m)²) = O(n²/m)` and the reference layer is
`O(m²)`, minimized near `m ≈ n^{2/3}` to give roughly `O(n^{4/3})` storage and
sub-cubic reasoning, at the cost of coarser (possibly disjunctive) answers for
queries that cross the hierarchy. Design choices to specify: how reference
intervals are chosen (domain episodes vs. fixed time granularities vs. a
balanced tree), how an interval is (re)assigned to a reference when asserted,
how to keep the reference layer path-consistent incrementally, and how to fall
back to local refinement when a coarse cross-cluster answer is not precise
enough. This is genuinely a research-level (★★★★) design with no single optimal
answer; the reference-hierarchy is the standard approach.
