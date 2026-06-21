# Book exercises — worked solutions

Solutions to the chapter exercises of Forbus & de Kleer, *Building Problem
Solvers*. There is one directory per chapter.

**About the statements.** The book's exercise text is copyrighted, so every
problem is **paraphrased in our own words**; the answers, derivations, and code
are original. The book's difficulty stars (★ … ★★★★) are kept as a guide.

**Two kinds of chapter.**
- **Code** chapters cover systems implemented in the `ltms` package, so they
  ship a runnable `solutions.py` (with a self-checking `solve()`); the test
  suite runs them (`pytest tests/test_exercises.py`).
- **Analysis** chapters cover systems outside this package's scope (CPS, FTRE,
  QP/TGIZMO, ATMS, constraint languages, relaxation); their answers are
  conceptual — algorithm sketches, derivations, complexity, and design.

| Chapter | Topic | Kind |
|---|---|---|
| [ch03](ch03/) | Classical Problem Solving | analysis |
| [ch04](ch04/) | Pattern-Directed Inference (TRE) | code |
| [ch05](ch05/) | Extending PDIS (FTRE) | analysis |
| [ch06](ch06/) | Introduction to Truth Maintenance | code |
| [ch07](ch07/) | Justification-Based TMS (JTMS) | code |
| [ch08](ch08/) | Putting the JTMS to Work (JTRE) | code |
| [ch09](ch09/) | **Logic-Based TMS (LTMS)** | code |
| [ch10](ch10/) | **Putting an LTMS to Work (LTRE)** | code |
| [ch11](ch11/) | Implementing Qualitative Process Theory | analysis |
| [ch12](ch12/) | Assumption-Based TMS (ATMS) | analysis |
| [ch13](ch13/) | Improving Completeness of TMS (CLTMS) | code |
| [ch14](ch14/) | Putting the ATMS to Work | analysis |
| [ch15](ch15/) | Antecedent Constraint Languages | analysis |
| [ch16](ch16/) | Assumption-Based Constraint Languages | analysis |
| [ch17](ch17/) | A Tiny Diagnosis Engine (TGDE) | analysis |
| [ch18](ch18/) | Symbolic Relaxation Systems | analysis |

Run every code chapter's solutions:

```bash
. .venv/bin/activate
for f in exercises/ch*/solutions.py; do echo "== $f =="; python "$f"; done
```
