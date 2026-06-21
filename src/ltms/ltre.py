"""LTRE -- a pattern-directed reasoning engine layered on the LTMS.

The engine does universal instantiation (rule matching over a fact database);
the LTMS does all propositional reasoning (clause normalization, BCP, belief
revision, contradictions). Each ground simple proposition maps to one
:class:`Datum`, which owns one LTMS :class:`~ltms.core.TmsNode`. Belief is read
off the node label; ``(not P)`` is just the sign of ``P`` -- there is no node
for the negation.

* ``assert!`` uses *direct translation*: a formula's simple props become nodes,
  connectives stay, and the result is normalized to clauses. No node is created
  for the compound.
* ``assume!`` is asymmetric: a simple proposition is made a retractable
  assumption directly; a compound formula gets a guard node ``N_F`` with
  ``(implies N_F formula)`` so the clauses can be switched off.
* Rules trigger on existence (``INTERN``) or belief (``TRUE`` / ``FALSE``). A
  belief-conditioned rule that matches before the label is decided is parked on
  the node and woken by the LTMS via the injected enqueue procedure.
"""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass, field
from enum import Enum
from typing import Any

from .core import LTMS, Label, TmsNode
from .normalize import CONNECTIVES, add_formula
from .terms import Term, Var, is_compound, is_variable
from .unify import FAIL, substitute, unify

RuleBody = Callable[["dict[Var, Term]", "LTRE"], None]


class Trigger(Enum):
    INTERN = "intern"  # fires as soon as the datum exists
    TRUE = "true"  # fires when the proposition is believed true
    FALSE = "false"  # fires when the proposition is believed false


@dataclass
class Datum:
    counter: int
    lisp_form: Term  # the unsigned simple proposition
    tms_node: TmsNode
    dbclass: Dbclass
    assumption: Any = None  # informant if currently assumed, else None


@dataclass
class Rule:
    counter: int
    trigger: Term  # unsigned pattern
    condition: Trigger
    body: RuleBody
    environment: dict[Var, Term]
    test: Callable[[dict[Var, Term]], bool] | None = None
    dbclass: Dbclass | None = None


@dataclass
class Dbclass:
    name: str
    ltre: LTRE
    facts: list[Datum] = field(default_factory=list)
    rules: list[Rule] = field(default_factory=list)


def _signed(fact: Term) -> tuple[Term, bool]:
    """Split a fact into (unsigned form, is_negated)."""
    if isinstance(fact, tuple) and len(fact) == 2 and fact[0] == "not":
        return fact[1], True
    return fact, False


def _is_simple(form: Term) -> bool:
    """True iff ``form`` is a simple proposition (not a connective formula)."""
    return not (isinstance(form, tuple) and len(form) > 0 and form[0] in CONNECTIVES)


class LTRE:
    """A logic-based reasoning engine instance."""

    def __init__(self, title: str = "ltre", *, debugging: bool = False) -> None:
        self.title = title
        self.debugging = debugging
        self.ltms = LTMS(
            title=f"{title}-ltms",
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
        if is_compound(term):
            if not term:
                raise ValueError("cannot index the empty term ()")
            return self.get_dbclass(term[0], env)
        if is_variable(term):
            if env is not None and term in env:
                return self.get_dbclass(env[term], env)
            raise ValueError(f"dbclass: unbound variable {term!r} in head position")
        if isinstance(term, str):
            bucket = self.dbclass_table.get(term)
            if bucket is None:
                bucket = Dbclass(term, self)
                self.dbclass_table[term] = bucket
            return bucket
        raise ValueError(f"dbclass key must be a symbol, got {term!r}")

    def referent(self, form: Term, *, create: bool = False) -> Datum | None:
        """Intern (or look up) the datum for an unsigned simple proposition."""
        bucket = self.get_dbclass(form)
        for datum in bucket.facts:
            if datum.lisp_form == form:
                return datum
        if not create:
            return None
        self.datum_counter += 1
        node = self.ltms.create_node(None)
        datum = Datum(self.datum_counter, form, node, bucket)
        node.datum = datum
        bucket.facts.append(datum)
        for rule in list(bucket.rules):  # let pre-existing rules see the new datum
            self._try_rule_on(rule, datum)
        return datum

    def build_tms_formula(self, formula: Term) -> Any:
        """Replace simple props with their nodes, leaving connectives in place."""
        if isinstance(formula, tuple) and len(formula) > 0 and formula[0] in CONNECTIVES:
            return (formula[0], *[self.build_tms_formula(s) for s in formula[1:]])
        datum = self.referent(formula, create=True)
        assert datum is not None
        return datum.tms_node

    # -- assertions --------------------------------------------------------- #

    def assert_(self, fact: Term, informant: Any = "user") -> None:
        """Install ``fact`` (any propositional formula) as permanent clauses."""
        add_formula(self.ltms, self.build_tms_formula(fact), informant)

    def assume(self, fact: Term, informant: Any = "user") -> Datum:
        """Install ``fact`` as a retractable assumption."""
        form, neg = _signed(fact)
        if _is_simple(form):
            datum = self.referent(form, create=True)
            assert datum is not None
            node = datum.tms_node
            if datum.assumption is None:
                datum.assumption = informant
                self.ltms.convert_to_assumption(node)
                self.ltms.enable_assumption(node, Label.FALSE if neg else Label.TRUE)
            elif datum.assumption != informant:
                raise ValueError(f"{fact} already assumed by {datum.assumption!r}")
            return datum
        # Compound formula: guard node N_F with (implies N_F formula).
        datum = self.referent(fact, create=True)
        assert datum is not None
        node = datum.tms_node
        if datum.assumption is None:
            datum.assumption = informant
            guarded = ("implies", node, self.build_tms_formula(fact))
            add_formula(self.ltms, guarded, informant)
            self.ltms.convert_to_assumption(node)
            self.ltms.enable_assumption(node, Label.TRUE)
        return datum

    def retract(self, fact: Term, informant: Any = "user") -> None:
        form, _neg = _signed(fact)
        datum = self.referent(form) if _is_simple(form) else self.referent(fact)
        if datum is not None and datum.assumption == informant:
            datum.assumption = None
            self.ltms.retract_assumption(datum.tms_node)

    def contradiction(self, facts: list[Term], informant: Any = "contradiction") -> None:
        """Declare that the given (signed) facts cannot all hold together."""
        trues: list[TmsNode] = []
        falses: list[TmsNode] = []
        for fact in facts:
            form, neg = _signed(fact)
            datum = self.referent(form, create=True)
            assert datum is not None
            (falses if neg else trues).append(datum.tms_node)
        self.ltms.add_clause(falses, trues, informant)

    # -- queries ------------------------------------------------------------ #

    def is_true(self, fact: Term) -> bool:
        form, neg = _signed(fact)
        datum = self.referent(form)
        if datum is None:
            return False
        return datum.tms_node.is_false if neg else datum.tms_node.is_true

    def is_false(self, fact: Term) -> bool:
        form, neg = _signed(fact)
        datum = self.referent(form)
        if datum is None:
            return False
        return datum.tms_node.is_true if neg else datum.tms_node.is_false

    def is_known(self, fact: Term) -> bool:
        form, _neg = _signed(fact)
        datum = self.referent(form)
        return datum is not None and datum.tms_node.is_known

    def is_unknown(self, fact: Term) -> bool:
        return not self.is_known(fact)

    def fetch(self, pattern: Term) -> list[Term]:
        form, _neg = _signed(pattern)
        out: list[Term] = []
        for datum in self.get_dbclass(form).facts:
            result = unify(form, datum.lisp_form)
            if result is not FAIL:
                out.append(substitute(form, result))  # type: ignore[arg-type]
        return out

    # -- rules -------------------------------------------------------------- #

    def add_rule(
        self,
        trigger: Term,
        body: RuleBody,
        *,
        condition: Trigger = Trigger.TRUE,
        test: Callable[[dict[Var, Term]], bool] | None = None,
        environment: dict[Var, Term] | None = None,
    ) -> Rule:
        form, _neg = _signed(trigger)
        env: dict[Var, Term] = dict(environment) if environment else {}
        self.rule_counter += 1
        rule = Rule(self.rule_counter, form, condition, body, env, test)
        bucket = self.get_dbclass(form, env)
        rule.dbclass = bucket
        bucket.rules.append(rule)
        for datum in list(bucket.facts):  # let the new rule see pre-existing data
            self._try_rule_on(rule, datum)
        return rule

    def rule(
        self,
        trigger: Term,
        *,
        condition: Trigger = Trigger.TRUE,
        test: Callable[[dict[Var, Term]], bool] | None = None,
        environment: dict[Var, Term] | None = None,
    ) -> Callable[[RuleBody], RuleBody]:
        def register(body: RuleBody) -> RuleBody:
            self.add_rule(
                trigger, body, condition=condition, test=test, environment=environment
            )
            return body

        return register

    def _try_rule_on(self, rule: Rule, datum: Datum) -> None:
        result = unify(datum.lisp_form, rule.trigger, dict(rule.environment))
        if result is FAIL:
            return
        bindings: dict[Var, Term] = result  # type: ignore[assignment]
        if rule.test is not None and not rule.test(bindings):
            return
        item = (rule.body, bindings)
        node = datum.tms_node
        if rule.condition is Trigger.INTERN:
            self.queue.append(item)
        elif rule.condition is Trigger.TRUE:
            if node.is_true:
                self.queue.append(item)
            else:
                node.true_rules.append(item)
        else:  # Trigger.FALSE
            if node.is_false:
                self.queue.append(item)
            else:
                node.false_rules.append(item)

    # -- control loop ------------------------------------------------------- #

    def run_rules(self) -> int:
        fired = 0
        while self.queue:
            body, bindings = self.queue.pop()  # LIFO
            self.rules_run += 1
            fired += 1
            body(bindings, self)
        return fired

    def uassert(self, fact: Term, informant: Any = "user") -> None:
        """assert! then run rules to quiescence."""
        self.assert_(fact, informant)
        self.run_rules()

    def uassume(self, fact: Term, informant: Any = "user") -> None:
        """assume! then run rules to quiescence."""
        self.assume(fact, informant)
        self.run_rules()
