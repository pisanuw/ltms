"""Property-based checks of LTMS counter and support invariants (Hypothesis).

Across random clause sets and assume/retract sequences, the pvs/sats counters
must always equal what a fresh scan of the literals would compute, and every
node's support must be well-formed.
"""

from __future__ import annotations

import contextlib

from hypothesis import given, settings
from hypothesis import strategies as st

from ltms.core import ENABLED_ASSUMPTION, LTMS, Clause, Label, LTMSContradiction, avoid_all


def _recompute(clause: Clause) -> tuple[int, int]:
    pvs = sum(1 for n, s in clause.literals if n.label is Label.UNKNOWN or n.label is s)
    sats = sum(1 for n, s in clause.literals if n.label is s)
    return pvs, sats


def _check_invariants(m: LTMS) -> None:
    for clause in m.clauses:
        pvs, sats = _recompute(clause)
        assert clause.pvs == pvs, f"pvs mismatch on {clause}: {clause.pvs} != {pvs}"
        assert clause.sats == sats, f"sats mismatch on {clause}: {clause.sats} != {sats}"
        assert clause.pvs >= 0
    for node in m.nodes.values():
        if node.label is Label.UNKNOWN:
            assert node.support is None
        else:
            assert node.support is ENABLED_ASSUMPTION or isinstance(node.support, Clause)


# A clause is a list of (var_index, is_positive); generated over a small var set.
_NVARS = 5
_clauses = st.lists(
    st.lists(
        st.tuples(st.integers(0, _NVARS - 1), st.booleans()),
        min_size=1,
        max_size=3,
        unique_by=lambda lit: lit[0],
    ),
    min_size=0,
    max_size=8,
)


_assumptions = st.lists(st.tuples(st.integers(0, _NVARS - 1), st.booleans()), max_size=4)


@given(clauses=_clauses, assume=_assumptions)
@settings(max_examples=200)
def test_counter_and_support_invariants(clauses, assume) -> None:
    m = LTMS()
    nodes = [m.create_node(i, assumption=True) for i in range(_NVARS)]
    # avoid_all keeps random conflicting inputs from raising mid-sequence.
    with m.with_contradiction_handler(avoid_all):
        for clause in clauses:
            trues = [nodes[i] for i, pos in clause if pos]
            falses = [nodes[i] for i, pos in clause if not pos]
            with contextlib.suppress(LTMSContradiction):
                m.add_clause(trues, falses, "rand")
        _check_invariants(m)

        enabled = []
        for i, pos in assume:
            node = nodes[i]
            if node.label is Label.UNKNOWN:
                try:
                    m.enable_assumption(node, Label.TRUE if pos else Label.FALSE)
                    enabled.append(node)
                except (ValueError, LTMSContradiction):
                    pass
        _check_invariants(m)

        for node in enabled:
            if node.support is ENABLED_ASSUMPTION:
                m.retract_assumption(node)
        _check_invariants(m)
