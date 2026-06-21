"""ltms -- a logic-based Truth Maintenance System and reasoning engine.

An independent Python reimplementation of the algorithms in Forbus & de Kleer,
*Building Problem Solvers* (MIT Press, 1993). See the project README and NOTICE.
"""

from __future__ import annotations

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
from .unify import FAIL, substitute, unify

__all__ = [
    "FAIL",
    "Term",
    "Var",
    "is_atom",
    "is_compound",
    "is_variable",
    "read",
    "read_all",
    "substitute",
    "term_to_str",
    "unify",
    "var",
]

__version__ = "0.0.0"
