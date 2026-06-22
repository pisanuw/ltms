"""WatchedLTMS -- a 2-watched-literals Boolean Constraint Propagation engine.

An alternative to the counter-based :class:`~ltms.core.LTMS`. Instead of
maintaining ``pvs``/``sats`` counters on every clause of an assigned node, each
clause *watches* two non-false literals; only when a watched literal becomes
false is the clause re-examined (and a replacement watch sought). This is the
SAT-solver data structure, and it is what makes unit propagation scale.

The TMS-specific parts -- well-founded ``support`` per node and the two-phase
retraction -- are kept, but retraction is driven by the support pointers (no
counters): when a node is unlabelled, any node whose forcing clause used it as a
(now non-false) antecedent loses support and is re-derived if possible.

This engine is validated to produce the *same* forced labels and the *same*
contradictions as the reference :class:`~ltms.core.LTMS` (see the differential
tests), and to be sound against a real SAT solver. It implements the
propositional core (clauses, assumptions, retraction, contradictions,
explanation); the rule engine / CWA / DDS facilities run on the reference LTMS.
"""

from __future__ import annotations

from collections.abc import Callable, Iterator
from contextlib import contextmanager
from typing import Any

from .core import ENABLED_ASSUMPTION, Clause, Label, LTMSContradiction, Support, TmsNode

ContradictionHandler = Callable[["list[Clause]", "WatchedLTMS"], bool]


def _opposite(sign: Label) -> Label:
    return Label.FALSE if sign is Label.TRUE else Label.TRUE


class WatchedLTMS:
    """A logic-based TMS using two-watched-literals propagation."""

    def __init__(self, title: str = "watched-ltms") -> None:
        self.title = title
        self.node_counter = 0
        self.clause_counter = 0
        self.nodes: dict[Any, TmsNode] = {}
        self.clauses: list[Clause] = []
        self.checking_contradictions = True
        self.contradiction_handlers: list[ContradictionHandler] = []
        self.violated: list[Clause] = []
        # literal -> clauses watching it; literal -> all clauses containing it.
        self._watchers: dict[tuple[TmsNode, Label], list[Clause]] = {}
        self._membership: dict[tuple[TmsNode, Label], list[Clause]] = {}
        self._watched: dict[Clause, list[int]] = {}
        self._pending: list[tuple[TmsNode, Label]] = []  # literals just made false

    # -- literal predicates ------------------------------------------------- #

    @staticmethod
    def _is_false(node: TmsNode, sign: Label) -> bool:
        return node.label is not Label.UNKNOWN and node.label is not sign

    @staticmethod
    def _is_satisfied(node: TmsNode, sign: Label) -> bool:
        return node.label is sign

    def _nonfalse_indices(self, clause: Clause) -> list[int]:
        return [
            k for k, (n, s) in enumerate(clause.literals) if not self._is_false(n, s)
        ]

    def _clause_is_satisfied(self, clause: Clause) -> bool:
        return any(self._is_satisfied(n, s) for n, s in clause.literals)

    # -- node / clause construction ---------------------------------------- #

    def create_node(self, datum: Any, *, assumption: bool = False) -> TmsNode:
        self.node_counter += 1
        node = TmsNode(self.node_counter, datum, self)  # type: ignore[arg-type]
        node.assumption = assumption
        if datum is not None:
            self.nodes[datum] = node
        return node

    def add_clause(
        self, true_nodes: list[TmsNode], false_nodes: list[TmsNode], informant: Any = None
    ) -> Clause | None:
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
        simplified = self._simplify(literals)
        if simplified is None:
            return None  # tautology
        self.clause_counter += 1
        clause = Clause(self.clause_counter, informant, simplified)
        self.clauses.append(clause)
        for n, s in simplified:
            self._membership.setdefault((n, s), []).append(clause)
        self._install(clause)
        if not internal:
            self._propagate()
            self.check_for_contradictions()
        return clause

    def _simplify(
        self, literals: list[tuple[TmsNode, Label]]
    ) -> list[tuple[TmsNode, Label]] | None:
        ordered = sorted(literals, key=lambda lit: lit[0].index)
        result: list[tuple[TmsNode, Label]] = []
        for n, s in ordered:
            if result and result[-1][0] is n:
                if result[-1][1] is s:
                    continue
                return None  # n and ~n -> tautology
            result.append((n, s))
        return result

    # -- watched-literal machinery ----------------------------------------- #

    def _set_watches(self, clause: Clause, indices: list[int]) -> None:
        self._watched[clause] = indices
        for k in indices:
            n, s = clause.literals[k]
            self._watchers.setdefault((n, s), []).append(clause)

    def _clear_watches(self, clause: Clause) -> None:
        for k in self._watched.get(clause, []):
            n, s = clause.literals[k]
            watchers = self._watchers.get((n, s))
            if watchers and clause in watchers:
                watchers.remove(clause)
        self._watched[clause] = []

    def _install(self, clause: Clause) -> None:
        """Choose watches and force/record if the clause is unit/violated."""
        self._clear_watches(clause)
        lits = clause.literals
        if not lits:  # empty clause == FALSE
            self._record_violation(clause)
            return
        nonfalse = self._nonfalse_indices(clause)
        if not nonfalse:
            self._set_watches(clause, [0] if len(lits) == 1 else [0, 1])
            self._record_violation(clause)
            return
        if len(nonfalse) == 1:
            k = nonfalse[0]
            if len(lits) == 1:
                self._set_watches(clause, [k])
            else:
                other = next(j for j in range(len(lits)) if j != k)
                self._set_watches(clause, [k, other])
            n, s = lits[k]
            if n.label is Label.UNKNOWN:  # unit: force the lone non-false literal
                self._assign(n, s, clause)
            return
        self._set_watches(clause, [nonfalse[0], nonfalse[1]])

    def _assign(self, node: TmsNode, value: Label, reason: Support) -> None:
        node.label = value
        node.support = reason
        self._pending.append((node, _opposite(value)))  # this literal is now false

    # public labelling primitive (parity with LTMS.set_truth)
    def set_truth(self, node: TmsNode, value: Label, reason: Support) -> None:
        self._assign(node, value, reason)
        self._propagate()

    def _propagate(self) -> None:
        while self._pending:
            lit = self._pending.pop()
            for clause in list(self._watchers.get(lit, [])):
                self._on_false(clause, lit)

    def _on_false(self, clause: Clause, lit: tuple[TmsNode, Label]) -> None:
        watched = self._watched.get(clause, [])
        lits = clause.literals
        # locate the watched index that corresponds to the falsified literal
        false_idx = next(
            (k for k in watched if lits[k][0] is lit[0] and lits[k][1] is lit[1]), None
        )
        if false_idx is None:
            return  # stale watch
        others = [k for k in watched if k != false_idx]
        other = others[0] if others else false_idx
        # try to find a replacement non-false literal not already watched
        for k, (n, s) in enumerate(lits):
            if k in watched:
                continue
            if not self._is_false(n, s):
                # move the watch from the false literal to k
                watched.remove(false_idx)
                watched.append(k)
                self._watchers[lit].remove(clause)
                self._watchers.setdefault((n, s), []).append(clause)
                return
        # no replacement: inspect the other watched literal
        on, os = lits[other]
        if other == false_idx:  # unit clause whose sole literal went false
            self._record_violation(clause)
        elif self._is_satisfied(on, os):
            return  # clause already satisfied
        elif on.label is Label.UNKNOWN:
            self._assign(on, os, clause)  # forced
        else:
            self._record_violation(clause)

    def _record_violation(self, clause: Clause) -> None:
        if clause not in self.violated:
            self.violated.append(clause)

    # -- contradictions ----------------------------------------------------- #

    def check_for_contradictions(self) -> None:
        if not self.checking_contradictions:
            return
        while True:
            still = [c for c in self.violated if not self._nonfalse_indices(c)]
            self.violated = []
            if not still:
                return
            if not any(h(still, self) for h in reversed(self.contradiction_handlers)):
                raise LTMSContradiction(still)
            self._propagate()

    @contextmanager
    def with_contradiction_handler(self, handler: ContradictionHandler) -> Iterator[None]:
        self.contradiction_handlers.append(handler)
        try:
            yield
        finally:
            self.contradiction_handlers.remove(handler)

    # -- assumptions & retraction ------------------------------------------ #

    def convert_to_assumption(self, node: TmsNode) -> None:
        node.assumption = True

    def assume(self, node: TmsNode, value: Label) -> None:
        self.convert_to_assumption(node)
        self.enable_assumption(node, value)

    def enable_assumption(self, node: TmsNode, value: Label) -> None:
        if not node.assumption:
            raise ValueError("not an assumption")
        if node.label is Label.UNKNOWN:
            self.set_truth(node, value, ENABLED_ASSUMPTION)
            self.check_for_contradictions()
        elif node.label is value:
            node.support = ENABLED_ASSUMPTION
        else:
            raise ValueError(f"cannot enable as {value.value}: already {node.label.value}")

    def retract_assumption(self, node: TmsNode) -> None:
        self._retract(node)
        self._propagate()
        self.check_for_contradictions()

    def _retract(self, node: TmsNode) -> None:
        if node.label is Label.UNKNOWN or node.support is not ENABLED_ASSUMPTION:
            return
        freed = self._propagate_unknownness(node)
        touched: set[Clause] = set()
        for n in freed:  # re-derive from alternative support
            for s in (Label.TRUE, Label.FALSE):
                touched.update(self._membership.get((n, s), []))
        for clause in touched:
            self._install(clause)

    def _propagate_unknownness(self, start: TmsNode) -> list[TmsNode]:
        freed: list[TmsNode] = []
        queue: list[TmsNode] = [start]
        while queue:
            node = queue.pop(0)
            if node.label is Label.UNKNOWN:
                continue
            old = node.label
            node.label = Label.UNKNOWN
            node.support = None
            freed.append(node)
            # clauses where node was a false antecedent: literal (node, ~old)
            for clause in self._membership.get((node, _opposite(old)), []):
                consequent = self._clause_consequent(clause)
                if (consequent is not None and consequent is not node
                        and consequent.label is not Label.UNKNOWN):
                    queue.append(consequent)
        return freed

    @staticmethod
    def _clause_consequent(clause: Clause) -> TmsNode | None:
        for node, _s in clause.literals:
            if node.support is clause:
                return node
        return None

    # -- explanation / nogoods --------------------------------------------- #

    def assumptions_of_node(self, node: TmsNode) -> list[TmsNode]:
        result: list[TmsNode] = []
        visited: set[int] = set()
        work = [node]
        while work:
            n = work.pop()
            if id(n) in visited:
                continue
            visited.add(id(n))
            if n.support is ENABLED_ASSUMPTION:
                result.append(n)
            elif isinstance(n.support, Clause):
                work.extend(m for m, _s in n.support.literals if m is not n)
        return result

    def assumptions_of_clause(self, clause: Clause) -> list[TmsNode]:
        result: list[TmsNode] = []
        seen: set[int] = set()
        for n, _s in clause.literals:
            for a in self.assumptions_of_node(n):
                if id(a) not in seen:
                    seen.add(id(a))
                    result.append(a)
        return result

    # -- queries ------------------------------------------------------------ #

    @staticmethod
    def is_true(node: TmsNode) -> bool:
        return node.label is Label.TRUE

    @staticmethod
    def is_false(node: TmsNode) -> bool:
        return node.label is Label.FALSE
