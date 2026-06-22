"""JTMS -- a Justification-based Truth Maintenance System.

The simplest TMS, and the foundation the LTMS generalizes. It maintains a
two-valued belief label (``IN`` / ``OUT``) over a network of nodes connected by
**justifications**, where a justification is logically a definite (Horn) clause
``antecedents => consequence``.

Key properties (and the traps a port must respect):

* ``OUT`` does **not** mean false -- it means "not currently derivable". The
  JTMS can never derive a negation; that is the core difference from the LTMS.
* A node's ``support`` is overloaded three ways: ``None`` (OUT), a
  :class:`Justification` (derived; empty antecedents = a premise), or the
  :data:`ENABLED_ASSUMPTION` sentinel.
* Adding justifications / enabling assumptions only flips ``OUT -> IN`` via a
  monotone forward sweep.
* **Retraction is strictly two-phase**: first label ``OUT`` everything whose
  current support flows through the retracted node, *then* search for
  alternative support. Interleaving admits ill-founded circular support.
* The JTMS only *signals* contradictions (a contradictory node that is IN); it
  never resolves them. Dependency-directed backtracking is the caller's job,
  built on :meth:`JTMS.assumptions_of_node`.
"""

from __future__ import annotations

from collections.abc import Callable, Iterable
from enum import Enum
from typing import Any, Union


class Belief(Enum):
    IN = "IN"
    OUT = "OUT"


class _EnabledAssumption:
    """Sentinel marking a node believed because it is an enabled assumption."""

    def __repr__(self) -> str:
        return "ENABLED_ASSUMPTION"


ENABLED_ASSUMPTION = _EnabledAssumption()

Support = Union["Justification", _EnabledAssumption, None]


class JTMSContradiction(Exception):
    """Raised by the default contradiction handler."""

    def __init__(self, nodes: list[Node]) -> None:
        super().__init__(f"contradiction among IN nodes: {nodes}")
        self.nodes = nodes


class Justification:
    """A recorded inference: ``antecedents => consequence`` with an informant."""

    __slots__ = ("index", "informant", "consequence", "antecedents")

    def __init__(
        self, index: int, informant: Any, consequence: Node, antecedents: list[Node]
    ) -> None:
        self.index = index
        self.informant = informant
        self.consequence = consequence
        self.antecedents = antecedents

    def __repr__(self) -> str:
        return f"<just {self.index}: {self.informant}>"


class Node:
    """A proposition with a cached belief label and its current support."""

    __slots__ = (
        "index",
        "datum",
        "label",
        "support",
        "justs",
        "consequences",
        "contradictory",
        "assumption",
        "in_rules",
        "out_rules",
        "jtms",
    )

    def __init__(self, index: int, datum: Any, jtms: JTMS) -> None:
        self.index = index
        self.datum = datum
        self.jtms = jtms
        self.label = Belief.OUT
        self.support: Support = None
        self.justs: list[Justification] = []
        self.consequences: list[Justification] = []
        self.contradictory = False
        # False, True, or the string "DEFAULT" for default-reasoning assumptions.
        self.assumption: bool | str = False
        self.in_rules: list[Any] = []
        self.out_rules: list[Any] = []

    @property
    def is_in(self) -> bool:
        return self.label is Belief.IN

    @property
    def is_out(self) -> bool:
        return self.label is Belief.OUT

    @property
    def is_premise(self) -> bool:
        s = self.support
        return isinstance(s, Justification) and not s.antecedents

    def __repr__(self) -> str:
        return f"<node {self.index}: {self.datum} {self.label.value}>"


def _default_handler(jtms: JTMS, nodes: list[Node]) -> None:
    raise JTMSContradiction(nodes)


class JTMS:
    """A justification-based truth maintenance system instance."""

    def __init__(
        self,
        title: str = "jtms",
        *,
        node_string: Callable[[Node], str] | None = None,
        contradiction_handler: Callable[[JTMS, list[Node]], None] | None = None,
        enqueue_procedure: Callable[[Any], None] | None = None,
    ) -> None:
        self.title = title
        self.node_counter = 0
        self.just_counter = 0
        self.nodes: list[Node] = []
        self.justs: list[Justification] = []
        self.contradictions: list[Node] = []
        self.assumptions: list[Node] = []
        self.checking_contradictions = True
        self.node_string = node_string or (lambda n: str(n.datum))
        self.contradiction_handler = contradiction_handler or _default_handler
        self.enqueue_procedure = enqueue_procedure

    # -- node / justification creation -------------------------------------- #

    def create_node(
        self, datum: Any, *, assumption: bool = False, contradictory: bool = False
    ) -> Node:
        self.node_counter += 1
        node = Node(self.node_counter, datum, self)
        node.assumption = assumption
        node.contradictory = contradictory
        if assumption:
            self.assumptions.append(node)
        if contradictory:
            self.contradictions.append(node)
        self.nodes.append(node)
        return node

    def make_contradiction(self, node: Node) -> None:
        if not node.contradictory:
            node.contradictory = True
            self.contradictions.append(node)
            self.check_for_contradictions()

    def justify_node(self, informant: Any, consequence: Node, antecedents: list[Node]) -> None:
        """Record ``antecedents => consequence`` and relabel if it now applies."""
        self.just_counter += 1
        just = Justification(self.just_counter, informant, consequence, list(antecedents))
        consequence.justs.append(just)
        for ant in antecedents:
            ant.consequences.append(just)
        self.justs.append(just)
        if antecedents or consequence.is_out:
            if self._check_justification(just):
                self._install_support(consequence, just)
        else:
            # antecedent-free justification on an already-IN node => premise.
            consequence.support = just
        self.check_for_contradictions()

    # -- assumptions -------------------------------------------------------- #

    def convert_to_assumption(self, node: Node) -> None:
        if not node.assumption:
            node.assumption = True
            self.assumptions.append(node)

    def enable_assumption(self, node: Node) -> None:
        if not node.assumption:
            raise ValueError(f"{self.node_string(node)} is not an assumption")
        if node.is_out:
            self._make_node_in(node, ENABLED_ASSUMPTION)
            self._propagate_inness(node)
        elif node.support is ENABLED_ASSUMPTION or node.is_premise:
            pass  # already enabled, or a premise (premise wins)
        else:
            node.support = ENABLED_ASSUMPTION  # override derived support
        self.check_for_contradictions()

    def retract_assumption(self, node: Node) -> None:
        """Disable an enabled assumption (two-phase relabel)."""
        if node.support is ENABLED_ASSUMPTION:
            self._make_node_out(node)
            out = self._propagate_outness(node)
            self._find_alternative_support([node, *out])

    # -- forward IN propagation (monotone) ---------------------------------- #

    def _check_justification(self, just: Justification) -> bool:
        return just.consequence.is_out and self._justification_satisfied(just)

    @staticmethod
    def _justification_satisfied(just: Justification) -> bool:
        return all(a.is_in for a in just.antecedents)

    def _install_support(self, conseq: Node, just: Justification) -> None:
        self._make_node_in(conseq, just)
        self._propagate_inness(conseq)

    def _propagate_inness(self, node: Node) -> None:
        q: list[Node] = [node]
        while q:
            n = q.pop(0)
            for j in n.consequences:
                if self._check_justification(j):
                    self._make_node_in(j.consequence, j)
                    q.append(j.consequence)

    def _fire_rules(self, rules: list[Any]) -> list[Any]:
        """Enqueue any waiting rules; return the cleared list, or leave it
        untouched when there is no enqueue procedure to fire them."""
        if self.enqueue_procedure is None:
            return rules
        for rule in rules:
            self.enqueue_procedure(rule)
        return []

    def _make_node_in(self, conseq: Node, reason: Support) -> None:
        conseq.label = Belief.IN
        conseq.support = reason
        conseq.in_rules = self._fire_rules(conseq.in_rules)

    # -- two-phase retraction ---------------------------------------------- #

    def _make_node_out(self, node: Node) -> None:
        node.support = None
        node.label = Belief.OUT
        node.out_rules = self._fire_rules(node.out_rules)

    def _propagate_outness(self, node: Node) -> list[Node]:
        """Phase 1: label OUT every node whose *current support* is via ``node``."""
        out: list[Node] = []
        queue: list[Justification] = list(node.consequences)
        while queue:
            j = queue.pop(0)
            conseq = j.consequence
            if conseq.support is j:  # identity: this just is its current support
                self._make_node_out(conseq)
                out.append(conseq)
                queue.extend(conseq.consequences)
        return out

    def _find_alternative_support(self, nodes: Iterable[Node]) -> None:
        """Phase 2: re-derive any forgotten node from another satisfied just."""
        for node in nodes:
            if not node.is_in:
                for just in node.justs:
                    if self._check_justification(just):
                        self._install_support(just.consequence, just)
                        break

    # -- contradictions ----------------------------------------------------- #

    def check_for_contradictions(self) -> None:
        if not self.checking_contradictions:
            return
        cnodes = [n for n in self.contradictions if n.is_in]
        if cnodes:
            self.contradiction_handler(self, cnodes)

    # -- introspection / explanation ---------------------------------------- #

    def assumptions_of_node(self, node: Node) -> list[Node]:
        """Enabled assumptions underlying ``node``'s current well-founded support."""
        result: list[Node] = []
        visited: set[int] = set()
        work: list[Node] = [node]
        while work:
            n = work.pop()
            if id(n) in visited:
                continue
            visited.add(id(n))
            if n.support is ENABLED_ASSUMPTION:
                result.append(n)
            elif n.is_in and isinstance(n.support, Justification):
                work.extend(n.support.antecedents)
        return result

    def enabled_assumptions(self) -> list[Node]:
        return [n for n in self.assumptions if n.support is ENABLED_ASSUMPTION]

    def why_node(self, node: Node) -> str:
        if node.is_out:
            return f"{self.node_string(node)} is OUT."
        if node.support is ENABLED_ASSUMPTION:
            return f"{self.node_string(node)} is IN via enabled assumption."
        assert isinstance(node.support, Justification)
        ants = ", ".join(self.node_string(a) for a in node.support.antecedents)
        return (
            f"{self.node_string(node)} is IN via {node.support.informant}"
            + (f" <= {ants}" if ants else " (premise).")
        )
