import pytest

from ltms.core import ENABLED_ASSUMPTION, LTMS, Label, LTMSContradiction, avoid_all


def test_enable_and_retract_restores_label():
    m = LTMS()
    a = m.create_node("a", assumption=True)
    b = m.create_node("b")
    m.add_clause([b], [a], "a->b")  # ~a v b
    m.enable_assumption(a, Label.TRUE)
    assert a.is_true and b.is_true
    assert a.support is ENABLED_ASSUMPTION
    m.retract_assumption(a)
    assert a.label is Label.UNKNOWN
    assert b.label is Label.UNKNOWN  # consequence withdrawn


def test_alternative_support_survives_retraction():
    m = LTMS()
    a = m.create_node("a", assumption=True)
    b = m.create_node("b", assumption=True)
    c = m.create_node("c")
    m.add_clause([c], [a], "a->c")
    m.add_clause([c], [b], "b->c")
    m.enable_assumption(a, Label.TRUE)
    m.enable_assumption(b, Label.TRUE)
    assert c.is_true
    m.retract_assumption(a)
    assert c.is_true  # re-derived from b
    m.retract_assumption(b)
    assert c.label is Label.UNKNOWN


def test_retraction_two_phase_avoids_circular_support():
    # b <-> c mutually imply; with no independent ground both are UNKNOWN.
    m = LTMS()
    b = m.create_node("b")
    c = m.create_node("c")
    m.add_clause([c], [b], "b->c")
    m.add_clause([b], [c], "c->b")
    a = m.create_node("a", assumption=True)
    m.add_clause([b], [a], "a->b")
    m.enable_assumption(a, Label.TRUE)
    assert b.is_true and c.is_true
    m.retract_assumption(a)
    # Neither b nor c may keep the other IN: both must go UNKNOWN.
    assert b.label is Label.UNKNOWN and c.label is Label.UNKNOWN


def test_avoid_all_resolves_contradiction_with_nogood():
    m = LTMS()
    a = m.create_node("a", assumption=True)
    b = m.create_node("b", assumption=True)
    # Enable both assumptions first, THEN add the conflicting constraint so the
    # clash surfaces as a violated clause (rather than being forced earlier).
    m.enable_assumption(a, Label.TRUE)
    m.enable_assumption(b, Label.TRUE)
    n_clauses_before = len(m.clauses)
    with m.with_contradiction_handler(avoid_all):
        m.add_clause([], [a, b], "not-both")  # both true -> violated -> avoid_all
    assert not (a.is_true and b.is_true)  # one was retracted
    assert len(m.clauses) > n_clauses_before  # a nogood clause was added


def test_unsatisfiable_without_assumptions_raises():
    m = LTMS()
    p = m.create_node("p")
    m.add_clause([p], [], "p")
    with pytest.raises(LTMSContradiction), m.with_contradiction_handler(avoid_all):
        m.add_clause([], [p], "not-p")  # no assumptions to retract


def test_enable_conflicting_value_raises():
    m = LTMS()
    a = m.create_node("a", assumption=True)
    m.add_clause([a], [], "a")  # a := TRUE (premise)
    a.assumption = True
    with pytest.raises(ValueError, match="cannot enable"):
        m.enable_assumption(a, Label.FALSE)
