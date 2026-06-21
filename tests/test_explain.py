from ltms.core import LTMS, Label
from ltms.explain import explain_node, support_for_node, why_node
from ltms.normalize import add_formula


def _chain():
    m = LTMS()
    p, q, r = m.create_node("p"), m.create_node("q"), m.create_node("r")
    add_formula(m, ("implies", p, q))
    add_formula(m, ("implies", q, r))
    m.assume(p, Label.TRUE)
    return m, p, q, r


def test_why_node_assumption_and_derived():
    m, p, q, r = _chain()
    assert "assumption" in why_node(m, p)
    assert "<=" in why_node(m, q)  # derived from p


def test_support_for_node():
    m, p, q, r = _chain()
    ants, _informant = support_for_node(q)
    assert p in ants
    assert support_for_node(m.create_node("unknown")) is None


def test_explain_node_is_well_founded_order():
    m, p, q, r = _chain()
    proof = explain_node(m, r)
    # Proof lists p before q before r (antecedents precede consequents).
    joined = " | ".join(proof)
    assert joined.index("p") < joined.index("q") < joined.index("r")
    assert len(proof) == 3


def test_assumptions_of_node_through_chain():
    m, p, q, r = _chain()
    assert m.assumptions_of_node(r) == [p]
