# Chapter 14: Putting the ATMS to Work — Exercise Solutions

**ANALYSIS ONLY.** The ATMS-based problem-solving system of this chapter (the ATMS
itself, ATRE, the focused/suggestions control architecture, and the Blocks-World
planners `plan-a`/`plan-e`) is **not implemented in this package** (it is explicitly
a non-goal — see `BRIEFING.md`). Therefore every answer below is a conceptual /
design / complexity / derivation answer. There is **no runnable code** and no
`solutions.py`; `codeRuns` is reported as `false`.

Exercise statements are my own paraphrases of the copyrighted text, not quotations.

Conventions used below:
- *ATMS* = assumption-based TMS. A **node** carries a **label**: a set of
  **environments**, where each environment is a minimal, consistent set of
  **assumptions** under which the node holds. Labels are kept *sound, consistent,
  complete, and minimal*.
- A **nogood** is an environment known to be contradictory.
- *ATRE* = the ATMS-coupled rule engine; rules trigger on `:IN`, `:INTERN`, etc.
- *STRIPS operator* = preconditions + add-list + delete-list.

---

## Exercise 1 (*) — Dropping the antisymmetry / antireflexivity laws in Blocks World

**Paraphrase.** Take the symmetry-excluding (`On(x,y)` and `On(y,x)` cannot both
hold) and irreflexivity (`On(x,x)` cannot hold) laws out of the Blocks-World
axioms. In the three-block envisionment produced by `plan-e`, does removing them
create extra states? And if those laws had been written with an `:IN` trigger
rather than an `:INTERN` trigger, would they ever fire at all?

**Answer.**
These two laws are **pruning / consistency** axioms: they fire to assert a
contradiction (a nogood) when a physically impossible configuration is proposed.
They never *generate* configurations; they only *kill* them.

- *Does removing them add states?* It depends on whether the rest of the
  formalization (the STRIPS operator preconditions for `move`/`puton`, the
  `clear`/`on` bookkeeping, and the "at most one block on a block" restriction)
  already forbids the offending configurations. In the standard formalization the
  operator preconditions require the moved block and its destination to be
  `clear`, and `clear(x)` is false once something is `on x`. That precondition
  structure **already** prevents reflexive `On(x,x)` (you can't put `x` on `x`
  because moving `x` first makes `x` not clear / not at its source) and prevents
  the two-cycle `On(x,y) ∧ On(y,x)` (putting `y` on `x` requires `x` clear, but
  `x` is under nothing only if `On(y,x)` is not yet asserted; the geometric
  one-on-one constraint blocks the cycle). So with the usual operators, removing
  antisymmetry/antireflexivity yields **no new reachable states** — the impossible
  states were already unreachable by construction. The laws are *redundant given
  the operators*; they exist as defensive/explanatory constraints. (If the
  operator set were sloppier, e.g. allowed asserting `on` without the `clear`
  precondition, then yes, removing the laws would let cyclic/reflexive states
  appear.)

  Concretely for three blocks `{A,B,C}` plus the table: the number of legal towers
  is unchanged (13 states; see Ex. 2), because antisymmetry/antireflexivity only
  excluded already-illegal stackings.

- *`:IN` instead of `:INTERN`?* An `:INTERN` trigger fires the rule once, for the
  *generic/interned* pattern, independent of any particular environment — it
  installs the constraint structurally for every matching instance. An `:IN`
  trigger fires only when the triggering datum is *believed in the current focus
  environment*. A consistency law like antisymmetry asserts a contradiction
  exactly in those environments where both `On(x,y)` and `On(y,x)` are believed —
  but those environments are **nogoods**, i.e. inconsistent, so the antecedents
  are *never simultaneously `:IN`* in any consistent focus. Hence with an `:IN`
  trigger the law would **never execute**: the precondition (both `on` facts
  believed together) can only be met in an environment that the law itself would
  declare nogood, so it is never `:IN`. This is exactly why such pruning laws are
  written `:INTERN` — they must run on the *pattern* to detect the conflict and
  create the nogood, rather than waiting for the (impossible) belief state.

---

## Exercise 2 (**) — Counting states and transitions of an N-block envisionment

**Paraphrase.** Derive a closed-form (or recurrence) for the number of distinct
states, and another for the number of transitions, in the complete envisionment of
N blocks.

**Answer.**

**States.** A Blocks-World *state* with N distinct labeled blocks on a table is a
set of vertical towers — i.e. a partition of the N blocks into ordered stacks,
where the stacks themselves are unordered (the table has no left/right). The count
`a(N)` of such configurations satisfies

> a(N) = number of ways to partition an N-set into a set of *linearly ordered*
> blocks (sequences) = the number of "sets of lists" =
> Σ_{k=1}^{N} (number of ways to split N labeled items into k nonempty ordered
> lists, lists unordered among themselves).

These are the **arrangement / "sets of sequences" numbers** (OEIS A000262),
satisfying the recurrence

> a(0) = 1, a(1) = 1,
> a(N) = (2N − 1)·a(N−1) − (N−1)(N−2)·a(N−2).

Values: a(1)=1, a(2)=3, a(3)=13, a(4)=73, a(5)=501, a(6)=4051, ...
A closed form is a(N) = N! · Σ_{k=0}^{N−1} C(N−1,k)/k!  (equivalently the
coefficient form of e^{x/(1−x)}). For **three blocks this gives 13 states**, which
matches the chapter's three-block envisionment.

(If one instead distinguishes "on table" positions or counts only fully-specified
towers differently, the constant changes, but the standard one-arm Blocks World
uses A000262. I assume the standard one-gripper, table-is-a-set model.)

**Transitions.** A transition is one operator application: pick the top (clear)
block of some tower and either (a) put it on the table, or (b) put it on top of
some other tower's clear top. From a state, the number of *applicable moves* equals

> (number of clear blocks not already alone on the table that can go to the table)
> + (ordered pairs of distinct clear tops, for stack-on-stack moves).

Rather than a single clean closed form for the *total* transition count, the clean
result is the **average branching factor times state count**. Counting directed
edges over the whole envisionment: in a state with t towers there are t clear
tops; each clear top can move onto the table (unless it is already a singleton on
the table) or onto any of the other (t−1) clear tops, giving up to
t + t(t−1) − (singletons-to-table) candidate moves. Summing applicable moves over
all a(N) states gives the transition total T(N). A useful **upper bound** is

> T(N) ≤ a(N) · ( N + N(N−1) ) = a(N) · N²  (very loose),

and a tighter accounting is T(N) = Σ_states [ (#clear tops)·(#clear tops − 1) +
(#non-singleton clear tops) ]. The graph is **undirected-reversible up to operator
choice**: every "put X on Y" move has an inverse "put X on table / elsewhere," so
the transition relation is symmetric in reachability. For three blocks the
hand-enumeration yields the chapter's transition count (on the order of 30+ directed
edges); the key deliverable is the recurrence/closed form above for states and the
per-state summation formula for transitions.

---

## Exercise 3 (**) — `explore-network` for the ATMS with environment + keyword args

**Paraphrase.** Port the `explore-network` debugging browser to the ATMS. Beyond
the usual arguments it takes an *environment* and a *keyword*: with `:IMPLIED-BY`,
display only nodes/justifications that hold *in* (are implied by) the given
environment; with `:CONSISTENT`, display only nodes/justifications whose labels are
*consistent with* the given environment.

**Answer (algorithm sketch).**
`explore-network` is an interactive graph walker: it prints the current node, its
justifications (with antecedent nodes) and its consequences, then lets the user
step to a neighbor. The ATMS version adds a **visibility filter** parametrized by
`(env, mode)`:

```
explore-network-atms(start-node, env, mode):
    cur = start-node
    loop:
        print-node(cur)                       # name + label
        ins  = [j for j in justifications-in(cur)  if visible-just(j, env, mode)]
        outs = [c for c in consequences(cur)       if visible-node(c, env, mode)]
        print antecedent justifications `ins`, consequence nodes `outs`
        read user choice -> set cur to a chosen neighbor, or quit
```

Visibility predicates (the only new logic):

- **node-holds-in(node, env)** = ∃ E ∈ label(node) with E ⊆ env. (env entails one
  of the node's environments → node is believed in env.)
- **label-consistent-with(node, env)** = ∃ E ∈ label(node) with E ∪ env not a
  nogood (i.e. E ∪ env is a consistent environment). For the standard ATMS where
  labels are already consistent, this reduces to: some environment of the node can
  be merged with `env` without hitting a recorded nogood.

```
visible-node(n, env, mode):
    mode == :IMPLIED-BY -> node-holds-in(n, env)
    mode == :CONSISTENT -> label-consistent-with(n, env)

visible-just(j, env, mode):
    # a justification is shown iff all its antecedents are visible AND
    # the conjunction (union of one chosen env per antecedent) is itself
    # implied-by / consistent-with env, depending on mode
    mode == :IMPLIED-BY -> every antecedent holds-in env
    mode == :CONSISTENT -> the environment formed by unioning one consistent
                           env from each antecedent with `env` is not a nogood
```

**Cost.** Each visibility test is a subset/nogood check over the label, O(|label| ×
|env|) for `:IMPLIED-BY` and additionally a nogood lookup for `:CONSISTENT`. The
two modes differ exactly in *strength*: `:IMPLIED-BY` shows the cross-section of the
network you *currently believe* under `env` (good for "why do I believe this here"
debugging); `:CONSISTENT` shows everything that *could* still be believed if you
extended `env` (good for "what is reachable / not yet ruled out" debugging). The
two additional arguments thus turn one browser into a believed-view and a
possibility-view of the same ATMS graph.

---

## Exercise 4 (**) — Efficient `:IN` rule execution via `remove-node`

**Paraphrase.** Use the ATMS primitive `remove-node` to build an efficient
mechanism for firing rules that have `:IN` triggers.

**Answer (design).**
The naive way to implement an `:IN` trigger ("fire when this datum is believed in
the current focus") is to re-test, on every label change anywhere, whether the
trigger node now holds in the focus — O(rules × label-churn), which is wasteful
because most label changes are irrelevant.

The efficient trick uses a **disjunction / monitor node** plus `remove-node`:

1. For an `:IN` trigger on node `n`, install a special **trigger node** `T_n`
   justified by `n` (so `T_n` becomes believed exactly when `n` is `:IN` in the
   focus). Queue the rule body on `T_n`'s "becomes-in" hook.
2. When the focus enables the rule to fire, the rule **executes once** and then we
   no longer need the monitor structure to keep tracking it (an `:IN` trigger is
   "fire on first belief," not a persistent constraint). At that point call
   `remove-node(T_n)` to delete the trigger node and its justification from the
   network.

Why `remove-node` matters: without it, every transient monitor node accumulates and
keeps participating in label propagation forever, so adding K `:IN` rules
permanently grows the network by K nodes and degrades all future label updates.
`remove-node` retracts the node *and* the justifications mentioning it and patches
the labels of anything that depended on it, so the monitor cost is **paid once and
reclaimed**, giving amortized O(1) extra network burden per `:IN` rule fired rather
than O(rules) permanent overhead. The net effect: `:IN`-triggered rules become
"one-shot" subscriptions that clean up after themselves, which is the efficient
mechanism asked for. (This presupposes `remove-node` correctly handles dependent
relabeling, which is the chapter's stated motivation for providing it.)

---

## Exercise 5 — Generalizing "at most one block on a block": `straddles` / `straddlers`

Replace `clear`/`on` by two set-valued relations: **straddles(b)** = the set of
things block `b` rests on (a block can rest on several), and **straddlers(b)** =
the set of blocks resting on `b`.

### 5a (*) — STRIPS extensions needed

**Paraphrase.** What must change in the STRIPS operators so they correctly maintain
state described by `straddles`/`straddlers` rather than `clear`/`on`?

**Answer.** With `clear`/`on`, each operator's add/delete list touches a **fixed,
small** number of literals (move X from Y to Z: delete `on(X,Y)`, `clear(Z)`; add
`on(X,Z)`, `clear(Y)`). With set-valued straddles/straddlers, the operator must
edit *set membership*, which standard STRIPS cannot express directly because the
literals to add/delete depend on the **current contents of the sets** (how many
blocks straddle the support, etc.). Required extensions:

- Replace the precondition `clear(Z)` (Boolean) with a **cardinality / set
  condition** on `straddlers(Z)` (e.g. "room remains" or "Z can bear another"),
  since multiple blocks may straddle Z now.
- The add-list must add `X` to `straddles`-set membership for each support `s` that
  `X` will rest on, and add `X` to `straddlers(s)` for each such `s`.
- The delete-list must remove `X` from `straddlers(old-support)` and remove the old
  supports from `straddles(X)`.
- Because a block may rest on *several* supports and support *several* blocks, the
  add/delete lists are **parameterized by the current state** (their contents are
  not known until instantiation). This is precisely the "partially specified
  add/delete list" need that recurs in Ex. 8d.

### 5b (**) — New laws and operators using straddles/straddlers

**Paraphrase.** Define a fresh set of domain laws and operators using
straddles/straddlers as the primitives.

**Answer (formalization sketch).**

Domain laws (invariants):
- **Mutual consistency:** `s ∈ straddles(b)  ⟺  b ∈ straddlers(s)`.
- **Acyclicity:** the "rests-on" relation induced by straddles is a strict partial
  order (no block transitively straddles itself). This replaces antisymmetry +
  antireflexivity from Ex. 1, now lifted to a transitive closure constraint.
- **Support / capacity:** an admissibility predicate `supports(s, S)` saying the
  set `S = straddlers(s)` is a physically allowed load for `s` (in the simplest
  model, `|straddlers(s)| ≤ k` for some capacity `k`; for plain Blocks World `k=1`,
  recovering the original).
- **Groundedness:** every block transitively straddles the `table`.

Operators (generalized `puton`):
- `puton(X, Supports)` where `Supports ⊆ blocks ∪ {table}`:
  - **pre:** `X` is "top-free" (`straddlers(X)` empty, or empty enough to be
    liftable) and every `s ∈ Supports` admits `X` (capacity check on
    `straddlers(s) ∪ {X}`).
  - **delete:** for each old support `o ∈ straddles(X)`: remove `X` from
    `straddlers(o)` and `o` from `straddles(X)`.
  - **add:** for each `s ∈ Supports`: add `s` to `straddles(X)` and `X` to
    `straddlers(s)`.
- `move-to-table(X)` is the special case `puton(X, {table})`.

### 5c (***) — Implement and test

**Paraphrase.** Implement the extended planner with the straddles/straddlers
formalization and exercise it on several problems.

**Answer (out of scope — design only).** Implementation requires the chapter's
ATMS planner, which this package does not provide, so this is left as a design.
The implementation plan: (1) represent `straddles`/`straddlers` as ATMS-tracked set
facts (one node per membership literal `member(b, straddlers(s))`); (2) implement
the parameterized add/delete computation from 5a by quantifying over the
*believed* membership literals in the current focus environment; (3) reuse the
acyclicity and capacity laws as `:INTERN` consistency rules that post nogoods.
Tests would include: a 3-block tower rebuild, a "two blocks both resting on one
wide block" (capacity k=2) case that the original `clear`/`on` model cannot
express, and a regression that with capacity k=1 the envisionment reproduces the 13
states of Ex. 2. **Not implemented here.**

---

## Exercise 6 — `clear` as a default assumption

A block is *presumed clear* unless something is known to be on it.

### 6a (*) — What gets simpler vs. harder

**Paraphrase.** If `clear` becomes a default (assumed clear absent evidence of a
block on top), which parts of the implementation simplify and which get harder?

**Answer.**

- **Simpler:** We no longer assert and retract `clear` literals explicitly with
  every move. Operators stop maintaining the `clear` add/delete bookkeeping
  entirely; the truth of `clear(b)` is derived. Initial-state specification gets
  shorter — you only state the `on` facts; everything not under something is
  automatically clear. This eliminates a whole class of "forgot to update clear"
  bugs.
- **Harder / more complicated:** `clear` is now **non-monotonic** (a default that
  must be *defeated* when an `on(_, b)` becomes believed). You need an ATMS
  assumption node `clear(b)` plus a defeating justification: `on(x,b) ⊢ ¬clear(b)`,
  and a nogood linking the assumption with the defeater. Operator **preconditions**
  that test `clear` must now query the assumption-under-the-focus rather than a
  plain fact, and the planner must handle environments where the default holds vs.
  where it is overridden. Contradiction handling grows: putting a block on `b`
  while `clear(b)` was assumed must retract/override the default cleanly. So
  belief-revision complexity moves from the operator code into the TMS, which is
  exactly the trade ATMS defaults are meant to make.

### 6b (**) — Implement and re-verify `plan-a` examples

**Paraphrase.** Make the change and show the `plan-a` examples still work.

**Answer (out of scope — design only).** Requires the chapter planner. Plan:
declare `clear(b)` as an ATMS assumption for every block, add the defeater
justification `on(?x,b) → ¬clear(b)`, and replace precondition lookups of `clear`
with focus-relative belief checks. Verification = rerun the chapter's `plan-a`
example suite and confirm identical solution plans (the default formulation should
be *behaviorally equivalent* on those examples, since they never rely on a block
being non-clear-but-unknown). **Not implemented here.**

### 6c (*) — A `drop` operator: original formulation vs. default-clear

**Paraphrase.** Consider `drop`: beforehand the gripper holds a block, afterward it
does not. Can the original Blocks-World formulation implement it? Can the
default-clear formulation?

**Answer.** `drop` removes a block from the gripper without specifying *where* it
ends up resting in a fully determined way — its landing/support depends on context.

- **Original (explicit `clear`) formulation:** awkward/impossible to capture
  cleanly as a single STRIPS operator, because the operator's add-list would need
  to assert `on(X, ?)` for an *under-determined* support and update the `clear` of
  whatever it lands on, but STRIPS add/delete lists must be fixed at definition
  time. You cannot enumerate "whatever it lands on" statically. So plain STRIPS +
  explicit clear cannot represent `drop` faithfully (you'd have to pre-commit to a
  specific destination, which is `puton`, not `drop`).
- **Default-clear formulation:** more natural. With `clear` derived as a default,
  `drop` need only assert `holding` becomes false and assert the new resting
  `on(X, landing)`; the `clear` of the landing block is then *automatically
  defeated* by the default machinery — no explicit `clear` delete is needed. The
  default absorbs the bookkeeping that made `drop` hard before. (It still needs the
  landing support determined, but it no longer needs the brittle `clear` updates.)

### 6d (**) — Implement `drop`; effect on the envisionment

**Paraphrase.** Implement `drop` and describe how it changes the 3-block (and
N-block) envisionment.

**Answer (out of scope for code; effect analysis given).** Adding `drop` does **not
add reachable *states*** (the set of legal towers is unchanged — `drop` reaches
configurations already reachable by `puton`/`move-to-table`). It **adds
*transitions*** (extra edges/operator instances into existing states), increasing
the branching factor and hence the envisionment's edge count and search cost. For
three blocks the state count stays 13 (Ex. 2); the transition count rises because
each "remove block from gripper to a support" now has a `drop` realization in
addition to the deliberate `puton`. For N blocks the state count stays a(N)
(A000262) while transitions grow roughly proportionally to the number of
clear-top landing sites per state. **Not implemented here.**

---

## Exercise 7 — Casino Robot (`grab-dice`, `shoot`, `Score(n)`)

`grab-dice` puts the table's dice into the (shaken) gripper; `shoot` spills them
onto the table; `Score(n)` is true iff the showing faces sum to `n`.

### 7a (**) — Computing odds with the chapter's planners

**Paraphrase.** Assuming fair dice, how would you use this chapter's planning /
envisioning machinery to compute the probabilities of the various `Score(n)`
outcomes?

**Answer.** Model the shaken dice as a **choice / disjunction over assumptions**:
after `grab-dice` (shaken), introduce two assumption sets, `face1 ∈ {1..6}` and
`face2 ∈ {1..6}`, with the mutual-exclusion nogoods that pick exactly one face
each. `shoot` then makes the chosen faces visible and derives
`Score(face1+face2)`. The ATMS **envisions all 36 assumption combinations** as 36
environments; each consistent leaf environment corresponds to one equiprobable
outcome (uniform because the dice are fair and the 36 environments are
symmetric). To get the odds of `Score(n)`:

> P(Score(n)) = (number of consistent leaf environments whose label contains
>               `Score(n)`) / 36.

The ATMS label of node `Score(n)` is exactly the set of `(face1,face2)`
environments producing sum `n`, so **counting the environments in that label**
gives the count of favorable outcomes directly. This yields the standard 2d6
distribution (P(7)=6/36, P(2)=P(12)=1/36, ...). The key idea: the envisionment
*is* the sample space, and ATMS label cardinality *is* the favorable-outcome count,
so probability = |label(Score(n))| / |total leaf environments|.

### 7b (**) — Implement the Casino Robot domain

**Paraphrase.** Implement the domain model, using whatever extensions earlier
problems require.

**Answer (out of scope — design only).** Requires ATRE/ATMS. Plan: `grab-dice`
asserts `in-gripper(dice) ∧ shaken`; the shaken state spawns the 6×6 face
assumptions with per-die "exactly one face" mutual-exclusion nogoods; `shoot`
asserts `on-table(dice)` and justifies `Score(f1+f2)` from the two chosen faces.
Then read odds from label cardinalities per 7a. **Not implemented here.**

---

## Exercise 8 — Adding `color` and the `paint` operator

### 8a (*) — `paint` as a STRIPS operator

**Paraphrase.** Write `paint(B, c)` (which sets B's color to `c` regardless of
prior color) as a STRIPS operator.

**Answer.**
```
paint(B, c):
  pre:    block(B), color(c)            ; (optionally: clear(B) or accessible(B))
  delete: color(B, ?old)               ; remove B's previous color literal
  add:    color(B, c)
```
The `delete: color(B, ?old)` is a small generalization: it deletes whatever current
`color(B, _)` literal holds. In strict STRIPS you encode this either with a
variabilized delete (delete every `color(B,*)`) or by maintaining a single
functional `color(B)` whose old value is removed. This is still a *fully specified*
operator because exactly one block (B) and one color (c) are involved.

### 8b (*) — Other Blocks-World changes needed for color

**Paraphrase.** What else in the domain must change to support color?

**Answer.**
- Add `color` to the **state representation** (a `color(b, _)` literal per block)
  and to the **initial-state** description (every block needs an initial color, or
  color must be a default/unknown).
- Decide a **frame** policy: movement operators (`move`, `puton`) must *not* touch
  color, and `paint` must *not* touch position — i.e., color and location are
  independent fluents, so the existing operators' add/delete lists are unchanged but
  the planner's frame assumptions must carry `color` across non-paint actions.
- If color participates in goals, the **goal language** and matcher must handle
  color literals.
- In the ATMS/envisionment, color **multiplies the state space**: with C colors and
  N blocks, the geometric a(N) states each split into up to C^N colorings, so the
  envisionment grows by a factor up to C^N unless color is left as an irrelevant
  default.

### 8c (*) — Why "spreading" paint breaks standard STRIPS

**Paraphrase.** If `paint(B, c)` also recolors every block resting (transitively)
on B — so painting the bottom of a tower paints the whole tower — explain why
plain STRIPS cannot encode this.

**Answer.** A STRIPS add/delete list is **fixed at operator-definition time** and
may not depend on the state it is applied to. But "all blocks transitively on B"
is a **state-dependent set**: which blocks get recolored, and how many, depends on
the current tower structure (on `(On A table),(On B A),(On C B)` painting B
recolors A? no — recolors B and everything above B: B and C; the example paints
all three by painting the table-block, i.e. the set is determined by the current
`on` chain). Since the add-list (`color(x,c)` for each `x` above B) cannot be
written down without inspecting the present state, it is a **universally
quantified / conditional effect**, which lies outside the (propositional,
context-independent) STRIPS add/delete formalism. Standard STRIPS would need a
separate operator instance per possible tower shape, which is not finitely
specifiable in general. (This is exactly the motivation for ADL / conditional
effects / quantified effects.)

### 8d (***) — Operators with partially specified add/delete lists

**Paraphrase.** Extend the operator machinery to allow add/delete lists that are
only partially specified (computed at apply-time), and demonstrate it on mixed
move + spreading-paint problems.

**Answer (out of scope — design only).** Requires the chapter planner. Design:
generalize an operator's effects from a static list to a pair of **effect
*generators*** — functions that, given the operator binding and the current
believed state (focus environment), *compute* the literals to add and delete by
quantifying over matching state facts (e.g., "for each `x` with `above(x, B)`,
add `color(x, c)` and delete its old color"). Under the ATMS this is natural: the
generator queries the believed `above`/`on` literals in the current environment and
emits per-instance justifications. Demonstration would solve a problem requiring a
block move *and then* a spreading paint, checking that color propagates exactly to
the post-move tower members. **Not implemented here.**

---

## Exercise 9 — Two more rule-triggering strategies: `:EACH-IN` and `:CONSISTENT-WITH`

`:EACH-IN` — queue the rule when *each* trigger is `:IN` (believed) *individually*.
`:CONSISTENT-WITH` — queue the rule when the triggers are *consistent with* the
current focus.

### 9a (*) — Do they require an ATMS?

**Paraphrase.** Do these two strategies need an ATMS, or can a single-context TMS
support them?

**Answer.**

- **`:EACH-IN`** does **not** require an ATMS. "Each trigger believed (somewhere /
  individually)" is a condition any TMS that can report a datum's belief status can
  evaluate. In a single-context (J/L)TMS, `:EACH-IN` degenerates to "each trigger
  is currently IN," which the JTMS already supports — so no assumption sets are
  needed. (It is *weaker* than requiring the conjunction to be jointly believed.)
- **`:CONSISTENT-WITH`** **does** require an ATMS (or equivalent multi-environment
  reasoning). "Consistent with the focus" is a statement about whether the triggers
  *could* be believed together in some extension of the current environment without
  hitting a nogood. Determining that requires the ATMS notion of environments and
  recorded nogoods; a single-context TMS only knows the one current belief set and
  cannot answer "is this jointly *possible*," only "is this currently *true*."

### 9b (*) — Are they useful?

**Paraphrase.** Argue whether each strategy is useful, with examples.

**Answer.**

- **`:EACH-IN` — useful but narrow.** It fires speculatively when each premise has
  *independent* support, even if the premises have never co-occurred in one
  context. Useful for **opportunistic / heuristic** forward chaining: e.g., a
  diagnosis rule "if symptom A is plausible and symptom B is plausible, consider
  hypothesis H" that you want to *propose* whenever both symptoms have shown up
  somewhere, not only when both are jointly established. Risk: it can fire on
  premises that are individually believable but **mutually inconsistent** (A in one
  context, B in a contradictory context), producing spurious work — so it suits
  suggestion-generation, not sound deduction.
- **`:CONSISTENT-WITH` — useful for focused search / generation.** It fires a rule
  whenever its triggers *don't conflict* with the current focus, which is ideal for
  **possibility exploration**: e.g., a constraint-satisfaction generator "if placing
  queen here is consistent with the board so far, try it" or a planner that proposes
  an action whenever its preconditions are *not yet ruled out*. It avoids both
  over-eager firing (it respects nogoods) and over-strict firing (it doesn't demand
  the triggers already be proven). The example contrast: in cryptarithmetic,
  `:CONSISTENT-WITH` lets you propose a digit assignment as long as it doesn't clash
  with committed assignments — exactly the desired branch-generation behavior.

### 9c (**) — Implement and evaluate `:EACH-IN`

**Answer (out of scope — design only).** Requires ATRE. Design: when any single
trigger becomes `:IN`, check whether *every other* trigger of the rule is `:IN`
(in any/its-own support); if so, enqueue. Implementation cost ≈ per-trigger
belief check; evaluation would compare rules fired and wasted firings vs. strict
conjunctive `:IN`. Expectation: more firings, more speculative (some wasted on
mutually-inconsistent premise combinations). **Not implemented here.**

### 9d (**) — Implement and evaluate `:CONSISTENT-WITH`

**Answer (out of scope — design only).** Requires ATMS focus + nogoods. Design:
on a focus change or trigger label change, enqueue the rule iff the union of (one
environment per trigger) with the focus is not a nogood. Evaluation: measure how
much it prunes vs. unconditional firing on a focused search (e.g., N-queens /
cryptarithmetic). Expectation: strong pruning when nogoods are dense, with the
overhead of a consistency check per candidate. **Not implemented here.**

---

## Exercise 10 (***) — Backward-chaining planner modeled on `plan-a`

**Paraphrase.** Using the forward planner `plan-a` as a template, implement a
backward-chaining (goal-regression) planner.

**Answer (design — out of scope for code).** A backward planner regresses goals
through operators: given a goal literal `g`, find an operator whose add-list
contains `g`, make that operator's preconditions the new subgoals, and recurse
until subgoals are satisfied by the initial state. ATMS role: each operator choice
is an **assumption**; the regression tree's leaves correspond to environments, and
**nogoods prune** inconsistent operator-choice combinations (e.g., choosing two
operators with conflicting effects). The structural change from `plan-a`: instead
of forward state expansion driven by applicable operators, you drive expansion by
**goal-achievers** and accumulate preconditions, using STRIPS goal-regression for
the frame (a precondition survives unless an intervening operator deletes it).
Termination/threats handled by the standard partial-order or total-order
backward-search bookkeeping. **Not implemented here.**

---

## Exercise 11 (***) — Reimplement a planning technique on ATRE as world model

**Paraphrase.** Take a planning technique of your choice and reimplement it using
ATRE as the world-modeling substrate.

**Answer (design — out of scope for code).** Choose forward state-space planning.
Use ATRE to maintain each candidate world as a set of believed literals under an
environment; operator application = asserting add-list literals and the operator's
choice assumption, with delete-list handled by justifications that defeat the
removed literals; `:INTERN` consistency rules post nogoods for illegal states. The
search loop picks an applicable operator (a new assumption), lets ATRE propagate
the resulting world, and checks the goal against the believed literals. ATRE gives
**automatic state sharing** (common subexpressions across worlds share nodes) and
**nogood-based pruning** for free. **Not implemented here.**

---

## Exercise 12 (***) — General-purpose ATMS problem solver with focused control (suggestions architecture)

**Paraphrase.** Starting from the Section 14.4 design, build a general-purpose
ATMS-based solver that uses a *focused* control strategy within the *suggestions*
architecture.

**Answer (design — out of scope for code).** The **suggestions architecture**
separates *generating* candidate inferences (rules emit *suggestions* tagged with
the environment they apply to) from *deciding* which to pursue (a controller picks
the next focus). A **focused** strategy maintains a single current focus
environment (plus a frontier) instead of expanding all environments. Components:
(1) a suggestion queue holding `(rule, bindings, environment)` triples; (2) a focus
manager that orders suggestions by a control policy (best-first / DFS / BFS) over
environments; (3) the ATMS providing label maintenance and nogood pruning so that
suggestions whose environment becomes nogood are discarded. The solver loop: pop
the best suggestion consistent with the focus, execute it (assert nodes /
justifications under its environment), update the focus, repeat. This is the
reusable kernel that Exercises 13–14 build on. **Not implemented here.**

---

## Exercise 13 (***) — Natural-deduction propositional prover using KM* on the Ex.12 solver

**Paraphrase.** Using the Exercise 12 solver as a module, build a natural-deduction
system that solves propositional-logic problems using the KM* procedure.

**Answer (design — out of scope for code).** Represent each ND inference rule
(modus ponens, ∧-intro/elim, ∨-intro, →-intro via discharged assumptions, ⊥-elim,
etc.) as a **suggestion-generating rule** in the Ex.12 architecture. Discharged
assumptions map naturally onto ATMS **assumptions** (an assumption introduced for
→-introduction is later discharged by recording the environment in the conclusion's
label). KM* supplies the **control / focus heuristic** that picks which ND rule to
apply next, keeping the proof search focused rather than enumerating all derivable
formulas. A proof of `A → B` succeeds when `B`'s label contains an environment
whose only assumption is `A`. Soundness comes from the ATMS label discipline;
completeness for propositional logic comes from KM*'s coverage of the ND rule set.
**Not implemented here.**

---

## Exercise 14 — Cryptarithmetic: many-worlds vs. focused

### 14a (***) — Many-worlds cryptarithmetic in ATRE; `:INTERN` vs `:IN` rules

**Paraphrase.** Build a many-worlds cryptarithmetic solver in ATRE and compare
`:INTERN`-triggered against `:IN`-triggered rules in run time and rules fired.

**Answer (analysis — out of scope for code).** Many-worlds: assign each letter a
digit via assumptions, let the ATMS explore all assignments simultaneously, and let
column-sum constraints post nogoods that prune inconsistent digit combinations. The
solution = the consistent leaf environment(s). **`:INTERN` vs `:IN`:** `:INTERN`
rules fire once on the interned pattern (environment-independent) and are
**cheaper** because constraint structure is installed without per-environment
re-firing; `:IN` rules re-fire per believed environment, doing **more work**
(rules-fired count higher, run time higher) but only acting on actually-believed
data. Expectation: for a constraint-propagation task like cryptarithmetic,
`:INTERN` wins on both metrics because the constraints are environment-uniform and
benefit from being installed structurally once. **Not implemented here.**

### 14b (***) — Focused cryptarithmetic on the Ex.12 solver; BFS vs DFS, trigger variants

**Paraphrase.** Build a focused cryptarithmetic solver on the Ex.12 module and
compare breadth-first vs depth-first search and different rule-triggering
strategies.

**Answer (analysis — out of scope for code).** Focused search commits to one
partial assignment (focus) and extends it, backjumping on nogoods. **DFS** is
expected to dominate **BFS** here: cryptarithmetic has deep, narrow solution paths
and DFS reaches a full assignment quickly with O(depth) frontier memory, whereas
BFS holds an exponential frontier of partial assignments. Among trigger strategies,
`:CONSISTENT-WITH` (Ex.9) should prune best for the focused generator (only extend
with digits not yet ruled out). **Not implemented here.**

### 14c (***) — Which strategy is better, and how far it generalizes

**Paraphrase.** From the two implementations, judge which strategy suits
cryptarithmetic and what class of problems the conclusion generalizes to.

**Answer (analysis).** For cryptarithmetic — a **tightly constrained CSP with a
small set of unique solutions** — the **focused (DFS + consistency-driven)**
strategy is expected to win: it avoids materializing the combinatorial space of
worlds that the many-worlds ATMS labels would carry, and nogood-learning gives it
backjumping. The many-worlds strategy pays to maintain labels for vast numbers of
ultimately-inconsistent environments. **Generalization:** focused search wins on
problems that are **highly constrained with few solutions and deep dependency
chains** (most CSPs, configuration, planning). Many-worlds remains preferable when
you genuinely need **many** answers, or the comparative analysis across *all*
contexts (diagnosis/GDE-style multiple-fault reasoning, qualitative envisioning),
where the shared-label structure pays for itself. **Not implemented here.**

---

## Exercise 15 (*****) — Scalable-multiprocessor ATMS (2–100 processors)

**Paraphrase.** Beyond the data-parallel (Connection Machine) ATMS, how would you
organize an ATMS to run efficiently on a general scalable multiprocessor with
anywhere from 2 to ~100 processors? Implement and analyze it theoretically and
empirically.

**Answer (design — out of scope for code).** Two decompositions, chosen by
processor count:

- **Node/graph partitioning (coarse-grained, few processors).** Partition the
  justification graph across processors (e.g., by node, by dbclass, or by
  graph-cut to minimize cross-edges). Each processor owns label computation for its
  nodes; label updates that cross a partition boundary become **messages**. Because
  ATMS label propagation is local (a node's label is a function of its
  justifications' antecedent labels), this maps to a **bulk-synchronous /
  message-passing** scheme: rounds of local label updates separated by boundary
  exchanges, iterating to a fixpoint. Good locality minimizes messages; the cut
  quality bounds communication.
- **Environment/operation parallelism (finer-grained, many processors).** The
  expensive primitives — label union/minimization, subset tests, and nogood
  checking — are set operations over environments represented as **bitvectors**
  (one bit per assumption). These parallelize directly: distribute environments
  (or bitvector chunks) across processors and do AND/OR/subset in parallel. This is
  the generalization of the data-parallel approach to a moderate-P machine.

A practical hybrid: graph-partition across the ~P nodes/processors for coarse
parallelism, and within each processor vectorize the bitvector label operations.
Load balancing via work-stealing on the label-update queue handles skew.

**Theoretical analysis.** Speedup is bounded by (a) the **critical path** of the
justification DAG (longest dependency chain — inherently serial) and (b)
**communication** across the partition cut. With a graph of depth D and good
partition, ideal time ≈ O(D) synchronization rounds; per-round work parallelizes by
P. Amdahl limit set by D/(total work). Bitvector ops give a further constant/
near-linear factor in the assumption dimension.

**Empirical analysis.** Measure speedup vs. P (2,4,…,100) on benchmarks with
varying graph depth and nogood density; report scaling, message volume, and
load-balance. Expect good scaling on wide/shallow problems and saturation
(critical-path-bound) on deep/narrow ones. **Not implemented here.**

---

## Exercise 16 (*****) — ATMS ideas "turned inside out" for distributed design teams

**Paraphrase.** An ATMS helps a single-address-space problem solver stay coherent
and reuse intermediate products. Can the *idea* be inverted to help **teams of
human designers** keep their work coherent and reuse each other's artifacts (in a
distributed system rather than one process)?

**Answer (design / position — out of scope for code).** Yes. Re-cast the ATMS
concepts as a **distributed dependency / provenance service** for design artifacts:

- **Assumptions → design decisions / requirements / version choices.** Each
  artifact (drawing, analysis, sub-design) is labeled with the set of decisions and
  input-versions it depends on — its **environment(s)**, exactly like an ATMS
  label.
- **Nogoods → incompatibility records.** When two decisions or artifact versions
  conflict (interface mismatch, contradictory requirement), record the conflicting
  combination as a nogood; the system then warns any designer whose work would rely
  on that combination — automatic **coherence checking** across the team.
- **Label propagation → automatic impact / reuse analysis.** When a designer
  changes a decision, the dependency labels identify exactly which downstream
  artifacts are affected (must be revisited) and which remain valid — supporting
  *reuse* (an artifact valid under a still-current environment can be reused
  as-is) and *coherence* (flagging stale artifacts). This is essentially
  dependency-directed change notification, like build-system/`make` provenance but
  with multi-context labels.
- **Multiple environments → exploring design alternatives in parallel.** Different
  branches of the design (alternative configurations) live in different
  environments, so the team can compare alternatives and share the
  context-independent (interned) sub-results across them, the team-scale analogue of
  ATMS subexpression sharing.

Architecturally, this becomes a shared (possibly replicated/eventually-consistent)
dependency store the team's tools consult — an "inside-out" ATMS where the
problem solver is a distributed group of humans+tools rather than a single program.
The hard parts are distributed nogood propagation under partition/latency and
mapping informal design dependencies onto formal assumption sets. **Not
implemented here.**

---

### Summary

All 16 exercises are addressed (16 main problems; multi-part items 5–9 and 14 have
their sub-parts a–d covered individually). Answers are **analysis only** — the
ATMS / ATRE / focused-suggestions machinery this chapter builds on is outside this
package's scope (`BRIEFING.md` non-goals), so no code was written and `codeRuns` is
`false`. Implementation sub-parts (5c, 6b, 6d, 7b, 8d, 10–15) are given as designs
/ algorithm sketches with the reasoning that would drive an implementation.
