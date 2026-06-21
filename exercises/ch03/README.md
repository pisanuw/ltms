# Chapter 3 — Classical Problem Solving (Analysis Only)

These are **analysis-only** answers. Chapter 3's Classical Problem Solver (CPS),
the subway/beam search code, and the algebra rewrite system are **not implemented
in the LTMS package** (CPS is explicitly a non-goal in `BRIEFING.md`), so there is
**no `solutions.py`** here. Each exercise below gives a paraphrase of what is asked,
followed by a conceptual answer: an algorithm sketch, derivation, complexity argument,
or design. No code is provided.

Notation reminders from the chapter: `bsolve`/`beam-solve` is the generic best-first
search driver, `n`/`ri` is the beam width, `algebra-distance` is the heuristic for the
algebra domain, `match` is the one-shot pattern matcher, `?x` matches one element and
`??x` (segment variable) matches a (possibly empty) run of elements, and operators come
in three families: isolation, attraction, and collection.

---

## Exercise 1 (*) — Minimum beam width for the Boston subway

**Paraphrase.** Find the smallest beam width passed to `beam-solve` that still lets the
search plot a route from Logan Airport to Kendall Square.

**Answer.** This is an empirical, data-dependent question whose exact answer depends on
the specific subway graph encoded in the book's data file and on the heuristic and
tie-breaking order used. The conceptual point is what beam search does and how to find
the threshold.

- Beam search keeps only the best `b` nodes at each frontier expansion (it is best-first
  pruned to width `b`). It is **incomplete**: with too small a beam it can permanently
  discard the only nodes on any path to the goal and then fail even though a route exists.
- Procedure to find the minimum: run `beam-solve` with `b = 1, 2, 3, ...` increasing, and
  report the smallest `b` that returns a successful course. Because pruning is monotone in
  a loose sense but not strictly (a wider beam can occasionally change tie order), confirm
  the threshold by also checking that the next one or two larger widths still succeed.
- Expected result and reasoning: the Logan-to-Kendall trip requires at least one line
  transfer (e.g., Blue line toward downtown, then Red line out to Kendall/MIT). At a
  transfer station the goal-directed heuristic (straight-line / hop distance) does **not**
  reward stepping onto the transfer line, so the correct successor is usually not the
  single best-ranked node. A beam of `b = 1` (pure greedy/hill-climbing) therefore
  typically fails at the transfer. A small width on the order of `b = 2` or `b = 3` is
  the realistic minimum: just enough to retain the transfer node alongside the
  greedily-preferred-but-dead-end node.

**State assumption.** I do not have the book's exact subway data loaded, so I cannot give
the single numeric answer with certainty; the defensible claim is `b = 1` fails (greedy
gets stuck at the transfer) and the minimum successful width is small (about 2-3). The
method above pins it down exactly once the data file is run.

---

## Exercise 2 (*) — `algebra-distance` can overestimate

**Paraphrase.** Show that the `algebra-distance` heuristic can report more steps than are
actually needed to solve an equation (i.e., it is not admissible).

**Answer.** `algebra-distance` estimates remaining work essentially by counting structural
features that separate the current equation from the goal form `x = (something)` —
roughly, the number of occurrences of the unknown plus the operator nesting depth around
those occurrences (each occurrence and each enclosing operator looks like it needs its own
collection/isolation step). It overestimates whenever **one operator removes several of
those features at once**.

Concrete witness. Consider

    x + x = 6.

A naive feature count sees the unknown appearing twice and concludes two collection
steps plus an isolation step are needed (heuristic value about 3). But a single collection
rule `x + x -> 2*x` rewrites the left side to

    2*x = 6,

and then one isolation step gives `x = 3`. The actual cost is **2 steps**, while the
heuristic predicted about 3. Therefore `algebra-distance(x + x = 6) > h*(x + x = 6)`,
so the heuristic overestimates and is not admissible.

A second, stronger witness: `x*x = x` (or any equation where a single algebraic identity
collapses many occurrences, e.g. factoring `x^2 - x = 0` to `x(x-1)=0`). The heuristic
counts every occurrence of `x`, but one factoring/collection move can dispatch several at
once. **Consequence:** because the heuristic is not admissible, A* using it is not
guaranteed to return an optimal (shortest) solution sequence.

---

## Exercise 3 (*) — Cycle detection in `bsolve` (dedup explored states)

**Paraphrase.** Modify `bsolve` so that newly proposed paths landing on an
already-visited state are dropped; analyze the time/space cost and judge whether it pays
off.

**Answer (design).**

- Maintain a `closed` set (a hash set) of canonical state keys that have ever been
  expanded (graph search), plus optionally the states currently on the open frontier.
- When generating successors of a node, compute each child's canonical key and discard the
  child if its key is already in `closed` (or already queued). Only surviving children are
  inserted into the priority queue / beam.
- "Canonical key" matters: for algebra, normalize the equation (sort commutative operands,
  fold constants) so syntactically different but semantically identical states collapse;
  for the subway, the key is just the station (plus, if the cost model needs it, the line
  you arrived on).

**Complexity.**

- *Time:* per generated node, one hash insert + one hash lookup, both expected `O(k)`
  where `k` is the size of the state key (`O(1)` amortized in the number of nodes). The
  membership test is cheap relative to expanding a node, so the asymptotic per-node cost is
  unchanged; the win is a (potentially exponential) reduction in the **number** of nodes
  expanded, because revisited states and the duplicate subtrees hanging off them are
  pruned. Net: usually a large constant-to-exponential speedup in graph-shaped spaces.
- *Space:* adds `O(N)` storage for the closed set, where `N` is the number of distinct
  states reached. Plain tree-search keeps only the frontier; graph-search must remember
  every closed state, so worst-case memory grows from frontier-size to total-distinct-
  states.

**Is it worthwhile?**

- **Subway / map domain: yes, strongly.** The graph is small, has many cycles (you can
  ride back and forth), and revisiting stations is pure waste. The `O(N)` table is tiny and
  prevents infinite loops, so dedup is clearly worth it.
- **Algebra domain: it depends.** If a good canonical form exists, dedup catches rewrite
  loops (e.g., applying a rule and its inverse) and helps. But if states are nearly all
  distinct (a tree-like rewrite space), the closed table costs `O(N)` memory while pruning
  almost nothing, so the benefit shrinks. Recommendation: enable dedup (with normalization)
  by default for bounded domains; for memory-limited deep searches, prefer a cheaper guard
  (e.g., reject only states already on the *current path*, giving cycle-freedom at `O(depth)`
  space instead of `O(N)`).

---

## Exercise 4 (**) — Make the operator set pluggable

**Paraphrase.** The algebra operators are hard-wired. Rewrite `setup-algebra-problem` so
alternate operator sets can be swapped in and new operators added just by loading extra
files, without editing existing code.

**Answer (design).**

- Replace the hard-coded operator list with a **registry** (a global list or table) that
  operator-definition files populate at load time. Each definition file ends with a call
  like `(register-algebra-operator <op>)` (or the `defAlgebraOperator` macro of Ex. 5b),
  which appends to the registry. No central file lists the operators.
- `setup-algebra-problem` is changed to take the operator set as a parameter (or read it
  from the registry / a "current operator set" variable) instead of referencing a fixed
  constant. Signature becomes roughly `setup-algebra-problem(equation, unknown,
  operators := *current-algebra-operators*)`.
- To support **alternate sets**, key the registry by a set name: `(define-operator-set
  'trig (list ...))`, and a `(use-operator-set 'trig)` selector that binds the
  current-operator-set variable. Experiments then switch sets with one call.
- Ancillary definitions added to `algebra.lisp`: the registry variable, `register-algebra-
  operator`, `define-operator-set`, `use-operator-set`, and a defaulting of
  `setup-algebra-problem`'s operator argument to the current set.

**Effect.** Adding operators becomes "drop in a file and load it"; switching regimes
becomes a single selector call; existing operator code never has to be edited because it
only ever *appends* to the registry.

---

## Exercise 5 — Generic operator constructors and sugar

The three operator families share structure (`Name`, `Before` pattern = LHS of the law,
`After` pattern = RHS). Exploit this.

### 5a (**) — `use-attraction-operator`, `use-collection-operator`, `use-isolation-operator`

**Paraphrase.** Define one generic constructor per method class that turns a
`(Name, Before, After)` triple into a working operator object.

**Answer (sketch).** Each constructor builds and registers an operator record whose
applicability test is "does `Before` match the current expression?" and whose action is
"rewrite the matched subexpression to `After` under the resulting bindings." They differ
only in **which class the operator is filed under** and, secondarily, in *where* the match
is attempted and how the result is scored:

- *Isolation* — applied at the top level of the equation; pulls the unknown out of an
  enclosing operator (e.g., `log(arg,base) = rhs  ->  arg = base^rhs`). Filed as an
  isolation method so the driver tries it when the unknown is "wrapped."
- *Attraction* — applied to bring two separated occurrences of the unknown together
  (e.g., `log(u,w) + log(v,w) -> log(u*v, w)`). Filed as attraction; the heuristic should
  recognize it reduces the count of unknown-occurrences.
- *Collection* — applied to merge already-adjacent occurrences (e.g., the product/sum
  identity collapsing to `u^2 - v^2`). Filed as collection.

Generic skeleton shared by all three (pseudocode):

    make-operator(name, before, after, class):
        return operator{
          name:  name,
          class: class,
          applicable?(expr): (match before expr) /= :FAIL
          apply(expr):
              dict := match(before, expr)         ; bindings
              return instantiate(after, dict)     ; substitute bindings into RHS
        }
    use-isolation-operator(name, before, after)  = register(make-operator(name, before, after, 'isolation))
    use-collection-operator(name, before, after) = register(make-operator(name, before, after, 'collection))
    use-attraction-operator(name, before, after) = register(make-operator(name, before, after, 'attraction))

`instantiate` walks `after`, replacing each `(? var)` / `(?? var)` with the value bound to
`var` in `dict`. The lambda guards inside the `Before` patterns (e.g.,
`(lambda (term) (occurs-in? 'x term))`) are honored automatically because they are part of
the pattern that `match` enforces.

### 5b (**) — `defAlgebraOperator` macro

**Paraphrase.** Add syntactic sugar: a macro that defines a new operator from its name,
method class, before-pattern, and after-pattern.

**Answer (sketch).** A macro that expands into the appropriate `use-*-operator` call:

    (defmacro defAlgebraOperator (name class before after)
       `(,(case class
             ((isolation)  'use-isolation-operator)
             ((attraction) 'use-attraction-operator)
             ((collection) 'use-collection-operator))
         ',name ,before ,after))

So `(defAlgebraOperator Isolate-Log isolation <before> <after>)` expands to
`(use-isolation-operator 'Isolate-Log <before> <after>)`. This removes the boilerplate of
remembering which constructor goes with which class and gives one uniform definition form.

### 5c (**) — `defAlgebraLaw`: auto-translate an identity into operators

**Paraphrase.** Since the three method classes are purely syntactic transforms of an
identity, write a procedure that takes an algebraic identity and automatically produces the
right set of methods, wrap it in a macro `defAlgebraLaw`, and test it by adding new
identities.

**Answer (sketch).** Given a single identity `LHS = RHS`:

1. **Direction.** A usable operator must move *toward* a solved form, so orient the
   identity in the direction that reduces unknown-complexity (fewer occurrences of `x`, or
   `x` less deeply nested). If both directions are useful, emit two operators.
2. **Add the occurs-in guards.** For each pattern variable, decide from the identity
   whether the matched term must contain the unknown, must not, or is unconstrained, and
   attach the corresponding `(lambda (term) (occurs-in? 'x term))` /
   `(not (occurs-in? ...))` guard. This is exactly the hand-written guard decoration seen
   in the chapter's examples — it can be inferred from which variables appear on which
   side and how often.
3. **Classify the method:**
   - if the rewrite *exposes* the unknown by stripping an enclosing operator at the
     equation top level -> **isolation**;
   - if it *reduces the number of separate occurrences* of the unknown -> **attraction**;
   - if it *combines adjacent occurrences into one* -> **collection**.
4. **Emit** the corresponding `use-*-operator` call(s) via the 5a constructors.

`defAlgebraLaw` is the macro front end: `(defAlgebraLaw <lhs> <rhs>)` expands to a `progn`
of the generated `use-*-operator` forms. Test by feeding it identities such as
`a*(b+c) = a*b + a*c`, `log(u)+log(v) = log(u*v)`, `(a+b)(a-b) = a^2 - b^2`, then solving
equations that need them and confirming the operators fire and are filed under the right
class.

**Caveat to state.** Fully automatic classification and guard inference is heuristic; for
ambiguous identities the translator may need a hint (which variable is the unknown, which
direction to orient). A practical implementation lets the user override class/direction.

---

## Exercise 6 (**) — Implement A* search

**Paraphrase.** Using the search variants in `variants.lisp` as a template, add A* search.

**Answer (sketch).** A* is best-first search ordered by `f(n) = g(n) + h(n)`, where `g` is
the path cost from the start and `h` is the heuristic estimate to the goal. Given the
chapter's generic best-first driver, A* is the instantiation that uses this `f` as the
priority key. Algorithm (graph-search form):

    A*(start, goal?, successors, cost, h):
        open := priority-queue keyed by f, containing node(start, g=0, f=h(start))
        best-g := { start -> 0 }                 ; best known g per state
        while open not empty:
            n := pop-min(open)                   ; lowest f
            if goal?(n.state): return reconstruct-path(n)
            for (s', step) in successors(n.state):
                g' := n.g + cost(step)
                if s' unseen or g' < best-g[s']:
                    best-g[s'] := g'
                    f' := g' + h(s')
                    push(open, node(s', parent=n, g=g', f=f'))
        return :FAIL

Key points to get right relative to the chapter's framework:

- The priority/merge function differs from plain best-first (which keys on `h` alone) and
  from uniform-cost (which keys on `g` alone); A* sums them. In the book's variant style,
  this is just supplying a different comparison/merge predicate to the shared driver.
- Keep `best-g` so a cheaper route to a state replaces a worse one (handles re-expansion).
- **Admissibility:** if `h` never overestimates true remaining cost, A* returns an optimal
  solution. Note (per Ex. 2) `algebra-distance` is **not** admissible, so A* on the algebra
  domain is fast but not guaranteed optimal; the straight-line/hop heuristic on the subway
  is admissible, so A* is optimal there.

---

## Exercise 7 — Exhaustive / multi-result `match`

The current `match` returns the *first* legal binding or `:FAIL`. A rewrite system that
backtracks needs *all* matches.

### 7a (*) — Why the given call returns `:FAIL`

**Paraphrase.** Explain why this call fails:

    (match '(+ (* (?? A) x (?? B)) (* (?? A) (- 1 x)))
            '(+ (* 2 x x) (* 2 x (- 1 x))))

**Answer.** The pattern uses the **segment variable `A` twice** and requires both uses to
bind to the **same** sequence. Consider the two product subterms that must match in order:

- First conjunct of the pattern, `(* (?? A) x (?? B))`, against `(* 2 x x)`.
  `match` is one-shot and greedy/left-to-right. To make the literal `x` in the pattern line
  up, the *first* successful binding it commits to is `A = (2)`, then the pattern's `x`
  matches the data's first `x`, leaving `B = (x)`. So after the first product, `A` is locked
  to `(2)`.
- Second conjunct, `(* (?? A) (- 1 x))`, against `(* 2 x (- 1 x))`. With `A` already pinned
  to `(2)`, the pattern reduces to `(* 2 (- 1 x))`, but the data is `(* 2 x (- 1 x))` — there
  is an extra `x` between `2` and `(- 1 x)`. `2 (-1 x)` cannot equal `2 x (-1 x)`, so this
  conjunct fails.

The binding that *would* succeed is `A = (2 x)` (so the second product is `(* 2 x (- 1 x))`,
matching exactly, and the first product is `(* 2 x x)` with the trailing `x` absorbed by
`B`). But that requires `A` to absorb the `x` in the **first** product too, i.e.
`A = (2 x)`, `B = ()`. The single-pass matcher commits to the *first* consistent binding of
`A` it finds while processing the first conjunct (`A = (2)`), never reconsiders it, and so
never discovers the globally consistent assignment `A = (2 x)`. Lacking backtracking over
the segment variable's earlier commitment, `match` returns `:FAIL` even though a consistent
match exists. This is exactly the motivation for the exhaustive/backtracking version.

### 7b (*) — All-matches version of `match`

**Paraphrase.** Rewrite `match` to return a *list of dictionaries*, one per distinct legal
way the pattern matches the expression.

**Answer (sketch).** Convert the matcher to **continuation/accumulation style** that
collects every consistent binding set instead of stopping at the first:

    match-all(pat, exp, dict):           ; returns a list of dictionaries (possibly empty)
      - constant pat: if pat = exp return (list dict) else return '()
      - (? v guard...): if guard(exp) and consistent(v, exp, dict)
                          return (list (extend dict v exp)) else '()
      - (?? v ...): a segment var: for each split point i of the remaining exp list,
            let seg = first i elements;
            if guard(seg) and consistent(v, seg, dict):
                append the results of matching the rest of the pattern against the
                remaining (len-i) elements, under (extend dict v seg);
            collect (append) all such successful continuations.
      - list pat: match the head element-pattern producing a *set* of partial dicts,
            then for each, recursively match-all the tail, appending all results.

The crucial change from the one-shot matcher is that a segment variable iterates over
**all** split points and the element matcher returns a **set** of dictionaries that the
caller flat-maps over, so every consistent assignment survives. For the 7a example this
returns the single dictionary `{A=(2 x), B=()}` instead of `:FAIL`. An empty list means no
match (the analog of `:FAIL`).

### 7c (**) — Incremental (generator) `match`

**Paraphrase.** Because there can be very many matches, make `match` produce them lazily:
return the current dictionary plus a zero-argument procedure that yields the next match and
a fresh generator.

**Answer (sketch).** Wrap the search in a **lazy stream / generator** so matches are
produced on demand rather than all at once:

- Represent the search as a closure over the matcher's choice stack (the pending split
  points for each `??` variable and the position in each list). Returning a match also
  returns a thunk that, when called, resumes the search from the most recent unexhausted
  choice point (backtracking by advancing the next segment-split index), and yields either
  `(values next-dict next-thunk)` or `(values :no-more nil)`.
- Mechanically this is the all-matches algorithm of 7b transformed to coroutine form: each
  place where 7b *appends* results becomes a place where the generator *yields* the first
  result now and stores the continuation to produce the rest later. In Lisp this is done
  with success/failure continuations (a success continuation that captures "what to do for
  the next answer") or an explicit agenda of resumable choice points.
- Benefit: a backtracking rewrite system pulls matches one at a time and stops as soon as a
  rule application succeeds, avoiding the cost of enumerating the (possibly exponential)
  full match set. Space is `O(depth of choice stack)` instead of `O(number of matches)`.

---

## Exercise 8 — Iterative deepening

Premise: in an exponentially branching tree, the number of nodes at depth `d` is on the
order of the total number of nodes above depth `d`, so re-exploring shallower levels while
pushing the bound deeper costs only a constant factor.

### 8a (*) — `id-search`

**Paraphrase.** Implement iterative-deepening DFS.

**Answer (sketch).** Run depth-limited DFS repeatedly with an increasing cutoff:

    id-search(start, goal?, successors):
        for limit = 0, 1, 2, ... :
            result := dls(start, goal?, successors, limit)
            if result /= :cutoff-only : return result   ; found a solution, or proved none exists
    dls(node, goal?, successors, limit):
        if goal?(node.state): return path(node)
        if limit = 0: return :cutoff                      ; hit the bound, deeper nodes unseen
        cutoff-hit? := false
        for s' in successors(node.state):
            r := dls(child(node, s'), goal?, successors, limit-1)
            if r is a path: return r
            if r = :cutoff: cutoff-hit? := true
        return (if cutoff-hit? :cutoff :failure)          ; distinguish "bound reached" from "subtree exhausted"

If a whole iteration completes with no `:cutoff` anywhere, the space is exhausted and there
is no solution. Memory is `O(b*d)` (DFS frontier) and time is `O(b^d)` — the repeated
shallow work adds only a constant factor `b/(b-1)`.

### 8b (**) — Empirical comparison

**Paraphrase.** Compare `id-search` empirically against the other strategies on the subway
and algebra domains.

**Answer (what to measure and expected outcome).** Instrument each strategy to count
**nodes expanded**, **peak frontier/memory**, and **solution length**, then run all
strategies on a battery of subway routes and algebra equations of varying difficulty.

- *Optimality / solution length:* ID-DFS returns a **shortest-in-#-steps** solution (like
  BFS) because it finds the goal at the smallest depth bound; plain DFS does not; best-first
  with a non-admissible heuristic (algebra) need not.
- *Memory:* ID-DFS uses `O(b*d)` — far less than BFS/best-first, which can hold an
  exponential frontier. This is its main selling point.
- *Time:* ID-DFS re-expands shallow nodes each iteration, so it does more node expansions
  than BFS by a constant factor `~b/(b-1)`; on the subway (small `b`, shallow goals) the
  overhead is modest. On algebra, a good (if inadmissible) heuristic in best-first usually
  expands far fewer nodes than uninformed ID-DFS, so best-first/A* tends to win on raw
  expansions while ID-DFS wins on memory and on guaranteeing minimal step count.
- *Expected verdict:* ID-DFS is the best memory-vs-optimality tradeoff for uninformed
  search; where a useful heuristic exists (algebra), informed search is faster but may give
  longer solutions.

### 8c (**) — Iterative-deepening A* (IDA*)

**Paraphrase.** Apply iterative deepening to A*: implement IDA* and evaluate it.

**Answer (sketch).** IDA* replaces the *depth* bound with an `f = g + h` **cost bound**:

    ida*(start, goal?, successors, cost, h):
        bound := h(start)
        loop:
            t := dfs-contour(start, g=0, bound)         ; DFS pruning any node with f > bound
            if t is a solution: return it
            if t = +inf: return :FAIL                    ; no node left to expand
            bound := t                                   ; t = smallest f that exceeded the old bound
    dfs-contour(node, g, bound):
        f := g + h(node.state)
        if f > bound: return f                            ; over the contour; report its f
        if goal?(node.state): return solution(node)
        min := +inf
        for (s', step) in successors(node.state):
            r := dfs-contour(child(node,s'), g + cost(step), bound)
            if r is a solution: return r
            min := minimum(min, r)
        return min

Each iteration explores the set of nodes with `f <= bound` (a "contour"); the next bound is
the smallest `f` that exceeded the current one. Properties: memory `O(b*d)` like ID-DFS,
optimal when `h` is admissible (so optimal on the subway, not guaranteed optimal on algebra
where `algebra-distance` overestimates). Empirically IDA* keeps A*'s informedness while
slashing A*'s memory; its weakness is many re-expansions when `f`-values are nearly all
distinct (each iteration may raise the bound by a tiny amount), which can make it
re-traverse almost the whole prefix repeatedly.

---

## Exercise 9 — Lifting the algebra system's two limitations

The system hard-codes a single unknown and solves one equation at a time.

### 9a (*) — Configurable unknown

**Paraphrase.** Let the variable being solved for be specified per problem rather than
fixed.

**Answer (design).** Thread the unknown through as data instead of hard-coding `x`:

- Add an `unknown` parameter to `setup-algebra-problem` and store it in the problem/state.
- Everywhere an operator's guard tests `(occurs-in? 'x term)`, replace the literal `'x`
  with the problem's current unknown — most cleanly by binding a dynamic variable
  `*unknown*` for the duration of the solve and having the guards read it
  (`(occurs-in? *unknown* term)`), or by closing the guard lambdas over the unknown when the
  operator is instantiated.
- The goal test becomes "the LHS is exactly `*unknown*` and the RHS is free of
  `*unknown*`," again parameterized rather than literal.

This is a small change because the only place the unknown is "known" is in the operator
guards and the goal test.

### 9b (**) — Systems of equations

**Paraphrase.** Generalize states to *sets* of equations; the goal is a state containing an
equation with the designated unknown alone on the left and free of it on the right. (Hint:
treat the choice of which variable to substitute for as its own search, calling CPS
recursively to solve for it.)

**Answer (design).**

- **State** = a set (conjunction) of equations rather than one equation.
- **Operators** at this level are *substitution* moves: pick an equation in the set, pick a
  variable `v` occurring in the set, solve that equation for `v` (this is the inner,
  single-equation CPS from Ex. 9a, called **recursively**), then substitute the resulting
  expression for `v` into the other equations, yielding a new state with one fewer variable.
- **Search controls the substitution order:** which variable to eliminate next, and using
  which equation, are the choice points; CPS searches over these choices. This is Gaussian-
  elimination-as-search, but symbolic and over arbitrary algebraic (not just linear) forms.
- **Goal test:** some equation in the state has the designated unknown isolated on the LHS
  and an RHS free of *all* remaining variables (i.e., expressed purely in known quantities).
- **Termination/pruning:** prefer substitutions that strictly reduce the count of distinct
  variables; this guarantees progress and bounds depth by the number of variables. Cycle
  detection (Ex. 3) avoids re-deriving equivalent systems.

### 9c (*) — Equilibrium weight `W_e` from the diet equations

**Paraphrase.** Use the generalized system to derive a person's equilibrium weight `W_e`
from the given weekly diet/exercise equations.

**Answer (derivation).** The OCR mangles the equations; the standard form of this textbook
problem (weekly calorie balance) is:

- Weekly weight change: `dW = (7*M*W - C_f + C_e) / 3500`
  (`3500` kcal per pound; `7*M*W` = weekly metabolic burn, `M` ~ 11 men / 10 women;
  `C_f` = food calories that week, `C_e` = exercise calories that week, with sign convention
  that intake decreases and burn increases weight change — equivalently
  `dW = (7*M*W + C_e - C_f)/3500` reads as "burn minus intake").
- Weekly food intake: `C_f = 7 * C_fd` (`C_fd` = daily food calories, 7 days).
- Weekly exercise burn: `C_e = N * W / 150` (the chapter's `Ce = N*W/150`; about 1 kcal per
  pound of body weight per mile, times `N` miles).

**Equilibrium** is `dW = 0` (weight steady from week to week). Set the numerator to zero:

    7*M*W - C_f + C_e = 0
    7*M*W - 7*C_fd + (N*W)/150 = 0

Substitute `C_f` and `C_e`, then solve for `W = W_e`:

    7*M*W + (N/150)*W = 7*C_fd
    W * (7*M + N/150) = 7*C_fd

    W_e = 7*C_fd / (7*M + N/150)

Equivalently, clearing the 150:

    W_e = (1050 * C_fd) / (1050*M + N).

This is exactly what the recursive substitution search would produce: eliminate `C_f` and
`C_e` via their defining equations, impose `dW = 0`, and isolate `W`.

**Caveat.** The sign/constant convention of the OCR'd `SW` equation is ambiguous; I used the
conventional "burn minus intake over 3500" reading. If instead intake exceeds the
gain/loss term with the opposite sign, the algebra is identical up to a sign and the
isolation step is the same; the equilibrium condition `dW = 0` and the resulting formula
shape `W_e = 7*C_fd / (7*M + N/150)` stand.

---

## Exercise 10 (***) — Reconstruct STUDENT (algebra word problems)

**Paraphrase.** Rebuild Bobrow's STUDENT, which solved algebra *word* problems, by
(a) writing rewrite rules that turn English sentence fragments into algebraic expressions,
and (b) extending the CPS algebra system to solve the resulting equations. The worked
example (Bill's father/uncle ages) should yield Bill = 8.

**Answer (design + worked derivation).**

**(a) English -> equations via pattern rewrites.** STUDENT's method is shallow,
template-based NLP using segment-variable patterns (the `??` matcher of Ex. 7) that map
fixed phrasings onto arithmetic:

- Tokenize and apply normalizing rewrites first: `"twice"` -> `"2 times"`,
  `"X times as old as Y"` -> `(* X Y)` relation, `"sum of A and B"` -> `(+ A B)`,
  `"two years from now Z's age"` -> `(+ Z 2)`, `"is/equals/will be"` -> `=`,
  `"Find Q"` -> the unknown is `Q`.
- Treat each distinct noun phrase ("Bill", "Bill's father", "Bill's father's uncle") as a
  variable; coreference is by string identity of the (normalized) phrase, so the same phrase
  always denotes the same variable.
- Each declarative sentence becomes one equation by matching against the relation templates.
  This is precisely the "rewrite rules that translate sentence fragments into algebraic
  expressions" requested.

**(b) Solve with the (extended, multi-equation) CPS.** Feed the generated equation set into
the Ex. 9b system-of-equations solver; the designated unknown is the phrase named in "Find."

**Worked derivation of the example.** Let `B` = Bill, `F` = Bill's father, `U` = the uncle.
The sentences translate to:

1. "the uncle is twice as old as the father" -> `U = 2*F`.
2. "two years from now the father will be three times as old as Bill" ->
   `F + 2 = 3*(B + 2)`.
3. "the sum of their ages is 92" -> `U + F + B = 92`.

Solve (this is the recursive substitution search of 9b):

- From (1): `U = 2*F`. Substitute into (3): `2*F + F + B = 92` -> `3*F + B = 92`.
- From (2): `F + 2 = 3*B + 6` -> `F = 3*B + 4`. Substitute into the previous:
  `3*(3*B + 4) + B = 92` -> `9*B + 12 + B = 92` -> `10*B = 80` -> `B = 8`.

So **Bill is 8** (and `F = 28`, `U = 56`; check: `56 + 28 + 8 = 92`, and two years on
`30 = 3*10`). This matches STUDENT's published answer, confirming the rewrite-then-solve
pipeline.

**Caveats to state.** Genuine STUDENT also handled units, idioms, and an "equivalence
dictionary" for synonymous phrasings, and would *fail* on sentences outside its template
set — its competence is brittle and tied to the phrasing patterns supplied. A faithful
reconstruction therefore lives or dies by how many phrase templates you encode; the example
above needs only a handful.
