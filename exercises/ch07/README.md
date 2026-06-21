# Chapter 7 -- Justification-Based Truth Maintenance Systems (JTMS)

Study solutions for the exercises in Forbus & de Kleer, *Building Problem
Solvers*, Chapter 7. Each exercise below is **paraphrased** (not quoted) and
followed by an answer. Exercises that probe observable JTMS behavior are
demonstrated in `solutions.py` against the real `ltms` JTMS; design exercises
that ask for algorithm modifications are answered in prose.

The chapter's JTMS is implemented in `src/ltms/jtms.py` (core algorithm) and
`src/ltms/jtre.py` (the JTMS-backed rule engine). References to method names
below point at that code.

Run the demos:

```
# from the repository root
. .venv/bin/activate
python exercises/ch07/solutions.py
```

---

## Exercise 1 (*) -- Why not let assumption override existing support?

**Paraphrase.** Someone claims the last branch of `enable-assumption` is wrong:
a node that already has a real supporting justification is "more solid" than a
mere assumption, so enabling it as an assumption ought to take over. What is
the flaw in that reasoning?

**Answer.** The argument has the solidity backwards. A node that already holds
via a justification (or, even stronger, via a premise) is supported *by other
beliefs*, which means it is **non-retractable on its own**: you cannot make it
go OUT just by retracting an assumption, because its support does not run
through any assumption that you can disable. Overwriting that derived support
with `ENABLED_ASSUMPTION` would do real damage:

1. **It hides the real reason.** The well-founded support, and therefore the
   explanation (`why_node`) and the set returned by `assumptions_of_node`, would
   now point at the bare assumption instead of the actual derivation. Dependency
   tracking would be wrong.

2. **It makes a stable belief spuriously retractable.** A node that should stay
   IN no matter what (because its antecedents independently hold) would suddenly
   go OUT the moment you retract the assumption. That breaks soundness of the
   labeling: the network would claim the node is unsupported when it is not.

3. **A premise must win.** If the node is a premise (antecedent-free
   justification), it holds *universally*; demoting it to an assumption would let
   you retract something that is unconditionally true.

So "already justified" is exactly the case where you should **keep** the
existing support, which is what the code does (`JTMS.enable_assumption`: if the
node is already IN via a premise or a justification, the assumption is recorded
but the support is left alone). The proposed "improvement" would replace strong,
non-retractable support with weak, retractable support, which is strictly worse.

**Demonstrated by code:** `demo_enable_assumption_rule` in `solutions.py` shows
a premise-supported node that is also made an assumption and enabled, yet keeps
its premise support (`is_premise` stays True).

---

## Exercise 2 (**) -- Propagate "premise-hood" to universally held nodes

**Paraphrase.** A node justified only by premises holds universally but is not
itself recorded as a premise. Modify the JTMS so that every universally held
node gets a premise justification (saving useless backtracks, since no
assumption set should ever be blamed for such a node). What does this cost?

**Answer.**

*Mechanism.* A node holds **universally** when it has a satisfied justification
all of whose antecedents are themselves universally held (base case: an
antecedent-free justification, i.e. a premise). Propagate the property forward:
during the normal IN sweep, when a justification fires and *every* antecedent is
already flagged universal, flag the consequent universal too and install a
premise (antecedent-free) justification on it. Concretely, add a boolean
`universal` field to `Node`; seed it on premises in `justify_node`; and in
`_propagate_inness` / `_check_justification`, when installing support, set
`consequence.universal = all(a.universal for a in just.antecedents)` and, if
True, also call `justify_node(<premise-informant>, consequence, [])`.

*Why it helps search.* Dependency-directed backtracking blames the
`assumptions_of_node` of a contradiction. If a universally-held node still
carried assumption-based support, the search could waste a backtrack "fixing" an
assumption that can never actually change that node's status. Giving such nodes
premise support makes `assumptions_of_node` return the empty set for them, so
they are never blamed.

*What we lose.*

1. **Retractability / hypothetical reasoning is destroyed for those nodes.**
   Once a node carries a real premise justification, it is IN forever in this
   JTMS (premises are never retracted). If you later want to reason
   counterfactually about whether one of the *original* premises still holds,
   the propagated premise will keep the downstream node IN even after the
   genuine cause is gone. We trade flexibility for the no-backtrack guarantee.

2. **Loss of fine-grained dependency information.** The explanation collapses:
   `why_node` reports "premise" instead of the real chain of premises that made
   it universal. We can no longer recover *which* premises were responsible.

3. **Bookkeeping / monotonicity cost.** We add justifications and a per-node
   flag, and we must be careful with cycles (a node must not be declared
   universal on the strength of a cycle that ultimately rests on an assumption).

In short: we gain backtrack pruning at the cost of losing the ability to
question or explain anything once it has been "frozen" as a premise.

---

## Exercise 3 (**) -- Propagate "contradiction-hood"

**Paraphrase.** By analogy with Exercise 2, if a contradiction has a
justification in which all antecedents but one are universally held, that last
antecedent can itself be marked contradictory. Modify the JTMS to propagate
contradictions. Note that this is only marginally useful in this JTMS, since a
contradiction merely tells the inference engine to act.

**Answer.**

*Mechanism.* Let `X` be a node already known contradictory, supported (or
supportable) by a justification `J` whose antecedents are `n` plus a set `U` of
universally-held nodes. Logically, `U` always holds, so `n ⇒ X` and `X` is a
contradiction; therefore `n` can never be IN consistently either, i.e. `n` is
itself contradictory. Implementation: maintain the `universal` flag from
Exercise 2; whenever a node is marked contradictory (`make_contradiction`) or
whenever a justification of a contradictory node is found to have all-but-one
universal antecedents, call `make_contradiction` on that remaining antecedent.
Run this as a fixpoint, because newly-marked contradictions can trigger further
propagation. Guard against cycles so a node is not declared contradictory on the
basis of support that loops back through itself.

*Why only marginal utility here.* In a pure JTMS the only thing a contradiction
does is fire `check_for_contradictions`, which signals the inference engine; the
JTMS does not itself use the extra contradictory markings to prune anything.
Knowing that `n` is "also" contradictory does not change relabeling, and the
engine would have discovered the conflict anyway when it tried to enable a
support for the original contradictory node. The propagated markings become
genuinely useful only in richer systems (e.g. ATMS nogood minimization) where
contradiction information is exploited to prune the search space directly.

---

## Exercise 4 (**) -- `assumptions-of-node` is not minimal

**Paraphrase.**
(a) Show a call sequence where `assumptions-of-node` returns assumptions that a
*different* well-founded support would not need.
(b) Write `minimal-assumptions-of-node` that returns a subset of that result
which still supports the node and has no supporting proper subset (hint: try
retracting each returned assumption and check whether the node stays IN).
(c) Give a case with more than one smallest such subset.
(d) When would the inference engine prefer the minimal version?

**Answer.**

**(a)** `assumptions_of_node` walks the *single current* well-founded support
chain, so it reports the assumptions of whichever justification happens to be
installed, even if a cheaper alternative exists. Sequence:

```
g.justify(j1, g <= a, b)     # justification 1
g.justify(j2, g <= c)        # justification 2
enable a; enable b; enable c
```

g becomes IN via j1 (installed first), so `assumptions_of_node(g) = {a, b}`.
But j2 shows `{c}` alone supports g, so `{a, b}` is non-minimal: there is an
alternative well-founded support that is not even a subset of the reported set.
**Demonstrated by code:** `demo_assumptions_of_node_superset` (reports
`['a','b']` with support `j1`).

**(b)** Algorithm (implemented as `minimal_assumptions_of_node` in
`solutions.py`): start from `S = assumptions_of_node(node)`; for each assumption
`x` in `S`, retract `x`; if the node is still IN (alternative support kicked in),
`x` was redundant -- drop it; otherwise re-enable `x`, it is required. The
survivors support the node and none can be removed. (Caveat: this greedy
single-pass routine finds *a* minimal-by-removal set; restoring an assumption
that was already dropped is unnecessary because removal only ever happens when an
alternative is found, but a fully rigorous version should re-check at the end.)
In the demo, starting from `{a, b}` the routine retracts `a` (g stays IN via j2)
then `b` (still IN via j2), so it returns `{}` -- `c` provides support all along,
which is exactly the "alternative support not in the original set" point.

**(c)** Multiple smallest subsets exist when the node has two (or more)
single-assumption justifications that are *both* outside the current support:

```
g.justify(j1, g <= a, b)   # current support
g.justify(j2, g <= c)
g.justify(j3, g <= d)
enable a, b, c, d
```

After minimizing from `{a, b}`, either `{c}` or `{d}` is a smallest supporting
set; neither contains the other. Which one a procedure lands on depends on the
order alternative supports are tried. (Truly enumerating *all* minimal supports
requires examining every justification, not just retract-and-test, which is the
ATMS's job in later chapters.)

**(d)** A backtracking inference engine benefits from minimal sets when
resolving a contradiction: the smaller the blamed assumption set (the nogood),
the more general the constraint learned and the fewer future contexts pruned
unnecessarily. Using `assumptions_of_node` directly can blame irrelevant
assumptions, causing the engine to retract things that had nothing to do with
the conflict and to record an overly specific nogood. Minimal sets give tighter
nogoods and better-targeted backtracking.

**Demonstrated by code:** `demo_assumptions_of_node_superset` and
`demo_alternative_support_switch`.

---

## Exercise 5 (**) -- Count-based justification satisfaction

**Paraphrase.** With many justifications, repeatedly re-checking whether each is
satisfied is expensive. Keep, per justification, a count of how many antecedents
are currently OUT (or, dually, IN); when the count of OUT antecedents hits zero
the consequent is supportable. Avoid circular support.

**Answer.**

*Design.* Give each `Justification` an integer `out_count` initialized to the
number of antecedents. Whenever an antecedent flips OUT->IN, decrement the
`out_count` of every justification that lists it; whenever it flips IN->OUT,
increment. A justification is satisfied exactly when its `out_count == 0`. This
turns the O(antecedents) `_justification_satisfied` scan into O(1) per event,
and we only revisit a justification when one of its antecedents actually
changes (we already iterate `node.consequences` on a label change, so the
decrement happens right there). Antecedent-free justifications start at count 0
and are satisfied immediately, matching premise semantics.

*Avoiding circularities.* The danger is declaring a node supportable on the
strength of support that ultimately depends on the node itself. The standard
fix, which the count scheme must preserve, is the JTMS's **two-phase
retraction**:

1. *Phase 1 (outness):* before looking for new support, label OUT every node
   whose *current* support flows through the changed node, and increment counts
   accordingly. This guarantees no node is still claiming circular support.
2. *Phase 2 (find support):* only now scan justifications with `out_count == 0`
   to re-derive nodes, installing well-founded support.

The count is purely a satisfaction cache; correctness still comes from doing
outness fully before inness, so a node can never be re-supported via a
justification that (transitively) depends on the node we just took OUT. (This
mirrors how `ltms/jtms.py` separates `_propagate_outness` from
`_find_alternative_support`.)

---

## Exercise 6 (**) -- Cache nogoods to abort doomed relabeling

**Paraphrase.** In dependency-directed search driven by enabling/retracting
assumptions, the JTMS may do a lot of relabeling only to discover a
contradiction at the end. Record every assumption set known to support a
contradiction (a *nogood*); when a new assumption is enabled, first check
whether the resulting assumption set contains a known nogood, and if so abort
relabeling and immediately signal a contradiction. Implement this, and explain
why simply installing a contradictory justification for each conflicting
assumption set accomplishes little.

**Answer.**

*Design.* Maintain a global `nogoods: list[frozenset[Node]]` of minimal
assumption sets known to be inconsistent. In `enable_assumption`, *before*
calling `_propagate_inness`, compute the prospective enabled-assumption set
`A = enabled_assumptions() ∪ {node}` and test `any(ng <= A for ng in nogoods)`.
If some nogood is a subset, skip relabeling entirely and call the contradiction
handler directly (the engine must back out). When a contradiction *is* reached
the normal way, record `frozenset(assumptions_of_node(contradiction_node))`
(ideally the minimal set from Exercise 4b) into `nogoods`. Keep the list
subset-minimal so the membership test stays cheap.

*Why the "just install a contradictory justification" idea fails.* Adding, for
each known-bad assumption set, a justification
`{a1, ..., ak} => contradiction-node` does **not** save the work this exercise
targets, because that justification only fires *after* all of `a1..ak` have been
relabeled IN. In other words, the JTMS still performs the entire forward
relabeling sweep to make those assumptions and their consequences IN, and only
*then* notices the contradiction -- exactly the wasted effort we wanted to
avoid. It also pollutes the network with extra justifications that have to be
maintained on every retraction. The point of nogood caching is to short-circuit
**before** relabeling, using a cheap set-subset test, which a justification can
never do because justifications are evaluated only by propagation, not by
look-ahead.

**Partly demonstrated by code:** `demo_contradiction_and_culprits` shows the
JTMS signaling a contradiction and `assumptions_of_node` recovering the culprit
set `{p, not-p}` -- the very set you would store as a nogood. (The look-ahead
caching itself is an algorithm modification, not in the current public JTMS.)

---

## Exercise 7 (**) -- One-blocker-per-justification scheme

**Paraphrase.** Design a JTMS that records, for each justification, a single
node currently *preventing* it from being a supporting justification, and for
each node, the list of justifications it is currently blocking. Explain when
this is more efficient.

**Answer.**

*Design.* This is the truth-maintenance analogue of the **two-watched-literal**
trick (and indeed of the watched-literal scheme used in `ltms/watched.py` for
the LTMS). A justification needs *all* antecedents IN to fire. Instead of
re-scanning all antecedents on every change, store one **blocker**: a single
antecedent that is currently OUT. Maintain `node.blocking: list[Justification]`,
the justifications for which this node is the recorded blocker. Invariants and
updates:

- A justification with a non-None blocker is **not** satisfiable and is ignored.
- When a node goes IN, we only need to revisit the justifications in its
  `blocking` list (the ones it was holding up). For each, look for *another* OUT
  antecedent: if found, move the blocker pointer there (re-watch); if none
  remains, the justification is now satisfied -- fire it.
- When a node goes OUT, any justification that had no blocker and listed this
  node now acquires this node as its blocker (cheap: just set the pointer).

*When it is more efficient.* Big win when justifications have **many
antecedents** and antecedents change status **frequently**: a status flip then
touches only the justifications actually watching that node, not every
justification mentioning it, and re-scanning for a new blocker is amortized.
For justifications with one or two antecedents the bookkeeping overhead can
outweigh the savings, so it pays off precisely in the large-fan-in, high-churn
regime -- the same setting that motivates Exercise 5's counters, of which this
is a lazier, pointer-based alternative.

---

## Exercise 8 (***) -- Derivation-depth scheme instead of IN/OUT propagation

**Paraphrase.** Design a JTMS that, rather than propagating IN/OUT labels,
stores with each justification a *derivation count* (the maximum number of
justifications between it and an assumption/premise, or infinity if it does not
hold) and with each node the *minimum* such depth over its supporting
justifications. Explain how retraction works when cycles are present, and
suggest other uses for the depth count.

**Answer.**

*Representation.* Define, for a node `n`, `depth(n)` = minimum over its
justifications `J` of `depth(J)`, where
`depth(J) = 1 + max(depth(a) for a in antecedents(J))`, with `depth = 0` for
premises/enabled assumptions and `depth = ∞` for a justification with any
infinite-depth antecedent. A node is **IN** iff `depth(n) < ∞`. This is exactly
a shortest-/longest-path computation on the justification DAG: the node's depth
is its distance from the assumption/premise layer along its *cheapest* support,
where the cost of a support is the *longest* chain it forces (the `max` over
antecedents). Forward propagation is then a relaxation: when an antecedent's
depth decreases, recompute affected justifications and push improvements.

*Retraction with cycles.* The hard case is a node whose only remaining support
forms a cycle: in a naive depth scheme each cycle member could keep a finite
depth by pointing at the next, giving **ill-founded circular support**. The
`max`-of-antecedents rule actually guards against this on the *deriving* side
(a real well-founded chain has strictly increasing depth, so a cycle cannot
manufacture a finite depth from nothing), but on retraction you must invalidate
correctly. The robust procedure mirrors two-phase relabeling:

1. *Invalidate:* set `depth = ∞` for the retracted node and, transitively, for
   every node whose current best support runs through it. Because depth is
   defined by the *forced longest chain*, a cycle that only supported itself now
   has every member at `∞` (no member can claim a finite depth that does not
   ultimately bottom out at a premise/assumption).
2. *Recompute:* run the relaxation from the still-valid (finite-depth) frontier
   outward; only nodes with a genuine path back to depth 0 regain a finite
   depth. Cycles with no external grounding stay at `∞` (correctly OUT).

Using a Dijkstra/Bellman-Ford-style frontier (process nodes in increasing
recomputed depth) makes both phases terminate and keeps the well-founded
property: a node gets a finite depth only via a strictly-shorter-grounded
support, so circular re-derivation is impossible.

*Other uses for the depth count.*

- **Best-first / shortest-proof explanation:** follow minimum-depth
  justifications to produce the *shortest* well-founded proof, not just any one.
- **Search ordering and cost estimation:** depth approximates inference effort,
  so an engine can prefer shallow derivations or prune deep ones.
- **Cheap cycle / self-support detection:** an `∞` depth that fails to resolve
  during recomputation flags an ungrounded cycle.
- **Incremental change scoping:** a label flip only needs to touch nodes whose
  depth could actually change, bounding the propagation work.

---

## Summary of code-demonstrated exercises

| Exercise | Type | Demonstrated in `solutions.py` |
|---|---|---|
| 1 | Behavior / explanation | `demo_enable_assumption_rule` |
| 2 | Algorithm modification | prose only |
| 3 | Algorithm modification | prose only |
| 4a-4c | Behavior + procedure | `demo_assumptions_of_node_superset`, `demo_alternative_support_switch`, `minimal_assumptions_of_node` |
| 5 | Algorithm modification | prose only |
| 6 | Algorithm modification | partly (`demo_contradiction_and_culprits` shows the nogood set) |
| 7 | Algorithm design | prose only |
| 8 | Algorithm design | prose only |

Plus `demo_jtre_belief_revision`: an end-to-end JTRE belief-revision demo
(assume, justify, retract) showing the JTMS taking a derived fact OUT when its
sole supporting assumption is retracted.
