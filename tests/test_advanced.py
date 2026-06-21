from ltms.cwa import close_predicate, closed_world
from ltms.dds import dd_search
from ltms.indirect import try_indirect_proof
from ltms.ltre import LTRE

# --- indirect proof -------------------------------------------------------- #


def test_indirect_proof_by_cases():
    # r follows from (p v q), (p -> r), (q -> r), but BCP alone cannot derive it.
    e = LTRE()
    e.assert_(("or", ("p",), ("q",)))
    e.assert_(("implies", ("p",), ("r",)))
    e.assert_(("implies", ("q",), ("r",)))
    assert e.is_unknown(("r",))  # unit propagation is incomplete here
    assert try_indirect_proof(e, ("r",)) is True
    assert e.is_true(("r",))


def test_indirect_proof_fails_when_not_entailed():
    e = LTRE()
    e.assert_(("p",))
    assert try_indirect_proof(e, ("q",)) is False
    assert e.is_unknown(("q",))


def test_indirect_proof_of_negation():
    e = LTRE()
    e.assert_(("implies", ("p",), ("q",)))
    e.assert_(("not", ("q",)))
    # ~p follows (modus tollens); BCP already gets this, but proof should agree.
    assert try_indirect_proof(e, ("not", ("p",))) is True
    assert e.is_false(("p",))


# --- closed-world assumptions --------------------------------------------- #


def _bird_world():
    e = LTRE()
    for b in ("tweety", "opus", "woody"):
        e.referent(("bird", b), create=True)
    e.assert_(("bird", "tweety"))
    return e


def test_close_predicate_assumes_unknowns_false():
    e = _bird_world()
    close_predicate(e, "bird", informant="cwa")
    assert e.is_true(("bird", "tweety"))
    assert e.is_false(("bird", "opus"))
    assert e.is_false(("bird", "woody"))


def test_closed_world_context_manager_withdraws():
    e = _bird_world()
    with closed_world(e, "bird", informant="cwa"):
        assert e.is_false(("bird", "opus"))
    assert e.is_unknown(("bird", "opus"))  # closure withdrawn on exit
    assert e.is_true(("bird", "tweety"))  # real fact untouched


# --- dependency-directed search (graph coloring) --------------------------- #


def _coloring(colors):
    e = LTRE()
    nodes = ["a", "b", "c"]
    edges = [("a", "b"), ("b", "c"), ("a", "c")]  # triangle
    for n in nodes:
        for c in colors:
            e.referent(("color", n, c), create=True)
    for u, v in edges:  # adjacent nodes may not share a color
        for c in colors:
            e.contradiction([("color", u, c), ("color", v, c)], informant="adj")
    choice_sets = [[("color", n, c) for c in colors] for n in nodes]

    def extract(eng):
        return tuple(
            (n, c) for n in nodes for c in colors if eng.is_true(("color", n, c))
        )

    return e, choice_sets, extract


def test_dd_search_three_coloring_triangle():
    e, choice_sets, extract = _coloring(["r", "g", "b"])
    solutions = dd_search(e, choice_sets, extract)
    assert solutions  # triangle is 3-colorable
    for sol in solutions:
        assigned = dict(sol)
        assert set(assigned) == {"a", "b", "c"}  # every node colored
        assert assigned["a"] != assigned["b"]
        assert assigned["b"] != assigned["c"]
        assert assigned["a"] != assigned["c"]


def test_dd_search_two_coloring_triangle_unsatisfiable():
    e, choice_sets, extract = _coloring(["r", "g"])
    solutions = dd_search(e, choice_sets, extract)
    assert solutions == []  # triangle is not 2-colorable
