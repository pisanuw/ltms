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
