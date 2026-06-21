"""Explanation facilities: render well-founded support as human-readable proofs.

These sit on top of the core's ``support`` data (each node's single forcing
clause, the ``ENABLED_ASSUMPTION`` sentinel, or ``None``) and the
``assumptions_of_node`` walk. ``why_node`` describes one node; ``explain_node``
produces a numbered, topologically-ordered proof back to enabled assumptions.
"""

from __future__ import annotations

from .core import ENABLED_ASSUMPTION, LTMS, Clause, Label, TmsNode


def support_for_node(node: TmsNode) -> tuple[list[TmsNode], object] | None:
    """Return ``(antecedent_nodes, informant)`` for a derived node.

    ``None`` if the node is unknown; ``([], ENABLED_ASSUMPTION)`` if it is an
    enabled assumption.
    """
    if node.label is Label.UNKNOWN:
        return None
    if node.support is ENABLED_ASSUMPTION:
        return ([], ENABLED_ASSUMPTION)
    if isinstance(node.support, Clause):
        antecedents = [m for m, _s in node.support.literals if m is not node]
        return (antecedents, node.support.informant)
    return ([], "premise")


def _signed(ltms: LTMS, node: TmsNode) -> str:
    name = ltms.node_string(node)
    if node.is_true:
        return name
    if node.is_false:
        return f"(not {name})"
    return f"{name}?"


def why_node(ltms: LTMS, node: TmsNode) -> str:
    """One-line description of why ``node`` has its current label."""
    if node.label is Label.UNKNOWN:
        return f"{ltms.node_string(node)} is UNKNOWN."
    if node.support is ENABLED_ASSUMPTION:
        return f"{_signed(ltms, node)} is an enabled assumption."
    if isinstance(node.support, Clause):
        antecedents = [m for m, _s in node.support.literals if m is not node]
        if not antecedents:
            return f"{_signed(ltms, node)} is a premise ({node.support.informant})."
        ants = ", ".join(_signed(ltms, m) for m in antecedents)
        return f"{_signed(ltms, node)} via {node.support.informant} <= {ants}"
    return f"{_signed(ltms, node)} (no recorded support)."


def explain_node(ltms: LTMS, node: TmsNode) -> list[str]:
    """A numbered well-founded proof of ``node`` back to enabled assumptions."""
    order: list[TmsNode] = []
    visited: set[int] = set()

    def visit(n: TmsNode) -> None:
        if id(n) in visited or n.label is Label.UNKNOWN:
            return
        visited.add(id(n))
        if isinstance(n.support, Clause):
            for m, _s in n.support.literals:
                if m is not n:
                    visit(m)
        order.append(n)

    visit(node)
    return [f"{i + 1}. {why_node(ltms, n)}" for i, n in enumerate(order)]
