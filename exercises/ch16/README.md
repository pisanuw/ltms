# Chapter 16 — Assumption-Based Constraint Languages: exercises

**Analysis only — no code.** The Chapter 16 systems (TCON, the JTMS-backed
constraint propagator, and ATCON, the ATMS-backed constraint propagator) are
**not implemented in this package**; porting the ATMS/constraint suite is an
explicit non-goal (see `BRIEFING.md`). So these are conceptual answers
(algorithm sketches, derivations, complexity arguments, and design discussion),
not runnable demonstrations. `solutions.py` is intentionally absent and
`codeRuns = false`.

Problem statements are **paraphrased in our own words** (the originals are
copyrighted); the analysis is original.

Difficulty is shown as the book's star rating (★ = easy … ★★★★ = research-level).

---

## Background needed for both exercises

A *constraint language* attaches small local rules ("a + b = c", and any two of
the three cells determine the third) to *cells* (variables) and propagates
values when cells become known. Three ways to make such a propagator support
hypothetical reasoning and retraction:

* **TCON (no TMS / re-execution model).** Values are just stored in cells. To
  explore a different set of assumptions you change a cell, *re-run* every rule
  whose inputs changed, and on a context switch you may have to *undo and redo*
  large amounts of propagation. Rule executions are repeated once per context.

* **TCON + JTMS.** Each derived value becomes a JTMS node with a justification
  recording which inputs (and which constraint) produced it. A context is a set
  of enabled assumptions; switching contexts is a JTMS label propagation
  (believe/retract) rather than a re-execution, and cached results need not be
  recomputed — but each *node* still holds a single current value, so a value
  that is true in one context and false in another must be relabeled when you
  move between contexts.

* **ATCON (TCON + ATMS).** Each derived value is an ATMS node whose *label* is
  the set of minimal environments (assumption sets) in which it holds. A rule
  fires *once* per distinct combination of antecedent values; its result is
  recorded with the environment(s) under which it is valid. There is **no
  context switch at all**: to read a cell's value in a context you just find the
  unique node whose label environment is a subset of that context. The price is
  the bookkeeping cost of maintaining labels and the nogood/minimal-environment
  machinery, and the memory cost of caching every value-in-every-environment.

**The `atcon-delay` flag.** ATCON normally runs with `delay = t`. In that mode,
before actually executing a rule, ATCON checks whether the rule's result could
*possibly be useful* — i.e. whether the antecedents have **external support**
(support coming from outside the current constraint) and whether there is some
*single consistent environment* in which all antecedents simultaneously hold.
If not, the rule is requeued/suppressed instead of run. This suppression is
done by `has-external-support` and `has-complete-external-support`. With
`delay = nil`, ATCON skips these checks and fires every queued rule immediately.
Crucially, the delay machinery itself costs effort (it computes prospective
labels and looks for a consistent witness environment), so it is a *bet*: it
pays only when the rule work it avoids is more expensive than the check.

---

**1 (★) — Show one program that wins with `atcon-delay nil` and one that wins
with `atcon-delay t`; then characterize the two regimes.**

Paraphrase: build an ATCON example whose performance clearly *improves* when
delay is turned off (`nil`), and another whose performance clearly *degrades*
when delay is turned on (`t`), and then state the general property that
distinguishes the two cases.

Answer.

*Setup of the experiment.* For each program, count the dominant cost as
(rules actually executed × cost-per-rule) + (delay-check overhead). The delay
flag trades the second term against the first.

**(a) A program that improves with `delay = nil`** — cheap rules, no useless
rules to avoid. Take a long deterministic chain of arithmetic constraints with
exactly one consistent environment, e.g. cells `x0 = 1`, and `x_{i+1} = x_i + 1`
realized by `adder` constraints, chained `n` deep, with **no contradictions and
no branching** (every assumption used is mutually consistent, every rule has a
single set of antecedent values, and every result is genuinely wanted). Here:

* With `delay = t`: before each of the `n` additions ATCON computes the
  prospective label, verifies external support, and searches for a consistent
  witness environment — all that work is performed `n` times and **never
  prevents a single rule**, because every rule's result is in fact used. Net
  overhead ≈ `n × (delay-check cost)` with zero savings.
* With `delay = nil`: ATCON just runs the `n` cheap additions. The check cost
  vanishes.

So a fully-determined, contradiction-free, single-environment network with
*cheap* rules is strictly faster with `delay = nil`; the speedup grows linearly
in chain length `n`.

**(b) A program that degrades with `delay = t`** — same flavor, sharpened: the
*relative* harm of `delay = t` is largest exactly when (i) rules are cheap and
(ii) essentially no rule execution would have been saved. Concretely, a wide
"fan" of independent cheap constraints, all of whose outputs are consumed and
none of which is ever in a dead/inconsistent environment, manifests this:
turning delay on multiplies per-rule work by the (fixed) check overhead without
ever skipping a rule, so wall-clock time *increases* the moment you set
`delay = t`. (Equivalently: program (a) read in the other direction —
"degrades when `t`" and "improves when `nil`" describe the same network.)

**(c) The complementary program that *needs* `delay = t`** (to show the flag is
not pointless, and to anchor the characterization). Build a network where most
candidate rule firings are useless: a constraint whose output cell feeds back
into the inputs of *its own* sibling rules, plus assumptions that are
**pairwise inconsistent**, so that many antecedent combinations exist *node by
node* but no *single consistent environment* contains a whole antecedent set.
Make the rules **expensive** (e.g. each rule does a costly numeric solve or
spawns sub-constraints). With `delay = t`, `has-complete-external-support`
discovers up front that there is no consistent witness environment and suppresses
those firings, so the expensive body never runs. With `delay = nil`, every one
of those doomed combinations executes its expensive body, produces a value that
the ATMS then labels with the *empty/nogood* environment (useless), and the work
is wasted. Here `delay = t` can avoid an exponential number of expensive useless
firings, so `delay = nil` degrades catastrophically.

*Abstraction (the general characteristic).* The flag is a wager on the ratio

> savings = (# useless rule firings prevented) × (cost per rule)
> against
> overhead = (# rules considered) × (cost of one delay check).

`delay = t` wins iff `savings > overhead`. The two ends of the spectrum:

* **`delay = nil` is better** when rules are *cheap* and *almost every firing is
  useful* — deterministic, low-branching, contradiction-free networks (few or no
  inconsistent antecedent combinations, few duplicate/dead rules). The check
  never earns its keep. (Programs (a)/(b).)
* **`delay = t` is better** when rules are *expensive* and many candidate
  firings are *useless* — networks with strong feedback within constraints and
  many mutually inconsistent assumptions, so that lots of antecedent
  combinations have no consistent witness environment. A cheap up-front label
  computation then saves a costly body, possibly an exponential number of times.
  (Program (c).)

Caveats to state with any demonstration: if rules have side effects or signal
contradictions, the *order* in which rules fire differs between the two modes,
so the timing comparison must be made on a side-effect-free, confluent network
to be meaningful (the book flags this explicitly). Also, the absolute numbers
depend on the cost model assumed for one ATMS label computation versus one rule
body; the *qualitative* crossover above is robust to that choice.

---

**2 (★★) — Use an explicit nogood database to get an exponential speedup in a
JTMS-backed TCON.**

Paraphrase: assume the JTMS keeps an explicit table of *nogoods* (assumption
sets already known to be inconsistent), consulted before any assumption is
enabled. Exhibit a TCON program whose running time drops from exponential to
polynomial because of that nogood table.

Answer.

*What the explicit nogood database buys.* In plain TCON, exploring assumption
spaces means enabling assumptions, propagating, and on a contradiction
backtracking and trying the next combination — and the *same* small inconsistent
sub-combination can be rediscovered over and over inside many different larger
candidate contexts. An explicit nogood database records each minimal
inconsistent assumption set once; thereafter, **before** an assumption is
enabled, TCON checks whether enabling it would superset a recorded nogood, and
if so prunes that whole branch without any propagation. This is exactly
dependency-directed backtracking with nogood caching: a refuted *reason* is
generalized to the small set of choices that actually caused the conflict, so it
prunes every future context that contains that set, not just the one that
triggered it.

*A program that exhibits the exponential improvement.* Encode a constraint
problem with a small "core" conflict and a large irrelevant "tail":

* Choice cells `a, b` (two Boolean assumptions) wired by constraints so that the
  combination `a = T, b = T` propagates to a contradiction (e.g. a constraint
  `c = a AND b` plus a constraint forcing `c = F`). The minimal nogood is
  `{a=T, b=T}`.
* Plus `k` further *independent* Boolean choice cells `d1 … dk` that are
  completely unconstrained relative to the conflict (they only feed cheap
  downstream constraints). The full assumption space therefore has
  `4 × 2^k` candidate contexts.

Now compare:

* **Without the nogood database.** Search enumerates contexts. Every time it
  fixes `a = T, b = T` and then iterates over the `2^k` settings of
  `d1 … dk`, it re-derives the *same* `a∧b` contradiction `2^k` times — once per
  tail combination — because nothing remembers that `{a=T,b=T}` is already dead.
  Work is Θ(2^k) wasted contradiction re-derivations (exponential in `k`).
* **With the nogood database.** The *first* time `a = T, b = T` is enabled, TCON
  derives the contradiction and records the minimal nogood `{a=T, b=T}`. On
  every subsequent context, the pre-enable check sees that any context extending
  `{a=T, b=T}` supersets a recorded nogood and prunes it *before* enabling and
  *before* touching the `d` tail at all. The entire `a=T, b=T` half of the space
  collapses to a single recorded fact. The remaining consistent regions
  (`a=F` or `b=F`) are explored once. Work is polynomial in `k`.

So the speedup is Θ(2^k) → O(k): exponential, driven entirely by the database
turning "rediscover the conflict in every tail context" into "record it once,
prune by superset thereafter."

*Why this is the JTMS analogue of what ATCON gets for free.* The same pruning is
intrinsic to ATCON: the ATMS stores nogoods as part of label maintenance, never
puts an inconsistent environment into any label, and never context-switches, so
it never re-derives a known conflict. Exercise 2 shows that bolting an explicit
nogood table onto a JTMS-backed TCON recovers the key asymptotic win
(no exponential re-derivation of conflicts) without paying for full ATMS label
machinery — at the cost that TCON still re-executes rules across genuinely
distinct consistent contexts, whereas ATCON would cache those too.

*Connection to the JTMS-chapter exercise it cites.* The cited exercise (the
JTMS chapter's "maintain an explicit nogood database" problem) is the
prerequisite: it asks you to add the table and the pre-enable superset check to
the JTMS. Exercise 2 here is the payoff — a constraint program where that table
yields a provable exponential improvement, by the small-core / large-tail
construction above.

---

## Summary

| Ex | Topic | Core result |
|----|-------|-------------|
| 1 (★)  | `atcon-delay` t vs nil | Flag is a wager: `delay=t` wins when rules are expensive and many firings are useless (inconsistent/feedback networks); `delay=nil` wins when rules are cheap and almost every firing is useful (deterministic, confluent, single-environment networks). Demonstrate with a cheap deterministic chain (nil wins) vs an expensive feedback network with pairwise-inconsistent assumptions (t wins). |
| 2 (★★) | Explicit nogood database in JTMS-TCON | Small-core/large-tail program: without nogoods the `{a=T,b=T}` conflict is re-derived Θ(2^k) times across the irrelevant `d`-tail; with a consulted nogood table it is recorded once and pruned by superset, giving O(k). Recovers ATMS-style conflict caching without full label machinery. |
