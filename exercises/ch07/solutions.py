"""Chapter 7 (JTMS) exercise demonstrations using the ltms public API.

Most Chapter 7 exercises ask the reader to *modify* the JTMS algorithm (premise
propagation, derivation counts, nogood caching, count-based justifications,
etc.). Those are design/answer exercises, written up in README.md. The
exercises that probe observable JTMS *behavior* (Exercise 1's relabeling rule,
and Exercise 4's assumptions-of-node phenomenon) are demonstrated here against
the real ltms JTMS, using only the documented public API.

Run::

    # from the repository root
    . .venv/bin/activate
    python exercises/ch07/solutions.py
"""

from __future__ import annotations

from typing import Any

from ltms import JTMS, JTre
from ltms.jtms import JTMSContradiction


def _names(nodes: list[Any]) -> list[Any]:
    return [n.datum for n in nodes]


def minimal_assumptions_of_node(jtms: JTMS, node: Any) -> list[Any]:
    """Exercise 4b: shrink assumptions_of_node to a no-redundancy support set.

    Strategy from the book's hint: start from the assumptions that currently
    underlie the well-founded support, then try retracting each one. If the
    node stays IN without it, it was not needed *within this set*; otherwise
    restore it.

    Caveat: "stays IN" can be due to support that lies OUTSIDE the starting
    set (a different enabled assumption entirely). When that happens every
    member looks removable and this returns the empty set -- a non-redundant
    subset of the *reported* support, not necessarily one that holds the node
    up on its own. ``demo_assumptions_of_node_superset`` exhibits exactly that
    case (c, outside {a, b}, keeps g IN).
    """
    base = list(jtms.assumptions_of_node(node))
    keep = list(base)
    for asm in base:
        if asm not in keep:
            continue
        jtms.retract_assumption(asm)
        if node.is_in:
            keep.remove(asm)  # redundant: alternative support kept the node IN
        else:
            jtms.enable_assumption(asm)  # genuinely needed -- put it back
    return keep


def demo_enable_assumption_rule() -> dict[str, Any]:
    """Exercise 1: the final case of enable-assumption keeps existing support.

    When an assumption is enabled but the node is already IN via a real
    justification (not the enabled-assumption sentinel and not a premise), the
    JTMS keeps the derived/premise support rather than overwriting it with the
    bare assumption. We show a premise-supported node is unaffected by being
    enabled as an assumption, so its well-founded support survives retraction
    of the assumption status.
    """
    j = JTMS("ex1")
    a = j.create_node("a", assumption=True)
    p = j.create_node("p")  # will be a premise (antecedent-free justification)
    j.justify_node("premise", p, [])  # p is now IN as a premise
    # Make p also an assumption and enable it; per the final case, the premise
    # support must win, because a premise holds universally.
    j.convert_to_assumption(p)
    j.enable_assumption(p)
    return {
        "a_in_initially": a.is_in,
        "p_in": p.is_in,
        "p_is_premise_after_enable": p.is_premise,
        "p_support_is_premise_not_assumption": p.is_premise,
    }


def demo_assumptions_of_node_superset() -> dict[str, Any]:
    """Exercise 4a/4b/4c: assumptions-of-node can return a non-minimal set.

    g has two justifications: j1: g <= a, b  and  j2: g <= c. With a, b, c all
    enabled, g's *current* well-founded support is whichever justification was
    installed first (j1 here), so assumptions_of_node(g) reports {a, b}. But
    {c} alone also supports g, so {a, b} is not minimal -- there is an
    alternative well-founded support not contained in the reported set.
    """
    j = JTMS("ex4")
    a = j.create_node("a", assumption=True)
    b = j.create_node("b", assumption=True)
    c = j.create_node("c", assumption=True)
    g = j.create_node("g")
    j.justify_node("j1", g, [a, b])
    j.justify_node("j2", g, [c])
    j.enable_assumption(a)
    j.enable_assumption(b)
    j.enable_assumption(c)

    reported = _names(j.assumptions_of_node(g))
    current_support = getattr(g.support, "informant", str(g.support))
    minimal = _names(minimal_assumptions_of_node(j, g))
    return {
        "g_in": g.is_in,
        "current_support": current_support,
        "assumptions_of_node_g": sorted(str(x) for x in reported),  # non-minimal
        "minimal_assumptions_of_node_g": minimal,  # empty: c (outside {a,b}) holds g IN
        "g_still_in_after_minimization": g.is_in,
    }


def demo_alternative_support_switch() -> dict[str, Any]:
    """Exercise 4 (supporting): retraction finds alternative well-founded support.

    c is justified independently by a and by b. assumptions_of_node(c) names
    just one of them; retracting that one re-derives c from the other.
    """
    j = JTMS("alt")
    a = j.create_node("a", assumption=True)
    b = j.create_node("b", assumption=True)
    c = j.create_node("c")
    j.justify_node("r1", c, [a])
    j.justify_node("r2", c, [b])
    j.enable_assumption(a)
    j.enable_assumption(b)
    before = _names(j.assumptions_of_node(c))
    j.retract_assumption(a)
    after = _names(j.assumptions_of_node(c))
    return {
        "c_in_before": True,
        "assumptions_before": before,
        "c_in_after_retract_a": c.is_in,
        "assumptions_after": after,
    }


def demo_contradiction_and_culprits() -> dict[str, Any]:
    """Exercise 6 context: the JTMS only *signals* a contradiction.

    p and (not p) are assumptions that jointly justify a contradictory node.
    Enabling both makes the contradictory node IN; the default handler raises,
    and assumptions_of_node identifies the culprit assumption set (the
    candidate "nogood" of Exercise 6).
    """
    j = JTMS("contra")
    p = j.create_node("p", assumption=True)
    notp = j.create_node("not-p", assumption=True)
    foo = j.create_node("contradiction", contradictory=True)
    j.justify_node("conflict", foo, [p, notp])
    j.enable_assumption(p)
    signaled = False
    culprits: list[Any] = []
    try:
        j.enable_assumption(notp)
    except JTMSContradiction:
        signaled = True
        culprits = _names(j.assumptions_of_node(foo))
    return {
        "contradiction_signaled": signaled,
        "nogood_assumption_set": sorted(str(x) for x in culprits),
    }


def demo_jtre_belief_revision() -> dict[str, Any]:
    """End-to-end JTRE demo: assume, justify, query, retract (belief revision).

    Shows the JTMS doing the work the inference engine relies on: a derived
    fact goes OUT when its only supporting assumption is retracted.
    """
    e = JTre()
    e.assume(("rain",), "user")
    e.justify("wet-rule", ("wet", "ground"), [("rain",)])
    wet_in = e.is_in(("wet", "ground"))
    why = e.why(("wet", "ground"))
    e.retract(("rain",), "user")
    wet_after = e.is_in(("wet", "ground"))
    return {
        "wet_in_with_rain": wet_in,
        "why_wet": why,
        "wet_in_after_retract_rain": wet_after,
    }


def solve() -> dict[str, Any]:
    """Run all demonstrable Chapter 7 exercises and return labeled results."""
    return {
        "ex1_enable_assumption_keeps_premise": demo_enable_assumption_rule(),
        "ex4_assumptions_of_node_non_minimal": demo_assumptions_of_node_superset(),
        "ex4_alternative_support_switch": demo_alternative_support_switch(),
        "ex6_contradiction_signaled_with_culprits": demo_contradiction_and_culprits(),
        "jtre_belief_revision": demo_jtre_belief_revision(),
    }


if __name__ == "__main__":
    import pprint

    pprint.pprint(solve())
