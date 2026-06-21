"""TRE -- a tiny pattern-directed forward-chaining inference engine.

This is the minimal substrate every truth-maintenance layer sits on. Belief is
simply "present in the database"; there is no retraction and no notion of
support. The engine has three moving parts:

* a database of **facts**, indexed by the leftmost symbol of each fact
  (``get_dbclass`` -- "car indexing"),
* a database of **rules**, each a ``(trigger pattern, body)`` pair, indexed the
  same way, and
* a **LIFO queue** of pending rule activations drained by :meth:`Tre.run_rules`.

Adding a fact and adding a rule both funnel through the single match point
:meth:`Tre._try_rule_on`, so fact-vs-rule arrival order never matters. Rule
bodies are ordinary Python callables ``body(bindings, tre)`` -- nested
("conjunctive") rules are written by having a body call :meth:`Tre.add_rule`
again, capturing the current bindings.
"""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass, field

from ..terms import Term, Var, is_compound, is_variable, term_to_str
from ..unify import FAIL, substitute, unify

# A rule body receives the match bindings and the engine.
RuleBody = Callable[["dict[Var, Term]", "Tre"], None]


@dataclass
class Rule:
    """A stored rule: a trigger pattern, a body, and a seed environment."""

    counter: int
    trigger: Term
    body: RuleBody
    environment: dict[Var, Term]
    dbclass: Dbclass | None = None


@dataclass
class Dbclass:
    """Index bucket for one leftmost symbol: its facts and its rules."""

    name: str
    tre: Tre
    facts: list[Term] = field(default_factory=list)
    fact_set: set[Term] = field(default_factory=set)
    rules: list[Rule] = field(default_factory=list)


class Tre:
    """A pattern-directed inference engine instance (the 'database')."""

    def __init__(self, title: str = "tre", *, debugging: bool = False) -> None:
        self.title = title
        self.debugging = debugging
        self.dbclass_table: dict[str, Dbclass] = {}
        self.queue: list[tuple[RuleBody, dict[Var, Term]]] = []
        self.rule_counter = 0
        self.rules_run = 0

    # -- indexing ----------------------------------------------------------- #

    def get_dbclass(self, term: Term, env: dict[Var, Term] | None = None) -> Dbclass:
        """Return (creating if needed) the bucket for ``term``'s leftmost symbol."""
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

    # -- facts -------------------------------------------------------------- #

    def assert_(self, fact: Term) -> bool:
        """Add ``fact`` (dedup by equality). If new, queue matching rules.

        Returns True iff the fact was newly added. Does **not** run rules.
        """
        bucket = self.get_dbclass(fact)
        if fact in bucket.fact_set:
            return False
        bucket.fact_set.add(fact)
        bucket.facts.append(fact)
        if self.debugging:
            print(f"  >> asserting {term_to_str(fact)}")
        for rule in list(bucket.rules):
            self._try_rule_on(rule, fact)
        return True

    def fetch(self, pattern: Term) -> list[Term]:
        """Return substituted copies of all facts unifying with ``pattern``."""
        out: list[Term] = []
        for fact in self.get_dbclass(pattern).facts:
            result = unify(pattern, fact)
            if result is not FAIL:
                out.append(substitute(pattern, result))  # type: ignore[arg-type]
        return out

    # -- rules -------------------------------------------------------------- #

    def add_rule(
        self,
        trigger: Term,
        body: RuleBody,
        environment: dict[Var, Term] | None = None,
    ) -> Rule:
        """Install a rule and test it against facts already present."""
        env: dict[Var, Term] = dict(environment) if environment else {}
        self.rule_counter += 1
        rule = Rule(counter=self.rule_counter, trigger=trigger, body=body, environment=env)
        bucket = self.get_dbclass(trigger, env)
        rule.dbclass = bucket
        bucket.rules.append(rule)
        for fact in list(bucket.facts):
            self._try_rule_on(rule, fact)
        return rule

    def rule(
        self, trigger: Term, environment: dict[Var, Term] | None = None
    ) -> Callable[[RuleBody], RuleBody]:
        """Decorator form of :meth:`add_rule`."""

        def register(body: RuleBody) -> RuleBody:
            self.add_rule(trigger, body, environment)
            return body

        return register

    def _try_rule_on(self, rule: Rule, fact: Term) -> None:
        """The single match point: unify, and on success queue the activation."""
        result = unify(fact, rule.trigger, dict(rule.environment))
        if result is not FAIL:
            self.queue.append((rule.body, result))  # type: ignore[arg-type]

    # -- control loop ------------------------------------------------------- #

    def run_rules(self) -> int:
        """Drain the queue to quiescence; return the number of rules fired."""
        fired = 0
        while self.queue:
            body, bindings = self.queue.pop()  # LIFO
            self.rules_run += 1
            fired += 1
            body(bindings, self)
        return fired

    def run_forms(self, facts: list[Term]) -> None:
        """Assert each fact then run rules to quiescence (batch driver)."""
        for fact in facts:
            self.assert_(fact)
            self.run_rules()

    # -- convenience -------------------------------------------------------- #

    def instantiate(self, pattern: Term, bindings: dict[Var, Term]) -> Term:
        """Substitute ``bindings`` into ``pattern`` (for building new facts)."""
        return substitute(pattern, bindings)

    def all_facts(self) -> list[Term]:
        """Every fact currently in the database (debug/inspection)."""
        return [f for bucket in self.dbclass_table.values() for f in bucket.facts]
