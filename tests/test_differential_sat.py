"""Differential testing of BCP soundness against a real SAT solver (PySAT).

BCP is sound but incomplete, so we check only soundness:

* every literal the LTMS *forces* is genuinely entailed by the clause set, and
* every conflict the LTMS *detects* corresponds to an unsatisfiable prefix.

We make no completeness claims (the LTMS may leave entailed literals unknown).
Skipped automatically if PySAT is not installed.
"""

from __future__ import annotations

import pytest
from hypothesis import given, settings
from hypothesis import strategies as st

from ltms.core import LTMS, Label, LTMSContradiction

_pysat = pytest.importorskip("pysat.solvers")
Minisat22 = _pysat.Minisat22

_NVARS = 5


def _dimacs(var_index: int, positive: bool) -> int:
    return (var_index + 1) if positive else -(var_index + 1)


_clauses = st.lists(
    st.lists(
        st.tuples(st.integers(0, _NVARS - 1), st.booleans()),
        min_size=1,
        max_size=3,
        unique_by=lambda lit: lit[0],
    ),
    min_size=1,
    max_size=10,
)


@given(clauses=_clauses)
@settings(max_examples=300, deadline=None)
def test_bcp_is_sound_against_minisat(clauses) -> None:
    m = LTMS()
    nodes = [m.create_node(i) for i in range(_NVARS)]
    cnf: list[list[int]] = []
    contradiction = False

    for clause in clauses:
        cnf.append([_dimacs(i, pos) for i, pos in clause])
        trues = [nodes[i] for i, pos in clause if pos]
        falses = [nodes[i] for i, pos in clause if not pos]
        try:
            m.add_clause(trues, falses, "c")
        except LTMSContradiction:
            contradiction = True
            break

    if contradiction:
        # If the LTMS detected a conflict, the clauses really are unsatisfiable.
        with Minisat22(bootstrap_with=cnf) as solver:
            assert solver.solve() is False
        return

    # We do NOT assert the CNF is satisfiable here: BCP is refutation-incomplete,
    # so it may miss a real contradiction (e.g. the 4-clause set on two vars).
    # Soundness only: each literal the LTMS forced is genuinely entailed
    # (CNF & the negated literal is unsatisfiable).
    with Minisat22(bootstrap_with=cnf) as solver:
        for i, node in enumerate(nodes):
            if node.label is Label.TRUE:
                assert solver.solve(assumptions=[_dimacs(i, False)]) is False
            elif node.label is Label.FALSE:
                assert solver.solve(assumptions=[_dimacs(i, True)]) is False
