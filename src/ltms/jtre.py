"""JTRE -- a JTMS-backed pattern-directed inference engine.

Binds the :class:`~ltms.jtms.JTMS` to a forward rule engine. Each ground fact
(a :class:`Datum`) owns exactly one JTMS :class:`~ltms.jtms.Node`; belief is read
off the node label. Rules trigger on a fact's *existence* (``INTERN``) or on its
*belief* (``IN`` / ``OUT``). A belief-conditioned rule that matches before the
node has the required label is **parked** on the node and woken by the JTMS via
the injected enqueue procedure when the label is later assigned.

This is the JTMS analogue of the LTRE built later, and shares its shape: a
datum<->node bridge, car-indexed ``dbclass`` buckets, and a deferred rule queue.
"""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass, field
from enum import Enum
from typing import Any

from .jtms import JTMS, Node
from .terms import Term, Var, index_symbol
from .unify import FAIL, substitute, unify

RuleBody = Callable[["dict[Var, Term]", "JTre"], None]


class Condition(Enum):
    INTERN = "intern"  # fires as soon as the datum exists
    IN = "in"  # fires when the node is believed (IN)
    OUT = "out"  # fires when the node is disbelieved (OUT)


@dataclass
class Datum:
    counter: int
    lisp_form: Term
    tms_node: Node
    dbclass: Dbclass
    assumption: Any = None  # informant if this fact was assumed, else None


@dataclass
class Rule:
    counter: int
    trigger: Term
    condition: Condition
    body: RuleBody
    environment: dict[Var, Term]
    dbclass: Dbclass | None = None


@dataclass
class Dbclass:
    name: str
    jtre: JTre
    facts: list[Datum] = field(default_factory=list)
    rules: list[Rule] = field(default_factory=list)


class JTre:
    """A JTMS-backed inference engine instance."""

    def __init__(self, title: str = "jtre", *, debugging: bool = False) -> None:
        self.title = title
        self.debugging = debugging
        self.jtms = JTMS(
            title=f"{title}-jtms",
            node_string=lambda n: str(n.datum.lisp_form) if isinstance(n.datum, Datum) else str(n),
            enqueue_procedure=self._enqueue,
        )
        self.dbclass_table: dict[str, Dbclass] = {}
        self.queue: list[tuple[RuleBody, dict[Var, Term]]] = []
        self.datum_counter = 0
        self.rule_counter = 0
        self.rules_run = 0

    def _enqueue(self, item: Any) -> None:
        self.queue.append(item)

    # -- indexing / interning ---------------------------------------------- #

    def get_dbclass(self, term: Term, env: dict[Var, Term] | None = None) -> Dbclass:
        symbol = index_symbol(term, env)
        bucket = self.dbclass_table.get(symbol)
        if bucket is None:
            bucket = Dbclass(symbol, self)
            self.dbclass_table[symbol] = bucket
        return bucket

    def referent(self, fact: Term, *, create: bool = False) -> Datum | None:
        """Find (or, if ``create``, intern) the datum for a ground fact."""
        bucket = self.get_dbclass(fact)
        for datum in bucket.facts:
            if datum.lisp_form == fact:
                return datum
        if not create:
            return None
        self.datum_counter += 1
        node = self.jtms.create_node(None)
        datum = Datum(self.datum_counter, fact, node, bucket)
        node.datum = datum
        bucket.facts.append(datum)
        for rule in list(bucket.rules):  # let pre-existing rules see the new datum
            self._try_rule_on(rule, datum)
        return datum

    # -- assertions --------------------------------------------------------- #

    def assert_(self, fact: Term, informant: Any = "user") -> Datum:
        """Install ``fact`` as a premise (antecedent-free justification)."""
        datum = self.referent(fact, create=True)
        assert datum is not None
        self.jtms.justify_node(informant, datum.tms_node, [])
        return datum

    def assume(self, fact: Term, informant: Any = "user") -> Datum:
        """Install ``fact`` as a retractable assumption."""
        datum = self.referent(fact, create=True)
        assert datum is not None
        if datum.assumption is None:
            datum.assumption = informant
            self.jtms.convert_to_assumption(datum.tms_node)
            self.jtms.enable_assumption(datum.tms_node)
        return datum

    def retract(self, fact: Term, informant: Any = "user") -> None:
        datum = self.referent(fact)
        if datum is not None and datum.assumption == informant:
            datum.assumption = None
            self.jtms.retract_assumption(datum.tms_node)

    def justify(self, informant: Any, consequent: Term, antecedents: list[Term]) -> None:
        """Record that ``antecedents`` (ground facts) jointly justify ``consequent``."""
        c = self.referent(consequent, create=True)
        assert c is not None
        anodes = []
        for a in antecedents:
            d = self.referent(a, create=True)
            assert d is not None
            anodes.append(d.tms_node)
        self.jtms.justify_node(informant, c.tms_node, anodes)

    def contradiction(self, fact: Term, informant: Any = "contradiction") -> Datum:
        datum = self.referent(fact, create=True)
        assert datum is not None
        self.jtms.make_contradiction(datum.tms_node)
        return datum

    # -- queries ------------------------------------------------------------ #

    def is_in(self, fact: Term) -> bool:
        d = self.referent(fact)
        return d is not None and d.tms_node.is_in

    def is_out(self, fact: Term) -> bool:
        d = self.referent(fact)
        return d is None or d.tms_node.is_out

    def fetch(self, pattern: Term) -> list[Term]:
        out: list[Term] = []
        for datum in self.get_dbclass(pattern).facts:
            result = unify(pattern, datum.lisp_form)
            if result is not FAIL:
                out.append(substitute(pattern, result))  # type: ignore[arg-type]
        return out

    def why(self, fact: Term) -> str:
        d = self.referent(fact)
        if d is None:
            return f"{fact} is unknown."
        return self.jtms.why_node(d.tms_node)

    # -- rules -------------------------------------------------------------- #

    def add_rule(
        self,
        trigger: Term,
        body: RuleBody,
        *,
        condition: Condition = Condition.IN,
        environment: dict[Var, Term] | None = None,
    ) -> Rule:
        env: dict[Var, Term] = dict(environment) if environment else {}
        self.rule_counter += 1
        rule = Rule(self.rule_counter, trigger, condition, body, env)
        bucket = self.get_dbclass(trigger, env)
        rule.dbclass = bucket
        bucket.rules.append(rule)
        for datum in list(bucket.facts):  # let the new rule see pre-existing data
            self._try_rule_on(rule, datum)
        return rule

    def rule(
        self,
        trigger: Term,
        *,
        condition: Condition = Condition.IN,
        environment: dict[Var, Term] | None = None,
    ) -> Callable[[RuleBody], RuleBody]:
        def register(body: RuleBody) -> RuleBody:
            self.add_rule(trigger, body, condition=condition, environment=environment)
            return body

        return register

    def _try_rule_on(self, rule: Rule, datum: Datum) -> None:
        result = unify(datum.lisp_form, rule.trigger, dict(rule.environment))
        if result is FAIL:
            return
        item = (rule.body, result)
        node = datum.tms_node
        if rule.condition is Condition.INTERN:
            self.queue.append(item)  # type: ignore[arg-type]
        elif rule.condition is Condition.IN:
            if node.is_in:
                self.queue.append(item)  # type: ignore[arg-type]
            else:
                node.in_rules.append(item)
        else:  # Condition.OUT
            if node.is_out:
                self.queue.append(item)  # type: ignore[arg-type]
            else:
                node.out_rules.append(item)

    # -- control loop ------------------------------------------------------- #

    def run_rules(self) -> int:
        fired = 0
        while self.queue:
            body, bindings = self.queue.pop()  # LIFO
            self.rules_run += 1
            fired += 1
            body(bindings, self)
        return fired
