"""DDS example: solve graph coloring by dependency-directed search.

Run: ``python examples/coloring_dds.py``
"""

from __future__ import annotations

from ltms.dds import dd_search
from ltms.ltre import LTRE

NODES = ["wa", "nt", "sa", "q"]
EDGES = [("wa", "nt"), ("wa", "sa"), ("nt", "sa"), ("nt", "q"), ("sa", "q")]
COLORS = ["red", "green", "blue"]


def main() -> list[tuple[tuple[str, str], ...]]:
    e = LTRE()
    for n in NODES:
        for c in COLORS:
            e.referent(("color", n, c), create=True)
    for u, v in EDGES:
        for c in COLORS:
            e.contradiction([("color", u, c), ("color", v, c)], informant="adjacent")

    choice_sets = [[("color", n, c) for c in COLORS] for n in NODES]

    def extract(eng):
        return tuple(
            (n, c) for n in NODES for c in COLORS if eng.is_true(("color", n, c))
        )

    solutions = dd_search(e, choice_sets, extract)
    print(f"Found {len(solutions)} proper colorings; first one:")
    if solutions:
        for n, c in solutions[0]:
            print(f"  {n}: {c}")
    return solutions


if __name__ == "__main__":
    main()
