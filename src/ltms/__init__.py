"""ltms -- a logic-based Truth Maintenance System and reasoning engine.

An independent Python reimplementation of the algorithms in Forbus & de Kleer,
*Building Problem Solvers* (MIT Press, 1993). See the project README and NOTICE.

Quick start::

    from ltms import LTRE
    e = LTRE()
    e.assert_(("implies", ("rain",), ("wet",)))
    e.assert_(("rain",))
    e.is_true(("wet",))      # -> True
"""

from __future__ import annotations

from .core import (
    ENABLED_ASSUMPTION,
    LTMS,
    Clause,
    Label,
    LTMSContradiction,
    TmsNode,
    avoid_all,
)
from .cwa import close_predicate, closed_world
from .dds import dd_search
from .explain import explain_node, support_for_node, why_node
from .indirect import try_indirect_proof
from .jtms import JTMS, JTMSContradiction, Justification
from .jtre import JTre
from .ltre import LTRE, Datum, Trigger
from .normalize import add_formula, normalize
from .terms import (
    Term,
    Var,
    is_atom,
    is_compound,
    is_variable,
    read,
    read_all,
    term_to_str,
    var,
)
from .tre import Tre
from .unify import FAIL, substitute, unify

__all__ = [
    # terms & unification
    "Term", "Var", "var", "is_atom", "is_compound", "is_variable",
    "read", "read_all", "term_to_str", "unify", "substitute", "FAIL",
    # TRE
    "Tre",
    # JTMS / JTRE
    "JTMS", "Justification", "JTMSContradiction", "JTre",
    # LTMS core
    "LTMS", "TmsNode", "Clause", "Label", "ENABLED_ASSUMPTION",
    "LTMSContradiction", "avoid_all",
    # CNF + LTRE + facilities
    "normalize", "add_formula", "LTRE", "Datum", "Trigger",
    "try_indirect_proof", "close_predicate", "closed_world", "dd_search",
    # explanation
    "why_node", "explain_node", "support_for_node",
]

__version__ = "0.1.0"
