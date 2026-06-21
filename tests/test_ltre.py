from ltms.core import avoid_all
from ltms.ltre import LTRE, Trigger
from ltms.terms import Var

X = Var("x")


def test_assert_simple_is_true():
    e = LTRE()
    e.assert_(("weather", "sunny"))
    assert e.is_true(("weather", "sunny"))
    assert e.is_unknown(("weather", "rainy"))


def test_propositional_disjunction_resolution():
    e = LTRE()
    e.assert_(("or", ("p",), ("q",)))  # p v q
    e.assert_(("not", ("p",)))  # ~p  -> forces q
    assert e.is_true(("q",))
    assert e.is_false(("p",))
    assert e.is_true(("not", ("p",)))  # negation read by inverting the label


def test_implication_formula():
    e = LTRE()
    e.assert_(("implies", ("rain",), ("wet",)))
    e.assert_(("rain",))
    assert e.is_true(("wet",))


def test_true_rule_parks_then_fires():
    e = LTRE()
    fired: list[object] = []
    e.add_rule(("human", X), lambda b, t: fired.append(b[X]), condition=Trigger.TRUE)
    # Datum exists but not yet believed -> parked.
    e.referent(("human", "socrates"), create=True)
    e.run_rules()
    assert fired == []
    e.assert_(("human", "socrates"))
    e.run_rules()
    assert fired == ["socrates"]


def test_intern_rule_fires_on_existence():
    e = LTRE()
    fired: list[object] = []
    e.add_rule(("seen", X), lambda b, t: fired.append(b[X]), condition=Trigger.INTERN)
    e.referent(("seen", "a"), create=True)
    e.run_rules()
    assert fired == ["a"]


def test_forward_chaining_rule():
    e = LTRE()
    e.add_rule(
        ("human", X),
        lambda b, t: t.assert_(("mortal", b[X])),
        condition=Trigger.TRUE,
    )
    e.uassert(("human", "socrates"))
    assert e.is_true(("mortal", "socrates"))


def test_assume_and_retract_simple():
    e = LTRE()
    e.assume(("p",), "hyp")
    assert e.is_true(("p",))
    e.retract(("p",), "hyp")
    assert e.is_unknown(("p",))


def test_assume_negated_simple():
    e = LTRE()
    e.assume(("not", ("rain",)), "hyp")
    assert e.is_false(("rain",))
    assert e.is_true(("not", ("rain",)))


def test_assume_compound_formula_with_guard():
    e = LTRE()
    e.assume(("implies", ("a",), ("b",)), "hyp")  # guarded implication
    e.assert_(("a",))
    assert e.is_true(("b",))
    e.retract(("implies", ("a",), ("b",)), "hyp")
    assert e.is_true(("a",))  # a is its own premise
    assert e.is_unknown(("b",))  # implication withdrawn -> b loses support


def test_retract_restores_derived_conclusion():
    e = LTRE()
    e.assert_(("implies", ("p",), ("q",)))
    e.assume(("p",), "hyp")
    assert e.is_true(("q",))
    e.retract(("p",), "hyp")
    assert e.is_unknown(("p",))
    assert e.is_unknown(("q",))


def test_fetch_patterns():
    e = LTRE()
    e.assert_(("color", "sky", "blue"))
    e.assert_(("color", "grass", "green"))
    assert sorted(e.fetch(("color", X, Var("y")))) == [
        ("color", "grass", "green"),
        ("color", "sky", "blue"),
    ]


def test_ltre_contradiction_with_avoid_all():
    e = LTRE()
    e.assume(("a",), "h1")
    e.assume(("b",), "h2")
    with e.ltms.with_contradiction_handler(avoid_all):
        e.contradiction([("a",), ("b",)])  # a and b cannot both hold
    assert not (e.is_true(("a",)) and e.is_true(("b",)))


def test_rule_test_guard():
    e = LTRE()
    fired: list[object] = []
    e.add_rule(
        ("n", X),
        lambda b, t: fired.append(b[X]),
        condition=Trigger.TRUE,
        test=lambda b: isinstance(b[X], int) and b[X] > 0,
    )
    e.uassert(("n", 5))
    e.uassert(("n", -3))
    assert fired == [5]
