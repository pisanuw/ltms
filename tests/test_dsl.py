import pytest

from ltms.dsl import KBResult, load_kb, parse_expr
from ltms.terms import Var


def test_parse_simple_proposition():
    assert parse_expr("rain") == ("rain",)
    assert parse_expr("wet ground") == ("wet", "ground")
    assert parse_expr("sprinkler on") == ("sprinkler", "on")


def test_parse_implication_and_precedence():
    assert parse_expr("rain -> wet ground") == ("implies", ("rain",), ("wet", "ground"))
    # & binds tighter than ->
    assert parse_expr("a & b -> c") == ("implies", ("and", ("a",), ("b",)), ("c",))
    # | binds tighter than ->, looser than &
    assert parse_expr("a | b & c") == ("or", ("a",), ("and", ("b",), ("c",)))


def test_parse_negation_and_parens():
    assert parse_expr("~ rain") == ("not", ("rain",))
    assert parse_expr("(a -> b) & c") == ("and", ("implies", ("a",), ("b",)), ("c",))


def test_parse_variables():
    assert parse_expr("human ?x") == ("human", Var("x"))


def test_kb_assert_and_query():
    kb = """
    # background theory
    rain -> wet ground
    sprinkler on -> wet ground
    assume rain
    query wet ground
    """
    result = load_kb(kb)
    assert ("wet ground", "true") in result.queries


def test_kb_belief_revision():
    kb = """
    rain -> wet ground
    sprinkler on -> wet ground
    assume rain
    assume sprinkler on
    retract rain
    expect wet ground true       # sprinkler still supports it
    retract sprinkler on
    expect wet ground unknown    # nothing supports it now
    """
    result = load_kb(kb)
    assert result.engine is not None
    assert result.engine.is_unknown(("wet", "ground"))


def test_kb_disjunction_resolution():
    result = load_kb("p | q\n~ p\nexpect q true\nexpect p false\n")
    assert ("q", "true") in result.queries


def test_kb_contradiction_declaration():
    # Declaring a, b mutually exclusive; asserting a forces b false.
    kb = "contradiction a, b\na\nexpect a true\nexpect b false\n"
    result = load_kb(kb)
    assert result.engine is not None
    assert result.engine.is_false(("b",))


def test_kb_universal_rule():
    kb = """
    rule (human ?x) => (mortal ?x)
    human socrates
    expect mortal socrates true
    """
    load_kb(kb)


def test_kb_conjunctive_rule():
    kb = """
    rule (parent ?x ?y) & (parent ?y ?z) => (grandparent ?x ?z)
    parent ann bob
    parent bob cy
    expect grandparent ann cy true
    """
    load_kb(kb)


def test_kb_taxonomy_directive():
    kb = """
    taxonomy red, green, blue
    assume red
    expect red true
    expect green false
    expect blue false
    """
    load_kb(kb)


def test_kb_complete_directive():
    # {x v ~y, x v y} entails x; BCP misses it until `complete` adds implicates.
    kb = """
    x | ~ y
    x | y
    expect x unknown
    complete
    expect x true
    """
    result = load_kb(kb)
    assert result.clauses_added >= 1


def test_expect_failure_raises():
    with pytest.raises(AssertionError, match="expect failed"):
        load_kb("rain\nexpect rain false\n")


def test_kb_result_type():
    assert isinstance(load_kb("query rain\n"), KBResult)
