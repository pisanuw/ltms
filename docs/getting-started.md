---
title: Getting Started
nav_order: 2
---

# Getting Started

## Install (development)

```bash
git clone https://github.com/pisanuw/ltms
cd ltms
python -m venv .venv && . .venv/bin/activate
pip install -e ".[dev]"      # add ".[dev,sat]" for the PySAT differential tests
pytest                        # everything green
```

The package targets Python 3.10+ and ships type hints (`py.typed`). The continuous
integration build runs `ruff`, `mypy --strict`, and `pytest` on Python 3.10–3.13.

## The reasoning engine (LTRE)

`LTRE` is the high-level entry point: a forward-chaining, pattern-directed
reasoning engine sitting on top of the LTMS. You assert facts and implications,
make retractable assumptions, and ask what is currently believed.

```python
from ltms import LTRE

e = LTRE()
e.assert_(("or", ("p",), ("q",)))   # p v q
e.assert_(("not", ("p",)))          # ~p
e.is_true(("q",))                   # True  — forced by unit propagation
```

Assumptions are belief you can take back. Retracting one automatically un-derives
everything that depended on it:

```python
e.assume(("rain",), "guess")        # "guess" is the informant / reason
e.assert_(("implies", ("rain",), ("wet",)))
e.is_true(("wet",))                 # True
e.retract(("rain",), "guess")
e.is_unknown(("wet",))              # True  — belief revised, no manual cleanup
```

Queries are three-valued: a proposition is `TRUE`, `FALSE`, or `UNKNOWN`. The
helpers `is_true`, `is_false`, `is_known`, and `is_unknown` read the label,
inverting the sign for negated queries.

## World models in `.kb` files

A world model can live in a `.kb` data file, separate from your Python. The DSL
is a small Lisp-like language with directives for assertions, assumptions,
implication rules, taxonomies, contradictions, queries, and self-checking
`expect` lines:

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

See the [Examples](examples.md) page for the full set of runnable demos and `.kb`
knowledge bases, and the
[`ltms.dsl`](https://github.com/pisanuw/ltms/blob/main/src/ltms/dsl.py) source for
the directive reference.

## Where to go next

- **Understand the design:** the [Architecture](architecture.md) page maps every
  module and explains the core algorithms.
- **Learn the theory:** the [Study Companion](companion/README.md) walks through
  the book chapter by chapter, with runnable commands against this code.
- **See it work:** the [Examples](examples.md) and [Exercises](exercises.md)
  pages collect the runnable material.
