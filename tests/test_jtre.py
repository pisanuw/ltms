from ltms.jtre import Condition, JTre
from ltms.terms import Var

X, Y, Z = Var("x"), Var("y"), Var("z")


def test_assert_premise_is_in():
    e = JTre()
    e.assert_(("weather", "sunny"))
    assert e.is_in(("weather", "sunny"))
    assert not e.is_in(("weather", "rainy"))


def test_in_rule_fires_after_belief():
    e = JTre()
    fired = []
    e.add_rule(("human", X), lambda b, t: fired.append(b[X]), condition=Condition.IN)
    # Datum exists but is not yet believed: rule is parked, not fired.
    e.referent(("human", "socrates"), create=True)
    e.run_rules()
    assert fired == []
    # Now make it believed; the parked rule wakes and fires.
    e.assert_(("human", "socrates"))
    e.run_rules()
    assert fired == ["socrates"]


def test_intern_rule_fires_on_existence():
    e = JTre()
    fired = []
    e.add_rule(("seen", X), lambda b, t: fired.append(b[X]), condition=Condition.INTERN)
    e.referent(("seen", "a"), create=True)
    e.run_rules()
    assert fired == ["a"]  # fired even though not believed


def test_forward_chaining_rule_justifies_conclusion():
    e = JTre()

    def mortal(b, t):
        t.justify("human=>mortal", ("mortal", b[X]), [("human", b[X])])

    e.add_rule(("human", X), mortal, condition=Condition.IN)
    e.assert_(("human", "socrates"))
    e.run_rules()
    assert e.is_in(("mortal", "socrates"))


def test_assume_and_retract_with_forward_rule():
    e = JTre()

    def deriving(b, t):
        t.justify("p=>q", ("q", b[X]), [("p", b[X])])

    e.add_rule(("p", X), deriving, condition=Condition.IN)
    e.assume(("p", "a"), "hypothesis")
    e.run_rules()
    assert e.is_in(("q", "a"))
    e.retract(("p", "a"), "hypothesis")
    assert e.is_out(("p", "a"))
    assert e.is_out(("q", "a"))  # conclusion withdrawn with its support


def test_dependency_directed_backtracking():
    retracted = []

    def handler(jtms, nodes):
        asns = jtms.assumptions_of_node(nodes[0])
        retracted.append(asns[0].datum.lisp_form)
        jtms.retract_assumption(asns[0])

    e = JTre()
    e.jtms.contradiction_handler = handler

    def both_bad(b, t):
        t.contradiction(("conflict",))
        t.justify("a,b=>conflict", ("conflict",), [("a",), ("b",)])

    # Build the contradiction once both a and b are believed.
    e.add_rule(("a",), both_bad, condition=Condition.IN)
    e.assume(("a",), "h1")
    e.run_rules()
    e.assume(("b",), "h2")
    e.run_rules()
    assert e.is_out(("conflict",))
    assert len(retracted) == 1


def test_fetch_and_why():
    e = JTre()
    e.assert_(("color", "sky", "blue"))
    assert e.fetch(("color", X, Y)) == [("color", "sky", "blue")]
    assert "IN" in e.why(("color", "sky", "blue"))
