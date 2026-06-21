# Chapter 11: Implementing Qualitative Process Theory - Exercise Solutions

**Analysis only.** This chapter's system (TGIZMO, the Qualitative Process Theory
engine built on the LTRE) is *out of scope* for our Python LTMS/LTRE port. We did
not implement QP theory, the measurement-interpretation (MI) algorithm, the
modeling language (`mlang.lisp`), `translate-relations`, or limit analysis.
Accordingly, the answers below are **conceptual**: algorithm sketches,
derivations, complexity arguments, and design discussions. No code was written or
run for this chapter.

These solutions are original paraphrases of the exercise prompts followed by my
own analysis. The exercise wording itself (copyrighted, Forbus & de Kleer,
*Building Problem Solvers*) is not reproduced.

Throughout I use QP terminology: a *quantity* has an amount `A` (value) and a
derivative `D` (`Ds`); `I+`/`I-` are direct influences; `Qprop`/`Qprop-` are
qualitative proportionalities; a *process* or *view* is *active* when its
preconditions and quantity conditions hold; the *process structure* is the set of
active processes/views; `resolve-influences` computes the net `Ds` sign of each
influenced quantity; a *state* (snapshot) records the qualitative situation.

---

## Exercise 1 (*) - Is the amount > 0 conjunct in the fluid-flow quantity condition redundant?

**Paraphrase.** The fluid-flow process is gated by two conditions: that the source
holds a positive amount of the substance, and that source pressure exceeds
destination pressure. Is the "positive amount" clause actually needed?

**Answer.** It is **necessary** in general, because pressure and amount are linked
only indirectly through a *monotonic* qualitative proportionality, not an
equality. `pressure` is `Qprop` to `amount-of` (and modulated by container
geometry). A `Qprop` guarantees the *ordinal* relationship between a quantity and
its derivative-mate only when the function is known to pass through a particular
correspondence point. In the bare modeling language used here, the system does not
automatically know that "amount = 0" corresponds to "pressure = 0," nor that two
different containers' pressures both bottom out at zero amount. So from
`pressure(src) > pressure(dst)` alone the engine cannot conclude
`amount(src) > 0`.

Concretely: the destination could be empty (pressure low) while the source merely
has higher pressure; or both containers could legitimately have pressures that do
not vanish at zero amount under the impoverished math. Dropping the conjunct would
let flow start (or, worse, continue) when the source is empty, producing physically
absurd behavior (negative or never-emptying reservoirs).

If we *added* a `Correspondence` linking `(pressure, zero)` to `(amount, zero)`
(see Exercise 16a) **and** a `Function-Spec` asserting all containers share one
pressure-level function (Exercise 16b), then for two otherwise-identical containers
the engine could derive `amount(src) > 0` from the pressure inequality, and the
conjunct would become redundant for those cases. In the general heterogeneous case
it is still needed. So: keep it.

---

## Exercise 2 (*) - What happens when TGIZMO instantiates the malformed `Zorch-it` process?

**Paraphrase.** Trace what the instantiation machinery does with a process
definition whose quantity condition and influences mention variables (`?bar`,
`?self`) that are never introduced/bound in the `:INDIVIDUALS` field.

**Answer.** The instantiation fails to produce a well-formed process instance
because of **unbound (free) variables**, and any instance it does create is
**ill-formed**:

- `:INDIVIDUALS` declares only `?foo` (a `physob`). The variables `?bar` and
  `?self` are never bound there.
- `?self` is the conventional name for the process instance itself; in a correctly
  written definition it is supplied by the instantiator. Its appearance in
  `(grump ?self)` is acceptable *only* if the implementation treats `?self`
  specially. If it does not, `(Quantity (grump ?self))` and the influence
  `(I+ (strength ?foo) (grump ?self))` reference an undefined object.
- `?bar` is genuinely free: it appears in the quantity condition
  `(< (A (strength ?foo)) (A (strength ?bar)))` and in
  `(Qprop (grump ?self) (strength ?bar))`, but nothing ranges over it. The
  matcher has no individuals of the right type to bind it to, so either (a) no
  instances are created (the pattern-matcher finds no consistent binding for
  `?bar`), or (b) instances are created with `?bar` left as a logic variable,
  yielding a quantity condition and a `Qprop` over an unground term, which the
  downstream rules (quantity-condition truth maintenance, influence resolution)
  cannot evaluate.

**Diagnosis to report:** every variable used in `:QUANTITY-CONDITIONS`,
`:RELATIONS`, and `:INFLUENCES` must be bound in `:INDIVIDUALS` (or be `?self`).
`Zorch-it` violates this, so it is a modeling error. A robust `mlang`
implementation should *signal an error at definition/compile time* listing the
free variables, rather than silently producing degenerate instances. (This is a
good motivation for the `:BIND` / `:TYPE` machinery of Exercise 17.)

---

## Exercise 3 (*) - Why does `resolve-influences` test for a `Resolved` marker instead of just checking whether `Ds` is known?

**Paraphrase.** Influence resolution could simply check "do we already have a
sign for this quantity's derivative?" Why does it instead look for an explicit
`Resolved` assertion?

**Answer.** Because *knowing a `Ds` value* and *having finished resolving the
influences* are different facts, and conflating them is unsound. Reasons:

1. **A `Ds` value can become known for reasons other than resolution.** It might
   be given as an input/boundary condition, asserted by the scenario, propagated
   by an inequality/ordinal rule, or inherited. If `resolve-influences` keyed off
   "Ds known," it would skip quantities whose derivative is externally known but
   whose influences have *not* been combined, and it would never detect a
   contradiction between an asserted `Ds` and the influences acting on it.

2. **Resolution is a closed-world / completeness commitment.** Net derivative =
   sign of the sum of all influences is valid *only after all influences are in
   hand*. The `Resolved` marker is the engine's record that "the set of
   influences on this quantity is now complete and has been combined." It is the
   justification (in TMS terms) that the derived `Ds` depends on. The marker lets
   the LTRE *retract* the resolution correctly if the process structure later
   changes (an influence appears or disappears), because the `Ds` belief is
   justified by `Resolved`, not merely co-present with it.

3. **Idempotence / termination.** A `Resolved` flag gives a clean termination test
   for the resolution pass and prevents re-resolving (which matters when influence
   resolution and quantity-condition evaluation iterate to fixpoint).

In short, `Resolved` is the *provenance* of the derivative conclusion; "Ds known"
is just a value and carries no provenance, so it cannot drive sound,
retraction-aware control.

---

## Exercise 4 (*) - Why doesn't `check-comp-cycle` explicitly look for the "object doesn't exist" non-relation case?

**Paraphrase.** When the object owning a number N1 does not exist, N1 stands in no
ordinal relation to any other number. Given that, why does the comparison-cycle
checker not test for this situation directly?

**Answer.** Because the property is enforced **structurally / by construction**,
so the cycle checker never *sees* a stray ordinal relation it would have to filter
out. The book's representation ties a quantity's number to the *existence of its
owning object*: the assertions establishing ordinal relations on N1 are themselves
*justified by* the existence (`Exists`/`Consider`) of the object. When the object
does not exist, those justifications are out, the ordinal relations on N1 are not
believed, and the equality/inequality graph that `check-comp-cycle` walks simply
contains no node/edges for N1.

So the invariant `for all N2: NOT[N1 N2] AND NOT[N2 N1]` holds automatically as a
consequence of TMS label propagation, not as a rule the algorithm must apply.
`check-comp-cycle` only ever examines relations that are *currently believed*; a
non-existent object contributes none. Adding an explicit check would be redundant
(and a performance cost), because the LTMS already prunes those relations before
the checker runs. The design lesson: push such invariants into the
justification structure so downstream algorithms can assume them.

---

## Exercise 5 (*) - Why is there only one "no flow" state when there are two distinct reasons for no flow?

**Paraphrase.** In the flow example, "no flow" can arise either from equal
pressures or from a blocked path (`aligned` false), yet the diagram shows a single
state for "no flow." Why aren't there two states?

**Answer.** Because a **state (qualitative state / process structure) is
individuated by which processes and views are *active***, not by *why* the inactive
ones are inactive. The flow process is inactive in both scenarios; therefore the
*process structure* is identical (flow off), and the consequent qualitative
behavior (no transfer, derivatives all zero from this process) is the same. QP's
state abstraction deliberately groups together all situations that share the same
active-process set and the same ordinal/derivative consequences.

Equal-pressure vs blocked-path differ only in the *truth values of individual
quantity conditions and preconditions* (`pressure(src) = pressure(dst)` vs
`NOT aligned(path)`), which are finer-grained than the state. Those distinctions
matter for *transitions* (limit analysis): from the equal-pressure state a small
perturbation can restart flow, whereas from the blocked-path state it cannot until
the path becomes aligned. But for describing the *current* qualitative behavior
they are equivalent, so QP collapses them into one state.

If we *wanted* to distinguish them, we would have to choose a finer state
abstraction keyed on the union of precondition/quantity-condition truth values
(exactly the alternative explored in Exercise 15a), which multiplies the number of
states.

---

## Exercise 6 - Implementing magnitude (`m`) in TGIZMO

### 6a (*) - When would `m` be useful?

**Paraphrase.** Give circumstances where a magnitude function `m` (the absolute
size of a quantity, ignoring sign) earns its keep.

**Answer.** `m(q)` is useful whenever the *sign* of a quantity is variable but the
physics depends on the **size** of the deviation:

- **Comparing rates regardless of direction.** Two opposing flows into a tank:
  the net derivative of the amount is decided by which flow has the larger
  magnitude, `m(rate1)` vs `m(rate2)`, even though the rates have opposite signs as
  contributions.
- **Symmetric driving terms.** Heat/fluid flow whose rate is `Qprop` to a
  *difference* (`temp(src) - temp(dst)`): the magnitude of the difference sets the
  magnitude of the rate, and as the difference shrinks toward zero the rate's
  magnitude shrinks too. Reasoning about "the gap is closing" is naturally stated
  with `m`.
- **Limit/equilibrium reasoning.** Approaching equilibrium is "`m(difference)`
  decreasing toward zero." Oscillation/over-shoot reasoning needs magnitudes of
  successive excursions.
- **Quantities with no fixed sign convention** (e.g., a force or velocity that can
  point either way) where you want to compare strengths.

### 6b (*) - Which procedures/rules need modification to support `m`?

**Paraphrase.** Identify the parts of TGIZMO that must change to fully support
`m`.

**Answer.** `m` is a new term-former in the qualitative math, so every component
that parses, normalizes, compares, or propagates qualitative values is touched:

1. **Term/expression representation and the parser in `mlang`** -- accept `(m q)`
   as a legal quantity term; `translate-relations` must handle it.
2. **The ordinal/inequality reasoner** (the `>`, `<`, `=` comparison rules and
   `check-comp-cycle`) -- add the *defining axioms* of `m`:
   `m(q) >= 0`; `q > 0 => m(q) = q`; `q < 0 => m(q) = -q`; `q = 0 <=> m(q) = 0`;
   and the order-reversing/preserving rules so that ordinal facts about `q`
   translate into ordinal facts about `m(q)` (case split on sign).
3. **`resolve-influences` / sign arithmetic** -- the qualitative `sign`,
   negation, addition, and the `s+`/`s-` combinators must be extended so that
   `Ds(m(q))` can be derived. By the chain rule, `Ds(m(q)) = sign(q) * Ds(q)`
   when `q != 0` (and is `m(Ds(q))`-like at `q = 0`). This is the subtle part.
4. **`Qprop`/correspondence propagation** -- proportionalities stated over `m`
   must propagate ordinal info under the sign case-split.
5. **Snapshot/state machinery** -- if `m` values are tracked, they become part of
   the recorded qualitative state.

### 6c (**) - Extend the qualitative math to support `m`

**Paraphrase.** Sketch the extension of the qualitative algebra that actually makes
`m` work.

**Answer (algorithm sketch).** Treat `m` as a defined function over the existing
sign/ordinal algebra and case-split on the sign of the argument:

- **Sign domain.** Add `m` to the set of quantity terms. Maintain the invariant
  `[m(q), zero] in {>, =}` (never `<`).
- **Value axioms (asserted as LTRE rules, justified by the sign of `q`):**
  - belief `q > 0`  -> assert `m(q) = q`
  - belief `q < 0`  -> assert `m(q) = (- q)` (introduce the negation term, with
    `(- q) > 0`)
  - belief `q = 0`  -> assert `m(q) = 0`
  These are properly justified so that when the sign of `q` is revised, the `m`
  equality is retracted and replaced.
- **Ordinal propagation:** for two quantities with the *same* sign, `m` is
  monotone (`a > b > 0 => m(a) > m(b)`); for opposite signs use the zero pivot
  (`m(q) > 0` for any nonzero `q`). Encode these as comparison rules feeding the
  existing inequality network so `check-comp-cycle` keeps everything consistent.
- **Derivative (the hard rule):** `Ds(m(q)) = sign(q) * Ds(q)` for `q != 0`. Add a
  qualitative multiplication of `sign(q)` (a `{-,0,+}` value) by `Ds(q)`; this
  reuses the sign-multiplication table already needed for influences. At `q = 0`
  the magnitude has a non-smooth point: `Ds(m(q))` follows `m(Ds(q))`
  (the magnitude bounces off zero), which limit analysis should flag as a
  potential transition.
- **Integration with `resolve-influences`:** when a quantity influences `m(q)`,
  route the contribution through the sign-multiplied derivative rule above.

Complexity: the additions are a constant number of rules per `m`-term plus extra
ordinal edges; the dominant cost is the extra sign case-splits multiplying the
number of qualitative states the searcher must consider.

---

## Exercise 7 (**) - Profile TGIZMO and propose three speedups for the hot subsystem

**Paraphrase.** Measure where TGIZMO spends its time across several examples and
recommend three optimizations for the most expensive subsystem.

**Answer (analysis, no runnable profile available).** For an LTRE-based QP engine
the time sinks are predictable; in order of typical cost:

1. **Instantiation / pattern matching** (finding all process & view instances by
   matching `:INDIVIDUALS` patterns against the object pool) -- combinatorial in
   the number of objects and the arity of patterns.
2. **Truth maintenance / BCP and label propagation** in the LTMS as
   quantity-condition truth values change.
3. **Ordinal reasoning** (`check-comp-cycle`, transitive-closure of `<`,`=`,`>`).
4. **Influence resolution** and the **state/snapshot search** (MI) on top.

For most "many objects, few relations" scenarios the **matcher/instantiator**
dominates. Three concrete speedups:

1. **Type/argument indexing (a discrimination net or RETE-style join).** Index
   candidate objects by type and by already-bound arguments so each `:INDIVIDUALS`
   clause filters against a small candidate set instead of the whole pool. The
   `:TYPE`/`:TEST` keywords of Exercise 17 make this indexing explicit and let the
   matcher prune early.
2. **Incremental re-instantiation.** Cache instances and only re-match the deltas
   when objects/relations are added, rather than re-instantiating the whole domain
   theory each cycle (memoize per `(pattern, binding-prefix)`).
3. **Compile-time expansion (`translate-relations`).** Move work out of run-time
   rules into compiled clauses (cf. Exercise 16e): expand math primitives,
   correspondences, and proportionalities at rule-compile time so the LTRE runs
   fewer, flatter rules and the BCP step shrinks.

(If profiling instead showed ordinal reasoning as the hot spot, the analogous fix
is to maintain incremental transitive closure with union-find for `=` classes
rather than recomputing cycles.)

---

## Exercise 8 - Discrimination using measurable parameters

### 8a (**) - A `predictions` procedure that finds discriminating measurements

**Paraphrase.** Given parameters whose `Ds` (derivative) values are measurable,
write a routine that proposes which *additional* measurements would best tell apart
the multiple interpretations the MI algorithm currently allows.

**Answer (algorithm sketch).**
1. Let `I = {i1, ..., ik}` be the current set of consistent interpretations
   (process structures + ordinal/derivative assignments) from MI.
2. For each *measurable* parameter `p` not yet measured, and each interpretation
   `ij`, look up the value `Ds(p)` that `ij` predicts (it is determined inside the
   state struct). Build the prediction vector
   `pred(p) = (v1, ..., vk)` over interpretations.
3. A measurement of `p` *discriminates* iff `pred(p)` is not constant across the
   surviving interpretations, i.e. the partition it induces (by predicted value in
   `{-,0,+}`) has more than one block.
4. **Rank** candidate measurements by discriminating power. A good objective is the
   one that most evens out / shrinks the candidate set: choose `p` maximizing
   information gain, e.g. minimize the size of the largest resulting block, or
   maximize entropy of the induced partition. (This is the same myopic
   one-step-lookahead criterion used in GDE/Sherlock probe selection.)
5. Return the ranked list; the top measurement, once taken, lets MI rule out every
   interpretation inconsistent with the observed value.

Edge cases: a parameter that all interpretations agree on is useless (skip it); if
no measurable parameter splits the set, report that the interpretations are
observationally indistinguishable with the available probes.

### 8b (**) - Compile a discrimination tree offline

**Paraphrase.** Since MI with *no* observations enumerates the full set of possible
states, use that to precompile a decision tree that reproduces MI's answers for any
future data without on-line qualitative reasoning.

**Answer (algorithm sketch).**
1. **Offline:** run MI with an empty measurement set to get `S`, the complete set
   of possible states for the scenario (each annotated with the `Ds`/ordinal value
   it predicts for every measurable parameter).
2. **Build a decision tree** by recursive partitioning, exactly as 8a's criterion
   but applied repeatedly:
   - Node holds a set of still-possible states (root = `S`).
   - Choose the measurable parameter whose value best splits the node's states
     (max information gain / min worst-case block).
   - Create a child branch per possible measured value `{-, 0, +, unknown}`,
     each child carrying the subset of states consistent with that value.
   - Recurse until each leaf is a single state, or a set of states that no further
     measurement can separate (label the leaf with that ambiguity group).
3. **On-line:** to interpret real data, just walk the tree: read the measured
   value of the parameter at each node and descend; the leaf gives the
   interpretation(s). No matching, no TMS, no ordinal reasoning at run time.

Cost trade-off: tree construction is exponential offline (it touches all states and
all parameter orderings considered greedily), but on-line lookup is O(tree depth) =
O(number of measurements queried). This is the classic compile-knowledge-once,
use-many-times design, appropriate when the scenario/domain theory is fixed and the
data varies (e.g., a fielded diagnostic).

---

## Exercise 9 - Reconstructing the LTRE database from a state struct

### 9a (*) - Is `snapshot`'s stored information sufficient to rebuild the LTRE database?

**Paraphrase.** A state struct is meant to capture enough to rebuild the LTRE's
contents and labels. Does `snapshot` actually store enough? If not, what is
missing?

**Answer.** In general **not by itself sufficient**, for two reasons:

1. **Derived vs. primitive facts.** A snapshot typically records the *believed*
   qualitative facts (active processes/views, ordinal relations, `Ds` values) but
   not necessarily the *justification structure* (which datum justifies which) nor
   the disbelieved-but-present clauses. To reconstruct LTMS *labels* (`:TRUE`,
   `:FALSE`, `:UNKNOWN`) and support, you must be able to re-derive them, which
   requires the **assumptions** (the chosen quantity-condition / precondition
   truth assignments and any modeling-assumption choices) plus the **domain
   theory** and **scenario**, so the rules can re-fire.

2. **Missing pieces to record:**
   - The set of **assumptions/choices** that distinguish this state from its
     siblings (the precondition & quantity-condition truth assignment that defines
     the state).
   - A reference to (or hash of) the **domain theory and scenario** used, so that
     the same instantiation is reproduced.
   - Any **input/boundary values** that were asserted externally (not derivable).
   - Optionally the **nogoods/contradiction info** learned, so re-derivation does
     not re-explore refuted branches.

If those are stored (or recoverable because the same TGIZMO + domain theory +
scenario are supplied), then re-running instantiation + asserting the recorded
assumptions + closing under the rules regenerates the labels deterministically. The
state need not store every label, only the *assumptions* that pin down the state,
because the labels are a function of (assumptions + theory).

### 9b (**) - Write `reconsider` to reproduce a state in a TGIZMO

**Paraphrase.** Implement a procedure that, given a saved state and a TGIZMO (plus
any extra info from 9a), recreates that exact qualitative state.

**Answer (algorithm sketch).**
1. Ensure the TGIZMO is initialized with the **same domain theory and scenario**
   that produced the state (load/instantiate them; reuse the recorded reference
   from 9a).
2. **Reset** the LTRE/LTMS to a clean labeled state (retract any current
   assumptions).
3. **Re-assert the state's defining assumptions:** the recorded precondition and
   quantity-condition truth assignment and any modeling-assumption choices,
   together with externally given input/boundary values.
4. **Run to fixpoint:** let instantiation, quantity-condition evaluation, and
   `resolve-influences` propagate. Because the rules are deterministic given the
   assumptions and theory, this reproduces exactly the snapshot's active processes,
   ordinal relations, and `Ds` values.
5. **Verify:** compare the regenerated process structure / ordinal set against the
   state struct; if they differ, the snapshot was missing information (loop back to
   9a's diagnosis). Optionally re-install learned nogoods to prevent contradiction
   re-exploration.

Key point: `reconsider` works by *re-deriving* rather than by literally writing
labels back, which is what makes the stored state struct compact (assumptions
only) yet faithful.

---

## Exercise 10 (***) - Extend TGIZMO to do limit analysis

**Paraphrase.** Add limit analysis: from a qualitative state, determine the possible
*next* states by analyzing how ordinal relations and derivatives drive quantities
to their limit points.

**Answer (design sketch).** Limit analysis computes qualitative state transitions:

1. **Identify limit points.** For each quantity, find the ordinal relations
   (to landmark values such as zero, container `Bottom`/`Top`, or to other
   quantities) that could change. A limit point is reached when a quantity moving
   in the direction of its `Ds` would cross or meet a value it is currently
   `<`/`>`/`=` to.
2. **Compute the direction of change** of every active ordinal relation from the
   `Ds` values: e.g. if `A < B` and `Ds(A) > 0`, `Ds(B) <= 0`, the gap is closing
   and `A < B` can transition to `A = B`. Build the set of *individually possible*
   changes for each relation that is "moving."
3. **Generate candidate transitions.** Each currently-`<`/`>` relation that is
   closing can go to `=`; each `=` that is being broken can go to `<` or `>`. An
   active process can deactivate (a quantity condition fails) and an inactive one
   can activate.
4. **Filter by quantity-space consistency (limit ordering).** Combine candidate
   changes and reject combinations that violate the relative *rates* of approach
   (equality-change rules: a relation that reaches its limit "sooner" must change
   first). This prunes spurious simultaneous transitions. The result is the set of
   consistent *next* qualitative states.
5. **For each surviving combination, snapshot a successor state** (run MI /
   resolution under the new ordinal assignment) and link it to the current state
   in a transition graph.

Implementation hooks: add a `limit-analysis` pass that reads the current state's
ordinal + `Ds` facts, proposes relation changes, and uses the existing ordinal
reasoner + `check-comp-cycle` to test consistency, then calls `snapshot` per
successor. Complexity is exponential in the number of simultaneously-moving
relations, mitigated by the equality-change ordering filter.

---

## Exercise 11 (***) - Build an envisioner on top of limit analysis

**Paraphrase.** Using TGIZMO + limit analysis, build an envisioner that produces the
total envisionment: all reachable qualitative states and the transitions among
them.

**Answer (algorithm sketch).** An envisioner is a fixed-point graph search over
limit analysis (Exercise 10):

1. **Initialize** a worklist with all *initial* qualitative states consistent with
   the scenario (run MI with the given boundary conditions; if the initial ordinal
   relations are underdetermined, enumerate the consistent completions).
2. **Loop:** pop a state `s`; if already in the state graph, skip; else add it.
   Run **limit analysis** on `s` to get its successor states `succ(s)`. Add each
   transition edge `s -> s'` and push unseen `s'` onto the worklist.
3. **Terminate** when the worklist is empty. Because the qualitative state space is
   finite (finite process structures x finite ordinal assignments), the search
   halts. The result is the **attainable envisionment**: a directed graph whose
   nodes are qualitative states and whose edges are legal transitions; cycles
   represent oscillation/steady behaviors, sinks represent equilibria.

Engineering: memoize states by a canonical key (active-process set + ordinal
relation set + `Ds` signs) so identical states are merged. Reuse `snapshot` to
build node contents and `reconsider`/re-derivation as needed. For the *total*
envisionment (every consistent state, not just reachable), seed the worklist with
all states MI produces with no boundary commitments, then connect them with limit
analysis.

Complexity: O(|states| x cost-of-limit-analysis); |states| is worst-case
exponential in the number of quantities, so practical envisioners rely on
abstraction (process structure only) to keep it tractable.

---

## Exercise 12 (***) - Build a history generator on top of limit analysis

**Paraphrase.** Use TGIZMO + limit analysis to generate a *history*: a particular
time-ordered sequence of qualitative states/episodes for a specific simulation,
rather than the whole envisionment graph.

**Answer (design sketch).** A history is a *single path* (per consistent branch)
through the transition structure, annotated with episodes (intervals) and instants:

1. **Start** from the given initial state.
2. **Step:** run limit analysis to find the successors of the current state. Each
   transition corresponds to some relation reaching a limit *at an instant*; the
   time spent in the current state before that is an *episode* (an interval).
3. **Branch on ambiguity:** if limit analysis yields several consistent
   successors, the history *branches* (the simulation is genuinely
   non-deterministic at the qualitative level); generate one history per branch
   (or all, as a tree).
4. **Record episodes and instants:** for each step append `(state, duration-as-an
   -interval)` then the instantaneous transition `(state-at-instant)` where the
   limiting relation becomes equality, followed by the next interval state.
5. **Stop** on reaching a quiescent state (no active process drives change), a
   cycle (mark it as periodic), or a user step bound.

Difference from the envisioner (Exercise 11): the envisioner builds the *graph of
all* states; the history generator unrolls *time-ordered sequences*, distinguishing
intervals (open episodes) from instants (transition points) and carrying temporal
continuity (a quantity's value/derivative at the end of one episode constrains the
start of the next). It can be implemented as a DFS over the transition graph that
emits interval/instant annotations and detects cycles, reusing limit analysis and
`snapshot`.

---

## Exercise 13 - Interpretation depends on theory and scenario

### 13a (*) - MI output for theory `tnst`, scenario `ex2`, with "water level dropping"

**Paraphrase.** With the `tnst` domain theory, scenario `ex2`, and the stipulation
that the can's water level is falling, what interpretations should MI produce, and
is that what you expect?

**Answer.** Stipulating `Ds(level(water-in-can)) < 0` means the amount of water is
decreasing (since `level` is `Qprop` to `amount`). MI must find a process structure
whose net influence on the can's water amount is negative. With `tnst` as given
(boiling/heat-flow style theory without evaporation/condensation), the only way to
*remove* water is an **active outflow** (a fluid-flow process whose source is the
can) or, if the theory includes boiling, **boiling consuming the liquid**. So MI
should return the interpretation(s) in which exactly those level-lowering processes
are active and any inflow is dominated or off.

**Is it expected?** Partly. If `tnst` lacks evaporation, MI *cannot* explain a
dropping level by evaporation, even though that is the physically intuitive cause
for water in an open can. So MI will either (a) attribute the drop to whatever
removal process the theory *does* have (e.g. an outflow/leak path, possibly an
unexpected one), or (b) report **no interpretation** if no modeled process can
lower the level. Both outcomes are "expected" given the theory's limits, and they
demonstrate the exercise's point: interpretation is only as good as the domain
theory. The "missing evaporation" gap is exactly what 13b fixes.

### 13b (***) - Add evaporation and condensation to `tnst`; rerun MI on ex1, ex2, ex3

**Paraphrase.** Extend `tnst` with evaporation and condensation processes, then
describe how MI's results change for the three example scenarios.

**Answer (modeling sketch + expected effects).** Add two processes:

- **Evaporation:** individuals = a contained liquid and the surrounding gas region;
  quantity condition roughly `temperature(liquid) > 0` (and liquid amount > 0);
  influences `I-` on the liquid's amount and `I+` on the gas's amount of that
  substance (vapor). Optionally gated by saturation: active while
  `pressure(vapor) < saturation-pressure(temp)`.
- **Condensation:** the reverse; active while `pressure(vapor) >
  saturation-pressure(temp)`; `I+` on liquid amount, `I-` on vapor amount.

Effect on MI:

- **For a dropping-level scenario (ex2 from 13a):** MI now has a *legitimate*
  level-lowering interpretation (evaporation) in addition to any outflow. So the
  number of interpretations *increases* (ambiguity rises) unless other conditions
  disambiguate. This is the intended fix for 13a's gap.
- **For scenarios where vapor/gas is present (ex1, ex3):** new states appear in
  which condensation can *raise* the liquid level or supply liquid, and
  evaporation/condensation can be in dynamic balance (an equilibrium where
  vapor pressure = saturation pressure). MI may now return additional process
  structures combining the original flow/heat processes with evap/cond.
- **General consequence:** richer theory => more possible interpretations for the
  *same* data, illustrating the cost of expressiveness. To keep interpretations
  manageable one then leans on Exercises 8/14 (extra measurements, extra
  knowledge) to prune.

(Exact per-scenario answers depend on the precise contents of `ex1/ex2/ex3`, which
are defined in the book's `tnst`/scenario files we do not have ported; the
*qualitative* change is "more, finer interpretations, with evaporation now an
admissible cause of falling levels.")

---

## Exercise 14 - Other knowledge to reduce interpretations

### 14a (*) - Three kinds of information that prune interpretations

**Paraphrase.** List three additional knowledge sources that can cut the number of
candidate interpretations of a measurement set.

**Answer.**
1. **Additional measurements / observations** (values of other quantities, or
   `Ds` of measurable parameters) -- each observed value eliminates every
   interpretation that predicts a different value (cf. Exercise 8).
2. **Temporal / history continuity** -- knowledge of the *previous* qualitative
   state restricts the current one to its legal successors under limit analysis;
   states unreachable from the known past are pruned.
3. **Structural / commonsense constraints and prior probabilities** -- e.g.
   conservation laws, known component health ("the valve is not broken"),
   modeling-assumption defaults, or relative likelihoods that rank or rule out
   exotic process combinations. Other valid answers: known operating mode of the
   device, symmetry/`Function-Spec` facts (Exercise 16b), or user-supplied
   process-existence assumptions.

### 14b (***) - Implement at least one such knowledge source in TGIZMO

**Paraphrase.** Extend TGIZMO to use one of the knowledge kinds from 14a, and test
on varied examples.

**Answer (design sketch, taking "temporal continuity").** Add a *previous-state*
input to the MI driver. Implementation:

1. Accept an optional `prior-state` (a snapshot) alongside the measurements.
2. Before generating interpretations, compute `legal-successors(prior-state)` using
   limit analysis (Exercise 10).
3. Constrain MI's search so the only process structures considered are those in
   `legal-successors`. Concretely, assert the disjunction "current process
   structure in {successors}" as a nogood-generating constraint, so any candidate
   interpretation outside that set is immediately refuted by the LTMS.
4. Run MI as usual; report the surviving interpretations.

Testing: take scenarios with genuine ambiguity (e.g. the dropping-level case),
supply different priors, and confirm that interpretations inconsistent with the
prior's reachable successors are dropped, while a prior consistent with several
successors leaves the corresponding ambiguity. (Alternatively, "extra measurement"
is the easiest to implement: simply assert the measured value as a fact and let the
LTMS prune; this reuses existing machinery and is the lowest-effort valid answer.)

---

## Exercise 15 - Trade-offs in MI search organization

### 15a (*) - Searching on precondition/quantity-condition truth instead of active-process sets

**Paraphrase.** Suppose MI branched on whether the union of all preconditions and
quantity conditions is true/false, rather than on which processes/views are active.
How does that change (1) the number of interpretations, (2) the information per
interpretation, and (3) efficiency?

**Answer.**
1. **Number of interpretations: more (finer).** Each precondition/quantity
   condition is an independent boolean, so the raw space is `2^(#conditions)`, far
   larger than the space of *distinct active-process sets* (many condition
   combinations map to the same process structure, as Exercise 5 showed for the
   "no flow" cases). You get many interpretations that are behaviorally identical
   but differ in *why*.
2. **Information per interpretation: more detailed.** Each interpretation now pins
   down the truth value of every condition, distinguishing e.g.
   equal-pressure-no-flow from blocked-path-no-flow. That extra detail is
   sometimes useful (it tells you the cause and the available transitions) but is
   redundant if you only care about behavior.
3. **Efficiency: worse.** A larger branching space means more LTMS work, more
   contradiction checking, and more snapshots, most of it producing distinctions
   the consumer does not need. So unless the fine distinctions are required, this
   organization is strictly more expensive than branching on active-process sets.

### 15b (**) - Minimal MI when only the process structure is wanted

**Paraphrase.** If interpretations need no more detail than the process structure,
the current MI over-computes. Rewrite it to do the least work needed to show a
process structure is a valid interpretation of the measurements.

**Answer (algorithm sketch).**
1. Enumerate candidate **process structures** (sets of active processes/views)
   directly, not full ordinal/derivative states.
2. For each candidate, **check feasibility lazily:** assert "these
   processes/views active, the rest inactive," then test only whether the
   measurements can be *consistently explained* under that structure -- i.e. run
   `resolve-influences` just far enough to confirm the measured `Ds`/values are
   derivable (or at least not contradicted). Do **not** compute the full ordinal
   relation set or generate snapshots.
3. Use the LTMS to short-circuit: the moment a candidate structure contradicts a
   measurement, prune it (and record a nogood so supersets sharing the conflict
   are skipped).
4. Return the set of feasible process structures.

This avoids (a) enumerating complete ordinal assignments within each structure and
(b) building full state snapshots, computing only the influence resolution needed
to validate against the data. Savings are largest when many ordinal completions
collapse to the same process-structure verdict.

### 15c (***) - Backward-chaining MI that instantiates only relevant theory

**Paraphrase.** For very large problems, even building the full process structure is
too much. Develop a backward-chaining MI that instantiates only the potentially
relevant parts of the domain theory for the scenario and searches that smaller
space.

**Answer (design sketch).** Invert the control flow: drive instantiation *from the
measurements/goals* rather than forward from all objects.

1. **Goal = explain the observed values/`Ds`.** For a measured quantity `q` whose
   value/derivative must be explained, ask: which processes/views can *influence*
   `q`? Use the domain theory's influence/`Qprop` structure as a dependency index.
2. **Backward-instantiate only those.** Instantiate just the processes/views that
   could affect `q` (matching only the individuals they need), not the entire
   domain theory over all objects.
3. **Recurse on their preconditions/quantity conditions:** to make a relevant
   process active you must satisfy its conditions, which may mention other
   quantities; recursively instantiate only what is needed to establish or refute
   those, expanding the relevant frontier on demand.
4. **Search the restricted space** of relevant process structures with the LTMS,
   pruning by nogoods as in 15b.
5. **Memoize** relevance so shared sub-instantiations are not repeated.

This is analogous to backward chaining / goal-directed instantiation (and to
demand-driven ATMS focusing): the cost scales with the *relevant* sub-theory around
the measured quantities, not with the whole scenario, which is the only way to make
MI tractable for engine/process-plant-scale models. The risk is missing
indirect couplings, mitigated by following all influence/Qprop chains transitively
until closure or a depth bound.

---

## Exercise 16 - Extending the modeling language's qualitative math

### 16a (**) - An LTRE rule for `Correspondence`

**Paraphrase.** Implement `Correspondence`, which carries ordinal information across
qualitative proportionalities (e.g. "level = bottom when amount = 0," so amount > 0
implies level > bottom). The rule must handle multiple indirect influences and
respect the signs of the proportionalities.

**Answer (rule sketch).** A `Correspondence` ties a *value point* of a dependent
quantity to a *value point* of an independent quantity, given a `Qprop` between
them. The rule's logic:

- Given `(Correspondence (Q1 v1) (Q2 v2))` and a `Qprop`/`Qprop-` relation
  `(qprop Q1 Q2)` (or `qprop-`):
  - When the ordinal relation between `Q2` and `v2` is known
    (`Q2 > v2` / `Q2 < v2` / `Q2 = v2`), conclude the corresponding ordinal
    relation between `Q1` and `v1`:
    - for `qprop` (positive): same direction -- `Q2 > v2 => Q1 > v1`,
      `Q2 < v2 => Q1 < v1`, `Q2 = v2 => Q1 = v1`.
    - for `qprop-` (negative): reversed direction -- `Q2 > v2 => Q1 < v1`, etc.
- **Multiple indirect influences:** `Q1` may be `Qprop` to several quantities. The
  correspondence conclusion is valid only when the *net* indirect influence sign is
  determined. So the rule fires the directional conclusion only when all other
  indirect influences on `Q1` are held at their correspondence points (the standard
  "all-but-one at correspondence" condition), or when the signs combine
  unambiguously; otherwise it asserts nothing (ambiguous). Encode this by guarding
  the rule on the resolved net sign of `Q1`'s indirect influences, with each
  contribution's sign read from the corresponding `qprop`/`qprop-`.
- All conclusions are asserted as LTRE facts justified by the correspondence, the
  proportionality sign(s), and the triggering ordinal relation, so they retract
  cleanly when any premise changes.

This is the workhorse rule reused by 16b/c/d.

### 16b (**) - An LTRE rule for `Function-Spec`

**Paraphrase.** Implement `Function-Spec`, which says several objects share the
*same* (unknown) function relating two quantities, letting ordinal info propagate
*across objects* (e.g. equal glasses: more water => higher level).

**Answer (rule sketch, building on 16a).** `Function-Spec name (qprop Qa Qb)`
declares that for every entity of the relevant type, `Qa = f(Qb)` for one shared
monotone `f`. The rule:

- For any two instances `x`, `y` sharing the same `Function-Spec` and the same
  controlling value of `Qb`, propagate ordinal relations on `Qb` into ordinal
  relations on `Qa`, using the proportionality sign exactly as in `Correspondence`:
  - `Qb(x) > Qb(y) => Qa(x) > Qa(y)` (positive `qprop`); reversed for `qprop-`;
  - `Qb(x) = Qb(y) => Qa(x) = Qa(y)`.
- Justification: the shared-function declaration plus the `Qb` ordinal relation.
  Because `f` is single-valued and monotone, equal inputs force equal outputs and
  ordered inputs force ordered outputs *across the different objects* (this is the
  key power: it relates quantities of *distinct* individuals, which a per-object
  `Qprop` cannot).
- Implementation reuses 16a: treat each object's `(Qa, Qb)` pair as a
  correspondence indexed by the shared function name, so a known ordinal relation
  on one object's `Qb` relative to another's becomes a correspondence point.

### 16c (**) - Transform `=` over binary sums/products into Qprops + correspondences

**Paraphrase.** Allow `=` constraints built from binary `+` and `-` (and `*`) and
write an LTRE rule that compiles them into the appropriate qualitative
proportionalities and correspondences (e.g. `flow-rate = temp(src) - temp(dst)`).

**Answer (transformation rule).** For `(= q (op a b))`:

- **Sum `(= q (+ a b))`:** `q` is `Qprop+` to `a` and `Qprop+` to `b`
  (`q` increases with each addend). Add the correspondence: when `a = 0` and
  `b = 0`, `q = 0` (so signs of the addends fix the sign of `q`). For partial
  info, `q`'s sign follows the qualitative sum `[a] (+) [b]` (ambiguous only when
  `a`,`b` have opposite signs).
- **Difference `(= q (- a b))`:** `q` is `Qprop+` to `a` and `Qprop-` to `b`.
  Correspondence: `a = b => q = 0`; hence `a > b => q > 0`, `a < b => q < 0`. This
  is exactly what makes `flow-rate = temp(src) - temp(dst)` positive when the
  source is hotter -- the rule emits `Qprop+ q temp(src)`, `Qprop- q temp(dst)`,
  and the correspondence `((q, zero) (temp(src), temp(dst)))`.
- **Product `(= q (* a b))`** (also see 16d): `q` is `Qprop` to both `a` and `b`
  with sign of each factor mattering; correspondence `a = 0 or b = 0 => q = 0`, and
  the sign of `q` is the qualitative product `[a] (x) [b]`.

The LTRE rule pattern-matches the `=` form, emits the `Qprop`/`Qprop-` facts and
the zero-correspondence, then lets the 16a/16b machinery do the ordinal
propagation. Each emitted fact is justified by the original `=` statement.

### 16d (**) - Implement products and quotients via Qprops + correspondences

**Paraphrase.** Support `*` and `/` in definitions (e.g.
`temperature = heat / amount-of`; `flow-rate = conductance * (temp(src) -
temp(dst))`) by reducing them to qualitative proportionalities and correspondences.

**Answer.**
- **Product `(= q (* a b))`:** emit `Qprop+ q a` *modulated by sign of b* and
  `Qprop+ q b` *modulated by sign of a*. Sign rule: `[q] = [a] (x) [b]`
  (qualitative sign multiplication). Correspondence: `a = 0 or b = 0 => q = 0`.
  Monotonicity is only unconditional when the other factor is held positive (the
  usual "other factors fixed" caveat), so guard ordinal conclusions on the sign of
  the held factor.
- **Quotient `(= q (/ a b))`** (e.g. `temperature = heat / amount`): emit
  `Qprop+ q a` and `Qprop- q b` (q rises with numerator, falls with denominator),
  for `b > 0`. Sign rule `[q] = [a] (x) [b]` (division and multiplication share
  the sign table for nonzero `b`). Correspondence: `a = 0, b > 0 => q = 0`; assert
  `b > 0` as a guard (avoid division by zero qualitatively -- if `b` can reach 0,
  flag a limit point).
- For the conductance example, compose 16c (the difference) with the product:
  `flow-rate = conductance * diff`, `diff = temp(src) - temp(dst)`, so chain the
  difference's Qprops/correspondence into the product's.

All reduce to (a) Qprop/Qprop- facts whose signs come from the qualitative
multiply/divide table and (b) zero-correspondences, then handled by 16a's rule.
Guard against the denominator reaching zero.

### 16e (***) - Move the math primitives into `translate-relations` (compile time)

**Paraphrase.** Rather than implementing the math primitives (16a-d) as run-time
LTRE rules, expand them at *rule-compile time* inside `translate-relations`,
generating the right clauses up front.

**Answer (design sketch).** `translate-relations` already turns a model's
`:RELATIONS` field into LTRE clauses at compile time. Extend it so that when it sees
`Correspondence`, `Function-Spec`, or `=`-with-arithmetic forms, it **expands them
in place** into the primitive `Qprop`/`Qprop-`/correspondence/ordinal clauses,
instead of leaving a generic primitive for a run-time rule to interpret:

1. Add cases to `translate-relations` for each new form.
2. For `(= q (op a b))`, statically emit the corresponding `Qprop+/Qprop-` clauses
   and the zero-correspondence clause(s) derived in 16c/16d -- since the operator
   and operands are known at compile time, the sign structure is fixed and can be
   baked in.
3. For `Correspondence`/`Function-Spec`, emit specialized directional-ordinal
   clauses for the specific quantities/objects involved, rather than a generic
   rule that re-derives them each run.
4. Net effect: the run-time LTRE carries fewer, flatter, fully-specialized clauses;
   no generic interpreter rule fires per match; BCP and instantiation are cheaper
   (this is the optimization motivated in Exercise 7's "compile-time expansion"
   recommendation).

Trade-off: faster run time and smaller live rule set, at the cost of larger
compiled output and a more complex `translate-relations`. The general principle
(partial evaluation / compile-time expansion of rules) is the same one behind
RETE/network compilation.

---

## Exercise 17 - Friendlier modeling-language syntax for `:INDIVIDUALS`

### 17a (**) - Add `:TYPE`, `:CONDITIONS`, `:TEST`, `:BIND` to individuals fields

**Paraphrase.** Extend `mlang.lisp` so an individuals entry can use the keywords
`:TYPE` (type pattern), `:CONDITIONS` (extra clauses), `:TEST` (procedural filter),
and `:BIND` (abbreviation for a compound term), as sugar over the plain
`(?var (type ?var))` form.

**Answer (design sketch).** This is a *macro-expansion* in `mlang`'s parser for the
individuals field; each entry is rewritten to the existing low-level form:

- `(?sub :TYPE substance)` -> `(?sub (substance ?sub))` (the base pattern).
- `(?gas :TYPE Contained-Gas :CONDITIONS (Consider (Gas :system)))` -> the type
  pattern *plus* the extra clauses appended to the instance's required conditions,
  so they must hold (or be asserted) for the instance.
- `(?force :TYPE force :TEST (not (reaction-force? ?force)))` -> the type pattern
  plus a *procedural guard* evaluated on the bindings-so-far during matching; if
  the test returns false the candidate binding is discarded before an instance is
  built. This is the same mechanism as procedural tests in the TRE rules, so reuse
  that machinery (run the test as a Lisp predicate over current bindings).
- `(?dst-cl :BIND (C-S ?sub ?st ?dst))` -> introduce `?dst-cl` as an alias that is
  *substituted* by `(C-S ?sub ?st ?dst)` throughout the rest of the process/view
  body; implement by adding `?dst-cl` to the binding environment as a derived
  (computed) binding rather than a matched one, after `?sub/?st/?dst` are bound.

Implementation notes: parse each entry, detect the keywords, and lower to the
canonical individuals representation before the existing instantiation code runs.
`:TEST` must be threaded into the matcher's per-candidate filtering (early pruning,
which also helps Exercise 7's performance). `:BIND` must be order-sensitive (its
free vars must already be bound by earlier entries) -- check this at compile time
and error otherwise (cf. the free-variable problem in Exercise 2).

### 17b (*) - Arguments for and against an `:ASSUMPTIONS` keyword

**Paraphrase.** Should the language add an `:ASSUMPTIONS` keyword marking which
individuals are modeling assumptions? Give both sides.

**Answer.**
*For:*
- **Explicitness/documentation:** it makes the modeler's commitments visible, so a
  reader (and the system) can tell which individuals are *assumed* (defeasible,
  choosable) versus *required* (definitional).
- **Tooling/control:** the MI/envisioner can systematically vary the marked
  assumptions (turn modeling assumptions on/off) to generate alternative
  interpretations; assumption retraction and ATMS-style focusing become
  first-class.
- **Consistency with TMS semantics:** assumptions are exactly the things the truth
  maintenance layer wants to identify, so labeling them aligns the modeling
  language with the inference machinery.

*Against:*
- **Redundancy/inference of intent:** in many cases whether an individual is an
  assumption is already determined by its role (e.g. `Consider`/`Exists` clauses
  are inherently assumptions); the keyword duplicates information.
- **Added complexity / footgun:** another keyword to learn, and a chance for the
  declared assumption set to drift out of sync with how the individual is actually
  used, creating confusing bugs.
- **Premature commitment:** what counts as an assumption can depend on context/use,
  so freezing it in the definition may be too rigid.

Recommendation: include it but make it *optional* and *default-derived* (infer
assumption status from clause type, let `:ASSUMPTIONS` override), getting the
explicitness benefit without forcing redundancy.

### 17c (**) - [truncated in source]

**Paraphrase (note).** The source text for Exercise 17c is **cut off** in the
provided OCR (it ends mid-sentence: an "unfortunate consequence of the decision to
use the simple ... [individuals representation]"). Based on the lead-in, 17c almost
certainly asks to address a limitation of the simple, *flat/positional* individuals
representation, most likely: that variable *scoping/ordering* and the lowering of
the new keywords (17a) interact awkwardly (e.g. `:BIND` and `:TEST` referencing
later-bound variables), and to fix it -- perhaps by moving to a more structured,
order-aware representation or a proper binding environment.

**Conceptual answer (given the likely intent).** The fix is to replace the
flat individuals list with an **ordered binding-environment model**: process each
entry in sequence, threading an explicit environment so that `:BIND`, `:TEST`, and
`:CONDITIONS` can refer only to variables already bound, with compile-time checks
for forward references (the same discipline that would have caught Exercise 2's
free `?bar`). This makes the keyword extensions of 17a well-defined and composable,
at the cost of giving up the convenience of treating the field as an unordered set.

*If the precise wording of 17c is needed, the source file should be re-OCR'd; the
provided text terminates before the question is stated in full.*

---

## Summary

All chapter-11 exercises (1-17, with 17c noted as truncated in the source) are
addressed at the analysis level: conceptual answers, algorithm/design sketches,
derivations, and complexity discussion. **No code was written or executed** for
this chapter, since TGIZMO / QP theory is outside the scope of our LTMS/LTRE port.
Where an exercise depends on book-specific files we do not have (scenarios
`ex1/ex2/ex3`, theory `tnst`, `mlang.lisp`, `translate-relations`), I described the
expected qualitative behavior and the implementation strategy rather than exact
outputs.
