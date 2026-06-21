"""Robinson unification over terms, shared by every layer of the engine.

Bindings are a ``dict`` mapping :class:`~ltms.terms.Var` to terms. Functions
return the (possibly extended) bindings on success, or the :data:`FAIL`
sentinel on failure.

**Critical:** the empty dict ``{}`` is a *successful* result meaning "unified
with no new bindings". It must never be confused with failure, so callers test
``result is not FAIL`` -- never truthiness. This mirrors the Lisp ``nil`` vs
``:FAIL`` distinction and is the single most common porting bug.

Unification includes the occurs-check, so it refuses to bind ``?x`` to a term
that contains ``?x`` (e.g. ``?x = (f ?x)``). Variables are **not** standardized
apart: the two sides are assumed to share no variables (database facts are
ground), exactly as in BPS.
"""

from __future__ import annotations

from .terms import Term, Var, is_compound, is_variable


class _Fail:
    """Singleton failure sentinel, distinct from an empty (successful) dict."""

    _instance: _Fail | None = None

    def __new__(cls) -> _Fail:
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance

    def __repr__(self) -> str:
        return "FAIL"

    def __bool__(self) -> bool:  # guard against accidental truthiness tests
        raise TypeError("Do not test unify results for truthiness; compare 'is FAIL'.")


FAIL = _Fail()


def unify(a: Term, b: Term, bindings: dict[Var, Term] | None = None) -> dict[Var, Term] | _Fail:
    """Unify terms ``a`` and ``b`` under ``bindings``.

    Returns the extended bindings, or :data:`FAIL`.
    """
    if bindings is None:
        bindings = {}
    if a == b:  # identical constants, variables, or already-equal subtrees
        return bindings
    if is_variable(a):
        return _unify_var(a, b, bindings)
    if is_variable(b):
        return _unify_var(b, a, bindings)
    if not is_compound(a) or not is_compound(b):
        return FAIL  # unequal atoms, or atom vs compound
    if len(a) != len(b):
        return FAIL
    for xa, xb in zip(a, b, strict=True):
        result = unify(xa, xb, bindings)
        if isinstance(result, _Fail):
            return FAIL
        bindings = result
    return bindings


def _unify_var(v: Var, exp: Term, bindings: dict[Var, Term]) -> dict[Var, Term] | _Fail:
    if v in bindings:
        return unify(bindings[v], exp, bindings)
    if _occurs(v, exp, bindings):
        return FAIL
    extended = dict(bindings)
    extended[v] = exp
    return extended


def _occurs(v: Var, exp: Term, bindings: dict[Var, Term]) -> bool:
    """True iff ``v`` occurs in ``exp`` under ``bindings`` (binding would cycle)."""
    if v == exp:
        return True
    if is_variable(exp):
        if exp in bindings:
            return _occurs(v, bindings[exp], bindings)
        return False
    if is_compound(exp):
        return any(_occurs(v, e, bindings) for e in exp)
    return False


def substitute(term: Term, bindings: dict[Var, Term]) -> Term:
    """Return ``term`` with every variable replaced by its fully resolved value.

    Chains are followed recursively (stronger than the Lisp one-pass ``sublis``),
    which is safe because the occurs-check rules out cyclic bindings.
    """
    if is_variable(term):
        if term in bindings:
            return substitute(bindings[term], bindings)
        return term
    if is_compound(term):
        return tuple(substitute(e, bindings) for e in term)
    return term
