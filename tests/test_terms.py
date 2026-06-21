from ltms.terms import (
    Var,
    is_atom,
    is_compound,
    is_variable,
    read,
    read_all,
    term_to_str,
    var,
)


def test_var_equality_and_hash_by_name():
    assert Var("x") == Var("x")
    assert Var("x") != Var("y")
    assert hash(Var("x")) == hash(Var("x"))
    assert var("?x") == Var("x")  # leading ? stripped
    assert var("x") == Var("x")


def test_predicates():
    assert is_variable(Var("x"))
    assert not is_variable("x")
    assert is_compound(("f", "a"))
    assert not is_compound("f")
    assert is_atom("f")
    assert is_atom(3)
    assert not is_atom(Var("x"))
    assert not is_atom(("f",))


def test_var_not_equal_to_symbol():
    assert Var("x") != "x"
    assert "x" != Var("x")  # noqa: SIM300  (deliberately testing reflected __eq__)


def test_read_simple():
    assert read("foo") == "foo"
    assert read("(foo a b)") == ("foo", "a", "b")
    assert read("(human ?x)") == ("human", Var("x"))


def test_read_nested_and_numbers():
    assert read("(implies (human ?x) (mortal ?x))") == (
        "implies",
        ("human", Var("x")),
        ("mortal", Var("x")),
    )
    assert read("(n 3 -4 2.5)") == ("n", 3, -4, 2.5)
    assert read("()") == ()


def test_read_all():
    forms = read_all("(a) (b ?x)")
    assert forms == [("a",), ("b", Var("x"))]


def test_term_to_str_roundtrip():
    s = "(implies (human ?x) (mortal ?x))"
    assert term_to_str(read(s)) == s
