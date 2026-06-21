"""Runnable solutions for selected Chapter 13 (CLTMS / completeness) exercises.

See README.md for the paraphrased problem statements and written answers.
This chapter's algorithms (consensus, prime implicates, completion, indirect
proof) are implemented in the ltms package, so most exercises can be exercised
directly through the public API.
"""

from __future__ import annotations

from math import comb

from ltms import (
    LTMS,
    LTRE,
    Label,
    add_formula,
    complete,
    consensus,
    normalize,
    prime_implicates,
    try_indirect_proof,
)
from ltms.core import LTMSContradiction

T, F = Label.TRUE, Label.FALSE


def _show(clause):
    """Readable, order-independent rendering of a clause (set of literals)."""
    if clause is None:
        return None
    return tuple(sorted((str(n.datum), s.name) for n, s in clause))


# --- Ex 1: many more prime implicates than CNF conjuncts ------------------- #
def ex1_blowup() -> dict[str, object]:
    """A transitive implication chain: n-1 conjuncts, C(n,2) prime implicates.

    x0 -> x1 -> ... -> x_{n-1} is stored as n-1 binary clauses, but its prime
    implicates are *every* derived implication x_i -> x_j (i < j), so the count
    grows quadratically while the input grows linearly.
    """
    results = {}
    for n in (5, 8):
        m = LTMS()
        xs = [m.create_node(("x", i), assumption=True) for i in range(n)]
        clauses = []
        for i in range(n - 1):
            for c in normalize(("implies", xs[i], xs[i + 1])):
                clauses.append(frozenset(c))
        pis = prime_implicates(clauses)
        results[f"n={n}"] = {
            "input_conjuncts": len(clauses),
            "prime_implicates": len(pis),
            "expected_C(n,2)": comb(n, 2),
        }
        assert len(pis) == comb(n, 2)
    return results


# --- Ex 2: consensus is not associative ----------------------------------- #
def ex2_non_associative() -> dict[str, object]:
    """Three clauses where left- and right-grouped consensus disagree.

    c1 = {a}, c2 = {~a, b}, c3 = {a, ~b, c}.
      Left:  (c1 o c2) = {b}; ({b} o c3) = {a, c}        -- defined.
      Right: (c2 o c3) shares TWO complementary pairs -> tautology -> None,
             so c1 o None = None                          -- undefined.
    """
    m = LTMS()
    a = m.create_node("a", assumption=True)
    b = m.create_node("b", assumption=True)
    c = m.create_node("c", assumption=True)
    c1 = frozenset({(a, T)})
    c2 = frozenset({(a, F), (b, T)})
    c3 = frozenset({(a, T), (b, F), (c, T)})

    left = consensus(consensus(c1, c2), c3)
    right_inner = consensus(c2, c3)
    right = None if right_inner is None else consensus(c1, right_inner)

    results = {
        "left_(c1.c2).c3": _show(left),
        "right_inner_c2.c3": _show(right_inner),
        "right_c1.(c2.c3)": _show(right),
        "associative": left == right,
    }
    assert left is not None and right is None
    assert results["associative"] is False
    return results


# --- Ex 4: prime implicates of a TAXONOMY on n nodes ---------------------- #
def ex4_taxonomy() -> dict[str, object]:
    """A taxonomy (exactly-one-of n) has 1 + C(n,2) prime implicates.

    Its CNF is already prime: the single 'at least one' clause plus the
    n(n-1)/2 pairwise 'not both' clauses; no consensus produces anything new.
    """
    results = {}
    for n in (3, 5, 6):
        m = LTMS()
        nodes = [m.create_node(("t", i), assumption=True) for i in range(n)]
        cnf = [frozenset(c) for c in normalize(("taxonomy", *nodes))]
        pis = prime_implicates(cnf)
        expected = 1 + comb(n, 2)
        results[f"n={n}"] = {
            "prime_implicates": len(pis),
            "formula_1+C(n,2)": expected,
        }
        assert len(pis) == expected
    return results


# --- Ex 9: the "kean" prime-implicate counting problem -------------------- #
def kean_prime_implicates(k: int, m_: int) -> int:
    """Build the kean(k, m) clause set and count its prime implicates.

    Faithful to the (buggy) printed listing: clauses (a_i v ~s_j) for all i,j,
    plus the single clause (~a_1 v ... v ~a_k).
    """
    m = LTMS()
    a = {i: m.create_node(("a", i), assumption=True) for i in range(1, k + 1)}
    s = {j: m.create_node(("s", j), assumption=True) for j in range(1, m_ + 1)}
    clauses = [frozenset((a[i], F) for i in range(1, k + 1))]
    for i in range(1, k + 1):
        for j in range(1, m_ + 1):
            clauses.append(frozenset({(a[i], T), (s[j], F)}))
    return len(prime_implicates(clauses))


def ex9_kean() -> dict[str, object]:
    """Counts under our faithful reading of the printed code.

    Each s_j implies every a_i, which contradicts 'not all a_i', so each ~s_j is
    a unit prime implicate; with the original big clause that is m + 1 total.
    The book's stated 60,466,236 comes from a different (un-garbled) listing;
    see README for discussion.
    """
    return {
        "kean(3,6)_our_reading": kean_prime_implicates(3, 6),
        "kean(3,6)_m+1": 6 + 1,
        "kean(5,10)_our_reading": kean_prime_implicates(5, 10),
        "kean(5,10)_m+1": 10 + 1,
        "book_answer_kean(5,10)": 60466236,
    }


# --- Theme demo: BCP incompleteness cured by complete() / indirect proof -- #
def ex_completeness_demo() -> dict[str, object]:
    """{x v ~y, x v y} entails x, but unit propagation never derives it.

    Both completion (adding the prime implicate {x}) and indirect proof recover
    the entailment; the 4-clause unsatisfiable set over {p,q} is likewise only
    caught after completion.
    """
    results = {}

    # (a) plain BCP leaves x unknown
    m = LTMS()
    x = m.create_node("x", assumption=True)
    y = m.create_node("y", assumption=True)
    add_formula(m, ("or", x, ("not", y)), "c1")
    add_formula(m, ("or", x, y), "c2")
    results["bcp_x_label"] = x.label.name
    assert x.label is Label.UNKNOWN

    # (b) complete() adds the prime implicate {x} and forces it TRUE
    added = complete(m)
    results["complete_added_clauses"] = added
    results["after_complete_x_label"] = x.label.name
    assert x.label is Label.TRUE

    # (c) indirect proof recovers the same entailment without completion
    e = LTRE()
    e.assert_(("or", ("x",), ("not", ("y",))))
    e.assert_(("or", ("x",), ("y",)))
    results["bcp_only_is_true_x"] = e.is_true(("x",))
    results["indirect_proves_x"] = try_indirect_proof(e, ("x",))
    results["after_indirect_is_true_x"] = e.is_true(("x",))
    assert results["bcp_only_is_true_x"] is False
    assert results["indirect_proves_x"] is True
    assert results["after_indirect_is_true_x"] is True

    # (d) the 4-clause set over {p,q} is unsat; BCP misses it, complete() catches it
    m2 = LTMS()
    p = m2.create_node("p", assumption=True)
    q = m2.create_node("q", assumption=True)
    for lits in [
        ("or", p, q),
        ("or", p, ("not", q)),
        ("or", ("not", p), q),
        ("or", ("not", p), ("not", q)),
    ]:
        add_formula(m2, lits, "4clause")
    results["bcp_4clause_contradiction"] = False  # no contradiction from BCP alone
    try:
        complete(m2)
        results["complete_4clause_contradiction"] = False
    except LTMSContradiction:
        results["complete_4clause_contradiction"] = True
    assert results["complete_4clause_contradiction"] is True

    return results


def solve() -> dict:
    return {
        "ex1_blowup": ex1_blowup(),
        "ex2_non_associative": ex2_non_associative(),
        "ex4_taxonomy": ex4_taxonomy(),
        "ex9_kean": ex9_kean(),
        "completeness_demo": ex_completeness_demo(),
    }


if __name__ == "__main__":
    import pprint

    pprint.pp(solve())
