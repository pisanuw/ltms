"""LTMS core -- Boolean Constraint Propagation over propositional clauses.

A sound-but-incomplete propositional reasoner. The inference engine supplies
**clauses** (disjunctions of signed literals); the LTMS propagates three-valued
labels (``TRUE`` / ``FALSE`` / ``UNKNOWN``) by unit propagation, records the
forcing clause as each node's well-founded **support**, and detects
contradictions.

Negation is just the label: there is no separate node for ``not P``.

This module (Session 3) implements the BCP engine: clause installation, the
incremental ``pvs``/``sats`` counters, forward propagation, and deferred
contradiction detection. Assumptions, retraction, formula normalization, and
explanation are added in :mod:`ltms.core` Session-4 extensions / sibling modules.

Counter discipline (the heart of BCP -- get this exactly right):

* ``pvs`` ("potential violators") = (#literals UNKNOWN) + (#literals currently
  satisfying). Equivalently, literals **not** yet labeled opposite their sign.
* ``sats`` = #literals currently satisfying.
* violated  <=> ``pvs == 0``;  unit/forcing <=> ``pvs == 1``;  satisfied <=>
  ``sats > 0``.

A satisfying literal still counts toward ``pvs`` (if its support is later
retracted it could become a violator again), so satisfied clauses are never
discarded -- their counters must stay live for correct retraction.
"""

from __future__ import annotations

from collections.abc import Callable
from enum import Enum
from typing import Any, Union


class Label(Enum):
    UNKNOWN = "UNKNOWN"
    TRUE = "TRUE"
    FALSE = "FALSE"


def negate(label: Label) -> Label:
    if label is Label.TRUE:
        return Label.FALSE
    if label is Label.FALSE:
        return Label.TRUE
    return Label.UNKNOWN


class _EnabledAssumption:
    """Sentinel: node believed because it is an enabled assumption."""

    def __repr__(self) -> str:
        return "ENABLED_ASSUMPTION"


ENABLED_ASSUMPTION = _EnabledAssumption()

# A literal is a (node, sign) pair; sign is Label.TRUE or Label.FALSE.
Literal = "tuple[TmsNode, Label]"
Support = Union["Clause", _EnabledAssumption, None]


class LTMSContradiction(Exception):
    """Raised when a contradiction is detected and no handler resolves it."""

    def __init__(self, clauses: list[Clause]) -> None:
        super().__init__(f"unresolved contradiction in clauses: {clauses}")
        self.clauses = clauses


class TmsNode:
    """A proposition with a three-valued label and its well-founded support."""

    __slots__ = (
        "index",
        "datum",
        "label",
        "support",
        "true_clauses",
        "false_clauses",
        "assumption",
        "true_rules",
        "false_rules",
        "ltms",
    )

    def __init__(self, index: int, datum: Any, ltms: LTMS) -> None:
        self.index = index
        self.datum = datum
        self.ltms = ltms
        self.label = Label.UNKNOWN
        self.support: Support = None
        self.true_clauses: list[Clause] = []
        self.false_clauses: list[Clause] = []
        self.assumption = False
        self.true_rules: list[Any] = []
        self.false_rules: list[Any] = []

    @property
    def is_true(self) -> bool:
        return self.label is Label.TRUE

    @property
    def is_false(self) -> bool:
        return self.label is Label.FALSE

    @property
    def is_known(self) -> bool:
        return self.label is not Label.UNKNOWN

    @property
    def is_assumption_enabled(self) -> bool:
        return self.support is ENABLED_ASSUMPTION

    def __repr__(self) -> str:
        return f"<node {self.index}: {self.datum} {self.label.value}>"


class Clause:
    """A disjunction of signed literals, with the incremental BCP counters."""

    __slots__ = ("index", "informant", "literals", "pvs", "sats")

    def __init__(
        self, index: int, informant: Any, literals: list[tuple[TmsNode, Label]]
    ) -> None:
        self.index = index
        self.informant = informant
        self.literals = literals
        self.pvs = 0
        self.sats = 0

    @property
    def is_violated(self) -> bool:
        return self.pvs == 0

    @property
    def is_satisfied(self) -> bool:
        return self.sats > 0

    @property
    def is_unit_open(self) -> bool:
        return self.pvs == 1

    def __repr__(self) -> str:
        parts = [
            f"{'' if s is Label.TRUE else '~'}{n.datum}" for n, s in self.literals
        ]
        return f"<clause {self.index}: ({' v '.join(parts)})>"


# Sentinel for a tautological (always-true) clause, dropped on install.
_TAUTOLOGY = object()

# A contradiction handler returns True iff it resolved the contradiction.
ContradictionHandler = Callable[["list[Clause]", "LTMS"], bool]


class LTMS:
    """A logic-based truth maintenance system instance (BCP engine)."""

    def __init__(
        self,
        title: str = "ltms",
        *,
        node_string: Callable[[TmsNode], str] | None = None,
        enqueue_procedure: Callable[[Any], None] | None = None,
    ) -> None:
        self.title = title
        self.node_counter = 0
        self.clause_counter = 0
        self.nodes: dict[Any, TmsNode] = {}
        self.clauses: list[Clause] = []
        self.checking_contradictions = True
        self.node_string = node_string or (lambda n: str(n.datum))
        self.enqueue_procedure = enqueue_procedure
        self.contradiction_handlers: list[ContradictionHandler] = []
        self.violated_clauses: list[Clause] = []
        self.pending_contradictions: list[Clause] = []
        self._to_check: list[Clause] = []

    # -- node creation ------------------------------------------------------ #

    def create_node(self, datum: Any, *, assumption: bool = False) -> TmsNode:
        self.node_counter += 1
        node = TmsNode(self.node_counter, datum, self)
        node.assumption = assumption
        if datum is not None:
            self.nodes[datum] = node
        return node

    # -- clause installation ------------------------------------------------ #

    def add_clause(
        self,
        true_nodes: list[TmsNode],
        false_nodes: list[TmsNode],
        informant: Any = None,
    ) -> Clause | None:
        """Install the clause ``(OR true_nodes... (NOT false_nodes)...)``."""
        literals = [(n, Label.TRUE) for n in true_nodes]
        literals += [(n, Label.FALSE) for n in false_nodes]
        return self.add_clause_literals(literals, informant)

    def add_clause_literals(
        self,
        literals: list[tuple[TmsNode, Label]],
        informant: Any = None,
        *,
        internal: bool = False,
    ) -> Clause | None:
        simplified = self._simplify_clause(literals)
        if simplified is _TAUTOLOGY:
            return None
        assert isinstance(simplified, list)
        clause = self._bcp_add_clause(simplified, informant)
        if not internal:
            self._run_bcp()
            self.check_for_contradictions()
        return clause

    def _simplify_clause(
        self, literals: list[tuple[TmsNode, Label]]
    ) -> list[tuple[TmsNode, Label]] | object:
        ordered = sorted(literals, key=lambda lit: lit[0].index)
        result: list[tuple[TmsNode, Label]] = []
        for node, sign in ordered:
            if result and result[-1][0] is node:
                if result[-1][1] is sign:
                    continue  # duplicate literal
                return _TAUTOLOGY  # node and its negation
            result.append((node, sign))
        return result

    def _bcp_add_clause(
        self, literals: list[tuple[TmsNode, Label]], informant: Any
    ) -> Clause:
        self.clause_counter += 1
        clause = Clause(self.clause_counter, informant, literals)
        pvs = 0
        sats = 0
        for node, sign in literals:
            if node.label is Label.UNKNOWN:
                pvs += 1
            elif node.label is sign:  # currently satisfying
                sats += 1
                pvs += 1
            # else: violated literal -- contributes nothing
            if sign is Label.TRUE:
                node.true_clauses.append(clause)
            else:
                node.false_clauses.append(clause)
        clause.pvs = pvs
        clause.sats = sats
        self.clauses.append(clause)
        self._to_check.append(clause)
        return clause

    # -- propagation -------------------------------------------------------- #

    def set_truth(self, node: TmsNode, value: Label, reason: Support) -> None:
        """Label an UNKNOWN node, update counters, queue affected clauses."""
        node.label = value
        node.support = reason
        if value is Label.TRUE:
            self._fire_rules(node.true_rules)
            node.true_rules = []
            for clause in node.true_clauses:  # node now satisfies these
                clause.sats += 1
            for clause in node.false_clauses:  # node was a potential violator here
                clause.pvs -= 1
                if clause.pvs < 2:
                    self._to_check.append(clause)
        else:  # Label.FALSE
            self._fire_rules(node.false_rules)
            node.false_rules = []
            for clause in node.false_clauses:
                clause.sats += 1
            for clause in node.true_clauses:
                clause.pvs -= 1
                if clause.pvs < 2:
                    self._to_check.append(clause)

    def _fire_rules(self, rules: list[Any]) -> None:
        if self.enqueue_procedure is not None:
            for rule in rules:
                self.enqueue_procedure(rule)

    def _run_bcp(self) -> None:
        while self._to_check:
            self._check_clause(self._to_check.pop())

    def _check_clause(self, clause: Clause) -> None:
        if clause.is_violated:
            if clause not in self.violated_clauses:
                self.violated_clauses.append(clause)
        elif clause.is_unit_open:
            lit = self._find_unknown_literal(clause)
            if lit is not None:  # guard: the lone pvs may be a satisfying literal
                node, sign = lit
                self.set_truth(node, sign, clause)

    @staticmethod
    def _find_unknown_literal(clause: Clause) -> tuple[TmsNode, Label] | None:
        for node, sign in clause.literals:
            if node.label is Label.UNKNOWN:
                return (node, sign)
        return None

    # -- contradictions ----------------------------------------------------- #

    def check_for_contradictions(self) -> None:
        if not self.checking_contradictions:
            self.pending_contradictions.extend(
                c for c in self.violated_clauses if c.is_violated
            )
            self.violated_clauses = []
            return
        still = [c for c in self.violated_clauses if c.is_violated]
        self.violated_clauses = []
        if still:
            self._dispatch_contradiction(still)

    def _dispatch_contradiction(self, clauses: list[Clause]) -> None:
        for handler in reversed(self.contradiction_handlers):  # stack: top first
            if handler(clauses, self):
                return
        raise LTMSContradiction(clauses)

    # -- queries ------------------------------------------------------------ #

    def label_of(self, node: TmsNode) -> Label:
        return node.label
