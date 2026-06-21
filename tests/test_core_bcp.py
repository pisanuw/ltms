import pytest

from ltms.core import LTMS, Label, LTMSContradiction


def test_unit_clause_forces_truth():
    m = LTMS()
    a = m.create_node("a")
    m.add_clause([a], [], "premise")
    assert a.is_true
    a2 = m.create_node("a2")
    m.add_clause([], [a2], "neg-premise")
    assert a2.is_false


def test_unit_propagation_disjunction():
    m = LTMS()
    a, b = m.create_node("a"), m.create_node("b")
    m.add_clause([a, b], [], "a-or-b")  # pvs=2, nothing forced
    assert a.label is Label.UNKNOWN and b.label is Label.UNKNOWN
    m.add_clause([], [a], "not-a")  # a := FALSE -> forces b := TRUE
    assert a.is_false
    assert b.is_true


def test_implication_chain():
    m = LTMS()
    p, q, r = m.create_node("p"), m.create_node("q"), m.create_node("r")
    m.add_clause([q], [p], "p->q")  # ~p v q
    m.add_clause([r], [q], "q->r")  # ~q v r
    assert p.label is Label.UNKNOWN
    m.add_clause([p], [], "p")  # assert p
    assert p.is_true and q.is_true and r.is_true


def test_well_founded_support_is_the_forcing_clause():
    m = LTMS()
    p, q = m.create_node("p"), m.create_node("q")
    impl = m.add_clause([q], [p], "p->q")
    m.add_clause([p], [], "p")
    assert q.support is impl  # q forced by the implication clause


def test_contradiction_raises_by_default():
    m = LTMS()
    p = m.create_node("p")
    m.add_clause([p], [], "p")  # p := TRUE
    with pytest.raises(LTMSContradiction):
        m.add_clause([], [p], "not-p")  # p := FALSE -> violated clause


def test_bcp_is_incomplete_leaves_entailed_literal_unknown():
    # {x v ~y, x v y} entails x, but unit propagation cannot derive it.
    m = LTMS()
    x, y = m.create_node("x"), m.create_node("y")
    m.add_clause([x], [y], "x v ~y")
    m.add_clause([x, y], [], "x v y")
    assert x.label is Label.UNKNOWN  # expected: BCP is sound, not complete
    assert y.label is Label.UNKNOWN


def test_bcp_is_refutation_incomplete():
    # {~x~y, ~xy, x~y, xy} is UNSAT, but unit propagation cannot detect it:
    # every clause keeps 2 potential violators, so nothing is ever forced.
    m = LTMS()
    x, y = m.create_node("x"), m.create_node("y")
    m.add_clause([], [x, y], "~x v ~y")
    m.add_clause([y], [x], "~x v y")
    m.add_clause([x], [y], "x v ~y")
    m.add_clause([x, y], [], "x v y")
    # No contradiction raised, all labels unknown -- expected (sound, not complete).
    assert x.label is Label.UNKNOWN and y.label is Label.UNKNOWN


def test_tautology_is_dropped():
    m = LTMS()
    x = m.create_node("x")
    result = m.add_clause([x], [x], "x v ~x")  # tautology
    assert result is None
    assert x.label is Label.UNKNOWN
    assert m.clauses == []


def test_duplicate_literals_collapse_to_unit():
    m = LTMS()
    a = m.create_node("a")
    m.add_clause([a, a], [], "a v a")  # simplifies to unit (a)
    assert a.is_true


def test_deferred_dispatch_parks_when_checking_disabled():
    m = LTMS()
    m.checking_contradictions = False
    p = m.create_node("p")
    m.add_clause([p], [], "p")
    m.add_clause([], [p], "not-p")  # contradiction, but parked (not raised)
    assert m.pending_contradictions  # parked instead of dispatched


def test_longer_propagation_with_negatives():
    m = LTMS()
    a, b, c = m.create_node("a"), m.create_node("b"), m.create_node("c")
    m.add_clause([b], [a], "a->b")  # ~a v b
    m.add_clause([], [c, b], "~b v ~c")  # b -> ~c
    m.add_clause([a], [], "a")
    assert a.is_true and b.is_true and c.is_false
