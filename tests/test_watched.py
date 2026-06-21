"""Watched-literals engine: unit tests + equivalence to the counter LTMS + SAT."""

from __future__ import annotations

import pytest
from hypothesis import given, settings
from hypothesis import strategies as st

from ltms.core import LTMS, Label, LTMSContradiction
from ltms.watched import WatchedLTMS

# --- basic behaviour ------------------------------------------------------- #


def test_unit_propagation():
    m = WatchedLTMS()
    a, b = m.create_node("a"), m.create_node("b")
    m.add_clause([a, b], [], "a v b")
    m.add_clause([], [a], "~a")  # a := FALSE -> forces b
    assert a.label is Label.FALSE
    assert b.label is Label.TRUE


def test_implication_chain():
    m = WatchedLTMS()
    p, q, r = (m.create_node(x) for x in "pqr")
    m.add_clause([q], [p], "p->q")
    m.add_clause([r], [q], "q->r")
    m.add_clause([p], [], "p")
    assert p.label is Label.TRUE and q.label is Label.TRUE and r.label is Label.TRUE


def test_contradiction_raises():
    m = WatchedLTMS()
    p = m.create_node("p")
    m.add_clause([p], [], "p")
    with pytest.raises(LTMSContradiction):
        m.add_clause([], [p], "~p")


def test_retraction_restores_and_finds_alternative():
    m = WatchedLTMS()
    a = m.create_node("a", assumption=True)
    b = m.create_node("b", assumption=True)
    c = m.create_node("c")
    m.add_clause([c], [a], "a->c")
    m.add_clause([c], [b], "b->c")
    m.enable_assumption(a, Label.TRUE)
    m.enable_assumption(b, Label.TRUE)
    assert c.label is Label.TRUE
    m.retract_assumption(a)
    assert c.label is Label.TRUE  # re-derived from b
    m.retract_assumption(b)
    assert c.label is Label.UNKNOWN


def test_bcp_incompleteness_leaves_unknown():
    m = WatchedLTMS()
    x, y = m.create_node("x"), m.create_node("y")
    m.add_clause([x], [y], "x v ~y")
    m.add_clause([x, y], [], "x v y")
    assert x.label is Label.UNKNOWN and y.label is Label.UNKNOWN


# --- random clause-set strategies ------------------------------------------ #

_NVARS = 5
_clauses = st.lists(
    st.lists(
        st.tuples(st.integers(0, _NVARS - 1), st.booleans()),
        min_size=1,
        max_size=3,
        unique_by=lambda lit: lit[0],
    ),
    min_size=0,
    max_size=10,
)
_assumptions = st.lists(st.tuples(st.integers(0, _NVARS - 1), st.booleans()), max_size=5)


# --- equivalence to the reference counter-based LTMS ----------------------- #


@given(clauses=_clauses, assume=_assumptions)
@settings(max_examples=300, deadline=None)
def test_watched_matches_counter_ltms(clauses, assume) -> None:
    counter = LTMS()
    watched = WatchedLTMS()
    cn = [counter.create_node(i, assumption=True) for i in range(_NVARS)]
    wn = [watched.create_node(i, assumption=True) for i in range(_NVARS)]
    c_bad = w_bad = False

    def labels_match() -> None:
        for i in range(_NVARS):
            assert cn[i].label is wn[i].label, f"label mismatch at var {i}"

    for clause in clauses:
        try:
            counter.add_clause([cn[i] for i, p in clause if p],
                               [cn[i] for i, p in clause if not p], "c")
        except LTMSContradiction:
            c_bad = True
        try:
            watched.add_clause([wn[i] for i, p in clause if p],
                               [wn[i] for i, p in clause if not p], "c")
        except LTMSContradiction:
            w_bad = True
        assert c_bad == w_bad
        if c_bad:
            return
        labels_match()

    for i, p in assume:
        if cn[i].label is not Label.UNKNOWN:
            continue
        val = Label.TRUE if p else Label.FALSE
        try:
            counter.enable_assumption(cn[i], val)
        except LTMSContradiction:
            c_bad = True
        try:
            watched.enable_assumption(wn[i], val)
        except LTMSContradiction:
            w_bad = True
        assert c_bad == w_bad
        if c_bad:
            return
        labels_match()


# --- soundness against a real SAT solver ----------------------------------- #

_pysat = pytest.importorskip("pysat.solvers")
Minisat22 = _pysat.Minisat22


def _dimacs(i: int, positive: bool) -> int:
    return (i + 1) if positive else -(i + 1)


@given(clauses=_clauses)
@settings(max_examples=200, deadline=None)
def test_watched_is_sound_against_minisat(clauses) -> None:
    m = WatchedLTMS()
    nodes = [m.create_node(i) for i in range(_NVARS)]
    cnf: list[list[int]] = []
    contradiction = False
    for clause in clauses:
        cnf.append([_dimacs(i, p) for i, p in clause])
        try:
            m.add_clause([nodes[i] for i, p in clause if p],
                         [nodes[i] for i, p in clause if not p], "c")
        except LTMSContradiction:
            contradiction = True
            break
    if contradiction:
        with Minisat22(bootstrap_with=cnf) as solver:
            assert solver.solve() is False
        return
    with Minisat22(bootstrap_with=cnf) as solver:
        for i, node in enumerate(nodes):
            if node.label is Label.TRUE:
                assert solver.solve(assumptions=[_dimacs(i, False)]) is False
            elif node.label is Label.FALSE:
                assert solver.solve(assumptions=[_dimacs(i, True)]) is False
