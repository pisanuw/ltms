# PLAN.md — Building a Logic-based TMS and Reasoning Engine in Python

A multi-session implementation plan for a clean-room Python 3 port of the
**Logic-based Truth Maintenance System (LTMS)** and its **logic-based
reasoning engine (LTRE)** from Forbus & de Kleer, *Building Problem Solvers*
(BPS), MIT Press, 1993.

> Reference code: `refs/bps-lisp/` (Common Lisp, gitignored).
> Reference text: `refs/book/` (OCR of the book PDF, gitignored — MIT Press copyright).
> Deep technical digest of the reference: [STUDY-NOTES.md](STUDY-NOTES.md).

---

## 1. Goal, scope, non-goals

**Goal.** A faithful, well-tested, idiomatic-Python implementation of:
1. a **pattern-directed forward-chaining inference engine** (TRE → LTRE), and
2. a **Logic-based TMS** (clausal Boolean Constraint Propagation, well-founded
   support, dependency-directed backtracking, explanation),
plus the three advanced LTRE facilities (indirect proof, closed-world
assumptions, dependency-directed search).

**In scope (core).** terms + unification; TRE; the LTMS BCP engine; LTRE;
indirect proof / CWA / DD-search; explanation/`why`; a conformance test suite
ported from the book's `*-ex` example files.

**In scope (optional, later).** A JTMS (as a stepping stone and contrast); the
completeness extension (CLTMS: prime implicates via Tison/IPIA); a PySAT
backend for heavy satisfiability queries.

**Non-goals.** Porting the rest of the BPS suite (ATMS, GDE, TGIZMO/QP, TCON,
RELAX, CPS, FTRE) beyond what the LTMS needs; raw SAT-solver performance
(delegate that to PySAT); preserving Lisp macro/codegen machinery (we use
closures, not `eval`).

**Why this is worth doing.** Research confirms there is **no faithful Python
LTMS** in existence. JTMS/ATMS have toy Python ports; the LTMS (clausal BCP +
DDB) is the least-ported TMS outside Lisp/Racket. The closest external
reference is `namin/biohacker` (Racket `ltms.rkt`/`cltms.rkt`); the QRG Lisp is
ground truth. This is genuinely new work. (See [STUDY-NOTES.md](STUDY-NOTES.md) §Research.)

---

## 2. Target architecture

Source layout (`src/` package, `pytest` tests, `pyproject.toml`):

```
src/ltms/
  terms.py        # Symbol, Var, term predicates (is_variable, is_compound), pretty-print
  unify.py        # unify, unify_variable, occurs_check, substitute(walk*), FAIL sentinel
  tre/
    engine.py     # Tre, Dbclass, Rule, get_dbclass (car-indexing), assert!, fetch, run_rules
  tms/
    substrate.py  # shared: Datum<->Node bridge, dbclass index, enqueue hook, contradiction-handler stack
    jtms.py       # (optional) Node(IN/OUT), Justification, two-phase relabel  ── stepping stone
    jtre.py       # (optional) JTMS rule-engine binding
  ltms/
    core.py       # Ltms, TmsNode, Clause, BCP (pvs/sats counters), set_truth, add_clause
    normalize.py  # propositional formula -> CNF (normalize/disjoin/simplify-clause)
    retract.py    # propagate_unknownness, find_alternative_support
    contra.py     # deferred contradiction dispatch, handler stack, add_nogood
    explain.py    # support_for_node, assumptions_of_node/clause, why_node, explain_node
    ltre.py       # Ltre, Datum, build_tms_formula, assert!/assume!/retract!, rules, queries
    indirect.py   # try_indirect_proof
    cwa.py        # close_set, with_closed_set, set-rule machinery
    dds.py        # DD-Search (depth-first dependency-directed search)
    cltms.py      # (optional) completeness: trie, consensus, IPIA, complete mode, tms-env
tests/            # ported *-ex conformance + property-based + differential (PySAT) tests
examples/         # runnable demos (family relations, N-queens, etc.)
```

**Layering (each layer depends only on the ones above it):**

```
terms + unify  →  TRE  →  [JTMS/JTRE optional]  →  LTMS core (BCP)  →  LTRE  →  indirect / CWA / DDS  →  [CLTMS optional]
                                     └──────── shared TMS substrate (Datum↔Node, dbclass, enqueue, contradiction stack) ───────┘
```

**Key design decisions (decided up front — see STUDY-NOTES for rationale):**
- **Terms** = Python tuples; **atoms** = interned `Symbol` (or `str`); **variables** = a `Var` class (do *not* use the Lisp `?name` symbol hack). Numbers = `int`/`float`.
- **Bindings** = dict `{Var: term}`; **failure** = a dedicated `FAIL = object()` sentinel (the empty dict is a *valid success*, so never test bindings by truthiness).
- **Rule bodies are Python callables** `body(bindings, engine)` — never generated/`eval`'d Lisp. Nested rules = the body calls `engine.add_rule(...)`, capturing bindings via closure.
- **No node for negation.** A fact is stored unsigned; `(:NOT P)` is read by inverting `P`'s label. One `Datum`/`TmsNode` per ground proposition.
- **`support` is tri-valued:** `None` (unknown/out) | the `ENABLED_ASSUMPTION` sentinel | the forcing `Clause`. Compare the sentinel with `is`.
- **Engine is instance state**, not a global. Replace the Lisp `*LTRE*` special with explicit engine arguments (optionally a `contextvars` "current engine" for sugar).
- **Watched-literals** (the SAT-solver data structure) is the eventual hot-path representation for BCP; start with the book's `pvs`/`sats` counters (simpler, faithful) and migrate in the hardening session.

---

## 3. The five correctness invariants (must hold in every session that touches them)

These are the traps that silently corrupt a TMS. Each appears as an explicit
test and a code comment where relevant.

1. **FAIL ≠ empty-success.** `unify` returns `FAIL` on failure and `{}` on
   "unified, no new bindings." Callers test `is not FAIL`.
2. **`pvs` counter discipline.** `pvs = (#literals UNKNOWN) + (#literals
   currently satisfying)`. Violated ⇔ `pvs == 0`; unit/forcing ⇔ `pvs == 1`;
   satisfied ⇔ `sats > 0`. Maintain incrementally in `set_truth`; never rescan
   literals on the hot path; never delete satisfied clauses (retraction needs
   live counters).
3. **Deferred contradiction dispatch.** BCP must *not* raise on the first
   violated clause — it records it and keeps propagating. Handlers run once, at
   the end of the top-level operation. Raising mid-BCP corrupts half-updated
   counters.
4. **Two-phase retraction.** First label the node *and all it transitively
   forced* `UNKNOWN` (phase 1), *then* search for alternative support (phase 2).
   Interleaving reintroduces ill-founded circular support.
5. **Composable contradiction-handler stack.** A handler returns truthy iff it
   resolved the contradiction; the dispatcher tries handlers top-down until one
   does. `indirect`/`cwa`/`dds` all rely on this exact contract and on
   exception-safe `assuming`/`with_assumptions` (try/finally).

---

## 4. Sessions

Each session ends **green**: typechecks, lint clean, tests pass, with the
listed book example(s) ported and matching expected behavior. "Effort" is a
rough sizing, not a deadline.

### Session 0 — Scaffold + terms + unification  *(foundation; ~1 session)*
**Goal.** A buildable, tested package skeleton and the term/unification layer everything shares.
**Deliverables.**
- `pyproject.toml` (src layout, deps: `pytest`, `hypothesis`, `ruff`, `mypy`), `README.md`, `LICENSE`, `NOTICE` (carry the BPS Forbus/de Kleer/Xerox copyright notice — the port is a permitted derivative work).
- GitHub Actions CI: lint + typecheck + test on push/PR (gates everything after).
- `terms.py`, `unify.py`.
**Tasks.**
- Implement `Var`, `Symbol`, `is_variable`, `is_compound`; choose tuple representation; a reader for `?x`-style strings → `Var` (test convenience only).
- Port `unify` / `unify_variable` / `free_in` (occurs-check) faithfully (5-clause `cond`); `substitute`/`resolve` (recursive, chases chains — stronger than Lisp one-pass `sublis`). `FAIL` sentinel.
**Acceptance tests.** Classic unify cases; occurs-check rejects `?x = (F ?x)`; repeated-variable consistency `(p ?x ?x)` vs `(p a b)` fails / `(p a a)` succeeds; `{}`-success ≠ `FAIL`; substitution resolves chained bindings. (Invariant #1.)
**Risks.** Numeric equality policy (`1 == 1.0`?) — decide once, apply in both `unify` and matchers. Don't standardize variables apart (TRE relies on disjoint var sets / seed environments).

### Session 1 — TRE: pattern-directed inference (no TMS)  *(first runnable demo; ~1 session)*
**Goal.** A working forward-chainer: assert facts + define rules → derive facts. This is the conceptual core all TMS layers sit on; build it cleanly once.
**Deliverables.** `tre/engine.py`: `Tre`, `Dbclass`, `Rule`, `get_dbclass` (car-indexing, leftmost-constant key), `insert`/`assert_`, `fetch`, rule registration (body = callable), LIFO queue, `run_rules`, `run_forms` driver.
**Tasks.**
- `try_rule_on` as the single match chokepoint (used by both "fact arrived" and "rule arrived" paths — bidirectional incremental join).
- Nested rules via closures capturing current bindings (replaces Lisp `*ENV*` + eval'd `let`).
- Thread the active binding environment explicitly into `get_dbclass` (replaces Lisp `boundp`/`*ENV*` dual lookup).
**Acceptance tests.** Port `tre/treex1` (the book's TRE example). Assertion order vs rule-definition order independence. (Note: the `(integer ?x)→(integer (1+ ?x))` example diverges by design — bound it in tests; don't add loop detection.)
**Risks.** The two-binding-notion `get_dbclass`; remembering `assert!` only *enqueues* — `run_rules` drains.

### Session 2 — JTMS + JTRE  *(optional but recommended stepping stone; ~1 session)*
**Goal.** Build the *simplest* TMS first to establish the node/justification/contradiction/explanation patterns and especially the **two-phase retraction** discipline — on a system where it's easy to get right — before the harder LTMS. Also the canonical contrast (`IN/OUT` vs `TRUE/FALSE/UNKNOWN`).
**Deliverables.** `tms/substrate.py` (reusable `Datum`↔`Node` bridge, dbclass index, enqueue hook, contradiction-handler stack, `with_contradiction_*` context managers); `tms/jtms.py`; `tms/jtre.py`.
**Tasks.** `Node(IN/OUT)`, `Justification`; `justify_node` (incl. premise special case); `enable_assumption` (3-way); `retract_assumption` = `propagate_outness` (phase 1, identity `is` test on support) → `find_alternative_support` (phase 2); `assumptions_of_node`; `why_node`; contradiction callback.
**Acceptance tests.** Port `jtms/jtms-ex`. Verify the circular-support case stays well-founded; `assumptions_of_node` backtrace. (Invariants #4, #5.)
**Decision point.** A team focused purely on the LTMS *may skip this session* and build the substrate inside Session 3 instead. Recommended to keep it: it de-risks the LTMS and the substrate is reused verbatim.

### Session 3 — LTMS core, part 1: clauses + forward BCP  *(~1–2 sessions)*
**Goal.** The Boolean Constraint Propagation engine for *assertions only* (no retraction yet). End-of-session demo: install clauses → watch unit propagation force `TRUE/FALSE` labels → detect a violated clause.
**Deliverables.** `ltms/core.py`: `Ltms`, `TmsNode`, `Clause`, interned literals, `add_clause`/`bcp_add_clause` (counter init), `set_truth` (label + incremental `pvs`/`sats` + queue + enqueue hook), `check_clauses`/`check_clause`/`find_unknown_pair`, `satisfied?`/`violated?`, `top_set_truth`.
**Tasks.** Get the counter deltas in `set_truth` to *exactly* mirror `bcp_add_clause` init. `clauses-to-check` work list (LIFO is fine). **Defer** contradictions (record to `violated_clauses`, never raise).
**Acceptance tests.** Unit-propagation forcing; violated-clause detection (recorded, not raised); the BCP-incompleteness cases (`{x∨¬y, x∨y}` leaves `x` UNKNOWN — *expected*). (Invariants #2, #3.)
**Risks.** `pvs` counts UNKNOWN **+** satisfying literals (not just unknowns); satisfied clauses are *kept*; `find_unknown_pair` must re-guard that the literal is still UNKNOWN.

### Session 4 — LTMS core, part 2: assumptions, retraction, contradictions, formulas, explanation  *(~1–2 sessions)*
**Goal.** A complete standalone LTMS: retractable assumptions, contradiction handling, formula input, and explanations.
**Deliverables.** `ltms/retract.py` (`propagate_unknownness` + `clause_consequent` + `find_alternative_support`), `ltms/contra.py` (`check_for_contradictions`, handler stack, `add_nogood`, `avoid_all`), `ltms/normalize.py` (`add_formula`, `normalize`/`normalize_1` with `negate` flag, `disjoin`, `simplify_clause`/`sort_clause`, `:TAXONOMY`), `ltms/explain.py` (`support_for_node`, `assumptions_of_node`/`_of_clause` via a per-call `visited` set, `why_node`, `explain_node`).
**Tasks.** `enable_assumption`/`retract_assumption`/`convert_to_assumption`; strict two-phase retraction; CNF edge cases (`(:OR)`=FALSE=`[[]]`, `(:AND)`=TRUE=`[]`, tautology drop); nogood order (retract culprit *before* adding nogood).
**Acceptance tests.** Port the propositional parts of `ltms/ltms-ex`; retraction restores prior labels; contradiction → `avoid_all` installs a nogood and recovers; `explain_node` prints a well-founded proof. (Invariants #2–#5.)
**Risks.** `support` tri-value handling everywhere; `assumptions_of_clause` under inconsistency; deferred-dispatch + handler-stack composition.

### Session 5 — LTRE: the reasoning engine on the LTMS  *(~1–2 sessions)*
**Goal.** Wire the pattern-directed engine to the LTMS — the headline deliverable: assert formulas + rules, propagate belief, query, explain.
**Deliverables.** `ltms/ltre.py`: `Ltre`, `Datum`, `referent`/`insert`, `get_dbclass`, `build_tms_formula` (direct translation, nodes at leaves), `assert!`/`assume!`/`retract!` (note the asymmetry: `assume!` adds a guard node + `:IMPLIES`), `fetch`, `true?`/`false?`/`known?`/`unknown?` (sign-inverting), the rule system (`:INTERN`/`:TRUE`/`:FALSE` triggers, `:VAR`/`:TEST` options, parked rules on `node.true_rules`/`false_rules`), the **LTMS→LTRE enqueue bridge**, `run_rules`, `contradiction`, `assuming`.
**Tasks.** Install the enqueue procedure in `create_ltre` so `set_truth` wakes belief-conditioned rules. Multi-trigger rules via nested `add_rule` closures (cartesian-product join). `rassert!` sugar = build the tuple with bound values (no `quotize`).
**Acceptance tests.** Port the rule examples in `ltms/ltms-ex`; `:INTERN` fires on existence, `:TRUE` waits for belief; assume → derive → retract → un-derive. (Invariant #1, #5.)
**Risks.** Strip/invert `:NOT` consistently; `assert!`-vs-`assume!` node asymmetry; rules enqueue (not run) until `run_rules`.

### Session 6 — Advanced facilities: indirect proof, CWA, DD-search  *(~1–2 sessions)*
**Goal.** The three composable facilities that exercise the contradiction-handler stack.
**Deliverables.** `ltms/indirect.py` (`try_indirect_proof`), `ltms/cwa.py` (`close_set`, `with_closed_set`, set-rule machinery: CWA-justification translation, NOT-IN-SET, CONSTRUAL-UNIQUENESS, `form<` via datum counter), `ltms/dds.py` (`DD_Search`, `signed_view_node`).
**Tasks.** Port Lisp `catch`/`throw` markers → custom exceptions carrying a marker identity + `:LOSERS` payload, caught at the matching level. In DDS, **capture assumption labels before any retraction** (else wrong nogoods). Exception-safe `assuming`/`with_assumptions` (try/finally) and `with_closed_set` unwind.
**Acceptance tests.** Port `indirect.lisp`'s indirect-proof example; `cwa` `cwa-shakedown`/`laccept`; `dds` `test-dd-search`; then **N-queens via DDS** as the integration showcase.
**Risks.** CWA defensive ordering (retract old → assume new → justify); the known lingering-CWA edge (book Exercise 5) — document it; DDS mutual-exclusion `true?` short-circuit.

### Session 7 — Hardening, performance, packaging, release  *(~1 session)*
**Goal.** Make it fast enough, trustworthy, and publishable.
**Deliverables.** Watched-literals BCP (borrowed from SAT solvers) behind the same `Clause` API; property-based tests (Hypothesis) for the invariants; **differential testing vs PySAT** as an oracle (random clause sets: LTMS-derived units / detected contradictions must be SAT-consistent); benchmarks; `examples/` gallery; docs; PyPI release.
**Tasks.** Profile BCP; migrate counters→watched literals where it pays. Reserve an unambiguous package name (**not `pytms`** — taken by an unrelated transport simulator). Cross-check selected examples against `biohacker/ltms.rkt` output.
**Acceptance tests.** Hypothesis invariants hold over random inputs; PySAT differential agreement on satisfiable/unsatisfiable random CNFs (modulo BCP incompleteness — only assert what BCP *should* find); perf budget met.
**Risks.** Watched-literals + retraction interaction (retraction needs to restore watches correctly) — keep the counter implementation as a reference oracle in tests.

### Session 8 — (Optional) CLTMS: logical completeness  *(~2 sessions; advanced)*
**Goal.** Make BCP logically complete via prime implicates, behind a `complete` mode flag (`None` / `True` / `DELAY`).
**Deliverables.** `ltms/cltms.py`: trie/discrimination-tree subsumption DB (port first, in isolation), `consensus` (pure function returning a fresh sorted literal list — **drop** the Lisp reused-cons hack), IPIA (incremental Tison), CNF-with-subsumption `add_formula`, lazy `delay_sat` + retraction-driven re-completion, and `tms_env` (CMS/ATMS label read-off).
**Acceptance tests.** Port `cltms` examples; the BCP-incomplete cases now resolve (`{x∨¬y, x∨y}` forces `x`; the 4-clause non-Horn set detects unsat); subsumption correctness.
**Risks.** Exponential prime-implicate blowup — default to `DELAY`, guard/warn on eager mode; consensus tautology detection (second complementary pair → fail); requeue `DIRTY` clauses on retraction or the LTMS is silently incomplete after retractions.
**Recommendation.** Treat as genuinely optional. The book itself notes completeness "comes at significant computational cost"; most inference engines tolerate BCP incompleteness.

---

## 5. Cross-cutting concerns

**Testing strategy (build the harness in Session 0, grow it every session).**
- **Golden/conformance:** port each `*-ex` file as the acceptance test for its layer (`treex1`, `jtms-ex`, `ltms-ex`, `laccept`, `cwa-shakedown`, `test-dd-search`, indirect-proof, queens). These pin exact behavior.
- **Property-based (Hypothesis):** the five invariants (§3); well-founded support is acyclic; retraction is the inverse of assertion for counter state; soundness (no `TRUE` and `FALSE` on one node without a recorded contradiction).
- **Differential (oracle):** PySAT (MIT; bundles CaDiCaL/Glucose/MiniSat; `solve(assumptions=...)`, `get_core()`) as a satisfiability oracle for random CNFs — assert only what BCP is guaranteed to find (unit consequences, refutations within unit resolution).
- **External cross-check:** `biohacker/ltms.rkt` (Racket) for selected example outputs; QRG Lisp as ground truth (no local Lisp runtime — read code / use `death/bps` if a runtime is set up).

**Performance.** Counters first (faithful, debuggable) → watched literals (Session 7). Delegate hard satisfiability/optimization to PySAT rather than writing a fast CDCL in Python. Borrow from the modern-systems survey: persist learned nogoods (CDCL idea), signed-delta retraction (differential-dataflow idea), proof-tree/semiring framing for the `explain` API.

**Licensing & provenance.** The BPS *code* license permits derivative works with the copyright notice retained → ship a `NOTICE` with the Forbus/de Kleer/Xerox notice; choose our own OSI license for original code. The BPS *book text* is MIT Press copyright → keep `refs/book/` gitignored, never vendor it. Do not depend on or shadow the PyPI name `pytms`.

**Definition of done (project).** Core sessions 0–6 complete; conformance suite
green; `examples/` runnable (family relations, assume/retract, N-queens);
docs + README; published to PyPI under a reserved name. CLTMS (8) and a JTMS
(2) are optional extensions.

---

## 6. Suggested ordering & dependencies

```
0 ──▶ 1 ──▶ 3 ──▶ 4 ──▶ 5 ──▶ 6 ──▶ 7
            ▲
      2 ────┘ (optional; builds substrate + two-phase retraction early)
                                          8 (optional; after 4, ideally after 7)
```

Critical path to "LTMS + reasoning engine working end-to-end": **0 → 1 → 3 → 4 → 5**.
Sessions 2 (JTMS), 7 (hardening), and 8 (CLTMS) are value-adds around that spine.

---

## 7. References

- Forbus & de Kleer, *Building Problem Solvers*, MIT Press 1993 — chapters 4 (PDIS/TRE), 6 (TMS intro), 7 (JTMS), 9 (LTMS), 10 (LTRE), 13 (CLTMS). Official site: `qrg.northwestern.edu/BPS/readme.html`.
- McAllester, "An Outlook on Truth Maintenance" (MIT AI Memo 551, 1980) and "Truth Maintenance" (AAAI-90, pp. 1109–1116) — the LTMS = clause DB closed under unit resolution.
- Doyle, "A Truth Maintenance System", *Artificial Intelligence* 12(3):231–272, 1979 — the JTMS ancestor.
- de Kleer, ATMS trilogy, *Artificial Intelligence* 28(2), 1986 — the sibling alternative.
- External ports: `namin/biohacker` (Racket LTMS, primary check), `jphmrst/bps` (Haskell/Scala JTMS+ATMS, *structure only* — restrictive license), `death/bps` (clean Lisp mirror).
- Tooling/adjacent: PySAT (`pysathq/pysat`); clingo/Potassco (ASP); Souffle/semiring provenance (explanation model); differential dataflow (incremental retraction).

Full annotated details, per-module data structures, algorithms, gotchas, and the
Lisp→Python idiom table are in [STUDY-NOTES.md](STUDY-NOTES.md).
