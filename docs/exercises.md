---
title: Exercises
nav_order: 5
---

# Book Exercises — Worked Solutions

Worked solutions to the chapter exercises of *Building Problem Solvers*, one
directory per chapter, under
[`exercises/`](https://github.com/pisanuw/ltms/tree/main/exercises/) in the repo.

**About the statements.** The book's exercise text is copyrighted, so every
problem is **paraphrased in our own words**; the answers, derivations, and code
are original. The book's difficulty stars (★ … ★★★★) are kept as a guide.

**Two kinds of chapter:**

- **Code** chapters cover systems implemented in the `ltms` package, so they ship
  a runnable `solutions.py` with a self-checking `solve()`. The test suite runs
  them (`pytest tests/test_exercises.py`), so the answers are verified in CI.
- **Analysis** chapters cover systems outside this package's scope (CPS, FTRE,
  QP / TGIZMO, ATMS, constraint languages, relaxation); their answers are
  conceptual — algorithm sketches, derivations, complexity, and design.

| Chapter | Topic | Kind |
|---|---|---|
| [ch03](https://github.com/pisanuw/ltms/tree/main/exercises/ch03/) | Classical Problem Solving | analysis |
| [ch04](https://github.com/pisanuw/ltms/tree/main/exercises/ch04/) | Pattern-Directed Inference (TRE) | code |
| [ch05](https://github.com/pisanuw/ltms/tree/main/exercises/ch05/) | Extending PDIS (FTRE) | analysis |
| [ch06](https://github.com/pisanuw/ltms/tree/main/exercises/ch06/) | Introduction to Truth Maintenance | code |
| [ch07](https://github.com/pisanuw/ltms/tree/main/exercises/ch07/) | Justification-Based TMS (JTMS) | code |
| [ch08](https://github.com/pisanuw/ltms/tree/main/exercises/ch08/) | Putting the JTMS to Work (JTRE) | code |
| [ch09](https://github.com/pisanuw/ltms/tree/main/exercises/ch09/) | **Logic-Based TMS (LTMS)** | code |
| [ch10](https://github.com/pisanuw/ltms/tree/main/exercises/ch10/) | **Putting an LTMS to Work (LTRE)** | code |
| [ch11](https://github.com/pisanuw/ltms/tree/main/exercises/ch11/) | Implementing Qualitative Process Theory | analysis |
| [ch12](https://github.com/pisanuw/ltms/tree/main/exercises/ch12/) | Assumption-Based TMS (ATMS) | analysis |
| [ch13](https://github.com/pisanuw/ltms/tree/main/exercises/ch13/) | Improving Completeness of TMS (CLTMS) | code |
| [ch14](https://github.com/pisanuw/ltms/tree/main/exercises/ch14/) | Putting the ATMS to Work | analysis |
| [ch15](https://github.com/pisanuw/ltms/tree/main/exercises/ch15/) | Antecedent Constraint Languages | analysis |
| [ch16](https://github.com/pisanuw/ltms/tree/main/exercises/ch16/) | Assumption-Based Constraint Languages | analysis |
| [ch17](https://github.com/pisanuw/ltms/tree/main/exercises/ch17/) | A Tiny Diagnosis Engine (TGDE) | analysis |
| [ch18](https://github.com/pisanuw/ltms/tree/main/exercises/ch18/) | Symbolic Relaxation Systems | analysis |

Each chapter also has a narrated walk-through of its notable solutions in the
[Study Companion](companion/README.md).

## Run them

```bash
. .venv/bin/activate
for f in exercises/ch*/solutions.py; do echo "== $f =="; python "$f"; done
```

Where an exercise is a declarative propositional model, it is *also* expressed as
a `.kb` data file under `exercises/chNN/kb/` — the model lives in the file, not in
Python. These are self-checking (`expect` lines) and run by
`pytest tests/test_kb_files.py`; load any of them with
`python examples/run_kb.py <file.kb>`. See the [Examples](examples.md) page.
