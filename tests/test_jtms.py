import pytest

from ltms.jtms import ENABLED_ASSUMPTION, JTMS, JTMSContradiction


def test_premise_is_in():
    j = JTMS()
    a = j.create_node("a")
    j.justify_node("premise", a, [])
    assert a.is_in
    assert a.is_premise


def test_justification_with_antecedents():
    j = JTMS()
    a = j.create_node("a", assumption=True)
    b = j.create_node("b")
    j.justify_node("a=>b", b, [a])
    assert b.is_out  # a not yet enabled
    j.enable_assumption(a)
    assert a.is_in and b.is_in
    assert b.support is not None and not b.is_premise


def test_enable_then_retract_propagates_out():
    j = JTMS()
    a = j.create_node("a", assumption=True)
    b = j.create_node("b")
    c = j.create_node("c")
    j.justify_node("a=>b", b, [a])
    j.justify_node("b=>c", c, [b])
    j.enable_assumption(a)
    assert a.is_in and b.is_in and c.is_in
    j.retract_assumption(a)
    assert a.is_out and b.is_out and c.is_out


def test_alternative_support_survives_retraction():
    j = JTMS()
    a = j.create_node("a", assumption=True)
    b = j.create_node("b", assumption=True)
    c = j.create_node("c")
    j.justify_node("a=>c", c, [a])
    j.justify_node("b=>c", c, [b])
    j.enable_assumption(a)
    j.enable_assumption(b)
    assert c.is_in
    j.retract_assumption(a)
    assert c.is_in  # re-derived from b
    j.retract_assumption(b)
    assert c.is_out


def test_circular_support_is_not_well_founded():
    # b <= c and c <= b: with no independent ground, both stay OUT.
    j = JTMS()
    b = j.create_node("b")
    c = j.create_node("c")
    j.justify_node("c=>b", b, [c])
    j.justify_node("b=>c", c, [b])
    assert b.is_out and c.is_out
    # Add a real ground for b; now both become IN, grounded in the premise.
    j.justify_node("premise", b, [])
    assert b.is_in and c.is_in


def test_assumptions_of_node():
    j = JTMS()
    a = j.create_node("a", assumption=True)
    b = j.create_node("b", assumption=True)
    c = j.create_node("c")
    d = j.create_node("d")
    j.justify_node("a,b=>c", c, [a, b])
    j.justify_node("c=>d", d, [c])
    j.enable_assumption(a)
    j.enable_assumption(b)
    asns = set(j.assumptions_of_node(d))
    assert asns == {a, b}
    assert a.support is ENABLED_ASSUMPTION


def test_default_handler_raises_on_contradiction():
    j = JTMS()
    a = j.create_node("a", assumption=True)
    x = j.create_node("x", contradictory=True)
    j.justify_node("a=>x", x, [a])
    with pytest.raises(JTMSContradiction):
        j.enable_assumption(a)


def test_dependency_directed_backtracking_via_handler():
    retracted = []

    def handler(jtms, nodes):
        # Resolve by retracting one assumption underlying the contradiction.
        asns = jtms.assumptions_of_node(nodes[0])
        retracted.append(asns[0])
        jtms.retract_assumption(asns[0])

    j = JTMS(contradiction_handler=handler)
    a = j.create_node("a", assumption=True)
    b = j.create_node("b", assumption=True)
    x = j.create_node("x", contradictory=True)
    j.justify_node("a,b=>x", x, [a, b])
    j.enable_assumption(a)
    j.enable_assumption(b)  # triggers the contradiction + handler
    assert x.is_out
    assert len(retracted) == 1


def test_enable_assumption_requires_assumption_flag():
    j = JTMS()
    a = j.create_node("a")
    with pytest.raises(ValueError, match="not an assumption"):
        j.enable_assumption(a)


def test_premise_beats_enabled_assumption():
    j = JTMS()
    a = j.create_node("a", assumption=True)
    j.justify_node("premise", a, [])
    assert a.is_premise
    j.enable_assumption(a)  # no-op: premise wins
    assert a.is_premise
    assert a.support is not ENABLED_ASSUMPTION
