"""Dependency-directed search over choice sets.

Depth-first assignment of mutually-exclusive choice sets. Each choice is assumed
in turn; rules run; if assuming it produces a contradiction, a pushed handler
identifies the assumptions actually responsible (via ``assumptions_of_clause``)
and installs a nogood that forces this choice false *given those culprits* --
so the same dead combination is never re-explored. When all choice sets are
assigned without contradiction, a solution is recorded.

This is the dependency-directed (nogood-learning) form of backtracking; the
nogood is the learned clause rather than a transient chronological undo.
"""

from __future__ import annotations

from collections.abc import Callable
from typing import Any

from .core import ENABLED_ASSUMPTION, Clause, Label
from .ltre import LTRE, _signed


def dd_search(
    ltre: LTRE,
    choice_sets: list[list[Any]],
    extract: Callable[[LTRE], Any],
) -> list[Any]:
    """Find every assignment of ``choice_sets`` consistent with the LTMS.

    ``extract`` is called with the engine at each solution and its return value
    is collected. Returns the list of extracted solutions.
    """
    solutions: list[Any] = []
    _dds(ltre, [list(cs) for cs in choice_sets], extract, solutions)
    return solutions


def _dds(
    ltre: LTRE,
    choice_sets: list[list[Any]],
    extract: Callable[[LTRE], Any],
    solutions: list[Any],
) -> None:
    if not choice_sets:
        solutions.append(extract(ltre))
        return
    first, rest = choice_sets[0], choice_sets[1:]
    for choice in first:
        if ltre.is_false(choice):
            continue  # already ruled out by a learned nogood
        if ltre.is_true(choice):
            _dds(ltre, rest, extract, solutions)  # forced; rest of set excluded
            return
        form, neg = _signed(choice)
        datum = ltre.referent(form, create=True)
        assert datum is not None
        cnode = datum.tms_node
        value = Label.FALSE if neg else Label.TRUE
        failed = [False]

        def handler(clauses: list[Clause], m: object, cnode: Any = cnode,
                    failed: Any = failed) -> bool:
            for clause in clauses:
                if clause.is_violated:
                    assumptions = ltre.ltms.assumptions_of_clause(clause)
                    if cnode in assumptions:
                        status = cnode.label  # capture before retracting
                        ltre.ltms._retract_assumption(cnode)
                        ltre.ltms.add_nogood(cnode, status, assumptions, internal=True)
                        ltre.queue.clear()  # abandon rule firing down this dead branch
                        failed[0] = True
                        return True
            return False

        with ltre.ltms.with_contradiction_handler(handler):
            ltre.ltms.convert_to_assumption(cnode)
            try:
                ltre.ltms.enable_assumption(cnode, value)
                if not failed[0]:
                    ltre.run_rules()
                if not failed[0]:
                    _dds(ltre, rest, extract, solutions)
            finally:
                if cnode.support is ENABLED_ASSUMPTION:
                    ltre.ltms.retract_assumption(cnode)
