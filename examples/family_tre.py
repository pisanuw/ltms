"""TRE example: derive ancestor relations by forward chaining.

Run: ``python examples/family_tre.py``
"""

from __future__ import annotations

from ltms.terms import Var
from ltms.tre import Tre

X, Y, Z = Var("x"), Var("y"), Var("z")


def main() -> list[tuple[object, ...]]:
    tre = Tre()

    # ancestor(x, y) :- parent(x, y)
    tre.add_rule(("parent", X, Y), lambda b, t: t.assert_(("ancestor", b[X], b[Y])))

    # ancestor(x, z) :- parent(x, y), ancestor(y, z)
    def chain(b, t):
        x = b[X]
        t.add_rule(("ancestor", b[Y], Z), lambda b2, t2: t2.assert_(("ancestor", x, b2[Z])))

    tre.add_rule(("parent", X, Y), chain)

    tre.run_forms(
        [("parent", "ann", "bob"), ("parent", "bob", "cy"), ("parent", "cy", "dee")]
    )

    ancestors = sorted(tre.fetch(("ancestor", X, Y)))
    print("Ancestors derived:")
    for a in ancestors:
        print(f"  {a[1]} is an ancestor of {a[2]}")
    return ancestors


if __name__ == "__main__":
    main()
