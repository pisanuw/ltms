"""Chapter 8 (Putting the JTMS to Work) -- runnable demonstrations.

The chapter's running systems are JTRE (a JTMS-backed pattern-directed rule
engine) and JSAINT (a symbolic-integration problem solver built on JTRE).  The
``ltms`` package implements the truth-maintenance + rule-engine substrate
(JTMS / JTre / Tre / LTRE), so the exercises that probe rule-engine *mechanics*
can be demonstrated directly.  JSAINT itself is not implemented in the package,
so the JSAINT-specific exercises (6-16) are answered in prose in README.md.

Only the public API listed in the assignment is used.

Run:
    # from the repository root
    . .venv/bin/activate
    python exercises/ch08/solutions.py
"""

from __future__ import annotations

from typing import Any

from ltms import JTre, Tre, Var

X = Var("x")
Y = Var("y")
N = Var("n")
F = Var("f")


# --------------------------------------------------------------------------- #
# Exercise 1a -- the two disasters a careless :TEST option can cause.
#
# The original rule used a :TEST whose body called (fetch '(using trap-door-code))
# inside the trigger.  Two failure modes:
#   (1) Non-termination / unbounded work / side effects: the test runs arbitrary
#       code during matching, so a buggy or expensive test stalls the matcher.
#   (2) Incorrect / non-monotonic belief: a :TEST that consults the *current*
#       database (fetch) is not a function of the trigger bindings, so whether
#       the rule fires depends on assertion ORDER, and the conclusion is not
#       retracted when the consulted fact later goes away (no dependency link).
#
# We demonstrate disaster (2): an order-dependent, dependency-blind test.
# --------------------------------------------------------------------------- #
def _ex1a_unsafe_test() -> dict[str, Any]:
    out: dict[str, Any] = {}

    # --- Order A: the consulted fact arrives BEFORE the trigger. ---
    e1 = JTre()
    fired_a: list[Any] = []

    # Unsafe test: peeks at the live database instead of only at the bindings.
    e1.add_rule(
        ("prime-number", N),
        lambda b, t: fired_a.append(b[N]),
        # condition IN; the "test" is faked here as a body-side db peek
    )

    def gate_a(b: dict[Var, Any], t: JTre) -> None:
        if t.is_in(("using", "trap-door-code")):  # database peek == unsafe :TEST
            t.justify("suggest", ("suggest-code-key", b[N]), [("prime-number", b[N])])

    e1.add_rule(("prime-number", N), gate_a)
    e1.assert_(("using", "trap-door-code"))
    e1.run_rules()
    e1.assert_(("prime-number", 7))
    e1.run_rules()
    out["orderA_suggested"] = e1.is_in(("suggest-code-key", 7))

    # --- Order B: identical asserts, reversed order -> different belief. ---
    e2 = JTre()
    e2.add_rule(
        ("prime-number", N),
        lambda b, t: (
            t.justify("suggest", ("suggest-code-key", b[N]), [("prime-number", b[N])])
            if t.is_in(("using", "trap-door-code"))
            else None
        ),
    )
    e2.assert_(("prime-number", 7))
    e2.run_rules()
    e2.assert_(("using", "trap-door-code"))  # arrives too late
    e2.run_rules()
    out["orderB_suggested"] = e2.is_in(("suggest-code-key", 7))

    # The bug: same facts, opposite conclusions => order-dependent (disaster 2).
    out["order_dependent_bug"] = out["orderA_suggested"] != out["orderB_suggested"]
    return out


# --------------------------------------------------------------------------- #
# Exercise 3 -- conjunctive triggers: fire only when ALL belief conditions of
# the triggers hold simultaneously.
#
# JTre's primitive is a single-trigger rule.  A conjunctive ((:IN p)(:IN q))
# rule is expressed by *nesting*: the outer rule on p installs an inner rule on
# q that captures p's bindings.  Because both inner and outer fire under
# Condition.IN, the body runs only when both p and q are believed -- and if
# either later goes OUT, the JTMS withdraws the justified conclusion.
# --------------------------------------------------------------------------- #
def _ex3_conjunctive_trigger() -> dict[str, Any]:
    e = JTre()
    fired: list[tuple[Any, Any]] = []

    def on_foo(b: dict[Var, Any], t: JTre) -> None:
        x = b[X]

        def on_bar(_b2: dict[Var, Any], t2: JTre) -> None:
            # trigger ("bar", x) is fully ground in x, so reuse the captured x
            fired.append((x, x))
            t2.justify("foo&bar=>mumble", ("mumble", x), [("foo", x), ("bar", x)])

        # inner rule fires only when (bar x) is also believed IN
        t.add_rule(("bar", x), on_bar)

    e.add_rule(("foo", X), on_foo)

    e.assert_(("foo", "a"))
    e.run_rules()
    after_foo_only = e.is_in(("mumble", "a"))  # bar not yet present
    e.assert_(("bar", "a"))
    e.run_rules()
    after_both = e.is_in(("mumble", "a"))  # now both hold

    return {
        "mumble_after_foo_only": after_foo_only,  # expect False
        "mumble_after_both": after_both,  # expect True
        "conjunction_fired": fired,  # [("a","a")]
    }


# --------------------------------------------------------------------------- #
# Exercise 4 -- one-shot rules: a fully ground trigger like (bar A) can match at
# most one fact, so the rule struct should be discarded after it fires.
#
# We emulate the optimisation: a body that de-registers itself by guarding on a
# "done" flag, so a second matching fact does no work.  We measure body
# invocations to show the rule fires exactly once.
# --------------------------------------------------------------------------- #
def _ex4_one_shot_rule() -> dict[str, Any]:
    e = JTre()
    calls = {"n": 0}
    done = {"flag": False}

    def on_foo(b: dict[Var, Any], t: JTre) -> None:
        x = b[X]

        def on_bar(b2: dict[Var, Any], t2: JTre) -> None:
            if done["flag"]:  # one-shot guard: ignore further matches
                return
            done["flag"] = True
            calls["n"] += 1
            t2.justify("g", ("mumble", x), [("foo", x), ("bar", x)])

        # trigger is fully ground in x: at most one (bar <x>) can ever match
        t.add_rule(("bar", x), on_bar)

    e.add_rule(("foo", X), on_foo)
    e.assert_(("foo", "a"))
    e.run_rules()
    e.assert_(("bar", "a"))
    e.run_rules()
    # A second, equal assertion is deduped at the datum level; re-justify anyway:
    e.justify("dup", ("bar", "a"), [])
    e.run_rules()

    return {
        "mumble_in": e.is_in(("mumble", "a")),
        "body_invocations": calls["n"],  # exactly 1
    }


# --------------------------------------------------------------------------- #
# Exercise 4 (baseline, no optimisation) -- show that without the guard a rule
# struct *would* be re-attempted; we count match attempts in a plain Tre.
# A ground trigger only ever has one successful match, confirming the rule
# struct is dead weight afterwards (the point of the exercise).
# --------------------------------------------------------------------------- #
def _ex4_match_count() -> dict[str, Any]:
    t = Tre()
    matches: list[Any] = []
    t.add_rule(("bar", "a"), lambda b, eng: matches.append(True))
    t.assert_(("bar", "a"))
    t.run_rules()
    t.assert_(("bar", "b"))  # different fact: cannot match ground (bar a)
    t.run_rules()
    return {"successful_matches_for_ground_trigger": len(matches)}  # 1


# --------------------------------------------------------------------------- #
# Exercise 7 -- logical status of a control term like (integrate ...).
# Demonstration: control terms behave like ordinary believed propositions in
# the engine -- they are asserted, justified, and retracted exactly like domain
# facts.  We treat (integrate expr) as a node whose belief drives a method, then
# retract its support to show it is a first-class (object-level) proposition,
# supporting the "standard predicate" reading discussed in the README.
# --------------------------------------------------------------------------- #
def _ex7_control_term_is_proposition() -> dict[str, Any]:
    e = JTre()

    def method(b: dict[Var, Any], t: JTre) -> None:
        # firing a "control" goal justifies a result
        t.justify("polyterm", ("integral-result", b[X]), [("integrate", b[X])])

    e.add_rule(("integrate", X), method)
    e.assume(("integrate", "x^2"), "goal")
    e.run_rules()
    while_goal_in = e.is_in(("integral-result", "x^2"))
    e.retract(("integrate", "x^2"), "goal")
    after_goal_out = e.is_in(("integral-result", "x^2"))
    return {
        "result_while_goal_in": while_goal_in,  # True
        "result_after_goal_retracted": after_goal_out,  # False (TMS withdraws it)
    }


# --------------------------------------------------------------------------- #
# Exercise 11a -- a tiny symbolic differentiator written as match/Tre rules.
# This is the differentiation capability the u-substitution method needs.
# Expressions: ("const", c), ("var",), ("+", a, b), ("*", a, b), ("^", ("var",), n)
# We forward-derive ("deriv", expr) facts.
# --------------------------------------------------------------------------- #
def _ex11a_symbolic_diff() -> dict[str, Any]:
    t = Tre()
    A, B, C, NN = Var("a"), Var("b"), Var("c"), Var("nn")

    # d/dx const = 0
    def d_const(b: dict[Var, Any], eng: Tre) -> None:
        eng.assert_(("deriv", ("const", b[C]), ("const", 0)))

    t.add_rule(("d", ("const", C)), d_const)

    # d/dx x = 1
    def d_var(_b: dict[Var, Any], eng: Tre) -> None:
        eng.assert_(("deriv", ("var",), ("const", 1)))

    t.add_rule(("d", ("var",)), d_var)

    # d/dx (x^n) = n*x^(n-1)
    def d_power(b: dict[Var, Any], eng: Tre) -> None:
        n = int(b[NN])
        eng.assert_(
            (
                "deriv",
                ("^", ("var",), n),
                ("*", ("const", n), ("^", ("var",), n - 1)),
            )
        )

    t.add_rule(("d", ("^", ("var",), NN)), d_power)

    # sum rule: d(a+b) = da + db  (request sub-derivatives, then combine)
    def sum_rule(b: dict[Var, Any], eng: Tre) -> None:
        a, bb = b[A], b[B]
        eng.assert_(("d", a))
        eng.assert_(("d", bb))

        def combine(_bnd: dict[Var, Any], e2: Tre) -> None:
            da = e2.fetch(("deriv", a, Var("da")))
            db = e2.fetch(("deriv", bb, Var("db")))
            if da and db:
                da0, db0 = da[0], db[0]
                assert isinstance(da0, tuple) and isinstance(db0, tuple)
                e2.assert_(("deriv", ("+", a, bb), ("+", da0[2], db0[2])))

        eng.add_rule(("deriv", a, Var("da")), combine)
        eng.add_rule(("deriv", bb, Var("db")), combine)

    t.add_rule(("d", ("+", A, B)), sum_rule)

    # Differentiate x^3 + 5
    t.assert_(("d", ("+", ("^", ("var",), 3), ("const", 5))))
    t.run_rules()
    result = t.fetch(("deriv", ("+", ("^", ("var",), 3), ("const", 5)), Var("r")))
    answer = None
    if result:
        top = result[0]
        assert isinstance(top, tuple)
        answer = top[2]
    return {
        "deriv_x3_plus_5": answer,
        # expect ("+", ("*",("const",3),("^",("var",),2)), ("const",0))
    }


def solve() -> dict[str, Any]:
    """Run every implementable Chapter 8 exercise; return labeled results."""
    return {
        "ex1a_unsafe_test_order_dependence": _ex1a_unsafe_test(),
        "ex3_conjunctive_trigger": _ex3_conjunctive_trigger(),
        "ex4_one_shot_rule": _ex4_one_shot_rule(),
        "ex4_ground_trigger_match_count": _ex4_match_count(),
        "ex7_control_term_is_proposition": _ex7_control_term_is_proposition(),
        "ex11a_symbolic_differentiation": _ex11a_symbolic_diff(),
    }


if __name__ == "__main__":
    import pprint

    pprint.pprint(solve())
