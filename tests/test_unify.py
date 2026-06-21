import pytest

from ltms.terms import Var, read
from ltms.unify import FAIL, substitute, unify

X, Y, Z = Var("x"), Var("y"), Var("z")


def test_identical_atoms_succeed_with_empty_bindings():
    result = unify("a", "a")
    assert result is not FAIL
    assert result == {}


def test_distinct_atoms_fail():
    assert unify("a", "b") is FAIL


def test_empty_success_is_not_fail():
    # The single most important invariant: {} (success) != FAIL (failure).
    assert unify("a", "a") is not FAIL
    assert unify("a", "b") is FAIL


def test_variable_binds_to_constant():
    assert unify(X, "a") == {X: "a"}
    assert unify("a", X) == {X: "a"}


def test_compound_unification():
    assert unify(("f", X, "b"), ("f", "a", Y)) == {X: "a", Y: "b"}


def test_repeated_variable_consistency():
    assert unify(("p", X, X), ("p", "a", "a")) == {X: "a"}
    assert unify(("p", X, X), ("p", "a", "b")) is FAIL


def test_length_mismatch_fails():
    assert unify(("f", "a"), ("f", "a", "b")) is FAIL
    assert unify(("f", "a", "b"), ("f", "a")) is FAIL


def test_atom_vs_compound_fails():
    assert unify("a", ("a",)) is FAIL
    assert unify(("a",), "a") is FAIL


def test_occurs_check_rejects_cyclic_binding():
    assert unify(X, ("f", X)) is FAIL
    assert unify(("f", X), X) is FAIL


def test_variable_to_variable():
    result = unify(X, Y)
    assert result is not FAIL
    # x bound to y (or y to x); substitution makes them agree.
    assert substitute(X, result) == substitute(Y, result)


def test_chained_binding_via_substitute():
    # x = y, y = a  -> substitute(x) resolves the whole chain to a.
    b = unify(X, Y)
    assert b is not FAIL
    b = unify(Y, "a", b)  # type: ignore[arg-type]
    assert b is not FAIL
    assert substitute(X, b) == "a"  # type: ignore[arg-type]


def test_no_standardizing_apart_shared_variable():
    # Same logic variable on both sides is intentional; (p ?x ?x) vs (p a ?x).
    assert unify(read("(p ?x ?x)"), read("(p a ?x)")) == {X: "a"}


def test_substitute_resolves_compound():
    b = {X: "a", Y: ("g", "b")}
    assert substitute(("f", X, Y), b) == ("f", "a", ("g", "b"))


def test_fail_is_not_truthy():
    with pytest.raises(TypeError):
        bool(FAIL)
