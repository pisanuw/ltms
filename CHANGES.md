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

2026-06-21 [code] Added file DSL (ltms/dsl.py): lisp-like .kb format for world models, separate from Python. Statements: assert (bare), assume/retract, contradiction, rule (=> with & antecedents), query, expect (self-checking). parse_expr/load_kb/load_kb_file. examples/kb/belief_revision.kb + run_kb.py runner. 14 tests.

2026-06-21 [code] Added watched-literals engine (ltms/watched.py): WatchedLTMS, 2-watched-literals BCP (no per-clause counters), support-pointer two-phase retraction. Validated by differential tests: identical forced labels + contradictions vs counter LTMS over random CNF+assumptions (300 ex), and sound vs PySAT Minisat22 (200 ex). Reference LTMS stays default; rule engine/CWA/DDS run on it.

2026-06-21 [doc] Started exercises/ (per-chapter book exercise solutions, paraphrased + original). ch09 (LTMS) and ch10 (LTRE) hand-written with runnable solutions.py: clause-count blow-up, taxonomy CNF size, BCP completeness via complete(); XOR, one-step abduction (NEEDS), and N-queens via dd_search (counts 4->2,5->10,6->4). tests/test_exercises.py runs every solutions.py.

2026-06-21 [doc] exercises/ch16 (Assumption-Based Constraint Languages): analysis-only README (no code; ATCON/TCON not in package). Ex1 atcon-delay t/nil tradeoff (savings vs check overhead, cheap-deterministic vs expensive-feedback); Ex2 explicit nogood DB exponential->poly via small-core/large-tail.

2026-06-21 [doc] Wrote exercises/ch14/README.md: analysis-only answers for all 16 ch14 (Putting the ATMS to Work) exercises; ATMS/ATRE out of scope so no code, design/complexity sketches only.

2026-06-21 [doc] exercises/ch17 (TGDE / A Tiny Diagnosis Engine) analysis-only README: all 10 exercises paraphrased + answered (lattice size 2^n, min-card => min, single-valued predictions, direct min-hitting-set diagnosis, prob-threshold smallest-diagnoses, hierarchical OK assumptions, horizon effect, prob misdiagnosis, CLTMS complete diagnoser on polybox, best-input active diagnosis). No code; out of scope.

2026-06-21 [doc] Completed exercises/ for ALL 16 chapters (3-18): paraphrased problem statements + original answers. Code chapters (4,6,7,8,9,10,13) ship runnable solutions.py (verified, run in CI via test_exercises.py); analysis chapters (3,5,11,12,14,15,16,17,18) give conceptual answers (systems out of scope). exercises/README.md index. Drafted via background workflow (wf_804932f3-27e, 14 agents); ch9/ch10/ch18 + index hand-finished. Added examples/kb/{modus_tollens,diagnosis,family}.kb. README updated (DSL, WatchedLTMS, exercises).

2026-06-21 [code] Extended DSL with `taxonomy` (exactly-one) and `complete` (prime-implicate completion) directives. Moved world models into .kb data files: examples/kb/{taxonomy,completeness}.kb and per-chapter exercises/chNN/kb/*.kb (ch4 ancestor, ch6 lamp, ch9 incompleteness/completeness/taxonomy/disjunction, ch10 belief_revision/modus_chain/xor, ch13 proof_by_cases). belief_revision_ltre.py is now a thin .kb loader (no theory in Python). test_kb_files runs all 16 .kb files (self-checking via expect).

2026-06-21 [doc] Scrubbed absolute local paths from tracked files: workflow-generated exercise READMEs/solutions referenced an absolute working directory; replaced with repo-relative paths ("# from the repository root"). 0 occurrences remain in tracked files.

2026-06-21 [doc] Added companion/ — a chapter-by-chapter study companion to the book (index + ch03-ch18). Concepts, worked-example explanations, and exercise-solution walk-throughs, all in our own words (no book text), with runnable "Try it" commands and repo-relative links. Index + flagship ch9/ch10 hand-written; ch3-8,11-18 drafted via background workflow (wf_3363593e-69b, 14 agents) then verified (links resolve, cited commands run, no absolute paths). README links to it.

2026-06-21 [plan] Next task (requested, interrupted before any work): create GitHub Pages under ./docs explaining the project and including the companion (companion/).

2026-06-21 [doc] Built GitHub Pages site under ./docs (just-the-docs via remote_theme). Moved companion/ -> docs/companion/ (git mv, single source) + added per-page front matter; rewrote 180 out-of-docs links (../src,../exercises,../examples,PLAN/STUDY-NOTES/BRIEFING) to absolute github blob/tree URLs. New pages: index, getting-started, architecture, exercises, examples + _config.yml/Gemfile/.gitignore. Updated README/BRIEFING companion paths. Needs one-time repo setting: Pages -> Deploy from branch -> main -> /docs.

2026-06-21 [code] Committed the docs/ Pages site to main (be78819) and pushed to origin. Code side complete; only the one-time repo Pages setting (Deploy from branch -> main -> /docs) remains, which requires user action in GitHub Settings.

2026-06-21 [note] Ran /code-improve whole-repo sweep (report-only): 4 reviewers + 2 simplifiers + audits. Found 1 real bug, CI build gap, simplification proposals. Report in CODE-IMPROVE-REPORT.md (untracked).

2026-06-21 [code] Fixed dsl.tokenize infinite-loop on stray '<','-','=' (now raises ValueError) + regression test; added CI build job (python -m build, verified wheel+sdist) + build>=1.0 to dev deps. mypy clean, dsl tests pass.

2026-06-21 [note] Set GitHub repo description + 14 topics via gh; user enabled Pages (Deploy from branch -> main -> /docs). Presentation/setup complete.

2026-06-21 [code] Applied 6 code-improve simplifications (core set_truth collapse, jtms _fire_rules, explain _antecedents, watched unit-watch, ltre retract dedup, dsl expr_text); unify is-FAIL skipped (breaks mypy narrowing). 161 tests pass, mypy clean.

2026-06-21 [code] Committed above as 8ea0dfe (local, not pushed). Deleted untracked CODE-IMPROVE-REPORT.md.

2026-06-21 [code] Published ltms 0.1.0 to PyPI (pypi.org/project/ltms/0.1.0): wheel+sdist via twine, twine check passed, verified pip-installable from a clean venv. TestPyPI dry-run skipped (separate-account auth). Pending: push main + tag v0.1.0.

2026-06-21 [code] Finalized 0.1.0 release: added PyPI/Python/license badges to README, committed (eaafb56), pushed main to GitHub, tagged + pushed v0.1.0. Repo now matches PyPI. (0.1.0 is immutable on PyPI; next fix needs 0.1.1.)

2026-06-24 [code] audit-ci-gates: CI installed only .[dev], so pysat absent -> importorskip silently skipped ALL of test_watched.py (7 watched-engine tests) + the BCP-vs-Minisat22 differential test on every run (confirmed: "0 collected / 2 skipped"). Fixed CI to install .[dev,sat] (python-sat ships cp310-cp313 linux wheels = full matrix), added pip cache + cache-dependency-path, pytest -ra to surface skips, and a CI status badge to README. Verified: deliberate break in a watched test -> red with sat / silently skipped without. 161 tests, YAML valid. Committed on branch ci/run-sat-tests (65eaaff); CI ran green on the runners (python-sat-1.9.dev5 installs cp310-cp313, "161 passed" 0 skipped); merged to main.
