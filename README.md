# ltms

A logic-based **Truth Maintenance System (LTMS)** and a **pattern-directed
reasoning engine** in pure Python, after Forbus & de Kleer, *Building Problem
Solvers* (MIT Press, 1993).

The LTMS maintains belief over a set of propositional clauses using **Boolean
Constraint Propagation** (unit propagation), records **well-founded support** for
every derived value, performs **dependency-directed backtracking** on
contradictions, and can **explain** why anything is believed. A small
forward-chaining rule engine sits on top of it.

> See [PLAN.md](PLAN.md) for the multi-session build plan and
> [STUDY-NOTES.md](STUDY-NOTES.md) for the technical digest.

## Why

There is no faithful Python LTMS in the wild — JTMS/ATMS have a few toy ports,
but the clausal-BCP LTMS with dependency-directed backtracking is the
least-ported truth maintenance system outside Lisp/Racket. This is a clean,
tested, idiomatic-Python implementation.

## What's here

| Layer | Module | What it gives you |
|---|---|---|
| Terms + unification | `ltms.terms`, `ltms.unify` | s-expression terms, occurs-checked unification |
| TRE | `ltms.tre` | pattern-directed forward chaining (no belief revision) |
| JTMS + JTRE | `ltms.jtms`, `ltms.jtre` | justification-based belief, IN/OUT, two-phase retraction |
| LTMS core | `ltms.core`, `ltms.normalize` | clausal Boolean Constraint Propagation, assumptions, nogoods, CNF |
| LTRE | `ltms.ltre` | reasoning engine: `assert!`/`assume!`/`retract!`, belief-conditioned rules |
| Facilities | `ltms.indirect`, `ltms.cwa`, `ltms.dds` | indirect proof, closed-world assumptions, dependency-directed search |
| Completeness | `ltms.cltms` | prime implicates / `complete()` (optional logical completeness) |
| Watched literals | `ltms.watched` | `WatchedLTMS`, the SAT-style 2-watched-literals BCP engine |
| Explanation | `ltms.explain` | `why_node`, `explain_node` (well-founded proofs) |
| File DSL | `ltms.dsl` | read world models from `.kb` files, separate from Python |

## Usage

```python
from ltms import LTRE

e = LTRE()
e.assert_(("or", ("p",), ("q",)))   # p v q
e.assert_(("not", ("p",)))          # ~p
e.is_true(("q",))                   # True  (unit propagation)

e.assume(("rain",), "guess")        # retractable assumption
e.assert_(("implies", ("rain",), ("wet",)))
e.is_true(("wet",))                 # True
e.retract(("rain",), "guess")
e.is_unknown(("wet",))              # True  (belief revised)
```

### World models in files

The world model can live in a `.kb` data file, separate from Python:

```
# examples/kb/belief_revision.kb
rain         -> wet ground
sprinkler on -> wet ground
assume rain
expect wet ground true
```

```python
from ltms.dsl import load_kb_file
load_kb_file("examples/kb/belief_revision.kb")   # runs it; `expect` lines self-check
```

See [examples/](examples/) for runnable TRE, LTRE, and dependency-directed-search
demos, and [exercises/](exercises/) for worked solutions to the book's
chapter exercises (paraphrased statements + original answers/code).

## Install (development)

```bash
python -m venv .venv && . .venv/bin/activate
pip install -e ".[dev]"      # add ".[dev,sat]" for the PySAT differential tests
pytest
```

## Notes

BCP uses the book's incremental `pvs`/`sats` counters (sound but, by design,
not logically complete). A watched-literals rewrite and the completeness
extension (CLTMS, prime implicates) are tracked as future work in
[PLAN.md](PLAN.md).

## Provenance & licensing

Original code in this repository is MIT licensed (see [LICENSE](LICENSE)).

This is an independent reimplementation of the algorithms in *Building Problem
Solvers*; it does not copy the original Common Lisp source. The book and its
reference code are available from the Northwestern Qualitative Reasoning Group at
<https://www.qrg.northwestern.edu/BPS/readme.html>, where the full-text PDF is
offered for free download *"thanks to the gracious permission of MIT Press"*
(MIT Press retains print rights). The book PDF and other reference material are
kept local and are **not** redistributed here. See [NOTICE](NOTICE) for full
attribution.
