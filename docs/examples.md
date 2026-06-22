---
title: Examples
nav_order: 6
---

# Examples

Runnable demos live in
[`examples/`](https://github.com/pisanuw/ltms/tree/main/examples/). Activate the
environment first (`. .venv/bin/activate`).

## Python demos

| Demo | What it shows |
|---|---|
| [`family_tre.py`](https://github.com/pisanuw/ltms/blob/main/examples/family_tre.py) | Pattern-directed forward chaining with TRE — deriving family relationships from rules |
| [`belief_revision_ltre.py`](https://github.com/pisanuw/ltms/blob/main/examples/belief_revision_ltre.py) | Assumptions and automatic belief revision in LTRE (now a thin `.kb` loader) |
| [`coloring_dds.py`](https://github.com/pisanuw/ltms/blob/main/examples/coloring_dds.py) | Graph coloring solved by dependency-directed search with nogood learning |

```bash
python examples/family_tre.py
python examples/coloring_dds.py
```

## World models as `.kb` files

The `.kb` DSL lets a world model live in a data file, separate from Python. Each
file is self-checking: its `expect` lines assert the resulting belief state, and
`pytest tests/test_kb_files.py` runs every one of them.

| File | Demonstrates |
|---|---|
| [`belief_revision.kb`](https://github.com/pisanuw/ltms/blob/main/examples/kb/belief_revision.kb) | Retractable assumptions and belief revision |
| [`modus_tollens.kb`](https://github.com/pisanuw/ltms/blob/main/examples/kb/modus_tollens.kb) | Contrapositive reasoning via BCP |
| [`taxonomy.kb`](https://github.com/pisanuw/ltms/blob/main/examples/kb/taxonomy.kb) | The `taxonomy` (exactly-one) directive |
| [`completeness.kb`](https://github.com/pisanuw/ltms/blob/main/examples/kb/completeness.kb) | The `complete` directive (prime-implicate completion) |
| [`diagnosis.kb`](https://github.com/pisanuw/ltms/blob/main/examples/kb/diagnosis.kb) | A small diagnosis model |
| [`family.kb`](https://github.com/pisanuw/ltms/blob/main/examples/kb/family.kb) | Implication rules over family relationships |

Run any `.kb` file directly:

```bash
python examples/run_kb.py examples/kb/belief_revision.kb
```

A minimal model looks like this:

```
# examples/kb/belief_revision.kb
rain         -> wet ground
sprinkler on -> wet ground
assume rain
expect wet ground true
```

The full directive set (`assert`, `assume`/`retract`, `->` rules, `taxonomy`,
`complete`, `contradiction`, `query`, `expect`) is documented in the
[`ltms.dsl`](https://github.com/pisanuw/ltms/blob/main/src/ltms/dsl.py) source.
Chapter-specific `.kb` models also live under
[`exercises/chNN/kb/`](https://github.com/pisanuw/ltms/tree/main/exercises/) — see
the [Exercises](exercises.md) page.
