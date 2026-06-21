# Changes

Format: `YYYY-MM-DD [type] description` (max 200 chars). Types: decision, plan, doc, scope, code, note.

2026-06-20 [note] Initialized.

2026-06-20 [scope] Project: build Python LTMS + logic-based reasoning engine, based on Forbus & de Kleer BPS (../BPS code + book PDF).
2026-06-20 [note] Staged reference material in refs/ (gitignored): bps-lisp/ (ltms,jtms,tre,utils source) + book/ (full OCR text + chapters 4,6,7,8,9,10,13).
2026-06-20 [code] Initialized git repo on main; added remote origin -> github.com/pisanuw/ltms.git (public, empty). No commit/push yet. refs/ gitignored (copyright).
2026-06-20 [plan] Launched study+research+plan workflow (wf_779b0890-9e1) to map BPS internals and draft multi-session PLAN.md.

2026-06-20 [doc] Wrote PLAN.md (8-session plan: scaffold/terms/unify, TRE, optional JTMS, LTMS core x2, LTRE, advanced facilities, hardening, optional CLTMS) + STUDY-NOTES.md (technical digest).
2026-06-20 [note] Workflow wf_779b0890-9e1 done: 6 studies + 4 verified research topics succeeded; 2 plan-proposal agents failed on transient socket errors (plan authored by main loop instead). Raw output in refs/workflow-output.md (gitignored).
2026-06-20 [decision] Critical-path to working LTMS+engine = sessions 0->1->3->4->5; JTMS(2), hardening(7), CLTMS(8) are value-adds. Core invariants documented (FAIL!=empty, pvs discipline, deferred contradictions, two-phase retraction, handler stack).

2026-06-20 [code] Session 0 done: project scaffold (pyproject hatchling, MIT LICENSE, NOTICE w/ BPS attribution, README, GitHub Actions CI), src/ltms terms.py + unify.py (occurs-check, FAIL sentinel, substitute), 24 tests + Hypothesis props; ruff+mypy(strict) clean.

2026-06-20 [code] Session 1 done: TRE pattern-directed forward-chainer (src/ltms/tre): car-indexed dbclass, assert_/fetch, rule bodies as Python callables, nested (conjunctive) rules via closures, LIFO run_rules. 10 tests (transitive closure, order-independence, bounded recursion, dedup). ruff ignores UP005.

2026-06-20 [code] Session 2 done: JTMS core (ltms/jtms.py: Node IN/OUT, Justification, justify_node, enable/retract with strict two-phase relabel, assumptions_of_node, contradiction handler) + JTRE (ltms/jtre.py: Datum<->Node bridge, dbclass index, INTERN/IN/OUT rules parked + enqueue bridge). 17 tests incl. DDB + circular-support guard.

2026-06-20 [code] Session 3 done: LTMS BCP core (ltms/core.py: Label TRUE/FALSE/UNKNOWN, TmsNode, Clause w/ pvs+sats counters, add_clause, set_truth, forward unit propagation, simplify/tautology/dup, deferred contradiction detect + handler stack). 10 tests incl. BCP-incompleteness case, well-founded support, deferred dispatch.

2026-06-20 [code] Session 4 done: LTMS assumptions+retraction (enable/retract, two-phase propagate_unknownness + alt-support, clause_consequent), contradiction resolution (with_contradiction_handler stack, add_nogood, avoid_all), CNF normalize.py (and/or/not/implies/iff/taxonomy, add_formula), explain.py (why_node/explain_node/assumptions_of_node). 17 tests; ruff+mypy clean (88 total).

2026-06-20 [code] Session 5 done: LTRE reasoning engine (ltms/ltre.py): Datum<->Node bridge, build_tms_formula (direct translation), assert!/assume!/retract! (incl. guarded compound assumptions), INTERN/TRUE/FALSE rules parked + enqueue bridge, queries with negation inversion, contradiction(). 13 tests; 91 total green.

2026-06-20 [code] Session 6 done: advanced LTRE facilities. indirect.py (try_indirect_proof: assume negation, nogood on refutation), cwa.py (close_predicate/closed_world negation-as-failure), dds.py (dd_search: DFS over choice sets w/ nogood-learning backjump). LTMS.with_assumptions context mgr. 7 tests (proof-by-cases, CWA withdraw, 3-coloring solvable / 2-coloring unsat). 98 total.

2026-06-20 [code] Session 7 done: hardening. Public API in __init__ + py.typed; examples/ (family_tre, belief_revision_ltre, coloring_dds) + smoke tests; Hypothesis property tests (counter/support invariants); PySAT differential test (BCP soundness vs Minisat22) which surfaced + documented the 4-clause refutation-incompleteness case. Version 0.1.0; wheel builds. Watched-literals deferred (counters are BPS-faithful).

2026-06-20 [code] Session 8 done (optional): CLTMS completeness (ltms/cltms.py): consensus (resolution), subsumption, prime_implicates (brute-force saturation; IPIA noted as future work), complete() adds missing prime implicates so BCP becomes logically complete. 7 tests (literal-completeness {x v ~y, x v y}->x, 4-clause UNSAT detection). 112 total green.
2026-06-20 [note] All planned sessions (0-8) complete: 15 src modules, 16 test files (112 tests), 3 examples; ruff+mypy(strict) clean; wheel builds; pushed to github.com/pisanuw/ltms main.
