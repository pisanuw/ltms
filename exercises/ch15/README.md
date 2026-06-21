# Chapter 15 - Antecedent Constraint Languages (TCON): Exercise Solutions

**Analysis only.** TCON (the antecedent constraint language of Forbus & de Kleer,
Chapter 15) is *not* implemented in this `ltms` package; it is explicitly a non-goal
(see `BRIEFING.md`). Therefore the answers below are conceptual: algorithm sketches,
designs, derivations, and trade-off analyses, not runnable code. Exercise statements
are paraphrased (not quoted) to avoid reproducing copyrighted text.

Background reminders used throughout:

- A *constraint network* is a set of **cells** (each holding at most one value plus a
  justification) wired together by **constraints** (devices such as `adder`, `multiplier`).
- A constraint is built from **constraint rules**: small antecedent rules that fire when
  enough of the constraint's cells have values, computing a value for another cell and
  recording the inputs as that value's **antecedents** (dependency record).
- `set!` installs a value in a cell with an *informant* (the rule that produced it);
  conflicts between an incoming value and an existing value signal a contradiction.
- TCON runs on a TMS, so a value's justification is the conjunction of the cell values
  the firing rule read. Retracting a premise propagates through these dependencies.

---

## Exercise 1 - Logical and relational constraints

### 1a. An equality-test constraint `==?`

**Paraphrase.** Build a constraint with inputs `in1`, `in2` and output `output` that
forces `output` to `T` when the two inputs are `equal` (Lisp `equal`, i.e. structural
equality) and to `nil` otherwise.

**Answer.** One simulation rule suffices:

- Rule R1 (forward / simulation): trigger when both `in1` and `in2` have values `v1`,
  `v2`. Compute `output := (if (equal v1 v2) T nil)`. Antecedents = `{in1, in2}`.

That is the only *complete* direction. The inverse directions are weak because the
output is a coarse 1-bit summary:

- If `output = T`, you may add an inference rule: when `in1` is known and `output = T`,
  set `in2 := in1` (and symmetrically). Antecedents `{in1, output}` / `{in2, output}`.
  This is sound: equality plus one operand fixes the other.
- If `output = nil`, *no* value can be inferred for an unknown input (knowing two things
  are unequal does not pin a value), so there is no inference rule for that case.

So the minimal version is one rule; the "smart" version adds two inference rules guarded
on `output = T`. Each rule must list exactly the cells it read as antecedents so the TMS
can retract correctly (this discipline is the subject of Exercise 6).

### 1b. A `comparator` constraint

**Paraphrase.** Build a constraint whose output names the ordering relation between
numeric inputs `in1` and `in2` (e.g. `<`, `=`, `>`).

**Answer.** Simulation rule: when both inputs are numbers `v1`, `v2`, set
`output := (cond ((< v1 v2) '<) ((> v1 v2) '>) (t '=))`, antecedents `{in1,in2}`.

Inference rules (partial, by output symbol):

- `output = '='` behaves like `==?` with `T`: given one input, set the other equal.
- `output = '<'` or `'>'` yields only *inequality* knowledge, which a single-valued
  cell cannot store, so no value is propagated back (unless cells hold intervals/sets,
  cf. Exercise 4). For a pure point-valued network only the `'='` case has an inverse.

Choosing a fixed symbol vocabulary (`<`,`=`,`>`) is the design decision; you could
enrich it (`<=`, `>=`) but those overlap and complicate the simulation cond.

### 1c. `positive?`, `zero?`, `negative?`

**Paraphrase.** Using 1a/1b, build constraints whose output is `T` exactly when the
input satisfies the named sign relation with 0.

**Answer.** Each is a comparator (or `==?`) wired against a constant-0 cell:

- `zero?`: a `==?` with `in2` tied to a constant cell holding 0; `output` = T iff input = 0.
- `positive?`: a `comparator` with `in2 = 0`; define `output := (eq cmp '>)` as a thin
  wrapper, i.e. output T iff `in1 > 0`. Concretely, instantiate a `comparator`, set its
  `in2` constant cell to 0, and add a rule `output := (eq comparator-out '>)`.
- `negative?`: same, `output := (eq comparator-out '<)`.

Reuse is the point: these are macro-defined compositions, not new primitive rules. The
0 cell is a *ground constant* (an assumption that never retracts), so the dependency on
it is trivially stable.

### 1d. Enforce positive travel times in uniform motion

**Paraphrase.** Use `positive?` to require that travel time in the uniform-motion
constraint (`distance = rate * time`) is positive.

**Answer.** Add to the uniform-motion prototype an internal `positive?` constraint whose
input is the `time` cell, and a rule that signals a contradiction when its output is
`nil`:

- rule: when `positive?-out = nil`, call the contradiction signal (e.g. install a
  conflicting value or raise the TCON contradiction). Antecedent = `{positive?-out}`.

Effect: any propagation that would assign `time <= 0` (e.g. from a negative distance or
rate) becomes a TMS contradiction, retractable to whichever premise forced the bad time.
This turns a sign sanity check into a network-level constraint instead of an ad hoc check
inside the formula.

### 1e. A `relay` constraint

**Paraphrase.** Build a relay with inputs `in1`, `in2`, a control cell `coil`, and an
`output` that equals `in1` when `coil = T` and `in2` when `coil = nil`.

**Answer.** Two guarded equality rules in each direction:

- Forward: if `coil = T`, `output := in1` (antecedents `{coil, in1}`); if `coil = nil`,
  `output := in2` (antecedents `{coil, in2}`).
- Inverse: if `coil = T` and `output` known, `in1 := output` (`{coil, output}`); if
  `coil = nil` and `output` known, `in2 := output`.

Crucially, the antecedents *include `coil`*: the propagated value depends on the switch
position, so retracting/flipping `coil` correctly retracts `output`. The unselected input
contributes nothing and must not be listed as an antecedent. This is a value-routing
("mux") device, and it is exactly where TCON's strict dependency-tracking pays off.

### 1f. Signed square root via `relay`

**Paraphrase.** Use `relay` to build a constraint that, given input `x`, produces the
positive root when `x >= 0` and the negative root of `|x|` when `x < 0`.

**Answer.** Compose:

1. `negative? x -> neg` (sign test of the input).
2. `sqrt |x| -> r` where `|x|` is computed by an abs constraint; `r >= 0`.
3. a constraint producing `-r -> rneg`.
4. a `relay` with `coil = neg`, `in1 = rneg` (chosen when negative), `in2 = r` (chosen
   otherwise), `output = result`.

So `result = -sqrt(|x|)` when `x<0`, else `sqrt(x)`. The `coil` value `neg` makes the
choice explicit and dependency-tracked: the chosen branch's value carries `neg` among
its antecedents, so a later change to the sign of `x` cleanly switches the output. (A
plain `sqrt` constraint is ambiguous about sign; the relay disambiguates by routing.)

### 1g. Why relays-as-constraints cannot oscillate

**Paraphrase.** Real relays wired in a loop oscillate; explain why a network of
constraint-modeled relays does not.

**Answer.** Constraint propagation is *monotonic and quiescent*, not temporal. A cell
holds a single value with a well-founded justification; propagation runs to a fixed point
and stops. An oscillator needs the act of changing a value to *cause* a later change of
that same value over time, but TCON has no notion of time or of a value re-causing its own
change. If you tried to wire a relay's output back to drive its own coil, you would not
get oscillation: you would either reach a consistent fixed point, or the loop would create
a value whose justification depends (through the coil) on its own negation, which the TMS
flags as a contradiction / unfounded (circular) support rather than cycling. Modeling
oscillation requires an explicit time/state representation (a temporal or qualitative
simulator), which constraint local-propagation lacks.

---

## Exercise 2 - Why at most one `formulae` statement per prototype

**Paraphrase.** `process-constraint-rules` assumes each constraint definition has at most
one `formulae` form; describe the problem that two `formulae` forms in one prototype would
cause.

**Answer.** `process-constraint-rules` walks the single `formulae` block to generate the
constraint's rules and, importantly, to assign each generated rule a stable identity/index
within the prototype (rule naming, triggering bookkeeping, and the mapping from rules back
to the prototype). With two `formulae` blocks there is no single canonical ordering/naming:
the second block's rules would either collide with the first block's generated names/indices
or be silently dropped, and the dependency/informant records (which reference "the rule that
set this cell") would become ambiguous. In short, the code assumes one formulae body so that
rule generation is a single deterministic pass producing a well-defined, collision-free set
of rules; two bodies break that one-to-one structure. The clean fix is to require authors to
merge all rules into one `formulae` block (or to make rule naming block-qualified), which is
why the language enforces the single-block convention.

---

## Exercise 3 - Why not connect cells across networks with `==?`

**Paraphrase.** Explain why you should not join cells belonging to two *different*
constraint networks by an `==?` constraint.

**Answer.** `==?` only exposes a 1-bit equality summary; it does **not** propagate the
underlying value with its dependencies. So wiring two separate networks through `==?` does
not actually equate their cells - it merely reports whether they happen to match, with no
back-propagation when one side is unknown. You would *think* the networks were coupled but
they are not: changes in one network would not flow to the other, and the equality output
would silently flip without forcing reconciliation. (Contrast with an `equality`/`==`
*wire* that genuinely identifies two cells.) Even if you intended real coupling, joining
two independently constructed networks risks identifier/dependency collisions and mixes two
TMS contexts; the supported way to share a value is to wire the cells with an identity
constraint inside one network, not to bolt a boolean test between two networks.

---

## Exercise 4 - Allowing sets of symbols/numbers as cell values

**Paraphrase.** What changes are needed so a cell can hold a *set* of possible
symbols/numbers rather than a single value?

**Answer.** Move from single-value cells to *domain* cells (finite-domain / interval CSP
style). Required modifications:

1. **Cell representation.** A cell stores a set (or interval) of candidate values plus a
   justification for the current domain, instead of one value.
2. **`set!` becomes domain intersection.** Installing information *narrows* the domain
   (set intersection), rather than asserting equality. The "merge" of an incoming
   contribution and the existing domain is intersection; the result's antecedents are the
   union of the two contributors' antecedents.
3. **Contradiction = empty domain.** A conflict is no longer "two unequal values" but
   "intersection is empty"; that empty domain triggers the TMS contradiction, dependent on
   the constraints that shrank it.
4. **Constraint rules become relational filters.** An `adder` no longer waits for two
   point values; it can prune: e.g. given domains for `a` and `c`, restrict `b`'s domain to
   `{c - a : ...}`. Rules fire on *domain change*, not just on first becoming known, so the
   trigger condition and re-trigger semantics change.
5. **Termination / fixpoint.** Because rules now repeatedly narrow domains, you need a
   propagation queue with a monotone-decreasing measure (domains only shrink) to guarantee
   quiescence, analogous to arc-consistency (AC-3) propagation.
6. **Quiescence vs. solved.** A network is "solved" only when domains are singletons; the
   notion of a known cell changes from "has a value" to "domain is a singleton".

This essentially turns TCON into a finite-domain constraint propagator with TMS-backed
justifications, which is a strictly more expressive (and more expensive) system.

---

## Exercise 5 - `set!` value/informant precedence

### 5a. Where "first writer wins" is wrong

**Paraphrase.** `set!` keeps the value/informant that arrived first among compatible
contributors; describe an interaction sequence where that is suboptimal.

**Answer.** Suppose a cell first receives a value derived through a long chain of *assumed*
premises (informant = a derivation resting on a retractable assumption), and *later* the
same value is supplied as a directly observed/ground input. "First wins" keeps the fragile
derived justification. Now retract the assumption: the cell's value disappears (and any
downstream values with it) even though a perfectly good ground justification existed all
along. The user sees a value vanish that should have stayed. A second case: the first
informant's antecedents are huge, bloating dependency records and slowing later retraction
analysis, when a cheaper later justification existed. In both, keeping the first informant
yields unnecessarily wide or fragile dependencies.

### 5b. Make ground values take precedence

**Paraphrase.** Modify `set!` so a ground (premise/observed) value supersedes a
previously installed *derived* value (when they agree).

**Answer.** Change the merge logic in `set!`:

- When an incoming value equals the existing value, do not auto-keep the old one. Compare
  *informant strength*: if the incoming informant is **ground** (a user-set parameter /
  premise with empty or assumption-free support) and the existing informant is **derived**,
  *replace* the existing value's justification with the ground one (re-justify the cell on
  the premise), then update any downstream dependents to point at the now-ground support.
- If both are ground, or both derived, keep the existing one (preserve current behavior).
- If they *disagree*, it is still a contradiction (unchanged).

Concretely: tag each value with its support class (ground vs derived). On a compatible
re-`set!`, prefer the ground tag; re-running the TMS justification install makes the cell's
support well-founded on the premise so it survives assumption retraction. This is the
constraint-language analog of "premise beats derivation" priority in a TMS.

---

## Exercise 6 - Returning the *used* subset of inputs

**Paraphrase.** Instead of requiring every formula to read all its inputs (so dependency
records are right), let a formula return both the computed value *and* the subset of inputs
it actually used; modify TCON accordingly and weigh the trade-offs.

**Answer.**

*Modification.* A constraint rule's body returns a pair `(value . used-cells)`. `set!`
records `used-cells` as the antecedents of the new value, instead of the rule's full
declared trigger set. The rule-generation machinery no longer needs the discipline that
"every triggered input must appear in the value computation"; the runtime takes the
formula's word for which inputs mattered.

*Trade-offs.*

- (+) **Tighter dependencies.** When a formula short-circuits (e.g. `output := T` because
  one input already determined the answer, ignoring the others), the antecedents reflect
  the *minimal* support. This yields fewer spurious retractions and smaller, more accurate
  nogoods.
- (+) **Author freedom.** Formulas may legitimately ignore inputs in some branches without
  poisoning the dependency record, removing a subtle correctness burden on authors.
- (-) **Correctness now rests on the formula's honesty.** If a formula under-reports the
  inputs it used, the dependency record is *unsound*: retracting a truly-used premise will
  not retract the value, leaving stale beliefs. The old "use everything" rule made omission
  impossible by construction; this scheme makes it a per-formula obligation.
- (-) **Overhead.** Every formula must construct and return the used-set, and `set!` must
  process a variable-length antecedent list each call - more allocation and bookkeeping than
  a fixed declared trigger set.
- (-) **Harder static analysis.** You can no longer determine a constraint's dependency
  structure from its declaration alone; it is only known at run time.

Net: the approach trades a structural guarantee for finer-grained, possibly cheaper
dependencies, paying with a new soundness obligation on formula authors and per-call cost.

---

## Exercise 7 - Implementing a constraint with PDIS (JTRE) rules

**Paraphrase.** Show that a pattern-directed inference system can implement constraints by
writing JTRE rules for an `adder` constraint plus a rule that detects contradictory values.

**Answer (sketch).** Represent a cell's value as an asserted fact
`(value <cell> <number>)` and wire the adder around three cells `a`, `b`, `c` with
`a + b = c`. Three rules, one per solvable direction, each justified by the two values it
reads:

```
;; if a and b known, derive c
rule: (value a ?x) (value b ?y)  =>  assert (value c (+ ?x ?y))   justified by the two antecedents
;; if a and c known, derive b
rule: (value a ?x) (value c ?z)  =>  assert (value b (- ?z ?x))
;; if b and c known, derive c's complement
rule: (value b ?y) (value c ?z)  =>  assert (value a (- ?z ?y))
```

Each `assert` is installed with a justification naming the two `value` facts it used, so
the JTMS retracts a derived cell value when either premise is retracted - exactly the
dependency behavior TCON gives. Contradiction detection is a separate rule:

```
rule: (value ?cell ?v1) (value ?cell ?v2)  with  (not (equal ?v1 ?v2))
      =>  signal-contradiction / assert (contradiction) justified by the two value facts
```

This makes the JTMS mark the conflicting values' joint support as a nogood, which the
contradiction machinery then resolves. The construction generalizes: any constraint is a
bundle of such directional derivation rules plus the shared contradiction rule, which
demonstrates that constraint languages are a special case of pattern-directed inference.

*(Our package has a JTRE; this is the idea one would encode there - the adder is the
canonical example.)*

---

## Exercise 8 - Does the three-input adder of Fig. 15.8 capture adder semantics?

**Paraphrase.** Examine the three-input adder. Does its rule set always reflect true
three-input-adder semantics; if not, how to fix it?

**Answer.** A faithful `n`-input adder must support *every* solvable direction: from any
`n` of the `n+1` quantities (the `n` inputs plus the sum), derive the missing one. For a
three-input adder `s = a + b + c` that is four derivation directions:
`s := a+b+c`, `a := s-b-c`, `b := s-a-c`, `c := s-a-b`. If the figure's definition only
provides the forward direction(s) (compute the sum from inputs) or omits one of the
inverse solves, then it does **not** fully reflect adder semantics: there are consistent
states where a value is derivable by hand but the network stays quiescent without it (local
propagation incompleteness for that missing rule). The fix is to supply the full set of
directional rules so that whenever exactly one of the four quantities is unknown it gets
computed, each rule justified by the three values it read. (If the figure already lists all
four directions, then it *is* semantically complete for single-unknown cases; it still
cannot solve when two-or-more are unknown, but that is the inherent limit of local
propagation, not a bug in the constraint.)

---

## Exercise 9 - Shared structure when building constraints

**Paraphrase.** Modify TCON to share structure among constraints (per Section 15.5.1.1)
rather than rebuilding identical substructure.

**Answer (design).** When a composite constraint (e.g. `2D-vector`, uniform-motion) is
instantiated, TCON currently expands the prototype freshly each time, allocating new cells
and rules for every internal sub-constraint. Shared-structure building instead:

1. Compiles each prototype once into a *template* (the cell graph + rule closures).
2. At instantiation, allocates only the *boundary* cells unique to this instance and links
   them to the shared template's rule code, reusing the rule objects/closures across
   instances rather than copying them.
3. Uses a hash-cons / interning step: if an identical sub-constraint over the same cells is
   requested twice, return the existing instance instead of building a duplicate.

Benefits: far less consing at network build time, smaller memory footprint for large
repetitive networks, and faster construction. Care points: rule *code* can be shared but
per-instance *cell bindings* and *justifications* must stay distinct (a shared rule closure
must be parameterized by the instance's cells, not capture one instance's cells); and
interning must key on cell identity so two genuinely different wirings are not collapsed.
This is the standard "flyweight + memoize" transformation applied to constraint expansion.

---

## Exercise 10 - Removal rules

**Paraphrase.** Extend TCON with *removal* rules (Section 15.5.1.4) - rules that fire to
*undo* structure/values, not just add them.

**Answer (design).** A removal rule is a rule whose action is to *retract* a value or to
*dismantle* part of the network when its triggering condition becomes true (it is the dual
of the normal "addition" rule). To support them:

1. **Rule kind tag.** Mark rules as add vs remove. The runner treats removal-rule firings
   as TMS retractions: when the trigger pattern holds, the rule withdraws the targeted
   value(s) and lets two-phase relabeling propagate the loss of support.
2. **Trigger on becoming-true and re-firing on becoming-false.** Because retraction can
   later be undone (the premise reappears), the engine must re-evaluate removal rules when
   their trigger condition flips, so removed structure can be restored.
3. **Idempotence / well-foundedness.** Guard against a removal rule and an addition rule
   oscillating on the same cell; the TMS's well-founded support requirement plus a
   propagation queue (process to fixed point, detect no-progress) keeps it terminating.
4. **Dependency bookkeeping.** A removal must be itself justified, so that the *act* of
   removal is retractable - otherwise you cannot restore the structure when conditions
   change.

Use case: conditional network topology (e.g. a switch that physically disconnects part of
a circuit) where some wiring should *not* exist in certain modes; removal rules let the
network shrink as well as grow under propagation control.

---

## Exercise 11 - Indirect cells and wiring rules (Section 15.5.1.3)

### 11a. Uncontrolled growth, and limits to prevent it

**Paraphrase.** Explain how indirect cells plus wiring rules let a network grow without
bound, and what limits could stop that.

**Answer.** A *wiring rule* fires on cell values and *adds new constraints/cells* to the
network; an *indirect cell* names a cell computed at run time. Together they let
propagation create structure that itself triggers more wiring rules, which create more
structure - a feedback loop with no fixed termination, since each new piece can satisfy the
trigger of another wiring rule (think: a rule that, given a list cell, builds a constraint
for the list's `cdr`, recursively forever, or two rules that mutually spawn each other's
triggers). The network can grow unboundedly even though each individual step is legal.

Limits to impose: (1) a *depth/size budget* (stop expanding after N new constraints or
depth K); (2) *demand-driven / lazy* expansion - build a sub-constraint only when some cell
is actually queried, not eagerly (this is essentially exercise 11c); (3) *memoization /
interning* so a wiring rule never builds the same constraint twice (cuts loops that re-spawn
identical structure); (4) *stratification* so wiring rules cannot transitively re-trigger
themselves, guaranteeing a finite expansion order.

### 11b. Extend TCON to support indirect cells and wiring rules

**Paraphrase.** Add indirect cells and wiring rules to TCON.

**Answer (design).** Add a new cell variety whose referent is resolved at run time (an
indirect cell holds, or computes, the *identity* of another cell). Wiring rules are rules
whose action calls the constraint-construction API (allocate cells, instantiate a
constraint, link cells) instead of (or in addition to) `set!`. Required machinery:

1. **Indirect-cell deref.** When a rule reads an indirect cell, it first resolves the
   target cell, then reads/writes that; the resolution itself becomes part of the
   value's antecedents (so if the referent changes, the dependent value retracts).
2. **Wiring action API.** A safe, idempotent constructor that wiring rules call; it must
   intern (per 11a) so re-firing does not duplicate structure, and must register the new
   structure under a justification so the *wiring* is retractable.
3. **Re-propagation after growth.** After a wiring rule adds constraints, the new rules
   enter the propagation queue and run to quiescence.
4. **Growth guards.** The depth/size budget and demand-driven gating from 11a, wired into
   the constructor.

### 11c. Test with a growing, on-demand behavior simulation

**Paraphrase.** Build (and test) a constraint simulation that lazily *grows* a description
of behavior over time, on demand.

**Answer (design).** Model time as a chain of state cells `state[0], state[1], ...`. A
wiring rule says: "if `state[t]` exists and `state[t+1]` is *demanded*, instantiate the
transition constraint linking `state[t]` to a newly allocated `state[t+1]`." Demand is
created by a query for `state[t+1]`'s value. Thus the timeline extends one step each time
a further state is asked for, and never beyond what is needed - the network's size is
bounded by the deepest query, satisfying 11a's limits. A test: query `state[5]` of a simple
discrete dynamical system (say a counter or a bouncing-value relay), confirm exactly five
transition constraints were built, the propagated values are correct, and that querying
`state[10]` later extends rather than rebuilds. This exercises indirect cells (each
`state[t+1]` is named indirectly), wiring rules (transition instantiation), demand-driven
growth, and interning (no duplicate transitions).

---

## Exercise 12 - Algebraic manipulation to beat local-propagation limits

### 12a. `gather-equations`

**Paraphrase.** Write a procedure that, given a partially solved network and a target cell,
walks the network structure to collect a set of equations about that cell's value.

**Answer (algorithm).** Local propagation stalls when no single constraint has enough known
cells to fire, yet the *system* of equations is solvable (e.g. two simultaneous linear
relations through a shared unknown). `gather-equations(network, target)`:

1. Start a worklist with `target`.
2. For each cell on the worklist, collect every constraint touching it and emit that
   constraint's algebraic relation as an equation, substituting in any *known* cell values
   as constants.
3. Add the constraint's other *unknown* cells to the worklist (frontier expansion).
4. Continue until the worklist is empty or a budget is hit, returning the accumulated
   equation set (and the set of unknowns appearing in it).

The result is a system of equations relating `target` to the network's known boundary
values, suitable for handing to a symbolic solver. (Optionally prune cells that are already
determined; optionally stop expanding once the number of equations >= number of unknowns,
giving a likely-solvable subsystem.)

### 12b. Hook `gather-equations` to an algebraic manipulator; explore limits

**Paraphrase.** Connect `gather-equations` to a computer-algebra system and probe the
combination's limits with examples.

**Answer (analysis).** Feed the gathered equation system to a CAS (e.g. a Groebner/linear
solver, or sympy.solve in a modern setting), then write any solved values back into the
network *as justified values* (antecedents = the equations/cells used). Expected limits to
demonstrate by example:

- **Linear simultaneous systems** (two relations, two unknowns): solved cleanly - the win
  over pure local propagation.
- **Nonlinear systems** (products, `sin`/`cos`): the CAS may return multiple roots, no
  closed form, or extraneous solutions; the network has nowhere to put "either x or -x"
  (single-valued cells), so root selection must be resolved by extra constraints or by
  assumption/case split.
- **Underdetermined systems** (fewer independent equations than unknowns): CAS returns a
  parametric family, not a value - nothing to propagate.
- **Scaling / blow-up**: gathering too large a subsystem makes the CAS slow or non-terminate;
  the frontier-budget in 12a matters.
- **Dependency fidelity**: a CAS-derived value must record *which* equations (hence which
  cells) it used so the TMS can still retract it; manipulators that simplify away variables
  can lose this provenance.

### 12c. Rewrite TCON for symbolic-value propagation (Section 15.5.2)

**Paraphrase.** Rebuild TCON so cells can hold *symbolic* expressions and constraints
propagate symbolic values, generating equations.

**Answer (design).** Generalize a cell's value from a number to a *symbolic term* (a
variable or an algebraic expression). Constraint rules compute symbolically: an adder with
`a` known and `b` symbolic produces `c := a + b` as an expression rather than refusing to
fire. Needs:

1. **Symbolic value type** + an expression simplifier (so propagated expressions stay
   manageable).
2. **Constraint rules emit expressions**, and `set!` may install an expression whose
   antecedents are the contributing cells/constraints.
3. **Equation capture**: when two constraints both compute (symbolic) values for the same
   cell, equating them yields an equation; collect these into the system for a solver
   (ties to 12a/12b). When an expression becomes ground (all variables resolved) it
   collapses to a number.
4. **Solver hook + write-back** as in 12b, justified.

This converts TCON from a numeric propagator into an equation-builder, recovering global
solvability that local propagation alone cannot achieve.

### 12d. Reconstruct SYN or build an algebra-word-problem solver

**Paraphrase.** Using the symbolic-propagation TCON, rebuild the SYN circuit-synthesis
program (ref [6]) or build a textbook-algebra solver.

**Answer (analysis, four-star / open-ended).** This is a substantial project, not a short
answer. Sketch for the **algebra-word-problem** path (the more self-contained option):

1. Parse the problem into quantities (cells) and stated relations (constraints) - e.g.
   "the sum of two numbers is 20, their difference is 4" -> cells `x,y`, constraints
   `x+y=20`, `x-y=4`.
2. Run symbolic propagation (12c); where local propagation stalls, `gather-equations`
   (12a) + CAS (12b) solves the residual system.
3. Write solutions back as justified cell values and report them with their derivations.

For **SYN** (circuit synthesis), the same engine is used to propagate device equations
(Ohm/Kirchhoff style relations) symbolically and solve for component values meeting design
targets; reconstructing it faithfully means encoding SYN's component library as constraint
prototypes and its design goals as boundary equations. The key technical demands are the
same: robust symbolic simplification, root/case management for nonlinear relations, and
justified write-back so the synthesized design remains revisable. Stated assumption: a
modern reimplementation would lean on an existing CAS (sympy) rather than a hand-built
manipulator, scoping the effort to the constraint/equation-gathering layer.

---

## Exercise 13 - Simulation vs. inference split (predefined inputs/outputs)

### 13a. Which generated candidate values are legitimate predictions?

**Paraphrase.** Of the three values computed by `generate-candidates` in the Section 15.4.3
example, which are genuine *predictions* (outputs computed from inputs), and why?

**Answer.** A value is a *prediction* only if it flows from designated **inputs to
outputs** along the simulation direction - i.e. it is computed by a *simulation* rule from
observed inputs, so it can be checked against a future measurement. Values computed in the
*inference* direction (an input back-derived from an observed output) are *not* predictions:
they are diagnostic inferences about the cause, not forecasts of an observable. So among the
three, the ones obtained by running constraints forward from the set inputs (e.g. the value
the device *should* produce at an output terminal given its inputs) are the legitimate
predictions; any value obtained by reasoning backward from a measured output to an input is
not a prediction. (Without the exact figure I name the criterion; concretely, in the
classic adder example where input `a` is set and output `f` is set, the value computed for
an *output* from inputs is the prediction, while a value computed for an *input* from `f`
is an inference.)

### 13b. Dualist constraints (`adder-sim` / `adder-inf`) for the example

**Paraphrase.** Implement the simulation/inference split by splitting each constraint into a
sim component and an inf component, each terminal carrying both a simulated and an inferred
cell; write enough constraints for the Section 15.4.3 example.

**Answer (design).** Give every terminal two cells, addressed `(>> sim term)` and
`(>> inf term)`. Define:

- `adder-sim`: rules that compute *output* sim-cells from *input* sim-cells only
  (information flows inputs->outputs). E.g. `(>> sim f) := (>> sim a) + (>> sim b)`.
- `adder-inf`: rules that compute *input* inf-cells from *output* inf-cells (information
  flows outputs->inputs). E.g. `(>> inf a) := (>> inf f) - (>> inf b)`.

Set-up statements like `(set-parameter (>> sim a) 3)` (simulate forward from observed
input) and `(set-parameter (>> inf f) 10)` (infer backward from observed output). Then
`(>> sim f)` is the *prediction* and a mismatch between `(>> sim f)` and the observed/inf
value at `f` is the discrepancy that drives diagnosis. Wiring: instantiate one `adder-sim`
over the sim cells and one `adder-inf` over the inf cells of the same terminals; the two
do not cross, which is exactly what keeps predictions and inferences separable.

### 13c. Rewrite `suspend.lisp` for the dualist organization

**Paraphrase.** Adapt the candidate-generation / suspension machinery (`suspend.lisp`) to
the sim/inf split constraint organization.

**Answer (design).** `generate-candidates` should now: (1) run only `*-sim* constraints
forward to produce predictions at output terminals; (2) compare each predicted sim-value
with the corresponding inf-value (from observed outputs) to detect discrepancies; (3) for
diagnosis, propagate `*-inf*` constraints from observed outputs and treat conflicts between
sim and inf cells as the symptoms. The "suspend/resume" control just needs to track the two
cell families separately so a prediction is never accidentally fed back as an inference
(which would short-circuit the very split that makes prediction-vs-observation comparison
meaningful). Concretely: tag propagation passes as sim or inf, keep two work queues, and at
candidate-generation time read predictions from sim-output cells, expectations from inf
cells, and emit discrepancies where they disagree.

---

## Exercise 14 - A modular `2D-vector` (no flat `formulae`)

**Paraphrase.** The `2D-vector` constraint (Fig. 15.11) is defined "flat" with many direct
rules; redesign it as a composition of simpler constraints with *no* `formulae` block (hint:
new constraint types are needed, and `2D-motion` will need small changes).

**Answer (design).** A 2D vector relates Cartesian components `(x, y)` and polar
`(magnitude rho, angle theta)` by `x = rho*cos(theta)`, `y = rho*sin(theta)`,
`rho = sqrt(x^2+y^2)`, `theta = atan2(y,x)`. Instead of one big rule block, build it from
primitive constraints wired together:

Needed primitive constraint types:

- `multiplier` (already standard) for `rho*cos` and `rho*sin`.
- `cos` / `sin` constraints (input theta -> output the trig value, and inverse where defined).
- a `square` (or reuse `multiplier` with both inputs the same cell) and an `adder` for
  `x^2 + y^2`.
- a `sqrt` constraint (for `rho`); reuse the *signed* handling only if needed (`rho >= 0`).
- an `atan2` constraint for `theta` from `(x, y)`.

Wiring (internal cells in parentheses):

```
cos(theta)    -> (cx)
sin(theta)    -> (cy)
multiplier(rho, cx) -> x
multiplier(rho, cy) -> y
square(x) -> (x2);  square(y) -> (y2)
adder(x2, y2) -> (r2)
sqrt(r2) -> rho
atan2(y, x) -> theta
```

The constraint declaration just *instantiates and wires* these sub-constraints (a `parts`/
`connections` style body) with no `formulae` of its own - propagation through the primitives
reproduces the flat version's behavior, and each derived component now carries fine-grained
dependencies on exactly the sub-constraints involved.

*Change to `2D-motion`.* `2D-motion` previously reached into `2D-vector`'s flat internal
cells; after modularization those internals are renamed/owned by sub-constraints, so
`2D-motion` must refer to the vector through its *public* terminal cells (`x, y, rho,
theta`) rather than internal ones. That is the "minor change" the hint warns about: update
its cell references to the new public interface.

---

*End of Chapter 15 analysis. No code accompanies this chapter (TCON is out of scope for the
`ltms` package); all answers above are conceptual/design-level.*
