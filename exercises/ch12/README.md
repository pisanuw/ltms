# Chapter 12 — Assumption-Based Truth Maintenance Systems (ATMS)

**Analysis only.** The ATMS is out of scope for this Python package (we implement the
JTMS/LTMS family, not the ATMS, GDE, or interpretation-construction machinery). The
answers below are conceptual: algorithm sketches, derivations, complexity arguments, and
design notes. No code is written here, and there is no `solutions.py` to run. Exercise
statements are paraphrased in my own words (the book text is copyrighted); the original
star ratings indicate difficulty.

Background notation used throughout:
- An **assumption** is a special node that may be freely assumed true.
- An **environment** is a set of assumptions; it denotes their conjunction.
- A **label** of a node `n` is a set of environments `{E1, ..., Ek}`, each one a minimal,
  consistent environment from which `n` follows. Labels are kept **sound, complete,
  minimal, and consistent** (the "label properties").
- A **nogood** is an inconsistent (contradictory) environment.
- A **justification** is a Horn-like rule `a1 & a2 & ... & ak => c`.

---

## Exercise 1 (*) — Building GOAL's label with a binary tree of justifications

**Paraphrase.** The label of node `GOAL` in the chapter's worked example (Figure 12.6) is
normally derived through a chain of justifications; show on a somewhat bigger example that
the same label can instead be produced by a balanced binary tree of justifications, and
discuss the pros and cons.

**Answer.** Suppose `GOAL` depends on intermediate facts `n1..n8`, each justified by one
assumption (`A1..A8`), and `GOAL` is justified by their conjunction.

- **Linear (chain) form.** A single justification `n1 & n2 & ... & n8 => GOAL`. Computing
  GOAL's label requires one big cross-product (label intersection/union step) over all
  eight antecedent labels at once.
- **Binary-tree form.** Introduce auxiliary nodes and pair the antecedents:
  - `n1 & n2 => p1`, `n3 & n4 => p2`, `n5 & n6 => p3`, `n7 & n8 => p4`
  - `p1 & p2 => q1`, `p3 & p4 => q2`
  - `q1 & q2 => GOAL`

  Each internal justification combines exactly two labels. With single-assumption inputs,
  the final label of GOAL is the single environment `{A1,...,A8}` (assuming no nogoods),
  identical to the chain version.

**Label-combination rule (why this works).** To propagate through `x & y => z`, the ATMS
forms the pairwise cross-product of `label(x)` and `label(y)`: every environment from x is
unioned with every environment from y, then the result is pruned (remove nogood
supersets, remove non-minimal environments) and merged into `label(z)`. Because set union
is associative and commutative, batching the unions pairwise yields exactly the same
minimal/consistent set of environments as doing them all at once. So the label is
invariant to the tree shape.

**Advantages of the binary tree.**
- Each combination step touches only two labels, so individual updates are cheaper and the
  intermediate results are smaller and easier to incrementally maintain.
- Sub-results (`p1`, `q1`, ...) are shared/reusable if those conjunctions appear elsewhere
  (common-subexpression sharing), which is the whole point of an ATMS.
- Better incrementality: if one input label changes, only the path from that leaf up to
  GOAL must be recomputed (O(log k) combination nodes), not the whole k-way product.

**Disadvantages.**
- More nodes and justifications to store and keep labeled (the auxiliary `p`/`q` nodes).
- Each auxiliary node carries its own label that must be maintained, propagated, and kept
  minimal; for a one-shot computation that is pure overhead.
- Worst-case total work is not reduced when labels are large: the cross-products can still
  blow up; the tree only helps when intermediate labels stay small or are shared.

---

## Exercise 2 (**) — Simulate an ATMS using a JTMS (ignore efficiency)

**Paraphrase.** Disregarding performance, reproduce ATMS behavior on top of a JTMS.

**Answer (construction).** The JTMS holds one belief state at a time (one context); the
ATMS holds all contexts simultaneously via labels. To emulate the ATMS we enumerate
contexts and harvest results.

1. **Map assumptions.** Each ATMS assumption `Ai` becomes a JTMS assumption node that can
   be enabled or disabled (in/out).
2. **Map justifications.** Each ATMS justification `a1 & ... & ak => c` becomes a JTMS
   justification with the same antecedents and consequent. Map ATMS contradictions to a
   JTMS contradiction/nogood node.
3. **Enumerate environments.** Iterate over the powerset of assumptions. For each subset
   `E` (smallest first):
   - Enable exactly the assumptions in `E`, disable the rest, run JTMS label propagation
     (BCP) to quiescence.
   - If the JTMS reports a contradiction, record `E` as a **nogood** and skip it (and skip
     all supersets, since nogoods are upward-closed).
   - Otherwise, for every node `n` the JTMS now believes, add `E` to a running label set
     for `n`.
4. **Minimize.** After enumeration, post-process each node's collected environment set:
   discard any environment that is a superset of another in the same set. What remains is
   the ATMS label (minimal, consistent, sound, complete).
5. **Query.** "Is `n` true in context `E`?" becomes "does some environment in `label(n)`
   subset-of `E`?" "Is `E` consistent?" becomes "is `E` not a superset of any nogood?"

**Correctness.** The powerset enumeration is exhaustively the same set of environments the
ATMS reasons over; minimization enforces the label-minimality property; nogood pruning
enforces consistency. So the emulation computes identical labels.

**Why it is impractical (the point of the exercise).** Step 3 is `2^A` JTMS runs for `A`
assumptions, each a full propagation. The real ATMS gets the same answers in one
incremental label computation by combining labels symbolically rather than enumerating
models. This exercise demonstrates that the ATMS is essentially a "JTMS run in all
contexts at once," and that doing it naively is exponential.

---

## Exercise 3 (**) — Justifications forcing exponentially many environments

**Paraphrase.** Exhibit a set of justifications that makes the number of environments the
ATMS builds grow exponentially in the number of justifications.

**Answer.** Use `n` independent "disjunction-by-two-assumptions" gadgets feeding a single
conjunction.

For each `i = 1..n` create two assumptions `Ai`, `Bi` and a node `xi` with **two**
justifications:
```
Ai => xi
Bi => xi
```
So `label(xi) = { {Ai}, {Bi} }` — two environments each.

Now add one node `GOAL` justified by the conjunction of all the `xi`:
```
x1 & x2 & ... & xn => GOAL
```

Propagating the label of GOAL is the cross-product of all the `xi` labels:
```
label(GOAL) = { {y1, y2, ..., yn} : yi in {Ai, Bi} }
```
which has `2^n` distinct minimal environments. The number of justifications here is
`2n + 1` (two per gadget plus the conjunction), so the label size, and the number of
environments the ATMS must construct and store, is `2^(Θ(justifications))` — exponential.

This is the fundamental cost of completeness: when the assumption structure is genuinely
disjunctive, the minimal-support label is exponentially large, independent of how cleverly
the ATMS is implemented. (Adding nogoods that rule out combinations is exactly how a
problem solver keeps real labels small in practice.)

---

## Exercise 4 (*) — Filtering during interpretation construction

**Paraphrase.** Interpretation construction is a form of dependency-directed search over
the ATMS database. Extra solution constraints can be too costly to enforce eagerly, but
deferring them lets intermediate results explode. (a) Write a version of the
interpretation builder that applies a user-supplied `filter` (a predicate on environments)
when the intermediate set gets too big; (b) rewrite the antecedent-nogood N-queens solver
(`aqueens.lisp`) to use such filters instead.

**Answer.**

*Definition.* A **filter** is a procedure `filter(E) -> non-nil iff E satisfies the extra
constraints`. Interpretation construction grows a set of candidate environments by
intersecting/combining choice sets; the bulge is the size of this intermediate set.

**(a) Filtered interpretation construction (sketch).**

```
interpretations(choice-sets, filter, bulge-threshold):
  results <- { {} }                  # start from the empty environment
  for each choice-set C in choice-sets:
      next <- {}
      for each partial environment P in results:
          for each choice c in C:
              E <- P ∪ assumptions-of(c)
              if E is consistent (not a superset of any nogood):
                  add E to next
      results <- minimize(next)       # drop non-minimal / nogood supersets
      if |results| > bulge-threshold: # interpretation bulge detected
          results <- { E in results : filter(E) }   # apply expensive filter NOW
  return { E in results : filter(E) } # final filter pass guarantees soundness
```

Key points:
- The filter is applied **lazily**: only when `|results|` crosses the threshold, and once
  more at the end so the answer is always correct even if the bulge never triggered.
- Filtering mid-stream is sound because the extra constraints are monotone for this search:
  if a partial environment already violates a constraint that can never be repaired by
  adding assumptions, pruning it removes no valid completion. (When constraints are *not*
  monotone in that sense, the filter must only be applied to *complete* environments, i.e.
  the final pass; mid-stream filtering then becomes a heuristic that may discard
  recoverable partials, so it should be opt-in per constraint.)
- The threshold is the tradeoff knob: low threshold = filter often (cheap memory, more
  filter calls); high threshold = filter rarely (risk of bulge).

**(b) N-queens with filters instead of antecedent nogoods.**

The original `aqueens.lisp` installs all "two queens attack each other" facts as nogoods
*before* search, so interpretation construction never builds attacking combinations. The
filtered version instead:
- Choice set per column `i`: the assumptions `Q(i,1)..Q(i,n)` (queen in row r of column i).
- Do **not** pre-install attack nogoods.
- Define `filter(E)`: scan the queen placements in `E`; return nil if any two share a row
  or a diagonal, non-nil otherwise. (Same-column conflicts are excluded automatically
  because each column is one choice set contributing one assumption.)
- Run the filtered `interpretations` above with a modest `bulge-threshold`.

Behavior difference: the antecedent version prunes attacking pairs *at the moment a pair is
combined* (cheap, eager, lots of stored nogoods); the filter version lets partial boards
accumulate and culls them when the candidate set swells (no stored nogoods, but repeated
full-board re-checking). For N-queens the antecedent version is usually faster because the
constraint is cheap and pairwise; the filter version is the right design when the
constraint is genuinely expensive or global and cannot be decomposed into pairwise
nogoods. This is exactly the tradeoff the exercise is illustrating.

---

## Exercise 5 (***) — Bit-vector representation of assumption sets

**Paraphrase.** Re-implement `atms.lisp` so that environments (assumption sets) are stored
as bit vectors instead of lists, assuming the assumption count is modest.

**Answer (design).** Assign each assumption a fixed bit index `0..A-1` at creation. An
environment becomes an integer / fixed-width bit vector; bit `i` set means assumption `i`
is present. Then the core ATMS set operations become single machine-word (or word-array)
bit operations:

| ATMS operation | List version | Bit-vector version |
|---|---|---|
| union of two environments (justification combine) | merge two sorted lists | `a OR b` |
| subset test `E1 ⊆ E2` (minimality, nogood check) | scan membership | `(a AND b) == a` |
| equality of environments | list compare | integer `==` |
| environment ∈ nogoods (consistency) | scan nogood list | for each nogood `g`: `(g AND E) == g` |
| empty environment | `nil` | `0` |
| add assumption `i` | cons | `E OR (1 << i)` |

Implementation notes:
- For `A` up to the word size (e.g. ≤ 64) an environment is a single fixnum, so combine and
  subset are O(1). For larger `A`, use a vector of `ceil(A/word)` words; operations are
  O(A/word), a constant-factor (typically 64x) speedup over list scanning.
- **Minimality pruning** within a label: an environment `E` is redundant if some other
  label environment `E'` satisfies `E' ⊆ E`, i.e. `(E' AND E) == E'`. Bit AND makes this
  fast; the overall pairwise minimization stays O(L^2) in label size `L` but with tiny
  constants.
- **Nogood storage** is also bit vectors; "is `E` consistent" is "no nogood is a subset of
  E," each subset test a couple of AND/compare ops.
- Trade-off (why the "not too large" caveat): bit vectors waste space when `A` is large but
  individual environments are small/sparse (a 10000-assumption problem with 3-element
  environments wastes most bits). For sparse, very large assumption spaces, sorted lists or
  hashed sets can win. The bit-vector form is ideal for the common case of a few dozen
  assumptions with dense interaction, which is exactly the ATMS sweet spot.

---

## Exercise 6 (***/****) — Spatial planning: assigning groups to rooms/floors

**Paraphrase.** Many consistent solutions differ in desirability (groups want to be near or
far from others, some need special facilities). (a) Represent topological/spatial relations
among rooms; (b) represent preferences using that spatial vocabulary; (c) build a program
that produces good solutions; (d) test it on a real organization and building.

**Answer (design; this is an open project, so I state assumptions and a workable design).**

**(a) Spatial/topological representation.**
- Entities: `building`, `floor(building, level)`, `room(floor, id)` with attributes
  `capacity`, `facilities ⊆ {lab, server, conf, wet-lab, ...}`.
- Topology as relations (all derivable into ATMS assumptions/justifications):
  - `same-floor(r1, r2)`, `adjacent(r1, r2)` (share a wall / next door),
  - `on-floor(r, f)`, `above(f1, f2)`,
  - a metric/quasi-metric `dist(r1, r2)` (e.g. graph distance over an adjacency graph, plus
    a floor-change penalty).
- Represent the floor plan as a graph: nodes = rooms, edges = adjacency, with a separate
  "vertical" edge type connecting stairwell/elevator-adjacent rooms across floors.

**(b) Preference representation (uses the spatial vocabulary).**
- A preference is a tuple `(group-or-pair, predicate, weight)`:
  - `near(g1, g2, w)` rewards small `dist` between any room of g1 and any room of g2.
  - `far(g1, g2, w)` is the negation (penalize proximity).
  - `needs(g, facility, w)` is a hard or soft requirement that g's room has a facility.
  - `contiguous(g, w)` rewards a group's rooms being mutually adjacent.
- Hard constraints (capacity fits, exclusive facility use, one group per room) are encoded
  as ATMS **nogoods**; soft preferences are an additive objective `score(solution) = Σ w *
  satisfied(predicate)`.

**(c) Solver design.**
- Choice sets: for each group, the set of feasible room assignments (assumptions
  `assign(g, r)`). Use the ATMS / interpretation construction to enumerate *consistent*
  assignments (hard constraints as nogoods prune inconsistent room sharing, capacity, and
  facility conflicts).
- Because consistent solutions can still be numerous, do not enumerate all then sort.
  Instead pair interpretation construction with the **filter** idea from Exercise 4: prune
  partial assignments whose best achievable score is already below the current best
  (branch-and-bound on the soft objective), and apply preference scoring as a filter when
  the candidate set bulges.
- Output the top-k solutions by `score`, with explanations (which preferences each one
  satisfies/violates) read off directly from the environment/label structure — a natural
  ATMS strength.

**(d) Evaluation.** Take a real org chart (groups, sizes, declared adjacency preferences,
facility needs) and a real floor plan; check that (i) all hard constraints hold, (ii) the
ranked solutions match human judgment on a few hand-graded cases, and (iii) runtime stays
tractable (the bulge-control filtering is what makes this feasible). I cannot actually run
(d) here; it requires real-world data and is noted as the project capstone.

---

## Exercise 7 (**) — An ATMS that accepts arbitrary clauses

**Paraphrase.** What if the ATMS could take arbitrary disjunctive clauses as input, the way
the LTMS generalizes the JTMS beyond Horn justifications? Build a simple version on top of
`atms.lisp` and discuss how hard logical completeness becomes.

**Answer.** The basic ATMS justifications are essentially Horn (a conjunction of
antecedents implies one consequent). A clausal ("CMS"-style / clause-management) ATMS
accepts full clauses `l1 ∨ l2 ∨ ... ∨ lk`.

**Simple construction.**
- Keep the assumption/environment/label machinery unchanged.
- For an all-negative clause (`¬a ∨ ¬b ∨ ...`, i.e. "not all of these hold"), treat it as a
  **nogood generator**: the environment containing all those assumptions is contradictory,
  so install it as a nogood. This is the easy, mostly-mechanical part.
- For clauses with positive literals, you need **disjunctive/hyper-resolution** to push
  conclusions forward: from `a ∨ b` and a context where `¬a` holds, conclude `b`. The ATMS
  has no native "or" node, so you must resolve clauses against each other and against node
  labels to derive new (possibly shorter) clauses and new nogoods.

**Why completeness is hard.** With Horn justifications, ordinary label propagation (a kind
of unit propagation) already computes complete labels. With arbitrary clauses, label
propagation alone is **incomplete**, for the same reason BCP is incomplete in the LTMS:
some consequences only follow by case analysis / resolution, not by unit propagation. To
be logically complete you must compute the **prime implicates** of the clause set (close
the database under resolution and subsumption), and label nodes with respect to that closed
set. That closure is expensive (worst-case exponentially many prime implicates), which is
exactly the same completeness wall the CLTMS hits.

**Connection to this package.** Our `ltms/cltms.py` already does precisely this for the
LTMS: it computes prime implicates by resolution + subsumption and adds the missing ones so
that BCP becomes complete (with IPIA noted as future work). A clausal ATMS would graft that
same prime-implicate machinery onto the environment/label layer. So the honest answer to
"how difficult is completeness?" is: as difficult as prime-implicate generation in general,
i.e. potentially exponential, and the same tradeoff (incremental but incomplete vs complete
but expensive) reappears.

---

## Exercise 8 (**) — Interpretation construction with forward checking and dynamic reordering

**Paraphrase.** Without defaults, interpretation construction is plain backtracking search.
Build an interpretation constructor that adds forward checking and future-variable
reordering: dynamically reorder choice sets by remaining size and, after each choice,
delete from not-yet-visited choice sets any choice already known inconsistent with the
partial solution.

**Answer (algorithm).**

```
interpret(choice-sets, partial = {}):
  if choice-sets empty: emit partial; return
  # future-variable reordering (MRV / fail-first):
  pick the choice-set C with the FEWEST remaining live choices
  if C is empty: backtrack (dead end)
  for each choice c in C:
      E <- partial ∪ assumptions-of(c)
      if E consistent (not superset of a nogood):
          # forward checking: prune the rest
          pruned <- copy of (choice-sets without C)
          for each other choice-set D in pruned:
              remove from D every choice d such that
                  partial ∪ {c, d} is a known nogood / inconsistent
          # if any D became empty, this branch is doomed -> skip c
          if no D is empty:
              interpret(pruned, E)
```

How the two techniques map onto the ATMS:
- **Forward checking** uses the nogood database as the consistency oracle: after committing
  `c`, any future choice `d` whose pairing with the current partial environment is already a
  nogood is removed from its choice set immediately. If a choice set empties, prune now
  rather than discovering it deep in the tree.
- **Future-variable (dynamic) reordering** = the minimum-remaining-values / fail-first
  heuristic: always expand the choice set with the fewest surviving choices, because that
  is where backtracking is most likely and where forward checking already shrank the
  domain most. Combined with forward checking, an emptied domain is detected and pruned at
  once.
- Both are *search-order* optimizations: they do not change which interpretations exist,
  only how fast they are found. They drastically cut the intermediate "interpretation
  bulge" that the naive cross-product builder suffers from.

Complexity: still worst-case exponential (the problem is NP-hard in general), but forward
checking + MRV typically prunes orders of magnitude of the tree on structured problems,
mirroring standard CSP results (see Exercise 9 and Section 18.1).

---

## Exercise 9 (**) — A CSP solver, and the two graph-coloring examples

**Paraphrase.** A CSP is variables with finite domains plus constraints (each constraint
listed as its allowed value tuples; unlisted/universal constraints omitted); a solution
assigns every variable a value satisfying all constraints. Write a small Lisp `csp`
procedure (using one of the two solution-construction methods), then predict and explain
the outputs of the two given graph-coloring instances.

**Answer.**

**Solver (sketch; described, not coded per instructions).** Represent each variable's
value as a choice (assumption) and each constraint as the explicit set of allowed value
pairs; any pair not listed for a constrained variable-pair is forbidden (a nogood).

- Backtracking-search method: order variables; for each, try each domain value; a value is
  consistent if, for every already-assigned neighbor, the (var,value)/(neighbor,its-value)
  pair appears in that constraint's allowed-tuple list. Recurse; on dead end, backtrack.
  (This is the "interpretation construction = backtracking" view of Exercise 8, optionally
  with forward checking.)
- The example `(csp '((x a b)(y e f)(z c d g)) ...)` with constraints
  `Cxy={(b e),(b f)}`, `Cxz={(b c),(b d),(b g)}`, `Cyz={(e d),(f g)}`:
  - `Cxy` forces `x = b` (no allowed tuple has `x = a`).
  - With `x = b`, `Cxz` allows `z ∈ {c, d, g}` (all of z's domain).
  - `Cyz` couples y and z: allowed `(e,d)` and `(f,g)`.
  - So the solutions are `x=b, y=e, z=d` and `x=b, y=f, z=g`. (The book quotes the first.)

**First coloring instance — 3 nodes, "all different" on every pair (triangle), 3 colors.**
The three constraints `(n1 n2)`, `(n2 n3)`, `(n1 n3)` each list exactly the six
*different-color* ordered pairs over `{r,g,b}`, i.e. each pair must get different colors.
This is **proper 3-coloring of a triangle (K3)**. K3 is 3-colorable, so solutions exist:
every assignment giving the three nodes three *distinct* colors works. There are `3! = 6`
solutions (all permutations of `r,g,b` over `n1,n2,n3`). The CSP solver returns these six.

**Second coloring instance — 4 nodes, K4 (all six pairs "all different"), 3 colors.**
Here all `C(4,2) = 6` node pairs are constrained to differ, i.e. it is **proper 3-coloring
of K4**. A complete graph on 4 vertices needs 4 colors (its chromatic number is 4), so with
only 3 colors **no assignment can give all four nodes pairwise-distinct colors** — by
pigeonhole two of the four nodes must share a color, and they are adjacent. Therefore this
CSP has **no solution**; the solver returns the empty set.

**Explanation of the contrast.** The two instances differ only by adding a fourth fully
connected node. K3 is 3-chromatic (solvable with 3 colors, 6 solutions); K4 is 4-chromatic
(unsolvable with 3 colors). This is the classic "graph coloring as CSP" demonstration and
ties directly to the nogood reasoning the ATMS performs: in the K4 case every full
3-coloring attempt collapses into a nogood, so the interpretation set is empty.

---

### Notes on scope and method

- Exercises 1, 3, 8, 9 admit exact answers (label invariance, an explicit exponential
  family, standard CSP/forward-checking algorithms, and concrete coloring results), so
  those are given precisely.
- Exercises 2, 5, 7 are implementation tasks; since the ATMS is not in this package they
  are answered as designs/algorithm sketches with correctness and complexity arguments,
  cross-referenced to the parts we *do* implement (JTMS, and prime-implicate completion in
  `ltms/cltms.py`).
- Exercises 4 and 6 are open-ended; I stated explicit assumptions and gave a concrete,
  buildable design rather than vague description. Exercise 6(d) requires real-world data
  and cannot be executed in this environment.
- All answers are paraphrased; no wording is copied from the copyrighted source.
