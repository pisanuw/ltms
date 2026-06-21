# Briefing

- Purpose: Build a logic-based Truth Maintenance System (LTMS) and a logic-based reasoning engine in Python, based on Forbus & de Kleer, "Building Problem Solvers" (BPS).
- Current scope: Planning complete. Studied the BPS reference code and book, surveyed comparable systems, and produced PLAN.md (multi-session implementation plan) + STUDY-NOTES.md (technical digest). Next: execute Session 0 (scaffold + terms + unification).
- Key decisions: Target language is Python 3, src layout. Reference = BPS Common Lisp (copied into refs/, gitignored). Terms=tuples, Var class, dict bindings, FAIL sentinel, rule bodies as Python callables (no eval). Engine = instance, not global. BPS code license permits a derivative port if the copyright NOTICE is retained; book text stays gitignored (MIT Press copyright). git remote origin -> github.com/pisanuw/ltms (public).
- Non-goals: Porting the rest of the BPS suite (ATMS, GDE, TGIZMO/QP, TCON, RELAX, CPS, FTRE) beyond what the LTMS needs; raw SAT performance (delegate to PySAT); preserving Lisp macro/codegen. JTMS and CLTMS are optional, not core.
