"""Propositional formula -> CNF clauses, and ``add_formula`` for the LTMS.

A *formula* is built from :class:`~ltms.core.TmsNode` leaves and connective
tuples whose head is one of the strings in :data:`CONNECTIVES`:

    ("and", f, ...), ("or", f, ...), ("not", f),
    ("implies", a, b), ("iff", a, b), ("taxonomy", f, ...)

Conversion carries a ``negate`` flag so De Morgan is folded in line, exactly as
in BPS. CNF is a list of clauses; each clause is a list of ``(node, sign)``
literals. Edge cases: an empty disjunction is FALSE (one empty clause); an empty
conjunction is TRUE (no clauses); tautologies are dropped at install time.
"""

from __future__ import annotations

from typing import Any

from .core import LTMS, Clause, Label, TmsNode

CONNECTIVES = frozenset({"and", "or", "not", "implies", "iff", "taxonomy"})

# A CNF is a list of clauses; a clause is a list of (node, sign) literals.
ClauseLits = "list[tuple[TmsNode, Label]]"


def normalize(formula: Any) -> list[list[tuple[TmsNode, Label]]]:
    """Convert ``formula`` to CNF (a list of clauses)."""
    return _normalize_1(formula, negate=False)


def _normalize_1(exp: Any, negate: bool) -> list[list[tuple[TmsNode, Label]]]:
    if isinstance(exp, TmsNode):
        sign = Label.FALSE if negate else Label.TRUE
        return [[(exp, sign)]]
    if not isinstance(exp, tuple) or not exp or exp[0] not in CONNECTIVES:
        raise ValueError(f"not a formula (leaves must be TmsNode): {exp!r}")
    head = exp[0]
    if head == "not":
        return _normalize_1(exp[1], not negate)
    if head in ("and", "or"):
        # De Morgan: an unnegated AND is a conjunction of clauses and an
        # unnegated OR a disjunction; negation swaps the two roles.
        as_conjunction = (head == "and") != negate
        build = _normalize_conjunction if as_conjunction else _normalize_disjunction
        return build(exp[1:], negate)
    if head == "implies":
        a, b = exp[1], exp[2]
        return _normalize_1(("or", ("not", a), b), negate)
    if head == "iff":
        a, b = exp[1], exp[2]
        return _normalize_1(("and", ("implies", a, b), ("implies", b, a)), negate)
    if head == "taxonomy":
        return _normalize_1(_expand_taxonomy(exp[1:]), negate)
    raise ValueError(f"unknown connective: {head!r}")


def _normalize_conjunction(
    subs: tuple[Any, ...], negate: bool
) -> list[list[tuple[TmsNode, Label]]]:
    clauses: list[list[tuple[TmsNode, Label]]] = []
    for s in subs:
        clauses.extend(_normalize_1(s, negate))
    return clauses


def _normalize_disjunction(
    subs: tuple[Any, ...], negate: bool
) -> list[list[tuple[TmsNode, Label]]]:
    if not subs:
        return [[]]  # empty OR == FALSE == a single empty (violated) clause
    result = _normalize_1(subs[0], negate)
    for s in subs[1:]:
        result = _disjoin(result, _normalize_1(s, negate))
    return result


def _disjoin(
    cnf1: list[list[tuple[TmsNode, Label]]],
    cnf2: list[list[tuple[TmsNode, Label]]],
) -> list[list[tuple[TmsNode, Label]]]:
    """OR of two CNFs = cross product of their clauses."""
    return [c1 + c2 for c1 in cnf1 for c2 in cnf2]


def _expand_taxonomy(items: tuple[Any, ...]) -> tuple[Any, ...]:
    """``(taxonomy a b c)`` = exactly one holds: (or a b c) and pairwise not-both."""
    at_least_one: tuple[Any, ...] = ("or", *items)
    pairwise = [
        ("not", ("and", items[i], items[j]))
        for i in range(len(items))
        for j in range(i + 1, len(items))
    ]
    return ("and", at_least_one, *pairwise)


def add_formula(ltms: LTMS, formula: Any, informant: Any = None) -> list[Clause]:
    """Normalize ``formula`` to CNF and install each clause, then settle."""
    clauses: list[Clause] = []
    for lits in normalize(formula):
        clause = ltms.add_clause_literals(lits, ("implied-by", informant), internal=True)
        if clause is not None:
            clauses.append(clause)
    ltms._run_bcp()
    ltms.check_for_contradictions()
    return clauses
