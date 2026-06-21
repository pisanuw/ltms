import pytest

from ltms.cltms import complete, consensus, prime_implicates
from ltms.core import LTMS, Label, LTMSContradiction


def _lit(node, positive=True):
    return (node, Label.TRUE if positive else Label.FALSE)


def test_consensus_basic():
    m = LTMS()
    x, y = m.create_node("x"), m.create_node("y")
    c1 = frozenset({_lit(x), _lit(y, False)})  # x v ~y
    c2 = frozenset({_lit(x), _lit(y)})  # x v y
    assert consensus(c1, c2) == frozenset({_lit(x)})  # resolves on y -> x


def test_consensus_no_complementary_pair_returns_none():
    m = LTMS()
    x, y, z = (m.create_node(n) for n in "xyz")
    assert consensus(frozenset({_lit(x)}), frozenset({_lit(y), _lit(z)})) is None


def test_consensus_two_complementary_pairs_is_tautology():
    m = LTMS()
    x, y = m.create_node("x"), m.create_node("y")
    c1 = frozenset({_lit(x), _lit(y)})  # x v y
    c2 = frozenset({_lit(x, False), _lit(y, False)})  # ~x v ~y
    assert consensus(c1, c2) is None  # two complementary pairs -> tautology


def test_consensus_to_empty_clause():
    m = LTMS()
    x = m.create_node("x")
    assert consensus(frozenset({_lit(x)}), frozenset({_lit(x, False)})) == frozenset()


def test_prime_implicates_derives_unit():
    m = LTMS()
    x, y = m.create_node("x"), m.create_node("y")
    pis = prime_implicates([frozenset({_lit(x), _lit(y, False)}), frozenset({_lit(x), _lit(y)})])
    assert frozenset({_lit(x)}) in pis  # x is a prime implicate


def test_complete_makes_literal_completeness():
    # {x v ~y, x v y} entails x; plain BCP misses it, completion forces it.
    m = LTMS()
    x, y = m.create_node("x"), m.create_node("y")
    m.add_clause([x], [y], "x v ~y")
    m.add_clause([x, y], [], "x v y")
    assert x.label is Label.UNKNOWN  # incomplete before completion
    added = complete(m)
    assert added >= 1
    assert x.is_true  # now derived


def test_complete_detects_unsatisfiable_four_clause_set():
    # The four-clause set on {x, y} is UNSAT; completion must detect it.
    m = LTMS()
    x, y = m.create_node("x"), m.create_node("y")
    m.add_clause([], [x, y], "~x v ~y")
    m.add_clause([y], [x], "~x v y")
    m.add_clause([x], [y], "x v ~y")
    m.add_clause([x, y], [], "x v y")
    assert x.label is Label.UNKNOWN  # BCP alone cannot detect the conflict
    with pytest.raises(LTMSContradiction):
        complete(m)


def test_complete_is_idempotent_when_already_complete():
    m = LTMS()
    a = m.create_node("a")
    m.add_clause([a], [], "a")  # a single unit; already complete
    assert complete(m) == 0
