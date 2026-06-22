---
title: Home
nav_order: 1
---

# LTMS — a Truth Maintenance System in Python

A logic-based **Truth Maintenance System (LTMS)** and a **pattern-directed
reasoning engine**, written in pure Python after Forbus & de Kleer's
*Building Problem Solvers* (MIT Press, 1993).

The LTMS maintains belief over a set of propositional clauses using **Boolean
Constraint Propagation** (unit propagation), records **well-founded support** for
every value it derives, performs **dependency-directed backtracking** when it hits
a contradiction, and can **explain** why anything is believed. A small
forward-chaining rule engine sits on top of it.

[Get started](getting-started.md){: .btn .btn-primary }
[Study Companion](companion/README.md){: .btn }
[Architecture](architecture.md){: .btn }
[View on GitHub](https://github.com/pisanuw/ltms){: .btn }

---

## The 30-second version

```python
from ltms import LTRE

e = LTRE()
e.assert_(("or", ("p",), ("q",)))   # p v q
e.assert_(("not", ("p",)))          # ~p
e.is_true(("q",))                   # True  — forced by unit propagation

e.assume(("rain",), "guess")        # a retractable assumption
e.assert_(("implies", ("rain",), ("wet",)))
e.is_true(("wet",))                 # True
e.retract(("rain",), "guess")
e.is_unknown(("wet",))              # True  — belief is revised automatically
```

The idea running through the whole system: **separate *what* you believe from
*why* you believe it.** Once every inference records its justification, the
system can explain itself, retract a premise and automatically un-derive its
consequences, and search a space without throwing away work it can reuse.

## What's in this site

| Page | What you'll find |
|---|---|
| [Getting Started](getting-started.md) | Install, the Python API, and the `.kb` world-model file format |
| [Architecture](architecture.md) | The layered design, every module, and the key algorithms in plain language |
| [Study Companion](companion/README.md) | A chapter-by-chapter guide to the book, in our own words |
| [Exercises](exercises.md) | Worked solutions to the book's chapter exercises |
| [Examples](examples.md) | Runnable demos and `.kb` knowledge bases |

## Why this exists

There is no faithful Python LTMS in the wild. JTMS and ATMS have a few toy ports,
but the clausal-BCP LTMS with dependency-directed backtracking is the
least-ported truth maintenance system outside Lisp and Racket. This repository is
a clean, tested, idiomatic-Python implementation: 17 source modules, 143 tests,
`ruff` + `mypy --strict` clean, building from terms-and-unification all the way up
to optional logical completeness.

## Start with the companion

New to truth maintenance? The **[Study Companion](companion/README.md)** walks
through the book chapter by chapter — the big ideas, the data structures and
algorithms in plain language, the worked examples explained, and runnable
commands against this repo's code. A suggested path to the LTMS itself:

[Ch 4](companion/ch04.md) pattern rules → [Ch 6](companion/ch06.md) /
[Ch 7](companion/ch07.md) what a TMS is → [Ch 9](companion/ch09.md) the LTMS →
[Ch 10](companion/ch10.md) the reasoning engine.

## Provenance & licensing

Original code here is MIT licensed. This is an independent reimplementation of
the algorithms in *Building Problem Solvers*; it does not copy the original
Common Lisp source. The book's full-text PDF is available for free download from
the [Northwestern Qualitative Reasoning Group](https://www.qrg.northwestern.edu/BPS/readme.html)
"thanks to the gracious permission of MIT Press" (MIT Press retains print
rights). The book PDF and reference code are kept local and are **not**
redistributed here. See
[NOTICE](https://github.com/pisanuw/ltms/blob/main/NOTICE) for full attribution.
