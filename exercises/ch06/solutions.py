"""Chapter 6 -- Introduction to Truth Maintenance Systems.

Runnable demonstrations for the two Section 6.7 exercises. See README.md for the
paraphrased problem statements and full discussion.

Exercise 1 (*)  -- recording a multiplication as a TMS justification, and the
                   automatic invalidation that follows when an input is retracted.
Exercise 2 (**) -- the simplest justification-only TMS (a tiny self-contained
                   ``MiniTMS``), contrasted with the package's full JTMS/JTre.

Run::

    # from the repository root
    . .venv/bin/activate
    python exercises/ch06/solutions.py
"""

from __future__ import annotations

from typing import Any

from ltms import JTMS, JTre


# --------------------------------------------------------------------------- #
# Exercise 1: multiplication as TMS inference
# --------------------------------------------------------------------------- #
def ex1_multiplication_as_inference() -> dict[str, Any]:
    """Record ``x * y = z`` as a single justification and observe truth maintenance.

    The two inputs are assumptions; the product is the consequence of a
    ``multiply`` justification. Retracting an input automatically relabels the
    product ``OUT`` -- the TMS does the invalidation for us.
    """
    j = JTMS("ex1-multiply")
    x = j.create_node(("input", "x", 6), assumption=True)
    y = j.create_node(("input", "y", 7), assumption=True)
    z = j.create_node(("product", 42))

    j.enable_assumption(x)
    j.enable_assumption(y)
    # The multiplication step itself, recorded as antecedents => consequence.
    j.justify_node("multiply", z, [x, y])

    product_in = z.is_in
    why = j.why_node(z)
    # Which inputs does the cached product depend on?
    depends_on = sorted(str(n.datum) for n in j.assumptions_of_node(z))

    # Change an input: the TMS invalidates the cached product without us asking.
    j.retract_assumption(x)
    product_after_retract = z.is_in

    # Re-enable the input: the product becomes believed again via the same just.
    j.enable_assumption(x)
    product_after_reenable = z.is_in

    return {
        "product_in_after_multiply": product_in,        # True
        "why_product": why,
        "product_depends_on": depends_on,               # both inputs
        "product_in_after_retracting_x": product_after_retract,   # False
        "product_in_after_reenabling_x": product_after_reenable,  # True
        "moral": (
            "one justification caches the result, tracks its inputs, and is "
            "auto-invalidated on retraction; worth it only when demand >> change"
        ),
    }


# --------------------------------------------------------------------------- #
# Exercise 2: the simplest justification-only TMS
# --------------------------------------------------------------------------- #
class MiniTMS:
    """Minimal justification-only TMS: nodes carry just IN/OUT; justifications only.

    No premises, no assumptions, no contradictions, no retraction. Belief is
    monotone: ``seed`` marks a base node IN, ``justify`` adds an
    ``antecedents => consequence`` clause, and both run a forward closure that
    can only flip nodes OUT -> IN.
    """

    def __init__(self) -> None:
        self._label: list[bool] = []                         # is_in per node id
        self._data: list[Any] = []
        self._justs: list[tuple[int, tuple[int, ...]]] = []  # (conseq, antecedents)

    def node(self, datum: Any) -> int:
        self._label.append(False)
        self._data.append(datum)
        return len(self._label) - 1

    def is_in(self, n: int) -> bool:
        return self._label[n]

    def _close(self) -> None:
        """Forward sweep to a fixpoint: a node is IN if some just is satisfied."""
        changed = True
        while changed:
            changed = False
            for conseq, ants in self._justs:
                if not self._label[conseq] and all(self._label[a] for a in ants):
                    self._label[conseq] = True
                    changed = True

    def seed(self, n: int) -> None:
        """Mark a base node IN (the only way belief enters this minimal TMS)."""
        if not self._label[n]:
            self._label[n] = True
            self._close()

    def justify(self, conseq: int, antecedents: list[int]) -> None:
        self._justs.append((conseq, tuple(antecedents)))
        self._close()


def ex2_minimal_tms() -> dict[str, Any]:
    """A 30-line justification-only TMS, plus the same job via the full JTMS/JTre.

    The minimal engine grows belief monotonically and never retracts. The full
    JTMS/JTre is a strict superset: it adds premises, assumptions, two-phase
    retraction with alternative-support recovery, and contradiction signalling.
    """
    # --- the minimal justification-only TMS ------------------------------- #
    m = MiniTMS()
    a = m.node("a")
    b = m.node("b")
    c = m.node("c")  # goal
    m.justify(c, [a, b])                 # a, b => c
    before = m.is_in(c)                  # OUT: nothing seeded yet
    m.seed(a)
    after_a = m.is_in(c)                 # still OUT: b not yet IN
    m.seed(b)
    after_b = m.is_in(c)                 # now IN: both antecedents IN

    mini = {
        "c_in_before_seeding": before,   # False
        "c_in_after_seeding_a_only": after_a,  # False
        "c_in_after_seeding_a_and_b": after_b,  # True
    }

    # --- the same conclusion in the package's full JTMS -------------------- #
    j = JTMS("ex2-jtms")
    ja = j.create_node("a", assumption=True)
    jb = j.create_node("b", assumption=True)
    jc = j.create_node("c")
    j.enable_assumption(ja)
    j.enable_assumption(jb)
    j.justify_node("a,b=>c", jc, [ja, jb])
    jtms_goal_in = jc.is_in             # True

    # --- the capability the minimal TMS lacks: retraction with re-derivation #
    # JTre wraps the JTMS as a fact engine. Give the goal two independent
    # justifications and watch belief survive retracting one of them.
    e = JTre("ex2-jtre")
    e.assume(("p",), "route1")
    e.justify("goal-from-p", ("goal",), [("p",)])
    e.assume(("q",), "route2")
    e.justify("goal-from-q", ("goal",), [("q",)])
    goal_in = e.is_in(("goal",))                       # True
    e.retract(("p",), "route1")
    goal_after_retract_p = e.is_in(("goal",))          # True: re-derived via q
    why_after = e.why(("goal",))
    e.retract(("q",), "route2")
    goal_after_retract_both = e.is_in(("goal",))       # False: no support left

    full = {
        "jtms_goal_in": jtms_goal_in,
        "jtre_goal_in": goal_in,
        "jtre_goal_in_after_retract_p": goal_after_retract_p,
        "jtre_why_after_retract_p": why_after,
        "jtre_goal_in_after_retract_both": goal_after_retract_both,
        "note": (
            "MiniTMS cannot do the last three lines: it has no retraction. "
            "Justification-only TMS fits monotone, append-only reasoning."
        ),
    }

    return {"mini_tms": mini, "full_jtms_jtre": full}


def solve() -> dict:
    """Run the demonstrated Chapter 6 exercises and return labeled results."""
    return {
        "ex1_multiplication_as_inference": ex1_multiplication_as_inference(),
        "ex2_minimal_tms": ex2_minimal_tms(),
    }


if __name__ == "__main__":
    import pprint

    pprint.pprint(solve())
