# A Study Companion to *Building Problem Solvers*

A chapter-by-chapter guide to Forbus & de Kleer's *Building Problem Solvers*
(MIT Press, 1993), written to accompany this repository's Python implementation
of the truth-maintenance core.

Everything here is in **our own words** — explanations of the ideas, walk-throughs
of the worked examples, and solutions to the exercises. It is a companion *to*
the book, not a copy of it; to read the book itself, get the freely available PDF
from the [Northwestern Qualitative Reasoning Group](https://www.qrg.northwestern.edu/BPS/readme.html).

## How to use this companion

Each chapter page follows the same shape:

1. **The big idea** — why the chapter exists and what problem it solves.
2. **Concepts, step by step** — the data structures and algorithms in plain language.
3. **The examples, explained** — what each worked example demonstrates.
4. **Exercises walk-through** — the notable solutions (full set in [`../exercises/`](../exercises/)).
5. **Try it in this repo** — runnable commands against our Python code.
6. **Takeaways**.

Set up once, then follow along:

```bash
python -m venv .venv && . .venv/bin/activate
pip install -e ".[dev]"
pytest                       # everything green
```

## The arc of the book

The book builds a problem solver from the bottom up, and so does this repo. Each
layer adds one capability:

```
search            (ch 3)            how to explore a space of states
pattern rules     (ch 4-5)          fire rules by matching facts  ── src/ltms/tre
truth maintenance (ch 6-7)          remember WHY you believe things, revise cleanly ── src/ltms/jtms
   on a rule engine (ch 8)          a TMS-backed inference engine ── src/ltms/jtre
logic-based TMS   (ch 9-10, 13)     belief over clauses via Boolean Constraint Propagation ── src/ltms/core, ltre, cltms
assumption-based  (ch 12, 14)       reason in many contexts at once (ATMS)
applications      (ch 11, 15-18)    qualitative physics, constraints, diagnosis, relaxation
```

The thread running through all of it: **separate *what you believe* from *why you
believe it*.** Once inferences record their justifications, a system can explain
itself, retract a premise and automatically un-derive its consequences, and
search without losing work — the recurring payoff of truth maintenance.

## What this repository implements

| Book chapter | Companion | In this repo? | Module |
|---|---|---|---|
| 1 Preface, 2 Introduction | *(this page)* | — | — |
| 3 Classical Problem Solving | [ch03](ch03.md) | concept | — |
| 4 Pattern-Directed Inference (TRE) | [ch04](ch04.md) | ✅ code | [`tre/`](../src/ltms/tre/) |
| 5 Extending PDIS (FTRE) | [ch05](ch05.md) | concept | — |
| 6 Introduction to TMS | [ch06](ch06.md) | ✅ code | [`jtms.py`](../src/ltms/jtms.py) |
| 7 Justification-Based TMS | [ch07](ch07.md) | ✅ code | [`jtms.py`](../src/ltms/jtms.py) |
| 8 Putting the JTMS to Work (JTRE) | [ch08](ch08.md) | ✅ code | [`jtre.py`](../src/ltms/jtre.py) |
| 9 **Logic-Based TMS (LTMS)** | [ch09](ch09.md) | ✅ code | [`core.py`](../src/ltms/core.py), [`watched.py`](../src/ltms/watched.py) |
| 10 **Putting an LTMS to Work (LTRE)** | [ch10](ch10.md) | ✅ code | [`ltre.py`](../src/ltms/ltre.py), [`indirect`](../src/ltms/indirect.py)/[`cwa`](../src/ltms/cwa.py)/[`dds`](../src/ltms/dds.py) |
| 11 Qualitative Process Theory | [ch11](ch11.md) | concept | — |
| 12 Assumption-Based TMS (ATMS) | [ch12](ch12.md) | concept | — |
| 13 Improving Completeness (CLTMS) | [ch13](ch13.md) | ✅ code | [`cltms.py`](../src/ltms/cltms.py) |
| 14 Putting the ATMS to Work | [ch14](ch14.md) | concept | — |
| 15 Antecedent Constraint Languages | [ch15](ch15.md) | concept | — |
| 16 Assumption-Based Constraint Languages | [ch16](ch16.md) | concept | — |
| 17 A Tiny Diagnosis Engine (TGDE) | [ch17](ch17.md) | concept | — |
| 18 Symbolic Relaxation Systems | [ch18](ch18.md) | concept | — |

**Code** chapters have a working Python implementation, runnable examples, and
executable exercise solutions. **Concept** chapters cover systems outside this
package's scope; their pages explain the ideas and the exercise pages give
conceptual answers.

## Before chapter 3: what the book is doing (chapters 1–2)

The opening chapters set the agenda. AI reasoning programs differ from ordinary
programs in a specific way: instead of computing one answer by a fixed
procedure, they *search*, they reason from declarative knowledge, and they often
must **change their minds** as new information arrives. The book's method is to
build a sequence of small, readable engines — each one runnable, each one adding
exactly one idea — rather than presenting finished systems as black boxes. This
companion keeps that spirit: every implemented idea here is a few hundred lines
you can read, run, and modify.

A recurring design principle worth holding onto from the start: **make the
dependencies explicit.** A plain database knows *that* `wet` is true; a
truth-maintained database knows *because of* `rain` — and that single difference
is what lets it explain, retract, and search well.

## A suggested reading path

- **Just want the LTMS?** Read [ch04](ch04.md) (pattern rules) → [ch06](ch06.md)
  / [ch07](ch07.md) (what a TMS is) → [ch09](ch09.md) (LTMS) → [ch10](ch10.md)
  (the reasoning engine). That is the critical path this repo was built around.
- **Want the full belief-revision story?** Add [ch08](ch08.md) (JTRE) and
  [ch13](ch13.md) (completeness).
- **Curious about the wider family?** [ch12](ch12.md) (ATMS) and the application
  chapters (11, 14–18).

## Related documents in this repo

- [PLAN.md](../PLAN.md) — the multi-session build plan.
- [STUDY-NOTES.md](../STUDY-NOTES.md) — a dense technical digest of the TMS internals.
- [exercises/](../exercises/) — worked solutions to every chapter's exercises.
- [examples/](../examples/) — runnable demos, including `.kb` world-model files.
