# Chapter 17 — A Tiny Diagnosis Engine (TGDE)

**Analysis only.** The diagnosis engine of this chapter (TGDE, a compact reconstruction of
the General Diagnostic Engine, GDE) is out of scope for this Python package. We implement
the JTMS/LTMS family, not the ATMS, GDE, interpretation construction, or the probabilistic
measurement selector that TGDE is built on. The answers below are conceptual: algorithm
sketches, derivations, complexity arguments, and design notes. No code is written here, and
there is no `solutions.py` to run. Exercise statements are paraphrased in my own words (the
book text is copyrighted); the original star ratings indicate difficulty (★ = easy …
★★★★ = research-level).

## Background notation used throughout

Model-based diagnosis (Reiter / de Kleer–Williams style) sets up:

- A **device** is a set of `n` components `{c1, …, cn}`. Each component has a behavioral
  model guarded by a health **assumption** `OK(ci)` ("ci is behaving correctly").
- A **diagnosis** is an assignment of `OK`/`¬OK` (good/faulted) to every component such that
  the model together with the observations (inputs + measurements) is **consistent**. Writing
  a diagnosis by the set `Δ` of components it declares faulted, `Δ ⊆ {c1,…,cn}` is a
  diagnosis iff
  `MODEL ∧ OBS ∧ (∧_{c∈Δ} ¬OK(c)) ∧ (∧_{c∉Δ} OK(c))` is satisfiable.
- A **minimal diagnosis** is a diagnosis `Δ` such that no proper subset `Δ' ⊂ Δ` is also a
  diagnosis (you cannot exonerate any of its faulted components and still explain OBS).
- A **minimal-cardinality diagnosis** is a diagnosis with the fewest faulted components among
  all diagnoses.
- A **conflict** (de Kleer's "nogood") is a set of components that **cannot all be OK** given
  OBS, i.e. an inconsistent environment in ATMS terms: `MODEL ∧ OBS ⊢ ¬(∧_{c∈S} OK(c))`. A
  **minimal conflict** is a conflict with no proper-subset conflict.
- **Diagnoses ↔ conflicts duality.** `Δ` is a diagnosis iff `Δ` is a **hitting set** of the
  collection of conflicts (`Δ` intersects every conflict). Minimal diagnoses are the minimal
  hitting sets of the minimal conflicts. This is the engine TGDE/GDE turns the crank on.
- The **diagnosis lattice** is the Boolean lattice of all `2^n` candidate fault sets ordered
  by `⊆`; the consistent ones (the diagnoses) form an **upward-closed** region (a filter):
  every superset of a diagnosis is a diagnosis.
- TGDE assigns each diagnosis a **probability** from per-component prior fault probabilities
  (typically assuming faults are independent and rare), and uses those to choose the next
  measurement that maximizes expected information gain (minimizes expected entropy).

---

## Exercise 1 (★) — Counting diagnoses; size of the diagnosis lattice

**Paraphrase.** For a device of `n` components, how many diagnoses can it have, and what does
that imply about the size of the diagnosis lattice?

**Answer.** A candidate fault set is any subset of the `n` components, so there are `2^n`
candidates in total; these are exactly the nodes of the diagnosis lattice (the Boolean
lattice `2^{c1,…,cn}` ordered by `⊆`). In the worst case **every** subset is consistent with
the observations, so the number of diagnoses can be as large as `2^n`. (Concretely, with no
observations at all, or with observations that constrain nothing, the empty set "all OK" plus
every fault combination is consistent.)

Because the diagnoses are an upward-closed filter, the number of *minimal* diagnoses can also
be exponential: by Sperner's theorem an antichain in `2^n` can have up to `C(n, ⌊n/2⌋) ≈
2^n/√n` elements, so even the minimal frontier is exponential in the worst case.

**Implication.** Enumerating diagnoses explicitly is intractable in general — the lattice is
exponential in `n`. This is precisely why GDE/TGDE never enumerates the lattice. It instead
(a) computes **minimal conflicts** via the ATMS as observations arrive, (b) represents the
diagnoses implicitly as the **minimal hitting sets** of those conflicts, and (c) prunes by
probability, focusing on the few high-probability (small-cardinality) diagnoses. The
exponential lattice is the reason the whole method is conflict-driven rather than
enumeration-driven.

---

## Exercise 2 (★) — Every minimal-cardinality diagnosis is a minimal diagnosis

**Paraphrase.** Prove that any diagnosis with the smallest possible number of faulted
components is also a minimal diagnosis (subset-minimal).

**Answer.** Let `Δ` be a minimal-cardinality diagnosis, so `|Δ| = k` is the least cardinality
over all diagnoses. Suppose, for contradiction, that `Δ` is **not** subset-minimal. Then some
proper subset `Δ' ⊂ Δ` is also a diagnosis. A proper subset has strictly fewer elements:
`|Δ'| < |Δ| = k`. But that contradicts `k` being the minimum cardinality of any diagnosis.
Hence no such `Δ'` exists, and `Δ` is subset-minimal, i.e. a minimal diagnosis. ∎

**Remark (converse fails).** The converse is false: a minimal (subset-minimal) diagnosis need
not have minimal cardinality. Example: if the minimal conflicts are `{a,b}` and `{c,d}` and
also `{a,e}`-style structure can force it, you can have a subset-minimal hitting set of size 2
and another of size 1 simultaneously only when the smaller one hits all conflicts — but if the
conflicts are `{a,b}` and `{c}`, then `{c, a}` is *not* minimal whereas `{b, c}` and `{a, c}`
are minimal hitting sets of size 2 while no size-1 set hits both unless an element is shared.
The clean illustration: conflicts `{a,b}` and `{a,c}` give minimal diagnoses `{a}` (size 1)
and `{b,c}` (size 2). Both are subset-minimal; only `{a}` is minimal-cardinality. So
"minimal" is a strictly weaker property than "minimal-cardinality," which is exactly why TGDE
distinguishes the two and computes them separately.

---

## Exercise 3 (★) — At most one predicted value per measurement point per diagnosis

**Paraphrase.** Explain why, for any single diagnosis, each measurement point has at most one
predicted value (re Section 17.3). Could a variable such as `Z` ever take two different
values within one diagnosis?

**Answer.** Fixing a diagnosis `Δ` fixes the OK/faulted status of every component: components
in `Δ` are unconstrained (their faulted models contribute nothing, or only the trivial "any
output" model), and every component **not** in `Δ` is asserted `OK`, so its behavioral
equations hold. Under that fixed assumption set, the device behaves as a deterministic system
of equations over the good components plus the known inputs. Constraint propagation
(local propagation / the ATMS over the good-component justifications) is **functional**: a
correctly-modeled good gate maps fixed inputs to a unique output. So whatever values get
derived at a measurement point are derived by deterministic functions of the inputs, and the
point gets **at most one** predicted value (it may get *none* if the value isn't determined,
e.g. an output that depends on a faulted component).

Could `Z` get two values? Only if the model *and the diagnosis together are inconsistent* —
i.e. two derivation paths predict different values for `Z`. But two distinct predicted values
at one point is exactly a **contradiction**: it asserts a node is both `v1` and `v2`. That
makes the underlying environment a **nogood/conflict**, which means `Δ` is **not** a diagnosis
at all (it was ruled out). So *within a genuine diagnosis* `Z` cannot have two values; the
appearance of two values is precisely the signal that the assumed-good set is inconsistent and
must be discarded (it becomes a conflict that constrains the real diagnoses). This is why the
predicted-value table is single-valued per (diagnosis, point): multivaluedness and
diagnosis-hood are mutually exclusive.

---

## Exercise 4 (★★) — Compute minimal diagnoses directly (small fault sets, not large good sets)

**Paraphrase.** The ATMS interpretation-construction method works well when interpretations
contain few assumptions, but here the diagnoses correspond to the *good* components, so each
interpretation carries `n − k` assumptions (large). Devise an algorithm that computes minimal
diagnoses directly, manipulating the small **faulted** sets rather than the large good sets.

**Answer (conflicts → minimal hitting sets, computed directly over fault sets).**

The key is the duality: minimal diagnoses are the **minimal hitting sets** of the **minimal
conflicts**, and conflicts are small (a conflict is a set of good components whose joint OK is
already contradicted by OBS, typically just the support of one violated prediction). So work in
the dual space.

1. **Collect minimal conflicts.** As each measurement arrives, when a predicted value clashes
   with the measured value, the ATMS environment supporting the prediction is a conflict
   `C = {ci : OK(ci) was used}`. Keep the set `𝒞` of conflicts minimized (drop any conflict
   that is a superset of another). Conflicts are small (bounded by the dependency depth, not by
   `n`).

2. **Incrementally maintain minimal hitting sets.** Maintain `𝒟`, the set of minimal hitting
   sets of `𝒞` so far, represented as small fault sets. When a new minimal conflict `C` arrives,
   update each current minimal diagnosis `Δ ∈ 𝒟`:
   - If `Δ ∩ C ≠ ∅`, `Δ` already hits `C`; keep it.
   - Otherwise `Δ` fails to hit `C`; replace it with the children `Δ ∪ {x}` for each `x ∈ C`.
   Then re-minimize `𝒟` (remove any set that is a superset of another). This is exactly
   Reiter's HS-DAG / de Kleer's incremental hitting-set update, but the data objects are the
   *faulted* sets, which stay small (size = current cardinality of the diagnosis), never the
   `n − k` good sets.

3. **Output.** `𝒟` is the set of minimal diagnoses, each stored as a small fault set.

**Pseudocode (incremental):**

```
D := { {} }                       # empty fault set hits the empty conflict collection
for each minimal conflict C arriving:
    new_D := {}
    for Δ in D:
        if Δ ∩ C ≠ ∅:
            new_D.add(Δ)          # already a hitting set
        else:
            for x in C:
                new_D.add(Δ ∪ {x})
    D := minimal(new_D)           # keep only ⊆-minimal sets
```

**Why this is the requested improvement.** Memory and work scale with the (small) sizes of
conflicts and minimal diagnoses, not with the `(n−k)`-sized good environments the naive ATMS
interpretation construction would carry. Cost is governed by the number and size of minimal
conflicts and the branching `|C|` at each step; for the common case of few small conflicts it
is far cheaper than building good-component interpretations. (Worst case it is still
exponential — minimal hitting set is NP-hard — but the *typical* case with few small conflicts
is exactly where this representation wins.)

---

## Exercise 5 (★★) — Make `smallest-diagnoses` cheap (avoid the minimal-cardinality bottleneck)

**Paraphrase.** TGDE typically spends most of its effort building **minimal-cardinality**
diagnoses. Rewrite `smallest-diagnoses` so TGDE seldom does much work finding diagnoses.

**Answer.** The expense comes from insisting on *globally* minimal-cardinality diagnoses,
which requires (in effect) proving that no smaller hitting set of the conflicts exists — a
search over the whole lattice frontier. We can almost always avoid that proof because diagnosis
probabilities under independent rare faults fall off **exponentially** with cardinality. Use a
**probability-threshold / best-first** strategy instead of an exhaustive minimal-cardinality
sweep:

1. **Generate by increasing cardinality, lazily.** Enumerate candidate diagnoses (hitting
   sets) in nondecreasing order of cardinality using a best-first frontier (priority queue keyed
   by probability, which for rare independent faults is monotone in cardinality). Stop pulling
   candidates as soon as the **accumulated probability mass** of the diagnoses found so far
   exceeds a threshold (say 0.99 of total), or the next candidate's prior probability is below
   `ε`. The remaining (larger, exponentially less likely) diagnoses are never materialized.

2. **Cache the conflict-driven frontier.** Maintain the minimal hitting sets incrementally
   (Exercise 4) so that after each measurement you *update* the diagnosis set rather than
   recomputing `smallest-diagnoses` from scratch. Most measurements change only a few conflicts.

3. **Bound the cardinality.** Cap search at cardinality `k_max` (e.g. assume at most 2 or 3
   simultaneous faults). Under realistic priors the probability of `> k_max` simultaneous faults
   is negligible, so the cap is almost never binding yet eliminates the deep, expensive part of
   the lattice.

**Net effect.** `smallest-diagnoses` becomes "the few most probable diagnoses, generated lazily
and cached," so TGDE does `O(few)` work per step rather than re-deriving the whole
minimal-cardinality frontier. The trade is completeness vs. cost: you no longer guarantee you
have *all* minimal-cardinality diagnoses, only enough probability mass to drive measurement
selection — which is all the entropy computation actually needs.

---

## Exercise 6 (★★) — Hierarchical models (one OK assumption shared by a subcircuit)

**Paraphrase.** Extend TGDE's modeling language so models can be hierarchical: e.g. a full
adder gets a single `OK(adder)` assumption, and that one assumption is threaded into all the
rules implementing the gates inside it.

**Answer (design).**

- **Component as a module with one health assumption.** Let a model definition introduce a
  device type with ports and **one** assumption symbol `OK(self)`. A full-adder definition
  `(defcomponent full-adder (a b cin) (sum cout) …)` creates `OK(fa1)` for an instance `fa1`.

- **Guard every internal rule by the parent assumption, not by per-gate assumptions.** The
  adder's behavior is written as internal rules implementing its sum/carry equations, and each
  internal justification carries `OK(self)` in its antecedents. So predictions made inside the
  adder depend on `OK(fa1)`, and only `OK(fa1)` appears in their ATMS environments. The
  *internal* gates do **not** get their own `OK` assumptions (or if they do for a finer model,
  the parent assumption is added as a conjunct so the whole module can be exonerated/faulted as
  a unit).

- **Diagnosis granularity = the chosen hierarchy level.** With one assumption per adder, a
  conflict that uses the adder's behavior yields the conflict element `OK(fa1)`, so the
  diagnosis lattice is over *modules* (adders), not over the leaf gates. This is the whole point:
  it shrinks `n`, hence the lattice, dramatically.

- **Refinement on demand (hierarchical diagnosis).** Optionally support **expanding** a
  suspected module: once `fa1` is implicated, re-instantiate it with per-gate assumptions
  `OK(g1)…OK(gk)` and link `OK(fa1) ⇔ OK(g1) ∧ … ∧ OK(gk)` (the module is OK iff all its parts
  are). Re-run diagnosis on the expanded model restricted to the suspect module. This gives
  coarse-to-fine diagnosis: cheap module-level pass first, then drill into the implicated module.

- **Language mechanics.** The macro/translator that compiles a model emits, for each internal
  justification, the antecedent list with `OK(parent-instance)` spliced in; nesting composes
  (a gate inside an adder inside an ALU collects `OK(alu) ∧ OK(adder) ∧ OK(gate)` if you want
  per-level health, or just the top-most active level if you want module granularity). The
  assumption is passed down the instantiation tree exactly like a lexically scoped parameter.

**Benefit / cost.** Benefit: exponentially smaller lattice and far fewer conflicts at the
coarse level. Cost: coarse diagnoses are less specific (you learn "the adder is bad," not
"which gate"); refinement recovers specificity at extra cost only for implicated modules.

---

## Exercise 7 (★★) — Horizon effect: best measurement for cardinality `k` ≠ best for `k+1`

**Paraphrase.** The measurement that best discriminates among cardinality-`k` diagnoses may be
suboptimal for cardinality `k+1`. Give an example where TGDE makes more measurements than
necessary because of this horizon effect. (Hint: a multiple-fault case where the first few
measurements rule out all single faults.)

**Answer (example).** TGDE greedily picks the next measurement to best discriminate among the
*currently most probable* diagnoses, which (under rare-fault priors) are the **single faults**.
Construct a device where the true fault is a **double fault** but the single-fault hypotheses
"point" the measurement strategy in the wrong direction.

Consider a circuit with components `{a, b, c, d}` arranged so that:

- Measurements `m1, m2` are each highly informative for telling single faults apart (each
  cleanly separates "is it `a`?" vs "is it `b`?", etc.), so a greedy entropy-minimizer prefers
  them while single faults dominate the probability mass.
- The **true state** is the double fault `{c, d}`, whose joint misbehavior happens to be
  *invisible* at `m1` and `m2` (the two faults' effects on those points cancel, or those points
  lie outside the cone of `{c,d}`'s influence).
- A different measurement `m3` would directly reveal the `{c,d}` interaction in one shot.

Then TGDE, while single faults still carry most of the prior mass, spends `m1` and `m2` driving
down single-fault entropy. After those two measurements **all single faults are eliminated**
(each contradicts an observation), and only then does the probability mass shift to double
faults. At that horizon the engine finally selects `m3` and identifies `{c,d}`. So it used
**3** measurements (`m1, m2, m3`) where an oracle that anticipated the double fault would have
gone straight to `m3` and (with one disambiguating follow-up) used **fewer**.

**Why it happens.** Greedy one-step lookahead optimizes expected information **against the
current posterior**, which is dominated by the wrong (single-fault) hypotheses early on. The
measurements that crush single-fault entropy are wasted once the answer turns out to live at
cardinality `k+1`. Fixing it requires multi-step lookahead or a measurement utility that
hedges across cardinalities — both more expensive, which is why TGDE accepts the horizon
effect.

---

## Exercise 8 (★) — A TGDE misdiagnosis caused by its probability model, not by incompleteness

**Paraphrase.** Give an example where TGDE reports the wrong diagnosis even though its logic is
complete — the error comes from its oversimplified probability assumptions, not from missing
inferences.

**Answer.** TGDE assumes component faults are **independent** and that each component has a
small, fixed prior fault probability `p`, so a `k`-fault diagnosis gets probability `∝ p^k`
and the engine reports the **most probable** (hence smallest-cardinality) consistent diagnosis.
Both assumptions can produce a confident wrong answer while the logic is perfectly sound.

**Example (independence violated by a common cause).** Two components share a power rail or sit
on the same chip; a single environmental event (over-voltage, heat) faults **both** `c` and
`d` together. Reality: faults are correlated, `P({c,d})` is high. TGDE's model: `P({c,d}) = p^2`
is tiny, while each single fault `P({a})=p` is far larger. Suppose the observations are
**consistent with both** the true double fault `{c,d}` **and** a single fault `{a}` (the
double fault and the single fault both explain OBS — diagnoses are not uniquely determined yet).
TGDE will rank `{a}` far above `{c,d}` purely because `p ≫ p^2`, and report `{a}`. That is a
misdiagnosis: the device is logically modeled correctly, every inference is sound, no diagnosis
was missed — the engine simply assigned the wrong *probabilities* because its independence /
equal-prior assumption ignored the common-cause correlation.

**Variant (wrong priors).** Even with independence, if one component is actually far more
failure-prone than TGDE's uniform `p` assumes, TGDE can prefer a less-likely competitor.
Either way the failure is **probabilistic**, not logical: re-running with a correct joint prior
fixes it without changing a single inference rule.

---

## Exercise 9 (★★★) — A complete diagnostic procedure on top of the CLTMS

**Paraphrase.** Since the CLTMS is a general propositional reasoner, you can implement
diagnosis straight from the formal definitions. Using the CLTMS, build an algorithm that finds
the minimal diagnoses of any propositional model; try it on the polybox example; and discuss
the drawbacks of this approach.

**Answer (algorithm).** Encode the model so the CLTMS reasons about it directly:

1. **Encode.** For each component `ci` add a health literal `OK(ci)`. Encode the behavior as
   clauses guarded by health: for a good component, `OK(ci) ⇒ (behavior equations)`. (For a
   "weak fault model," faulted components impose no constraint; for a "strong fault model," add
   `¬OK(ci) ⇒ (fault behavior)`.) Add the inputs and each measurement as unit clauses (OBS).

2. **Test diagnosis-hood via the complete reasoner.** A fault set `Δ` is a diagnosis iff
   `MODEL ∧ OBS ∧ (∧_{c∉Δ} OK(c)) ∧ (∧_{c∈Δ} ¬OK(c))` is **satisfiable**. Because the CLTMS
   is logically **complete** (its `complete()` adds the prime implicates so BCP detects every
   entailment, including every contradiction), you can decide satisfiability/consistency of any
   such environment soundly and completely — this is what distinguishes the CLTMS from the
   ordinary LTMS for this task.

3. **Search the lattice minimally.** Find minimal diagnoses by an upward search over fault
   sets: test `Δ = {}`; if inconsistent, expand to single faults, etc.; keep only ⊆-minimal
   consistent sets. Equivalently and more efficiently, extract **minimal conflicts** from the
   CLTMS (each minimal inconsistent set of `OK` literals) and take their **minimal hitting
   sets** (Exercise 4). The CLTMS's completeness guarantees no conflict is missed, so the
   hitting sets are exactly the minimal diagnoses.

**On the polybox.** The polybox (de Kleer's three-multiplier / two-adder circuit:
`m1=a·c, m2=b·d, m3=c·e, x=m1+m2, y=m2+m3`) with inputs `a=b=c=d=e=3`, observed `x=10` (not 12)
and `y=12` yields minimal conflicts `{M1,A1,M2}` and `{A1,M2,A2,M3}` (using the OK literals of
those components), whose minimal hitting sets give the classic minimal diagnoses `{M1}`,
`{A1}`, and `{M2}` plus the larger ones — i.e. the procedure recovers exactly the textbook
polybox diagnoses.

**Drawbacks.**
- **Exponential search.** The lattice has `2^n` candidates; testing consistency over it (or
  enumerating minimal conflicts) is worst-case exponential. Satisfiability is NP-hard, so a
  *complete* per-environment test is expensive.
- **Cost of completion.** Making the CLTMS complete requires computing prime implicates, which
  is itself exponential in the worst case; you pay that up front.
- **No focusing.** This brute-force formal procedure has no probabilistic guidance — it does
  not prioritize likely (small) diagnoses or pick informative measurements, so it does
  *correctly* what GDE/TGDE do *efficiently*. It is a clean reference implementation, not a
  practical engine: GDE's ATMS-with-priors approach is far faster on real devices precisely
  because it avoids full completion and exhaustive lattice search.

---

## Exercise 10 (★★★) — Best **inputs** to apply (active diagnosis by stimulation)

**Paraphrase.** TGDE picks the best measurement to take next, but sometimes you cannot measure
more points and must instead choose new **inputs** to apply and re-measure outputs. Build a
TGDE variant that selects the best inputs. (Hint: make an assumption for every possible value
of every input cell. Try it on the full adder. Will it also work on the polybox?)

**Answer (design).** Treat the inputs as controllable rather than given, and choose the input
vector that is expected to be most discriminating among the current diagnoses.

1. **Assumptionize the inputs.** For each input cell `Ij` and each possible value `v` it can
   take, create an assumption `input(Ij)=v`. Exactly one value-assumption per input is active
   at a time (mutually exclusive choices). These input assumptions enter the ATMS environments
   alongside the `OK` assumptions, so every prediction is now labeled with *both* which
   components it assumes good *and* which input vector produced it.

2. **Predict over candidate input vectors.** For each candidate input vector `I = (v1,…,vm)`
   and each current diagnosis `Δ` (with its probability `P(Δ)`), use the ATMS labels to compute
   the predicted output values at the measurable outputs. Group the diagnoses by the
   output-vector they predict under `I`: this partitions the diagnoses into classes that `I`
   would distinguish.

3. **Score by expected information.** For each candidate `I`, the measured outputs will reveal
   which prediction class is true. Compute the expected entropy reduction (same one-step
   information-gain criterion TGDE already uses for measurements, but now the "experiment" is an
   input vector and its outputs):
   `score(I) = H(current Δ distribution) − E_{outcome}[ H(Δ | outputs under I) ]`.
   Pick the input vector with the highest score (cheapest, if costs differ). Apply it, measure
   the outputs, and update conflicts/diagnoses as usual.

4. **Loop.** Repeat: each chosen input vector splits the diagnosis set further until one
   diagnosis (or an acceptable few) remains.

**On the full adder.** This works very well. The full adder has discrete inputs `a, b, cin ∈
{0,1}`, so there are only `2^3 = 8` input vectors — a tiny experiment space. Each candidate
fault (a stuck gate) reveals itself for *some* input combination, so the algorithm can compute,
for the 8 vectors, which ones separate the suspected gate faults and choose the most
discriminating stimulus. (This is essentially digital test-vector / fault-discrimination
generation, which is exactly what input-selection diagnosis reduces to here.)

**Will it work on the polybox?** Conceptually yes, but with a serious practical caveat. The
polybox cells are **integer-valued arithmetic** (`·`, `+`), so each "input cell" has an
effectively **unbounded / very large domain**. Creating an assumption "for every possible value
of every input" is impractical — the input-assumption space and the candidate input-vector
space are huge (or infinite). You would have to **restrict** to a finite, representative set of
test values (and the prediction/entropy computation over numeric outputs is heavier than over
the adder's Booleans). So the hint's literal recipe (one assumption per possible input value)
is natural for the finite-domain digital full adder but does **not** scale to the polybox's
numeric domain without discretization — the algorithm is correct, but its enumeration step is
only tractable for small finite input domains.

---

*All answers above are conceptual analyses; nothing in this chapter is implemented in the
package, so there is no code to run.*
