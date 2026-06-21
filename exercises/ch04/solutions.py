"""Solutions / demonstrations for Chapter 4 (Pattern-Directed Inference, TRE/TRE).

Forbus & de Kleer, *Building Problem Solvers*, chapter 4 exercises.

This chapter's substrate (the TRE pattern-directed engine and its LTMS-backed
sibling LTRE) is implemented in the ``ltms`` package, so several exercises can
be demonstrated directly instead of only argued on paper. Each ``demo_*``
function below corresponds to one exercise and returns a small labeled result;
``solve()`` collects them all into one dict.

Run:
    cd /Users/pisan/bitbucket/pisanuw/ltms
    . .venv/bin/activate
    python exercises/ch04/solutions.py

Only the public ``ltms`` API is used.
"""

from __future__ import annotations

from typing import Any

from ltms import (
    FAIL,
    LTRE,
    Tre,
    Trigger,
    Var,
    substitute,
    try_indirect_proof,
    unify,
)

# Shared logic variables (BPS reuses ?x ?y ?z across rules; Var equality is by name).
X, Y, Z = Var("x"), Var("y"), Var("z")


# --------------------------------------------------------------------------- #
# Ex 1 -- order-independence (paper). We *demonstrate* the property by adding a
# rule before its triggering fact in one engine and after it in another, then
# showing the conclusions are identical.
# --------------------------------------------------------------------------- #
def demo_order_independence() -> dict[str, Any]:
    """Same facts + rule, two arrival orders, identical conclusions."""

    def build(rule_first: bool) -> Tre:
        t = Tre()
        add_fact = lambda: t.assert_(("human", "socrates"))  # noqa: E731
        add_rule = lambda: t.add_rule(  # noqa: E731
            ("human", X), lambda b, e: e.assert_(("mortal", b[X]))
        )
        if rule_first:
            add_rule()
            add_fact()
        else:
            add_fact()
            add_rule()
        t.run_rules()
        return t

    rule_first = build(rule_first=True).fetch(("mortal", X))
    fact_first = build(rule_first=False).fetch(("mortal", X))
    return {
        "rule_added_first": rule_first,
        "fact_added_first": fact_first,
        "identical": rule_first == fact_first,
    }


# --------------------------------------------------------------------------- #
# Ex 2 -- solve a logic-textbook problem with the natural-deduction machinery.
# Problem: (A v B), (A -> C), (B -> C)  |-  C   (constructive dilemma).
# LTRE/LTMS gives us modus ponens for free; C requires reasoning by cases,
# which the indirect-proof facility supplies.
# --------------------------------------------------------------------------- #
def demo_natural_deduction() -> dict[str, Any]:
    """Modus ponens directly; proof-by-cases (constructive dilemma) via indirect proof."""
    e = LTRE()
    # Direct modus-ponens chain: man(socrates), man(x)->mortal(x).
    e.assert_(("implies", ("man", "socrates"), ("mortal", "socrates")))
    e.assert_(("man", "socrates"))
    mp = e.is_true(("mortal", "socrates"))

    # Constructive dilemma needs case analysis, not just unit propagation.
    e2 = LTRE()
    e2.assert_(("or", ("a",), ("b",)))
    e2.assert_(("implies", ("a",), ("c",)))
    e2.assert_(("implies", ("b",), ("c",)))
    before = e2.is_true(("c",))  # not yet derivable by BCP alone
    proved = try_indirect_proof(e2, ("c",))
    return {
        "modus_ponens_mortal_socrates": mp,
        "c_before_indirect_proof": before,
        "c_proved_by_cases": proved,
        "c_now_true": e2.is_true(("c",)),
    }


# --------------------------------------------------------------------------- #
# Ex 3 -- full unification when BOTH patterns contain variables.
# The package's unify already does this correctly (Robinson with occurs-check),
# so we exhibit the cases the exercise warns about.
# --------------------------------------------------------------------------- #
def demo_full_unify() -> dict[str, Any]:
    """(Foo ?x ?x) vs (Foo ?y ?z): ?y and ?z must collapse to one variable."""
    fxx = ("Foo", X, X)
    fyz = ("Foo", Y, Z)
    b1 = unify(fxx, fyz)
    # After unification ?y is forced equal to ?z; substituting proves it.
    resolved = substitute(fyz, b1) if b1 is not FAIL else "FAIL"

    # The same-variable-both-sides case the exercise prints: (Foo ?x ?x) twice.
    b2 = unify(fxx, ("Foo", X, X))

    # A case that MUST fail because ?x cannot equal two distinct constants.
    b3 = unify(("Foo", X, X), ("Foo", "a", "b"))

    # A case that succeeds binding ?x once and reusing it consistently.
    b4 = unify(("Foo", X, X), ("Foo", "a", "a"))

    # Occurs-check: ?x = (g ?x) must be refused (no infinite term).
    b5 = unify(X, ("g", X))
    return {
        "foo_xx_vs_foo_yz_bindings": str(b1),
        "yz_collapsed_to_single_var": str(resolved),  # ('Foo', ?z, ?z)
        "same_var_both_sides_ok": b2 is not FAIL,
        "x_eq_a_and_b_fails": b3 is FAIL,
        "x_eq_a_twice_ok": b4 is not FAIL,
        "occurs_check_refuses_cycle": b5 is FAIL,
    }


# --------------------------------------------------------------------------- #
# Ex 4 -- multi-fetch: given several patterns, return the sets of assertions
# that jointly match (with consistent variable bindings across patterns).
# --------------------------------------------------------------------------- #
def multi_fetch(engine: Tre, patterns: list[tuple]) -> list[dict[Var, Any]]:
    """Return every binding environment under which ALL patterns match.

    This is the join of single-pattern fetches with shared variables, i.e. the
    cross-product filtered by unification consistency.
    """
    envs: list[dict[Var, Any]] = [{}]
    for pat in patterns:
        nxt: list[dict[Var, Any]] = []
        for env in envs:
            grounded = substitute(pat, env)
            for fact in engine.get_dbclass(grounded).facts:
                res = unify(grounded, fact, dict(env))
                if res is not FAIL:
                    nxt.append(res)  # type: ignore[arg-type]
        envs = nxt
    return envs


def demo_multi_fetch() -> dict[str, Any]:
    """Find x who is both a parent and employed (two patterns, shared ?x)."""
    t = Tre()
    for f in [
        ("parent", "ann", "bob"),
        ("parent", "cy", "dee"),
        ("employed", "ann"),
        ("employed", "ed"),
    ]:
        t.assert_(f)
    envs = multi_fetch(t, [("parent", X, Y), ("employed", X)])
    # Each env binds ?x (and ?y) to a consistent solution.
    solutions = sorted((env[X], env[Y]) for env in envs)
    return {"joint_parent_and_employed": solutions}  # [('ann', 'bob')]


# --------------------------------------------------------------------------- #
# Ex 5 -- show-rule: look a rule up by its counter and describe it. Rule objects
# returned by add_rule expose counter / trigger / condition / environment.
# --------------------------------------------------------------------------- #
def show_rule(engine: LTRE, counter: int) -> str | None:
    """Render a human-readable description of the rule whose counter == n."""
    for bucket in engine.dbclass_table.values():
        for rule in bucket.rules:
            if rule.counter == counter:
                trigger = rule.trigger
                env = rule.environment or "(empty)"
                cond = getattr(rule.condition, "name", str(rule.condition))
                return (
                    f"Rule #{rule.counter}\n"
                    f"  trigger:     {trigger}\n"
                    f"  fires when:  {cond}\n"
                    f"  environment: {env}\n"
                    f"  indexed under dbclass: {rule.dbclass.name}"
                )
    return None


def demo_show_rule() -> dict[str, Any]:
    """Install a rule, then describe it by its integer counter."""
    e = LTRE()
    r = e.add_rule(
        ("implies", X, Y),
        lambda b, eng: None,
        condition=Trigger.TRUE,
    )
    return {"counter": r.counter, "description": show_rule(e, r.counter)}


# --------------------------------------------------------------------------- #
# Ex 6 -- "lazy" AND-INTRODUCTION: only look for the second conjunct after the
# first is established. We emulate the rule as a nested (conjunctive) rule: the
# outer rule fires on conjunct A; only inside its body do we install the rule
# that watches for conjunct B. If A is never proved, B is never even looked up.
# --------------------------------------------------------------------------- #
def demo_lazy_and_introduction() -> dict[str, Any]:
    """Nested rules so the 2nd conjunct is sought only after the 1st is proved."""

    def run(prove_first: bool) -> dict[str, Any]:
        e = LTRE()
        looked_for_second = {"count": 0}

        # Outer rule: when (proved a) appears, THEN install the watcher for b.
        def on_first(_b: dict, eng: LTRE) -> None:
            def on_second(_b2: dict, eng2: LTRE) -> None:
                looked_for_second["count"] += 1
                eng2.assert_(("and-holds", "a", "b"))

            eng.add_rule(("proved", "b"), on_second, condition=Trigger.INTERN)

        e.add_rule(("proved", "a"), on_first, condition=Trigger.INTERN)

        # b is always available; a only when prove_first is True.
        e.assert_(("proved", "b"))
        if prove_first:
            e.assert_(("proved", "a"))
        e.run_rules()
        return {
            "second_conjunct_examined": looked_for_second["count"],
            "conjunction_asserted": e.is_known(("and-holds", "a", "b")),
        }

    return {
        "first_conjunct_fails": run(prove_first=False),  # second never examined
        "first_conjunct_holds": run(prove_first=True),  # second examined, AND made
    }


# --------------------------------------------------------------------------- #
# Ex 7 -- blackboard knowledge sources (paper). We sketch the multi-KS idea by
# running two independent TRE engines as "knowledge sources" that communicate by
# posting facts to a shared blackboard list, with an explicit scheduler.
# --------------------------------------------------------------------------- #
def demo_blackboard_sketch() -> dict[str, Any]:
    """Two TRE knowledge sources cooperating through a shared blackboard."""
    blackboard: list[tuple] = []

    # KS1: turns raw observations into hypotheses.
    ks1 = Tre()
    ks1.add_rule(
        ("observed", X),
        lambda b, e: blackboard.append(("hypothesis", b[X])),
    )
    # KS2: confirms a hypothesis if corroborating evidence exists.
    ks2 = Tre()
    ks2.add_rule(
        ("hypothesis", X),
        lambda b, e: blackboard.append(("confirmed", b[X]))
        if e.fetch(("evidence", b[X]))
        else None,
    )

    # Scheduler: a controller cycles the KSs, draining the blackboard between
    # activations (this explicit control is what an opportunistic blackboard
    # adds on top of a plain TRE -- see the paper answer for ex 7a).
    ks1.assert_(("observed", "fire"))
    ks1.run_rules()
    for item in list(blackboard):  # post round-1 results into KS2
        ks2.assert_(item)
    ks2.assert_(("evidence", "fire"))
    ks2.run_rules()

    return {
        "blackboard": sorted(blackboard),
        "fire_confirmed": ("confirmed", "fire") in blackboard,
    }


def solve() -> dict[str, Any]:
    """Run every demonstrable Chapter 4 exercise and collect labeled results."""
    return {
        "ex1_order_independence": demo_order_independence(),
        "ex2_natural_deduction": demo_natural_deduction(),
        "ex3_full_unify": demo_full_unify(),
        "ex4_multi_fetch": demo_multi_fetch(),
        "ex5_show_rule": demo_show_rule(),
        "ex6_lazy_and_introduction": demo_lazy_and_introduction(),
        "ex7_blackboard_sketch": demo_blackboard_sketch(),
    }


if __name__ == "__main__":
    import pprint

    pprint.pprint(solve())
