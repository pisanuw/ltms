"""Indirect proof: prove a fact by refuting its negation.

Assume ``(not fact)``, run rules, and if that assumption participates in a
contradiction, retract it and install a nogood that forces ``fact`` to hold.
This exploits the composable contradiction-handler stack: the pushed handler
resolves only contradictions implicating the assumed negation.
"""

from __future__ import annotations

from .core import ENABLED_ASSUMPTION, Clause, Label
from .ltre import LTRE, _signed
from .terms import Term


def try_indirect_proof(ltre: LTRE, fact: Term) -> bool:
    """Attempt to prove ``fact`` by refutation. Returns whether it now holds."""
    if ltre.is_known(fact):
        return ltre.is_true(fact)
    ltms = ltre.ltms
    form, neg = _signed(fact)
    datum = ltre.referent(form, create=True)
    assert datum is not None
    node = datum.tms_node
    # To prove `fact`, assume its negation and seek a contradiction.
    negation_value = Label.TRUE if neg else Label.FALSE

    def handler(clauses: list[Clause], m: object) -> bool:
        for clause in clauses:
            if clause.is_violated:
                assumptions = ltms.assumptions_of_clause(clause)
                if node in assumptions:
                    status = node.label  # capture before retracting
                    ltms._retract_assumption(node)
                    # nogood forces `node` to the proven (opposite) value.
                    ltms.add_nogood(node, status, assumptions, internal=True)
                    return True
        return False

    with ltms.with_contradiction_handler(handler):
        ltms.convert_to_assumption(node)
        try:
            ltms.enable_assumption(node, negation_value)
            ltre.run_rules()
        finally:
            if node.support is ENABLED_ASSUMPTION:  # negation survived: not proven
                ltms.retract_assumption(node)
    return ltre.is_true(fact)
