import pytest

from ltms.core import LTMS, Label, LTMSContradiction
from ltms.normalize import add_formula, normalize


def _nodes(m, *names):
    return [m.create_node(n) for n in names]


def test_implies_normalizes_to_single_clause():
    m = LTMS()
    p, q = _nodes(m, "p", "q")
    cnf = normalize(("implies", p, q))  # ~p v q
    assert cnf == [[(p, Label.FALSE), (q, Label.TRUE)]]


def test_and_normalizes_to_separate_clauses():
    m = LTMS()
    p, q = _nodes(m, "p", "q")
    cnf = normalize(("and", p, q))
    assert cnf == [[(p, Label.TRUE)], [(q, Label.TRUE)]]


def test_de_morgan_on_negated_and():
    m = LTMS()
    p, q = _nodes(m, "p", "q")
    cnf = normalize(("not", ("and", p, q)))  # ~p v ~q
    assert cnf == [[(p, Label.FALSE), (q, Label.FALSE)]]


def test_iff_expands_to_two_implications():
    m = LTMS()
    p, q = _nodes(m, "p", "q")
    cnf = normalize(("iff", p, q))  # (~p v q) and (~q v p)
    assert [(p, Label.FALSE), (q, Label.TRUE)] in cnf
    assert [(q, Label.FALSE), (p, Label.TRUE)] in cnf


def test_add_formula_propagates():
    m = LTMS()
    p, q, r = _nodes(m, "p", "q", "r")
    add_formula(m, ("implies", p, q))
    add_formula(m, ("implies", q, r))
    add_formula(m, p)  # assert p as a unit
    assert p.is_true and q.is_true and r.is_true


def test_taxonomy_exactly_one():
    m = LTMS()
    a, b, c = _nodes(m, "a", "b", "c")
    add_formula(m, ("taxonomy", a, b, c))
    # Assert a is true; "exactly one" forces b and c false.
    m.assume(a, Label.TRUE)
    assert a.is_true and b.is_false and c.is_false


def test_false_formula_is_contradiction():
    m = LTMS()
    p = m.create_node("p")
    add_formula(m, p)  # p true
    with pytest.raises(LTMSContradiction):
        add_formula(m, ("not", p))  # ~p -> violated
