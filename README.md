# ltms

A logic-based **Truth Maintenance System (LTMS)** and a **pattern-directed
reasoning engine** in pure Python, after Forbus & de Kleer, *Building Problem
Solvers* (MIT Press, 1993).

The LTMS maintains belief over a set of propositional clauses using **Boolean
Constraint Propagation** (unit propagation), records **well-founded support** for
every derived value, performs **dependency-directed backtracking** on
contradictions, and can **explain** why anything is believed. A small
forward-chaining rule engine sits on top of it.

> Status: **under construction.** See [PLAN.md](PLAN.md) for the multi-session
> build plan and [STUDY-NOTES.md](STUDY-NOTES.md) for the technical digest.

## Why

There is no faithful Python LTMS in the wild — JTMS/ATMS have a few toy ports,
but the clausal-BCP LTMS with dependency-directed backtracking is the
least-ported truth maintenance system outside Lisp/Racket. This is a clean,
tested, idiomatic-Python implementation.

## Layers (built bottom-up)

```
terms + unify  →  TRE  →  [JTMS]  →  LTMS core (BCP)  →  LTRE  →  indirect / CWA / DDS  →  [CLTMS]
```

## Install (development)

```bash
python -m venv .venv && . .venv/bin/activate
pip install -e ".[dev]"
pytest
```

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
