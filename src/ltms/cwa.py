"""Closed-world assumptions (a simplified, dependency-tracked CWA).

Closing a predicate assumes *false* every currently-undecided instance of that
predicate (negation as failure), as retractable assumptions under one informant.
Because the assumptions are ordinary LTMS assumptions, any later evidence that
one of them is actually true surfaces as a contradiction the caller can resolve,
and the whole closure can be withdrawn at once.

This captures the essence of the BPS CWA; the full set-construal machinery
(reified justifications, construal-uniqueness rules) is left as future work.
"""

from __future__ import annotations

from collections.abc import Iterator
from contextlib import contextmanager

from .ltre import LTRE
from .terms import Term


def close_predicate(ltre: LTRE, predicate: str, *, informant: object = "CWA") -> list[Term]:
    """Assume false every currently-unknown instance of ``predicate``.

    Returns the list of forms that were closed (assumed false).
    """
    bucket = ltre.dbclass_table.get(predicate)
    closed: list[Term] = []
    if bucket is None:
        return closed
    for datum in list(bucket.facts):
        if not datum.tms_node.is_known:
            ltre.assume(("not", datum.lisp_form), informant)
            closed.append(datum.lisp_form)
    return closed


@contextmanager
def closed_world(ltre: LTRE, predicate: str, *, informant: object = "CWA") -> Iterator[list[Term]]:
    """Close ``predicate`` for the duration of the block, then withdraw it."""
    closed = close_predicate(ltre, predicate, informant=informant)
    try:
        yield closed
    finally:
        for form in closed:
            ltre.retract(("not", form), informant)
