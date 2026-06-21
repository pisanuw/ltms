"""Property-based checks for unification invariants (Hypothesis)."""

from hypothesis import given
from hypothesis import strategies as st

from ltms.terms import Term, Var
from ltms.unify import FAIL, substitute, unify

_atoms = st.one_of(
    st.sampled_from(["a", "b", "c", "f", "g"]),
    st.integers(min_value=-3, max_value=3),
)
_vars = st.sampled_from([Var("x"), Var("y"), Var("z")])


def _terms(depth: int) -> st.SearchStrategy[Term]:
    if depth <= 0:
        return st.one_of(_atoms, _vars)
    return st.one_of(
        _atoms,
        _vars,
        st.lists(_terms(depth - 1), min_size=0, max_size=3).map(tuple),
    )


terms = _terms(3)


@given(terms, terms)
def test_unify_is_a_unifier(a: Term, b: Term) -> None:
    """If unify succeeds, applying the result makes both sides identical."""
    result = unify(a, b)
    if result is not FAIL:
        assert substitute(a, result) == substitute(b, result)  # type: ignore[arg-type]


@given(terms)
def test_unify_with_self_succeeds(a: Term) -> None:
    assert unify(a, a) is not FAIL


@given(terms, terms)
def test_unify_is_symmetric_in_success(a: Term, b: Term) -> None:
    assert (unify(a, b) is FAIL) == (unify(b, a) is FAIL)
