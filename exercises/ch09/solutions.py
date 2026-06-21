"""Runnable solutions for selected Chapter 9 (LTMS) exercises.

See README.md for the paraphrased problem statements and the written answers.
Each ``solve()`` entry is self-checking (asserts its expected result).
"""

from __future__ import annotations

from math import comb, prod

from ltms.cltms import complete
from ltms.core import LTMS, Label, LTMSContradiction
from ltms.normalize import normalize


def ex3_clause_count() -> dict[str, int]:
    """Ex 3: how many clauses does a big OR-of-ANDs add-formula create?

    CNF of a disjunction of conjunctions is the cross product: choosing one
    conjunct from each disjunct. So the (raw) clause count is the product of the
    conjunct-counts of the disjuncts. We verify the cross-product rule on a tiny
    disjoint case, then report the count for the book's formula.
    """
    m = LTMS()
    p1, p2 = m.create_node("p1"), m.create_node("p2")
    q1, q2, q3 = m.create_node("q1"), m.create_node("q2"), m.create_node("q3")
    cnf = normalize(("or", ("and", p1, p2), ("and", q1, q2, q3)))
    assert len(cnf) == 2 * 3  # cross product, disjoint literals

    # The book's formula has 13 disjuncts with these conjunct-counts:
    disjunct_sizes = [4, 4, 4, 4, 4, 4, 2, 3, 3, 3, 3, 3, 3]
    raw = prod(disjunct_sizes)
    return {"tiny_case_clauses": len(cnf), "book_formula_raw_clauses": raw}


def ex4_taxonomy_cnf_size() -> dict[int, int]:
    """Ex 4: a TAXONOMY over n nodes expands to C(n,2)+1 CNF clauses.

    'Exactly one of n' = (one of them holds) AND (no two hold together):
    1 big disjunction + one 2-literal clause per pair = 1 + n(n-1)/2.
    """
    counts: dict[int, int] = {}
    for n in range(2, 8):
        m = LTMS()
        nodes = [m.create_node(f"x{i}") for i in range(n)]
        cnf = normalize(("taxonomy", *nodes))
        counts[n] = len(cnf)
        assert len(cnf) == comb(n, 2) + 1
    return counts


def ex5_completeness() -> dict[str, str]:
    """Ex 5: adding all (prime) implicates makes BCP logically complete.

    Demonstrated two ways: a case where a unit becomes derivable, and an
    unsatisfiable case that BCP alone cannot refute until completion.
    """
    # Literal completeness: {x v ~y, x v y} entails x.
    m = LTMS()
    x, y = m.create_node("x"), m.create_node("y")
    m.add_clause([x], [y], "x v ~y")
    m.add_clause([x, y], [], "x v y")
    assert x.label is Label.UNKNOWN
    complete(m)
    assert x.is_true
    literal = "x forced TRUE after completion"

    # Refutation completeness: the unsatisfiable 4-clause set on {x, y}.
    m2 = LTMS()
    a, b = m2.create_node("a"), m2.create_node("b")
    m2.add_clause([], [a, b], "~a v ~b")
    m2.add_clause([b], [a], "~a v b")
    m2.add_clause([a], [b], "a v ~b")
    m2.add_clause([a, b], [], "a v b")
    detected = False
    try:
        complete(m2)
    except LTMSContradiction:
        detected = True
    assert detected
    refutation = "unsatisfiable 4-clause set detected after completion"
    return {"literal_completeness": literal, "refutation_completeness": refutation}


def solve() -> dict[str, object]:
    return {
        "ex3_clause_count": ex3_clause_count(),
        "ex4_taxonomy_cnf_size": ex4_taxonomy_cnf_size(),
        "ex5_completeness": ex5_completeness(),
    }


if __name__ == "__main__":
    import pprint

    pprint.pp(solve())
