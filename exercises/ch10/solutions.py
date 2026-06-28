"""Runnable solutions for selected Chapter 10 (LTRE) exercises.

See README.md for the paraphrased problem statements and written answers.
"""

from __future__ import annotations

from ltms.core import Label
from ltms.dds import dd_search
from ltms.ltre import LTRE
from ltms.terms import Term


# --- Ex 2: adding an XOR connective --------------------------------------- #
def xor(a: Term, b: Term) -> Term:
    """Exclusive-or as a derived connective: (a v b) & ~(a & b)."""
    return ("and", ("or", a, b), ("not", ("and", a, b)))


def ex2_xor() -> dict[str, bool]:
    results = {}
    e = LTRE()
    e.assert_(xor(("p",), ("q",)))
    e.assume(("p",), "h")
    results["p_true_forces_q_false"] = e.is_false(("q",))

    e2 = LTRE()
    e2.assert_(xor(("p",), ("q",)))
    e2.assume(("not", ("p",)), "h")
    results["p_false_forces_q_true"] = e2.is_true(("q",))
    assert all(results.values())
    return results


# --- Ex 3a: NEEDS (one-step abduction) ------------------------------------ #
def needs(engine: LTRE, fact: Term, value: bool = True) -> list[frozenset[Term]]:
    """Sets of facts which, if known, would force ``fact`` to ``value``.

    One-step abduction: for each clause mentioning the goal literal, the other
    literals must all be false, which pins each of their nodes to a definite
    (signed) fact. Each such clause yields one candidate support set. (Deeper
    explanations need a recursive search; see the README.)
    """
    datum = engine.referent(fact, create=True)
    assert datum is not None
    goal = datum.tms_node
    want = Label.TRUE if value else Label.FALSE
    out: list[frozenset[Term]] = []
    for clause in engine.ltms.clauses:
        if not any(n is goal and s is want for n, s in clause.literals):
            continue
        support: set[Term] = set()
        for n, s in clause.literals:
            if n is goal:
                continue
            form = n.datum.lisp_form if hasattr(n.datum, "lisp_form") else n.datum
            # to force the goal, this literal must be false:
            support.add(form if s is Label.FALSE else ("not", form))
        out.append(frozenset(support))
    return out


def ex3a_needs() -> list[list[Term]]:
    e = LTRE()
    # (a & b) -> c  ==  ~a v ~b v c
    e.assert_(("implies", ("and", ("a",), ("b",)), ("c",)))
    sets = needs(e, ("c",), value=True)
    as_sorted = [sorted(s, key=str) for s in sets]
    assert frozenset({("a",), ("b",)}) in sets  # need a and b
    return as_sorted


# --- Ex 7a: N-queens via dependency-directed search ----------------------- #
def n_queens(n: int) -> list[tuple[tuple[int, int], ...]]:
    e = LTRE()
    for r in range(n):
        for c in range(n):
            e.referent(("q", r, c), create=True)
    # No two queens may attack: same column or same diagonal.
    for r1 in range(n):
        for r2 in range(r1 + 1, n):
            for c1 in range(n):
                for c2 in range(n):
                    if c1 == c2 or abs(r1 - r2) == abs(c1 - c2):
                        e.contradiction([("q", r1, c1), ("q", r2, c2)], "attack")
    choice_sets = [[("q", r, c) for c in range(n)] for r in range(n)]

    def extract(eng: LTRE) -> tuple[tuple[int, int], ...]:
        return tuple(
            (r, c) for r in range(n) for c in range(n) if eng.is_true(("q", r, c))
        )

    return dd_search(e, choice_sets, extract)


def ex7a_n_queens() -> dict[int, int]:
    counts = {n: len(n_queens(n)) for n in (4, 5, 6)}
    assert counts == {4: 2, 5: 10, 6: 4}  # known solution counts
    return counts


def solve() -> dict[str, object]:
    return {
        "ex2_xor": ex2_xor(),
        "ex3a_needs": ex3a_needs(),
        "ex7a_n_queens_counts": ex7a_n_queens(),
    }


if __name__ == "__main__":
    import pprint

    pprint.pp(solve())
