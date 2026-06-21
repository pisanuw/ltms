from ltms.terms import Var
from ltms.tre import Tre

X, Y, Z, N = Var("x"), Var("y"), Var("z"), Var("n")


def test_assert_is_dedup_and_reports_new():
    tre = Tre()
    assert tre.assert_(("p", "a")) is True
    assert tre.assert_(("p", "a")) is False  # already present
    assert tre.fetch(("p", X)) == [("p", "a")]


def test_assert_only_enqueues_until_run_rules():
    tre = Tre()
    fired = []
    tre.add_rule(("light", X), lambda b, t: fired.append(b[X]))
    tre.assert_(("light", "on"))
    assert fired == []  # matched, queued, not yet run
    tre.run_rules()
    assert fired == ["on"]


def test_single_rule_derivation():
    tre = Tre()
    tre.add_rule(("human", X), lambda b, t: t.assert_(("mortal", b[X])))
    tre.run_forms([("human", "socrates")])
    assert tre.fetch(("mortal", X)) == [("mortal", "socrates")]


def _install_grandparent(tre: Tre) -> None:
    def outer(b, t):
        x = b[X]
        t.add_rule(("parent", b[Y], Z), lambda b2, t2: t2.assert_(("grandparent", x, b2[Z])))

    tre.add_rule(("parent", X, Y), outer)


def test_conjunctive_nested_rule():
    tre = Tre()
    _install_grandparent(tre)
    tre.run_forms([("parent", "a", "b"), ("parent", "b", "c"), ("parent", "c", "d")])
    gps = sorted(tre.fetch(("grandparent", X, Y)))
    assert gps == [("grandparent", "a", "c"), ("grandparent", "b", "d")]


def test_order_independence_rule_after_facts():
    # Same result whether the rule is added before or after the facts.
    tre = Tre()
    for fact in [("parent", "a", "b"), ("parent", "b", "c"), ("parent", "c", "d")]:
        tre.assert_(fact)
    _install_grandparent(tre)
    tre.run_rules()
    gps = sorted(tre.fetch(("grandparent", X, Y)))
    assert gps == [("grandparent", "a", "c"), ("grandparent", "b", "d")]


def test_transitive_closure_ancestor():
    tre = Tre()
    # ancestor(x,y) :- parent(x,y)
    tre.add_rule(("parent", X, Y), lambda b, t: t.assert_(("ancestor", b[X], b[Y])))

    # ancestor(x,z) :- parent(x,y), ancestor(y,z)
    def chain(b, t):
        x = b[X]
        t.add_rule(("ancestor", b[Y], Z), lambda b2, t2: t2.assert_(("ancestor", x, b2[Z])))

    tre.add_rule(("parent", X, Y), chain)
    tre.run_forms([("parent", "a", "b"), ("parent", "b", "c"), ("parent", "c", "d")])
    anc = sorted(tre.fetch(("ancestor", X, Y)))
    assert anc == [
        ("ancestor", "a", "b"),
        ("ancestor", "a", "c"),
        ("ancestor", "a", "d"),
        ("ancestor", "b", "c"),
        ("ancestor", "b", "d"),
        ("ancestor", "c", "d"),
    ]


def test_bounded_recursion_with_guard():
    tre = Tre()

    def count_up(b, t):
        n = b[N]
        if isinstance(n, int) and n < 5:
            t.assert_(("count", n + 1))

    tre.add_rule(("count", N), count_up)
    tre.run_forms([("count", 0)])
    counts = sorted(c[1] for c in tre.fetch(("count", N)))
    assert counts == [0, 1, 2, 3, 4, 5]


def test_fetch_returns_substituted_copies():
    tre = Tre()
    tre.run_forms([("color", "sky", "blue"), ("color", "grass", "green")])
    assert sorted(tre.fetch(("color", X, "blue"))) == [("color", "sky", "blue")]
    assert sorted(tre.fetch(("color", X, Y))) == [
        ("color", "grass", "green"),
        ("color", "sky", "blue"),
    ]


def test_rules_run_counter():
    tre = Tre()
    tre.add_rule(("a", X), lambda b, t: None)
    tre.run_forms([("a", 1), ("a", 2), ("a", 3)])
    assert tre.rules_run == 3


def test_decorator_rule_form():
    tre = Tre()
    seen = []

    @tre.rule(("event", X))
    def _(b, t):
        seen.append(b[X])

    tre.run_forms([("event", "click")])
    assert seen == ["click"]
